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

- **Map tab:** a flat dot map of every spill in the last 48 hours (red = dry-spill candidate, navy =
  rain-explained, grey = no gauge within 10 km; dot size = hours discharging), with numbered pins on the six
  longest dry spills. "Dry spills only" hides the rest. "2D map" keeps the map flat and north-up when a spill
  is selected (dots instead of 3D domes); the browser remembers the choice.
- **Deep dive** (the arrows button, top right of the map): the title block goes, the map fills the page, and the
  right column becomes a panel over the map with the full list of dry spills (scrollable) and the selected
  spill's case underneath. The panel can be closed and reopened; the button again or Esc returns to the overview.
- **Selecting a spill** (a dot, a pin or a list row) flies the map in and tilts it into 3D: spills stand up as
  columns (height = hours discharging, selected one gold), a dashed ring marks the 10 km rain-check area and
  the gauges inside it show their readings. "Show all of England" flies back out flat.
- **Right column:** the longest dry spills, then the selected spill's card: hours, gauges, the agents' verdict,
  a button to its evidence pack, and the full agent conversation folded underneath. For agent-checked spills
  the card also shows the investigator's severity and the top objection still open and ruled out.
- **Ask Genie:** a floating button, bottom right (see below).
- **Cases tab:** a status board (New, Ruled innocent, Needs review, Report drafted, Approved, Rejected), the
  confidence swing (how far the web evidence moved the skeptic's view) and repeat sites (overflows with more
  than one dry-spill candidate across detector runs). Click any case to open it on the map.
- **Reports tab:** the drafted evidence packs. A reviewer can edit the draft, approve it (with their name) or
  reject it (with a reason), download the approved pack as Markdown, mark it as sent, or undo. Nothing is
  emailed: a person sends the downloaded pack.
- **Ask Genie** (floating button, bottom right): plain-English follow-up questions to the Sentinels Genie agent on Databricks, which writes and
  runs the SQL. Each answer shows the text, a results table and the SQL. With a spill selected, the suggested
  questions are about that overflow and its company. Needs `serve.py` running with these set in the shell or
  in a `.env` file at the repo root (git-ignored; never commit them):

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
