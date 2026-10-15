import type { ContainerStatus, ContainerType, DwellClass } from '../api/types'
import { zoneStyle, type ZoneName } from '../theme'

export function ZoneBadge({ zone }: { zone: ZoneName | null }) {
  if (!zone) return <span className="text-muted">—</span>
  return <span className={`badge ${zoneStyle[zone].badge}`}>{zone}</span>
}

const TYPE_STYLE: Record<ContainerType, string> = {
  DRY: 'border-line bg-surface text-ink',
  REEFER: 'border-zone-reefer/40 bg-zone-reefer/10 text-zone-reefer',
  HAZMAT: 'border-danger/40 bg-danger/10 text-danger',
  OVERSIZED: 'border-warn/40 bg-warn/10 text-warn',
}

export function TypeBadge({ type }: { type: ContainerType | null }) {
  if (!type) return <span className="text-muted">—</span>
  return <span className={`badge ${TYPE_STYLE[type]}`}>{type.charAt(0) + type.slice(1).toLowerCase()}</span>
}

const STATUS_STYLE: Record<ContainerStatus, string> = {
  Active: 'border-ok/40 bg-ok/10 text-ok',
  Overstaying: 'border-danger/40 bg-danger/10 text-danger',
  Released: 'border-line bg-surface text-muted',
}

export function StatusBadge({ status }: { status: ContainerStatus }) {
  return <span className={`badge ${STATUS_STYLE[status]}`}>{status}</span>
}

const CLASS_STYLE: Record<DwellClass, string> = {
  'Short-stay': 'border-zone-fast/40 bg-zone-fast/10 text-zone-fast',
  'Medium-stay': 'border-zone-medium/40 bg-zone-medium/10 text-zone-medium',
  'Long-stay': 'border-zone-long/40 bg-zone-long/10 text-zone-long',
}

export function DwellClassBadge({ value }: { value: DwellClass | null }) {
  if (!value) return <span className="text-muted">—</span>
  return <span className={`badge ${CLASS_STYLE[value]}`}>{value}</span>
}
