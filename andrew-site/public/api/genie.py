"""Vercel serverless function: the hosted site's "Ask Genie" box -> Databricks Genie.

Same contract as andrew-site/serve.py's /api/genie, so the page works unchanged:
  GET  /api/genie  -> {"configured": bool}
  POST /api/genie  {"question", "conversation_id"?} -> {conversation_id, status, text, sql, sql_description, columns, rows}

Set DATABRICKS_HOST, DATABRICKS_TOKEN and GENIE_SPACE_ID in the Vercel project's Environment Variables
(never in the repo). Self-contained (standard library only) because Vercel only ships this folder.
Mirrors sentinels/genie.py.
"""
import json
import os
import re
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler

KEYS = ("DATABRICKS_HOST", "DATABRICKS_TOKEN", "GENIE_SPACE_ID")


def configured() -> bool:
    return all(os.environ.get(k) for k in KEYS)


def _call(method: str, path: str, body: dict | None = None) -> dict:
    base = f"{os.environ['DATABRICKS_HOST'].rstrip('/')}/api/2.0/genie/spaces/{os.environ['GENIE_SPACE_ID']}"
    req = urllib.request.Request(base + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": f"Bearer {os.environ['DATABRICKS_TOKEN']}",
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        raw = r.read()
    return json.loads(raw) if raw else {}


def ask(question: str, conversation_id: str | None, wait_s: int = 50, max_rows: int = 50) -> dict:
    if conversation_id:
        msg = _call("POST", f"/conversations/{conversation_id}/messages", {"content": question})
    else:
        msg = _call("POST", "/start-conversation", {"content": question})
        conversation_id = msg["conversation_id"]
    message_id = msg.get("message_id") or msg.get("id") or msg.get("message", {}).get("id")
    path = f"/conversations/{conversation_id}/messages/{message_id}"
    deadline = time.time() + wait_s
    while True:
        m = _call("GET", path)
        status = m.get("status")
        if status in ("COMPLETED", "FAILED", "CANCELLED", "QUERY_RESULT_EXPIRED") or time.time() > deadline:
            break
        time.sleep(1.5)
    out = {"conversation_id": conversation_id, "status": status, "text": None, "sql": None,
           "sql_description": None, "columns": [], "rows": []}
    if status != "COMPLETED":
        err = m.get("error")
        out["text"] = (err.get("error") if isinstance(err, dict) else err) or f"Genie did not finish (status {status})."
        return out
    for att in m.get("attachments") or []:
        if att.get("text"):
            out["text"] = att["text"].get("content")
        if att.get("query"):
            out["sql"] = att["query"].get("query")
            out["sql_description"] = att["query"].get("description")
            try:
                res = _call("GET", f"{path}/attachments/{att['attachment_id']}/query-result")
                sr = res.get("statement_response", res)
                out["columns"] = [c["name"] for c in sr["manifest"]["schema"]["columns"]]
                out["rows"] = (sr.get("result") or {}).get("data_array", [])[:max_rows]
            except Exception:  # noqa: BLE001 - the text answer is still useful
                pass
    return out


class handler(BaseHTTPRequestHandler):
    def _json(self, code: int, payload) -> None:
        data = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        return self._json(200, {"configured": configured()})

    def do_POST(self):
        if not configured():
            return self._json(503, {"error": "Genie isn't set up on this deployment"})
        origin, host = self.headers.get("Origin"), self.headers.get("Host")
        if origin and host and origin.split("://", 1)[-1] != host:  # only the site itself may ask
            return self._json(403, {"error": "forbidden origin"})
        if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
            return self._json(415, {"error": "send JSON"})
        try:
            length = int(self.headers.get("Content-Length", 0))
            if length > 5000:
                raise ValueError("request too large")
            body = json.loads(self.rfile.read(length))
            question = (body.get("question") or "").strip() if isinstance(body, dict) else ""
            conv = (body.get("conversation_id") or "").strip() or None
            if not question or len(question) > 500:
                raise ValueError("ask a question (under 500 characters)")
            if conv and not re.fullmatch(r"[\w\-]{1,100}", conv):
                raise ValueError("bad conversation id")
            return self._json(200, ask(question, conv))
        except (ValueError, json.JSONDecodeError) as e:
            return self._json(400, {"error": str(e)})
        except (urllib.error.URLError, KeyError, TimeoutError):
            return self._json(502, {"error": "Genie didn't answer. Try again in a moment."})
