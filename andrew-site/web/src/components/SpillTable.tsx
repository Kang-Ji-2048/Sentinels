// Ranked spill list: the table equivalent of the map, and the main way to open a case.
import { Radio, Repeat } from "lucide-react"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { cn } from "@/lib/utils"
import { fmt, hrs, titleCase, verdictOf, type Site } from "@/lib/data"
import { stageOf, type Decisions } from "@/lib/decisions"
import { StageBadge, VerdictBadge } from "./badges"

export function SpillTable({ sites, selected, decisions, repeats, onSelect, empty }: {
  sites: Site[]; selected: Site | null; decisions: Decisions; repeats: Map<string, number>
  onSelect: (s: Site) => void; empty: string
}) {
  if (!sites.length) return <p className="px-4 py-8 text-center text-sm text-muted-foreground md:px-6">{empty}</p>
  return (
    <Table>
      <TableHeader className="sticky top-0 z-10 bg-muted">
        <TableRow>
          <TableHead className="w-full pl-5 md:pl-6">Site</TableHead>
          <TableHead className="text-right">Hours</TableHead>
          <TableHead className="text-right">Rain 48 h</TableHead>
          <TableHead className="pr-5 md:pr-6">Stage</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {sites.map(s => {
          const stage = stageOf(s, decisions)
          const n = repeats.get(s.id) ?? 0
          const on = s.id === selected?.id
          return (
            <TableRow
              key={s.id}
              tabIndex={0}
              aria-selected={on}
              onClick={() => onSelect(s)}
              onKeyDown={e => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), onSelect(s))}
              className={cn("group cursor-pointer focus-visible:outline-2 focus-visible:-outline-offset-2", on && "bg-selection/30 hover:bg-selection/40")}
            >
              <TableCell className="w-full max-w-0 py-3.5 pl-5 md:pl-6">
                <div className="truncate font-medium text-primary underline-offset-4 group-hover:underline">{titleCase(s.name)}</div>
                <div className="mt-0.5 flex items-center gap-1.5 truncate text-xs text-muted-foreground">
                  <span className="truncate">{s.company} · {s.id}</span>
                  {n >= 2 && (
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <span className="inline-flex shrink-0 items-center gap-0.5 text-foreground"><Repeat aria-hidden className="size-3" />{n}×</span>
                      </TooltipTrigger>
                      <TooltipContent>{n} dry-spill candidates at this overflow across detector runs</TooltipContent>
                    </Tooltip>
                  )}
                </div>
              </TableCell>
              <TableCell className="num py-3.5 text-right align-top">
                <div className="flex items-center justify-end gap-1">
                  {s.ongoing && <Radio aria-label="still discharging" className="size-3.5 text-dry" />}
                  {hrs(s)}
                </div>
              </TableCell>
              <TableCell className="num py-3.5 text-right align-top">{fmt(s.rain48, 2)}</TableCell>
              <TableCell className="py-3.5 pr-5 align-top md:pr-6">
                {stage ? <StageBadge stage={stage} /> : <VerdictBadge verdict={verdictOf(s)} />}
              </TableCell>
            </TableRow>
          )
        })}
      </TableBody>
    </Table>
  )
}
