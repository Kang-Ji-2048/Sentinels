// The Markdown evidence pack a reviewer downloads after approving a case. Nothing is emailed: a person sends it.
import { fmt, pct, titleCase, when, words, type Run, type Site } from "./data"
import type { Decision } from "./decisions"

export const gaugeUrl = (station: string) =>
  `https://environment.data.gov.uk/flood-monitoring/id/stations/${encodeURIComponent(station)}`

export function downloadPack(run: Run, s: Site, d: Decision) {
  const c = s.case!
  const L: string[] = []
  if (c.illustrative) L.push("> **EXAMPLE, NOT A REAL EVIDENCE PACK.** The agent text in this pack was made up to show the format. Do not send it.", "")
  L.push("# Evidence pack: possible dry-day sewage spill", "", `**${titleCase(s.name)}** overflow, ${s.company} (${s.id})`, "",
    `Reviewed and approved by ${d.approved_by} on ${when(d.approved_at)}. Prepared with Sentinels.`, "",
    "## Report", "", d.report || c.report || "", "",
    "## The spill", "", `- Spill started: ${c.event_start}`,
    `- Discharging: ${s.hours == null ? "unknown (monitor offline)" : fmt(s.hours) + " hours"} at the time of the detector run (${when(run.run_at)})`, "",
    "## Rain gauges within 10 km", "", "| Gauge | Distance | Rain, 24 h before | Rain, 24 to 48 h before | Data |", "|---|---|---|---|---|",
    ...s.gauges.map(g => `| ${g.station} | ${fmt(g.km)} km | ${fmt(g.mm_0_24h_before, 2)} mm | ${fmt(g.mm_24_48h_before, 2)} mm | ${gaugeUrl(g.station)} |`),
    "", "Under 0.25 mm in a 24-hour window counts as a dry day.", "",
    "## Agents' assessment", "",
    `Final verdict: ${words(c.final_verdict)}, ${pct(c.breach_confidence)} confidence that this is a genuine dry-day spill (the skeptic alone said ${pct(c.skeptic_confidence)}).`, "")
  const items = (h: string, xs?: string[]) => { if (xs?.length) L.push(`${h}:`, "", ...xs.map(x => `- ${x}`), "") }
  items("Objections still standing", c.ruling?.objections_standing)
  items("Objections refuted", c.ruling?.objections_refuted)
  const srcs = (c.evidence?.searches ?? []).flatMap(q => q.sources ?? [])
  if (srcs.length) L.push("## Sources", "", ...srcs.map(x => (x.url ? `- [${x.name || x.url}](${x.url})` : `- ${x.name}`)), "")
  L.push("---", "", "This is a report of a possible breach for investigation, not proof. Spill data is self-reported by the water company and rain gauges are sparse.")
  const a = document.createElement("a")
  a.href = URL.createObjectURL(new Blob([L.join("\n")], { type: "text/markdown" }))
  a.download = `sentinels-${c.illustrative ? "EXAMPLE-" : ""}evidence-pack-${s.id}.md`
  document.body.append(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(a.href), 1000)
}
