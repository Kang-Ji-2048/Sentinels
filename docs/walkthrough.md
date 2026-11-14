# Judge walkthrough (5 minutes)

**Hook (20 s).** About 40 potentially illegal sewage spills happen in England every day, and almost none are caught
while they're happening. Storm overflows may only spill in heavy rain. Water companies now publish live overflow
status, and the Environment Agency publishes live rainfall. Nobody joins them up.

**Live numbers (30 s).** Open `02_detect_silver_gold`: 13,207 overflows across 8 companies, refreshed every 15
minutes. In the 48 hours before our first run, 157 spills started, and 71 began with no meaningful rain at any
gauge within 10 km. Show the 3D map: red columns are dry spills, and their height is hours discharging.

**One case, end to end (3 min).** Carnon River, South West Water (SBB00211), as of 14 Nov:
1. *Data:* discharging for about 21 hours and still going. Three EA gauges within 7 km recorded 0 to 0.2 mm in the
   48 hours before it started. (We first ranked Helliwell Syke higher, but its monitor was offline, so the
   detector now treats offline durations as unknown. Worth telling judges: it shows the data limits are handled.)
2. *Investigator (Claude):* builds the case, checks memory for this site's past spills and the company's record.
3. *Skeptic (Llama, served on Databricks):* argues the other side, for example sensor fault, ungauged rain or
   pump failure, and gives a confidence score. A different model family means it doesn't just agree with Claude.
   Low confidence stops the case here, so obviously innocent spills cost one cheap call.
4. *Evidence agent (Claude + Linkup):* searches the live web to test both sides, such as local news, bathing
   closures, EA enforcement and reported pump failures. Every fact is cited.
5. *Drafter:* writes the evidence pack and a draft report to the EA. A human approves before anything is sent.
6. Open the MLflow trace: every span, prompt, tool call and token count.

**Why it matters (30 s).** Memory in Delta builds a record of repeat offenders and faulty sensors over time.
Evidence packs are the input a regulator, journalist or campaign group needs. The limits are honest:
self-reported data, sparse gauges, and a dry spill is a candidate, not proof. That's why the skeptic exists.

**Bounties.**
- *Databricks:* medallion Delta pipeline, scheduled job, Foundation Model API for the skeptic, MLflow Tracing,
  Delta-backed agent memory.
- *Linkup:* the evidence agent is built around Linkup sourced answers, which verify fresh information and cite it.
