# Databricks notebook source
# MAGIC %md
# MAGIC # Sentinels 02: detect (silver + gold)
# MAGIC * **silver_spill_events**: one row per discharge event (site + start time), merged across snapshots.
# MAGIC * **silver_rain_readings**: 15-minute readings for the gauges near recent spills.
# MAGIC * **gold_dry_spill_candidates**: events where every gauge within 10 km saw < 0.25 mm in each of the two 24 h windows before the spill.

# COMMAND ----------

# MAGIC %pip install -q pydeck

# COMMAND ----------

# MAGIC %run ./_common

# COMMAND ----------

import json
from datetime import datetime, timedelta, timezone
import pandas as pd
from sentinels import detect, feeds

cfg = detect.DetectConfig()
now = datetime.now(timezone.utc)

latest = spark.sql(f"""SELECT * FROM {T('bronze_overflow_snapshots')}
  WHERE ingested_at = (SELECT max(ingested_at) FROM {T('bronze_overflow_snapshots')})""").toPandas()
rows = py_records(latest)
spills = detect.recent_spills(rows, cfg, now)
print(f"{len(spills)} spills started in the last {cfg.lookback_hours}h")

# COMMAND ----------

# Silver: events, merged so re-runs update an event's end time instead of duplicating it
ev = pd.DataFrame([{k: s[k] for k in ["id", "company", "latesteventstart", "latesteventend", "status",
                                      "latitude", "longitude", "receivingwatercourse", "lastupdated"]} for s in spills])
spark.createDataFrame(ev).createOrReplaceTempView("new_events")
spark.sql(f"""CREATE TABLE IF NOT EXISTS {T('silver_spill_events')} AS SELECT * FROM new_events WHERE 1=0""")
spark.sql(f"""MERGE INTO {T('silver_spill_events')} t USING new_events s
  ON t.id = s.id AND t.latesteventstart = s.latesteventstart
  WHEN MATCHED THEN UPDATE SET *
  WHEN NOT MATCHED THEN INSERT *""")

# COMMAND ----------

# Rainfall near each spill
stations = py_records(spark.table(T("bronze_rain_stations")).toPandas())
gauges_for = {s["id"]: detect.nearest_gauges(s, stations, cfg) for s in spills}
needed = sorted({g["station"] for gs in gauges_for.values() for g in gs})
since = now - timedelta(hours=cfg.lookback_hours + 48)
gauge_errors = {}
readings = detect.fetch_readings(needed, since, gauge_errors)  # parallel: ~1 min instead of ~10
if gauge_errors:
    print("gauge errors:", gauge_errors)
flat = [r for rs in readings.values() for r in rs]
if flat:
    spark.createDataFrame(pd.DataFrame(flat)).write.mode("overwrite").saveAsTable(T("silver_rain_readings"))
print(f"{len(needed)} gauges, {len(flat)} readings")

# COMMAND ----------

# Gold: verdict per spill
assessed = [detect.assess(s, gauges_for[s["id"]], readings, cfg) for s in spills]
gold = pd.DataFrame([{**{k: a.get(k) for k in ["id", "company", "receivingwatercourse", "latitude", "longitude",
                                               "latesteventstart", "latesteventend", "duration_hours", "monitor_offline", "verdict",
                                               "max_mm_0_24h_before", "max_mm_24_48h_before", "max_mm_during"]},
                      "gauges_json": json.dumps(a["gauges"]), "assessed_at": now} for a in assessed])
spark.createDataFrame(gold).write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(T("gold_spill_assessments"))
display(spark.sql(f"""SELECT verdict, count(*) n FROM {T('gold_spill_assessments')} GROUP BY verdict"""))
display(spark.sql(f"""SELECT company, id, receivingwatercourse, latesteventstart, duration_hours, max_mm_0_24h_before, max_mm_24_48h_before
  FROM {T('gold_spill_assessments')} WHERE verdict = 'dry_spill_candidate' ORDER BY duration_hours DESC"""))

# COMMAND ----------

# 3D map: column height = hours discharging, red = dry-spill candidate, blue = rain nearby, grey = no gauge
from sentinels.viz import spill_map
displayHTML(spill_map(assessed).to_html(as_string=True))
