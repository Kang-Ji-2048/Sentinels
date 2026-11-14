# Databricks notebook source
# Shared setup, pulled into other notebooks with %run ./_common
import os, sys
repo_root = os.path.dirname(os.getcwd())  # notebooks/ lives one level below the repo root
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)
# Drop cached sentinels modules so a re-run after a Git pull always uses the latest code
for _m in [m for m in sys.modules if m == "sentinels" or m.startswith("sentinels.")]:
    del sys.modules[_m]

CATALOG, SCHEMA = "workspace", "sentinels"
T = lambda name: f"{CATALOG}.{SCHEMA}.{name}"

import pandas as pd
from datetime import timezone

def py_records(pdf):
    """Spark->pandas rows as plain Python, with timestamps made tz-aware UTC (toPandas returns naive)."""
    out = []
    for r in pdf.to_dict("records"):
        row = {}
        for k, v in r.items():
            if isinstance(v, pd.Timestamp):
                v = v.to_pydatetime()
                v = v.replace(tzinfo=timezone.utc) if v.tzinfo is None else v
            elif not isinstance(v, (list, dict)) and pd.isna(v):
                v = None
            row[k] = v
        out.append(row)
    return out
