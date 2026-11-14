# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Undecided. No frontend exists yet; the only visual output today is a pydeck (deck.gl) map exported to `docs/map.html` and shown in Databricks notebooks. The app screen currently exists only as a Figma mock.

## Users

Hackathon judges watching a roughly five-minute demo on a shared screen or projector, with the presenter driving. They have not seen the product before and judge it on whether the problem and the result land quickly. (Confirmed by the owner, 14 Nov 2026.)

Other audiences named in the README but not the design target: regulators, journalists and campaign groups who would receive the evidence packs.

## Product Purpose

Sentinels catches sewage spills on dry days. Storm overflows in England may only discharge in heavy rain; Sentinels joins live overflow status from the water companies to Environment Agency rainfall, flags spills that started with no meaningful rain nearby, has a team of agents investigate and challenge each candidate, and drafts a report to the Environment Agency that a human approves.

Success on the app screen: a viewer can spot, at a glance, where sewage is spilling without rain right now and for how long. (Confirmed as the core job.)

## Positioning

Nobody else joins the live overflow feeds to live rainfall as it happens. Sentinels also checks its own work: a skeptic agent on a different model family argues the innocent explanation before a case goes further, and every fact from the evidence agent is cited.

## Operating Context

- Shown live during a judged demo; the walkthrough is in `docs/walkthrough.md`.
- The demo moves from live numbers, to the 3D map, to one case followed end to end (Helliwell Syke, Yorkshire Water, YWS00897).
- The pipeline runs on Databricks as a scheduled job, refreshing every 15 minutes; agent steps are traced in MLflow.

## Capabilities and Constraints

- Map: one column per discharging overflow. Height is hours discharging; colour is the verdict.
- Verdicts, in the code's terms: `dry_spill_candidate`, `rain_explained`, `no_gauge`.
- Per-site facts available: company, site id, receiving watercourse, hours discharging, and the wettest nearby gauge's rainfall in the 24 hours before the spill and in the 24 hours before that. A spill is dry only if both are under 0.25 mm.
- Agents: investigator (Claude), skeptic (a different model family served on Databricks; the code default is `system.ai.databricks-gpt-5-5`, set by `SENTINELS_SKEPTIC_MODEL`), evidence agent (Claude + Linkup web search), drafter.
- Chats (planned, not built): shows the agents' case transcript for a site, and lets the user ask follow-up questions in the same thread. (Confirmed.)
- A human approves every report before anything is sent.
- A dry spill is a candidate, not proof. The data is self-reported by water companies and rain gauges are sparse. The interface must not present a candidate as a confirmed breach.
- Open: the README says 9 water companies and about 15k overflows; the walkthrough says 13,207 overflows across 8 companies. Use live figures, and settle which is current before printing either.

## Brand Commitments

Name: Sentinels. No logo, typeface or palette has been made binding. The map's verdict colours in `sentinels/viz.py` (red candidate, blue rain-explained, grey no-gauge) are existing behaviour, not a brand decision.

## Evidence on Hand

- Live run figures in `docs/walkthrough.md`: 157 spills started in the 48 hours before the first run; 71 began with no meaningful rain at any gauge within 10 km.
- One worked case: Helliwell Syke (YWS00897), discharging 44.5 hours, three EA gauges within 10 km recording 0 to 0.12 mm in the 48 hours before.
- Rendered map: `docs/map.html`.
- Context figures in `README.md` (about 291k spills in 2025, EA; about 15k dry-day spills a year, Times/SAS).
- None exist and none may be invented: testimonials, users, customers, press, enforcement outcomes.

## Product Principles

1. The dry spills are the story. Everything else on screen is context for them.
2. Candidate, not verdict. State what the data shows and what it cannot.
3. Show the disagreement. The skeptic's challenge is part of the result, not hidden behind it.
4. Every claim traces to a source: a feed, a gauge, a citation or a trace.
5. A person decides. Nothing reaches the regulator without approval.
