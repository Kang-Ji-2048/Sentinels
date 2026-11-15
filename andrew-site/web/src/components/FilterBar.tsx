// Filters pinned to the top of the dashboard. They apply to the spill list, the charts and the map.
import { Radio, Search, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import type { Filter } from "./PipelineStrip"

export interface Filters { search: string; company: string | null; stage: Filter; ongoing: boolean }
export const DEFAULT_FILTERS: Filters = { search: "", company: null, stage: "long", ongoing: false }

export function FilterBar({ filters, onChange, companies, stageTitles, shown }: {
  filters: Filters; onChange: (f: Filters) => void; companies: string[]; stageTitles: Record<Filter, string>; shown: number
}) {
  const set = (patch: Partial<Filters>) => onChange({ ...filters, ...patch })
  const changed = filters.search !== "" || filters.company !== null || filters.stage !== DEFAULT_FILTERS.stage || filters.ongoing
  return (
    <div role="search" aria-label="Filter the dashboard"
      className="sticky top-0 z-30 -mx-4 border-y bg-background/95 px-4 py-3 shadow-sm backdrop-blur md:-mx-8 md:px-8">
      <div className="mx-auto flex max-w-[1440px] flex-wrap items-end gap-x-4 gap-y-3">
        <div className="grid min-w-56 flex-1 gap-1.5 sm:max-w-72">
          <Label htmlFor="f-search" className="text-xs text-muted-foreground">Site or overflow ID</Label>
          <div className="relative">
            <Search aria-hidden className="absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input id="f-search" type="search" placeholder="e.g. Carnon River or SBB00211" value={filters.search}
              onChange={e => set({ search: e.target.value })} className="pl-8" />
          </div>
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="f-company" className="text-xs text-muted-foreground">Water company</Label>
          <Select value={filters.company ?? "all"} onValueChange={v => set({ company: v === "all" ? null : v })}>
            <SelectTrigger id="f-company" className="w-52"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All companies</SelectItem>
              {companies.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="f-stage" className="text-xs text-muted-foreground">Show</Label>
          <Select value={filters.stage} onValueChange={v => set({ stage: v as Filter })}>
            <SelectTrigger id="f-stage" className="w-64"><SelectValue /></SelectTrigger>
            <SelectContent>
              {(Object.keys(stageTitles) as Filter[]).map(k => <SelectItem key={k} value={k}>{stageTitles[k]}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
        <div className="flex h-9 items-center gap-2">
          <Switch id="f-ongoing" checked={filters.ongoing} onCheckedChange={v => set({ ongoing: v })} />
          <Label htmlFor="f-ongoing" className="flex items-center gap-1.5 text-sm font-normal"><Radio aria-hidden className="size-3.5 text-dry" />Still discharging</Label>
        </div>
        <div className="ml-auto flex h-9 items-center gap-3">
          <span className="num text-sm text-muted-foreground" aria-live="polite">{shown} {shown === 1 ? "site" : "sites"} shown</span>
          {changed && <Button variant="ghost" size="sm" onClick={() => onChange(DEFAULT_FILTERS)}><X aria-hidden />Clear filters</Button>}
        </div>
      </div>
    </div>
  )
}
