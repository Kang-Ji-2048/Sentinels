"""Dry-spill detection: join recent overflow discharges to nearby EA rain gauges.

Rule (EA-style dry-day test, all thresholds configurable):
a spill is a dry-spill candidate if EVERY rain gauge within `radius_km` recorded less than
`dry_mm` in the 24h before the spill started AND less than `dry_mm` in the 24h before that.
Using the wettest nearby gauge keeps the rule conservative: one wet gauge clears the spill.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from . import feeds


@dataclass
class DetectConfig:
    lookback_hours: int = 48   # consider spills that started within this window
    radius_km: float = 10.0    # gauges counted as "nearby"
    dry_mm: float = 0.25       # less than this in a 24h window counts as a dry day
    max_gauges: int = 3        # nearest N gauges inside the radius


def recent_spills(rows: list[dict], cfg: DetectConfig, now: datetime | None = None) -> list[dict]:
    """Overflows whose latest event started inside the lookback window."""
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=cfg.lookback_hours)
    return [r for r in rows
            if r["latesteventstart"] and r["latesteventstart"] >= cutoff
            and r["latitude"] and r["longitude"]]


def nearest_gauges(spill: dict, stations: list[dict], cfg: DetectConfig) -> list[dict]:
    with_d = [dict(s, km=feeds.haversine_km(spill["latitude"], spill["longitude"], s["lat"], s["lon"]))
              for s in stations]
    return sorted([s for s in with_d if s["km"] <= cfg.radius_km], key=lambda s: s["km"])[:cfg.max_gauges]


def _sum(readings, start, end):
    """Total mm in [start, end), or None if the gauge reported under half its 15-min readings."""
    vals = [r["mm"] for r in readings if start <= r["time"] < end]
    expected = (end - start).total_seconds() / 900
    if expected > 0 and len(vals) < 0.5 * expected:
        return None
    return round(sum(vals), 2)


def assess(spill: dict, gauges: list[dict], readings_by_station: dict[str, list[dict]],
           cfg: DetectConfig) -> dict:
    """Rainfall context and a verdict for one spill."""
    t0 = spill["latesteventstart"]
    end = spill["latesteventend"] or datetime.now(timezone.utc)
    per_gauge = []
    for g in gauges:
        rd = readings_by_station.get(g["station"], [])
        if not rd:
            continue
        before_24 = _sum(rd, t0 - timedelta(hours=24), t0)
        before_48 = _sum(rd, t0 - timedelta(hours=48), t0 - timedelta(hours=24))
        if before_24 is None or before_48 is None:
            continue  # gauge offline for the window: missing data is not evidence of a dry day
        per_gauge.append({
            "station": g["station"], "km": round(g["km"], 1),
            "mm_0_24h_before": before_24, "mm_24_48h_before": before_48,
            "mm_during": _sum(rd, t0, end) or 0.0,
        })
    out = dict(spill)
    out["duration_hours"] = round((end - t0).total_seconds() / 3600, 1)
    out["gauges"] = per_gauge
    if not per_gauge:
        out["verdict"] = "no_gauge"
        return out
    wettest_24 = max(g["mm_0_24h_before"] for g in per_gauge)
    wettest_48 = max(g["mm_24_48h_before"] for g in per_gauge)
    out["max_mm_0_24h_before"] = wettest_24
    out["max_mm_24_48h_before"] = wettest_48
    out["max_mm_during"] = max(g["mm_during"] for g in per_gauge)
    dry = wettest_24 < cfg.dry_mm and wettest_48 < cfg.dry_mm
    out["verdict"] = "dry_spill_candidate" if dry else "rain_explained"
    return out


def run(cfg: DetectConfig | None = None, now: datetime | None = None) -> dict:
    """End-to-end live run: fetch feeds and rainfall, return every recent spill with a verdict."""
    cfg = cfg or DetectConfig()
    now = now or datetime.now(timezone.utc)
    rows, errors = feeds.fetch_all_overflows()
    spills = recent_spills(rows, cfg, now)
    stations = feeds.fetch_rain_stations()

    gauges_for = {s["id"]: nearest_gauges(s, stations, cfg) for s in spills}
    needed = {g["station"] for gs in gauges_for.values() for g in gs}
    since = now - timedelta(hours=cfg.lookback_hours + 48)
    readings = {}

    def _get(st):
        try:
            return st, feeds.fetch_rain_readings(st, since), None
        except Exception as e:  # noqa: BLE001
            return st, [], str(e)

    with ThreadPoolExecutor(max_workers=8) as pool:
        for st, rd, err in pool.map(_get, sorted(needed)):
            readings[st] = rd
            if err:
                errors[f"gauge {st}"] = err

    assessed = [assess(s, gauges_for[s["id"]], readings, cfg) for s in spills]
    return {"run_at": now, "overflows": len(rows), "recent_spills": len(spills),
            "assessed": assessed, "errors": errors}
