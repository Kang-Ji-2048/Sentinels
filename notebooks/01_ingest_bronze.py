# Databricks notebook source
# MAGIC %md
# MAGIC # Sentinels 01: ingest (bronze)
# MAGIC Snapshots every English storm overflow from 8 water-company ArcGIS feeds, plus every EA rain gauge.
# MAGIC Schedule this as a Job every 15 minutes: each run appends a snapshot, so bronze becomes a history
# MAGIC of overflow status that the feeds themselves don't keep.

# COMMAND ----------

# MAGIC %run ./_common

# COMMAND ----------

from datetime import datetime, timezone
import pandas as pd
from sentinels import feeds

ingested_at = datetime.now(timezone.utc)
rows, errors = feeds.fetch_all_overflows()
print(f"{len(rows)} overflows, feed errors: {errors}")

snap = pd.DataFrame(rows)
snap["ingested_at"] = ingested_at
spark.createDataFrame(snap).write.mode("append").option("mergeSchema", "true").saveAsTable(T("bronze_overflow_snapshots"))

stations = pd.DataFrame(feeds.fetch_rain_stations())
spark.createDataFrame(stations).write.mode("overwrite").saveAsTable(T("bronze_rain_stations"))
print(f"{len(stations)} rain gauges")

# COMMAND ----------

display(spark.sql(f"""
  SELECT company, count(*) AS overflows, sum(CASE WHEN status = 1 THEN 1 ELSE 0 END) AS discharging_now
  FROM {T('bronze_overflow_snapshots')} WHERE ingested_at = (SELECT max(ingested_at) FROM {T('bronze_overflow_snapshots')})
  GROUP BY company ORDER BY discharging_now DESC"""))
