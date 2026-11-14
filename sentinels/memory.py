"""Case memory: every past case per site, so agents can spot repeat offenders and faulty sensors.

Local runs use a JSONL file. On Databricks, notebooks/03_agents.py syncs this with a Delta table
(sentinels.gold.case_memory) so memory persists across runs and is queryable in SQL.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parents[1] / "data" / "case_memory.jsonl"


class CaseMemory:
    def __init__(self, path: Path | str = DEFAULT_PATH, records: list[dict] | None = None):
        self.path = Path(path)
        if records is not None:
            self.records = records
        elif self.path.exists():
            self.records = [json.loads(l) for l in self.path.read_text().splitlines() if l.strip()]
        else:
            self.records = []
        self.records = _latest_per_event(self.records)

    def site_history(self, site_id: str, exclude_event: object = None) -> list[dict]:
        """Past cases at a site. Pass the current spill's start to leave out earlier verdicts on that same spill."""
        skip = _event_key(site_id, exclude_event) if exclude_event is not None else None
        return [r for r in self.records if r["site_id"] == site_id
                and _event_key(r["site_id"], r.get("event_start")) != skip]

    def company_summary(self, company: str) -> dict:
        rs = [r for r in self.records if r["company"] == company]
        return {"cases": len(rs),
                "likely_breach": sum(r["final_verdict"] == "likely_breach" for r in rs),
                "sites": len({r["site_id"] for r in rs})}

    def record(self, case: dict) -> None:
        """Adds a case; a re-decided spill replaces its earlier verdict in memory."""
        self.records = _latest_per_event(self.records + [case])
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a") as f:
            f.write(json.dumps(case, default=str) + "\n")


def _event_key(site_id, event_start) -> tuple:
    try:  # datetimes from Delta and ISO strings from JSON compare equal
        return site_id, datetime.fromisoformat(str(event_start))
    except ValueError:
        return site_id, str(event_start)


def _latest_per_event(records: list[dict]) -> list[dict]:
    """One record per (site, spill): the most recently decided one."""
    latest = {}
    for r in records:
        k = _event_key(r["site_id"], r.get("event_start"))
        if k not in latest or str(r.get("decided_at")) >= str(latest[k].get("decided_at")):
            latest[k] = r
    return list(latest.values())
