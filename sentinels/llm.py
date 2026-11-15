"""Model clients. Claude for investigator/evidence/drafter; a different model for the skeptic.

The skeptic runs on a Databricks-served open model when DATABRICKS_HOST/DATABRICKS_TOKEN are set
(Databricks Foundation Model APIs speak the OpenAI chat format). Otherwise it falls back to a
smaller Claude model so the pipeline still runs anywhere. Set the skeptic model to
"adaption:<model id>" (e.g. adaption:qwen3.5-397b) to use an Adaption Labs hosted model instead.
"""
from __future__ import annotations

import json
import os

import anthropic

CLAUDE_MODEL = os.environ.get("SENTINELS_CLAUDE_MODEL", "claude-opus-5-5")
SKEPTIC_FALLBACK_MODEL = "claude-haiku-5-5"
# Databricks foundation models are served through Unity Gateway as system.ai.<name>;
# names differ by workspace (see the model-listing cell in notebooks/03_agents).
SKEPTIC_DATABRICKS_MODEL = os.environ.get("SENTINELS_SKEPTIC_MODEL", "system.ai.gpt-oss-120b")

_claude = None
# On Databricks, set with gateway_client() below
SKEPTIC_CLIENT = None


def gateway_client(host: str, token: str):
    """OpenAI-compatible client for Databricks Unity Gateway (foundation models under system.ai)."""
    from openai import OpenAI

    return OpenAI(api_key=token, base_url=f"{host.rstrip('/')}/ai-gateway/mlflow/v1")


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


def _name_variants(name: str) -> list[str]:
    """Unity Gateway accepts different spellings across workspaces: try the common ones."""
    short = name.removeprefix("system.ai.")
    bare = short.removeprefix("databricks-")
    out = []
    for n in [name, short, f"system.ai.{bare}", bare, f"databricks-{bare}"]:
        if n not in out:
            out.append(n)
    return out


def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    return json.loads(raw[raw.find("{"): raw.rfind("}") + 1])  # tolerate code fences / prose around it


def skeptic_json(system: str, user: str, schema: dict) -> tuple[dict, str]:
    """Returns (parsed JSON, model name used)."""
    prompt = (f"{user}\n\nRespond with ONLY a JSON object matching this JSON schema, no prose:\n"
              f"{json.dumps(schema)}")
    if SKEPTIC_DATABRICKS_MODEL.startswith("adaption:"):  # Adaption Labs hosted model
        from . import adaption

        model = SKEPTIC_DATABRICKS_MODEL.removeprefix("adaption:")
        try:
            return _parse_json(adaption.respond(model, system, prompt)), SKEPTIC_DATABRICKS_MODEL
        except Exception as e:  # noqa: BLE001
            print(f"Adaption skeptic model unavailable ({e}); falling back to {SKEPTIC_FALLBACK_MODEL}")
    host, token = os.environ.get("DATABRICKS_HOST"), os.environ.get("DATABRICKS_TOKEN")
    client = SKEPTIC_CLIENT
    if client is None and host and token:
        client = gateway_client(host, token)
    if client is not None and not SKEPTIC_DATABRICKS_MODEL.startswith("adaption:"):
        last_err = None
        for model in _name_variants(SKEPTIC_DATABRICKS_MODEL):
            try:
                r = client.chat.completions.create(
                    model=model, max_tokens=2000,
                    messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}])
            except Exception as e:  # noqa: BLE001 - wrong name / not enabled: try the next form
                last_err = e
                continue
            try:
                return _parse_json(r.choices[0].message.content), model
            except ValueError as e:  # malformed JSON from the open model: fall back below instead of crashing
                last_err = e
                break
        print(f"Databricks skeptic model unavailable ({last_err}); falling back to {SKEPTIC_FALLBACK_MODEL}")
    resp = claude().messages.create(
        model=SKEPTIC_FALLBACK_MODEL, max_tokens=4000, system=system,
        messages=[{"role": "user", "content": user}],
        output_config={"format": {"type": "json_schema", "schema": schema}})
    return json.loads(text_of(resp)), SKEPTIC_FALLBACK_MODEL
