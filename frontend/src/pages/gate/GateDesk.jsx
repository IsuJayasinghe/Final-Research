import { CheckCircle2, ChevronDown, ChevronRight, Loader2, LogIn, RefreshCw, UserX } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { checkInAppointment, completeAppointment, getGateDesk, markNoShow } from '../../lib/gateApi'
import { STATUS_LABEL, STATUS_STYLES, hhmm } from '../../lib/status'
import BookingDetails from './BookingDetails'

const GATES = [1, 2, 3, 4, 5, 6]

const todayLocal = () => {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

// remembers which gate this officer works at, so a reload keeps their desk
const savedGate = () => {
  try {
    const n = Number(localStorage.getItem('gateDeskLane'))
    return GATES.includes(n) ? n : 1
  } catch {
    return 1
  }
}

const SHOWN = { CONFIRMED: 'Expected', ARRIVED: 'At gate', COMPLETED: 'Done', NO_SHOW: 'No-show' }
const COUNT_STYLES = {
  CONFIRMED: 'text-[#123a5c]',
  ARRIVED: 'text-amber-600',
  COMPLETED: 'text-green-600',
  NO_SHOW: 'text-red-600',
}

function when(minutes) {
  if (minutes > 60) return `in ${Math.floor(minutes / 60)} h ${minutes % 60} min`
  if (minutes > 0) return `in ${minutes} min`
  if (minutes > -60) return `${-minutes} min ago`
  return `${Math.floor(-minutes / 60)} h ago`
}

export default function GateDesk() {
  const [lane, setLane] = useState(savedGate)
  const [date, setDate] = useState(todayLocal)
  const [desks, setDesks] = useState({}) // lane -> desk for the chosen date
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [busyId, setBusyId] = useState(null)
  const [expanded, setExpanded] = useState({}) // booking id -> details shown
  const [lastUpdated, setLastUpdated] = useState(new Date())

  const load = useCallback(async () => {
    try {
      const all = await Promise.all(GATES.map((n) => getGateDesk(n, date)))
      setDesks(Object.fromEntries(all.map((d) => [d.lane, d])))
      setLastUpdated(new Date())
      setError(null)
    } catch (err) {
      setError(
        err instanceof TypeError ? 'Could not reach the gate appointment service. Is the backend running?' : err.message,
      )
    } finally {
      setLoading(false)
    }
  }, [date])

  useEffect(() => {
    setLoading(true)
    load()
    const interval = setInterval(load, 10000)
    return () => clearInterval(interval)
  }, [load])

  const pick = (n) => {
    setLane(n)
    try {
      localStorage.setItem('gateDeskLane', String(n))
    } catch {
      // the choice just is not remembered
    }
  }

  const act = async (fn, id) => {
    setBusyId(id)
    try {
      await fn(id)
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusyId(null)
    }
  }

  const desk = desks[lane]
  const open = (d) => (d ? d.counts.CONFIRMED + d.counts.ARRIVED : 0)

  return (
    <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6 lg:px-8">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-[#123a5c]">Gate Desk</h1>
          <p className="mt-1 text-sm text-gray-600">
            Choose your gate to see its approved trucks for the day. Check each truck in when it arrives and complete the
            gate process when it is released.
          </p>
        </div>
        <div className="flex items-end gap-3">
          <div>
            <label htmlFor="deskDate" className="block text-xs font-medium text-gray-600">
              Date
            </label>
            <input
              id="deskDate"
              type="date"
              value={date}
              onChange={(e) => e.target.value && setDate(e.target.value)}
              className="mt-1 rounded-md border border-gray-300 px-3 py-1.5 text-sm"
            />
          </div>
          <button
            type="button"
            onClick={load}
            className="inline-flex items-center gap-1.5 rounded-md border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
        </div>
      </div>
      <p className="mt-1 text-right text-xs text-gray-500">
        Updated {lastUpdated.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })} · refreshes every 10 s
      </p>

      {error && <div className="mt-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div>}

      <div role="tablist" aria-label="Choose your gate" className="mt-4 grid grid-cols-3 gap-2 sm:grid-cols-6">
        {GATES.map((n) => {
          const d = desks[n]
          const active = n === lane
          return (
            <button
              key={n}
              type="button"
              role="tab"
              aria-selected={active}
              onClick={() => pick(n)}
              className={`rounded-xl border p-3 text-left transition-colors ${
                active ? 'border-[#123a5c] bg-[#123a5c] text-white' : 'border-gray-200 bg-white text-gray-700 hover:border-[#123a5c]/50'
              }`}
            >
              <span className="block text-sm font-semibold">Gate {n}</span>
              <span className={`block text-xs ${active ? 'text-white/80' : 'text-gray-500'}`}>
                {d ? `${open(d)} to process` : '...'}
              </span>
              {d?.closures.length > 0 && (
                <span className={`mt-1 inline-block rounded-full px-1.5 py-0.5 text-[10px] font-semibold ${active ? 'bg-white/20' : 'bg-red-50 text-red-700'}`}>
                  closed
                </span>
              )}
            </button>
          )
        })}
      </div>

      {loading && !desk ? (
        <div className="mt-6 flex items-center gap-2 text-sm text-gray-500">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading Gate {lane}...
        </div>
      ) : desk ? (
        <section className="mt-6 rounded-xl border border-gray-200 bg-white shadow-sm">
          <div className="grid grid-cols-2 gap-3 border-b border-gray-100 p-4 sm:grid-cols-5">
            {Object.keys(SHOWN).map((s) => (
              <div key={s}>
                <p className="text-xs text-gray-500">{SHOWN[s]}</p>
                <p className={`text-2xl font-bold ${COUNT_STYLES[s]}`}>{desk.counts[s]}</p>
              </div>
            ))}
            <div>
              <p className="text-xs text-gray-500">Forecast queue at {String(desk.queue_hour).padStart(2, '0')}:00</p>
              <p className="text-2xl font-bold text-gray-700">{desk.queue_now === null ? 'closed' : `${desk.queue_now} trucks`}</p>
            </div>
          </div>

          {desk.closures.map((c) => (
            <div key={c.start} className="border-b border-red-100 bg-red-50 px-4 py-2 text-xs text-red-800">
              Gate {desk.lane} is closed {c.start.slice(11, 16)} to {c.end.slice(11, 16)} ({c.reason}). Trucks booked in that
              window were moved to other gates.
            </div>
          ))}

          {desk.bookings.length === 0 ? (
            <p className="p-6 text-sm text-gray-500">
              No approved trucks on Gate {desk.lane} for {desk.date}. Approve requests under{' '}
              <Link to="/admin/approvals" className="font-medium text-[#123a5c] underline">
                Approvals
              </Link>
              .
            </p>
          ) : (
            <ul className="divide-y divide-gray-100">
              {desk.bookings.map((b) => {
                const finished = b.status === 'COMPLETED' || b.status === 'NO_SHOW'
                const shown = !!expanded[b.id]
                return (
                  <li key={b.id} className={`${b.next_up ? 'bg-blue-50/60' : ''} ${finished ? 'opacity-70' : ''}`}>
                    <div className="flex flex-wrap items-center justify-between gap-3 p-4">
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-[#123a5c]">
                        {hhmm(b.assigned_slot)} · {b.truck_id} · {b.container_id}
                        {b.next_up && <span className="ml-2 rounded-full bg-[#123a5c] px-2 py-0.5 text-[10px] font-semibold text-white">next</span>}
                      </p>
                      <p className="mt-0.5 text-xs text-gray-500">
                        {b.carrier} · {b.container_type} · {b.cargo_category}
                        {!finished && <> · slot {when(b.minutes_to_slot)}</>}
                      </p>
                      <p className="mt-1 text-xs text-gray-600">
                        Documents:{' '}
                        <b className={b.document_summary.cleared === b.document_summary.total ? 'text-green-700' : 'text-amber-700'}>
                          {b.document_summary.cleared === b.document_summary.total
                            ? 'all cleared'
                            : b.document_summary.cleared === 0
                              ? 'none uploaded'
                              : `${b.document_summary.cleared} of ${b.document_summary.total} cleared`}
                        </b>
                        {b.customs_risk_flag && <> · customs risk {b.customs_risk_flag}</>} · predicted clearance{' '}
                        {Math.round(b.predicted_clearance_minutes ?? 0)} min
                      </p>
                      <button
                        type="button"
                        aria-expanded={shown}
                        onClick={() => setExpanded((o) => ({ ...o, [b.id]: !o[b.id] }))}
                        className="mt-1.5 inline-flex items-center gap-1 text-xs font-semibold text-[#123a5c] hover:underline"
                      >
                        {shown ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
                        {shown ? 'Hide' : 'Show'} booking and documents ({b.document_summary.cleared}/{b.document_summary.total} cleared)
                      </button>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLES[b.status]}`}>{STATUS_LABEL[b.status]}</span>
                      {b.status === 'CONFIRMED' && (
                        <>
                          <button
                            type="button"
                            disabled={busyId === b.id}
                            onClick={() => act(checkInAppointment, b.id)}
                            className="inline-flex items-center gap-1.5 rounded-md bg-[#123a5c] px-3 py-1.5 text-xs font-semibold text-white hover:bg-[#0e2d47] disabled:opacity-60"
                          >
                            <LogIn className="h-3.5 w-3.5" />
                            Check in
                          </button>
                          <button
                            type="button"
                            disabled={busyId === b.id}
                            onClick={() => act(markNoShow, b.id)}
                            className="inline-flex items-center gap-1.5 rounded-md border border-red-300 px-3 py-1.5 text-xs font-semibold text-red-700 hover:bg-red-50 disabled:opacity-60"
                          >
                            <UserX className="h-3.5 w-3.5" />
                            No-show
                          </button>
                        </>
                      )}
                      {(b.status === 'CONFIRMED' || b.status === 'ARRIVED') && (
                        <button
                          type="button"
                          disabled={busyId === b.id}
                          onClick={() => act(completeAppointment, b.id)}
                          className="inline-flex items-center gap-1.5 rounded-md bg-green-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-green-700 disabled:opacity-60"
                        >
                          <CheckCircle2 className="h-3.5 w-3.5" />
                          Complete gate process
                        </button>
                      )}
                    </div>
                    </div>
                    {shown && <BookingDetails b={b} />}
                  </li>
                )
              })}
            </ul>
          )}
        </section>
      ) : null}
    </div>
  )
}
