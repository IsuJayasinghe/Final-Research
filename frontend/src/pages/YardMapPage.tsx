import { useEffect } from 'react'
import { Anchor, DoorOpen, RotateCw } from 'lucide-react'
import { api } from '../api/client'
import ErrorMessage from '../components/ErrorMessage'
import Loading from '../components/Loading'
import PageHeader from '../components/PageHeader'
import ZoneCard from '../components/yard/ZoneCard'
import { useApi } from '../hooks/useApi'
import { ZONE_ORDER, zoneStyle, type ZoneName } from '../theme'

// Layout follows the yard: gate side (top) -> fast access, medium; back of yard -> long term;
// reefer and hazardous yards on the side; berths at the bottom.
const LAYOUT: ZoneName[][] = [['Fast-Access', 'Medium-Access'], ['Long-Term', 'Reefer', 'Hazardous']]

export default function YardMapPage() {
  const yard = useApi(() => api.yardZones())

  useEffect(() => {
    const timer = setInterval(yard.reload, 30000)
    return () => clearInterval(timer)
  }, [yard.reload])

  const data = yard.data
  const zone = (name: ZoneName) => {
    const summary = data!.zones.find((z) => z.zone === name)
    return summary && <ZoneCard key={name} zone={summary} blocks={data!.blocks.filter((b) => b.zone === name)} />
  }

  return (
    <>
      <PageHeader
        title="Yard Layout"
        subtitle="Visual overview of container yard zones and current allocation."
        actions={
          <>
            <div className="hidden flex-wrap gap-3 rounded-lg border border-line bg-surface px-3 py-2 text-[11px] uppercase tracking-wider text-muted md:flex">
              {ZONE_ORDER.map((z) => (
                <span key={z} className="flex items-center gap-1.5">
                  <span className="h-2.5 w-2.5 rounded-sm" style={{ background: zoneStyle[z].color }} />{z}
                </span>
              ))}
            </div>
            <button className="btn-ghost" onClick={yard.reload} disabled={yard.loading}>
              <RotateCw size={14} className={yard.loading ? 'animate-spin' : ''} /> Refresh
            </button>
          </>
        }
      />

      {yard.error && <ErrorMessage message={yard.error} onRetry={yard.reload} />}
      {!data && yard.loading && <Loading text="Loading yard layout..." />}

      {data && (
        <div className="space-y-5 rounded-2xl border border-line bg-surface p-4 sm:p-6">
          <div className="flex items-center justify-center gap-2 rounded-lg border border-dashed border-line py-3 text-xs uppercase tracking-widest text-muted">
            <DoorOpen size={16} /> Gate entry / exit
          </div>

          <div className="grid items-start gap-5 lg:grid-cols-2">{LAYOUT[0].map(zone)}</div>
          <div className="grid items-start gap-5 lg:grid-cols-2">
            {zone(LAYOUT[1][0])}
            <div className="space-y-5">{LAYOUT[1].slice(1).map(zone)}</div>
          </div>

          <div className="flex items-center justify-center gap-2 rounded-lg border border-dashed border-line py-3 text-xs uppercase tracking-widest text-muted">
            <Anchor size={16} /> Berth area · quay cranes
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-muted">
            <span className="flex items-center gap-3">
              Stack height:
              {[0, 1, 2, 3, 4].map((h) => (
                <span key={h} className="flex items-center gap-1">
                  <span className="inline-block h-3 w-3 rounded-[2px]"
                        style={h === 0 ? { border: '1px dashed #2b3c5a' } : { background: '#94a3b8', opacity: 0.3 + 0.175 * h }} />
                  {h}
                </span>
              ))}
            </span>
            <span>
              Total: {data.total.used.toLocaleString()} / {data.total.capacity.toLocaleString()} slots ({data.total.utilization_pct}%)
            </span>
          </div>
        </div>
      )}
    </>
  )
}
