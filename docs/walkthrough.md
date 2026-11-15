# Judge walkthrough (5 minutes)

**Hook (20 s).** About 40 potentially illegal sewage spills happen in England every day, and almost none are caught
while they're happening. Storm overflows may only spill in heavy rain. Water companies now publish live overflow
status, and the Environment Agency publishes live rainfall. Nobody joins them up.

**Live numbers (30 s).** Open `02_detect_silver_gold`: 13,207 overflows across 8 companies, refreshed every 15
minutes. In the 48 hours before our first run, 157 spills started, and 71 began with no meaningful rain at any
gauge within 10 km. Show the 3D map: red columns are dry spills, and their height is hours discharging.

**One case, end to end (3 min).** Dawdon Dene Beck, Northumbrian Water (NWL00415), County Durham, 15 Nov run.
The full real run is in `data/example_case.json` (all 8 cases from this run are in `data/example_cases.json`).
1. *Data:* discharging for 16.4 hours. The nearest EA gauge is only 0.8 km away; it and a second gauge 7.5 km away
   recorded at most 0.2 mm in the 48 hours before and 0.0 mm during the spill. Monitor online.
2. *Investigator (Claude):* builds the case, checks memory for this site's past spills and the company's record.
3. *Skeptic (gpt-oss-120b, served on Databricks):* argues the other side. It rates groundwater, tidal backflow and an
   emergency pump discharge "medium", sensor faults and missed rain "low". Breach confidence: 0.78. A different
   model family means it doesn't just agree with Claude. Only near-certain innocent cases (below 0.15) stop here.
4. *Evidence agent (Claude + Linkup):* 5 live searches and 2 full-page reads. It found an independent copy of the
   monitor data (FloodMapper) showing one continuous ~16.6-hour discharge from the reported start, and a Northern
   Echo forecast describing 13-14 Nov as dry and frosty, with rain only on the 15th.
5. *Adjudicator (Claude):* refuted the sensor blip and timestamp error (independent data), missed rain (forecast +
   gauge 0.8 km away) and snowmelt. Still standing: a pump failure nobody reported, tidal backflow, groundwater, and
   that the site was matched to FloodMapper by name only. Final confidence 0.80: **likely_breach**.
6. *Drafter:* writes the evidence pack and a draft report to the EA, saying clearly it is a possible breach and
   listing what the EA should check. A human approves before anything is sent.
7. *Citation verifier (Linkup fetch):* re-opens each cited page. **7 of 10** cited claims were confirmed with a quote;
   3 were flagged as not supported by their page. That is the point: the reviewer sees exactly which claims to
   double-check before anything goes to the regulator.
8. Open the MLflow trace (the verdict and citation score are attached as feedback): every span, prompt, tool call
   and token count.

Same run, for questions: River Roding (Thames Water) likely_breach 0.77, nearest gauge 1.1 km, 0.0 mm; Carnon
River needs_review 0.60 (this time rain fell during the spill, so the agents held back).

**Why it matters (30 s).** Memory in Delta builds a record of repeat offenders and faulty sensors over time.
Evidence packs are the input a regulator, journalist or campaign group needs. The limits are honest:
self-reported data, sparse gauges, and a dry spill is a candidate, not proof. That's why the skeptic exists.

**Bounties.**
- *Databricks:* medallion Delta pipeline with MERGE, scheduled job, a Unity Gateway foundation model for the
  skeptic, MLflow Tracing with feedback scores, Delta-backed agent memory, and an AI/BI dashboard with a Genie
  space so anyone can ask "which company has the most dry spills?"
- *Linkup:* three uses. Search with date windows finds fresh cited context, fetch reads full pages, and fetch with
  grounded extraction verifies every citation in the final pack.
