import { AlertTriangle, Ban, Clock, Gauge, RefreshCw, Siren, Truck } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import HourChart, { Legend, STATUS, pad } from '../../components/HourChart'
import {
  closeLane,
  getClosures,
  getCongestionProfile,
  getLaneView,
  rebalanceLanes,
  reopenLane,
} from '../../lib/gateApi'
import { useRole } from '../../lib/role'
import { STATUS_LABEL, hhmm } from '../../lib/status'

const localDate = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`

function docState(a) {
  if (a.missing_documents === null) return { label: 'Docs unchecked', cls: 'bg-blue-50 text-blue-700' }
  if (a.missing_documents === 0) return { label: 'Docs cleared', cls: 'bg-green-50 text-green-700' }
  return { label: 'Docs incomplete', cls: 'bg-red-50 text-red-700' }
}

function LaneCard({ data, mine }) {
  const status = STATUS[data.status]
  const closed = data.status === 'closed'
  const barPct = closed ? 0 : Math.min(100, (data.predicted_queue_length / 14) * 100)
  const hasMine = data.bookings.some((b) => mine && b.truck_id.toUpperCase() === mine)
  return (
    <div
      className={`rounded-xl border bg-white p-5 shadow-sm ${closed ? 'border-gray-300 bg-gray-50' : 'border-gray-200'} ${
        hasMine ? 'ring-2 ring-[#123a5c]' : ''
      }`}
    >
      <div className="flex items-center justify-between">
        <h3 className="text-base font-bold text-[#123a5c]">
          Gate {data.lane}
          {hasMine && <span className="ml-2 rounded-full bg-[#123a5c] px-2 py-0.5 text-[10px] font-semibold text-white">your gate</span>}
        </h3>
        <span className={`flex items-center gap-1.5 text-xs font-semibold ${status.text}`}>
          <span className={`h-2 w-2 rounded-full ${status.dot}`} />
          {status.label}
        </span>
      </div>

      {closed ? (
        <p className="mt-3 flex items-start gap-2 rounded-md bg-gray-100 p-3 text-xs text-gray-600">
          <Ban className="mt-0.5 h-4 w-4 shrink-0" />
          Out of service ({data.closed_reason}). Drivers booked here are moved to another gate automatically.
        </p>
      ) : (
        <>
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
        </>
      )}

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
              const isMine = mine && b.truck_id.toUpperCase() === mine
              return (
                <li
                  key={b.id}
                  className={`flex items-center justify-between gap-2 rounded-md text-xs ${isMine ? 'bg-[#123a5c]/10 p-1.5 ring-1 ring-[#123a5c]/40' : ''}`}
                >
                  <div className="min-w-0">
                    <p className="truncate font-medium text-gray-800">
                      {b.truck_id} · {b.container_id}
                      {isMine && <span className="ml-1 font-semibold text-[#123a5c]">(you)</span>}
                    </p>
                    <p className="text-gray-500">
                      {b.container_type} · {STATUS_LABEL[b.status]?.toLowerCase() ?? b.status.toLowerCase()} · no-show {Math.round(b.p_no_show * 100)}%
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

// gate admin: take a lane out of service, reopen it, and re-check lane balance
function GateControls({ date, hour, closures, onChanged }) {
  const [lane, setLane] = useState(3)
  const [hours, setHours] = useState(3)
  const [reason, setReason] = useState('crane breakdown')
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState(null)
  const [error, setError] = useState(null)

  const run = async (fn, summarize) => {
    setBusy(true)
    setError(null)
    try {
      const out = await fn()
      setMessage(summarize(out))
      await onChanged()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const moved = (out) => {
    const n = (out.lane_changes ?? []).length
    return n === 0 ? 'Done. No driver needed to change gate.' : `Done. ${n} driver(s) were moved to another gate and notified.`
  }

  return (
    <section className="mt-6 rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-500">Gate admin controls</h2>
      <div className="mt-3 flex flex-wrap items-end gap-3">
        <div>
          <label htmlFor="closeLane" className="block text-xs font-medium text-gray-600">
            Lane
          </label>
          <select id="closeLane" value={lane} onChange={(e) => setLane(Number(e.target.value))} className="rounded-md border border-gray-300 px-2 py-1.5 text-sm">
            {[1, 2, 3, 4, 5, 6].map((n) => (
              <option key={n} value={n}>
                Gate {n}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="closeHours" className="block text-xs font-medium text-gray-600">
            Hours from {pad(hour)}:00
          </label>
          <input
            id="closeHours"
            type="number"
            min="1"
            max="48"
            value={hours}
            onChange={(e) => setHours(Number(e.target.value))}
            className="w-20 rounded-md border border-gray-300 px-2 py-1.5 text-sm"
          />
        </div>
        <div>
          <label htmlFor="closeReason" className="block text-xs font-medium text-gray-600">
            Reason (drivers see it)
          </label>
          <input
            id="closeReason"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            className="w-52 rounded-md border border-gray-300 px-2 py-1.5 text-sm"
          />
        </div>
        <button
          type="button"
          disabled={busy}
          onClick={() =>
            run(() => closeLane({ lane, hours, start: `${date}T${pad(hour)}:00`, reason }), moved)
          }
          className="rounded-md bg-red-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-red-700 disabled:opacity-60"
        >
          Close lane
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() => run(() => rebalanceLanes(), moved)}
          className="rounded-md border border-gray-300 px-3 py-1.5 text-xs font-semibold text-gray-700 hover:bg-gray-50 disabled:opacity-60"
        >
          Rebalance lanes now
        </button>
      </div>

      {closures.length > 0 && (
        <ul className="mt-3 space-y-1 text-xs text-gray-700">
          {closures.map((c) => (
            <li key={`${c.lane}-${c.start}`} className="flex flex-wrap items-center gap-2">
              <span className="rounded-full bg-gray-100 px-2 py-0.5 font-medium">Gate {c.lane} closed</span>
              <span>
                {c.start.replace('T', ' ').slice(5, 16)} to {c.end.replace('T', ' ').slice(5, 16)} - {c.reason}
              </span>
              <button
                type="button"
                disabled={busy}
                onClick={() => run(() => reopenLane(c.lane), () => `Gate ${c.lane} reopened.`)}
                className="font-semibold text-[#123a5c] underline"
              >
                Reopen
              </button>
            </li>
          ))}
        </ul>
      )}
      {message && <p className="mt-3 text-xs font-medium text-green-700">{message}</p>}
      {error && <p className="mt-3 text-xs font-medium text-red-700">{error}</p>}
      <p className="mt-3 text-xs text-gray-500">
        Closing a lane or a queue spike on one gate moves booked drivers to a lighter gate. Their time slot stays the same;
        each driver is told the new gate and why.
      </p>
    </section>
  )
}

export default function GateAllocationView() {
  const { role, myTruck } = useRole()
  const [params] = useSearchParams()
  const initial = useMemo(() => {
    const next = new Date(Date.now() + 3600 * 1000) // the next full hour
    const hourParam = Number(params.get('hour'))
    return {
      date: params.get('date') || localDate(next),
      hour: params.get('hour') !== null && hourParam >= 0 && hourParam <= 23 ? hourParam : next.getHours(),
    }
    // only the first render reads the link; later changes come from the controls
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
  const [date, setDate] = useState(initial.date)
  const [hour, setHour] = useState(initial.hour)
  const [profile, setProfile] = useState([])
  const [view, setView] = useState(null)
  const [closures, setClosures] = useState([])
  const [lastUpdated, setLastUpdated] = useState(new Date())
  const [error, setError] = useState(null)

  // whose truck to highlight: the one in the link (from My Trip), else the driver's own
  const mine = (params.get('truck') || (role === 'driver' ? myTruck : '')).trim().toUpperCase()

  const load = useCallback(async () => {
    try {
      const [p, v, c] = await Promise.all([getCongestionProfile(date), getLaneView(date, hour), getClosures()])
      setProfile(p)
      setView(v)
      setClosures(c)
      setLastUpdated(new Date())
      setError(null)
    } catch (err) {
      setError(
        err instanceof TypeError ? 'Could not reach the gate allocation service. Is the backend running?' : err.message,
      )
    }
  }, [date, hour])

  // reload when the chosen date/hour changes, and every 10 s so approvals, gate changes and disruptions show up live
  useEffect(() => {
    load()
    const interval = setInterval(load, 10000)
    return () => clearInterval(interval)
  }, [load])

  const lanes = view?.lanes ?? []
  const openLanes = lanes.filter((l) => l.status !== 'closed')
  const summary = useMemo(() => {
    if (openLanes.length === 0) return { totalQueue: 0, avgWait: 0, balanced: true, variance: '0.0' }
    const totalQueue = Math.round(openLanes.reduce((s, l) => s + l.predicted_queue_length, 0) * 10) / 10
    const avgWait = Math.round(openLanes.reduce((s, l) => s + l.predicted_avg_wait_minutes, 0) / openLanes.length)
    const mean = totalQueue / openLanes.length
    const variance = openLanes.reduce((s, l) => s + (l.predicted_queue_length - mean) ** 2, 0) / openLanes.length
    return { totalQueue, avgWait, balanced: variance <= 6, variance: variance.toFixed(1) }
  }, [openLanes])

  const congested = openLanes.filter((l) => l.status === 'congested')
  const peak = profile.length ? profile.reduce((a, b) => (b.max_lane_queue > a.max_lane_queue ? b : a)) : null
  const quiet = profile.length ? profile.reduce((a, b) => (b.max_lane_queue < a.max_lane_queue ? b : a)) : null
  const selectedRow = profile.find((r) => r.hour === hour)
  const myBooking = mine ? lanes.flatMap((l) => l.bookings).find((b) => b.truck_id.toUpperCase() === mine) : null

  return (
    <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6 lg:px-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-[#123a5c]">
            {role === 'admin' ? 'Gate Allocation & Lane Monitoring' : 'Gate Status'}
          </h1>
          <p className="mt-1 text-sm text-gray-600">
            Forecast congestion for each of the 6 gate lanes in any hour, with the trucks booked on each lane. Updates every
            10 seconds.
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

      {error && <div className="mt-6 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div>}

      {mine && (
        <div className="mt-6 rounded-xl border border-[#123a5c]/30 bg-[#123a5c]/5 p-4 text-sm text-[#123a5c]">
          {myBooking ? (
            <>
              <b>{mine}</b> is booked on <b>Gate {myBooking.lane}</b> at {hhmm(myBooking.assigned_slot)} ({STATUS_LABEL[myBooking.status]?.toLowerCase()}). Your gate is highlighted below.{' '}
              <Link to="/my-trip" className="font-semibold underline">
                Open My Trip
              </Link>
            </>
          ) : (
            <>
              <b>{mine}</b> has no booking in this hour. Pick the hour of your slot, or{' '}
              <Link to="/my-trip" className="font-semibold underline">
                open My Trip
              </Link>
              .
            </>
          )}
        </div>
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
          <Legend />
        </div>
        <div className="mt-4">
          {profile.length === 0 ? (
            <p className="text-sm text-gray-500">Loading the day&apos;s forecast...</p>
          ) : (
            <HourChart profile={profile} hour={hour} onPick={setHour} />
          )}
          <p className="mt-2 text-xs text-gray-500">
            Bar height = forecast queue in the busiest open lane. Showing <b>{pad(hour)}:00</b>
            {selectedRow && (
              <>
                : <b className={STATUS[selectedRow.status].text}>{STATUS[selectedRow.status].label}</b>,{' '}
                {selectedRow.max_lane_queue} trucks queued in the worst lane, {selectedRow.booked} booked in this hour.
              </>
            )}
          </p>
        </div>
      </section>

      {role === 'admin' && <GateControls date={date} hour={hour} closures={closures} onChanged={load} />}

      {/* Summary stats */}
      <div className="mt-6 grid gap-4 sm:grid-cols-4">
        {[
          { icon: Truck, label: 'Forecast queue (open lanes)', value: summary.totalQueue },
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
            <b>Active disruption in this hour:</b> forecast congestion is raised by <b>{view.disruption.uplift_pct}%</b>
            {view.disruption.lane && <> at <b>Gate {view.disruption.lane}</b></>}
            {view.disruption.vessel_delay_hours > 0 && <> (vessel delayed {view.disruption.vessel_delay_hours} h)</>}
            {view.disruption.queue_spike_pct > 0 && <> (queue spike +{view.disruption.queue_spike_pct}%)</>}.{' '}
            {role === 'admin' && (
              <Link to="/gate-optimization" className="font-semibold underline">
                Re-plan affected bookings
              </Link>
            )}
          </p>
        </div>
      )}

      {congested.length > 0 && (
        <div className="mt-6 flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4">
          <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-red-600" />
          <div className="flex-1 text-sm">
            <p className="font-semibold text-red-700">
              {congested.length === openLanes.length
                ? 'All open gate lanes are congested'
                : `Gate ${congested.map((l) => l.lane).join(', ')} ${congested.length > 1 ? 'are' : 'is'} congested`}{' '}
              at {pad(hour)}:00 (worst lane: {Math.max(...congested.map((l) => l.predicted_queue_length))} trucks queued).
            </p>
            <p className="mt-1 text-red-600">
              {role === 'admin' ? (
                <>
                  Bookings that have not arrived yet can be moved to a quieter hour.{' '}
                  <Link to="/gate-optimization" className="font-semibold underline">
                    Open Slot Optimization
                  </Link>
                </>
              ) : (
                'Expect longer waits in this hour. Your gate and time update automatically if the gate admin or the system changes them.'
              )}
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
            <LaneCard key={laneData.lane} data={laneData} mine={mine} />
          ))}
        </div>
      )}

      <div className="mt-6 rounded-xl border border-gray-200 bg-white p-4 text-sm text-gray-500">
        Queue length and wait time are the trained per-lane SARIMAX forecasts for the chosen hour (busy from 4 trucks queued,
        congested from 8), raised by any active disruption. The booked trucks are the real appointments assigned to each
        lane, spread across lanes so a busy hour does not pile onto one gate.
      </div>
    </div>
  )
}
