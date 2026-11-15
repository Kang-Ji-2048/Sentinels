// The agents' case, in the order it happened. All text is model or web output, rendered as plain text only.
import type { ReactNode } from "react"
import { Bot, ExternalLink, Gavel, Globe, ShieldQuestion, TriangleAlert } from "lucide-react"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Separator } from "@/components/ui/separator"
import { pct, words, type AgentCase, type Source } from "@/lib/data"

function Turn({ icon: Icon, who, meta, children }: { icon: typeof Bot; who: string; meta?: string; children?: ReactNode }) {
  return (
    <section className="grid gap-2 py-4">
      <h4 className="flex flex-wrap items-baseline gap-x-2 text-sm">
        <Icon aria-hidden className="size-4 translate-y-0.5 text-primary" />
        <span className="font-semibold text-primary">{who}</span>
        {meta && <span className="text-muted-foreground">{meta}</span>}
      </h4>
      <div className="grid gap-2 pl-6 text-sm leading-relaxed">{children}</div>
    </section>
  )
}
const List = ({ items }: { items?: string[] }) =>
  items?.length ? <ul className="grid list-disc gap-1 pl-4 marker:text-muted-foreground">{items.map((x, i) => <li key={i}>{x}</li>)}</ul> : null

function SourceLink({ src }: { src: Source }) {
  if (!/^https?:\/\//.test(src.url ?? "")) return <span>{src.name}</span>
  return (
    <a href={src.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-primary underline-offset-4 hover:underline">
      {src.name || src.url}<ExternalLink aria-hidden className="size-3" />
    </a>
  )
}

/** How far the evidence moved the case: hollow dot = the skeptic's view, solid = the final call. */
export function Swing({ from, to }: { from: number; to: number }) {
  const at = (x: number) => `${x * 100}%`
  return (
    <div className="grid gap-1.5">
      <div className="relative h-6" role="img" aria-label={`Skeptic ${pct(from)}, final ${pct(to)} confident this is a genuine dry-day spill`}>
        <div className="absolute inset-x-0 top-[11px] h-0.5 rounded bg-border" />
        {[0.4, 0.65].map(t => <div key={t} className="absolute top-1 h-4 w-px bg-muted-foreground/60" style={{ left: at(t) }} />)}
        <div className="absolute top-2.5 h-1 rounded bg-primary" style={{ left: at(Math.min(from, to)), width: at(Math.abs(to - from)) }} />
        <div className="absolute top-1.5 size-3 -translate-x-1/2 rounded-full border-2 border-primary bg-background" style={{ left: at(from) }} />
        <div className="absolute top-1.5 size-3 -translate-x-1/2 rounded-full border-2 border-primary bg-primary" style={{ left: at(to) }} />
      </div>
      <div className="flex justify-between text-xs text-muted-foreground">
        <span>0%</span><span>40% needs review · 65% likely breach</span><span>100%</span>
      </div>
    </div>
  )
}

export function AgentThread({ k }: { k: AgentCase | null }) {
  if (!k) return <p className="text-sm text-muted-foreground">No agent has investigated this spill yet. Run scripts/agents.py to investigate the top candidates.</p>
  const searches = k.evidence?.searches ?? []
  return (
    <div>
      {k.illustrative && (
        <Alert className="mb-2 border-2 border-dashed border-dry">
          <TriangleAlert aria-hidden className="text-dry" />
          <AlertTitle>Example conversation</AlertTitle>
          <AlertDescription>Made up to show how a case will look. No agent has run on this site, and none of the text below is real.</AlertDescription>
        </Alert>
      )}
      <div className="grid gap-3 rounded-lg border bg-muted/50 p-4">
        <p className="text-sm">
          Agents' verdict: <b className="font-semibold capitalize">{words(k.final_verdict)}</b>, {pct(k.breach_confidence)} confident it's a genuine dry-day spill
        </p>
        {typeof k.skeptic_confidence === "number" && <Swing from={k.skeptic_confidence} to={k.breach_confidence} />}
      </div>
      {k.case && <Turn icon={Bot} who="Investigator" meta={k.case.severity && `severity ${k.case.severity}`}>
        {k.case.summary && <p>{k.case.summary}</p>}<List items={k.case.breach_indicators} />
      </Turn>}
      {k.skeptic && <><Separator /><Turn icon={ShieldQuestion} who="Skeptic" meta={`${k.skeptic.model || "model unknown"} · ${pct(k.skeptic.breach_confidence)} genuine`}>
        {k.skeptic.strongest_objection && <p>{k.skeptic.strongest_objection}</p>}
        <List items={k.skeptic.innocent_explanations?.map(x => `${x.explanation} (${x.plausibility} plausibility)`)} />
      </Turn></>}
      <Separator />
      {k.evidence ? (
        <Turn icon={Globe} who="Evidence agent" meta={`${searches.length} web searches`}>
          {k.evidence.report && <p className="whitespace-pre-wrap">{k.evidence.report}</p>}
          {searches.map((q, i) => (
            <details key={i} className="rounded-md border bg-background px-3 py-2">
              <summary className="cursor-pointer font-medium">{q.query}</summary>
              {q.answer && <p className="mt-2">{q.answer}</p>}
              {!!q.sources?.length && <ul className="mt-2 grid gap-1">{q.sources.map((s, j) => <li key={j}><SourceLink src={s} /></li>)}</ul>}
            </details>
          ))}
        </Turn>
      ) : <Turn icon={Globe} who="Evidence agent"><p className="text-muted-foreground">Not run: the skeptic dismissed the case before any web search.</p></Turn>}
      {k.ruling && <><Separator /><Turn icon={Gavel} who="Adjudicator" meta={`${pct(k.ruling.final_confidence)} genuine`}>
        {k.ruling.reasoning && <p>{k.ruling.reasoning}</p>}
        <List items={k.ruling.objections_refuted?.map(x => `Refuted: ${x}`)} />
        <List items={k.ruling.objections_standing?.map(x => `Still standing: ${x}`)} />
      </Turn></>}
    </div>
  )
}
