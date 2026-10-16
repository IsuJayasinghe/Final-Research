import { Link } from 'react-router-dom'
import type { SectionSummary, ZoneSummary } from '../../api/types'
import { zoneStyle } from '../../theme'
import { utilizationColor } from '../../utils/format'

// Summary of one zone of the block: fill level, slots and bay range
export default function ZoneCard({ zone, section }: { zone: ZoneSummary; section?: SectionSummary }) {
  const style = zoneStyle[zone.zone]
  return (
    <div className="rounded-xl border-2 bg-card p-4" style={{ borderColor: `${style.color}66` }}>
      <div className="flex items-start justify-between gap-2">
        <h3 className="text-sm">{zone.zone}</h3>
        <p className="text-lg font-bold leading-none" style={{ color: utilizationColor(zone.utilization_pct) }}>
          {zone.utilization_pct.toFixed(0)}%
        </p>
      </div>
      <p className="mt-1 text-[11px] text-muted">{zone.description}</p>
      <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-surface">
        <div className="h-full rounded-full" style={{ width: `${Math.min(100, zone.utilization_pct)}%`, background: style.color }} />
      </div>
      <p className="mt-2 text-xs text-muted">
        {zone.used.toLocaleString()} / {zone.capacity.toLocaleString()} slots
        {section && <> · bays {section.first_bay}–{section.first_bay + section.bays - 1}</>}
      </p>
      <Link to={`/containers?zone=${encodeURIComponent(zone.zone)}`} className="mt-2 inline-block text-xs text-accent hover:underline">
        View containers
      </Link>
    </div>
  )
}
