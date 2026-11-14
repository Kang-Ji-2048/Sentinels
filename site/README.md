# Showcase site

One static page for judges: the problem, a 3D scrollytelling map of the latest live run, the pipeline and agent team, one case end to end, and honest limits.

```
python scripts/detect.py      # optional: fresh live run -> data/latest_run.json
python scripts/site_data.py   # -> site/data/run.json (+ site/data/case.json if data/example_case.json exists)
python -m http.server 8000 --directory site
```

Open http://localhost:8000. Design options: `?v=a` (dark preprint), `?v=b` (light preprint), `?v=c` (map first).
The agent panels in the case study stay empty until a real traced run is saved as `data/example_case.json`.
