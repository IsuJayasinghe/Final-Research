import { useEffect } from 'react'
import { Anchor, DoorOpen, RotateCw } from 'lucide-react'
import { api } from '../api/client'
import ErrorMessage from '../components/ErrorMessage'
import Loading from '../components/Loading'
import PageHeader from '../components/PageHeader'
import BlockMap from '../components/yard/BlockMap'
import ZoneCard from '../components/yard/ZoneCard'
import { useApi } from '../hooks/useApi'
import { ZONE_ORDER } from '../theme'

export default function YardMapPage() {
  const yard = useApi(() => api.yardZones())

  useEffect(() => {
    const timer = setInterval(yard.reload, 30000)
    return () => clearInterval(timer)
  }, [yard.reload])

  const data = yard.data
  return (
    <>
      <PageHeader
        title="Yard Layout"
        subtitle={data
          ? `${data.block.name} · ${data.block.bays} bays × ${data.block.rows} rows × ${data.block.tier_height} tiers · zones and current allocation`
          : 'Yard block zones and current allocation.'}
        actions={
          <button className="btn-ghost" onClick={yard.reload} disabled={yard.loading}>
            <RotateCw size={14} className={yard.loading ? 'animate-spin' : ''} /> Refresh
          </button>
        }
      />

      {yard.error && <ErrorMessage message={yard.error} onRetry={yard.reload} />}
      {!data && yard.loading && <Loading text="Loading yard block..." />}

      {data && (
        <>
          <div className="card">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-2 text-xs uppercase tracking-widest text-muted">
              <span className="flex items-center gap-2"><DoorOpen size={16} /> Gate end</span>
              <span className="font-semibold normal-case tracking-normal text-ink">{data.block.name} — seen from above</span>
              <span className="flex items-center gap-2">Far end <Anchor size={16} /></span>
            </div>
            <BlockMap yard={data} />
            <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-xs text-muted">
              <span className="flex flex-wrap items-center gap-3">
                Stack height:
                {[0, 1, 2, 3, 4].map((h) => (
                  <span key={h} className="flex items-center gap-1">
                    <span className="inline-block h-3 w-3 rounded-[2px]"
                          style={h === 0 ? { border: '1px dashed #64748b' } : { background: '#94a3b8', opacity: 0.3 + 0.175 * h }} />
                    {h}
                  </span>
                ))}
                <span className="flex items-center gap-1">
                  <span className="inline-block h-3 w-3"
                        style={{ background: 'repeating-linear-gradient(45deg,#1b2a44 0 3px,transparent 3px 6px)' }} />
                  buffer
                </span>
              </span>
              <span>
                Total: {data.total.used.toLocaleString()} / {data.total.capacity.toLocaleString()} slots ({data.total.utilization_pct}%)
              </span>
            </div>
          </div>

          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            {ZONE_ORDER.map((name) => {
              const zone = data.zones.find((z) => z.zone === name)
              return zone && <ZoneCard key={name} zone={zone} section={data.sections.find((s) => s.zone === name)} />
            })}
          </div>
        </>
      )}
    </>
  )
}
