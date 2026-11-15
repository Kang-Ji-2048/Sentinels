// The rain evidence for one spill: each nearby gauge's rainfall in the two 24 h windows before the spill and
// during it, against the 0.25 mm dry-day line. Bars under the line in both "before" windows = a dry day.
import { Bar, BarChart, CartesianGrid, LabelList, ReferenceLine, XAxis, YAxis } from "recharts"
import { ExternalLink } from "lucide-react"
import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { DRY_MM, fmt, type Site } from "@/lib/data"
import { gaugeUrl } from "@/lib/pack"

// One hue, light -> dark, in time order: earliest window first.
const SERIES = [
  { key: "before48", label: "24–48 h before", color: "#9DB9D8" },
  { key: "before24", label: "0–24 h before", color: "#4C7DB3" },
  { key: "during", label: "During the spill", color: "#12355B" },
] as const
const config = Object.fromEntries(SERIES.map(s => [s.key, { label: s.label, color: s.color }])) satisfies ChartConfig

export function NoGauge() {
  return <p className="text-sm text-muted-foreground">No Environment Agency rain gauge within 10 km, so rain can't be ruled in or out.</p>
}

export function EvidenceChart({ site }: { site: Site }) {
  if (!site.gauges.length) return <NoGauge />
  const data = site.gauges.map(g => ({ gauge: `${g.station} · ${fmt(g.km)} km`, before48: g.mm_24_48h_before, before24: g.mm_0_24h_before, during: g.mm_during }))
  const top = Math.max(DRY_MM * 2, ...data.flatMap(d => [d.before48, d.before24, d.during])) * 1.25
  const label = (v: unknown) => fmt(Number(v), 2)
  return (
    <figure className="grid gap-3">
      <ChartContainer config={config} className="aspect-auto h-64 w-full">
        <BarChart data={data} margin={{ top: 20, right: 8, left: 4, bottom: 0 }} barGap={3} barCategoryGap="20%">
          <CartesianGrid vertical={false} strokeDasharray="2 3" />
          <XAxis dataKey="gauge" tickLine={false} axisLine={false} fontSize={11} interval={0} />
          <YAxis domain={[0, top]} tickLine={false} axisLine={false} fontSize={11} unit=" mm" width={64} tickFormatter={v => Number(v).toFixed(2)} />
          <ChartTooltip cursor={{ fill: "var(--muted)" }} content={<ChartTooltipContent formatter={(v, name) => (
            <span className="flex w-full justify-between gap-3"><span className="text-muted-foreground">{config[name as keyof typeof config]?.label}</span><b className="num">{label(v)} mm</b></span>
          )} />} />
          <ReferenceLine y={DRY_MM} stroke="var(--foreground)" strokeDasharray="5 4" ifOverflow="extendDomain" />
          {SERIES.map(s => (
            <Bar key={s.key} dataKey={s.key} fill={s.color} radius={[4, 4, 0, 0]} minPointSize={2}>
              <LabelList dataKey={s.key} position="top" fontSize={10} formatter={label} className="num fill-muted-foreground" />
            </Bar>
          ))}
        </BarChart>
      </ChartContainer>
      {/* Legend in time order, with the threshold line as its own key item (kept off the plot so it never covers a value). */}
      <figcaption className="flex flex-wrap items-center justify-center gap-x-5 gap-y-1.5 text-xs">
        {SERIES.map(s => (
          <span key={s.key} className="flex items-center gap-1.5"><span aria-hidden className="size-2.5 rounded-sm" style={{ background: s.color }} />{s.label}</span>
        ))}
        <span className="flex items-center gap-1.5"><span aria-hidden className="w-5 border-t-2 border-dashed border-foreground" />Dry-day line, {DRY_MM} mm</span>
      </figcaption>
    </figure>
  )
}

export function GaugeTable({ site }: { site: Site }) {
  if (!site.gauges.length) return <NoGauge />
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Gauge</TableHead>
          <TableHead className="text-right">Distance</TableHead>
          <TableHead className="text-right">24–48 h before</TableHead>
          <TableHead className="text-right">0–24 h before</TableHead>
          <TableHead className="text-right">During</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {site.gauges.map(g => {
          const cell = (mm: number) => <span className={mm >= DRY_MM ? "font-semibold" : undefined}>{fmt(mm, 2)} mm</span>
          return (
            <TableRow key={g.station}>
              <TableCell>
                <a href={gaugeUrl(g.station)} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 font-medium text-primary underline-offset-4 hover:underline">
                  {g.station}<ExternalLink aria-hidden className="size-3" /><span className="sr-only">(EA data, opens in a new tab)</span>
                </a>
              </TableCell>
              <TableCell className="num text-right">{fmt(g.km)} km</TableCell>
              <TableCell className="num text-right">{cell(g.mm_24_48h_before)}</TableCell>
              <TableCell className="num text-right">{cell(g.mm_0_24h_before)}</TableCell>
              <TableCell className="num text-right">{fmt(g.mm_during, 2)} mm</TableCell>
            </TableRow>
          )
        })}
      </TableBody>
    </Table>
  )
}
