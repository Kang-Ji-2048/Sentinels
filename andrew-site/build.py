"""Build Andrew's Sentinels app page (3D map + side panel) from the latest detector run.

    python andrew-site/build.py                       -> andrew-site/build/index.html
    python -m http.server 8000 -d andrew-site/build   -> http://localhost:8000

Reads data/latest_run.json (from scripts/detect.py). Agent conversations come from data/reports/*.json,
data/example_*.json (pasted from notebooks/03_agents.py) and andrew-site/demo_*.json (made-up examples,
shown with an "Example conversation" banner). Latest file wins per site.
"""
import json
from pathlib import Path

here = Path(__file__).resolve().parent
root = here.parent
run_file = next(f for f in [root / "data" / "example_run.json", root / "data" / "latest_run.json"] if f.exists())
run = json.loads(run_file.read_text(encoding="utf-8"))  # example_run.json = the Databricks run that the agent cases came from


def rain48(a):
    mm = [a.get("max_mm_0_24h_before"), a.get("max_mm_24_48h_before")]
    return max((m for m in mm if m is not None), default=None)


sites = [{"id": a["id"], "company": a["company"], "name": a.get("receivingwatercourse") or a["id"],
          "lat": a["latitude"], "lon": a["longitude"], "verdict": a["verdict"],
          "hours": a.get("duration_hours"),  # None = monitor offline
          "rain48": rain48(a), "gauges": a.get("gauges") or [],
          # feed status: 1 discharging now, 0 stopped, -1 monitor offline (older runs have no Status, so derive it)
          "status": a.get("status") if a.get("status") is not None else
                    -1 if a.get("monitor_offline") else 1 if not a.get("latesteventend") else 0}
         for a in run["assessed"] if a.get("longitude") is not None and a.get("latitude") is not None]
# Gauge positions: runs made before detect.py saved them have none, so fill them in by station id from a newer
# local run (data/latest_run.json) when there is one. Without positions the page still works, minus the gauge dots.
newer = root / "data" / "latest_run.json"
if newer.exists() and newer != run_file:
    where = {g["station"]: (g["lat"], g["lon"]) for a in json.loads(newer.read_text(encoding="utf-8"))["assessed"]
             for g in a.get("gauges") or [] if g.get("lat") is not None}
    for s in sites:
        s["gauges"] = [g if g.get("lat") is not None or g["station"] not in where
                       else {**g, "lat": where[g["station"]][0], "lon": where[g["station"]][1]} for g in s["gauges"]]
all_g = [g for s in sites for g in s["gauges"]]
print(f"gauges with a map position: {sum(g.get('lat') is not None for g in all_g)} of {len(all_g)}")
cases = {}
for f in sorted([*(root / "data" / "reports").glob("*.json"), *(f for f in (root / "data").glob("example_*.json") if f.name != "example_run.json"),
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
# Spill record across runs, for the Cases tab's repeat sites. The overflow feeds only give each site's latest
# event, so every build adds this run's spills to andrew-site/history.json (one entry per site + event start).
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
data = json.dumps({"run_at": run["run_at"], "sites": sites, "history": history}).replace("</", "<\\/")  # can't close the <script>

template = (here / "app.html").read_text(encoding="utf-8")
assert "/*DATA*/null" in template
out = here / "build" / "index.html"
out.parent.mkdir(exist_ok=True)
# The Map tab is the dashboard layout: flat dot map that tilts into 3D when a spill is selected.
# (The template still holds the older full-bleed 3D/2D map behind MAP2D=false / DASH=false; it is no longer built.)
out.write_text(template.replace("/*DATA*/null", data).replace("/*MAP2D*/false", "true").replace("/*DASH*/false", "true"), encoding="utf-8")
print("wrote", out)
for old_page in ("2d.html", "dashboard.html"):  # pages from before the merge
    out.with_name(old_page).unlink(missing_ok=True)
