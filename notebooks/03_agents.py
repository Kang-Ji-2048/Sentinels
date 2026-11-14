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

import os, json
# Keys are looked up in order: secret scope "sentinels" -> a private keys file in your workspace home
# (outside the Git folder, so pulls never touch it) -> the widget boxes. Paste keys into the boxes once:
# they're saved to the keys file and reused on every later run.
dbutils.widgets.text("anthropic_key", "")
dbutils.widgets.text("linkup_key", "")
dbutils.widgets.text("adaption_key", "")  # optional: only for an adaption:<model> skeptic and notebook 04
dbutils.widgets.text("top_n", "3")
# Databricks model (system.ai.gpt-oss-120b) or an Adaption Labs model (adaption:qwen3.5-397b)
dbutils.widgets.text("skeptic_model", "system.ai.gpt-oss-120b")

_user = spark.sql("SELECT current_user()").first()[0]
KEYS_FILE = f"/Workspace/Users/{_user}/.sentinels_keys.json"
try:
    _saved = json.load(open(KEYS_FILE))
except Exception:
    _saved = {}

def _key(name, widget):
    try:
        return dbutils.secrets.get("sentinels", name)
    except Exception:
        pass
    typed = dbutils.widgets.get(widget).strip()
    if typed and typed != _saved.get(name):
        _saved[name] = typed
        with open(KEYS_FILE, "w") as f:
            json.dump(_saved, f)
    return typed or _saved.get(name, "")

os.environ["ANTHROPIC_API_KEY"] = _key("anthropic", "anthropic_key")
os.environ["LINKUP_API_KEY"] = _key("linkup", "linkup_key")
os.environ["ADAPTION_API_KEY"] = _key("adaption", "adaption_key")
print("Anthropic key:", "set" if os.environ["ANTHROPIC_API_KEY"] else "MISSING",
      "| Linkup key:", "set" if os.environ["LINKUP_API_KEY"] else "MISSING",
      "| Adaption key:", "set" if os.environ["ADAPTION_API_KEY"] else "not set", f"| saved in {KEYS_FILE}")

# COMMAND ----------

import json, mlflow
import pandas as pd
from databricks.sdk import WorkspaceClient
from sentinels import llm, orchestrator
from sentinels.memory import CaseMemory

# Skeptic runs on a Databricks foundation model via Unity Gateway: a different model family from Claude
w = WorkspaceClient()
token = w.config.authenticate()["Authorization"].split(" ", 1)[1]
_skeptic = dbutils.widgets.get("skeptic_model").strip()
if _skeptic.startswith("adaption:"):
    llm.SKEPTIC_DATABRICKS_MODEL = _skeptic
    from sentinels import adaption
    try:
        print("Adaption hosted models:", adaption.list_models())
    except Exception as e:
        print("Adaption model list unavailable:", e)
elif _skeptic:
    llm.SKEPTIC_CLIENT = llm.gateway_client(w.config.host, token)
    llm.SKEPTIC_DATABRICKS_MODEL = dbutils.widgets.get("skeptic_model").strip()
    try:  # names the gateway will actually serve (the catalog list below can include unserved ones)
        print("Gateway serves:", sorted(m.id for m in llm.SKEPTIC_CLIENT.models.list()))
    except Exception as e:
        print("Gateway model list unavailable:", e)
else:
    print("No skeptic_model set: skeptic falls back to Claude Haiku")

# Which foundation models does this workspace have? Pick a non-Claude one for the skeptic widget.
try:
    print([f"system.ai.{m.name}" for m in w.registered_models.list(catalog_name="system", schema_name="ai")])
except Exception as e:
    print("Could not list models; browse Catalog > system > ai instead:", e)
mlflow.set_experiment(f"/Users/{spark.sql('SELECT current_user()').first()[0]}/sentinels_traces")  # not ".../sentinels": that path is the Git folder
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
# One row per spill: a rerun replaces that spill's earlier verdict instead of adding a duplicate
spark.createDataFrame(new).createOrReplaceTempView("new_cases")
spark.sql(f"""MERGE INTO {T('gold_case_memory')} m USING new_cases n
  ON m.site_id = n.site_id AND m.event_start = n.event_start
  WHEN MATCHED THEN UPDATE SET * WHEN NOT MATCHED THEN INSERT *""")
reports = pd.DataFrame([{"site_id": r["site_id"], "decided_at": r["decided_at"], "final_verdict": r["final_verdict"],
                         "report_md": r["report"] or "", "evidence_json": json.dumps(r["evidence"] or {}),
                         "citations_checked": (r["citations"] or {}).get("checked"),
                         "citations_verified": (r["citations"] or {}).get("verified"),
                         "citations_json": json.dumps(r["citations"] or {})} for r in results])
spark.createDataFrame(reports).write.mode("append").option("mergeSchema", "true").saveAsTable(T("gold_evidence_packs"))
# Training rows for the Adaption triage model (notebook 04): spill data -> the team's verdict
from sentinels import adaption
train_rows = [dict(site_id=r["site_id"], decided_at=r["decided_at"], **ex) for r in results
              if (ex := adaption.training_example(r))]
if train_rows:
    spark.createDataFrame(pd.DataFrame(train_rows)).write.mode("append").saveAsTable(T("gold_training_examples"))
display(new)

# COMMAND ----------

# Show the first evidence pack
from IPython.display import Markdown
first = next((r for r in results if r["report"]), None)
Markdown(first["report"]) if first else print("No case survived the skeptic.")

# COMMAND ----------

# Export one complete case for the showcase site (data/example_case.json): copy this output.
best = max((r for r in results if r["report"]), key=lambda r: r["breach_confidence"], default=None)
if best:
    print(json.dumps(best, default=str, indent=1))
