# Judge walkthrough (5 minutes)

**Hook (20 s).** About 40 potentially illegal sewage spills happen in England every day, and almost none are caught
while they're happening. Storm overflows may only spill in heavy rain. Water companies now publish live overflow
status, and the Environment Agency publishes live rainfall. Nobody joins them up.

**Live numbers (30 s).** Open `02_detect_silver_gold`: 13,207 overflows across 8 companies, refreshed every 15
minutes. In the 48 hours before our first run, 157 spills started, and 71 began with no meaningful rain at any
gauge within 10 km. Show the 3D map: red columns are dry spills, and their height is hours discharging.

**One case, end to end (3 min).** Carnon River, South West Water (SBB00211), as of 14 Nov:
The full real run is in `data/example_case.json`.
1. *Data:* discharging for about 21 hours and still going. Two EA gauges, 5.7 and 6.5 km away, recorded at most
   0.2 mm in the 48 hours before it started and 0.0 mm during it. (We first ranked Helliwell Syke higher, but its monitor was offline, so the
   detector now treats offline durations as unknown. Worth telling judges: it shows the data limits are handled.)
2. *Investigator (Claude):* builds the case, checks memory for this site's past spills and the company's record.
3. *Skeptic (gpt-oss-120b, served on Databricks):* argues the other side and rates pump failure "high", with
   sensor fault and gauges missing local rain as "medium". Breach confidence: 0.25. A different model family means
   it doesn't just agree with Claude. Only near-certain innocent cases (below 0.15) stop here.
4. *Evidence agent (Claude + Linkup):* 5 live searches test both sides. It found that regulators described the region
   as in "severe drought" on 5 Nov, no reported pump failure or local rain, and South West Water's £7.9m fine in
   Sept 2026 for illegal discharges. Every fact is cited, and weak sources are flagged as weak.
5. *Adjudicator (Claude):* weighs each objection against the evidence. Refuted: missed rain, groundwater, and pump
   failure as an excuse (failing to fix a pump failure was itself one of the charges). Still standing: sensor fault
   and tidal influence. Final confidence 0.68, so the verdict is **likely_breach**.
6. *Drafter:* writes the evidence pack and a draft report to the EA, saying clearly it is a possible breach and
   listing what the EA should check. A human approves before anything is sent.
7. *Citation verifier (Linkup fetch):* re-opens each cited page and checks it really says what the pack
   claims. The pack ends with "n of m citations confirmed", with the supporting quote for each.
8. Open the MLflow trace (the verdict and citation score are attached as feedback): every span, prompt, tool call and token count.

**Why it matters (30 s).** Memory in Delta builds a record of repeat offenders and faulty sensors over time.
Evidence packs are the input a regulator, journalist or campaign group needs. The limits are honest:
self-reported data, sparse gauges, and a dry spill is a candidate, not proof. That's why the skeptic exists.

**Bounties.**
- *Databricks:* medallion Delta pipeline with MERGE, scheduled job, a Unity Gateway foundation model for the
  skeptic, MLflow Tracing with feedback scores, Delta-backed agent memory, and an AI/BI dashboard with a Genie
  space so anyone can ask "which company has the most dry spills?"
- *Linkup:* three uses. Search with date windows finds fresh cited context, fetch reads full pages, and fetch with
  grounded extraction verifies every citation in the final pack.
