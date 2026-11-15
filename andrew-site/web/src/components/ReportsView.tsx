// Every case the agents have looked at, with where the report has got to, plus overflows that keep spilling dry.
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { day, fmt, hrs, pct, titleCase, words, type HistoryEvent, type Run, type Site } from "@/lib/data"
import { stageOf, type Decisions, type Stage } from "@/lib/decisions"
import { StageBadge } from "./badges"

const ORDER: Stage[] = ["drafted", "review", "approved", "sent", "new", "innocent", "rejected"]

export function ReportsView({ run, decisions, onOpen }: { run: Run; decisions: Decisions; onOpen: (s: Site) => void }) {
  const cased = run.sites.filter(s => s.case)
    .sort((a, b) => ORDER.indexOf(stageOf(a, decisions)!) - ORDER.indexOf(stageOf(b, decisions)!) || b.case!.breach_confidence - a.case!.breach_confidence)

  const by = new Map<string, HistoryEvent[]>()
  for (const e of run.history.events) if (e.verdict === "dry_spill_candidate") by.set(e.id, [...(by.get(e.id) ?? []), e])
  const repeats = [...by.values()].filter(es => es.length >= 2).sort((a, b) => b.length - a.length)
  const runs = run.history.runs.length

  return (
    <div className="mx-auto grid w-full max-w-6xl gap-6 p-4 md:p-8">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">Reports</h1>
        <p className="mt-1 max-w-[70ch] text-muted-foreground">
          Drafted evidence packs. Nothing reaches the Environment Agency or a water company until a person approves it here, downloads the pack and sends it.
        </p>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Investigated cases</CardTitle>
          <CardDescription>Open a case to read the agents' reasoning and review its report.</CardDescription>
        </CardHeader>
        <CardContent className="px-0">
          {cased.length ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="pl-6">Site</TableHead>
                  <TableHead className="text-right">Hours</TableHead>
                  <TableHead>Agents' verdict</TableHead>
                  <TableHead className="text-right">Confidence</TableHead>
                  <TableHead className="pr-6">Stage</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {cased.map(s => (
                  <TableRow key={s.id} tabIndex={0} className="cursor-pointer" onClick={() => onOpen(s)}
                    onKeyDown={e => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), onOpen(s))}>
                    <TableCell className="pl-6">
                      <div className="flex items-center gap-2 font-medium">
                        {titleCase(s.name)}
                        {s.case!.illustrative && <Badge variant="outline" className="border-dashed border-dry text-dry">Example</Badge>}
                      </div>
                      <div className="text-xs text-muted-foreground">{s.company} · {s.id}</div>
                    </TableCell>
                    <TableCell className="num text-right">{hrs(s)}</TableCell>
                    <TableCell className="capitalize">{words(s.case!.final_verdict)}</TableCell>
                    <TableCell className="num text-right">{pct(s.case!.breach_confidence)}</TableCell>
                    <TableCell className="pr-6"><StageBadge stage={stageOf(s, decisions)!} /></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : <p className="px-6 text-sm text-muted-foreground">No agent cases yet. Run scripts/agents.py to investigate the top candidates.</p>}
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Repeat sites</CardTitle>
          <CardDescription>
            Overflows with more than one dry-spill candidate, across {runs} detector run{runs === 1 ? "" : "s"}. Several candidates is a pattern worth a look, not proof of a breach.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {repeats.length ? (
            <ul className="grid gap-3">
              {repeats.map(es => {
                es.sort((a, b) => a.start.localeCompare(b.start))
                const last = es.at(-1)!
                const live = run.sites.find(s => s.id === last.id)
                return (
                  <li key={last.id} className="grid gap-1.5 border-t pt-3 first:border-0 first:pt-0">
                    <div className="flex flex-wrap items-baseline gap-2">
                      {live ? <button className="font-medium text-primary underline-offset-4 hover:underline" onClick={() => onOpen(live)}>{titleCase(last.name)}</button>
                        : <span className="font-medium">{titleCase(last.name)}</span>}
                      <span className="text-xs text-muted-foreground">{last.company} · {last.id} · {es.length} dry-spill candidates</span>
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {es.slice(-8).map(e => <Badge key={e.start} variant="secondary" className="num">{day(e.start)} · {e.hours == null ? "?" : fmt(e.hours)} h</Badge>)}
                    </div>
                  </li>
                )
              })}
            </ul>
          ) : <p className="text-sm text-muted-foreground">No overflow has had more than one dry-spill candidate yet. This fills up as the detector keeps running: every build adds that run's spills to the record.</p>}
        </CardContent>
      </Card>
    </div>
  )
}
