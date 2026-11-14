"""Ask the Sentinels Genie agent (Databricks AI/BI Genie) a question from outside Databricks.

Used by the site's local server so visitors can ask follow-up questions in plain English
("which company has the most dry spills?"). Genie writes the SQL against our gold tables and views,
runs it, and answers. Docs: Databricks Genie Conversation API (/api/2.0/genie/spaces/...).

Needs three environment variables on the machine running the site (never commit them):
  DATABRICKS_HOST   e.g. https://dbc-xxxx.cloud.databricks.com
  DATABRICKS_TOKEN  a personal access token (User settings > Developer > Access tokens)
  GENIE_SPACE_ID    the agent ID shown in the Genie agent's About tab
"""
from __future__ import annotations

import os
import time

import requests

TIMEOUT = 30


def _base() -> str:
    host = os.environ["DATABRICKS_HOST"].rstrip("/")
    return f"{host}/api/2.0/genie/spaces/{os.environ['GENIE_SPACE_ID']}"


def _call(method: str, path: str, **kw) -> dict:
    r = requests.request(method, _base() + path, timeout=TIMEOUT,
                         headers={"Authorization": f"Bearer {os.environ['DATABRICKS_TOKEN']}"}, **kw)
    if r.status_code >= 400:
        raise RuntimeError(f"Genie {method} {path} -> {r.status_code}: {r.text[:300]}")
    return r.json() if r.content else {}


def configured() -> bool:
    return all(os.environ.get(k) for k in ("DATABRICKS_HOST", "DATABRICKS_TOKEN", "GENIE_SPACE_ID"))


def ask(question: str, conversation_id: str | None = None, wait_s: int = 90, max_rows: int = 50) -> dict:
    """Ask a question (pass conversation_id to follow up). Returns
    {conversation_id, status, text, sql, sql_description, columns, rows}."""
    if conversation_id:
        msg = _call("POST", f"/conversations/{conversation_id}/messages", json={"content": question})
    else:
        msg = _call("POST", "/start-conversation", json={"content": question})
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
        out["text"] = (m.get("error") or {}).get("error") if isinstance(m.get("error"), dict) else m.get("error")
        out["text"] = out["text"] or f"Genie did not finish (status {status})."
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
            except Exception as e:  # noqa: BLE001 - the text answer is still useful
                out["text"] = out["text"] or f"(query ran, but the result could not be read: {e})"
    return out


if __name__ == "__main__":  # quick check: python -m sentinels.genie "which company has the most dry spills?"
    import json
    import sys

    print(json.dumps(ask(" ".join(sys.argv[1:]) or "Which company has the most dry spills?"), indent=1))
