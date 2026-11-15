// The detect -> investigate -> report funnel, one clickable step per stage. Clicking a step filters the spill list.
import { ChevronRight } from "lucide-react"
import { cn } from "@/lib/utils"

export type Filter = "spills" | "dry" | "long" | "investigated" | "drafted" | "approved" | "sent"
export interface Step { key: Filter | null; label: string; value: number | null; hint: string; dry?: boolean }

function StepCard({ s, on, onPick }: { s: Step; on: boolean; onPick: (f: Filter) => void }) {
  const body = (
    <>
      <span className={cn("num text-3xl leading-none font-semibold tracking-tight", s.dry && "text-dry")}>
        {s.value == null ? "n/a" : s.value.toLocaleString("en-GB")}
      </span>
      <span className="text-sm leading-snug text-muted-foreground">{s.label}</span>
    </>
  )
  const base = "flex h-full w-full flex-col items-start gap-2 rounded-xl border px-5 py-4 text-left"
  return s.key ? (
    <button type="button" title={s.hint} aria-pressed={on} onClick={() => onPick(s.key!)}
      className={cn(base, "bg-background shadow-sm transition-colors hover:border-primary/60", on && "border-primary ring-2 ring-selection")}>
      {body}
    </button>
  ) : (
    <div title={s.hint} className={cn(base, "border-dashed")}>{body}</div>
  )
}

function Group({ title, steps, active, onPick }: { title: string; steps: Step[]; active: Filter; onPick: (f: Filter) => void }) {
  return (
    <div className="grid gap-3">
      <h3 className="text-xs font-semibold tracking-wider text-muted-foreground uppercase">{title}</h3>
      <ol className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {steps.map((s, i) => (
          <li key={s.label} className="relative">
            <StepCard s={s} on={s.key === active} onPick={onPick} />
            {i < steps.length - 1 && (
              <ChevronRight aria-hidden className="absolute top-1/2 -right-3 z-10 hidden size-4 -translate-y-1/2 text-muted-foreground/70 sm:block" />
            )}
          </li>
        ))}
      </ol>
    </div>
  )
}

export function PipelineStrip({ steps, active, onPick }: { steps: Step[]; active: Filter; onPick: (f: Filter) => void }) {
  return (
    <nav aria-label="Pipeline: from overflows to reports sent" className="grid gap-6 xl:grid-cols-2 xl:gap-8">
      <Group title="Detect" steps={steps.slice(0, 4)} active={active} onPick={onPick} />
      <Group title="Investigate & report" steps={steps.slice(4)} active={active} onPick={onPick} />
    </nav>
  )
}
