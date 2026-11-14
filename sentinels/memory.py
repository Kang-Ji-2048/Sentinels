"""Case memory: every past case per site, so agents can spot repeat offenders and faulty sensors.

Local runs use a JSONL file. On Databricks, notebooks/03_agents.py syncs this with a Delta table
(sentinels.gold.case_memory) so memory persists across runs and is queryable in SQL.
"""
from __future__ import annotations

import json
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

    def site_history(self, site_id: str) -> list[dict]:
        return [r for r in self.records if r["site_id"] == site_id]

    def company_summary(self, company: str) -> dict:
        rs = [r for r in self.records if r["company"] == company]
        return {"cases": len(rs),
                "likely_breach": sum(r["final_verdict"] == "likely_breach" for r in rs),
                "sites": len({r["site_id"] for r in rs})}

    def record(self, case: dict) -> None:
        self.records.append(case)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a") as f:
            f.write(json.dumps(case, default=str) + "\n")
