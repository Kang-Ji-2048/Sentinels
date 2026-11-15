import { useEffect, useMemo, useRef, useState, type ReactNode } from "react"
import { ChevronUp, Map as MapIcon, TriangleAlert } from "lucide-react"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"
import { Switch } from "@/components/ui/switch"
import { Toaster } from "@/components/ui/sonner"
import { TooltipProvider } from "@/components/ui/tooltip"
import { cn } from "@/lib/utils"
import { LONG_HOURS, VERDICT, byHours, dryCounts, isLong, loadRun, titleCase, when, type Run, type Site } from "@/lib/data"
import { fetchDecisions, stageOf, type Decisions } from "@/lib/decisions"
import { AreaSummary } from "@/components/AreaSummary"
import { CaseDetail, CaseSheet, type CaseTab } from "@/components/CaseSheet"
import { CompanyTable } from "@/components/CompanyTable"
import { CompanyBars, SpillBars } from "@/components/DashboardCharts"
import { DEFAULT_FILTERS, FilterBar, type Filters } from "@/components/FilterBar"
import { PipelineStrip, type Filter, type Step } from "@/components/PipelineStrip"
import { ReportsView } from "@/components/ReportsView"
import { DurationChart, DurationTable, StartTable, StartTimeline } from "@/components/SpillCharts"
import { SpillMap } from "@/components/SpillMap"
import { SpillTable } from "@/components/SpillTable"
import { ViewToggle, type PanelView } from "@/components/ViewToggle"
import { Swatch } from "@/components/badges"

type View = "overview" | "reports"
const viewFromHash = (): View => (location.hash === "#reports" ? "reports" : "overview")
const smooth = () => (window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth")

const FILTER_TITLE: Record<Filter, string> = {
  spills: "All spills, last 48 h",
  dry: "All dry-spill candidates",
  long: `Dry spills of ${LONG_HOURS} h or more`,
  investigated: "Investigated by the agents",
  drafted: "Report drafted, awaiting review",
  approved: "Approved reports",
  sent: "Reports sent",
}

function Panel({ title, description, action, children, className }: {
  title: string; description?: ReactNode; action?: ReactNode; children: ReactNode; className?: string
}) {
  return (
    <section className={cn("overflow-hidden rounded-xl border bg-background shadow-sm", className)}>
      <div className="flex flex-col gap-3 px-5 pt-5 pb-4 sm:flex-row sm:items-start sm:justify-between md:px-6">
        <div className="grid min-w-0 flex-1 gap-1">
          <h2 className="text-lg font-semibold">{title}</h2>
          {description && <p className="text-sm text-muted-foreground">{description}</p>}
        </div>
        {action}
      </div>
      {children}
    </section>
  )
}

export default function App() {
  const [run, setRun] = useState<Run | null>(null)
  const [error, setError] = useState("")
  const [decisions, setDecisions] = useState<Decisions>({})
  const [api, setApi] = useState(false)
  const [view, setView] = useState<View>(viewFromHash)
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS)
  const [mapOpen, setMapOpen] = useState(false)
  const [showContext, setShowContext] = useState(true)
  const [selected, setSelected] = useState<Site | null>(null)
  const [tab, setTab] = useState<CaseTab>("evidence")
  // Table or chart for each dashboard panel
  const [views, setViews] = useState<Record<"spills" | "companies" | "duration" | "starts", PanelView>>(
    { spills: "table", companies: "table", duration: "chart", starts: "chart" })
  const toggle = (k: keyof typeof views, label: string) =>
    <ViewToggle label={label} value={views[k]} onChange={v => setViews(cur => ({ ...cur, [k]: v }))} />
  const mapRef = useRef<HTMLElement>(null)
  const [scrollToMap, setScrollToMap] = useState(0)

  useEffect(() => {
    loadRun().then(setRun, e => setError(String(e.message || e)))
    fetchDecisions().then(d => { if (d) { setDecisions(d); setApi(true) } })
    const onHash = () => setView(viewFromHash())
    window.addEventListener("hashchange", onHash)
    return () => window.removeEventListener("hashchange", onHash)
  }, [])

  // After the map section opens (or is asked for again), bring it into view below the filter bar.
  useEffect(() => {
    if (scrollToMap) requestAnimationFrame(() => mapRef.current?.scrollIntoView({ behavior: smooth(), block: "start" }))
  }, [scrollToMap])

  const derived = useMemo(() => {
    if (!run) return null
    const dry = run.sites.filter(s => s.verdict === "dry_spill_candidate").sort(byHours)
    const long = dry.filter(isLong)
    const shortDry = dry.filter(s => s.hours != null && s.hours < LONG_HOURS).length
    const unknownDry = dry.filter(s => s.hours == null).length
    const cased = run.sites.filter(s => s.case)
    const stage = (s: Site) => stageOf(s, decisions)
    const lists: Record<Filter, Site[]> = {
      spills: [...run.sites].sort(byHours),
      dry,
      long,
      investigated: cased.sort(byHours),
      drafted: cased.filter(s => stage(s) === "drafted"),
      approved: cased.filter(s => stage(s) === "approved" || stage(s) === "sent"),
      sent: cased.filter(s => stage(s) === "sent"),
    }
    const steps: Step[] = [
      { key: null, label: "overflows monitored", value: run.overflows, hint: "Storm overflows in the water companies' live feeds" },
      { key: "spills", label: "spills started, last 48 h", value: run.recent_spills, hint: "Overflows whose latest spill began in the last 48 hours" },
      { key: "dry", label: "with no rain nearby", value: dry.length, hint: "No gauge within 10 km had 0.25 mm or more in either 24 h window before", dry: true },
      { key: "long", label: `lasting ${LONG_HOURS} h or more`, value: long.length, hint: "Dry-spill candidates that discharged for at least an hour", dry: true },
      { key: "investigated", label: "investigated by agents", value: cased.length, hint: "Investigator, skeptic, evidence agent and adjudicator have run" },
      { key: "drafted", label: "reports awaiting review", value: lists.drafted.length, hint: "Evidence packs drafted, waiting for a person" },
      { key: "approved", label: "approved by a person", value: lists.approved.length, hint: "Approved evidence packs" },
      { key: "sent", label: "sent to the EA", value: lists.sent.length, hint: "Packs a person has sent" },
    ]
    const companies = [...new Set(run.sites.map(s => s.company))].sort()
    return { dry, long, shortDry, unknownDry, lists, steps, companies, repeats: dryCounts(run) }
  }, [run, decisions])

  // Sites in scope for the charts and the map: company, search and "still discharging" apply; the stage picks the list.
  const scope = useMemo(() => {
    if (!run) return []
    const q = filters.search.trim().toLowerCase()
    return run.sites.filter(s => (!filters.company || s.company === filters.company) && (!filters.ongoing || s.ongoing)
      && (!q || s.name.toLowerCase().includes(q) || s.id.toLowerCase().includes(q)))
  }, [run, filters.company, filters.ongoing, filters.search])
  const scopeIds = useMemo(() => new Set(scope.map(s => s.id)), [scope])
  const focus = useMemo(() => (filters.company || filters.search.trim() ? scope : null), [scope, filters.company, filters.search])

  function go(v: View) {
    setView(v)
    history.replaceState(null, "", `#${v}`)
  }
  /** Open a site's case beside the map, opening the map and scrolling to it. */
  function openSite(s: Site | null, t: CaseTab = "evidence", scroll = true) {
    setSelected(cur => (s && cur?.id === s.id ? cur : s))
    setTab(t)
    if (s) { setMapOpen(true); if (scroll) setScrollToMap(n => n + 1) }
  }
  function openCompany(c: string) {
    setFilters(f => ({ ...f, company: f.company === c ? null : c }))
    setSelected(null)
    setMapOpen(true)
    setScrollToMap(n => n + 1)
  }

  if (error) return (
    <div className="grid min-h-svh place-items-center p-6">
      <Alert className="max-w-lg"><TriangleAlert aria-hidden /><AlertTitle>No data</AlertTitle><AlertDescription>{error}</AlertDescription></Alert>
    </div>
  )

  const list = derived ? derived.lists[filters.stage].filter(s => scopeIds.has(s.id)) : []
  const areaTitle = filters.company ?? (filters.search.trim() ? `Sites matching "${filters.search.trim()}"` : "All of England")
  const caseProps = run && { run, tab, onTab: setTab, decisions, api, onDecisions: setDecisions }

  return (
    <TooltipProvider delayDuration={200}>
      <div className="flex h-svh flex-col bg-background">
        <header className="flex h-14 shrink-0 items-center justify-between gap-4 border-b bg-background px-4 text-muted-foreground md:px-7">
          <div className="flex items-center gap-6">
            <span className="font-logo text-[22px] font-extrabold tracking-[-0.04em] text-primary">Sentinels</span>
            <nav aria-label="Views" className="flex h-14">
              {(["overview", "reports"] as View[]).map(v => (
                <a key={v} href={`#${v}`} aria-current={view === v ? "page" : undefined}
                  onClick={e => { e.preventDefault(); go(v) }}
                  className={cn("flex items-center border-b-4 border-transparent px-3 pt-1 text-sm font-medium capitalize hover:text-foreground",
                    view === v && "border-selection font-semibold text-primary")}>
                  {v}
                </a>
              ))}
            </nav>
          </div>
          <div className="flex items-center gap-3 text-sm">
            {!api && run && <span className="hidden rounded border px-2 py-0.5 text-xs sm:inline">Read-only</span>}
            {run && <span className="hidden sm:inline">Data from {when(run.run_at)}</span>}
          </div>
        </header>

        {!run || !derived || !caseProps ? (
          <div className="grid gap-4 p-6"><Skeleton className="h-16 w-full" /><Skeleton className="h-[60vh] w-full" /></div>
        ) : view === "reports" ? (
          <main className="min-h-0 flex-1 overflow-y-auto bg-muted/40">
            <ReportsView run={run} decisions={decisions} onOpen={s => { setSelected(s); setTab(s.case?.report ? "report" : "agents") }} />
          </main>
        ) : (
          <main className="min-h-0 flex-1 overflow-y-auto bg-muted/40">
            <div className="mx-auto grid w-full max-w-[1440px] gap-8 px-4 pb-10 md:gap-10 md:px-8">
              {/* Headline + pipeline */}
              <section aria-labelledby="headline" className="grid gap-6 pt-6 md:pt-10">
                <div className="flex flex-wrap items-end gap-x-6 gap-y-2">
                  <span className="num text-7xl leading-none font-bold tracking-tight text-dry">{derived.long.length}</span>
                  <div className="grid max-w-[70ch] gap-1 pb-1">
                    <h1 id="headline" className="text-2xl font-semibold tracking-tight">dry spills lasting {LONG_HOURS} hour or more, in the last 48 hours</h1>
                    <p className="text-muted-foreground">
                      No meaningful rain at any gauge within 10 km. {derived.dry.length} candidates in all: {derived.shortDry} lasted under an hour{derived.unknownDry ? `, ${derived.unknownDry} unknown (monitor offline)` : ""}.
                    </p>
                  </div>
                </div>
                <PipelineStrip steps={derived.steps} active={filters.stage} onPick={f => setFilters(cur => ({ ...cur, stage: f }))} />
              </section>

              <FilterBar filters={filters} onChange={setFilters} companies={derived.companies} stageTitles={FILTER_TITLE} shown={list.length} />

              {/* Tables / charts */}
              <div className="grid items-start gap-8 xl:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
                <Panel title={FILTER_TITLE[filters.stage]}
                  description={<>Click a site to open its case beside the map. <span className="num">{list.length}</span> shown{filters.company ? ` for ${filters.company}` : ""}.</>}
                  action={toggle("spills", "dry spills")}>
                  <div className={cn("max-h-[560px] overflow-y-auto border-t", views.spills === "chart" && "pt-4")}>
                    {views.spills === "table"
                      ? <SpillTable sites={list} selected={selected} decisions={decisions} repeats={derived.repeats} onSelect={s => openSite(s)}
                          empty="Nothing matches these filters." />
                      : <SpillBars sites={list} selected={selected} onSelect={s => openSite(s)} />}
                  </div>
                </Panel>
                <Panel title="By water company" description="Spills started in the last 48 h. Click a company to see its area on the map."
                  action={toggle("companies", "water companies")}>
                  {views.companies === "table"
                    ? <CompanyTable sites={run.sites} active={filters.company} onPick={openCompany} />
                    : <CompanyBars sites={run.sites} active={filters.company} onPick={openCompany} />}
                </Panel>
              </div>

              <div className="grid gap-8 lg:grid-cols-2">
                <Panel title="How long the dry spills lasted" description="Dry-spill candidates by duration, within the filters." action={toggle("duration", "durations")}>
                  {views.duration === "chart"
                    ? <div className="px-3 pb-5 md:px-5"><DurationChart sites={scope} /></div>
                    : <DurationTable sites={scope} />}
                </Panel>
                <Panel title="When spills started" description="Over the 48 hours before the detector run, within the filters." action={toggle("starts", "spill start times")}>
                  {views.starts === "chart"
                    ? <div className="px-3 pb-5 md:px-5"><StartTimeline sites={scope} runAt={run.run_at} /></div>
                    : <div className="max-h-[360px] overflow-y-auto"><StartTable sites={scope} runAt={run.run_at} /></div>}
                </Panel>
              </div>

              {/* Map (half width) with the case or area details beside it */}
              <section ref={mapRef} id="map" aria-labelledby="map-h" className="grid scroll-mt-24 gap-4">
                <div className="flex flex-wrap items-end justify-between gap-3">
                  <div className="grid gap-1">
                    <h2 id="map-h" className="text-2xl font-semibold tracking-tight">
                      Map{mapOpen && <span className="font-normal text-muted-foreground"> · {selected ? titleCase(selected.name) : areaTitle}</span>}
                    </h2>
                    <p className="text-muted-foreground">
                      {mapOpen ? "Columns are spills of an hour or more (height = hours discharging); shorter spills are dots." : "Click a site or a water company above to open it here, or open the full map."}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {mapOpen && (selected || filters.company) && (
                      <Button variant="outline" onClick={() => { setSelected(null); setFilters(f => ({ ...f, company: null })) }}>Show all of England</Button>
                    )}
                    <Button variant={mapOpen ? "ghost" : "default"} onClick={() => { setMapOpen(o => !o); if (!mapOpen) setScrollToMap(n => n + 1) }}>
                      {mapOpen ? <><ChevronUp aria-hidden />Hide map</> : <><MapIcon aria-hidden />Open the map</>}
                    </Button>
                  </div>
                </div>
                {mapOpen ? (
                  <>
                    <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-sm">
                      {Object.values(VERDICT).map(v => (
                        <span key={v.label} className="flex items-center gap-2"><Swatch color={v.color} />{v.label}</span>
                      ))}
                      <span className="ml-auto flex items-center gap-2">
                        <Switch id="context" checked={showContext} onCheckedChange={setShowContext} />
                        <Label htmlFor="context" className="text-sm font-normal">Show rain-explained and no-gauge spills</Label>
                      </span>
                    </div>
                    <div className="grid gap-6 lg:grid-cols-2">
                      <div className="relative h-[60vh] min-h-[420px] overflow-hidden rounded-xl border bg-background shadow-sm lg:h-[680px]">
                        <SpillMap sites={scope} selected={selected} focus={focus} showContext={showContext} onSelect={s => openSite(s, "evidence", false)} />
                      </div>
                      <aside aria-label={selected ? "Case details" : "Area summary"}
                        className="overflow-hidden rounded-xl border bg-background shadow-sm lg:h-[680px]">
                        {selected
                          ? <CaseDetail site={selected} {...caseProps} onClose={() => setSelected(null)} />
                          : <AreaSummary title={areaTitle} sites={scope} onSelect={s => openSite(s, "evidence", false)} />}
                      </aside>
                    </div>
                  </>
                ) : (
                  <button onClick={() => { setMapOpen(true); setScrollToMap(n => n + 1) }}
                    className="flex h-40 flex-col items-center justify-center gap-2 rounded-xl border border-dashed bg-background/60 text-muted-foreground transition-colors hover:border-primary/60 hover:text-foreground">
                    <MapIcon aria-hidden className="size-6" />
                    <span className="font-medium">Open the map of {scope.length} spills</span>
                  </button>
                )}
              </section>

              <p className="text-center text-xs text-muted-foreground">A candidate, not proof. Spill data is self-reported by the water companies and gauges are sparse. A person approves every report before it is sent.</p>
            </div>
          </main>
        )}
      </div>
      {caseProps && <CaseSheet site={view === "reports" ? selected : null} {...caseProps} onClose={() => setSelected(null)} />}
      <Toaster position="bottom-center" richColors={false} />
    </TooltipProvider>
  )
}
