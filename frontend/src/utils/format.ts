// Display helpers shared by the pages

export function formatDays(days: number | null | undefined, digits = 1) {
  return days == null ? '—' : `${days.toFixed(digits)} ${days.toFixed(digits) === '1.0' ? 'day' : 'days'}`
}

export function formatPct(value: number | null | undefined, digits = 1) {
  return value == null ? '—' : `${value.toFixed(digits)}%`
}

export function formatNumber(value: number | null | undefined) {
  return value == null ? '—' : value.toLocaleString()
}

export function formatDateTime(iso: string | null | undefined) {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleString(undefined, { year: 'numeric', month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

export function formatDate(iso: string | null | undefined) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: '2-digit' })
}

/** Colour for a utilisation percentage: green below 70%, amber below 85%, red at 85%+ (FR08). */
export function utilizationColor(pct: number) {
  if (pct >= 85) return '#ef4444'
  if (pct >= 70) return '#f59e0b'
  return '#10b981'
}
