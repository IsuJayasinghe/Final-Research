// Colours for charts (Recharts needs real colour values, not Tailwind classes).
// Keep in sync with tailwind.config.js.
export const colors = {
  accent: '#22d3ee',
  ok: '#10b981',
  warn: '#f59e0b',
  danger: '#ef4444',
  muted: '#a3b3cd',
  line: '#33496f',
  surface: '#1a2c4c',
  ink: '#e6edf7',
}

export type ZoneName = 'Fast-Access' | 'Medium-Access' | 'Long-Term' | 'Reefer' | 'Hazardous'

export const zoneStyle: Record<ZoneName, { color: string; text: string; badge: string }> = {
  'Fast-Access': { color: '#10b981', text: 'text-zone-fast', badge: 'border-zone-fast/40 bg-zone-fast/10 text-zone-fast' },
  'Medium-Access': { color: '#f59e0b', text: 'text-zone-medium', badge: 'border-zone-medium/40 bg-zone-medium/10 text-zone-medium' },
  'Long-Term': { color: '#38bdf8', text: 'text-zone-long', badge: 'border-zone-long/40 bg-zone-long/10 text-zone-long' },
  Reefer: { color: '#22d3ee', text: 'text-zone-reefer', badge: 'border-zone-reefer/40 bg-zone-reefer/10 text-zone-reefer' },
  Hazardous: { color: '#ef4444', text: 'text-zone-hazard', badge: 'border-zone-hazard/40 bg-zone-hazard/10 text-zone-hazard' },
}

export const ZONE_ORDER: ZoneName[] = ['Fast-Access', 'Medium-Access', 'Long-Term', 'Reefer', 'Hazardous']
