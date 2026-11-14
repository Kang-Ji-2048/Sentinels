"""Export the latest detector run (and an example agent case, if present) for the showcase site.

python site/build_data.py  ->  site/data/run.json  (+ site/data/case.json)
"""
import json
from collections import Counter
from pathlib import Path

root = Path(__file__).resolve().parents[1]
# Prefer the Databricks pipeline's run (example_run.json) so map sites match the agent cases; else the local run.
run_file = next(f for f in [root / "data" / "example_run.json", root / "data" / "latest_run.json"] if f.exists())
run = json.loads(run_file.read_text())
print("run:", run_file.name)
keep = ["id", "company", "receivingwatercourse", "latitude", "longitude", "status", "monitor_offline", "latesteventstart",
        "latesteventend", "duration_hours", "verdict", "max_mm_0_24h_before", "max_mm_24_48h_before", "gauges"]
spills = [{k: a.get(k) for k in keep} for a in run["assessed"] if a.get("longitude") is not None]
out = {
    "run_at": run["run_at"], "overflows": run["overflows"], "recent_spills": run["recent_spills"],
    "verdicts": Counter(a["verdict"] for a in run["assessed"]),
    "by_company": Counter(a["company"] for a in run["assessed"] if a["verdict"] == "dry_spill_candidate"),
    "spills": spills,
}
# Add gauge coordinates so the map can draw each spill's link to its rain gauges.
try:
    import sys
    sys.path.insert(0, str(root))
    from sentinels import feeds
    where = {st["station"]: st for st in feeds.fetch_rain_stations()}
    for sp in spills:
        for g in sp.get("gauges") or []:
            if g["station"] in where:
                g["lat"], g["lon"] = where[g["station"]]["lat"], where[g["station"]]["lon"]
except Exception as e:  # noqa: BLE001  (map still works without the links)
    print("gauge locations unavailable:", e)
dest = root / "site" / "data"
dest.mkdir(parents=True, exist_ok=True)
(dest / "run.json").write_text(json.dumps(out, default=str, separators=(",", ":")))
print("wrote", dest / "run.json", len(spills), "spills")
# The followed case: the most confident real agent run (example_cases.json is a list, example_case.json one case).
cases = []
for f in sorted((root / "data").glob("example_*.json")):
    if f.name == "example_run.json":
        continue
    loaded = json.loads(f.read_text())
    cases += loaded if isinstance(loaded, list) else [loaded]
on_map = {s["id"] for s in spills}
cases = [c for c in cases if c.get("site_id") in on_map] or cases
if cases:
    best = max(cases, key=lambda c: (c.get("final_verdict") == "likely_breach", c.get("breach_confidence") or 0))
    (dest / "case.json").write_text(json.dumps(best, default=str))
    print("case:", best["site_id"], best.get("final_verdict"), best.get("breach_confidence"), f"(of {len(cases)})")
