import { ChevronDown, ChevronRight, Loader2, RefreshCw } from 'lucide-react'
import { Fragment, useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  cancelAppointment,
  confirmAppointment,
  getAppointmentEvents,
  listAppointments,
} from '../../lib/gateApi'

const STATUS_STYLES = {
  PENDING: 'bg-blue-50 text-blue-700',
  CONFIRMED: 'bg-green-50 text-green-700',
  WAITLISTED: 'bg-amber-50 text-amber-700',
  CANCELLED: 'bg-gray-100 text-gray-500',
}

const FILTERS = ['ALL', 'PENDING', 'CONFIRMED', 'WAITLISTED', 'CANCELLED']

const fmtSlot = (iso) => (iso ? `${iso.slice(5, 10)} ${iso.slice(11, 16)}` : '--')
const fmtDateTime = (iso) => (iso ? iso.replace('T', ' ').slice(0, 16) : '--')

function riskClass(p) {
  if (p >= 0.3) return 'text-red-600'
  if (p >= 0.15) return 'text-amber-600'
  return 'text-green-600'
}

function EventTimeline({ events }) {
  if (!events) return <p className="text-xs text-gray-400">Loading history...</p>
  return (
    <ol className="space-y-2 border-l-2 border-gray-200 pl-4">
      {events.map((e, i) => (
        <li key={i} className="text-xs text-gray-700">
          <span className="font-semibold text-[#123a5c]">{e.event_type}</span>{' '}
          <span className="text-gray-400">{fmtDateTime(e.event_time)}</span>
          {e.old_arrival || e.new_arrival ? (
            <span className="ml-2 text-gray-500">
              {fmtSlot(e.old_arrival)} &rarr; {fmtSlot(e.new_arrival)}
            </span>
          ) : null}
          {e.reason && <p className="mt-0.5 text-gray-600">{e.reason}</p>}
        </li>
      ))}
    </ol>
  )
}

export default function Appointments() {
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filter, setFilter] = useState('ALL')
  const [openId, setOpenId] = useState(null)
  const [events, setEvents] = useState({})
  const [busyId, setBusyId] = useState(null)

  const load = useCallback(async () => {
    try {
      setRows(await listAppointments())
      setError(null)
    } catch {
      setError('Could not reach the gate appointment service. Is the backend running?')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const toggle = async (id) => {
    if (openId === id) {
      setOpenId(null)
      return
    }
    setOpenId(id)
    setEvents((prev) => ({ ...prev, [id]: null }))
    try {
      const ev = await getAppointmentEvents(id)
      setEvents((prev) => ({ ...prev, [id]: ev }))
    } catch (err) {
      setError(err.message)
    }
  }

  const act = async (fn, id) => {
    setBusyId(id)
    try {
      await fn(id)
      await load()
      if (openId === id) {
        const ev = await getAppointmentEvents(id)
        setEvents((prev) => ({ ...prev, [id]: ev }))
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setBusyId(null)
    }
  }

  const shown = rows.filter((r) => filter === 'ALL' || r.status === filter)
  const counts = rows.reduce((acc, r) => ({ ...acc, [r.status]: (acc[r.status] ?? 0) + 1 }), {})

  return (
    <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6 lg:px-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-[#123a5c]">Appointments</h1>
          <p className="mt-1 text-sm text-gray-600">
            Saved bookings with the model&apos;s risk score and the reason behind every slot decision.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={load}
            className="inline-flex items-center gap-2 rounded-md border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
          <Link
            to="/gate-appointment"
            className="rounded-md bg-[#123a5c] px-3 py-2 text-sm font-semibold text-white hover:bg-[#0e2d47]"
          >
            New appointment
          </Link>
        </div>
      </div>

      <div className="mt-5 flex flex-wrap gap-2">
        {FILTERS.map((f) => (
          <button
            key={f}
            type="button"
            onClick={() => setFilter(f)}
            className={`rounded-full border px-3 py-1 text-xs font-medium ${
              filter === f
                ? 'border-[#123a5c] bg-[#123a5c] text-white'
                : 'border-gray-300 text-gray-600 hover:bg-gray-50'
            }`}
          >
            {f === 'ALL' ? `All (${rows.length})` : `${f[0]}${f.slice(1).toLowerCase()} (${counts[f] ?? 0})`}
          </button>
        ))}
      </div>

      {error && (
        <div className="mt-4 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="mt-4 overflow-x-auto rounded-xl border border-gray-200 bg-white shadow-sm">
        {loading ? (
          <div className="flex items-center gap-2 p-6 text-sm text-gray-500">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading appointments...
          </div>
        ) : shown.length === 0 ? (
          <p className="p-6 text-sm text-gray-500">
            No appointments yet.{' '}
            <Link to="/gate-appointment" className="font-medium text-[#123a5c] hover:underline">
              Request one
            </Link>
            .
          </p>
        ) : (
          <table className="w-full min-w-205 text-left text-sm">
            <thead className="bg-gray-50 text-xs uppercase tracking-wide text-gray-500">
              <tr>
                <th className="w-8 px-3 py-3" />
                <th className="px-3 py-3">#</th>
                <th className="px-3 py-3">Truck / Container</th>
                <th className="px-3 py-3">Requested</th>
                <th className="px-3 py-3">Assigned</th>
                <th className="px-3 py-3">Lane</th>
                <th className="px-3 py-3">No-show risk</th>
                <th className="px-3 py-3">Status</th>
                <th className="px-3 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {shown.map((r) => {
                const open = openId === r.id
                const moved = r.assigned_slot && r.assigned_slot !== r.requested_slot
                return (
                  <Fragment key={r.id}>
                    <tr className="border-t border-gray-100 align-top">
                      <td className="px-3 py-3">
                        <button
                          type="button"
                          aria-label={open ? 'Hide history' : 'Show history'}
                          onClick={() => toggle(r.id)}
                          className="text-gray-400 hover:text-[#123a5c]"
                        >
                          {open ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                        </button>
                      </td>
                      <td className="px-3 py-3 font-medium text-gray-800">{r.id}</td>
                      <td className="px-3 py-3">
                        <p className="font-medium text-gray-800">{r.truck_id}</p>
                        <p className="text-xs text-gray-500">
                          {r.container_id} · {r.container_type}
                        </p>
                      </td>
                      <td className="px-3 py-3 text-gray-700">{fmtSlot(r.requested_slot)}</td>
                      <td className="px-3 py-3">
                        <span className={moved ? 'font-semibold text-[#123a5c]' : 'text-gray-700'}>
                          {fmtSlot(r.assigned_slot)}
                        </span>
                        {r.overbooked && (
                          <span className="ml-2 rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-semibold text-amber-800">
                            overbooked
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-3 text-gray-700">{r.lane ? `Gate ${r.lane}` : '--'}</td>
                      <td className={`px-3 py-3 font-semibold ${riskClass(r.p_no_show)}`}>
                        {Math.round(r.p_no_show * 100)}%
                      </td>
                      <td className="px-3 py-3">
                        <span
                          className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLES[r.status] ?? ''}`}
                        >
                          {r.status}
                        </span>
                      </td>
                      <td className="px-3 py-3 text-right">
                        <div className="flex justify-end gap-2">
                          {r.status === 'PENDING' && (
                            <button
                              type="button"
                              disabled={busyId === r.id}
                              onClick={() => act(confirmAppointment, r.id)}
                              className="rounded-md bg-[#123a5c] px-2.5 py-1 text-xs font-semibold text-white hover:bg-[#0e2d47] disabled:opacity-60"
                            >
                              Confirm
                            </button>
                          )}
                          {r.status !== 'CANCELLED' && (
                            <button
                              type="button"
                              disabled={busyId === r.id}
                              onClick={() => act(cancelAppointment, r.id)}
                              className="rounded-md border border-gray-300 px-2.5 py-1 text-xs font-semibold text-gray-700 hover:bg-gray-50 disabled:opacity-60"
                            >
                              Cancel
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                    {open && (
                      <tr className="bg-gray-50">
                        <td />
                        <td colSpan={8} className="px-3 py-4">
                          <div className="grid gap-4 md:grid-cols-2">
                            <div>
                              <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                                Why this slot
                              </p>
                              <p className="mt-1 text-sm text-gray-800">{r.decision_reason || '--'}</p>
                              <p className="mt-3 text-xs font-semibold uppercase tracking-wide text-gray-500">
                                Risk summary
                              </p>
                              <p className="mt-1 text-sm text-gray-800">{r.risk_summary || '--'}</p>
                              <p className="mt-2 text-xs text-gray-500">
                                Predicted clearance ~{r.predicted_clearance_minutes ?? '--'} min · late{' '}
                                {Math.round(r.p_late * 100)}%
                              </p>
                            </div>
                            <div>
                              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
                                History
                              </p>
                              <EventTimeline events={events[r.id]} />
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                )
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
