"""Run the agent team locally on the latest detector run (no Databricks needed).

Needs ANTHROPIC_API_KEY and LINKUP_API_KEY in the environment. The skeptic uses Claude Haiku
locally (or Unity Gateway if DATABRICKS_HOST and DATABRICKS_TOKEN are set).
    python scripts/detect.py          # refresh data/latest_run.json
    python scripts/agents.py 1        # investigate the top N candidates (default 1)
Evidence packs are written to data/reports/.
"""
import json
import sys
from datetime import datetime
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
try:  # use the OS certificate store (needed behind antivirus HTTPS scanning)
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass
from sentinels import orchestrator  # noqa: E402
from sentinels.memory import CaseMemory  # noqa: E402

top_n = int(sys.argv[1]) if len(sys.argv) > 1 else 1
run = json.loads((root / "data" / "latest_run.json").read_text())
cands = sorted((a for a in run["assessed"] if a["verdict"] == "dry_spill_candidate"),
               key=lambda a: -a["duration_hours"])[:top_n]
memory = CaseMemory()
out_dir = root / "data" / "reports"
out_dir.mkdir(parents=True, exist_ok=True)
for spill in cands:
    for k in ("latesteventstart", "latesteventend"):
        if spill.get(k):
            spill[k] = datetime.fromisoformat(spill[k])
    print(f"Investigating {spill['company']} {spill['id']} ({spill['receivingwatercourse']}) ...")
    r = orchestrator.run_case(spill, memory)
    print(f"  verdict={r['final_verdict']} confidence={r['breach_confidence']:.2f} "
          f"skeptic={r['skeptic_model']} searches={r['n_sources']}")
    print(f"  strongest objection: {r['strongest_objection']}")
    path = out_dir / f"{spill['id']}.json"
    path.write_text(json.dumps(r, default=str, indent=1))
    if r["report"]:
        (out_dir / f"{spill['id']}.md").write_text(r["report"])
        print(f"  evidence pack: {out_dir / (spill['id'] + '.md')}")
