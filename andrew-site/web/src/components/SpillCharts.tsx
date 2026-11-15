// Two small charts for the dashboard: how long the dry spills lasted, and when the last 48 h of spills started.
import { Bar, BarChart, CartesianGrid, LabelList, XAxis, YAxis } from "recharts"
import { ChartContainer, ChartLegend, ChartLegendContent, ChartTooltip, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import type { Site } from "@/lib/data"

const BUCKETS: { label: string; test: (h: number) => boolean }[] = [
  { label: "Under 15 min", test: h => h < 0.25 },
  { label: "15–60 min", test: h => h >= 0.25 && h < 1 },
  { label: "1–3 h", test: h => h >= 1 && h < 3 },
  { label: "3–12 h", test: h => h >= 3 && h < 12 },
  { label: "12 h or more", test: h => h >= 12 },
]
const durationConfig = { n: { label: "Dry-spill candidates", color: "var(--dry)" } } satisfies ChartConfig

function durationData(sites: Site[]) {
  const dry = sites.filter(s => s.verdict === "dry_spill_candidate")
  return {
    data: BUCKETS.map(b => ({ bucket: b.label, n: dry.filter(s => s.hours != null && b.test(s.hours)).length })),
    unknown: dry.filter(s => s.hours == null).length,
    total: dry.length,
  }
}

export function DurationTable({ sites }: { sites: Site[] }) {
  const { data, unknown, total } = durationData(sites)
  const rows = unknown ? [...data, { bucket: "Unknown (monitor offline)", n: unknown }] : data
  return (
    <Table>
      <TableHeader className="bg-muted">
        <TableRow><TableHead className="pl-5 md:pl-6">Duration</TableHead><TableHead className="text-right">Dry-spill candidates</TableHead><TableHead className="pr-5 text-right md:pr-6">Share</TableHead></TableRow>
      </TableHeader>
      <TableBody>
        {rows.map(r => (
          <TableRow key={r.bucket}>
            <TableCell className="py-3 pl-5 md:pl-6">{r.bucket}</TableCell>
            <TableCell className="num py-3 text-right font-medium text-dry">{r.n}</TableCell>
            <TableCell className="num py-3 pr-5 text-right text-muted-foreground md:pr-6">{total ? Math.round((r.n / total) * 100) : 0}%</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}

/** One series (dry candidates), so no legend: the title names it. */
export function DurationChart({ sites }: { sites: Site[] }) {
  const { data, unknown } = durationData(sites)
  return (
    <figure className="grid gap-2">
      <ChartContainer config={durationConfig} className="aspect-auto h-64 w-full">
        <BarChart data={data} margin={{ top: 22, right: 8, left: -12, bottom: 0 }}>
          <CartesianGrid vertical={false} strokeDasharray="2 3" />
          <XAxis dataKey="bucket" tickLine={false} axisLine={false} fontSize={12} interval={0} />
          <YAxis allowDecimals={false} tickLine={false} axisLine={false} fontSize={11} />
          <ChartTooltip cursor={{ fill: "var(--muted)" }} content={<ChartTooltipContent />} />
          <Bar dataKey="n" fill="var(--color-n)" radius={[4, 4, 0, 0]} maxBarSize={64}>
            <LabelList dataKey="n" position="top" fontSize={12} className="num fill-foreground" />
          </Bar>
        </BarChart>
      </ChartContainer>
      <figcaption className="text-xs text-muted-foreground">
        Most dry-spill candidates are short. Only the ones lasting an hour or more are counted in the headline{unknown ? `; ${unknown} have an unknown duration (monitor offline)` : ""}.
      </figcaption>
    </figure>
  )
}

const startConfig = {
  dry: { label: "Dry-spill candidates", color: "var(--dry)" },
  other: { label: "Other spills", color: "#A3B1BE" },
} satisfies ChartConfig

function startBins(sites: Site[], runAt: string) {
  const end = new Date(runAt.replace(" ", "T")).getTime()
  const STEP = 4 * 3600_000, N = 12
  const bins = Array.from({ length: N }, (_, i) => {
    const t = new Date(end - (N - i) * STEP)
    return { t: +t, label: t.toLocaleString("en-GB", { weekday: "short", hour: "2-digit", minute: "2-digit" }), dry: 0, other: 0 }
  })
  for (const s of sites) {
    if (!s.start) continue
    const i = Math.floor((new Date(s.start.replace(" ", "T")).getTime() - (end - N * STEP)) / STEP)
    if (i < 0 || i >= N) continue
    if (s.verdict === "dry_spill_candidate") bins[i].dry++
    else bins[i].other++
  }
  return bins
}

export function StartTable({ sites, runAt }: { sites: Site[]; runAt: string }) {
  const bins = startBins(sites, runAt)
  return (
    <Table>
      <TableHeader className="bg-muted">
        <TableRow><TableHead className="pl-5 md:pl-6">4 hours from</TableHead><TableHead className="text-right">Dry-spill candidates</TableHead><TableHead className="pr-5 text-right md:pr-6">Other spills</TableHead></TableRow>
      </TableHeader>
      <TableBody>
        {bins.map(b => (
          <TableRow key={b.t}>
            <TableCell className="py-2.5 pl-5 md:pl-6">{b.label}</TableCell>
            <TableCell className="num py-2.5 text-right font-medium text-dry">{b.dry}</TableCell>
            <TableCell className="num py-2.5 pr-5 text-right md:pr-6">{b.other}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}

/** Spills started per 4-hour window over the 48 hours before the detector run. */
export function StartTimeline({ sites, runAt }: { sites: Site[]; runAt: string }) {
  const bins = startBins(sites, runAt)
  return (
    <figure className="grid gap-2">
      <ChartContainer config={startConfig} className="aspect-auto h-64 w-full">
        <BarChart data={bins} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
          <CartesianGrid vertical={false} strokeDasharray="2 3" />
          <XAxis dataKey="label" tickLine={false} axisLine={false} fontSize={11} interval={1} />
          <YAxis allowDecimals={false} tickLine={false} axisLine={false} fontSize={11} />
          <ChartTooltip cursor={{ fill: "var(--muted)" }} content={<ChartTooltipContent />} />
          <ChartLegend content={<ChartLegendContent />} />
          <Bar dataKey="dry" stackId="a" fill="var(--color-dry)" stroke="var(--background)" strokeWidth={1} />
          <Bar dataKey="other" stackId="a" fill="var(--color-other)" stroke="var(--background)" strokeWidth={1} radius={[4, 4, 0, 0]} />
        </BarChart>
      </ChartContainer>
      <figcaption className="text-xs text-muted-foreground">Spills that started in each 4-hour window, by verdict. Each overflow is counted once, at its latest spill.</figcaption>
    </figure>
  )
}
