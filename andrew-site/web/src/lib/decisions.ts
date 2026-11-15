// Reviewer decisions (approve / reject / sent), stored in andrew-site/decisions.json by andrew-site/serve.py.
import type { AgentCase, Site } from "./data"

export type DecisionStatus = "draft" | "approved" | "rejected" | "sent"
export interface Decision {
  status: DecisionStatus
  log: { status: DecisionStatus; by: string; at: string; note: string }[]
  report?: string
  approved_by?: string
  approved_at?: string
  rejected_by?: string
  rejected_at?: string
  reason?: string
  sent_by?: string
  sent_at?: string
  sent_note?: string
}
export type Decisions = Record<string, Decision>

export const caseKey = (c: AgentCase) => `${c.site_id}|${c.event_start}`
export const EMPTY: Decision = { status: "draft", log: [] }
export const decisionOf = (s: Site, d: Decisions): Decision => (s.case && d[caseKey(s.case)]) || EMPTY

/** null when serve.py isn't running (page opened from another static server): read-only mode. */
export async function fetchDecisions(): Promise<Decisions | null> {
  try {
    const r = await fetch("/api/decisions")
    return r.ok ? await r.json() : null
  } catch {
    return null
  }
}

export async function postDecision(s: Site, status: DecisionStatus, reviewer: string, note: string, report: string): Promise<Decisions> {
  const c = s.case!
  const r = await fetch("/api/decisions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ key: caseKey(c), status, reviewer, note, report, site_id: c.site_id,
      event_start: c.event_start, company: s.company, illustrative: !!c.illustrative }),
  })
  const body = await r.json()
  if (!r.ok) throw new Error(body.error || "Couldn't save")
  return body
}

// ---- Pipeline stage for each site ----
export type Stage = "new" | "innocent" | "review" | "drafted" | "approved" | "sent" | "rejected"
export const STAGE: Record<Stage, { label: string; className: string }> = {
  new: { label: "New", className: "border-dry text-dry bg-transparent" },
  innocent: { label: "Ruled innocent", className: "border-border text-muted-foreground bg-muted" },
  review: { label: "Needs review", className: "border-selection bg-selection/25 text-foreground" },
  drafted: { label: "Report drafted", className: "border-primary bg-primary text-primary-foreground" },
  approved: { label: "Approved", className: "border-approved bg-approved text-white" },
  sent: { label: "Sent", className: "border-foreground bg-foreground text-background" },
  rejected: { label: "Rejected", className: "border-border bg-muted text-muted-foreground line-through decoration-1" },
}

export function stageOf(s: Site, d: Decisions): Stage | null {
  if (!s.case) return s.verdict === "dry_spill_candidate" ? "new" : null
  const st = decisionOf(s, d).status
  if (st === "approved" || st === "sent" || st === "rejected") return st
  if (s.case.final_verdict === "likely_innocent") return "innocent"
  return s.case.report ? "drafted" : "review"
}
