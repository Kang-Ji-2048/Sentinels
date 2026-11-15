# Databricks notebook source
# MAGIC %md
# MAGIC # Sentinel 05: insights layer for the AI/BI dashboard and Genie
# MAGIC Adds Unity Catalog comments (Genie reads them to understand the data) and three views that the
# MAGIC dashboard and Genie space sit on. Run after 02 and 03. It is cheap: SQL only, no API calls.
# MAGIC
# MAGIC **One-time setup in the UI (about 10 minutes)**
# MAGIC 1. **Genie space:** sidebar > Genie > New. Add the tables `workspace.sentinels.v_company_scoreboard`,
# MAGIC    `v_dry_spills`, `v_case_outcomes` and `gold_spill_assessments`. Paste the instructions printed by the
# MAGIC    last cell into *Instructions*. Try: "Which company has the most dry spills?", "Show dry spills
# MAGIC    lasting over 12 hours on a map", "Which cases did the agents rate likely_breach and why?"
# MAGIC 2. **Dashboard:** sidebar > Dashboards > Create dashboard. On the Data tab add the three views as
# MAGIC    datasets. On the canvas add: a point map from `v_dry_spills` (latitude/longitude, colour =
# MAGIC    company, size = duration_hours); a bar chart of `dry_spills` by `company` from
# MAGIC    `v_company_scoreboard`; a counter of total dry spills; and a table of `v_case_outcomes`.
# MAGIC    Publish it, and add the Genie space to the dashboard so judges can ask follow-ups.

# COMMAND ----------

# MAGIC %run ./_common

# COMMAND ----------

S = f"{CATALOG}.{SCHEMA}"
spark.sql(f"""COMMENT ON TABLE {S}.gold_spill_assessments IS 'One row per storm overflow spill that started in
the last 48 hours in England, joined to the nearest Environment Agency rain gauges. verdict =
dry_spill_candidate means every gauge within 10 km saw under 0.25 mm of rain in both 24-hour windows before
the spill started (a possible permit breach); rain_explained means it rained; no_gauge means no usable gauge.'""")
for col, txt in {
    "id": "Overflow (storm overflow / CSO) site id from the water company",
    "receivingwatercourse": "River, stream or sea the overflow discharges into",
    "latesteventstart": "When the spill started (UTC)",
    "duration_hours": "Hours discharging; NULL when the monitor is offline and the end is unknown",
    "max_mm_0_24h_before": "Wettest nearby gauge, mm of rain in the 24 hours before the spill",
    "max_mm_24_48h_before": "Wettest nearby gauge, mm of rain 24 to 48 hours before the spill",
    "max_mm_during": "Wettest nearby gauge, mm of rain while the spill was running",
}.items():
    spark.sql(f"ALTER TABLE {S}.gold_spill_assessments ALTER COLUMN {col} COMMENT '{txt}'")

# COMMAND ----------

spark.sql(f"""CREATE OR REPLACE VIEW {S}.v_dry_spills
COMMENT 'Dry-day spills (possible permit breaches) with location, for maps' AS
SELECT id AS site_id, company, receivingwatercourse AS watercourse, latitude, longitude,
       latesteventstart AS started_at, duration_hours, monitor_offline,
       max_mm_0_24h_before, max_mm_24_48h_before, max_mm_during
FROM {S}.gold_spill_assessments WHERE verdict = 'dry_spill_candidate'""")

spark.sql(f"""CREATE OR REPLACE VIEW {S}.v_company_scoreboard
COMMENT 'Per water company: spills in the last 48 hours, how many were on dry days, and dry-spill hours' AS
SELECT company,
       count(*) AS spills_48h,
       count_if(verdict = 'dry_spill_candidate') AS dry_spills,
       round(count_if(verdict = 'dry_spill_candidate') / count(*), 2) AS dry_share,
       round(sum(CASE WHEN verdict = 'dry_spill_candidate' THEN duration_hours END), 1) AS dry_spill_hours
FROM {S}.gold_spill_assessments GROUP BY company""")

_pack_cols = spark.table(f"{S}.gold_evidence_packs").columns  # citation columns arrive with the next 03 run
_cit = ("p.citations_checked, p.citations_verified" if "citations_checked" in _pack_cols
        else "CAST(NULL AS BIGINT) AS citations_checked, CAST(NULL AS BIGINT) AS citations_verified")
spark.sql(f"""CREATE OR REPLACE VIEW {S}.v_case_outcomes
COMMENT 'Cases the agent team investigated: final verdict, confidence, skeptic objection and how many cited claims Linkup confirmed' AS
WITH m AS (SELECT * FROM {S}.gold_case_memory
           QUALIFY row_number() OVER (PARTITION BY site_id, event_start ORDER BY decided_at DESC) = 1),
     p AS (SELECT * FROM {S}.gold_evidence_packs
           QUALIFY row_number() OVER (PARTITION BY site_id ORDER BY decided_at DESC) = 1)
SELECT m.site_id, m.company, m.watercourse, m.event_start, m.duration_hours, m.final_verdict,
       round(m.breach_confidence, 2) AS breach_confidence, m.skeptic_model, m.strongest_objection,
       m.n_sources, {_cit}, m.decided_at
FROM m LEFT JOIN p ON m.site_id = p.site_id""")

display(spark.sql(f"SELECT * FROM {S}.v_company_scoreboard ORDER BY dry_spills DESC"))

# COMMAND ----------

print("""Genie instructions (paste into the space):
This data tracks sewage spills from storm overflows in England, refreshed from live water-company feeds and
Environment Agency rain gauges. A "dry spill" is a spill that started with under 0.25 mm of rain at every gauge
within 10 km in each of the two 24-hour windows before it: a possible permit breach, not proof.
Use v_dry_spills for anything about dry spills and maps, v_company_scoreboard to compare companies, and
v_case_outcomes for what the AI agent team concluded (final_verdict is likely_breach, needs_review or
likely_innocent; breach_confidence is 0-1). Durations are in hours and rainfall in mm. When asked about the
worst offenders, rank by dry_spills, then dry_spill_hours. Always say a dry spill is a candidate breach.""")
