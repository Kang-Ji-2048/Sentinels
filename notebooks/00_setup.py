# Databricks notebook source
# MAGIC %md
# MAGIC # Sentinels 00: setup
# MAGIC Run once. Creates the schema and checks that this workspace can reach the live data and APIs.
# MAGIC Free Edition only allows outbound traffic to a list of trusted domains, so check this first.

# COMMAND ----------

CATALOG, SCHEMA = "workspace", "sentinels"
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")

# COMMAND ----------

import requests
for url in ["https://services3.arcgis.com/VCOY1atHWVcDlvlJ/arcgis/rest/services/stream_service_outfall_locations_view/FeatureServer/0?f=json",
            "https://environment.data.gov.uk/flood-monitoring/id/stations?parameter=rainfall&_limit=1",
            "https://api.linkup.so/v1/search",
            "https://api.anthropic.com/v1/models"]:
    try:
        print(requests.get(url, timeout=10).status_code, url)
    except Exception as e:
        print("BLOCKED", url, type(e).__name__)
