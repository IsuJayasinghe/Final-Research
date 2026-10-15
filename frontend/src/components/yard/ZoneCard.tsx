import { Link } from 'react-router-dom'
import type { BlockSummary, ZoneSummary } from '../../api/types'
import { zoneStyle } from '../../theme'
import { utilizationColor } from '../../utils/format'
import BlockGrid from './BlockGrid'

export default function ZoneCard({ zone, blocks }: { zone: ZoneSummary; blocks: BlockSummary[] }) {
  const style = zoneStyle[zone.zone]
  return (
    <div className="rounded-xl border-2 bg-card p-5" style={{ borderColor: `${style.color}66` }}>
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <h3 className="text-base">{zone.zone}</h3>
          <p className="text-xs text-muted">{zone.description}</p>
        </div>
        <div className="text-right">
          <p className="text-xl font-bold" style={{ color: utilizationColor(zone.utilization_pct) }}>
            {zone.utilization_pct.toFixed(0)}% Full
          </p>
          <p className="text-xs text-muted">{zone.used.toLocaleString()} containers</p>
        </div>
      </div>
      <div className="space-y-4">
        {blocks.map((b) => <BlockGrid key={b.block} block={b} />)}
      </div>
      <Link to={`/containers?zone=${encodeURIComponent(zone.zone)}`} className="mt-4 inline-block text-xs text-accent hover:underline">
        View containers in {zone.zone}
      </Link>
    </div>
  )
}
