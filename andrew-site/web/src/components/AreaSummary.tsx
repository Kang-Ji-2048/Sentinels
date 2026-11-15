// Shown beside the map when no single spill is open: what is spilling in the area on the map.
import { Radio } from "lucide-react"
import { LONG_HOURS, byHours, hrs, isLong, titleCase, type Site } from "@/lib/data"

function Stat({ value, label, dry }: { value: number; label: string; dry?: boolean }) {
  return (
    <div className="grid gap-1 rounded-lg border p-3">
      <span className={`num text-2xl leading-none font-semibold ${dry ? "text-dry" : ""}`}>{value}</span>
      <span className="text-xs text-muted-foreground">{label}</span>
    </div>
  )
}

export function AreaSummary({ title, sites, onSelect }: { title: string; sites: Site[]; onSelect: (s: Site) => void }) {
  const dry = sites.filter(s => s.verdict === "dry_spill_candidate").sort(byHours)
  const longest = dry.slice(0, 8)
  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="grid gap-1 border-b p-5">
        <h3 className="text-xl font-semibold">{title}</h3>
        <p className="text-sm text-muted-foreground">Spills that started in the last 48 hours. Click a column on the map or a site below to open its case here.</p>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto p-5">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Stat value={sites.length} label="spills" />
          <Stat value={dry.length} label="dry-spill candidates" dry />
          <Stat value={dry.filter(isLong).length} label={`dry, ${LONG_HOURS} h or more`} dry />
          <Stat value={sites.filter(s => s.ongoing).length} label="still discharging" />
        </div>
        <h4 className="mt-6 mb-2 text-xs font-semibold tracking-wider text-muted-foreground uppercase">Longest dry spills here</h4>
        {longest.length ? (
          <ul className="divide-y rounded-lg border">
            {longest.map(s => (
              <li key={s.id}>
                <button onClick={() => onSelect(s)} className="flex w-full items-center justify-between gap-3 px-3 py-2.5 text-left hover:bg-muted">
                  <span className="min-w-0">
                    <span className="block truncate font-medium text-primary">{titleCase(s.name)}</span>
                    <span className="block truncate text-xs text-muted-foreground">{s.company} · {s.id}</span>
                  </span>
                  <span className="num flex shrink-0 items-center gap-1 text-sm">
                    {s.ongoing && <Radio aria-label="still discharging" className="size-3.5 text-dry" />}{hrs(s)} h
                  </span>
                </button>
              </li>
            ))}
          </ul>
        ) : <p className="text-sm text-muted-foreground">No dry-spill candidates here.</p>}
      </div>
    </div>
  )
}
