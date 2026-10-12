import {
  AlertTriangle,
  ArrowDown,
  ArrowRight,
  ArrowUp,
  CalendarDays,
  CheckCircle2,
  Clock,
  Loader2,
  MapPin,
  Package,
  Snowflake,
  Truck,
} from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { cancelAppointment, confirmAppointment, createAppointment } from '../../lib/gateApi'

const CONTAINER_TYPES = [
  { value: 'standard', label: 'Standard', icon: Package },
  { value: 'reefer', label: 'Reefer', icon: Snowflake },
  { value: 'hazardous', label: 'Hazardous', icon: AlertTriangle },
  { value: 'oversized', label: 'Oversized', icon: Truck },
]

// Typical past reliability per carrier (averages from the training data). In production
// this comes from the carrier's booking history; here it pre-fills an editable field.
const CARRIER_RELIABILITY = {
  'Carrier-A': 0.75, 'Carrier-B': 0.54, 'Carrier-C': 0.69, 'Carrier-D': 0.79, 'Carrier-E': 0.79,
  'Carrier-F': 0.71, 'Carrier-G': 0.81, 'Carrier-H': 0.71, 'Carrier-I': 0.84, 'Carrier-J': 0.87,
}
const CARRIERS = Object.keys(CARRIER_RELIABILITY)

const CUSTOMS_RISK = [
  { value: 'low', label: 'Low' },
  { value: 'medium', label: 'Medium' },
  { value: 'high', label: 'High' },
]

const WEATHER = [
  { value: 0, label: '0 - Clear' },
  { value: 1, label: '1 - Light rain' },
  { value: 2, label: '2 - Heavy rain' },
  { value: 3, label: '3 - Storm' },
]

const HOURS = Array.from({ length: 24 }, (_, h) => ({
  value: h,
  label: `${String(h).padStart(2, '0')}:00`,
}))

const INPUT_CLASS =
  'mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm outline-none focus:border-[#123a5c] focus:ring-1 focus:ring-[#123a5c]'

const isoDate = (d) => d.toISOString().slice(0, 10)
const today = () => isoDate(new Date())
function tomorrowDate() {
  const d = new Date()
  d.setDate(d.getDate() + 1)
  return isoDate(d)
}

const hhmm = (iso) => (iso ? iso.slice(11, 16) : '--')
const pct = (p) => `${Math.round(p * 100)}%`

function ResultStat({ icon: Icon, label, value }) {
  return (
    <div className="flex items-center gap-3">
      <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-white text-[#123a5c]">
        <Icon className="h-5 w-5" />
      </span>
      <div>
        <p className="text-xs text-gray-500">{label}</p>
        <p className="text-lg font-bold text-[#123a5c]">{value}</p>
      </div>
    </div>
  )
}

function RiskBar({ risk }) {
  const parts = [
    { key: 'p_on_time', label: 'On time', cls: 'bg-green-500' },
    { key: 'p_late', label: 'Late', cls: 'bg-amber-400' },
    { key: 'p_no_show', label: 'No-show', cls: 'bg-red-500' },
  ]
  return (
    <div>
      <div className="flex h-3 w-full overflow-hidden rounded-full bg-gray-100">
        {parts.map((p) => (
          <span key={p.key} className={p.cls} style={{ width: `${risk[p.key] * 100}%` }} />
        ))}
      </div>
      <div className="mt-2 flex justify-between text-xs text-gray-600">
        {parts.map((p) => (
          <span key={p.key}>
            <span className={`mr-1 inline-block h-2 w-2 rounded-full ${p.cls}`} />
            {p.label} {pct(risk[p.key])}
          </span>
        ))}
      </div>
    </div>
  )
}

export default function GateAppointment() {
  const [form, setForm] = useState({
    truckId: '',
    containerId: '',
    carrier: CARRIERS[0],
    cargoCategory: 'export',
    containerType: 'standard',
    preferredDate: tomorrowDate(),
    arrivalHour: 9,
    customsRiskFlag: 'low',
    carrierReliability: CARRIER_RELIABILITY[CARRIERS[0]],
    missingDocuments: 0,
    weatherSeverity: 0,
    vesselDelay: false,
  })
  const [status, setStatus] = useState('idle') // idle | assigning | assigned | error
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [lifecycle, setLifecycle] = useState(null) // CONFIRMED | CANCELLED | null
  const [actionBusy, setActionBusy] = useState(false)

  const updateField = (field) => (e) =>
    setForm((prev) => ({ ...prev, [field]: e.target.value }))

  const updateCarrier = (e) => {
    const carrier = e.target.value
    setForm((prev) => ({ ...prev, carrier, carrierReliability: CARRIER_RELIABILITY[carrier] }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setStatus('assigning')
    setError(null)
    setLifecycle(null)
    try {
      setResult(await createAppointment(form))
      setStatus('assigned')
    } catch (err) {
      setError(
        err instanceof TypeError
          ? 'Could not reach the gate appointment service. Is the backend running?'
          : err.message,
      )
      setStatus('error')
    }
  }

  const runAction = async (action, nextState) => {
    setActionBusy(true)
    try {
      await action(result.appointment.id)
      setLifecycle(nextState)
    } catch (err) {
      setError(err.message)
    } finally {
      setActionBusy(false)
    }
  }

  const appt = result?.appointment
  const lanes = result?.lanes ?? []
  const maxQueue = Math.max(1, ...lanes.map((l) => l.predicted_queue_length))
  const waitlisted = appt?.status === 'WAITLISTED'
  const moved = appt && appt.assigned_slot && appt.assigned_slot !== appt.requested_slot

  return (
    <div className="mx-auto max-w-4xl px-4 py-10 sm:px-6 lg:px-8">
      <h1 className="text-2xl font-bold text-[#123a5c]">Request a Gate Appointment</h1>
      <p className="mt-1 text-sm text-gray-600">
        Your booking is scored for no-show risk, placed in the best hourly slot (overbooking only
        where predicted no-shows make it safe), assigned the shortest-queue lane, and saved.
      </p>

      <form
        onSubmit={handleSubmit}
        className="mt-8 grid gap-5 rounded-xl border border-gray-200 bg-white p-6 shadow-sm sm:grid-cols-2"
      >
        <div>
          <label htmlFor="truckId" className="block text-sm font-medium text-gray-700">
            Truck ID
          </label>
          <input
            id="truckId"
            required
            value={form.truckId}
            onChange={updateField('truckId')}
            placeholder="TRK-80579"
            className={INPUT_CLASS}
          />
        </div>

        <div>
          <label htmlFor="containerId" className="block text-sm font-medium text-gray-700">
            Container ID
          </label>
          <input
            id="containerId"
            required
            value={form.containerId}
            onChange={updateField('containerId')}
            placeholder="MAEU3483419"
            className={INPUT_CLASS}
          />
        </div>

        <div>
          <label htmlFor="carrier" className="block text-sm font-medium text-gray-700">
            Carrier Company
          </label>
          <select id="carrier" value={form.carrier} onChange={updateCarrier} className={INPUT_CLASS}>
            {CARRIERS.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="cargoCategory" className="block text-sm font-medium text-gray-700">
            Cargo Category
          </label>
          <select
            id="cargoCategory"
            value={form.cargoCategory}
            onChange={updateField('cargoCategory')}
            className={INPUT_CLASS}
          >
            <option value="export">Export</option>
            <option value="import">Import</option>
          </select>
        </div>

        <div className="sm:col-span-2">
          <span className="block text-sm font-medium text-gray-700">Container Type</span>
          <div className="mt-2 grid grid-cols-2 gap-3 sm:grid-cols-4">
            {CONTAINER_TYPES.map(({ value, label, icon: Icon }) => (
              <label
                key={value}
                className={`flex cursor-pointer flex-col items-center gap-1.5 rounded-lg border px-3 py-3 text-sm transition-colors ${
                  form.containerType === value
                    ? 'border-[#123a5c] bg-[#123a5c]/5 text-[#123a5c]'
                    : 'border-gray-200 text-gray-600 hover:border-gray-300'
                }`}
              >
                <input
                  type="radio"
                  name="containerType"
                  value={value}
                  checked={form.containerType === value}
                  onChange={updateField('containerType')}
                  className="sr-only"
                />
                <Icon className="h-5 w-5" />
                {label}
              </label>
            ))}
          </div>
        </div>

        <div>
          <label htmlFor="preferredDate" className="block text-sm font-medium text-gray-700">
            Planned Arrival Date
          </label>
          <input
            id="preferredDate"
            type="date"
            min={today()}
            value={form.preferredDate}
            onChange={updateField('preferredDate')}
            className={INPUT_CLASS}
          />
        </div>

        <div>
          <label htmlFor="arrivalHour" className="block text-sm font-medium text-gray-700">
            Planned Arrival Hour
          </label>
          <select
            id="arrivalHour"
            value={form.arrivalHour}
            onChange={updateField('arrivalHour')}
            className={INPUT_CLASS}
          >
            {HOURS.map((h) => (
              <option key={h.value} value={h.value}>
                {h.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="customsRiskFlag" className="block text-sm font-medium text-gray-700">
            Customs Risk Level
          </label>
          <select
            id="customsRiskFlag"
            value={form.customsRiskFlag}
            onChange={updateField('customsRiskFlag')}
            className={INPUT_CLASS}
          >
            {CUSTOMS_RISK.map((r) => (
              <option key={r.value} value={r.value}>
                {r.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="missingDocuments" className="block text-sm font-medium text-gray-700">
            Missing Documents
          </label>
          <input
            id="missingDocuments"
            type="number"
            min="0"
            max="5"
            value={form.missingDocuments}
            onChange={updateField('missingDocuments')}
            className={INPUT_CLASS}
          />
        </div>

        <div>
          <label htmlFor="weatherSeverity" className="block text-sm font-medium text-gray-700">
            Weather on Arrival Day
          </label>
          <select
            id="weatherSeverity"
            value={form.weatherSeverity}
            onChange={updateField('weatherSeverity')}
            className={INPUT_CLASS}
          >
            {WEATHER.map((w) => (
              <option key={w.value} value={w.value}>
                {w.label}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-end">
          <label className="flex cursor-pointer items-center gap-2 pb-2 text-sm text-gray-700">
            <input
              type="checkbox"
              checked={form.vesselDelay}
              onChange={(e) => setForm((prev) => ({ ...prev, vesselDelay: e.target.checked }))}
              className="h-4 w-4 accent-[#123a5c]"
            />
            Linked vessel is delayed
          </label>
        </div>

        <div className="sm:col-span-2">
          <label htmlFor="carrierReliability" className="block text-sm font-medium text-gray-700">
            Carrier Past Reliability:{' '}
            <span className="font-semibold text-[#123a5c]">
              {Number(form.carrierReliability).toFixed(2)}
            </span>
          </label>
          <input
            id="carrierReliability"
            type="range"
            min="0.5"
            max="1"
            step="0.01"
            value={form.carrierReliability}
            onChange={updateField('carrierReliability')}
            className="mt-2 w-full accent-[#123a5c]"
          />
          <p className="mt-1 text-xs text-gray-500">
            Customs risk, missing documents, weather and reliability are entered here for the demo; in
            production they come from customs records, forecasts and the carrier&apos;s booking history.
          </p>
        </div>

        <div className="sm:col-span-2">
          <button
            type="submit"
            disabled={status === 'assigning'}
            className="flex w-full items-center justify-center gap-2 rounded-md bg-[#123a5c] px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-[#0e2d47] disabled:opacity-70 sm:w-auto"
          >
            {status === 'assigning' ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Scoring risk and assigning slot...
              </>
            ) : (
              'Request Appointment'
            )}
          </button>
        </div>
      </form>

      {error && (
        <div className="mt-6 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {status === 'assigned' && appt && (
        <div
          className={`mt-6 rounded-xl border p-6 ${
            waitlisted ? 'border-amber-200 bg-amber-50' : 'border-green-200 bg-green-50'
          }`}
        >
          <div className="flex flex-wrap items-center gap-2">
            <p
              className={`text-sm font-semibold uppercase tracking-wide ${
                waitlisted ? 'text-amber-700' : 'text-green-700'
              }`}
            >
              {waitlisted
                ? 'Waitlisted - no nearby slot has spare capacity'
                : lifecycle === 'CONFIRMED'
                  ? 'Appointment Confirmed'
                  : lifecycle === 'CANCELLED'
                    ? 'Appointment Cancelled'
                    : `Appointment #${appt.id} Booked - awaiting your confirmation`}
            </p>
            {appt.overbooked && (
              <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-800">
                Overbooked slot
              </span>
            )}
          </div>

          {!waitlisted && (
            <div className="mt-4 grid gap-4 sm:grid-cols-4">
              <ResultStat icon={MapPin} label="Gate Lane" value={`Gate ${appt.lane}`} />
              <ResultStat
                icon={CalendarDays}
                label={moved ? `Slot (you asked ${hhmm(appt.requested_slot)})` : 'Arrival Slot'}
                value={hhmm(appt.assigned_slot)}
              />
              <ResultStat
                icon={Clock}
                label={`Gate entry (~${result.timing.predicted_wait_minutes} min queue)`}
                value={hhmm(result.timing.gate_entry)}
              />
              <ResultStat icon={Truck} label="Expected Departure" value={hhmm(result.timing.departure)} />
            </div>
          )}

          <div className="mt-6 grid gap-4 md:grid-cols-2">
            <div className="rounded-lg border border-gray-200 bg-white p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                No-show risk model (Model 2)
              </p>
              <div className="mt-3">
                <RiskBar risk={result.risk} />
              </div>
              <ul className="mt-4 space-y-1.5 text-sm">
                {result.risk.drivers.map((d) => (
                  <li key={d.feature} className="flex items-center gap-2 text-gray-700">
                    {d.effect === 'raises' ? (
                      <ArrowUp className="h-4 w-4 shrink-0 text-red-500" />
                    ) : (
                      <ArrowDown className="h-4 w-4 shrink-0 text-green-600" />
                    )}
                    <span>
                      {d.label} <span className="text-gray-400">({d.effect} no-show risk)</span>
                    </span>
                  </li>
                ))}
              </ul>
              <p className="mt-3 text-xs text-gray-500">Explained with SHAP values.</p>
            </div>

            <div className="rounded-lg border border-gray-200 bg-white p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                Slot decision (overbooking rule)
              </p>
              <p className="mt-3 text-sm text-gray-800">{result.decision.reason}</p>
              <dl className="mt-3 grid grid-cols-3 gap-2 text-center text-xs">
                <div className="rounded-md bg-gray-50 p-2">
                  <dt className="text-gray-500">Booked in slot</dt>
                  <dd className="text-base font-bold text-[#123a5c]">
                    {result.decision.bookings_in_slot}/{result.decision.capacity}
                  </dd>
                </div>
                <div className="rounded-md bg-gray-50 p-2">
                  <dt className="text-gray-500">Expected arrivals</dt>
                  <dd className="text-base font-bold text-[#123a5c]">
                    {result.decision.expected_arrivals_after}
                  </dd>
                </div>
                <div className="rounded-md bg-gray-50 p-2">
                  <dt className="text-gray-500">Clearance</dt>
                  <dd className="text-base font-bold text-[#123a5c]">
                    ~{appt.predicted_clearance_minutes ?? '--'} min
                  </dd>
                </div>
              </dl>
            </div>
          </div>

          {lanes.length > 0 && (
            <div className="mt-4 rounded-lg border border-gray-200 bg-white p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                Congestion model (Model 1): forecast queue at the assigned hour
              </p>
              <ul className="mt-3 space-y-2">
                {lanes.map((l) => {
                  const chosen = l.lane === appt.lane
                  return (
                    <li key={l.lane} className="flex items-center gap-2 text-xs">
                      <span className={`w-12 ${chosen ? 'font-bold text-[#123a5c]' : 'text-gray-600'}`}>
                        Gate {l.lane}
                      </span>
                      <span className="h-2.5 flex-1 rounded bg-gray-100">
                        <span
                          className={`block h-2.5 rounded ${chosen ? 'bg-green-600' : 'bg-[#123a5c]/40'}`}
                          style={{ width: `${Math.min(100, (l.predicted_queue_length / maxQueue) * 100)}%` }}
                        />
                      </span>
                      <span className="w-20 text-right text-gray-600">
                        {l.predicted_queue_length} trucks
                      </span>
                    </li>
                  )
                })}
              </ul>
            </div>
          )}

          <div className="mt-5 flex flex-wrap items-center gap-3">
            {!waitlisted && !lifecycle && (
              <>
                <button
                  type="button"
                  disabled={actionBusy}
                  onClick={() => runAction(confirmAppointment, 'CONFIRMED')}
                  className="inline-flex items-center gap-2 rounded-md bg-[#123a5c] px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-[#0e2d47] disabled:opacity-70"
                >
                  <CheckCircle2 className="h-4 w-4" />
                  Confirm appointment
                </button>
                <button
                  type="button"
                  disabled={actionBusy}
                  onClick={() => runAction(cancelAppointment, 'CANCELLED')}
                  className="rounded-md border border-gray-300 px-4 py-2.5 text-sm font-semibold text-gray-700 transition-colors hover:bg-gray-50 disabled:opacity-70"
                >
                  Cancel
                </button>
              </>
            )}
            {lifecycle === 'CONFIRMED' && (
              <Link
                to="/document-upload"
                state={{
                  containerId: form.containerId,
                  truckId: form.truckId,
                  containerType: form.containerType,
                }}
                className="inline-flex items-center gap-2 rounded-md bg-[#123a5c] px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-[#0e2d47]"
              >
                Continue to Document Upload
                <ArrowRight className="h-4 w-4" />
              </Link>
            )}
            <Link to="/appointments" className="text-sm font-medium text-[#123a5c] hover:underline">
              View all appointments
            </Link>
          </div>
          {!waitlisted && !lifecycle && (
            <p className="mt-2 text-xs text-gray-500">
              Unconfirmed bookings may be moved if conditions change; confirmed bookings stay fixed.
            </p>
          )}
        </div>
      )}
    </div>
  )
}
