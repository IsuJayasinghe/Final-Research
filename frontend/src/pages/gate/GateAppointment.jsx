import {
  AlertTriangle,
  ArrowDown,
  ArrowRight,
  ArrowUp,
  CalendarDays,
  Clock,
  Loader2,
  MapPin,
  Package,
  Snowflake,
  Truck,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  cancelAppointment,
  createAppointment,
  getCarriers,
  getCongestionProfile,
  getWeather,
} from '../../lib/gateApi'
import HourChart, { Legend, STATUS, pad } from '../../components/HourChart'
import { useRole } from '../../lib/role'

const CONTAINER_TYPES = [
  { value: 'standard', label: 'Standard', icon: Package },
  { value: 'reefer', label: 'Reefer', icon: Snowflake },
  { value: 'hazardous', label: 'Hazardous', icon: AlertTriangle },
  { value: 'oversized', label: 'Oversized', icon: Truck },
]

// Shown until the carrier profiles (reliability, past no-show rate) load from the API.
const FALLBACK_CARRIERS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J'].map((l) => ({
  carrier: `Carrier-${l}`,
}))

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
    carrier: FALLBACK_CARRIERS[0].carrier,
    cargoCategory: 'export',
    containerType: 'standard',
    preferredDate: tomorrowDate(),
    arrivalHour: 9,
  })
  const { setMyTruck } = useRole()
  const [dayProfile, setDayProfile] = useState([]) // how busy the gate is each hour of the chosen date
  const [carriers, setCarriers] = useState(FALLBACK_CARRIERS)
  const [forecast, setForecast] = useState(null) // weather forecast for the chosen arrival date
  const [status, setStatus] = useState('idle') // idle | assigning | assigned | error
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [lifecycle, setLifecycle] = useState(null) // CONFIRMED | CANCELLED | null
  const [actionBusy, setActionBusy] = useState(false)

  const updateField = (field) => (e) =>
    setForm((prev) => ({ ...prev, [field]: e.target.value }))

  // carrier profiles (reliability and past no-show rate) come from the model's history
  useEffect(() => {
    getCarriers()
      .then(setCarriers)
      .catch(() => {})
  }, [])

  // the weather forecast for the arrival day is fetched, not typed
  useEffect(() => {
    let cancelled = false
    setForecast(null)
    getWeather(form.preferredDate)
      .then((w) => !cancelled && setForecast(w))
      .catch(() => !cancelled && setForecast({ severity: null, source: 'unavailable' }))
    return () => {
      cancelled = true
    }
  }, [form.preferredDate])

  // the driver looks at the gate first: expected congestion for every hour of the chosen date
  useEffect(() => {
    let cancelled = false
    getCongestionProfile(form.preferredDate)
      .then((p) => !cancelled && setDayProfile(p))
      .catch(() => !cancelled && setDayProfile([]))
    return () => {
      cancelled = true
    }
  }, [form.preferredDate])

  const profile = carriers.find((c) => c.carrier === form.carrier)
  const chosenHour = Number(form.arrivalHour)
  const chosenRow = dayProfile.find((r) => r.hour === chosenHour)
  const quieter = chosenRow
    ? dayProfile
        .filter((r) => Math.abs(r.hour - chosenHour) <= 3 && r.max_lane_queue < chosenRow.max_lane_queue - 2)
        .sort((a, b) => a.max_lane_queue - b.max_lane_queue)[0]
    : null

  const handleSubmit = async (e) => {
    e.preventDefault()
    setStatus('assigning')
    setError(null)
    setLifecycle(null)
    try {
      setResult(await createAppointment(form))
      setMyTruck(form.truckId) // remembered so My Trip opens straight to this booking
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
        Look at how busy the gate is, pick a time, and enter your truck details. The gate admin then
        approves your request, and once approved you upload your documents and follow your trip live.
      </p>

      <form
        onSubmit={handleSubmit}
        className="mt-8 grid gap-5 rounded-xl border border-gray-200 bg-white p-6 shadow-sm sm:grid-cols-2"
      >
        <div className="sm:col-span-2">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-[#123a5c]">
            1. Check the gate and pick your time
          </h2>
          <p className="mt-1 text-xs text-gray-500">
            Each bar is one hour of your chosen date: how busy the gate is expected to be. Click an hour to choose it.
            Quieter hours mean shorter waits.
          </p>
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

        <div className="sm:col-span-2">
          {dayProfile.length === 0 ? (
            <p className="text-xs text-gray-500">Loading the gate forecast for this date...</p>
          ) : (
            <>
              <HourChart
                profile={dayProfile}
                hour={chosenHour}
                onPick={(h) => setForm((prev) => ({ ...prev, arrivalHour: h }))}
                height="h-24"
              />
              <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-xs text-gray-600">
                <span>
                  {chosenRow && (
                    <>
                      {pad(chosenHour)}:00 is expected to be{' '}
                      <b className={STATUS[chosenRow.status].text}>{STATUS[chosenRow.status].label.toLowerCase()}</b> (about{' '}
                      {chosenRow.avg_wait_minutes} min wait).
                    </>
                  )}
                  {quieter && (
                    <>
                      {' '}
                      Tip: <b>{pad(quieter.hour)}:00</b> is quieter (about {quieter.avg_wait_minutes} min).
                    </>
                  )}
                </span>
                <Legend />
              </div>
            </>
          )}
        </div>

        <div className="rounded-lg border border-gray-200 bg-gray-50 p-3 text-xs text-gray-700 sm:col-span-2">
          <span className="font-semibold text-[#123a5c]">Weather forecast for your arrival day: </span>
          {forecast === null ? (
            'loading...'
          ) : forecast.severity === null ? (
            <>
              not available for this date. The seasonal typical weather will be assumed.
            </>
          ) : (
            <>
              <b>{forecast.label}</b>
              {forecast.precipitation_mm != null && <> ({forecast.precipitation_mm} mm rain expected)</>} - from the
              Open-Meteo forecast for the port.
            </>
          )}
        </div>

        <div className="sm:col-span-2 border-t border-gray-100 pt-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-[#123a5c]">
            2. Your truck and container
          </h2>
        </div>

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
          <select id="carrier" value={form.carrier} onChange={updateField('carrier')} className={INPUT_CLASS}>
            {carriers.map((c) => (
              <option key={c.carrier} value={c.carrier}>
                {c.carrier}
              </option>
            ))}
          </select>
          {profile?.reliability != null && (
            <p className="mt-1 text-xs text-gray-500">
              From history: reliability <b>{profile.reliability.toFixed(2)}</b> · past no-show rate{' '}
              <b>{(profile.past_no_show_rate * 100).toFixed(1)}%</b>
            </p>
          )}
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

        <div className="rounded-lg border border-blue-100 bg-blue-50 p-3 text-xs text-blue-900 sm:col-span-2">
          <b>Nothing else is typed in.</b> Carrier reliability comes from the carrier&apos;s history, weather from the
          forecast, and the customs risk, missing documents and linked-vessel delay are read from your documents
          with OCR after booking. Until then the risk estimate assumes the typical situation and is firmed up once
          your documents are checked.
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
                : lifecycle === 'CANCELLED'
                  ? 'Request cancelled'
                  : `Request #${appt.id} sent - waiting for the gate admin to approve`}
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

          <div className="mt-4 grid gap-2 text-xs sm:grid-cols-3">
            <div className="rounded-md border border-gray-200 bg-white p-2">
              <p className="text-gray-500">Carrier reliability (from history)</p>
              <p className="font-semibold text-gray-800">
                {result.conditions.carrier.reliability_used.toFixed(2)}
                {result.conditions.carrier.past_no_show_rate != null && (
                  <span className="font-normal text-gray-500">
                    {' '}
                    · past no-show {(result.conditions.carrier.past_no_show_rate * 100).toFixed(1)}%
                  </span>
                )}
              </p>
            </div>
            <div className="rounded-md border border-gray-200 bg-white p-2">
              <p className="text-gray-500">Weather on arrival day</p>
              <p className="font-semibold text-gray-800">
                {result.conditions.weather.severity === null
                  ? 'forecast unavailable (typical assumed)'
                  : `${result.conditions.weather.label} (${result.conditions.weather.source})`}
              </p>
            </div>
            <div className="rounded-md border border-gray-200 bg-white p-2">
              <p className="text-gray-500">Linked vessel delay</p>
              <p className="font-semibold text-gray-800">
                {result.risk.vessel_known ? 'known' : 'not known yet (read from the booking confirmation)'}
              </p>
            </div>
          </div>

          {!result.risk.documents_known && (
            <div className="mt-4 flex flex-wrap items-center justify-between gap-2 rounded-lg border border-blue-100 bg-blue-50 p-3 text-xs text-blue-900">
              <span>
                <b>Documents not checked yet.</b> This estimate assumes a typical document situation and vessel
                delay. Upload your documents to firm up the risk and the clearance time.
              </span>
              <Link
                to="/document-upload"
                state={{
                  appointmentId: appt.id,
                  containerId: form.containerId,
                  truckId: form.truckId,
                  containerType: form.containerType,
                }}
                className="font-semibold text-[#123a5c] hover:underline"
              >
                Upload documents now
              </Link>
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

          {!waitlisted && !lifecycle && (
            <div className="mt-5 rounded-lg border border-blue-100 bg-blue-50 p-4 text-sm text-blue-900">
              <p className="font-semibold">What happens next</p>
              <ol className="mt-2 list-decimal space-y-1 pl-5 text-xs">
                <li>The gate admin reviews your request. This slot and gate are provisional until then.</li>
                <li>Once approved, document upload opens for you. You will see it on My Trip.</li>
                <li>
                  Upload your documents, then follow your trip live: your gate, the queue at that hour, and any delay
                  or gate change, with the reason.
                </li>
              </ol>
            </div>
          )}

          <div className="mt-5 flex flex-wrap items-center gap-3">
            {!waitlisted && !lifecycle && (
              <>
                <Link
                  to="/my-trip"
                  className="inline-flex items-center gap-2 rounded-md bg-[#123a5c] px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-[#0e2d47]"
                >
                  Track my trip
                  <ArrowRight className="h-4 w-4" />
                </Link>
                <button
                  type="button"
                  disabled={actionBusy}
                  onClick={() => runAction(cancelAppointment, 'CANCELLED')}
                  className="rounded-md border border-gray-300 px-4 py-2.5 text-sm font-semibold text-gray-700 transition-colors hover:bg-gray-50 disabled:opacity-70"
                >
                  Cancel request
                </button>
              </>
            )}
            <Link to="/gate-allocation" className="text-sm font-medium text-[#123a5c] hover:underline">
              See the gate
            </Link>
          </div>
        </div>
      )}
    </div>
  )
}
