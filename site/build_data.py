"""Export the latest detector run (and an example agent case, if present) for the showcase site.

python site/build_data.py  ->  site/data/run.json  (+ site/data/case.json)
"""
import json
import shutil
from collections import Counter
from pathlib import Path

root = Path(__file__).resolve().parents[1]
run = json.loads((root / "data" / "latest_run.json").read_text())
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
case = root / "data" / "example_case.json"
if case.exists():
    shutil.copy(case, dest / "case.json")
    print("copied", case)
