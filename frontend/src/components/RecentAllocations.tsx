import { Link } from 'react-router-dom'
import type { ContainerRecord } from '../api/types'
import { formatDays } from '../utils/format'
import { StatusBadge, TypeBadge, ZoneBadge } from './Badges'

export default function RecentAllocations({ rows }: { rows: ContainerRecord[] }) {
  if (!rows.length) {
    return <p className="py-8 text-center text-sm text-muted">No allocations yet. Register a container arrival to see it here.</p>
  }
  return (
    <div className="-mx-5 overflow-x-auto">
      <table className="w-full min-w-[640px]">
        <thead>
          <tr>
            <th className="table-head">Container ID</th>
            <th className="table-head">Type</th>
            <th className="table-head">Allocated zone</th>
            <th className="table-head">Slot</th>
            <th className="table-head">Predicted dwell</th>
            <th className="table-head">Status</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.allocation_id} className={r.status === 'Overstaying' ? 'bg-danger/5' : ''}>
              <td className="table-cell font-mono text-accent">
                <Link to={`/containers?search=${r.container_id}`}>{r.container_id}</Link>
              </td>
              <td className="table-cell"><TypeBadge type={r.container_type} /></td>
              <td className="table-cell"><ZoneBadge zone={r.zone} /></td>
              <td className="table-cell font-mono text-muted">{r.slot ?? '—'}</td>
              <td className="table-cell">{formatDays(r.predicted_dwell_days)}</td>
              <td className="table-cell"><StatusBadge status={r.status} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
