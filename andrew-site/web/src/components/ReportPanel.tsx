// Review a drafted evidence pack: edit, approve (with a name), reject (with a reason the agents will see),
// mark as sent, undo, download. Nothing is emailed from here: a person sends the downloaded pack.
import { useEffect, useState } from "react"
import { toast } from "sonner"
import { Check, Download, Info, Send, TriangleAlert, Undo2, X } from "lucide-react"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { when, type Run, type Site } from "@/lib/data"
import { decisionOf, postDecision, type DecisionStatus, type Decisions } from "@/lib/decisions"
import { downloadPack } from "@/lib/pack"

const store = {
  get: (k: string) => { try { return localStorage.getItem(k) ?? "" } catch { return "" } },
  set: (k: string, v: string) => { try { localStorage.setItem(k, v) } catch { /* private window: name isn't remembered */ } },
}

export function ReportPanel({ run, site, decisions, api, onDecisions }: {
  run: Run; site: Site; decisions: Decisions; api: boolean; onDecisions: (d: Decisions) => void
}) {
  const c = site.case
  const d = decisionOf(site, decisions)
  const [text, setText] = useState(d.report || c?.report || "")
  const [name, setName] = useState(() => store.get("sentinels-reviewer"))
  const [sentTo, setSentTo] = useState("")
  const [reason, setReason] = useState("")
  const [rejectOpen, setRejectOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  useEffect(() => setText(d.report || c?.report || ""), [site.id, d.status]) // eslint-disable-line react-hooks/exhaustive-deps

  if (!c?.report)
    return <p className="text-sm text-muted-foreground">No evidence pack drafted. The agents draft one when a case is rated needs review or likely breach.</p>

  async function send(status: DecisionStatus, note = "") {
    if (!name.trim()) return toast.error("Add your name first, so the record shows who decided.")
    if (status === "rejected" && !note) return toast.error("Give a reason for rejecting.")
    setSaving(true)
    try {
      onDecisions(await postDecision(site, status, name.trim(), note, text))
      toast.success({ approved: "Approved. Download the pack to send it.", rejected: "Rejected. The agents will see your reason.", sent: "Marked as sent.", draft: "Decision undone." }[status])
      setRejectOpen(false)
      setReason("")
    } catch (e) {
      toast.error(`Not saved: ${(e as Error).message}`)
    }
    setSaving(false)
  }

  const said = {
    approved: `Approved by ${d.approved_by}, ${when(d.approved_at)}.`,
    sent: `Sent by ${d.sent_by}, ${when(d.sent_at)}${d.sent_note ? ` to ${d.sent_note}` : ""}. Approved by ${d.approved_by}.`,
    rejected: `Rejected by ${d.rejected_by}, ${when(d.rejected_at)}: ${d.reason}`,
    draft: null,
  }[d.status]
  const editable = d.status === "draft" && api

  return (
    <div className="grid gap-4">
      {c.illustrative && (
        <Alert className="border-2 border-dashed border-dry">
          <TriangleAlert aria-hidden className="text-dry" />
          <AlertTitle>Example report</AlertTitle>
          <AlertDescription>Made up to show the review flow. Its downloaded pack is marked as an example and must not be sent.</AlertDescription>
        </Alert>
      )}
      <div className="grid gap-1 rounded-lg border bg-muted/50 p-3 text-sm">
        <span className="text-muted-foreground">Suggested recipients</span>
        <span><b className="font-semibold">Environment Agency</b> (incident line or area office) · copy to <b className="font-semibold">{site.company}</b></span>
      </div>
      {said && <p className="rounded-md border-l-4 border-primary bg-muted/50 px-3 py-2 text-sm">{said}</p>}
      {!api && (
        <Alert>
          <Info aria-hidden />
          <AlertTitle>Read-only</AlertTitle>
          <AlertDescription>Decisions can't be saved. Start the page with python andrew-site/serve.py to approve or reject.</AlertDescription>
        </Alert>
      )}
      <div className="grid gap-2">
        <Label htmlFor="draft">{editable ? "Draft report (you can edit it)" : "Report"}</Label>
        <Textarea id="draft" value={text} onChange={e => setText(e.target.value)} readOnly={!editable} className="min-h-72 font-normal leading-relaxed" />
      </div>

      {api && (
        <div className="grid gap-3 border-t pt-4">
          <div className="grid gap-1.5 sm:max-w-xs">
            <Label htmlFor="reviewer">Reviewer</Label>
            <Input id="reviewer" autoComplete="name" placeholder="Your name" value={name}
              onChange={e => { setName(e.target.value); store.set("sentinels-reviewer", e.target.value.trim()) }} />
          </div>
          {d.status === "approved" && (
            <div className="grid gap-1.5 sm:max-w-xs">
              <Label htmlFor="sent-to">Sent to (optional)</Label>
              <Input id="sent-to" placeholder="e.g. EA South West, incident line" value={sentTo} onChange={e => setSentTo(e.target.value)} />
            </div>
          )}
          <div className="flex flex-wrap gap-2">
            {d.status === "draft" && <>
              <Button disabled={saving} onClick={() => send("approved")}><Check aria-hidden />Approve</Button>
              <Button variant="outline" disabled={saving} onClick={() => setRejectOpen(true)}><X aria-hidden />Reject…</Button>
            </>}
            {(d.status === "approved" || d.status === "sent") && (
              <Button onClick={() => downloadPack(run, site, d)}><Download aria-hidden />{c.illustrative ? "Download example pack" : "Download evidence pack"}</Button>
            )}
            {d.status === "approved" && <Button variant="outline" disabled={saving} onClick={() => send("sent", sentTo.trim())}><Send aria-hidden />Mark as sent</Button>}
            {d.status !== "draft" && (
              <Button variant="ghost" disabled={saving} onClick={() => send("draft", "undone")}>
                <Undo2 aria-hidden />Undo {d.status === "sent" ? "sent" : d.status === "approved" ? "approval" : "rejection"}
              </Button>
            )}
          </div>
        </div>
      )}
      {d.log.length > 0 && (
        <p className="text-xs text-muted-foreground">History: {d.log.map(l => `${l.status} by ${l.by}, ${when(l.at)}`).join(" · ")}</p>
      )}

      <Dialog open={rejectOpen} onOpenChange={setRejectOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reject this report?</DialogTitle>
            <DialogDescription>The agents see your reason the next time they look at this site.</DialogDescription>
          </DialogHeader>
          <Label htmlFor="reason" className="sr-only">Reason for rejecting</Label>
          <Textarea id="reason" autoFocus placeholder="e.g. this outfall is tidal" value={reason} onChange={e => setReason(e.target.value)} className="min-h-24" />
          <DialogFooter>
            <DialogClose asChild><Button variant="ghost">Cancel</Button></DialogClose>
            <Button variant="destructive" disabled={saving || !reason.trim()} onClick={() => send("rejected", reason.trim())}>Reject report</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
