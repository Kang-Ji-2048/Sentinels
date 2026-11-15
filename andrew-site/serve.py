"""Serve Andrew's Sentinels page and save report decisions (approve / reject / sent) to a file.

    python andrew-site/serve.py          -> http://localhost:8000

Decisions go to andrew-site/decisions.json. A rejection of a real (non-example) case is also added to the agents'
case memory (data/case_memory.jsonl), so its reason is in front of the agents next time they look at that site.
The Ask tab's questions go to the Sentinels Genie agent through sentinels/genie.py, when DATABRICKS_HOST,
DATABRICKS_TOKEN and GENIE_SPACE_ID are set in the environment (never commit them).
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
sys.path.insert(0, str(HERE.parent))  # repo root, for sentinels.genie
from sentinels import genie  # noqa: E402
DECISIONS = HERE / "decisions.json"
MEMORY = HERE.parent / "data" / "case_memory.jsonl"
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
STATUSES = {"approved", "rejected", "sent", "draft"}  # "draft" = decision undone
NEXT = {"draft": {"approved", "rejected"}, "approved": {"sent", "draft"}, "rejected": {"draft"}, "sent": {"draft"}}


def load() -> dict:
    return json.loads(DECISIONS.read_text(encoding="utf-8")) if DECISIONS.exists() else {}


def save(decisions: dict) -> None:
    tmp = DECISIONS.with_suffix(".tmp")
    tmp.write_text(json.dumps(decisions, indent=1), encoding="utf-8")
    os.replace(tmp, DECISIONS)  # never leave a half-written file


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
        with MEMORY.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"site_id": d["site_id"], "company": text(body, "company", 100),
                                "event_start": d["event_start"], "final_verdict": "rejected_by_reviewer",
                                "reviewer_reason": note, "decided_at": now}) + "\n")
    return decisions


def ask_genie(body: dict) -> dict:
    question = text(body, "question", 500)
    if not question:
        raise ValueError("ask a question")
    conv = text(body, "conversation_id", 100) or None
    if conv and not re.fullmatch(r"[\w\-]+", conv):
        raise ValueError("bad conversation id")
    return genie.ask(question, conv)


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
        if self.path == "/api/genie":
            return self._json(200, {"configured": genie.configured()})
        return super().do_GET()

    def do_POST(self):
        routes = {"/api/decisions": decide, "/api/genie": ask_genie}
        if self.path not in routes:
            return self._json(404, {"error": "not found"})
        if self.path == "/api/genie" and not genie.configured():
            return self._json(503, {"error": "Genie isn't set up on this machine"})
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
            if not isinstance(body, dict):
                raise ValueError("send a JSON object")
            return self._json(200, routes[self.path](body))
        except (ValueError, json.JSONDecodeError) as e:
            return self._json(400, {"error": str(e)})
        except Exception as e:  # noqa: BLE001 - Genie / network failure: say so, keep serving
            print(f"{self.path} error:", e, file=sys.stderr)
            return self._json(502, {"error": "Genie didn't answer. Check the server window for details."
                                    if self.path == "/api/genie" else "Couldn't save. Check the server window."})


def load_env(path: Path) -> None:
    """KEY=VALUE lines from .env, without overriding what the environment already sets."""
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            key, sep, value = line.strip().partition("=")
            if sep and key and not key.startswith("#"):
                os.environ.setdefault(key.removeprefix("export ").strip(), value.strip().strip("'\""))


if __name__ == "__main__":
    load_env(HERE.parent / ".env")
    build = HERE / "build"
    if not (build / "index.html").exists():
        sys.exit("No page yet: run python andrew-site/build.py first.")
    print(f"Sentinels on http://localhost:{PORT}  (decisions saved to {DECISIONS})")
    print("Ask tab:", "Genie connected" if genie.configured() else "off (set DATABRICKS_HOST, DATABRICKS_TOKEN, GENIE_SPACE_ID)")
    ThreadingHTTPServer(("127.0.0.1", PORT), partial(Handler, directory=str(build))).serve_forever()
