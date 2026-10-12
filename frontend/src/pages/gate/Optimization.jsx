import { Loader2, Ship, Siren } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { clearDisruption, getSlots, reoptimize } from '../../lib/gateApi'

const INPUT_CLASS =
  'mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm outline-none focus:border-[#123a5c] focus:ring-1 focus:ring-[#123a5c]'

function tomorrowDate() {
  const d = new Date()
  d.setDate(d.getDate() + 1)
  return d.toISOString().slice(0, 10)
}

const hhmm = (iso) => iso.slice(11, 16)

function SlotRow({ row, scale }) {
  const over = row.bookings > row.capacity
  return (
    <li className="grid grid-cols-[3.5rem_1fr_9rem] items-center gap-3 text-xs">
      <span className="font-medium text-gray-700">{hhmm(row.slot)}</span>
      <span className="relative block h-4 rounded bg-gray-100">
        <span
          className={`absolute left-0 top-0 block h-4 rounded ${over ? 'bg-amber-500' : 'bg-[#123a5c]/70'}`}
          style={{ width: `${(row.bookings / scale) * 100}%` }}
        />
        <span
          className="absolute top-0 block h-4 border-l-2 border-green-500"
          style={{ left: `${(row.expected_arrivals / scale) * 100}%` }}
          title={`Expected arrivals ${row.expected_arrivals}`}
        />
        <span
          className="absolute -top-0.5 block h-5 border-l-2 border-dashed border-red-400"
          style={{ left: `${(row.capacity / scale) * 100}%` }}
          title={`Capacity ${row.capacity}`}
        />
      </span>
      <span className="text-right text-gray-500">
        {row.bookings > 0 ? (
          <>
            <b className="text-gray-800">{row.bookings}</b> booked · {row.expected_arrivals} exp ·{' '}
          </>
        ) : null}
        {row.forecast_wait_min} min wait
      </span>
    </li>
  )
}

export default function Optimization() {
  const [date, setDate] = useState(tomorrowDate())
  const [slots, setSlots] = useState([])
  const [loadingSlots, setLoadingSlots] = useState(true)
  const [error, setError] = useState(null)

  const [disruption, setDisruption] = useState({
    startHour: 10,
    windowHours: 1,
    vesselDelayHours: 4,
    queueSpikePct: 0,
  })
  const [running, setRunning] = useState(false)
  const [outcome, setOutcome] = useState(null)

  const loadSlots = useCallback(async (d) => {
    setLoadingSlots(true)
    try {
      setSlots(await getSlots(d))
      setError(null)
    } catch (err) {
      setError(
        err instanceof TypeError
          ? 'Could not reach the gate appointment service. Is the backend running?'
          : err.message,
      )
    } finally {
      setLoadingSlots(false)
    }
  }, [])

  useEffect(() => {
    loadSlots(date)
  }, [date, loadSlots])

  const setField = (field) => (e) => setDisruption((p) => ({ ...p, [field]: e.target.value }))

  const apply = async (e) => {
    e.preventDefault()
    setRunning(true)
    setError(null)
    try {
      const hour = String(disruption.startHour).padStart(2, '0')
      setOutcome(
        await reoptimize({
          vesselDelayHours: disruption.vesselDelayHours,
          queueSpikePct: disruption.queueSpikePct,
          windowHours: disruption.windowHours,
          start: `${date}T${hour}:00`,
        }),
      )
      await loadSlots(date)
    } catch (err) {
      setError(err.message)
    } finally {
      setRunning(false)
    }
  }

  const clear = async () => {
    try {
      await clearDisruption()
      setOutcome(null)
      await loadSlots(date)
    } catch (err) {
      setError(err.message)
    }
  }

  const scale = Math.max(8, ...slots.map((s) => Math.max(s.bookings, s.capacity + 2)))
  const visible = slots.filter((s) => s.bookings > 0 || (Number(s.slot.slice(11, 13)) >= 6 && Number(s.slot.slice(11, 13)) <= 20))

  return (
    <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6 lg:px-8">
      <h1 className="text-2xl font-bold text-[#123a5c]">Slot Optimization &amp; Disruptions</h1>
      <p className="mt-1 text-sm text-gray-600">
        Hourly slot load against capacity. When a vessel is delayed or the gate queue spikes, only
        unconfirmed bookings are re-optimized, and each move is explained.
      </p>

      {error && (
        <div className="mt-4 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="mt-6 grid gap-6 lg:grid-cols-5">
        <section className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm lg:col-span-3">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-500">Slot board</h2>
            <div>
              <label htmlFor="boardDate" className="block text-xs font-medium text-gray-600">
                Date
              </label>
              <input
                id="boardDate"
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                className="rounded-md border border-gray-300 px-2 py-1 text-sm"
              />
            </div>
          </div>
          <div className="mt-3 flex flex-wrap gap-4 text-[11px] text-gray-500">
            <span>
              <span className="mr-1 inline-block h-2 w-3 rounded bg-[#123a5c]/70" />
              bookings
            </span>
            <span>
              <span className="mr-1 inline-block h-3 border-l-2 border-green-500" />
              expected arrivals (1 - no-show risk)
            </span>
            <span>
              <span className="mr-1 inline-block h-3 border-l-2 border-dashed border-red-400" />
              capacity
            </span>
            <span>
              <span className="mr-1 inline-block h-2 w-3 rounded bg-amber-500" />
              overbooked
            </span>
          </div>
          {loadingSlots ? (
            <div className="mt-6 flex items-center gap-2 text-sm text-gray-500">
              <Loader2 className="h-4 w-4 animate-spin" />
              Loading slots...
            </div>
          ) : (
            <ul className="mt-4 space-y-1.5">
              {visible.map((row) => (
                <SlotRow key={row.slot} row={row} scale={scale} />
              ))}
            </ul>
          )}
        </section>

        <section className="space-y-6 lg:col-span-2">
          <form
            onSubmit={apply}
            className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm"
          >
            <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-500">
              Inject a disruption
            </h2>
            <div className="mt-3 grid grid-cols-2 gap-3">
              <div>
                <label htmlFor="d-start" className="block text-xs font-medium text-gray-600">
                  Starts at (on {date.slice(5)})
                </label>
                <select
                  id="d-start"
                  value={disruption.startHour}
                  onChange={setField('startHour')}
                  className={INPUT_CLASS}
                >
                  {Array.from({ length: 24 }, (_, h) => (
                    <option key={h} value={h}>
                      {String(h).padStart(2, '0')}:00
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label htmlFor="d-window" className="block text-xs font-medium text-gray-600">
                  Lasts (hours)
                </label>
                <input
                  id="d-window"
                  type="number"
                  min="1"
                  max="12"
                  value={disruption.windowHours}
                  onChange={setField('windowHours')}
                  className={INPUT_CLASS}
                />
              </div>
              <div>
                <label htmlFor="d-vessel" className="flex items-center gap-1 text-xs font-medium text-gray-600">
                  <Ship className="h-3.5 w-3.5" />
                  Vessel delay (h)
                </label>
                <input
                  id="d-vessel"
                  type="number"
                  min="0"
                  max="12"
                  step="0.5"
                  value={disruption.vesselDelayHours}
                  onChange={setField('vesselDelayHours')}
                  className={INPUT_CLASS}
                />
              </div>
              <div>
                <label htmlFor="d-spike" className="flex items-center gap-1 text-xs font-medium text-gray-600">
                  <Siren className="h-3.5 w-3.5" />
                  Queue spike (%)
                </label>
                <input
                  id="d-spike"
                  type="number"
                  min="0"
                  max="200"
                  value={disruption.queueSpikePct}
                  onChange={setField('queueSpikePct')}
                  className={INPUT_CLASS}
                />
              </div>
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              <button
                type="submit"
                disabled={running}
                className="inline-flex items-center gap-2 rounded-md bg-[#123a5c] px-4 py-2 text-sm font-semibold text-white hover:bg-[#0e2d47] disabled:opacity-70"
              >
                {running && <Loader2 className="h-4 w-4 animate-spin" />}
                Apply &amp; re-optimize
              </button>
              <button
                type="button"
                onClick={clear}
                className="rounded-md border border-gray-300 px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50"
              >
                Clear disruption
              </button>
            </div>
            <p className="mt-3 text-xs text-gray-500">
              Forecast congestion in the window rises (a vessel delay adds up to +60%, a queue spike
              adds its percentage). Confirmed bookings never move.
            </p>
          </form>

          {outcome && (
            <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-500">
                Re-optimization result
              </h2>
              <dl className="mt-3 grid grid-cols-4 gap-2 text-center text-xs">
                <div className="rounded-md bg-gray-50 p-2">
                  <dt className="text-gray-500">Considered</dt>
                  <dd className="text-lg font-bold text-[#123a5c]">{outcome.considered}</dd>
                </div>
                <div className="rounded-md bg-gray-50 p-2">
                  <dt className="text-gray-500">Kept fixed</dt>
                  <dd className="text-lg font-bold text-[#123a5c]">{outcome.fixed_confirmed}</dd>
                </div>
                <div className="rounded-md bg-gray-50 p-2">
                  <dt className="text-gray-500">Moved</dt>
                  <dd className="text-lg font-bold text-[#123a5c]">{outcome.moved}</dd>
                </div>
                <div className="rounded-md bg-gray-50 p-2">
                  <dt className="text-gray-500">Total wait</dt>
                  <dd className="text-sm font-bold text-[#123a5c]">
                    {Math.round(outcome.expected_wait_before_min)} &rarr;{' '}
                    {Math.round(outcome.expected_wait_after_min)} min
                  </dd>
                </div>
              </dl>
              {outcome.changes.length === 0 ? (
                <p className="mt-4 text-sm text-gray-600">
                  No booking needed to move - the disruption was cheaper to absorb than to reshuffle.
                </p>
              ) : (
                <ul className="mt-4 space-y-3">
                  {outcome.changes.slice(0, 6).map((c) => (
                    <li key={c.appointment_id} className="rounded-lg border border-gray-200 p-3">
                      <p className="text-sm font-semibold text-[#123a5c]">
                        #{c.appointment_id} {c.truck_id}: {hhmm(c.old_slot)} &rarr;{' '}
                        {c.new_slot ? hhmm(c.new_slot) : 'waitlist'}
                      </p>
                      <ul className="mt-1 list-disc space-y-0.5 pl-5 text-xs text-gray-700">
                        {c.reasons.map((r, i) => (
                          <li key={i}>{r}</li>
                        ))}
                      </ul>
                    </li>
                  ))}
                  {outcome.changes.length > 6 && (
                    <li className="text-xs text-gray-500">
                      + {outcome.changes.length - 6} more moves (see Appointments for each reason)
                    </li>
                  )}
                </ul>
              )}
            </div>
          )}
        </section>
      </div>
    </div>
  )
}
