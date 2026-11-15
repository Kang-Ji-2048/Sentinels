// One spill, end to end: the rain evidence, the agents' case, and the report a person approves and sends.
// CaseDetail is the content (shown beside the map); CaseSheet wraps it in a side sheet for the Reports page.
import { useState } from "react"
import { X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { DRY_MM, fmt, hrs, titleCase, verdictOf, when, type Run, type Site } from "@/lib/data"
import { stageOf, type Decisions } from "@/lib/decisions"
import { AgentThread } from "./AgentThread"
import { EvidenceChart, GaugeTable } from "./EvidenceChart"
import { ReportPanel } from "./ReportPanel"
import { ViewToggle, type PanelView } from "./ViewToggle"
import { StageBadge, VerdictBadge } from "./badges"

export type CaseTab = "evidence" | "agents" | "report"

interface CaseProps {
  run: Run; site: Site; tab: CaseTab; onTab: (t: CaseTab) => void
  decisions: Decisions; api: boolean; onDecisions: (d: Decisions) => void
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid gap-0.5">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="num text-sm font-medium">{value}</dd>
    </div>
  )
}

function verdictLine(s: Site) {
  if (!s.gauges.length) return "No rain gauge within 10 km, so the detector can't tell whether it rained."
  const w24 = Math.max(...s.gauges.map(g => g.mm_0_24h_before)), w48 = Math.max(...s.gauges.map(g => g.mm_24_48h_before))
  const n = s.gauges.length
  return s.verdict === "dry_spill_candidate"
    ? `All ${n} gauge${n > 1 ? "s" : ""} within 10 km stayed under ${DRY_MM} mm in both 24-hour windows before the spill (wettest: ${fmt(w48, 2)} mm 24–48 h before, ${fmt(w24, 2)} mm 0–24 h before).`
    : `At least one gauge within 10 km recorded ${DRY_MM} mm or more in a 24-hour window before the spill (wettest: ${fmt(w48, 2)} mm 24–48 h before, ${fmt(w24, 2)} mm 0–24 h before), so rain may explain it.`
}

function Header({ site, decisions, Title, Description }: {
  site: Site; decisions: Decisions; Title: React.ElementType; Description: React.ElementType
}) {
  const stage = stageOf(site, decisions)
  return (
    <>
      <div className="flex flex-wrap gap-1.5">
        <VerdictBadge verdict={verdictOf(site)} />
        {stage && <StageBadge stage={stage} />}
      </div>
      <Title className="text-xl font-semibold">{titleCase(site.name)}</Title>
      <Description className="text-sm text-muted-foreground">{site.company} · overflow {site.id}</Description>
      <dl className="mt-1 grid grid-cols-3 gap-3">
        <Fact label="Started" value={when(site.start)} />
        <Fact label="Discharging" value={site.hours == null ? "unknown (monitor offline)" : `${hrs(site)} h${site.ongoing ? ", still going" : ""}`} />
        <Fact label="Wettest gauge, 48 h" value={site.rain48 == null ? "no gauge" : `${fmt(site.rain48, 2)} mm`} />
      </dl>
    </>
  )
}

function Body({ run, site, tab, onTab, decisions, api, onDecisions }: CaseProps) {
  const [evidenceView, setEvidenceView] = useState<PanelView>("chart")
  return (
    <Tabs value={tab} onValueChange={v => onTab(v as CaseTab)} className="flex min-h-0 flex-1 flex-col gap-0">
      <TabsList className="mx-5 mt-4 grid w-auto shrink-0 grid-cols-3">
        <TabsTrigger value="evidence">Rain evidence</TabsTrigger>
        <TabsTrigger value="agents">Agents</TabsTrigger>
        <TabsTrigger value="report">Report &amp; send</TabsTrigger>
      </TabsList>
      <div className="min-h-0 flex-1 overflow-y-auto p-5">
        <TabsContent value="evidence" className="grid gap-4">
          <p className="text-sm leading-relaxed">{verdictLine(site)}</p>
          {site.gauges.length > 0 && (
            <div className="flex justify-end"><ViewToggle label="rain evidence" value={evidenceView} onChange={setEvidenceView} /></div>
          )}
          {evidenceView === "chart" ? <EvidenceChart site={site} /> : <GaugeTable site={site} />}
          <p className="text-xs text-muted-foreground">A candidate, not proof. Spill data is self-reported by the water company and rain gauges are sparse.</p>
        </TabsContent>
        <TabsContent value="agents"><AgentThread k={site.case} /></TabsContent>
        <TabsContent value="report">
          <ReportPanel key={site.id} run={run} site={site} decisions={decisions} api={api} onDecisions={onDecisions} />
        </TabsContent>
      </div>
    </Tabs>
  )
}

/** Inline case panel, e.g. beside the map. */
export function CaseDetail(props: CaseProps & { onClose: () => void }) {
  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="relative grid gap-2 border-b p-5 pr-12">
        <Header site={props.site} decisions={props.decisions} Title="h3" Description="p" />
        <Button variant="ghost" size="icon" className="absolute top-3 right-3" onClick={props.onClose} aria-label="Close this case">
          <X aria-hidden />
        </Button>
      </div>
      <Body {...props} />
    </div>
  )
}

/** The same case in a side sheet (used from the Reports page). */
export function CaseSheet({ site, onClose, ...rest }: Omit<CaseProps, "site"> & { site: Site | null; onClose: () => void }) {
  return (
    <Sheet open={!!site} onOpenChange={o => !o && onClose()}>
      <SheetContent side="right" className="w-full gap-0 p-0 data-[side=right]:w-full data-[side=right]:sm:max-w-[600px]">
        {site && <>
          <SheetHeader className="gap-2 border-b p-5 pr-12">
            <Header site={site} decisions={rest.decisions} Title={SheetTitle} Description={SheetDescription} />
          </SheetHeader>
          <Body site={site} {...rest} />
        </>}
      </SheetContent>
    </Sheet>
  )
}
