# Andrew's site: Sentinels app page

A self-contained copy of the app page Andrew built: the 3D spill map with the Figma "Sentinels - App" layout.
Nothing outside this folder is changed.

## Run it

```
pip install -r requirements.txt
python scripts/detect.py                          # live data -> data/latest_run.json
python andrew-site/build.py                       # -> andrew-site/build/index.html
python -m http.server 8000 -d andrew-site/build   # open http://localhost:8000
```

## What's on the page

- **Map:** one semi-transparent column per spill in the last 48 hours. Height is hours discharging; red is a
  dry-spill candidate, faint navy is rain-explained, grey has no gauge within 10 km. "Dry spills only" hides
  the rest.
- **Selecting a spill** (click a column or a row) zooms in, draws the 10 km rain-check area as a gold ring, and
  plots the rain gauges inside it with their 48-hour readings (white = dry, navy = 0.25 mm or more in a day).
  Click it again, or "Show all of England", to zoom back out.
- **Side panel:** the longest dry spills, then the selected site's case: verdict, gauge readings and the agents'
  conversation when one exists.

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
