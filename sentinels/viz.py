"""3D map of a detector run: column height = hours discharging, colour = verdict."""
from __future__ import annotations

import pydeck as pdk

COLOURS = {"dry_spill_candidate": [220, 50, 47, 230],   # red: possible breach
           "rain_explained": [38, 139, 210, 160],       # blue: rain nearby
           "no_gauge": [147, 161, 161, 140]}            # grey: can't tell


def spill_map(assessed: list[dict]) -> pdk.Deck:
    pts = [{"lon": a["longitude"], "lat": a["latitude"], "hours": max(a.get("duration_hours") or 0, 0.3),
            "colour": COLOURS.get(a["verdict"], [200, 200, 200, 150]),
            "label": f"{a['company']} {a['id']}<br/>{a.get('receivingwatercourse')}<br/>"
                     f"{a['verdict'].replace('_', ' ')}: {a.get('duration_hours')} h discharging<br/>"
                     f"rain in 24 h before: {a.get('max_mm_0_24h_before', 'n/a')} mm"}
           for a in assessed if a.get("longitude") is not None]
    layer = pdk.Layer("ColumnLayer", pts, get_position=["lon", "lat"], get_elevation="hours",
                      elevation_scale=1500, radius=2500, get_fill_color="colour", pickable=True,
                      auto_highlight=True, extruded=True)
    view = pdk.ViewState(latitude=53.0, longitude=-1.8, zoom=5.6, pitch=50, bearing=-15)
    return pdk.Deck(layers=[layer], initial_view_state=view, map_style="dark",
                    tooltip={"html": "{label}"})
