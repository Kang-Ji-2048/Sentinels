"""Model clients. Claude for investigator/evidence/drafter; a different model for the skeptic.

The skeptic runs on a Databricks-served open model when DATABRICKS_HOST/DATABRICKS_TOKEN are set
(Databricks Foundation Model APIs speak the OpenAI chat format). Otherwise it falls back to a
smaller Claude model so the pipeline still runs anywhere.
"""
from __future__ import annotations

import json
import os

import anthropic

CLAUDE_MODEL = os.environ.get("SENTINELS_CLAUDE_MODEL", "claude-opus-5-5")
SKEPTIC_FALLBACK_MODEL = "claude-haiku-5-5"
# Model names available differ by workspace: check Serving > Foundation models.
SKEPTIC_DATABRICKS_MODEL = os.environ.get("SENTINELS_SKEPTIC_MODEL", "databricks-meta-llama-3-3-70b-instruct")

_claude = None
# On Databricks, set this to WorkspaceClient().serving_endpoints.get_open_ai_client()
SKEPTIC_CLIENT = None


def claude() -> anthropic.Anthropic:
    global _claude
    if _claude is None:
        _claude = anthropic.Anthropic()
    return _claude


def claude_call(**kwargs):
    """messages.create with server-side refusal fallback enabled."""
    kwargs.setdefault("model", CLAUDE_MODEL)
    kwargs.setdefault("max_tokens", 16000)
    resp = claude().beta.messages.create(
        betas=["server-side-fallback-2026-07-01"], fallbacks="default", **kwargs)
    if resp.stop_reason == "refusal":
        raise RuntimeError(f"Model refused: {resp.stop_details}")
    return resp


def text_of(resp) -> str:
    return "".join(b.text for b in resp.content if b.type == "text")


def claude_json(system: str, user: str, schema: dict, effort: str = "medium") -> dict:
    resp = claude_call(system=system, messages=[{"role": "user", "content": user}],
                       output_config={"effort": effort,
                                      "format": {"type": "json_schema", "schema": schema}})
    return json.loads(text_of(resp))


def skeptic_json(system: str, user: str, schema: dict) -> tuple[dict, str]:
    """Returns (parsed JSON, model name used)."""
    host, token = os.environ.get("DATABRICKS_HOST"), os.environ.get("DATABRICKS_TOKEN")
    client = SKEPTIC_CLIENT
    if client is None and host and token:
        from openai import OpenAI  # Databricks serving endpoints are OpenAI-compatible

        client = OpenAI(api_key=token, base_url=f"{host.rstrip('/')}/serving-endpoints")
    if client is not None:
        prompt = (f"{user}\n\nRespond with ONLY a JSON object matching this JSON schema, no prose:\n"
                  f"{json.dumps(schema)}")
        r = client.chat.completions.create(
            model=SKEPTIC_DATABRICKS_MODEL, max_tokens=2000,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}])
        raw = r.choices[0].message.content.strip()
        raw = raw[raw.find("{"): raw.rfind("}") + 1]  # tolerate code fences around the JSON
        return json.loads(raw), SKEPTIC_DATABRICKS_MODEL
    resp = claude().messages.create(
        model=SKEPTIC_FALLBACK_MODEL, max_tokens=4000, system=system,
        messages=[{"role": "user", "content": user}],
        output_config={"format": {"type": "json_schema", "schema": schema}})
    return json.loads(text_of(resp)), SKEPTIC_FALLBACK_MODEL
