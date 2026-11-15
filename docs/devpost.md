# Devpost submission draft (paste each section into the matching Devpost field)

**Name:** Sentinels

**Tagline:** Autonomous agents that catch sewage spills on dry days, check their own work, and draft the report to the regulator.

**Track / bounties:** Autonomous Agents. Databricks bounty, Linkup bounty.

## Inspiration

Storm overflows in England may only discharge sewage when heavy rain would otherwise flood homes. In 2025 there
were 291,492 storm overflow spills (Environment Agency). Water companies' own figures, obtained by The Times, show
almost 15,000 of them happened on dry days: about 40 potentially illegal spills a day, lasting 157,803 hours in
total. Water companies now publish live overflow status, and the Environment Agency publishes live rainfall, but
nobody joins them up as it happens, checks for innocent explanations, and turns a suspicious spill into evidence
a regulator can act on.

## What it does

Every 15 minutes Sentinels pulls the live status of about 13,000 storm overflows from 8 English water companies
and the Environment Agency's rain gauges. It flags any spill that started when every gauge within 10 km saw under
0.25 mm of rain in each of the two days before. A team of agents then works each case:

1. **Investigator (Claude)** builds the case from the data and from Delta-backed memory of the site's history.
2. **Skeptic (gpt-oss-120b on Databricks)**, a different model family, argues for innocent explanations: sensor
   faults, rain the gauges missed, pump failures, tides. It gives a confidence score.
3. **Evidence agent (Claude + Linkup)** searches the live web and reads full pages to test both sides, citing
   every fact.
4. **Adjudicator (Claude)** decides which objections the evidence refutes and which still stand, and gives the
   final verdict: likely breach, needs review, or likely innocent.
5. **Drafter (Claude)** writes an evidence pack and a draft report to the Environment Agency, clearly labelled as
   a possible breach. A human approves it before anything is sent.
6. **Citation verifier (Linkup fetch)** re-opens every cited page and checks it really says what the pack claims.

In our real run on 15 Nov, the Dawdon Dene Beck overflow in County Durham (Northumbrian Water) had been
discharging for 16 hours with 0.0 mm of rain at a gauge only 0.8 km away. The skeptic still raised pump failure,
tides and groundwater. The evidence agent found an independent copy of the monitor data confirming one continuous
16.6-hour discharge, and a local forecast describing those days as dry and frosty. The adjudicator refuted the
sensor-fault and missed-rain objections, kept the unverified ones standing, and settled on 0.80: likely breach.
The citation verifier confirmed 7 of 10 cited claims and flagged the other 3 for the human reviewer. Across the 8 cases
decided so far there are 4 likely breaches, 2 needing review and 2 likely innocent.

Results land in Delta tables. A Genie agent and an AI/BI dashboard let anyone ask "which water company has the
most dry spills right now?" in plain English, and a 3D map shows every dry spill with the agents' conversation.

## How we built it

- **Databricks**: Bronze, silver and gold Delta tables (MERGE so reruns update events instead of duplicating),
  a scheduled Job (ingest, detect, agents, insights), Unity AI Gateway for the skeptic model, MLflow Tracing on
  every agent and tool call with the verdict and citation score attached as feedback, Unity Catalog comments,
  an AI/BI dashboard and a Genie agent.
- **Linkup**: `/search` with sourced answers and date windows for fresh evidence; `/fetch` to read full pages;
  `/fetch` with a JSON schema to verify each citation against the page it cites.
- **Anthropic Claude** for the investigator, evidence agent, adjudicator, drafter and verifier, with structured
  outputs; **gpt-oss-120b** for the skeptic so the two sides come from different model families.
- Python, pandas, pydeck and MapLibre for the maps.

## Challenges we ran into

- Rain gauges are sparse and sometimes silent. A gauge with missing readings now counts as unknown, not dry.
- Offline monitors made spills look like they lasted days. Durations for offline monitors are now unknown
  instead of guessed.
- Early runs cited weak web pages (an events listing as a weather source). We added source rules and then a
  citation verifier that re-reads every page and flags claims its page does not support.
- At first the skeptic stopped every case. We moved the decision to an adjudicator that weighs the skeptic's
  objections against the web evidence.

## Accomplishments that we're proud of

- It runs on live national data, end to end, and produced real cited evidence packs on the day.
- It argues with itself: a second model family plays the defence, and an adjudicator records which objections
  were refuted and which still stand.
- Every citation is machine-checked against its source.

## What we learned

A dry-day spill is a candidate, not proof. The value is in handling the uncertainty honestly: unknown is not dry,
an unverified objection is not refuted, and nothing is sent without a person.

## What's next

- Radar rainfall instead of gauges only.
- Southern Water and Welsh Water feeds.
- Train a cheap triage model on the team's verdicts (Adaption AutoScientist, already wired up) so thousands of
  candidates can be ranked before the full agent loop.
- Work with campaign groups to send approved packs to the Environment Agency.

## Built with

databricks, delta-lake, unity-catalog, mlflow, genie, linkup, anthropic-claude, gpt-oss, python, pandas,
pydeck, maplibre, environment-agency-api, arcgis
