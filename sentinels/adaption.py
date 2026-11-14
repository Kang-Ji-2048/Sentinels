"""Adaption Labs API: hosted model responses, dataset upload and AutoScientist training.

Used two ways:
1. As a model provider (skeptic_model = "adaption:<model id>", e.g. adaption:qwen3.5-397b).
2. To turn our adjudicated cases into a training set and train a small spill-triage model that
   learns from the agent team's past verdicts (notebooks/04_adaption.py).
Docs: https://docs.adaptionlabs.ai/api
"""
from __future__ import annotations

import hashlib
import json
import os

import requests

BASE = "https://api.prod.adaptionlabs.ai/api/v1"
TIMEOUT = 120


def _headers() -> dict:
    return {"Authorization": f"Bearer {os.environ['ADAPTION_API_KEY']}", "Content-Type": "application/json"}


def _req(method: str, path: str, **kw) -> dict:
    r = requests.request(method, f"{BASE}{path}", headers=_headers(), timeout=TIMEOUT, **kw)
    if r.status_code >= 400:
        raise RuntimeError(f"Adaption {method} {path} -> {r.status_code}: {r.text[:500]}")
    return r.json() if r.content else {}


# ---------------------------------------------------------------- hosted models
def list_models() -> list[str]:
    return [m["id"] for m in _req("GET", "/models", params={"type": "hosted"}).get("data", [])]


def respond(model: str, system: str, user: str) -> str:
    """One-shot text generation via the Responses API; returns the output text."""
    data = _req("POST", "/responses", json={
        "model": model,
        "input": [{"role": "system", "content": system}, {"role": "user", "content": user}]})
    if data.get("output_text"):
        return data["output_text"]
    parts = []
    for item in data.get("output", []):
        for c in item.get("content", []) or []:
            if isinstance(c, dict) and c.get("text"):
                parts.append(c["text"])
    return "".join(parts)


# ---------------------------------------------------------------- datasets + training
def upload_dataset(path: str, name: str, prompt_col: str = "prompt", completion_col: str = "completion") -> str:
    """Upload a JSONL file of prompt/completion rows as a raw dataset; returns dataset_id."""
    body = open(path, "rb").read()
    created = _req("POST", "/datasets", json={"source": {
        "name": name, "file_format": "jsonl", "processing_mode": "raw",
        "column_mapping": {"prompt": prompt_col, "completion": completion_col}}})
    up = created["upload_instructions"]
    put = requests.request(up.get("method", "PUT"), up["url"], data=body, timeout=TIMEOUT)
    put.raise_for_status()
    _req("POST", f"/datasets/{created['dataset_id']}/upload/complete",
         json={"file_size_bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()})
    return created["dataset_id"]


def dataset_status(dataset_id: str) -> dict:
    return _req("GET", f"/datasets/{dataset_id}/status")


def train(dataset_id: str, model: str | None = None, max_iterations: int = 1) -> dict:
    """Start an AutoScientist run (instruction tuning). Poll with run_status()."""
    payload = {"dataset_id": dataset_id, "training_method": "instruction", "max_iterations": max_iterations}
    if model:
        payload["model"] = model
    return _req("POST", "/autoscientist", json=payload)


def run_status(experiment_id: str) -> dict:
    return _req("GET", f"/autoscientist/{experiment_id}")


def base_models() -> dict:
    return _req("GET", "/autoscientist/models")


# ---------------------------------------------------------------- training examples
def training_example(result: dict) -> dict | None:
    """One adjudicated case -> a prompt/completion pair for a spill-triage model.

    The prompt holds only what's known before the expensive agents run (spill + rainfall data);
    the completion is the agent team's final verdict and reasoning, so the trained model learns
    to triage new candidates cheaply.
    """
    spill = result.get("spill")
    if not spill:
        return None
    ruling = result.get("ruling") or {}
    completion = {
        "verdict": result["final_verdict"],
        "confidence": round(float(result["breach_confidence"]), 2),
        "key_objection": result.get("strongest_objection"),
        "reasoning": ruling.get("reasoning") or result.get("skeptic", {}).get("strongest_objection"),
    }
    prompt = ("Triage this storm overflow spill in England. Is it a likely permit breach (a spill on a dry "
              "day), one that needs review, or likely innocent? Answer in JSON with verdict, confidence, "
              "key_objection and reasoning.\n\n" + json.dumps(spill, default=str))
    return {"prompt": prompt, "completion": json.dumps(completion)}
