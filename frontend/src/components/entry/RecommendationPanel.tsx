import { useState } from 'react'
import { Link } from 'react-router-dom'
import { AlertTriangle, Brain, Check, CheckCircle2, Info, Loader2, MapPin, PenLine, Plus } from 'lucide-react'
import { api } from '../../api/client'
import type { AcceptResult, AllocationResult, OverrideResult } from '../../api/types'
import { ZONE_ORDER, zoneStyle, type ZoneName } from '../../theme'
import { DwellClassBadge } from '../Badges'
import { useToast } from '../Toast'

interface Props {
  result: AllocationResult
  onNew: () => void
}

type Decision = { kind: 'accepted'; data: AcceptResult } | { kind: 'overridden'; data: OverrideResult }

function YesNo({ label, value }: { label: string; value: boolean }) {
  return (
    <div className={`rounded-lg border p-3 text-center ${value ? 'border-warn/50 bg-warn/10' : 'border-line bg-surface'}`}>
      <p className="label">{label}</p>
      <p className={`mt-1 font-semibold ${value ? 'text-warn' : 'text-ink'}`}>{value ? 'Yes' : 'No'}</p>
    </div>
  )
}

export default function RecommendationPanel({ result, onNew }: Props) {
  const toast = useToast()
  const [busy, setBusy] = useState(false)
  const [decision, setDecision] = useState<Decision | null>(null)
  const [overriding, setOverriding] = useState(false)
  const [zone, setZone] = useState<ZoneName>(ZONE_ORDER.find((z) => z !== result.recommended_zone) ?? 'Medium-Access')
  const [reason, setReason] = useState('')
  const style = zoneStyle[result.recommended_zone]

  const accept = async () => {
    setBusy(true)
    try {
      const data = await api.accept(result.allocation_id)
      setDecision({ kind: 'accepted', data })
      toast(`${data.container_id} accepted in ${result.recommended_zone}, slot ${data.slot}`)
    } catch (e) {
      toast((e as Error).message, 'error')
    } finally {
      setBusy(false)
    }
  }

  const override = async () => {
    if (!reason.trim()) return toast('Please give a reason for the override', 'error')
    setBusy(true)
    try {
      const data = await api.override(result.allocation_id, zone, reason.trim())
      setDecision({ kind: 'overridden', data })
      setOverriding(false)
      toast(`${data.container_id} moved to ${data.zone}, slot ${data.slot}`)
    } catch (e) {
      toast((e as Error).message, 'error')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="card">
        <div className="flex items-center gap-2 text-sm font-semibold"><Brain size={16} className="text-accent" /> AI PREDICTION RESULT</div>
        <div className="mt-3 flex items-end justify-between gap-3">
          <div>
            <p className="text-4xl font-bold">{result.predicted_dwell_days.toFixed(1)} days</p>
            <p className="mt-1 text-xs text-muted">Predicted dwell time · {result.model_used}</p>
          </div>
          <DwellClassBadge value={result.dwell_class} />
        </div>
      </div>

      <div className="card">
        <p className="card-title">YARD-TYPE COMPATIBILITY CHECK</p>
        <div className="grid grid-cols-3 gap-3">
          <YesNo label="Reefer?" value={result.compatibility.reefer} />
          <YesNo label="Hazardous?" value={result.compatibility.hazardous} />
          <YesNo label="Oversized?" value={result.compatibility.oversized} />
        </div>
      </div>

      <div className="card">
        <div className="flex items-center gap-2 text-sm font-semibold"><MapPin size={16} className="text-accent" /> RECOMMENDED ALLOCATION</div>
        <p className={`mt-3 text-2xl font-bold ${style.text}`}>{result.recommended_zone}</p>
        <p className="mt-1 font-mono text-sm">{result.block.replace(/_/g, ' ')} · slot {result.slot}</p>
        <p className="mt-3 flex gap-2 text-xs text-muted"><Info size={14} className="mt-0.5 shrink-0" />{result.reason}</p>
        <div className="mt-4">
          <div className="mb-1 flex justify-between text-[11px] text-muted">
            <span>Zone occupancy</span>
            <span>{result.zone_occupancy.used} / {result.zone_occupancy.capacity} ({result.zone_occupancy.utilization_pct}%)</span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-surface">
            <div className="h-full rounded-full" style={{ width: `${Math.min(100, result.zone_occupancy.utilization_pct)}%`, background: style.color }} />
          </div>
        </div>

        {!decision && !overriding && (
          <div className="mt-5 space-y-2">
            <button className="btn-success w-full py-2.5" onClick={accept} disabled={busy}>
              {busy ? <Loader2 size={16} className="animate-spin" /> : <Check size={16} />} Accept Recommendation
            </button>
            <button className="btn-outline w-full py-2.5" onClick={() => setOverriding(true)} disabled={busy}>
              <PenLine size={16} /> Override Zone
            </button>
          </div>
        )}

        {!decision && overriding && (
          <div className="mt-5 space-y-3 rounded-lg border border-line bg-surface p-4">
            <label className="block">
              <span className="label">Move to zone</span>
              <select className="input mt-1.5" value={zone} onChange={(e) => setZone(e.target.value as ZoneName)}>
                {ZONE_ORDER.filter((z) => z !== result.recommended_zone).map((z) => <option key={z}>{z}</option>)}
              </select>
            </label>
            {((result.compatibility.reefer && zone !== 'Reefer') || (result.compatibility.hazardous && zone !== 'Hazardous')) && (
              <p className="flex gap-2 rounded-md border border-warn/40 bg-warn/10 p-2 text-xs text-warn">
                <AlertTriangle size={14} className="mt-0.5 shrink-0" />
                {result.compatibility.reefer
                  ? 'Yard-type rule: reefer containers need powered slots. This zone has no reefer power.'
                  : 'Yard-type rule: hazardous cargo must be stored in the isolated hazardous yard.'}
              </p>
            )}
            <label className="block">
              <span className="label">Reason (required)</span>
              <textarea className="input mt-1.5" rows={2} value={reason} onChange={(e) => setReason(e.target.value)}
                        placeholder="e.g. Customs inspection expected" />
            </label>
            <div className="flex gap-2">
              <button className="btn-primary flex-1" onClick={override} disabled={busy}>
                {busy && <Loader2 size={14} className="animate-spin" />} Confirm override
              </button>
              <button className="btn-ghost" onClick={() => setOverriding(false)} disabled={busy}>Cancel</button>
            </div>
          </div>
        )}

        {decision && (
          <div className="mt-5 rounded-lg border border-ok/40 bg-ok/10 p-4 text-sm">
            <p className="flex items-center gap-2 font-semibold text-ok"><CheckCircle2 size={16} />
              {decision.kind === 'accepted' ? 'Recommendation accepted' : 'Zone overridden'}
            </p>
            <p className="mt-1 text-ink">
              {decision.kind === 'accepted'
                ? `Place ${decision.data.container_id} at slot ${decision.data.slot}.`
                : `Place ${decision.data.container_id} in ${decision.data.zone} at slot ${decision.data.slot}.`}
            </p>
            {decision.kind === 'overridden' && decision.data.reshuffles > 0 && (
              <p className="mt-1 text-xs text-muted">{decision.data.reshuffles} container(s) relocated.</p>
            )}
            <div className="mt-3 flex flex-wrap gap-2">
              <button className="btn-primary py-1.5" onClick={onNew}><Plus size={14} /> Register another</button>
              <Link to={`/containers?search=${result.container_id}`} className="btn-ghost py-1.5">View in tracking</Link>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
