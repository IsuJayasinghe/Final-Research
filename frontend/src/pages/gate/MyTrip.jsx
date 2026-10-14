import { AlertTriangle, ArrowRight, Bell, CheckCircle2, Clock, Loader2, MapPin, RefreshCw, Truck } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { STATUS } from '../../components/HourChart'
import { cancelAppointment, getLive, listAppointments } from '../../lib/gateApi'
import { useRole } from '../../lib/role'
import { STATUS_LABEL, STATUS_STYLES, dayAndHour, hhmm } from '../../lib/status'

const STEPS = ['Request sent', 'Approved by gate admin', 'Documents uploaded', 'Gate day']

// which step the driver is on, from the live phase
function stepIndex(phase) {
  switch (phase) {
    case 'awaiting_approval':
    case 'rejected':
    case 'waitlisted':
    case 'cancelled':
      return 0
    case 'upload_documents':
    case 'fix_documents':
      return 1
    case 'ready':
    default:
      return 3
  }
}

const LEVEL_STYLES = {
  success: 'border-green-200 bg-green-50 text-green-800',
  warning: 'border-amber-200 bg-amber-50 text-amber-900',
  error: 'border-red-200 bg-red-50 text-red-800',
  info: 'border-gray-200 bg-white text-gray-700',
}

function countdown(minutes) {
  if (minutes === undefined || minutes === null) return null
  if (minutes <= -60) return 'Your slot has passed'
  if (minutes <= 0) return 'Your slot is now'
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  if (h >= 24) return `Your slot is in ${Math.floor(h / 24)} day(s) ${h % 24} h`
  return `Your slot is in ${h > 0 ? `${h} h ` : ''}${m} min`
}

function Stepper({ phase }) {
  const current = stepIndex(phase)
  const stopped = phase === 'rejected' || phase === 'cancelled'
  return (
    <ol className="grid grid-cols-4 gap-2" aria-label="Progress">
      {STEPS.map((label, i) => {
        const done = i < current || (phase === 'past' && i === 3)
        const active = i === current && !stopped
        return (
          <li key={label} className="text-center">
            <span
              className={`mx-auto flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold ${
                stopped && i === 0
                  ? 'bg-red-100 text-red-700'
                  : done
                    ? 'bg-green-600 text-white'
                    : active
                      ? 'bg-[#123a5c] text-white'
                      : 'bg-gray-200 text-gray-500'
              }`}
            >
              {done ? <CheckCircle2 className="h-4 w-4" /> : i + 1}
            </span>
            <span className={`mt-1 block text-[11px] ${active || done ? 'font-medium text-gray-800' : 'text-gray-400'}`}>
              {label}
            </span>
          </li>
        )
      })}
    </ol>
  )
}

export default function MyTrip() {
  const { myTruck, setMyTruck } = useRole()
  const [truckInput, setTruckInput] = useState(myTruck)
  const [appointments, setAppointments] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [trip, setTrip] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [seen, setSeen] = useState(0)
  const [lastUpdated, setLastUpdated] = useState(null)

  const loadAppointments = useCallback(async (truck) => {
    if (!truck) return
    setLoading(true)
    try {
      const rows = await listAppointments({ truckId: truck })
      setAppointments(rows)
      setSelectedId((current) => {
        if (current && rows.some((r) => r.id === current)) return current
        const active = rows.filter((r) => r.status !== 'CANCELLED' && r.status !== 'REJECTED')
        return (active.length ? active : rows).at(-1)?.id ?? null
      })
      setError(null)
    } catch (err) {
      setError(
        err instanceof TypeError ? 'Could not reach the gate appointment service. Is the backend running?' : err.message,
      )
    } finally {
      setLoading(false)
    }
  }, [])

  const loadTrip = useCallback(async (id) => {
    if (!id) return
    try {
      setTrip(await getLive(id))
      setLastUpdated(new Date())
      setError(null)
    } catch (err) {
      setError(err instanceof TypeError ? 'Could not reach the gate appointment service.' : err.message)
    }
  }, [])

  // open straight to the driver's own bookings when the truck is already known
  useEffect(() => {
    if (myTruck) loadAppointments(myTruck)
  }, [myTruck, loadAppointments])

  // the trip updates itself: approval, delays and gate changes appear without a refresh
  useEffect(() => {
    setTrip(null)
    if (!selectedId) return undefined
    loadTrip(selectedId)
    const interval = setInterval(() => loadTrip(selectedId), 10000)
    return () => clearInterval(interval)
  }, [selectedId, loadTrip])

  // how many updates the driver has already read (kept per appointment)
  useEffect(() => {
    if (!selectedId) return
    try {
      setSeen(Number(localStorage.getItem(`gateSeen:${selectedId}`) ?? 0))
    } catch {
      setSeen(0)
    }
  }, [selectedId])

  const notes = trip?.notifications ?? []
  const unread = Math.max(0, notes.length - seen)
  const markRead = () => {
    setSeen(notes.length)
    try {
      localStorage.setItem(`gateSeen:${selectedId}`, String(notes.length))
    } catch {
      // not persisted; fine
    }
  }

  const find = (e) => {
    e.preventDefault()
    const truck = truckInput.trim().toUpperCase()
    setMyTruck(truck)
    loadAppointments(truck)
  }

  const cancel = async () => {
    if (!window.confirm('Cancel this appointment?')) return
    try {
      await cancelAppointment(selectedId)
      await loadAppointments(myTruck)
      await loadTrip(selectedId)
    } catch (err) {
      setError(err.message)
    }
  }

  const appt = trip?.appointment
  const live = trip?.live
  const phase = trip?.phase
  const canUpload = phase === 'upload_documents' || phase === 'fix_documents' || phase === 'ready'
  const laneStyle = live ? STATUS[live.lane_status] : null

  return (
    <div className="mx-auto max-w-4xl px-4 py-10 sm:px-6 lg:px-8">
      <h1 className="text-2xl font-bold text-[#123a5c]">My Trip</h1>
      <p className="mt-1 text-sm text-gray-600">
        Follow your appointment live: approval, your gate, the queue at your hour, delays and any gate change.
      </p>

      <form onSubmit={find} className="mt-6 flex flex-wrap items-end gap-3 rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
        <div>
          <label htmlFor="trip-truck" className="block text-xs font-medium text-gray-600">
            Your truck ID
          </label>
          <input
            id="trip-truck"
            value={truckInput}
            onChange={(e) => setTruckInput(e.target.value)}
            placeholder="TRK-80579"
            className="mt-1 rounded-md border border-gray-300 px-3 py-2 text-sm outline-none focus:border-[#123a5c] focus:ring-1 focus:ring-[#123a5c]"
          />
        </div>
        <button
          type="submit"
          className="rounded-md bg-[#123a5c] px-4 py-2 text-sm font-semibold text-white hover:bg-[#0e2d47]"
        >
          Find my bookings
        </button>
        {appointments.length > 1 && (
          <div>
            <label htmlFor="trip-appt" className="block text-xs font-medium text-gray-600">
              Booking
            </label>
            <select
              id="trip-appt"
              value={selectedId ?? ''}
              onChange={(e) => setSelectedId(Number(e.target.value))}
              className="mt-1 rounded-md border border-gray-300 px-2 py-2 text-sm"
            >
              {appointments.map((r) => (
                <option key={r.id} value={r.id}>
                  #{r.id} · {dayAndHour(r.assigned_slot ?? r.requested_slot)} · {STATUS_LABEL[r.status]}
                </option>
              ))}
            </select>
          </div>
        )}
        <span className="ml-auto text-xs text-gray-400">
          {lastUpdated && `Updated ${lastUpdated.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}`}
          {loading && <Loader2 className="ml-2 inline h-3.5 w-3.5 animate-spin" />}
        </span>
      </form>

      {error && <div className="mt-4 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div>}

      {!myTruck && !appointments.length && (
        <p className="mt-6 text-sm text-gray-500">
          Enter your truck ID to see your bookings, or{' '}
          <Link to="/gate-appointment" className="font-medium text-[#123a5c] hover:underline">
            request an appointment
          </Link>
          .
        </p>
      )}
      {myTruck && !loading && appointments.length === 0 && !error && (
        <p className="mt-6 text-sm text-gray-500">
          No bookings found for {myTruck}.{' '}
          <Link to="/gate-appointment" className="font-medium text-[#123a5c] hover:underline">
            Request an appointment
          </Link>
          .
        </p>
      )}

      {appt && (
        <>
          <section className="mt-6 rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <p className="text-sm font-semibold text-[#123a5c]">
                  Appointment #{appt.id} · {appt.truck_id} · {appt.container_id}
                </p>
                <p className="text-xs text-gray-500">
                  {appt.container_type} · {appt.cargo_category} · requested {dayAndHour(appt.requested_slot)}
                  {appt.assigned_slot && appt.assigned_slot !== appt.requested_slot && <> → now {dayAndHour(appt.assigned_slot)}</>}
                </p>
              </div>
              <span className={`rounded-full px-3 py-1 text-xs font-semibold ${STATUS_STYLES[appt.status]}`}>
                {STATUS_LABEL[appt.status]}
              </span>
            </div>
            <div className="mt-5">
              <Stepper phase={phase} />
            </div>

            <div
              className={`mt-5 flex flex-wrap items-center justify-between gap-3 rounded-lg border p-3 text-sm ${
                phase === 'rejected' ? LEVEL_STYLES.error : phase === 'arrive_now' ? LEVEL_STYLES.success : 'border-blue-100 bg-blue-50 text-blue-900'
              }`}
            >
              <span>
                <b>Next:</b> {trip.next_step}
                {phase === 'rejected' && appt.decision_reason && <span className="mt-1 block text-xs">{appt.decision_reason}</span>}
              </span>
              {canUpload && (
                <Link
                  to="/document-upload"
                  state={{ appointmentId: appt.id, containerId: appt.container_id, truckId: appt.truck_id, containerType: appt.container_type }}
                  className="inline-flex items-center gap-1.5 rounded-md bg-[#123a5c] px-3 py-1.5 text-xs font-semibold text-white hover:bg-[#0e2d47]"
                >
                  {phase === 'ready' ? 'Review documents' : 'Upload documents'}
                  <ArrowRight className="h-3.5 w-3.5" />
                </Link>
              )}
              {phase === 'rejected' && (
                <Link to="/gate-appointment" className="text-xs font-semibold underline">
                  Book another time
                </Link>
              )}
            </div>
            {phase === 'awaiting_approval' && (
              <p className="mt-2 text-xs text-gray-500">
                Document upload opens as soon as the gate admin approves your request. This page updates by itself.
              </p>
            )}
          </section>

          {live && (
            <section className="mt-6 rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-500">Your gate, live</h2>
                <span className="text-sm font-medium text-[#123a5c]">{countdown(trip.minutes_to_slot)}</span>
              </div>
              <div className="mt-4 grid gap-4 sm:grid-cols-4">
                <div className="flex items-center gap-3">
                  <span className="flex h-10 w-10 items-center justify-center rounded-full bg-[#123a5c]/10 text-[#123a5c]">
                    <MapPin className="h-5 w-5" />
                  </span>
                  <div>
                    <p className="text-xs text-gray-500">Your gate</p>
                    <p className="text-lg font-bold text-[#123a5c]">Gate {live.lane}</p>
                    <p className={`flex items-center gap-1 text-xs font-semibold ${laneStyle.text}`}>
                      <span className={`h-2 w-2 rounded-full ${laneStyle.dot}`} />
                      {laneStyle.label}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="flex h-10 w-10 items-center justify-center rounded-full bg-[#123a5c]/10 text-[#123a5c]">
                    <Truck className="h-5 w-5" />
                  </span>
                  <div>
                    <p className="text-xs text-gray-500">Queue at your hour</p>
                    <p className="text-lg font-bold text-[#123a5c]">{live.queue ?? '--'} trucks</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="flex h-10 w-10 items-center justify-center rounded-full bg-[#123a5c]/10 text-[#123a5c]">
                    <Clock className="h-5 w-5" />
                  </span>
                  <div>
                    <p className="text-xs text-gray-500">Expected gate entry</p>
                    <p className="text-lg font-bold text-[#123a5c]">{hhmm(live.gate_entry)}</p>
                    <p className="text-xs text-gray-500">~{Math.round(live.expected_wait_min)} min wait</p>
                  </div>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Expected departure</p>
                  <p className="text-lg font-bold text-[#123a5c]">{hhmm(live.departure)}</p>
                  <p
                    className={`mt-0.5 inline-block rounded-full px-2 py-0.5 text-xs font-semibold ${
                      live.delay_min >= 1 ? 'bg-red-50 text-red-700' : 'bg-green-50 text-green-700'
                    }`}
                  >
                    {live.delay_min >= 1 ? `+${Math.round(live.delay_min)} min delay` : 'On schedule'}
                  </p>
                </div>
              </div>

              {live.reasons.length > 0 && (
                <ul className="mt-4 space-y-1 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">
                  {live.reasons.map((r) => (
                    <li key={r} className="flex gap-1.5">
                      <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                      {r}
                    </li>
                  ))}
                </ul>
              )}

              <div className="mt-4 flex flex-wrap items-center gap-4 text-xs">
                <Link
                  to={`/gate-allocation?date=${live.monitor.date}&hour=${live.monitor.hour}&truck=${encodeURIComponent(appt.truck_id)}`}
                  className="font-semibold text-[#123a5c] underline"
                >
                  See my truck on the gate monitor
                </Link>
                <span className="inline-flex items-center gap-1 text-gray-400">
                  <RefreshCw className="h-3 w-3" /> refreshes every 10 s
                </span>
              </div>
            </section>
          )}

          <section className="mt-6 rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between gap-2">
              <h2 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-gray-500">
                <Bell className="h-4 w-4" />
                Updates
                {unread > 0 && (
                  <span className="rounded-full bg-red-500 px-2 py-0.5 text-[10px] font-bold text-white">{unread} new</span>
                )}
              </h2>
              {unread > 0 && (
                <button type="button" onClick={markRead} className="text-xs font-semibold text-[#123a5c] underline">
                  Mark all read
                </button>
              )}
            </div>
            <ul className="mt-3 space-y-2">
              {notes.map((n, i) => (
                <li key={`${n.time}-${n.type}-${i}`} className={`rounded-lg border p-3 text-xs ${LEVEL_STYLES[n.level] ?? LEVEL_STYLES.info}`}>
                  <p className="flex items-center justify-between gap-2 font-semibold">
                    <span>
                      {n.title}
                      {i < unread && <span className="ml-2 rounded-full bg-red-500 px-1.5 py-0.5 text-[9px] text-white">new</span>}
                    </span>
                    <span className="font-normal opacity-60">{n.time.replace('T', ' ').slice(5, 16)}</span>
                  </p>
                  <p className="mt-1">{n.message}</p>
                </li>
              ))}
            </ul>
          </section>

          {(appt.status === 'PENDING' || appt.status === 'CONFIRMED') && (
            <div className="mt-6 text-right">
              <button type="button" onClick={cancel} className="text-xs font-semibold text-gray-500 underline hover:text-red-700">
                Cancel this appointment
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
