# Showcase site

One static page for judges: the problem, a 3D scrollytelling map of the latest live run, the pipeline and agent team, one case end to end, and honest limits.

```
python scripts/detect.py      # optional: fresh live run -> data/latest_run.json
python site/build_data.py    # -> site/data/run.json (+ site/data/case.json if data/example_case.json exists)
python -m http.server 8000 --directory site
```

Open http://localhost:8000.
The agent panels in the case study stay empty until a real traced run is saved as `data/example_case.json`.

## Demo video

The demo video is recorded from the separate demo app (`andrew-site/`). Save it as `site/media/demo.mp4`
(H.264, ideally under 50 MB so it stays light in Git) and, optionally, a still as `site/media/demo-poster.jpg`.
The page shows a placeholder until the file exists.
