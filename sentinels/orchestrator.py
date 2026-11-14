"""Runs one case through the agent team and records the outcome in memory.

Flow: investigator -> skeptic -> evidence agent (Linkup) -> adjudicator -> drafter -> citation verifier
(Linkup fetch re-reads every cited page). Verifier scores are attached to the MLflow trace as feedback.
The skeptic only stops a case outright when it is near-certain the spill is innocent; otherwise the
evidence agent tests its objections on the live web and the adjudicator gives the final confidence.
"""
from __future__ import annotations

from datetime import datetime, timezone

from . import agents
from .agents import trace
from .memory import CaseMemory

DISMISS_THRESHOLD = 0.15  # skeptic confidence below this: dismissed without web evidence
REVIEW_THRESHOLD = 0.4    # final confidence for "needs_review" (evidence pack drafted)
BREACH_THRESHOLD = 0.65   # final confidence for "likely_breach"


def run_case(spill: dict, memory: CaseMemory, draft: bool = True) -> dict:
    out = _run_case(spill, memory, draft)
    _log_feedback(out)
    return out


def _log_feedback(out: dict) -> None:
    """Attach the outcome and citation-check score to the case's MLflow trace (shown in the trace UI)."""
    try:
        import mlflow
        from mlflow.entities import AssessmentSource

        trace_id = mlflow.get_last_active_trace_id()
        if not trace_id:
            return
        src = AssessmentSource(source_type="CODE", source_id="sentinels.orchestrator")
        mlflow.log_feedback(trace_id=trace_id, name="final_verdict", value=out["final_verdict"], source=src,
                            rationale=(out.get("ruling") or {}).get("reasoning"))
        v = out.get("citations")
        if v and v["checked"]:
            mlflow.log_feedback(trace_id=trace_id, name="citation_precision", value=v["precision"], source=src,
                                rationale=f"{v['verified']} of {v['checked']} cited claims confirmed by Linkup fetch")
    except Exception as e:  # noqa: BLE001 - tracing is optional
        print("MLflow feedback not logged:", e)


@trace(name="sentinels_case", span_type="CHAIN")
def _run_case(spill: dict, memory: CaseMemory, draft: bool = True) -> dict:
    history = memory.site_history(spill["id"], exclude_event=spill["latesteventstart"])
    case = agents.investigate(spill, history, memory.company_summary(spill["company"]))
    skeptic = agents.challenge(spill, case, history)
    skeptic_conf = float(skeptic["breach_confidence"])

    evidence, ruling, report, citations = None, None, None, None
    conf = skeptic_conf
    if skeptic_conf >= DISMISS_THRESHOLD:
        evidence = agents.gather_evidence(spill, case, skeptic)
        ruling = agents.adjudicate(spill, case, skeptic, evidence)
        conf = float(ruling["final_confidence"])
    verdict = ("likely_breach" if conf >= BREACH_THRESHOLD
               else "needs_review" if conf >= REVIEW_THRESHOLD else "likely_innocent")
    if draft and evidence and verdict != "likely_innocent":
        report = agents.draft_report(spill, case, skeptic, evidence, verdict, ruling)
        try:
            citations = agents.verify_citations(report)
            report += agents.citation_section(citations)
        except Exception as e:  # noqa: BLE001 - the pack is still useful without the check
            print("Citation check failed:", e)

    result = {
        "site_id": spill["id"], "company": spill["company"],
        "watercourse": spill.get("receivingwatercourse"),
        "event_start": spill["latesteventstart"], "duration_hours": spill.get("duration_hours"),
        "final_verdict": verdict, "breach_confidence": conf, "skeptic_confidence": skeptic_conf,
        "skeptic_model": skeptic.get("model"), "strongest_objection": skeptic["strongest_objection"],
        "severity": case["severity"], "n_sources": len(evidence["searches"]) if evidence else 0,
        "decided_at": datetime.now(timezone.utc),
    }
    memory.record(result)
    return {**result, "spill": agents.case_fields(spill), "case": case, "skeptic": skeptic, "evidence": evidence, "ruling": ruling,
            "report": report, "citations": citations}
