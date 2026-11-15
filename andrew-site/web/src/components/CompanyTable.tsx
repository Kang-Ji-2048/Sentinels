// Spills per water company in the last 48 h: a table with an inline stacked bar per row. Clicking a company
// opens the map on its area and filters the spill list to it.
import { MapPin } from "lucide-react"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { cn } from "@/lib/utils"
import type { Site } from "@/lib/data"

const OTHER = "#A3B1BE"

export function CompanyTable({ sites, active, onPick }: { sites: Site[]; active: string | null; onPick: (company: string) => void }) {
  const by = new Map<string, { company: string; dry: number; total: number }>()
  for (const s of sites) {
    const row = by.get(s.company) ?? { company: s.company, dry: 0, total: 0 }
    row.total++
    if (s.verdict === "dry_spill_candidate") row.dry++
    by.set(s.company, row)
  }
  const rows = [...by.values()].sort((a, b) => b.dry - a.dry || b.total - a.total)
  const max = Math.max(...rows.map(r => r.total))
  return (
    <div>
      <div className="flex flex-wrap items-center gap-x-5 gap-y-1 px-5 pb-3 text-xs text-muted-foreground md:px-6">
        <span className="flex items-center gap-1.5"><span aria-hidden className="size-2.5 rounded-sm bg-dry" />Dry-spill candidates</span>
        <span className="flex items-center gap-1.5"><span aria-hidden className="size-2.5 rounded-sm" style={{ background: OTHER }} />Other spills</span>
      </div>
      <Table>
        <TableHeader className="bg-muted">
          <TableRow>
            <TableHead className="pl-5 md:pl-6">Water company</TableHead>
            <TableHead className="w-2/5"><span className="sr-only">Chart</span></TableHead>
            <TableHead className="text-right">Dry</TableHead>
            <TableHead className="pr-5 text-right md:pr-6">Spills</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map(r => (
            <TableRow key={r.company} className={cn(active === r.company && "bg-selection/30 hover:bg-selection/40")}>
              <TableCell className="py-3 pl-5 md:pl-6">
                <button onClick={() => onPick(r.company)} aria-pressed={active === r.company}
                  className="group inline-flex items-center gap-1.5 text-left font-medium text-primary underline-offset-4 hover:underline">
                  {r.company}
                  <MapPin aria-hidden className="size-3.5 opacity-50 group-hover:opacity-100" />
                  <span className="sr-only">: show on the map</span>
                </button>
              </TableCell>
              <TableCell className="py-3">
                <div aria-hidden className="flex h-3 gap-0.5">
                  {r.dry > 0 && <span className="h-full rounded-l bg-dry" style={{ width: `${(r.dry / max) * 100}%` }} />}
                  {r.total > r.dry && <span className={cn("h-full rounded-r", !r.dry && "rounded-l")} style={{ width: `${((r.total - r.dry) / max) * 100}%`, background: OTHER }} />}
                </div>
              </TableCell>
              <TableCell className="num py-3 text-right font-medium text-dry">{r.dry}</TableCell>
              <TableCell className="num py-3 pr-5 text-right md:pr-6">{r.total}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
