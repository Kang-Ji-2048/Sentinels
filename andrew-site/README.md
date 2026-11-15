# Andrew's site: Sentinels app page

A self-contained copy of the app page Andrew built: the 3D spill map with the Figma "Sentinels - App" layout.
Nothing outside this folder is changed.

## Run it

The page is a React app (Vite + Tailwind + shadcn/ui) in `andrew-site/web/`. `app.html`, `build/` and
`public/index.html` are the old single-file page, kept only for reference.

```
pip install -r requirements.txt
python scripts/detect.py                          # live data -> data/latest_run.json
python andrew-site/build.py                       # -> andrew-site/web/public/data/run.json
cd andrew-site/web && npm install && npm run build && cd ../..   # -> andrew-site/web/dist (only after code changes)
python andrew-site/serve.py 8765                  # open http://localhost:8765 (8000 if that port is free)
```

While editing the page: run `python andrew-site/serve.py` (port 8000) and `npm run dev` in `andrew-site/web`; the dev
server proxies `/api` to port 8000. Theme tokens (Inter, navy / carmine / amber palette) are in `web/src/index.css`.

## What's on the page

- **Map:** one semi-transparent column per spill in the last 48 hours. Height is hours discharging; red is a
  dry-spill candidate, faint navy is rain-explained, grey has no gauge within 10 km. "Dry spills only" hides
  the rest.
- **Selecting a spill** (click a column or a row) zooms in, draws the 10 km rain-check area as a gold ring, and
  plots the rain gauges inside it with their 48-hour readings (white = dry, navy = 0.25 mm or more in a day).
  Click it again, or "Show all of England", to zoom back out.
- **Side panel:** the longest dry spills, then the selected site's case: verdict, gauge readings and the agents'
  conversation when one exists.

- **Cases tab:** a status board (New, Ruled innocent, Needs review, Report drafted, Approved, Rejected), the
  confidence swing (how far the web evidence moved the skeptic's view) and repeat sites (overflows with more
  than one dry-spill candidate across detector runs). Click any case to open it on the map.
- **Reports tab:** the drafted evidence packs. A reviewer can edit the draft, approve it (with their name) or
  reject it (with a reason), download the approved pack as Markdown, mark it as sent, or undo. Nothing is
  emailed: a person sends the downloaded pack.

## Files it writes (all git-ignored)

- `andrew-site/build/index.html`: the page.
- `andrew-site/history.json`: every spill seen by each build, for repeat sites. Rebuild after each detector run.
- `andrew-site/decisions.json`: approvals, rejections and sends, written by `serve.py`. Opening the page with
  any other static server works, but read-only.
- A rejection of a real (non-example) case is also appended to `data/case_memory.jsonl`, so the agents see the
  reviewer's reason next time they look at that site.

## Things to know

- **`demo_case.json` is made up.** It is an example agent conversation for Carnon River (SBB00211) so the
  layout can be seen before real agent runs exist. The page shows it under a red "Example conversation"
  banner and every line is marked as an example. Delete the file to remove it.
- **Gauge dots need gauge coordinates** in the detector output. The shared `sentinels/detect.py` doesn't save
  them yet; Andrew's local copy adds `"lat"` and `"lon"` to each gauge in `assess()`. Without that, the
  page works but shows no gauge dots.
- **Unknown durations** (monitor offline) show as "?" hours and sort last.
- `PRODUCT.md` and `DESIGN.md` are the product and design notes the page was built from.
- Needs internet for the basemap tiles (CARTO), fonts and libraries (MapLibre, deck.gl).
