"""Serve Andrew's Sentinels page and save report decisions (approve / reject / sent) to a file.

    python andrew-site/serve.py          -> http://localhost:8000

The "Ask about this spill" chat goes to the team's Databricks Genie space (sentinels/genie.py), which answers by
querying the pipeline's tables. It needs DATABRICKS_HOST, DATABRICKS_TOKEN and GENIE_SPACE_ID, either in the
environment or in the repo's .env file.

Decisions go to andrew-site/decisions.json. A rejection of a real (non-example) case is also added to the agents'
case memory (data/case_memory.jsonl), so its reason is in front of the agents next time they look at that site.
Local use only: binds to 127.0.0.1.
"""
import json
import os
import re
import sys
from datetime import datetime, timezone
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
DECISIONS = HERE / "decisions.json"
MEMORY = HERE.parent / "data" / "case_memory.jsonl"
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
STATUSES = {"approved", "rejected", "sent", "draft"}  # "draft" = decision undone
NEXT = {"draft": {"approved", "rejected"}, "approved": {"sent", "draft"}, "rejected": {"draft"}, "sent": {"draft"}}


def load() -> dict:
    return json.loads(DECISIONS.read_text()) if DECISIONS.exists() else {}


def save(decisions: dict) -> None:
    tmp = DECISIONS.with_suffix(".tmp")
    tmp.write_text(json.dumps(decisions, indent=1))
    os.replace(tmp, DECISIONS)  # never leave a half-written file


GENIE_VARS = ("DATABRICKS_HOST", "DATABRICKS_TOKEN", "GENIE_SPACE_ID")


def chat(body: dict) -> dict:
    """One question to Genie; pass the conversation_id back in to follow up in the same conversation."""
    question, conv = body.get("question"), body.get("conversation_id")
    if not isinstance(question, str) or not 0 < len(question.strip()) <= 1500:
        raise ValueError("question must be 1 to 1500 characters")
    if conv is not None and not (isinstance(conv, str) and re.fullmatch(r"[\w-]{1,100}", conv)):
        raise ValueError("bad conversation_id")
    if not all(os.environ.get(k) for k in GENIE_VARS):
        raise LookupError("Genie isn't connected. Set DATABRICKS_HOST, DATABRICKS_TOKEN and GENIE_SPACE_ID in .env "
                          "(or the environment) and restart serve.py.")
    sys.path.insert(0, str(HERE.parent))
    from sentinels import genie  # imported here so the page still serves without it
    out = genie.ask(question.strip(), conv)
    return {"answer": out["text"] or ("Genie ran a query; the result is below." if out["rows"] else "Genie gave no answer."),
            "conversation_id": out["conversation_id"], "status": out["status"], "sql": out["sql"],
            "columns": out["columns"], "rows": out["rows"][:20]}


def text(body: dict, key: str, limit: int) -> str:
    v = body.get(key) or ""
    if not isinstance(v, str) or len(v) > limit:
        raise ValueError(f"{key} must be text under {limit} characters")
    return v.strip()


def decide(body: dict) -> dict:
    key, status = text(body, "key", 200), text(body, "status", 20)
    if not re.fullmatch(r"[\w().\-]+\|[\w:+.\- ]+", key):
        raise ValueError("bad case key")
    if status not in STATUSES:
        raise ValueError("bad status")
    reviewer, note, report = text(body, "reviewer", 100), text(body, "note", 2000), text(body, "report", 50000)
    if not reviewer:
        raise ValueError("reviewer name is required")
    if status == "rejected" and not note:
        raise ValueError("a reason is required to reject")
    decisions = load()
    d = decisions.get(key, {"status": "draft", "log": []})
    if status not in NEXT[d["status"]]:
        raise ValueError(f"can't go from {d['status']} to {status}")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    d.update(status=status, site_id=text(body, "site_id", 60), event_start=text(body, "event_start", 60),
             illustrative=bool(body.get("illustrative")))
    if status == "approved":
        d.update(report=report, approved_by=reviewer, approved_at=now)
    elif status == "rejected":
        d.update(rejected_by=reviewer, rejected_at=now, reason=note)
    elif status == "sent":
        d.update(sent_by=reviewer, sent_at=now, sent_note=note)
    d["log"].append({"status": status, "by": reviewer, "at": now, "note": note})
    decisions[key] = d
    save(decisions)
    if status == "rejected" and not d["illustrative"]:  # never feed made-up example cases to the agents
        MEMORY.parent.mkdir(parents=True, exist_ok=True)
        with MEMORY.open("a") as f:
            f.write(json.dumps({"site_id": d["site_id"], "company": text(body, "company", 100),
                                "event_start": d["event_start"], "final_verdict": "rejected_by_reviewer",
                                "reviewer_reason": note, "decided_at": now}) + "\n")
    return decisions


class Handler(SimpleHTTPRequestHandler):
    def _json(self, code: int, payload) -> None:
        data = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/api/decisions":
            return self._json(200, load())
        return super().do_GET()

    def do_POST(self):
        if self.path not in ("/api/decisions", "/api/chat"):
            return self._json(404, {"error": "not found"})
        # Only this page may write: other sites in the same browser can't send JSON here without a CORS preflight,
        # and anything carrying a foreign Origin is refused.
        origin = self.headers.get("Origin")
        if origin and origin not in (f"http://localhost:{PORT}", f"http://127.0.0.1:{PORT}"):
            return self._json(403, {"error": "forbidden origin"})
        if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
            return self._json(415, {"error": "send JSON"})
        try:
            length = int(self.headers.get("Content-Length", 0))
            if length > 200_000:
                raise ValueError("request too large")
            body = json.loads(self.rfile.read(length))
            if self.path == "/api/chat":
                return self._json(200, chat(body))
            return self._json(200, decide(body))
        except (ValueError, json.JSONDecodeError) as e:
            return self._json(400, {"error": str(e)})
        except LookupError as e:
            return self._json(503, {"error": str(e)})
        except Exception as e:  # Genie or network failure: report it, keep the server up
            print("chat error:", repr(e)[:500])  # full detail in the terminal, not the browser
            return self._json(502, {"error": f"Genie didn't answer ({type(e).__name__}). Check the Databricks settings and network."})


def load_env(path: Path) -> None:
    """KEY=VALUE lines from .env, without overriding what the environment already sets."""
    if path.exists():
        for line in path.read_text().splitlines():
            key, sep, value = line.strip().partition("=")
            if sep and key and not key.startswith("#"):
                os.environ.setdefault(key.removeprefix("export ").strip(), value.strip().strip("'\""))


if __name__ == "__main__":
    load_env(HERE.parent / ".env")
    build = HERE / "build"
    if not (build / "index.html").exists():
        sys.exit("No page yet: run python andrew-site/build.py first.")
    print(f"Sentinels on http://localhost:{PORT}  (decisions saved to {DECISIONS})")
    missing = [k for k in GENIE_VARS if not os.environ.get(k)]
    print("chat (Genie):", "on" if not missing else f"off (missing {', '.join(missing)} in the environment or .env)")
    ThreadingHTTPServer(("127.0.0.1", PORT), partial(Handler, directory=str(build))).serve_forever()
