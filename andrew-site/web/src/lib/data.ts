// Shapes of andrew-site/web/public/data/run.json (written by andrew-site/build.py) and small display helpers.

export type Verdict = "dry_spill_candidate" | "rain_explained" | "no_gauge"

export interface Gauge {
  station: string
  km: number
  lat?: number
  lon?: number
  mm_0_24h_before: number
  mm_24_48h_before: number
  mm_during: number
}

export interface Source { name?: string; url?: string }

export interface AgentCase {
  illustrative?: boolean
  site_id: string
  company: string
  event_start: string
  final_verdict: string
  breach_confidence: number
  skeptic_confidence?: number
  case?: { summary?: string; severity?: string; breach_indicators?: string[] }
  skeptic?: {
    model?: string
    breach_confidence?: number
    strongest_objection?: string
    innocent_explanations?: { explanation: string; plausibility: string }[]
  }
  evidence?: { report?: string; searches?: { query: string; answer?: string; sources?: Source[] }[] }
  ruling?: { final_confidence?: number; reasoning?: string; objections_refuted?: string[]; objections_standing?: string[] }
  report?: string
}

export interface Site {
  id: string
  company: string
  name: string
  lat: number
  lon: number
  verdict: Verdict
  hours: number | null // null = monitor offline, duration unknown
  ongoing: boolean
  offline: boolean
  start: string | null
  end: string | null
  rain48: number | null
  rainDuring: number | null
  gauges: Gauge[]
  case: AgentCase | null
}

export interface HistoryEvent { id: string; company: string; name: string; start: string; hours: number | null; verdict: Verdict }

export interface Run {
  run_at: string
  overflows: number | null
  recent_spills: number
  sites: Site[]
  history: { runs: string[]; events: HistoryEvent[] }
}

export const DRY_MM = 0.25 // detector threshold: under this in a 24 h window is a dry day
export const AREA_M = 10_000 // the detector checks rain gauges within 10 km
export const LONG_HOURS = 1 // spills shorter than this are shown as small dots, not counted in the headline

export const VERDICT: Record<Verdict, { label: string; short: string; color: string; rgb: [number, number, number] }> = {
  dry_spill_candidate: { label: "Dry spill candidate", short: "Dry", color: "var(--dry)", rgb: [200, 16, 46] },
  rain_explained: { label: "Rain explained", short: "Rain", color: "var(--rain)", rgb: [43, 108, 176] },
  no_gauge: { label: "No gauge within 10 km", short: "No gauge", color: "var(--nogauge)", rgb: [140, 140, 140] },
}
export const verdictOf = (s: Site): Verdict => (s.verdict in VERDICT ? s.verdict : "no_gauge")

export async function loadRun(): Promise<Run> {
  const r = await fetch("data/run.json", { cache: "no-store" })
  if (!r.ok) throw new Error(`couldn't load data/run.json (${r.status}). Run python andrew-site/build.py first.`)
  return r.json()
}

/** "HOLME FEN DRAIN" -> "Holme Fen Drain"; mixed-case names are left alone. */
export const titleCase = (s: string) => (s === s.toUpperCase() ? s.toLowerCase().replace(/\b\w/g, c => c.toUpperCase()) : s)
export const fmt = (x: number | null | undefined, d = 1) => (x == null ? "n/a" : x.toFixed(d))
export const hrs = (s: Site) => (s.hours == null ? "?" : fmt(s.hours))
export const pct = (x: number | null | undefined) => (x == null ? "n/a" : `${Math.round(x * 100)}%`)
export const isLong = (s: Site) => s.hours != null && s.hours >= LONG_HOURS
export const words = (s: string) => s.replace(/_/g, " ")

const asDate = (t: string) => new Date(String(t).replace(" ", "T"))
export function when(t: string | null | undefined, withDay = true) {
  if (!t) return "n/a"
  const d = asDate(t)
  if (isNaN(+d)) return String(t)
  return d.toLocaleString("en-GB", withDay ? { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" } : { hour: "2-digit", minute: "2-digit" })
}
export const day = (t: string) => {
  const d = asDate(t)
  return isNaN(+d) ? String(t) : d.toLocaleDateString("en-GB", { day: "numeric", month: "short" })
}

/** Longest first; unknown durations (monitor offline) last. */
export const byHours = (a: Site, b: Site) => (b.hours ?? -1) - (a.hours ?? -1)

/** Dry-spill candidates per overflow across detector runs, for "repeat site" badges. */
export function dryCounts(run: Run): Map<string, number> {
  const m = new Map<string, number>()
  for (const e of run.history.events) if (e.verdict === "dry_spill_candidate") m.set(e.id, (m.get(e.id) ?? 0) + 1)
  return m
}
