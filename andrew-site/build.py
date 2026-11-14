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
run = json.loads(run_file.read_text())  # example_run.json = the Databricks run that the agent cases came from


def rain48(a):
    mm = [a.get("max_mm_0_24h_before"), a.get("max_mm_24_48h_before")]
    return max((m for m in mm if m is not None), default=None)


sites = [{"id": a["id"], "company": a["company"], "name": a.get("receivingwatercourse") or a["id"],
          "lat": a["latitude"], "lon": a["longitude"], "verdict": a["verdict"],
          "hours": a.get("duration_hours"),  # None = monitor offline
          "rain48": rain48(a), "gauges": a.get("gauges") or []}
         for a in run["assessed"] if a.get("longitude") is not None and a.get("latitude") is not None]
cases = {}
for f in sorted([*(root / "data" / "reports").glob("*.json"), *(f for f in (root / "data").glob("example_*.json") if f.name != "example_run.json"),
                 *here.glob("demo_*.json")],  # demo_* = made-up placeholder cases, flagged "illustrative"
                key=lambda f: (not f.name.startswith("demo_"), f.stat().st_mtime)):  # real runs always beat demo_*
    loaded = json.loads(f.read_text())
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
hist = json.loads(hist_path.read_text()) if hist_path.exists() else {"runs": [], "events": {}}
if run["run_at"] not in hist["runs"]:
    hist["runs"].append(run["run_at"])
for a in run["assessed"]:
    if a.get("latesteventstart"):
        hist["events"][f'{a["id"]}|{a["latesteventstart"]}'] = {
            "id": a["id"], "company": a["company"], "name": a.get("receivingwatercourse") or a["id"],
            "start": str(a["latesteventstart"]), "hours": a.get("duration_hours"), "verdict": a["verdict"]}
hist_path.write_text(json.dumps(hist, indent=1))
history = {"runs": hist["runs"], "events": list(hist["events"].values())}
print(f"spill record: {len(history['events'])} spills over {len(history['runs'])} runs")
data = json.dumps({"run_at": run["run_at"], "sites": sites, "history": history}).replace("</", "<\\/")  # can't close the <script>

template = (here / "app.html").read_text()
assert "/*DATA*/null" in template
out = here / "build" / "index.html"
out.parent.mkdir(exist_ok=True)
out.write_text(template.replace("/*DATA*/null", data))
print("wrote", out)
