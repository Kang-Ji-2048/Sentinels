// Verdict and stage badges: always an icon + a text label, so meaning never rests on colour alone.
import { CheckCircle2, CircleDashed, CircleSlash, CloudRain, Droplet, FileText, Search, Send, ShieldCheck, XCircle } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import { VERDICT, type Verdict } from "@/lib/data"
import { STAGE, type Stage } from "@/lib/decisions"

const VERDICT_ICON = { dry_spill_candidate: Droplet, rain_explained: CloudRain, no_gauge: CircleSlash }
const VERDICT_CLASS = {
  dry_spill_candidate: "border-dry text-dry",
  rain_explained: "border-rain text-rain",
  no_gauge: "border-nogauge text-muted-foreground",
}

export function VerdictBadge({ verdict, className }: { verdict: Verdict; className?: string }) {
  const Icon = VERDICT_ICON[verdict]
  return (
    <Badge variant="outline" className={cn("gap-1 bg-background", VERDICT_CLASS[verdict], className)}>
      <Icon aria-hidden className="size-3.5" />
      {VERDICT[verdict].label}
    </Badge>
  )
}

const STAGE_ICON = { new: CircleDashed, innocent: ShieldCheck, review: Search, drafted: FileText, approved: CheckCircle2, sent: Send, rejected: XCircle }

export function StageBadge({ stage, className }: { stage: Stage; className?: string }) {
  const Icon = STAGE_ICON[stage]
  return (
    <Badge variant="outline" className={cn("gap-1 whitespace-nowrap", STAGE[stage].className, className)}>
      <Icon aria-hidden className="size-3.5" />
      {STAGE[stage].label}
    </Badge>
  )
}

/** A small swatch for legends: a column (spills over an hour) or a dot (shorter). */
export function Swatch({ color, shape = "column" }: { color: string; shape?: "column" | "dot" }) {
  return shape === "column"
    ? <span aria-hidden className="inline-block h-4 w-2.5 shrink-0 rounded-[3px]" style={{ background: color }} />
    : <span aria-hidden className="inline-block size-2 shrink-0 rounded-full" style={{ background: color }} />
}
