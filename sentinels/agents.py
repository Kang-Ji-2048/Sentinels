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


CASE_FIELDS = ["id", "company", "receivingwatercourse", "latitude", "longitude", "status",
               "latesteventstart", "latesteventend", "duration_hours", "monitor_offline", "gauges",
               "max_mm_0_24h_before", "max_mm_24_48h_before", "max_mm_during", "verdict"]


def case_fields(spill: dict) -> dict:
    """The spill data every agent sees (also the input of the Adaption triage model)."""
    return {k: spill.get(k) for k in CASE_FIELDS}


def _case_brief(spill: dict) -> str:
    return json.dumps(case_fields(spill), default=str, indent=1)


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
LINKUP_BASE = "https://api.linkup.so/v1"


def _linkup(path: str, body: dict, timeout: int = 60) -> dict:
    r = requests.post(f"{LINKUP_BASE}{path}", json=body, timeout=timeout,
                      headers={"Authorization": f"Bearer {os.environ['LINKUP_API_KEY']}"})
    if r.status_code >= 400:
        raise RuntimeError(f"Linkup {path} -> {r.status_code}: {r.text[:300]}")
    return r.json()


def linkup_search(query: str, depth: str = "standard", from_date: str | None = None,
                  to_date: str | None = None) -> dict:
    body = {"q": query, "depth": depth, "outputType": "sourcedAnswer"}
    if from_date:
        body["fromDate"] = from_date
    if to_date:
        body["toDate"] = to_date
    data = _linkup("/search", body)
    return {"answer": data.get("answer"),
            "sources": [{"name": s.get("name"), "url": s.get("url"), "snippet": (s.get("snippet") or "")[:400]}
                        for s in data.get("sources", [])[:6]]}


def linkup_fetch(url: str, schema: dict | None = None, instructions: str | None = None) -> dict:
    """Reads one web page (Linkup /fetch). With a schema, Linkup extracts grounded fields from it."""
    body = {"url": url}
    if schema:
        body["schema"] = schema
        if instructions:
            body["instructions"] = instructions
    try:
        return _linkup("/fetch", body, timeout=90)
    except RuntimeError as e:  # the schema field may want a JSON string rather than an object
        if schema and "-> 400" in str(e):
            return _linkup("/fetch", {**body, "schema": json.dumps(schema)}, timeout=90)
        raise


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
            "from_date": {"type": "string", "description": "Optional ISO date (YYYY-MM-DD): only results after it"},
            "to_date": {"type": "string", "description": "Optional ISO date (YYYY-MM-DD): only results before it"},
        },
    },
}

LINKUP_FETCH_TOOL = {
    "name": "linkup_fetch",
    "description": ("Read the full text of one web page (Linkup fetch). Use it when a search result looks "
                    "important but its snippet is not enough, e.g. a news article, an EA notice or the "
                    "company's own page about this overflow."),
    "strict": True,
    "input_schema": {
        "type": "object", "additionalProperties": False, "required": ["url"],
        "properties": {"url": {"type": "string", "description": "The page URL, usually from a search result"}},
    },
}


@trace(name="evidence_agent", span_type="AGENT")
def gather_evidence(spill: dict, case: dict, skeptic: dict, max_searches: int = 5, max_fetches: int = 3) -> dict:
    """Claude drives Linkup searches (and full-page reads) to confirm or refute the case, then reports
    cited findings."""
    system = ("You are a fact-checker building a cited evidence pack about a possible illegal sewage "
              "spill in England. Use linkup_search to verify the investigator's questions AND to test "
              f"the skeptic's objections (e.g. was there unrecorded rain or a reported pump failure?). "
              f"Make at most {max_searches} searches; for time-sensitive questions (weather, incidents) set "
              "from_date/to_date to a window around the spill. Use linkup_fetch (at most "
              f"{max_fetches} times) to read a promising page in full before relying on it. "
              "Only state facts that a source supports, and cite "
              "every one by URL. Only cite a source that is actually about this overflow, river, town, "
              "company or the dates in question, from a news outlet, regulator, council, the company itself "
              "or a reference work. Leave out pages that only mention the topic in passing, content farms, "
              "forums, event listings, travel or forecast widgets, and results about other places with the "
              "same name; if a search returns nothing usable, say it found nothing. Finish with a short "
              "findings report: what supports a breach, what supports an innocent explanation, and what "
              "is unknown.")
    messages = [{"role": "user", "content":
                 f"Spill:\n{_case_brief(spill)}\n\nInvestigator:\n{json.dumps(case)}\n\n"
                 f"Skeptic:\n{json.dumps(skeptic)}"}]
    searches, fetches = [], []
    for _ in range(max_searches + max_fetches + 2):
        resp = llm.claude_call(system=system, messages=messages, tools=[LINKUP_TOOL, LINKUP_FETCH_TOOL],
                               output_config={"effort": "medium"})
        messages.append({"role": "assistant", "content": resp.content})
        if resp.stop_reason != "tool_use":
            break
        results = []
        for block in resp.content:
            if block.type != "tool_use":
                continue
            try:
                if block.name == "linkup_fetch":
                    if len(fetches) >= max_fetches:
                        raise RuntimeError("fetch limit reached; write the report with what you have")
                    out = _traced_fetch(block.input["url"])
                    fetches.append({"url": block.input["url"], "chars": len(out["markdown"])})
                else:
                    if len(searches) >= max_searches:
                        raise RuntimeError("search limit reached; write the report with what you have")
                    out = _traced_search(block.input["query"], block.input.get("from_date"),
                                         block.input.get("to_date"))
                    searches.append({"query": block.input["query"], **out})
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(out)})
            except Exception as e:  # noqa: BLE001
                results.append({"type": "tool_result", "tool_use_id": block.id,
                                "content": f"Tool failed: {e}", "is_error": True})
        messages.append({"role": "user", "content": results})
    return {"report": llm.text_of(resp), "searches": searches, "fetches": fetches}


@trace(name="linkup_search", span_type="TOOL")
def _traced_search(query, from_date=None, to_date=None):
    return linkup_search(query, from_date=from_date, to_date=to_date)


@trace(name="linkup_fetch", span_type="TOOL")
def _traced_fetch(url):
    return {"url": url, "markdown": (linkup_fetch(url).get("markdown") or "")[:8000]}


# ---------------------------------------------------------------- citation verifier (Linkup fetch)
CLAIMS_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["claims"],
    "properties": {"claims": {"type": "array", "items": {
        "type": "object", "additionalProperties": False, "required": ["claim", "url"],
        "properties": {"claim": {"type": "string", "description": "One factual claim, in one sentence"},
                       "url": {"type": "string", "description": "The URL cited for it"}}}}},
}
SUPPORT_SCHEMA = {
    "type": "object",
    "properties": {
        "supports_claim": {"type": "boolean", "description": "true only if the page itself states the claim"},
        "quote": {"type": "string", "description": "The sentence on the page that supports the claim, verbatim"},
    },
    "required": ["supports_claim", "quote"],
}


@trace(name="citation_verifier", span_type="AGENT")
def verify_citations(report_md: str, max_checks: int = 10) -> dict:
    """Re-reads every cited page with Linkup fetch and checks it really says what the pack claims."""
    from concurrent.futures import ThreadPoolExecutor

    claims = llm.claude_json(
        "List every factual claim in this evidence pack that is backed by a web URL, one entry per "
        "claim and URL pair. Skip claims backed only by the spill or rain-gauge data.",
        report_md, CLAIMS_SCHEMA, effort="low")["claims"][:max_checks]

    def check(c):
        try:
            data = _traced_check(c["url"], c["claim"])
            ok = data.get("supports_claim") is True and bool(data.get("quote"))
            return {**c, "status": "verified" if ok else "not_supported", "quote": data.get("quote")}
        except Exception as e:  # noqa: BLE001
            return {**c, "status": "unreachable", "quote": None, "error": str(e)[:200]}

    with ThreadPoolExecutor(max_workers=5) as pool:
        checks = list(pool.map(check, claims))
    verified = sum(c["status"] == "verified" for c in checks)
    return {"checked": len(checks), "verified": verified,
            "precision": round(verified / len(checks), 2) if checks else None, "checks": checks}


@trace(name="linkup_verify", span_type="TOOL")
def _traced_check(url, claim):
    return linkup_fetch(url, schema=SUPPORT_SCHEMA,
                        instructions=f"Does this page support this claim? Claim: {claim}").get("data") or {}


def citation_section(v: dict) -> str:
    """Markdown appended to the evidence pack so the human reviewer sees which citations held up."""
    icon = {"verified": "✅", "not_supported": "⚠️", "unreachable": "❔"}
    lines = [f"\n\n## Citation check (Linkup fetch)\n\n{v['verified']} of {v['checked']} cited claims were "
             "confirmed by re-reading the cited page.\n"]
    for c in v["checks"]:
        q = f' "{c["quote"][:200]}"' if c.get("quote") and c["status"] == "verified" else ""
        lines.append(f"- {icon[c['status']]} {c['claim']} ({c['url']}){q}")
    return "\n".join(lines)


# ---------------------------------------------------------------- adjudicator
ADJUDICATOR_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["final_confidence", "objections_refuted", "objections_standing", "reasoning"],
    "properties": {
        "final_confidence": {"type": "number", "description": "0-1: probability this is a genuine dry spill"},
        "objections_refuted": {"type": "array", "items": {"type": "string"}},
        "objections_standing": {"type": "array", "items": {"type": "string"}},
        "reasoning": {"type": "string"},
    },
}


@trace(name="adjudicator", span_type="AGENT")
def adjudicate(spill: dict, case: dict, skeptic: dict, evidence: dict) -> dict:
    """Weighs the skeptic's objections against the cited web evidence and gives a final confidence."""
    system = ("You are an impartial adjudicator. The investigator argues a sewage spill happened on a dry "
              "day; the skeptic gave innocent explanations and a confidence. A fact-checker then searched "
              "the live web. Decide which objections the evidence refutes, which still stand, and give a "
              "final probability that this is a genuine dry-day spill worth reporting for investigation. "
              "Unverified objections are not refuted, but speculative objections with no support in the "
              "data or the web evidence should carry little weight.")
    user = (f"Spill:\n{_case_brief(spill)}\n\nInvestigator:\n{json.dumps(case)}\n\n"
            f"Skeptic ({skeptic.get('model')}):\n{json.dumps(skeptic)}\n\nFact-checker report:\n{evidence['report']}")
    return llm.claude_json(system, user, ADJUDICATOR_SCHEMA)


# ---------------------------------------------------------------- drafter (action)
@trace(name="drafter", span_type="AGENT")
def draft_report(spill: dict, case: dict, skeptic: dict, evidence: dict, final_verdict: str,
                 ruling: dict | None = None) -> str:
    system = ("You write evidence packs for possible storm-overflow permit breaches in England, for a "
              "human reviewer to send to the Environment Agency. Be factual, neutral and concise. "
              "Every claim must point to the data or a cited URL. Only cite sources the evidence agent's "
              "report relies on; never add off-topic pages from the raw searches. Include the skeptic's strongest "
              "objection honestly. Use Markdown with these sections: Summary, The spill (data), "
              "Rainfall context, Innocent explanations considered, Web evidence (cited), "
              "Confidence and recommendation, Draft message to the Environment Agency. "
              "The draft message must say clearly it is a report of a POSSIBLE breach for investigation.")
    user = (f"Final verdict from our pipeline: {final_verdict}\n\nSpill data:\n{_case_brief(spill)}\n\n"
            f"Investigator:\n{json.dumps(case)}\n\nSkeptic ({skeptic.get('model')}):\n"
            f"{json.dumps(skeptic)}\n\nEvidence agent report:\n{evidence['report']}\n\n"
            f"Adjudicator ruling:\n{json.dumps(ruling)}\n\n"
            f"Raw searches:\n{json.dumps(evidence['searches'])[:20000]}")
    return llm.text_of(llm.claude_call(system=system, messages=[{"role": "user", "content": user}],
                                       output_config={"effort": "medium"}))
