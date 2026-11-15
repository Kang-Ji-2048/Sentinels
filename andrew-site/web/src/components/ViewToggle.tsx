// Table / Chart switch for a dashboard panel. Each panel remembers its own choice.
import { BarChart3, Table2 } from "lucide-react"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"

export type PanelView = "table" | "chart"

export function ViewToggle({ value, onChange, label }: { value: PanelView; onChange: (v: PanelView) => void; label: string }) {
  return (
    <ToggleGroup type="single" variant="outline" size="sm" spacing={0} value={value}
      onValueChange={v => v && onChange(v as PanelView)} aria-label={`Show ${label} as`}>
      <ToggleGroupItem value="table" aria-label="Table" className="gap-1.5 px-3 data-[state=on]:bg-primary data-[state=on]:text-primary-foreground">
        <Table2 aria-hidden />Table
      </ToggleGroupItem>
      <ToggleGroupItem value="chart" aria-label="Chart" className="gap-1.5 px-3 data-[state=on]:bg-primary data-[state=on]:text-primary-foreground">
        <BarChart3 aria-hidden />Chart
      </ToggleGroupItem>
    </ToggleGroup>
  )
}
