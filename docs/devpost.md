# Devpost entry (paste each section into the matching field)

**Name:** Sentinel

**Tagline:** Agents that catch sewage spills on dry days, argue over the evidence, and draft the report to the regulator.

**Track:** Autonomous Agents. **Bounties:** Databricks, Linkup.

**Try it out:**
- Repo: https://github.com/Kang-Ji-2048/Sentinels
- Demo: https://sentinels-andrew-site.vercel.app
- Explainer: SITE_1_URL
- Video: VIDEO_URL

## Inspiration

Storm overflows are only allowed to release sewage in heavy rain. England still had about 15,000 spills on dry days
in 2025, around 40 a day (water company figures obtained by The Times). The overflow data and the rainfall data are
both public and live. Nobody puts them together while the spill is still happening.

## What it does

Every 15 minutes Sentinel reads about 13,000 storm overflows across 8 water companies and the Environment Agency's
rain gauges. A spill is flagged when every gauge within 10 km saw under 0.25 mm of rain on each of the two days
before it started. Then a team of agents works the case:

1. **Investigator** (Claude) builds the case from the data and the site's history.
2. **Skeptic** (gpt-oss-120b on Databricks) argues it's innocent: a faulty sensor, rain the gauges missed, a pump
   failure. Using a different model family means it doesn't just agree with Claude.
3. **Evidence agent** (Claude + Linkup) searches the web and reads full pages to test both sides.
4. **Adjudicator** (Claude) decides which objections the evidence refutes and gives a verdict.
5. **Drafter** (Claude) writes an evidence pack and a draft report to the Environment Agency. A person approves it.
6. **Citation verifier** (Linkup) re-opens every cited page and checks it says what we claim.

A real case from 14 Nov: the Carnon River overflow in Cornwall had been spilling for 21 hours with 0.0 mm of rain
at both nearby gauges. The skeptic put breach confidence at 0.42. Linkup found the area was in drought a week
earlier (BBC) and the river has a record of dry-day spills (Surfers Against Sewage). The adjudicator raised it to
0.62, "needs review". All 9 cited claims checked out.

Everything lands in Delta tables, so you can ask Genie "which company has the most dry spills right now?" or check
your own postcode on the map.

## How we built it

- **Databricks:** bronze, silver and gold Delta tables (MERGE, so reruns update rather than duplicate), a Job
  that runs ingest, detect, agents and insights every 15 minutes, AI Gateway for the skeptic model, MLflow
  Tracing on every agent and tool call with the verdict and citation score logged as feedback, Unity Catalog,
  an AI/BI dashboard and a Genie space.
- **Linkup:** `/search` with date windows for fresh evidence, `/fetch` for full pages, and `/fetch` with a JSON
  schema to check each citation against its source.
- **Claude** for five of the six agents, with structured outputs.
- Python, pandas, MapLibre and deck.gl for the map.

## Challenges we ran into

- Rain gauges go quiet. A gauge with no readings now counts as unknown, not dry.
- Offline monitors made spills look days long, so their durations are now unknown too.
- Early runs cited an events listing as a weather source. We added source rules and the citation verifier.
- The skeptic first threw out every case. Moving the final call to an adjudicator fixed that.

## Accomplishments that we're proud of

- It runs end to end on live national data and produced real, cited evidence packs on the day.
- Two model families argue each case, and the record shows which objections were refuted and which still stand.
- Every citation is checked against the page it came from.

## What we learned

A dry-day spill is a lead, not proof. Most of the work is being honest about uncertainty: missing data isn't dry,
an unchecked objection isn't refuted, and nothing goes out without a person signing it off.

## What's next

- Radar rainfall instead of gauges alone.
- Add Southern Water and Welsh Water.
- Train a cheap triage model on past verdicts (Adaption, already wired in) to rank thousands of candidates.
- Hand approved packs to campaign groups to send to the Environment Agency.

## Built with

databricks, delta-lake, unity-catalog, mlflow, genie, linkup, claude, gpt-oss, python, pandas, maplibre, deck.gl,
environment-agency-api, arcgis
