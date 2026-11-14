"""Render the latest detector run as a 3D map: python scripts/map.py -> docs/map.html"""
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
from sentinels.viz import spill_map  # noqa: E402

run = json.loads((root / "data" / "latest_run.json").read_text())
out = root / "docs" / "map.html"
out.parent.mkdir(exist_ok=True)
spill_map(run["assessed"]).to_html(str(out), open_browser=False)
print("wrote", out)
