// Chart views for the spill list and the company table. Clicking a bar or its label does the same as clicking
// the name in the table: a site opens its case on the map, a company opens its area on the map.
import { Bar, BarChart, CartesianGrid, Cell, LabelList, XAxis, YAxis } from "recharts"
import { ChartContainer, ChartLegend, ChartLegendContent, ChartTooltip, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart"
import { VERDICT, fmt, titleCase, verdictOf, type Site } from "@/lib/data"

const OTHER = "#A3B1BE"
const MAX_BARS = 25
const clip = (s: string, n = 26) => (s.length > n ? s.slice(0, n - 1) + "…" : s)

/** A y-axis label that is also a button. */
function ClickTick({ x, y, payload, onPick, selected }: {
  x?: number; y?: number; payload?: { value: string }; onPick: (v: string) => void; selected?: string | null
}) {
  const v = payload?.value ?? ""
  return (
    <text x={x} y={y} dy={4} textAnchor="end" fontSize={12} role="button" tabIndex={0} aria-label={`${v}: show on the map`}
      className="cursor-pointer fill-primary hover:underline focus-visible:outline-none"
      fontWeight={selected === v ? 700 : 500}
      onClick={() => onPick(v)} onKeyDown={e => (e.key === "Enter" || e.key === " ") && onPick(v)}>
      {clip(v)}
    </text>
  )
}

const siteConfig = { hours: { label: "Hours discharging" } } satisfies ChartConfig

/** Hours discharging per site, longest first, coloured by verdict. */
export function SpillBars({ sites, selected, onSelect }: { sites: Site[]; selected: Site | null; onSelect: (s: Site) => void }) {
  const known = sites.filter(s => s.hours != null)
  const shown = known.slice(0, MAX_BARS)
  if (!shown.length) return <p className="px-5 py-8 text-center text-sm text-muted-foreground">No spills with a known duration here.</p>
  // Names can repeat (e.g. "Groundwater"), so key bars by site id and label them by name.
  const data = shown.map(s => ({ id: s.id, label: `${titleCase(s.name)} · ${s.id}`, hours: s.hours!, site: s }))
  const byLabel = new Map(data.map(d => [d.label, d.site]))
  const verdicts = [...new Set(shown.map(verdictOf))]
  return (
    <figure className="grid gap-2 px-3 pb-5 md:px-5">
      <ChartContainer config={siteConfig} className="aspect-auto w-full" style={{ height: 40 + data.length * 36 }}>
        <BarChart data={data} layout="vertical" margin={{ top: 4, right: 44, left: 8, bottom: 0 }} barCategoryGap={8}>
          <CartesianGrid horizontal={false} strokeDasharray="2 3" />
          <XAxis type="number" tickLine={false} axisLine={false} fontSize={11} unit=" h" />
          <YAxis type="category" dataKey="label" width={210} tickLine={false} axisLine={false} interval={0}
            tick={<ClickTick onPick={v => onSelect(byLabel.get(v)!)} selected={selected ? `${titleCase(selected.name)} · ${selected.id}` : null} />} />
          <ChartTooltip cursor={{ fill: "var(--muted)" }} content={<ChartTooltipContent hideIndicator formatter={(v, _n, item) => (
            <span className="grid gap-0.5">
              <b className="font-semibold">{item.payload.label}</b>
              <span className="num">{fmt(Number(v))} h · {VERDICT[verdictOf(item.payload.site)].label}</span>
            </span>
          )} />} />
          <Bar dataKey="hours" radius={[0, 4, 4, 0]} className="cursor-pointer" onClick={d => onSelect((d as unknown as { payload: { site: Site } }).payload.site)}>
            {data.map(d => (
              <Cell key={d.id} fill={selected?.id === d.id ? "var(--selection)" : VERDICT[verdictOf(d.site)].color}
                stroke={selected?.id === d.id ? "var(--foreground)" : undefined} />
            ))}
            <LabelList dataKey="hours" position="right" fontSize={11} formatter={(v: unknown) => fmt(Number(v))} className="num fill-foreground" />
          </Bar>
        </BarChart>
      </ChartContainer>
      <figcaption className="flex flex-wrap items-center gap-x-5 gap-y-1 px-2 text-xs text-muted-foreground">
        {verdicts.length > 1 && verdicts.map(v => (
          <span key={v} className="flex items-center gap-1.5"><span aria-hidden className="size-2.5 rounded-sm" style={{ background: VERDICT[v].color }} />{VERDICT[v].label}</span>
        ))}
        <span>
          Click a bar or a name to open it on the map.
          {known.length > MAX_BARS && ` Showing the ${MAX_BARS} longest of ${known.length}.`}
          {sites.length > known.length && ` ${sites.length - known.length} with an unknown duration aren't shown.`}
        </span>
      </figcaption>
    </figure>
  )
}

const companyConfig = {
  dry: { label: "Dry-spill candidates", color: "var(--dry)" },
  other: { label: "Other spills", color: OTHER },
} satisfies ChartConfig

/** Spills per company in the last 48 h, dry candidates first. */
export function CompanyBars({ sites, active, onPick }: { sites: Site[]; active: string | null; onPick: (company: string) => void }) {
  const by = new Map<string, { company: string; dry: number; other: number }>()
  for (const s of sites) {
    const row = by.get(s.company) ?? { company: s.company, dry: 0, other: 0 }
    if (s.verdict === "dry_spill_candidate") row.dry++
    else row.other++
    by.set(s.company, row)
  }
  const data = [...by.values()].sort((a, b) => b.dry - a.dry || b.other - a.other)
  const pick = (d: unknown) => onPick((d as { payload: { company: string } }).payload.company)
  return (
    <figure className="grid gap-2 px-3 pb-5 md:px-5">
      <ChartContainer config={companyConfig} className="aspect-auto w-full" style={{ height: 56 + data.length * 40 }}>
        <BarChart data={data} layout="vertical" margin={{ top: 4, right: 16, left: 8, bottom: 0 }} barCategoryGap={8}>
          <CartesianGrid horizontal={false} strokeDasharray="2 3" />
          <XAxis type="number" allowDecimals={false} tickLine={false} axisLine={false} fontSize={11} />
          <YAxis type="category" dataKey="company" width={150} tickLine={false} axisLine={false} interval={0}
            tick={<ClickTick onPick={onPick} selected={active} />} />
          <ChartTooltip cursor={{ fill: "var(--muted)" }} content={<ChartTooltipContent />} />
          <ChartLegend content={<ChartLegendContent />} verticalAlign="top" />
          <Bar dataKey="dry" stackId="a" fill="var(--color-dry)" stroke="var(--background)" strokeWidth={2} radius={[4, 0, 0, 4]} className="cursor-pointer" onClick={pick} />
          <Bar dataKey="other" stackId="a" fill="var(--color-other)" stroke="var(--background)" strokeWidth={2} radius={[0, 4, 4, 0]} className="cursor-pointer" onClick={pick} />
        </BarChart>
      </ChartContainer>
      <figcaption className="px-2 text-xs text-muted-foreground">Click a bar or a company name to see its area on the map.</figcaption>
    </figure>
  )
}
