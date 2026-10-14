import { CheckCircle2, Loader2, RefreshCw, XCircle } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { approveAppointment, getSlots, listAppointments, rejectAppointment } from '../../lib/gateApi'
import { STATUS_LABEL, STATUS_STYLES, dayAndHour } from '../../lib/status'

const LOW_RISK = 0.1 // "approve all low-risk" covers requests at or below this no-show risk

function riskClass(p) {
  if (p >= 0.3) return 'text-red-600'
  if (p >= 0.15) return 'text-amber-600'
  return 'text-green-600'
}

function docsText(a) {
  if (a.missing_documents === null) return 'not uploaded yet'
  return a.missing_documents === 0 ? 'cleared' : `${a.missing_documents} missing`
}

export default function Approvals() {
  const [pending, setPending] = useState([])
  const [decided, setDecided] = useState([])
  const [slotRows, setSlotRows] = useState({}) // date -> hourly slot board (bookings vs capacity)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [busyId, setBusyId] = useState(null)
  const [rejecting, setRejecting] = useState(null) // appointment id being rejected
  const [reason, setReason] = useState('')
  const [lastUpdated, setLastUpdated] = useState(new Date())

  const load = useCallback(async () => {
    try {
      const [wait, ok, no] = await Promise.all([
        listAppointments({ status: 'PENDING' }),
        listAppointments({ status: 'CONFIRMED' }),
        listAppointments({ status: 'REJECTED' }),
      ])
      setPending(wait.filter((a) => a.assigned_slot))
      setDecided([...ok, ...no].sort((a, b) => b.id - a.id).slice(0, 8))
      const dates = [...new Set(wait.filter((a) => a.assigned_slot).map((a) => a.assigned_slot.slice(0, 10)))]
      const boards = await Promise.all(dates.map((d) => getSlots(d).then((rows) => [d, rows])))
      setSlotRows(Object.fromEntries(boards))
      setLastUpdated(new Date())
      setError(null)
    } catch (err) {
      setError(
        err instanceof TypeError ? 'Could not reach the gate appointment service. Is the backend running?' : err.message,
      )
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
    const interval = setInterval(load, 10000)
    return () => clearInterval(interval)
  }, [load])

  const decide = async (fn, id) => {
    setBusyId(id)
    try {
      await fn()
      setRejecting(null)
      setReason('')
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusyId(null)
    }
  }

  const lowRisk = pending.filter((a) => a.p_no_show <= LOW_RISK && !a.overbooked)

  const approveAllLowRisk = async () => {
    if (!window.confirm(`Approve ${lowRisk.length} low-risk request(s)?`)) return
    setBusyId('bulk')
    try {
      for (const a of lowRisk) await approveAppointment(a.id)
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusyId(null)
    }
  }

  const slotInfo = (a) => slotRows[a.assigned_slot.slice(0, 10)]?.find((r) => r.slot === a.assigned_slot)

  return (
    <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6 lg:px-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-[#123a5c]">Appointment Approvals</h1>
          <p className="mt-1 text-sm text-gray-600">
            Review driver requests. Approving fixes the slot and opens document upload for the driver; rejecting
            releases the slot and tells the driver why.
          </p>
        </div>
        <div className="flex items-center gap-3 text-xs text-gray-500">
          <span>Updated {lastUpdated.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
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

      {error && <div className="mt-4 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div>}

      <section className="mt-6 rounded-xl border border-gray-200 bg-white shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-gray-100 p-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-500">
            Waiting for approval ({pending.length})
          </h2>
          <button
            type="button"
            disabled={lowRisk.length === 0 || busyId === 'bulk'}
            onClick={approveAllLowRisk}
            className="rounded-md bg-[#123a5c] px-3 py-1.5 text-xs font-semibold text-white hover:bg-[#0e2d47] disabled:opacity-50"
          >
            {busyId === 'bulk' ? 'Approving...' : `Approve all low-risk (${lowRisk.length})`}
          </button>
        </div>

        {loading ? (
          <div className="flex items-center gap-2 p-6 text-sm text-gray-500">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading requests...
          </div>
        ) : pending.length === 0 ? (
          <p className="p-6 text-sm text-gray-500">No requests are waiting. New driver requests appear here automatically.</p>
        ) : (
          <ul className="divide-y divide-gray-100">
            {pending.map((a) => {
              const slot = slotInfo(a)
              return (
                <li key={a.id} className="p-4">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-[#123a5c]">
                        #{a.id} · {a.truck_id} · {a.container_id}
                      </p>
                      <p className="mt-0.5 text-xs text-gray-500">
                        {a.carrier} · {a.container_type} · {a.cargo_category}
                      </p>
                      <p className="mt-2 text-xs text-gray-700">
                        Slot <b>{dayAndHour(a.assigned_slot)}</b>
                        {a.assigned_slot !== a.requested_slot && <> (asked {dayAndHour(a.requested_slot)})</>} · Gate{' '}
                        <b>{a.lane}</b>
                        {slot && (
                          <>
                            {' '}
                            · hour load <b>{slot.bookings}</b>/{slot.capacity} booked
                            {slot.overbooked && <span className="ml-1 rounded-full bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold text-amber-800">overbooked</span>}
                          </>
                        )}
                      </p>
                      <p className="mt-1 text-xs text-gray-600">{a.decision_reason}</p>
                    </div>
                    <div className="text-right text-xs">
                      <p className="text-gray-500">No-show risk</p>
                      <p className={`text-xl font-bold ${riskClass(a.p_no_show)}`}>{Math.round(a.p_no_show * 100)}%</p>
                      <p className="text-gray-500">documents: {docsText(a)}</p>
                    </div>
                  </div>
                  <p className="mt-2 text-xs text-gray-500">{a.risk_summary}</p>

                  {rejecting === a.id ? (
                    <div className="mt-3 flex flex-wrap items-center gap-2">
                      <input
                        autoFocus
                        value={reason}
                        onChange={(e) => setReason(e.target.value)}
                        placeholder="Reason the driver will see"
                        aria-label="Reason for rejecting"
                        className="min-w-64 flex-1 rounded-md border border-gray-300 px-3 py-1.5 text-sm outline-none focus:border-red-400"
                      />
                      <button
                        type="button"
                        disabled={busyId === a.id}
                        onClick={() => decide(() => rejectAppointment(a.id, reason), a.id)}
                        className="rounded-md bg-red-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-red-700 disabled:opacity-60"
                      >
                        Confirm reject
                      </button>
                      <button
                        type="button"
                        onClick={() => setRejecting(null)}
                        className="rounded-md border border-gray-300 px-3 py-1.5 text-xs font-semibold text-gray-600 hover:bg-gray-50"
                      >
                        Back
                      </button>
                    </div>
                  ) : (
                    <div className="mt-3 flex gap-2">
                      <button
                        type="button"
                        disabled={busyId === a.id}
                        onClick={() => decide(() => approveAppointment(a.id), a.id)}
                        className="inline-flex items-center gap-1.5 rounded-md bg-[#123a5c] px-3 py-1.5 text-xs font-semibold text-white hover:bg-[#0e2d47] disabled:opacity-60"
                      >
                        <CheckCircle2 className="h-3.5 w-3.5" />
                        Approve
                      </button>
                      <button
                        type="button"
                        disabled={busyId === a.id}
                        onClick={() => setRejecting(a.id)}
                        className="inline-flex items-center gap-1.5 rounded-md border border-red-300 px-3 py-1.5 text-xs font-semibold text-red-700 hover:bg-red-50 disabled:opacity-60"
                      >
                        <XCircle className="h-3.5 w-3.5" />
                        Reject
                      </button>
                    </div>
                  )}
                </li>
              )
            })}
          </ul>
        )}
      </section>

      {decided.length > 0 && (
        <section className="mt-6 rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-500">Recent decisions</h2>
          <ul className="mt-3 space-y-1.5 text-xs text-gray-700">
            {decided.map((a) => (
              <li key={a.id} className="flex flex-wrap items-center gap-2">
                <span className={`rounded-full px-2 py-0.5 font-medium ${STATUS_STYLES[a.status]}`}>{STATUS_LABEL[a.status]}</span>
                <span>
                  #{a.id} {a.truck_id} · {dayAndHour(a.assigned_slot ?? a.requested_slot)}
                  {a.lane && <> · Gate {a.lane}</>}
                </span>
                {a.status === 'REJECTED' && <span className="text-gray-500">{a.decision_reason}</span>}
              </li>
            ))}
          </ul>
          <p className="mt-3 text-xs text-gray-500">
            Full history for every request is on{' '}
            <Link to="/appointments" className="font-medium text-[#123a5c] underline">
              All Appointments
            </Link>
            .
          </p>
        </section>
      )}
    </div>
  )
}
