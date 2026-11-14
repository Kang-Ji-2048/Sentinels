# Sentinels

**Autonomous agents that catch sewage spills on dry days, check their own work, and draft the report to the regulator.**

> About 40 potentially illegal sewage spills happen every day in England, and almost none are caught in real time.

Storm overflows are only allowed to discharge sewage when heavy rain would otherwise flood homes. When an overflow spills on a **dry day**, it may be breaching its permit. In 2025 England had 291,492 storm overflow spills ([Environment Agency](https://www.gov.uk/government/news/fewer-and-shorter-storm-overflow-spills-in-2025-new-monitoring-data-shows)). Water companies' own figures, obtained by The Times, showed almost 15,000 dry-day spills in 2025, lasting 157,803 hours: about 40 a day ([The Times via East Devon Watch](https://eastdevonwatch.org/2026/03/17)). Water companies now publish near-real-time overflow status, but nobody joins that data to rainfall as it happens, checks for innocent explanations, and turns a suspicious spill into evidence someone can act on.

Sentinels does this as a pipeline on Databricks plus a team of agents:

1. **Watch.** Pull live overflow status from every water company and rainfall from the Environment Agency.
2. **Flag.** Mark spills that started with no meaningful rain nearby.
3. **Investigate.** An investigator agent builds the case using memory of the site's history and repeat offences.
4. **Challenge.** A skeptic agent, running on a different model, looks for innocent explanations such as a sensor fault, rain the gauges missed, snowmelt or permitted emergency discharge.
5. **Verify.** An evidence agent uses Linkup live web search (and full-page reads) to find fresh cited context: local news, bathing water closures, past fines, permit details. An adjudicator weighs the skeptic's objections against that evidence, and a citation verifier re-reads every cited page with Linkup to confirm it says what we claim.
6. **Act.** A drafter writes an evidence pack and a draft report to the Environment Agency. A human approves it before anything is sent.

This is not an app. It is a pipeline and an agent system, with every step traced in MLflow.

---

## Architecture

```mermaid
flowchart LR
    subgraph Sources["Live open data"]
        A1["8 English water company<br/>ArcGIS overflow feeds<br/>(~13k overflows)"]
        A2["EA flood-monitoring API<br/>rain gauges, 15-min readings"]
    end

    subgraph Databricks["Databricks Data Intelligence Platform"]
        B["Bronze (Delta)<br/>raw overflow snapshots<br/>+ rainfall readings"]
        S["Silver (Delta)<br/>discharge events<br/>+ nearest-gauge rainfall"]
        G["Gold (Delta)<br/>dry_spill_candidates"]
        M[("Memory (Delta)<br/>site history,<br/>past verdicts")]
        T["MLflow Tracing<br/>every agent step"]
    end

    subgraph Agents["Agent team"]
        I["Investigator<br/>(Claude)"]
        K["Skeptic<br/>(Databricks-hosted<br/>open model)"]
        L["Evidence agent<br/>(Linkup live search,<br/>cited sources)"]
        D["Drafter<br/>(Claude)"]
    end

    H{{"Human approves"}}
    EA["Evidence pack +<br/>draft EA report"]

    A1 --> B
    A2 --> B
    B --> S --> G
    G --> I
    M <--> I
    I --> K
    I --> L
    K --> D
    L --> D
    D --> EA --> H
    D --> M
    I -.-> T
    K -.-> T
    L -.-> T
    D -.-> T
```

### Why each part exists

| Component | What it does | Why it matters |
|---|---|---|
| **Medallion pipeline** (Bronze → Silver → Gold Delta tables) | Snapshots every overflow's status, turns status changes into discharge events, and joins each event to the nearest rain gauges | Reproducible, auditable data, which an evidence pack needs |
| **Dry-spill rule** | A spill counts as a candidate if every gauge within a set radius saw almost no rain on the day it started and the day before (EA-style dry-day test, thresholds configurable) | Simple, explainable and conservative |
| **Memory** (Delta table) | Keeps each site's past spills, past verdicts and how often the skeptic was right | Lets the investigator spot repeat offenders, and lets the system learn which sites have faulty sensors |
| **Investigator** (Claude) | Builds the case for a breach from the data and the memory | The prosecution |
| **Skeptic** (a different model, served on Databricks) | Argues for innocent explanations and scores how confident we can be | The defence. A second model avoids one model agreeing with itself |
| **Evidence agent** (Linkup) | Searches the live web for fresh, cited context about the site, the river and the company | Turns a data point into something a journalist or regulator can verify |
| **Drafter** (Claude) | Writes the evidence pack and a draft report to the EA, with every claim linked to data or a source | Ends in a real action, approved by a human |
| **Citation verifier** (Linkup fetch) | Re-opens every page the evidence pack cites and checks, with Linkup's grounded extraction, that the page really says what the pack claims. The pack ends with "n of m citations confirmed" | A regulator can trust the citations; hallucinated or off-topic sources are caught |
| **MLflow Tracing + feedback** | Records every agent call, tool call and decision, and attaches the verdict and citation-check score to each trace as feedback | Lets us walk judges through one real case step by step, and track grounding quality over time |
| **AI/BI dashboard + Genie** | Views with Unity Catalog comments over the gold tables; a Genie space answers plain-English questions such as "which company has the most dry spills?" | Makes the findings explorable by non-engineers |

---

## Data sources

| Source | Access | Licence |
|---|---|---|
| Storm overflow activity: one ArcGIS FeatureServer per company, listed on [Stream Water Data](https://www.streamwaterdata.co.uk/) as part of the National Storm Overflows Hub. Covers Anglian, Northumbrian, Severn Trent, South West, Thames, United Utilities, Wessex, Yorkshire and Scottish Water | Public, no key, max 1000 records per query | CC BY 4.0 |
| [EA flood-monitoring API](https://environment.data.gov.uk/flood-monitoring/doc/reference): rain gauges with 15-minute readings, searchable by location | Public, no key | Open Government Licence |
| [Linkup](https://www.linkup.so/) live web search with cited answers | API key | Commercial API |

Overflow status codes: `1` = discharging, `0` = stopped, `-1` = offline. Each record has the site id, company, current status and when it started, the latest event's start and end, lat/long, the receiving watercourse and a last-updated time. Most companies use the same field names. South West Water uses camelCase and Scottish Water uses a different schema, so ingestion normalises them.

**Known gaps.** Southern Water and Welsh Water publish elsewhere and are not covered yet. The spill data is self-reported by water companies, and rain gauges can miss local showers, which is exactly why the skeptic agent exists.

---

## Repository layout

```
sentinels/feeds.py         Live sources: 8 water-company ArcGIS feeds, EA rain gauges
sentinels/detect.py        Dry-spill rule: spill + nearest gauges -> verdict
sentinels/agents.py        Investigator, skeptic, Linkup evidence agent, drafter (MLflow-traced)
sentinels/orchestrator.py  Runs one case through the team; the skeptic gates the expensive steps
sentinels/memory.py        Case memory per site (JSONL locally, Delta on Databricks)
notebooks/00_setup         Schema + check this workspace can reach the APIs
notebooks/01_ingest_bronze Snapshot all overflows + gauges into Delta (schedule every 15 min)
notebooks/02_detect_...    Silver events (MERGE), rain readings, gold assessments
notebooks/03_agents        Top candidates -> agent team -> gold_case_memory + gold_evidence_packs + gold_training_examples
notebooks/05_insights      UC comments + views for the AI/BI dashboard and Genie space (plain-English questions)
notebooks/04_adaption      Train a cheap spill-triage model on the team's past verdicts (Adaption AutoScientist)
sentinels/adaption.py      Adaption Labs API: hosted models (optional skeptic), dataset upload, training
scripts/detect.py          Run the detector locally and print the top candidates
scripts/agents.py          Run the agent team locally on the top N candidates
scripts/map.py             3D map of the latest run -> docs/map.html
databricks.yml             Job: ingest -> detect -> agents every 15 min (starts paused)
docs/walkthrough.md        Five-minute judge walkthrough with one worked case
```

## Run it

**Locally (detector only, no keys needed):**
```
pip install -r requirements.txt
python scripts/detect.py
```

**On Databricks:** add this repo as a Git folder, then run `notebooks/00_setup`, `01_ingest_bronze`,
`02_detect_silver_gold` and `03_agents` in order. `03_agents` reads the Anthropic and Linkup keys from a
secret scope called `sentinels` (keys `anthropic`, `linkup`), or from the notebook widgets.

### First live run (14 Nov 2026, 12:50 UK time)

13,207 English overflows checked. 157 spills started in the previous 48 hours, and 71 of them had less
than 0.25 mm of rain at every gauge within 10 km in both 24-hour windows before the spill. The longest
with a working monitor: Carnon River (South West Water, SBB00211), still discharging after about 21 hours with
under 0.25 mm of rain at three gauges within 7 km. (Spills whose monitor has gone offline get an unknown duration
rather than a guessed one.)

## Learning from its own verdicts (Adaption)

Every case the agent team decides is saved as a training row: the prompt holds only what is known before
the expensive agents run (the spill and the rainfall), and the answer is the team's final verdict, confidence
and reasoning. `notebooks/04_adaption` uploads these rows to Adaption and runs AutoScientist to instruction-tune
a small model on them. The aim is a cheap triage model that can rank thousands of new candidates and send only
the promising ones to the full investigator, skeptic, Linkup and adjudicator loop. It needs a few dozen decided
cases first, so run 03 with a larger `top_n`.

## Models and APIs used

- **Anthropic Claude** (`claude-opus-5-5`): investigator, evidence agent, adjudicator, drafter, citation verifier. Structured outputs for every agent that returns JSON.
- **OpenAI gpt-oss-120b**, served by Databricks through Unity AI Gateway (`system.ai.gpt-oss-120b`): the skeptic. Falls back to Claude Haiku if the gateway model is unavailable.
- **Linkup**: `/search` (sourced answers, date windows) for the evidence agent, and `/fetch` both for full-page reads and, with a JSON schema, for grounded citation checks.
- **Databricks**: Delta Lake medallion tables with MERGE, Unity Catalog (with table and column comments), Jobs, MLflow Tracing with feedback scores, AI/BI dashboard and a Genie agent.
- **Adaption Labs** (built, not yet trained): optional hosted-model skeptic (`adaption:qwen3.5-397b`) and AutoScientist training of a triage model once enough cases are decided.
- **Data**: 8 water companies' ArcGIS storm overflow feeds (Stream / National Storm Overflows Hub), Environment Agency flood-monitoring rainfall API.

## Limitations

- A dry-day spill is a **candidate** breach, not proof. Some permits allow discharges in specific dry-weather conditions, and only the EA can decide.
- Rain gauges are sparse, so a nearby unrecorded shower can make a legitimate spill look dry. The skeptic agent and the confidence score exist for this reason.
- No report is sent automatically. A human approves every one.

Built at the Imperial AI Hackathon, 14 to 15 November 2026.
