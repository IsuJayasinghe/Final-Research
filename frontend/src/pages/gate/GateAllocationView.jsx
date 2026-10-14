import { AlertTriangle, Clock, Gauge, RefreshCw, Siren, Truck } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { getCongestionProfile, getLaneView } from '../../lib/gateApi'

const STATUS = {
  normal: { label: 'Normal', dot: 'bg-green-500', text: 'text-green-700', bar: 'bg-green-500' },
  busy: { label: 'Busy', dot: 'bg-amber-500', text: 'text-amber-700', bar: 'bg-amber-500' },
  congested: { label: 'Congested', dot: 'bg-red-500', text: 'text-red-700', bar: 'bg-red-500' },
}

const pad = (n) => String(n).padStart(2, '0')
const localDate = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`

function docState(a) {
  if (a.missing_documents === null) return { label: 'Docs unchecked', cls: 'bg-blue-50 text-blue-700' }
  if (a.missing_documents === 0) return { label: 'Docs cleared', cls: 'bg-green-50 text-green-700' }
  return { label: 'Docs incomplete', cls: 'bg-red-50 text-red-700' }
}

function LaneCard({ data }) {
  const status = STATUS[data.status]
  const barPct = Math.min(100, (data.predicted_queue_length / 14) * 100)
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between">
        <h3 className="text-base font-bold text-[#123a5c]">Gate {data.lane}</h3>
        <span className={`flex items-center gap-1.5 text-xs font-semibold ${status.text}`}>
          <span className={`h-2 w-2 rounded-full ${status.dot}`} />
          {status.label}
        </span>
      </div>

      <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-gray-100">
        <div className={`h-full rounded-full ${status.bar}`} style={{ width: `${barPct}%` }} />
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
        <div>
          <p className="text-xs text-gray-500">Forecast queue</p>
          <p className="font-semibold text-gray-800">{data.predicted_queue_length} trucks</p>
        </div>
        <div>
          <p className="text-xs text-gray-500">Expected wait</p>
          <p className="font-semibold text-gray-800">{data.predicted_avg_wait_minutes} min</p>
        </div>
      </div>

      <div className="mt-4 border-t border-gray-100 pt-3">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
          Booked trucks this hour ({data.bookings.length})
        </p>
        {data.bookings.length === 0 ? (
          <p className="text-sm text-gray-400">No bookings on this lane in this hour.</p>
        ) : (
          <ul className="space-y-2">
            {data.bookings.map((b) => {
              const doc = docState(b)
              return (
                <li key={b.id} className="flex items-center justify-between gap-2 text-xs">
                  <div className="min-w-0">
                    <p className="truncate font-medium text-gray-800">
                      {b.truck_id} · {b.container_id}
                    </p>
                    <p className="text-gray-500">
                      {b.container_type} · {b.status.toLowerCase()} · no-show {Math.round(b.p_no_show * 100)}%
                    </p>
                  </div>
                  <span className={`shrink-0 rounded-full px-2 py-0.5 font-medium ${doc.cls}`}>{doc.label}</span>
                </li>
              )
            })}
          </ul>
        )}
      </div>
    </div>
  )
}

// 24 bars, one per hour of the day: how congested the gate is expected to be. Click a bar to look at that hour.
function HourChart({ profile, hour, onPick }) {
  const scale = Math.max(14, ...profile.map((r) => r.max_lane_queue))
  return (
    <div>
      <div className="flex h-32 items-end gap-1" role="group" aria-label="Congestion by hour">
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
              className={`block rounded-t ${STATUS[r.status].bar} ${r.hour === hour ? 'ring-2 ring-[#123a5c] ring-offset-1' : 'opacity-70 hover:opacity-100'}`}
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

export default function GateAllocationView() {
  const initial = useMemo(() => {
    const next = new Date(Date.now() + 3600 * 1000) // the next full hour
    return { date: localDate(next), hour: next.getHours() }
  }, [])
  const [date, setDate] = useState(initial.date)
  const [hour, setHour] = useState(initial.hour)
  const [profile, setProfile] = useState([])
  const [view, setView] = useState(null)
  const [lastUpdated, setLastUpdated] = useState(new Date())
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    try {
      const [p, v] = await Promise.all([getCongestionProfile(date), getLaneView(date, hour)])
      setProfile(p)
      setView(v)
      setLastUpdated(new Date())
      setError(null)
    } catch (err) {
      setError(
        err instanceof TypeError
          ? 'Could not reach the gate allocation service. Is the backend running?'
          : err.message,
      )
    }
  }, [date, hour])

  // reload when the chosen date/hour changes, and every 20 s so new bookings and disruptions show up
  useEffect(() => {
    load()
    const interval = setInterval(load, 20000)
    return () => clearInterval(interval)
  }, [load])

  const lanes = view?.lanes ?? []
  const summary = useMemo(() => {
    if (lanes.length === 0) return { totalQueue: 0, avgWait: 0, balanced: true, variance: '0.0' }
    const totalQueue = Math.round(lanes.reduce((s, l) => s + l.predicted_queue_length, 0) * 10) / 10
    const avgWait = Math.round(lanes.reduce((s, l) => s + l.predicted_avg_wait_minutes, 0) / lanes.length)
    const mean = totalQueue / lanes.length
    const variance = lanes.reduce((s, l) => s + (l.predicted_queue_length - mean) ** 2, 0) / lanes.length
    return { totalQueue, avgWait, balanced: variance <= 6, variance: variance.toFixed(1) }
  }, [lanes])

  const congested = lanes.filter((l) => l.status === 'congested')
  const peak = profile.length ? profile.reduce((a, b) => (b.max_lane_queue > a.max_lane_queue ? b : a)) : null
  const quiet = profile.length ? profile.reduce((a, b) => (b.max_lane_queue < a.max_lane_queue ? b : a)) : null
  const selectedRow = profile.find((r) => r.hour === hour)

  return (
    <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6 lg:px-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-[#123a5c]">Gate Allocation & Lane Monitoring</h1>
          <p className="mt-1 text-sm text-gray-600">
            Forecast congestion for each of the 6 gate lanes in any hour, with the trucks booked on each lane.
          </p>
        </div>
        <div className="flex items-center gap-3 text-sm text-gray-500">
          <span>
            Updated {lastUpdated.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
          </span>
          <button
            type="button"
            onClick={load}
            className="flex items-center gap-1.5 rounded-md border border-gray-300 px-3 py-1.5 font-medium text-[#123a5c] hover:bg-gray-50"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="mt-6 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div>
      )}

      {/* Which hour to look at */}
      <section className="mt-6 rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div className="flex flex-wrap items-end gap-3">
            <div>
              <label htmlFor="monitorDate" className="block text-xs font-medium text-gray-600">
                Date
              </label>
              <input
                id="monitorDate"
                type="date"
                value={date}
                onChange={(e) => e.target.value && setDate(e.target.value)}
                className="rounded-md border border-gray-300 px-2 py-1.5 text-sm"
              />
            </div>
            <div>
              <label htmlFor="monitorHour" className="block text-xs font-medium text-gray-600">
                Hour
              </label>
              <select
                id="monitorHour"
                value={hour}
                onChange={(e) => setHour(Number(e.target.value))}
                className="rounded-md border border-gray-300 px-2 py-1.5 text-sm"
              >
                {Array.from({ length: 24 }, (_, h) => (
                  <option key={h} value={h}>
                    {pad(h)}:00
                  </option>
                ))}
              </select>
            </div>
            <button
              type="button"
              disabled={!peak}
              onClick={() => peak && setHour(peak.hour)}
              className="rounded-md bg-red-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-red-700 disabled:opacity-50"
            >
              Show busiest hour{peak ? ` (${pad(peak.hour)}:00)` : ''}
            </button>
            <button
              type="button"
              disabled={!quiet}
              onClick={() => quiet && setHour(quiet.hour)}
              className="rounded-md border border-gray-300 px-3 py-1.5 text-xs font-semibold text-gray-700 hover:bg-gray-50 disabled:opacity-50"
            >
              Show quietest hour{quiet ? ` (${pad(quiet.hour)}:00)` : ''}
            </button>
          </div>
          <div className="flex gap-3 text-[11px] text-gray-500">
            {Object.entries(STATUS).map(([key, s]) => (
              <span key={key} className="flex items-center gap-1">
                <span className={`h-2 w-2 rounded-full ${s.dot}`} />
                {s.label}
              </span>
            ))}
          </div>
        </div>
        <div className="mt-4">
          {profile.length === 0 ? (
            <p className="text-sm text-gray-500">Loading the day&apos;s forecast...</p>
          ) : (
            <HourChart profile={profile} hour={hour} onPick={setHour} />
          )}
          <p className="mt-2 text-xs text-gray-500">
            Bar height = forecast queue in the busiest lane. Showing <b>{pad(hour)}:00</b>
            {selectedRow && (
              <>
                : <b className={STATUS[selectedRow.status].text}>{STATUS[selectedRow.status].label}</b>,{' '}
                {selectedRow.max_lane_queue} trucks queued in the worst lane, {selectedRow.booked} booked in this hour.
              </>
            )}
          </p>
        </div>
      </section>

      {/* Summary stats */}
      <div className="mt-6 grid gap-4 sm:grid-cols-4">
        {[
          { icon: Truck, label: 'Forecast queue (all lanes)', value: summary.totalQueue },
          { icon: Clock, label: 'Average expected wait', value: `${summary.avgWait} min` },
          { icon: Truck, label: 'Trucks booked this hour', value: view?.booked_total ?? 0 },
        ].map(({ icon: Icon, label, value }) => (
          <div key={label} className="flex items-center gap-3 rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
            <span className="flex h-10 w-10 items-center justify-center rounded-full bg-[#123a5c]/10 text-[#123a5c]">
              <Icon className="h-5 w-5" />
            </span>
            <div>
              <p className="text-xs text-gray-500">{label}</p>
              <p className="text-xl font-bold text-gray-800">{value}</p>
            </div>
          </div>
        ))}
        <div className="flex items-center gap-3 rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <span className="flex h-10 w-10 items-center justify-center rounded-full bg-[#123a5c]/10 text-[#123a5c]">
            <Gauge className="h-5 w-5" />
          </span>
          <div>
            <p className="text-xs text-gray-500">Lane load balance</p>
            <p className={`text-xl font-bold ${summary.balanced ? 'text-green-700' : 'text-amber-700'}`}>
              {summary.balanced ? 'Balanced' : 'Imbalanced'}{' '}
              <span className="text-xs font-normal text-gray-400">(var {summary.variance})</span>
            </p>
          </div>
        </div>
      </div>

      {view?.disruption && (
        <div className="mt-6 flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          <Siren className="mt-0.5 h-5 w-5 shrink-0 text-amber-600" />
          <p>
            <b>Active disruption in this hour:</b> forecast congestion is raised by{' '}
            <b>{view.disruption.uplift_pct}%</b>
            {view.disruption.vessel_delay_hours > 0 && <> (vessel delayed {view.disruption.vessel_delay_hours} h)</>}
            {view.disruption.queue_spike_pct > 0 && <> (queue spike +{view.disruption.queue_spike_pct}%)</>}.{' '}
            <Link to="/gate-optimization" className="font-semibold underline">
              Re-plan affected bookings
            </Link>
          </p>
        </div>
      )}

      {congested.length > 0 && (
        <div className="mt-6 flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4">
          <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-red-600" />
          <div className="flex-1 text-sm">
            <p className="font-semibold text-red-700">
              {congested.length === lanes.length
                ? 'All gate lanes are congested'
                : `Gate ${congested.map((l) => l.lane).join(', ')} ${congested.length > 1 ? 'are' : 'is'} congested`}{' '}
              at {pad(hour)}:00 (worst lane: {Math.max(...congested.map((l) => l.predicted_queue_length))} trucks queued).
            </p>
            <p className="mt-1 text-red-600">
              Bookings that have not arrived yet can be moved to a quieter hour.{' '}
              <Link to="/gate-optimization" className="font-semibold underline">
                Open Slot Optimization
              </Link>
            </p>
          </div>
        </div>
      )}

      {/* Lane grid */}
      {lanes.length === 0 && !error ? (
        <p className="mt-6 text-sm text-gray-500">Loading lane data...</p>
      ) : (
        <div className="mt-6 grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
          {lanes.map((laneData) => (
            <LaneCard key={laneData.lane} data={laneData} />
          ))}
        </div>
      )}

      <div className="mt-6 rounded-xl border border-gray-200 bg-white p-4 text-sm text-gray-500">
        Queue length and wait time are the trained per-lane SARIMAX forecasts for the chosen hour (busy from 4 trucks queued,
        congested from 8). The booked trucks are the real appointments assigned to each lane, spread across lanes so a busy
        hour does not pile onto one gate.
      </div>
    </div>
  )
}
