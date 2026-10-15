import type { ZoneSummary } from '../api/types'
import { ZONE_ORDER, zoneStyle } from '../theme'
import { utilizationColor } from '../utils/format'

// Horizontal fill bar per zone (Dashboard "Zone-wise Occupancy")
export default function ZoneBars({ zones }: { zones: ZoneSummary[] }) {
  const byName = Object.fromEntries(zones.map((z) => [z.zone, z]))
  return (
    <div className="space-y-5">
      {ZONE_ORDER.filter((name) => byName[name]).map((name) => {
        const z = byName[name]
        return (
          <div key={name}>
            <div className="mb-1.5 flex items-center justify-between text-sm">
              <span className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-sm" style={{ background: zoneStyle[name].color }} />
                {name}
              </span>
              <span className="font-medium" style={{ color: utilizationColor(z.utilization_pct) }}>
                {z.utilization_pct.toFixed(0)}%
              </span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-surface">
              <div className="h-full rounded-full transition-all"
                   style={{ width: `${Math.min(100, z.utilization_pct)}%`, background: zoneStyle[name].color }} />
            </div>
            <p className="mt-1 text-[11px] text-muted">{z.used.toLocaleString()} / {z.capacity.toLocaleString()} slots</p>
          </div>
        )
      })}
    </div>
  )
}
