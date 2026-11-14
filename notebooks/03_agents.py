# Databricks notebook source
# MAGIC %md
# MAGIC # Sentinels 03: agents
# MAGIC Runs the top dry-spill candidates through the agent team, traced in MLflow:
# MAGIC investigator (Claude) -> skeptic (Databricks-served open model) -> evidence agent (Claude + Linkup) -> drafter (Claude).
# MAGIC Results and memory go to Delta tables.

# COMMAND ----------

# MAGIC %pip install -q anthropic>=2.8 openai
# MAGIC %restart_python

# COMMAND ----------

# MAGIC %run ./_common

# COMMAND ----------

import os
# Keys: a secret scope is best (databricks secrets create-scope sentinels). Falls back to widgets.
dbutils.widgets.text("anthropic_key", "")
dbutils.widgets.text("linkup_key", "")
dbutils.widgets.text("top_n", "3")
dbutils.widgets.text("skeptic_model", "system.ai.gpt-5-2")
def _secret(key, widget):
    try:
        return dbutils.secrets.get("sentinels", key)
    except Exception:
        return dbutils.widgets.get(widget)
os.environ["ANTHROPIC_API_KEY"] = _secret("anthropic", "anthropic_key")
os.environ["LINKUP_API_KEY"] = _secret("linkup", "linkup_key")

# COMMAND ----------

import json, mlflow
import pandas as pd
from databricks.sdk import WorkspaceClient
from sentinels import llm, orchestrator
from sentinels.memory import CaseMemory

# Skeptic runs on a Databricks foundation model via Unity Gateway: a different model family from Claude
w = WorkspaceClient()
token = w.config.authenticate()["Authorization"].split(" ", 1)[1]
if dbutils.widgets.get("skeptic_model").strip():
    llm.SKEPTIC_CLIENT = llm.gateway_client(w.config.host, token)
    llm.SKEPTIC_DATABRICKS_MODEL = dbutils.widgets.get("skeptic_model").strip()
else:
    print("No skeptic_model set: skeptic falls back to Claude Haiku")

# Which foundation models does this workspace have? Pick a non-Claude one for the skeptic widget.
try:
    print([f"system.ai.{m.name}" for m in w.registered_models.list(catalog_name="system", schema_name="ai")])
except Exception as e:
    print("Could not list models; browse Catalog > system > ai instead:", e)
mlflow.set_experiment(f"/Users/{spark.sql('SELECT current_user()').first()[0]}/sentinels")
try:
    mlflow.anthropic.autolog()  # token usage + raw calls under each agent span
except Exception as e:
    print("autolog unavailable, manual spans only:", e)

# Memory: Delta table -> CaseMemory
spark.sql(f"""CREATE TABLE IF NOT EXISTS {T('gold_case_memory')} (site_id STRING, company STRING, watercourse STRING,
  event_start TIMESTAMP, duration_hours DOUBLE, final_verdict STRING, breach_confidence DOUBLE, skeptic_model STRING,
  strongest_objection STRING, severity STRING, n_sources INT, decided_at TIMESTAMP)""")
mem_rows = py_records(spark.table(T("gold_case_memory")).toPandas())
memory = CaseMemory(path="/tmp/case_memory.jsonl", records=mem_rows)
print(f"{len(mem_rows)} past cases in memory")

# COMMAND ----------

top_n = int(dbutils.widgets.get("top_n"))
cands = spark.sql(f"""SELECT * FROM {T('gold_spill_assessments')} WHERE verdict = 'dry_spill_candidate'
  ORDER BY duration_hours DESC LIMIT {top_n}""").toPandas()
results = []
for r in py_records(cands):
    spill = {**r, "gauges": json.loads(r["gauges_json"])}
    print("Investigating", spill["company"], spill["id"], spill["receivingwatercourse"])
    results.append(orchestrator.run_case(spill, memory))

# COMMAND ----------

if not results:
    dbutils.notebook.exit("No dry-spill candidates to investigate")
new = pd.DataFrame([{k: r[k] for k in ["site_id", "company", "watercourse", "event_start", "duration_hours", "final_verdict",
                                       "breach_confidence", "skeptic_model", "strongest_objection", "severity", "n_sources",
                                       "decided_at"]} for r in results])
spark.createDataFrame(new).write.mode("append").saveAsTable(T("gold_case_memory"))
reports = pd.DataFrame([{"site_id": r["site_id"], "decided_at": r["decided_at"], "final_verdict": r["final_verdict"],
                         "report_md": r["report"] or "", "evidence_json": json.dumps(r["evidence"] or {})} for r in results])
spark.createDataFrame(reports).write.mode("append").option("mergeSchema", "true").saveAsTable(T("gold_evidence_packs"))
display(new)

# COMMAND ----------

# Show the first evidence pack
from IPython.display import Markdown
first = next((r for r in results if r["report"]), None)
Markdown(first["report"]) if first else print("No case survived the skeptic.")
