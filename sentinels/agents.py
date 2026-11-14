"""The agent team. Each agent has one job; the orchestrator decides the order."""
from __future__ import annotations

import json
import os

import requests

from . import llm

try:  # MLflow tracing when available (always on Databricks); no-op otherwise
    import mlflow

    trace = mlflow.trace
except ImportError:  # pragma: no cover
    def trace(fn=None, **_):
        return fn if fn else (lambda f: f)


def _case_brief(spill: dict) -> str:
    keep = ["id", "company", "receivingwatercourse", "latitude", "longitude", "status",
            "latesteventstart", "latesteventend", "duration_hours", "gauges",
            "max_mm_0_24h_before", "max_mm_24_48h_before", "max_mm_during", "verdict"]
    return json.dumps({k: spill.get(k) for k in keep}, default=str, indent=1)


# ---------------------------------------------------------------- investigator (prosecution)
INVESTIGATOR_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["summary", "breach_indicators", "repeat_offender", "severity", "questions_for_evidence"],
    "properties": {
        "summary": {"type": "string"},
        "breach_indicators": {"type": "array", "items": {"type": "string"}},
        "repeat_offender": {"type": "boolean"},
        "severity": {"type": "string", "enum": ["low", "medium", "high"]},
        "questions_for_evidence": {"type": "array", "items": {"type": "string"},
                                   "description": "What to look up on the live web to confirm or rule out a breach"},
    },
}


@trace(name="investigator", span_type="AGENT")
def investigate(spill: dict, history: list[dict], company_summary: dict) -> dict:
    system = ("You are an environmental investigator. Storm overflows may only discharge sewage when "
              "heavy rain would otherwise flood homes. Build the case that this spill may breach its "
              "permit, using ONLY the data given. Be precise about numbers and never invent facts.")
    user = (f"Spill data (live water-company feed joined to Environment Agency rain gauges):\n"
            f"{_case_brief(spill)}\n\nPast cases at this site from our memory:\n"
            f"{json.dumps(history[-10:], default=str)}\n\nCompany track record in memory: "
            f"{json.dumps(company_summary)}")
    return llm.claude_json(system, user, INVESTIGATOR_SCHEMA)


# ---------------------------------------------------------------- skeptic (defence, different model)
SKEPTIC_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["innocent_explanations", "strongest_objection", "breach_confidence"],
    "properties": {
        "innocent_explanations": {"type": "array", "items": {
            "type": "object", "additionalProperties": False, "required": ["explanation", "plausibility"],
            "properties": {"explanation": {"type": "string"},
                           "plausibility": {"type": "string", "enum": ["low", "medium", "high"]}}}},
        "strongest_objection": {"type": "string"},
        "breach_confidence": {"type": "number", "description": "0-1: probability this is a genuine dry spill"},
    },
}


@trace(name="skeptic", span_type="AGENT")
def challenge(spill: dict, case: dict, history: list[dict]) -> dict:
    system = ("You are a skeptical data auditor defending the water company. Your job is to find every "
              "innocent explanation for this apparent dry-day sewage spill: EDM sensor faults or blips "
              "(very short events), rain the gauges missed (distance, sparse gauges), snowmelt, "
              "groundwater infiltration, tidal outfalls, emergency discharges from pump failure, or "
              "data-feed errors. Rate each honestly. Then give the probability the spill is genuine.")
    user = (f"Spill data:\n{_case_brief(spill)}\n\nInvestigator's case:\n{json.dumps(case)}\n\n"
            f"Past cases at this site (including past sensor-fault findings):\n"
            f"{json.dumps(history[-10:], default=str)}")
    out, model = llm.skeptic_json(system, user, SKEPTIC_SCHEMA)
    out["model"] = model
    return out


# ---------------------------------------------------------------- evidence agent (Linkup)
LINKUP_URL = "https://api.linkup.so/v1/search"


def linkup_search(query: str, depth: str = "standard", from_date: str | None = None) -> dict:
    params = {"q": query, "depth": depth, "outputType": "sourcedAnswer"}
    if from_date:
        params["fromDate"] = from_date
    r = requests.get(LINKUP_URL, params=params, timeout=60,
                     headers={"Authorization": f"Bearer {os.environ['LINKUP_API_KEY']}"})
    r.raise_for_status()
    data = r.json()
    return {"answer": data.get("answer"),
            "sources": [{"name": s.get("name"), "url": s.get("url"), "snippet": (s.get("snippet") or "")[:400]}
                        for s in data.get("sources", [])[:6]]}


LINKUP_TOOL = {
    "name": "linkup_search",
    "description": ("Live web search with cited sources (Linkup). Use for fresh, verifiable context: "
                    "local news about sewage at this river or town, bathing water or swimming closures, "
                    "Environment Agency enforcement or fines against the company, permit details, "
                    "known works or pump failures, and recent weather reports for the area."),
    "strict": True,
    "input_schema": {
        "type": "object", "additionalProperties": False, "required": ["query"],
        "properties": {
            "query": {"type": "string", "description": "A specific natural-language search query"},
            "from_date": {"type": "string", "description": "Optional ISO date (YYYY-MM-DD) to only get results after it"},
        },
    },
}


@trace(name="evidence_agent", span_type="AGENT")
def gather_evidence(spill: dict, case: dict, skeptic: dict, max_searches: int = 5) -> dict:
    """Claude drives Linkup searches to confirm or refute the case, then reports cited findings."""
    system = ("You are a fact-checker building a cited evidence pack about a possible illegal sewage "
              "spill in England. Use linkup_search to verify the investigator's questions AND to test "
              f"the skeptic's objections (e.g. was there unrecorded rain or a reported pump failure?). "
              f"Make at most {max_searches} searches. Only state facts that a source supports, and cite "
              "every one by URL. Finish with a short findings report: what supports a breach, what "
              "supports an innocent explanation, and what is unknown.")
    messages = [{"role": "user", "content":
                 f"Spill:\n{_case_brief(spill)}\n\nInvestigator:\n{json.dumps(case)}\n\n"
                 f"Skeptic:\n{json.dumps(skeptic)}"}]
    searches = []
    for _ in range(max_searches + 2):
        resp = llm.claude_call(system=system, messages=messages, tools=[LINKUP_TOOL],
                               output_config={"effort": "medium"})
        messages.append({"role": "assistant", "content": resp.content})
        if resp.stop_reason != "tool_use":
            break
        results = []
        for block in resp.content:
            if block.type != "tool_use":
                continue
            try:
                out = _traced_search(block.input["query"], block.input.get("from_date"))
                searches.append({"query": block.input["query"], **out})
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(out)})
            except Exception as e:  # noqa: BLE001
                results.append({"type": "tool_result", "tool_use_id": block.id,
                                "content": f"Search failed: {e}", "is_error": True})
        messages.append({"role": "user", "content": results})
    return {"report": llm.text_of(resp), "searches": searches}


@trace(name="linkup_search", span_type="TOOL")
def _traced_search(query, from_date=None):
    return linkup_search(query, from_date=from_date)


# ---------------------------------------------------------------- drafter (action)
@trace(name="drafter", span_type="AGENT")
def draft_report(spill: dict, case: dict, skeptic: dict, evidence: dict, final_verdict: str) -> str:
    system = ("You write evidence packs for possible storm-overflow permit breaches in England, for a "
              "human reviewer to send to the Environment Agency. Be factual, neutral and concise. "
              "Every claim must point to the data or a cited URL. Include the skeptic's strongest "
              "objection honestly. Use Markdown with these sections: Summary, The spill (data), "
              "Rainfall context, Innocent explanations considered, Web evidence (cited), "
              "Confidence and recommendation, Draft message to the Environment Agency. "
              "The draft message must say clearly it is a report of a POSSIBLE breach for investigation.")
    user = (f"Final verdict from our pipeline: {final_verdict}\n\nSpill data:\n{_case_brief(spill)}\n\n"
            f"Investigator:\n{json.dumps(case)}\n\nSkeptic ({skeptic.get('model')}):\n"
            f"{json.dumps(skeptic)}\n\nEvidence agent report:\n{evidence['report']}\n\n"
            f"Raw searches:\n{json.dumps(evidence['searches'])[:20000]}")
    return llm.text_of(llm.claude_call(system=system, messages=[{"role": "user", "content": user}],
                                       output_config={"effort": "medium"}))
