"""Live data sources: water company storm overflow feeds and EA rainfall gauges."""
from __future__ import annotations

import math
from datetime import datetime, timezone

import requests

# One public ArcGIS FeatureServer per company (National Storm Overflows Hub / Stream Water Data).
# Found via arcgis.com item search for "Storm Overflow Activity". England only: EA rainfall
# does not cover Scotland, so Scottish Water is left out.
OVERFLOW_FEEDS = {
    "Anglian Water": "https://services3.arcgis.com/VCOY1atHWVcDlvlJ/arcgis/rest/services/stream_service_outfall_locations_view/FeatureServer/0",
    "Northumbrian Water": "https://services-eu1.arcgis.com/MSNNjkZ51iVh8yBj/arcgis/rest/services/Northumbrian_Water_Storm_Overflow_Activity_2_view/FeatureServer/0",
    "Severn Trent Water": "https://services1.arcgis.com/NO7lTIlnxRMMG9Gw/arcgis/rest/services/Severn_Trent_Water_Storm_Overflow_Activity/FeatureServer/0",
    "South West Water": "https://services-eu1.arcgis.com/OMdMOtfhATJPcHe3/arcgis/rest/services/NEH_outlets_PROD/FeatureServer/0",
    "Thames Water": "https://services2.arcgis.com/g6o32ZDQ33GpCIu3/arcgis/rest/services/Thames_Water_Storm_Overflow_Activity_(Production)_view/FeatureServer/0",
    "United Utilities": "https://services5.arcgis.com/5eoLvR0f8HKb7HWP/arcgis/rest/services/United_Utilities_Storm_Overflow_Activity/FeatureServer/0",
    "Wessex Water": "https://services.arcgis.com/3SZ6e0uCvPROr4mS/arcgis/rest/services/Wessex_Water_Storm_Overflow_Activity/FeatureServer/0",
    "Yorkshire Water": "https://services-eu1.arcgis.com/1WqkK5cDKUbF0CkH/arcgis/rest/services/Yorkshire_Water_Storm_Overflow_Activity/FeatureServer/0",
}

EA_BASE = "https://environment.data.gov.uk/flood-monitoring"
TIMEOUT = 30

_FIELDS = ["id", "company", "status", "statusstart", "latesteventstart", "latesteventend",
           "latitude", "longitude", "receivingwatercourse", "lastupdated"]
_DATE_FIELDS = {"statusstart", "latesteventstart", "latesteventend", "lastupdated"}


def _ms_to_dt(ms):
    return None if ms is None else datetime.fromtimestamp(ms / 1000, tz=timezone.utc)


def fetch_company(company: str, url: str, where: str = "1=1") -> list[dict]:
    """All overflow records for one company, normalised to lower-case field names."""
    rows, offset = [], 0
    while True:
        r = requests.get(f"{url}/query", timeout=TIMEOUT, params={
            "where": where, "outFields": "*", "returnGeometry": "false", "f": "json",
            "resultOffset": offset, "resultRecordCount": 1000, "orderByFields": "Id"})
        r.raise_for_status()
        data = r.json()
        if "error" in data:
            raise RuntimeError(f"{company}: {data['error']}")
        feats = data.get("features", [])
        for f in feats:
            a = {k.lower(): v for k, v in f["attributes"].items()}  # South West uses camelCase
            row = {k: a.get(k) for k in _FIELDS}
            for k in _DATE_FIELDS:
                row[k] = _ms_to_dt(row[k])
            row["company"] = company
            rows.append(row)
        if not data.get("exceededTransferLimit") or not feats:
            return rows
        offset += len(feats)


def fetch_all_overflows(where: str = "1=1") -> tuple[list[dict], dict[str, str]]:
    """Records from every company. Returns (rows, errors) so one broken feed doesn't stop the run."""
    rows, errors = [], {}
    for company, url in OVERFLOW_FEEDS.items():
        try:
            rows += fetch_company(company, url, where)
        except Exception as e:  # noqa: BLE001 - report and carry on
            errors[company] = str(e)
    return rows, errors


def fetch_rain_stations() -> list[dict]:
    """Every EA rainfall gauge in England with its location (~1000 stations, one call)."""
    r = requests.get(f"{EA_BASE}/id/stations", params={"parameter": "rainfall", "_limit": 10000},
                     timeout=TIMEOUT)
    r.raise_for_status()
    return [{"station": s["stationReference"], "lat": s["lat"], "lon": s["long"]}
            for s in r.json()["items"] if isinstance(s.get("lat"), (int, float))]


def fetch_rain_readings(station: str, since: datetime) -> list[dict]:
    """15-minute rainfall readings (mm) for one gauge since a time."""
    r = requests.get(f"{EA_BASE}/id/stations/{station}/readings", timeout=TIMEOUT, params={
        "parameter": "rainfall", "since": since.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "_sorted": "", "_limit": 10000})
    r.raise_for_status()
    return [{"station": station,
             "time": datetime.fromisoformat(i["dateTime"].replace("Z", "+00:00")),
             "mm": float(i["value"])}
            for i in r.json()["items"] if isinstance(i.get("value"), (int, float))]


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    p = math.pi / 180
    a = (math.sin((lat2 - lat1) * p / 2) ** 2
         + math.cos(lat1 * p) * math.cos(lat2 * p) * math.sin((lon2 - lon1) * p / 2) ** 2)
    return 12742 * math.asin(math.sqrt(a))
