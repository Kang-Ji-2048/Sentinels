# Andrew's site: Sentinels app page

A self-contained copy of the app page Andrew built: the 3D spill map with the Figma "Sentinels - App" layout.
Nothing outside this folder is changed.

## Run it

```
pip install -r requirements.txt
python scripts/detect.py                          # live data -> data/latest_run.json
python andrew-site/build.py                       # -> andrew-site/build/index.html
python andrew-site/serve.py                       # open http://localhost:8000
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

- **Cases tab:** a status board (New, Ruled innocent, Needs review, Report drafted, Approved, Rejected), the
  confidence swing (how far the web evidence moved the skeptic's view) and repeat sites (overflows with more
  than one dry-spill candidate across detector runs). Click any case to open it on the map.
- **Reports tab:** the drafted evidence packs. A reviewer can edit the draft, approve it (with their name) or
  reject it (with a reason), download the approved pack as Markdown, mark it as sent, or undo. Nothing is
  emailed: a person sends the downloaded pack.
- **Ask Genie box** (bottom right of the map, click to open): plain-English follow-up questions to the Sentinels Genie agent on Databricks, which writes and
  runs the SQL. Each answer shows the text, a results table and the SQL. Needs `serve.py` running with these
  set in the shell (never commit them):

  ```
  export DATABRICKS_HOST=https://dbc-xxxx.cloud.databricks.com
  export DATABRICKS_TOKEN=...        # User settings > Developer > Access tokens
  export GENIE_SPACE_ID=...          # the Genie agent's About tab
  python andrew-site/serve.py
  ```

  Without them, or on the hosted static copy, the box says it is off.

## Files it writes (all git-ignored)

- `andrew-site/build/index.html`: the page.
- `andrew-site/history.json`: every spill seen by each build, for repeat sites. Rebuild after each detector run.
- `andrew-site/decisions.json`: approvals, rejections and sends, written by `serve.py`. Opening the page with
  any other static server works, but read-only.
- A rejection of a real (non-example) case is also appended to `data/case_memory.jsonl`, so the agents see the
  reviewer's reason next time they look at that site.

## Things to know

- **Agent conversations are real runs** (`data/example_case.json`, exported from `notebooks/03_agents.py`).
  The made-up placeholder has been removed. `build.py` still accepts `andrew-site/demo_*.json` files flagged
  `"illustrative": true`, shown under a red "Example conversation" banner, but a real run always wins.
- **Gauge dots need gauge coordinates** in the detector output. The shared `sentinels/detect.py` doesn't save
  them yet; Andrew's local copy adds `"lat"` and `"lon"` to each gauge in `assess()`. Without that, the
  page works but shows no gauge dots.
- **Unknown durations** (monitor offline) show as "?" hours and sort last.
- `PRODUCT.md` and `DESIGN.md` are the product and design notes the page was built from.
- Needs internet for the basemap tiles (CARTO), fonts and libraries (MapLibre, deck.gl).
