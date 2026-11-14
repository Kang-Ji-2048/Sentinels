"""Runs one case through the agent team and records the outcome in memory.

Flow: investigator -> skeptic -> (only if the case survives) evidence agent -> drafter.
The skeptic gates the expensive steps, so obviously innocent spills cost one cheap call.
"""
from __future__ import annotations

from datetime import datetime, timezone

from . import agents
from .agents import trace
from .memory import CaseMemory

SURVIVE_THRESHOLD = 0.4   # skeptic's breach_confidence needed to spend on web evidence
BREACH_THRESHOLD = 0.65   # confidence needed to call it a likely breach


@trace(name="sentinels_case", span_type="CHAIN")
def run_case(spill: dict, memory: CaseMemory, draft: bool = True) -> dict:
    history = memory.site_history(spill["id"])
    case = agents.investigate(spill, history, memory.company_summary(spill["company"]))
    skeptic = agents.challenge(spill, case, history)
    conf = float(skeptic["breach_confidence"])

    evidence, report = None, None
    if conf >= SURVIVE_THRESHOLD:
        evidence = agents.gather_evidence(spill, case, skeptic)
        verdict = "likely_breach" if conf >= BREACH_THRESHOLD else "needs_review"
        if draft:
            report = agents.draft_report(spill, case, skeptic, evidence, verdict)
    else:
        verdict = "likely_innocent"

    result = {
        "site_id": spill["id"], "company": spill["company"],
        "watercourse": spill.get("receivingwatercourse"),
        "event_start": spill["latesteventstart"], "duration_hours": spill.get("duration_hours"),
        "final_verdict": verdict, "breach_confidence": conf,
        "skeptic_model": skeptic.get("model"), "strongest_objection": skeptic["strongest_objection"],
        "severity": case["severity"], "n_sources": len(evidence["searches"]) if evidence else 0,
        "decided_at": datetime.now(timezone.utc),
    }
    memory.record(result)
    return {**result, "case": case, "skeptic": skeptic, "evidence": evidence, "report": report}
