// 24 bars, one per hour of a day: how congested the gate is expected to be. Click a bar to pick that hour.
// Used by the booking form (so a driver looks at the gate before choosing a time) and by the gate monitor.

export const STATUS = {
  normal: { label: 'Normal', dot: 'bg-green-500', text: 'text-green-700', bar: 'bg-green-500' },
  busy: { label: 'Busy', dot: 'bg-amber-500', text: 'text-amber-700', bar: 'bg-amber-500' },
  congested: { label: 'Congested', dot: 'bg-red-500', text: 'text-red-700', bar: 'bg-red-500' },
  closed: { label: 'Closed', dot: 'bg-gray-400', text: 'text-gray-600', bar: 'bg-gray-400' },
}

export const pad = (n) => String(n).padStart(2, '0')

export function Legend() {
  return (
    <div className="flex gap-3 text-[11px] text-gray-500">
      {['normal', 'busy', 'congested'].map((key) => (
        <span key={key} className="flex items-center gap-1">
          <span className={`h-2 w-2 rounded-full ${STATUS[key].dot}`} />
          {STATUS[key].label}
        </span>
      ))}
    </div>
  )
}

export default function HourChart({ profile, hour, onPick, height = 'h-32' }) {
  const scale = Math.max(14, ...profile.map((r) => r.max_lane_queue))
  return (
    <div>
      <div className={`flex ${height} items-end gap-1`} role="group" aria-label="Congestion by hour">
        {profile.map((r) => (
          <button
            key={r.hour}
            type="button"
            onClick={() => onPick(r.hour)}
            aria-label={`${pad(r.hour)}:00, ${STATUS[r.status].label}, ${r.max_lane_queue} trucks queued`}
            title={`${pad(r.hour)}:00 - ${STATUS[r.status].label}: ${r.max_lane_queue} trucks in the worst lane, ~${r.avg_wait_minutes} min wait, ${r.booked} booked`}
            className="flex h-full flex-1 flex-col justify-end"
          >
            <span
              className={`block rounded-t ${STATUS[r.status].bar} ${
                r.hour === hour ? 'ring-2 ring-[#123a5c] ring-offset-1' : 'opacity-70 hover:opacity-100'
              }`}
              style={{ height: `${Math.max(5, (r.max_lane_queue / scale) * 100)}%` }}
            />
          </button>
        ))}
      </div>
      <div className="mt-1 flex gap-1 text-[10px] text-gray-400">
        {profile.map((r) => (
          <span key={r.hour} className="flex-1 text-center">
            {r.hour % 3 === 0 ? pad(r.hour) : ''}
          </span>
        ))}
      </div>
    </div>
  )
}
