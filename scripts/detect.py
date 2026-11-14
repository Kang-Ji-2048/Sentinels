"""Run the live dry-spill detector and save a snapshot: python -m scripts.detect"""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
try:  # use the OS certificate store (needed behind antivirus HTTPS scanning, e.g. Avast on Windows)
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass
from sentinels import detect  # noqa: E402

out = Path(__file__).resolve().parents[1] / "data" / "latest_run.json"
result = detect.run()
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(result, default=str, indent=1))
print(f"{result['overflows']} overflows, {result['recent_spills']} spills started in the last 48h")
print(Counter(a["verdict"] for a in result["assessed"]))
cands = sorted((a for a in result["assessed"] if a["verdict"] == "dry_spill_candidate"),
               key=lambda a: -(a["duration_hours"] or -1))
for a in cands[:10]:
    print(f"{a['duration_hours'] if a['duration_hours'] is not None else '?':>6}h  {a['company']:<20} {a['id']:<12} {a['receivingwatercourse']}")
if result["errors"]:
    print("errors:", result["errors"])
print("saved", out)
