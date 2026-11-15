"""Build the data file for Andrew's Sentinels dashboard from the latest detector run.

    python andrew-site/build.py                   -> andrew-site/web/public/data/run.json
    (cd andrew-site/web && npm run build)         -> andrew-site/web/dist  (the page)
    python andrew-site/serve.py                   -> http://localhost:8000

Reads data/latest_run.json (from scripts/detect.py). Agent conversations come from data/reports/*.json,
data/example_*.json (pasted from notebooks/03_agents.py) and andrew-site/demo_*.json (made-up examples,
shown with an "Example conversation" banner). Latest file wins per site.

The page reads data/run.json at load time, so rerunning this script is enough to refresh the data; the
React build only needs redoing when the page's code changes. serve.py serves the newest copy of run.json.
"""
import json
import sys
from pathlib import Path

here = Path(__file__).resolve().parent
root = here.parent
run = json.loads((root / "data" / "latest_run.json").read_text(encoding="utf-8"))


def rain48(a):
    mm = [a.get("max_mm_0_24h_before"), a.get("max_mm_24_48h_before")]
    return max((m for m in mm if m is not None), default=None)


def gauge_coords() -> dict:
    """Station -> (lat, lon) for runs made before detect.py saved gauge positions. One public EA call, cached."""
    cache = here / "gauge_coords.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    try:
        sys.path.insert(0, str(root))
        from sentinels import feeds
        coords = {s["station"]: [s["lat"], s["lon"]] for s in feeds.fetch_rain_stations()}
    except Exception as e:  # offline: the page still works, just without gauge dots
        print(f"no gauge positions ({e}); gauge dots won't show")
        return {}
    cache.write_text(json.dumps(coords), encoding="utf-8")
    return coords


assessed = [a for a in run["assessed"] if a.get("longitude") is not None and a.get("latitude") is not None]
if any(g.get("lat") is None for a in assessed for g in a.get("gauges") or []):
    coords = gauge_coords()
    for a in assessed:
        for g in a.get("gauges") or []:
            if g.get("lat") is None and g["station"] in coords:
                g["lat"], g["lon"] = coords[g["station"]]

sites = [{"id": a["id"], "company": a["company"], "name": a.get("receivingwatercourse") or a["id"],
          "lat": a["latitude"], "lon": a["longitude"], "verdict": a["verdict"],
          "hours": a.get("duration_hours"),  # None = monitor offline
          "ongoing": a.get("status") == 1, "offline": bool(a.get("monitor_offline")),
          "start": str(a["latesteventstart"]) if a.get("latesteventstart") else None,
          "end": str(a["latesteventend"]) if a.get("latesteventend") else None,
          "rain48": rain48(a), "rainDuring": a.get("max_mm_during"), "gauges": a.get("gauges") or []}
         for a in assessed]

cases = {}
for f in sorted([*(root / "data" / "reports").glob("*.json"), *(root / "data").glob("example_*.json"),
                 *here.glob("demo_*.json")],  # demo_* = made-up placeholder cases, flagged "illustrative"
                key=lambda f: (not f.name.startswith("demo_"), f.stat().st_mtime)):  # real runs always beat demo_*
    loaded = json.loads(f.read_text(encoding="utf-8"))
    for c in loaded if isinstance(loaded, list) else [loaded]:
        cases[c["site_id"]] = c
on_map = {s["id"] for s in sites}
for s in sites:
    s["case"] = cases.get(s["id"])
print(f"agent cases on the map: {sorted(cases.keys() & on_map) or 'none'}")
if cases.keys() - on_map:
    print(f"skipped (site not in data/latest_run.json; rerun scripts/detect.py?): {sorted(cases.keys() - on_map)}")

# Spill record across runs, for repeat sites. The overflow feeds only give each site's latest event, so every
# build adds this run's spills to andrew-site/history.json (one entry per site + event start).
hist_path = here / "history.json"
hist = json.loads(hist_path.read_text(encoding="utf-8")) if hist_path.exists() else {"runs": [], "events": {}}
if run["run_at"] not in hist["runs"]:
    hist["runs"].append(run["run_at"])
for a in run["assessed"]:
    if a.get("latesteventstart"):
        hist["events"][f'{a["id"]}|{a["latesteventstart"]}'] = {
            "id": a["id"], "company": a["company"], "name": a.get("receivingwatercourse") or a["id"],
            "start": str(a["latesteventstart"]), "hours": a.get("duration_hours"), "verdict": a["verdict"]}
hist_path.write_text(json.dumps(hist, indent=1), encoding="utf-8")
history = {"runs": hist["runs"], "events": list(hist["events"].values())}
print(f"spill record: {len(history['events'])} spills over {len(history['runs'])} runs")

out = here / "web" / "public" / "data" / "run.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps({"run_at": run["run_at"], "overflows": run.get("overflows"),
                           "recent_spills": run.get("recent_spills", len(run["assessed"])),
                           "sites": sites, "history": history}), encoding="utf-8")
print("wrote", out)
