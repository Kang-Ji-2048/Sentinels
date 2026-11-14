# Databricks notebook source
# MAGIC %md
# MAGIC # Sentinels 04: train a spill-triage model with Adaption
# MAGIC Every case the agent team decides (notebook 03) becomes a training row in `gold_training_examples`:
# MAGIC the prompt is only the spill + rainfall data, the completion is the team's final verdict and reasoning.
# MAGIC Adaption's AutoScientist instruction-tunes a small model on those rows, so new candidates can be
# MAGIC triaged cheaply before the expensive investigator / skeptic / Linkup / adjudicator loop runs.
# MAGIC The more cases 03 has decided (raise its `top_n`), the better the training set.

# COMMAND ----------

# MAGIC %run ./_common

# COMMAND ----------

import os, json, time
# Same key lookup as notebook 03: secret scope "sentinels" -> private keys file -> widget box
dbutils.widgets.text("adaption_key", "")
dbutils.widgets.text("base_model", "")  # empty = Adaption picks; see the base-model list below
dbutils.widgets.text("experiment_id", "")  # fill in to check on a run started earlier

_user = spark.sql("SELECT current_user()").first()[0]
KEYS_FILE = f"/Workspace/Users/{_user}/.sentinels_keys.json"
try:
    _saved = json.load(open(KEYS_FILE))
except Exception:
    _saved = {}
try:
    key = dbutils.secrets.get("sentinels", "adaption")
except Exception:
    key = dbutils.widgets.get("adaption_key").strip() or _saved.get("adaption", "")
    if key and key != _saved.get("adaption"):
        _saved["adaption"] = key
        with open(KEYS_FILE, "w") as f:
            json.dump(_saved, f)
os.environ["ADAPTION_API_KEY"] = key
print("Adaption key:", "set" if key else "MISSING")

from sentinels import adaption

# COMMAND ----------

# Training set: one row per decided case, latest decision per site/event
rows = spark.sql(f"""SELECT prompt, completion FROM {T('gold_training_examples')}
  QUALIFY ROW_NUMBER() OVER (PARTITION BY prompt ORDER BY decided_at DESC) = 1""").toPandas()
print(f"{len(rows)} training rows")
print(rows["completion"].map(lambda c: json.loads(c)["verdict"]).value_counts())
path = "/tmp/sentinels_triage.jsonl"
rows.to_json(path, orient="records", lines=True)

# COMMAND ----------

dataset_id = adaption.upload_dataset(path, name=f"sentinels-triage-{time.strftime('%Y%m%d-%H%M')}")
print("dataset:", dataset_id)
for _ in range(60):  # wait for Adaption to finish ingesting the file
    st = adaption.dataset_status(dataset_id)
    state = str(st.get("status", "")).lower()
    print(state or st)
    if state not in ("", "pending", "uploading", "processing", "queued", "running"):
        break
    time.sleep(10)

# COMMAND ----------

print("Base models AutoScientist can tune:", json.dumps(adaption.base_models(), indent=1)[:2000])
run = adaption.train(dataset_id, model=dbutils.widgets.get("base_model").strip() or None, max_iterations=1)
print(json.dumps(run, indent=1))
experiment_id = run.get("experiment_id") or run.get("id")
print("Put this in the experiment_id widget to check on it later:", experiment_id)

# COMMAND ----------

# Check on the run (rerun this cell; training takes a while)
eid = dbutils.widgets.get("experiment_id").strip() or globals().get("experiment_id")
print(json.dumps(adaption.run_status(eid), indent=1, default=str)[:4000])
