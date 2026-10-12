import {
  AlertTriangle,
  ArrowRight,
  CalendarDays,
  Clock,
  Loader2,
  MapPin,
  Package,
  Snowflake,
  Truck,
} from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { requestAppointment } from '../../lib/gateApi'

const CONTAINER_TYPES = [
  { value: 'standard', label: 'Standard', icon: Package },
  { value: 'reefer', label: 'Reefer', icon: Snowflake },
  { value: 'hazardous', label: 'Hazardous', icon: AlertTriangle },
  { value: 'oversized', label: 'Oversized', icon: Truck },
]

const CARRIERS = [
  'Carrier-A', 'Carrier-B', 'Carrier-C', 'Carrier-D', 'Carrier-E',
  'Carrier-F', 'Carrier-G', 'Carrier-H', 'Carrier-I', 'Carrier-J',
]

const CUSTOMS_RISK = [
  { value: 'low', label: 'Low' },
  { value: 'medium', label: 'Medium' },
  { value: 'high', label: 'High' },
]

const HOURS = Array.from({ length: 24 }, (_, h) => ({
  value: h,
  label: `${String(h).padStart(2, '0')}:00`,
}))

const INPUT_CLASS =
  'mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm outline-none focus:border-[#123a5c] focus:ring-1 focus:ring-[#123a5c]'

function tomorrowDate() {
  const d = new Date()
  d.setDate(d.getDate() + 1)
  return d.toISOString().slice(0, 10)
}

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
    carrierReliability: 0.75,
    missingDocuments: 0,
  })
  const [status, setStatus] = useState('idle') // idle | assigning | assigned | error
  const [assignment, setAssignment] = useState(null)
  const [error, setError] = useState(null)

  const updateField = (field) => (e) =>
    setForm((prev) => ({ ...prev, [field]: e.target.value }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    setStatus('assigning')
    setError(null)
    try {
      const result = await requestAppointment(form)
      const typeInfo = CONTAINER_TYPES.find((t) => t.value === form.containerType) ?? CONTAINER_TYPES[0]
      setAssignment({
        lane: result.lane,
        laneQueue: result.lane_queue,
        waitMinutes: result.predicted_wait_minutes,
        gateEntry: result.gate_entry_time,
        finishTime: result.end_time,
        predictedMinutes: result.predicted_minutes,
        containerType: typeInfo.label,
        cargoCategory: result.cargo_category,
        modelInputs: result.model_inputs,
        lanes: result.lanes,
      })
      setStatus('assigned')
    } catch {
      setError('Could not reach the gate appointment service. Is the backend running?')
      setStatus('error')
    }
  }

  const maxQueue = assignment ? Math.max(1, ...assignment.lanes.map((l) => l.predicted_queue_length)) : 1

  return (
    <div className="mx-auto max-w-4xl px-4 py-10 sm:px-6 lg:px-8">
      <h1 className="text-2xl font-bold text-[#123a5c]">Request a Gate Appointment</h1>
      <p className="mt-1 text-sm text-gray-600">
        Submit your container details and the system will assign the gate lane and
        arrival time slot with the shortest expected wait.
      </p>

      <form
        onSubmit={handleSubmit}
        className="mt-8 grid gap-5 rounded-xl border border-gray-200 bg-white p-6 shadow-sm sm:grid-cols-2"
      >
        <div className="sm:col-span-1">
          <label htmlFor="truckId" className="block text-sm font-medium text-gray-700">
            Truck ID
          </label>
          <input
            id="truckId"
            required
            value={form.truckId}
            onChange={updateField('truckId')}
            placeholder="TRK-80579"
            className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm outline-none focus:border-[#123a5c] focus:ring-1 focus:ring-[#123a5c]"
          />
        </div>

        <div className="sm:col-span-1">
          <label htmlFor="containerId" className="block text-sm font-medium text-gray-700">
            Container ID
          </label>
          <input
            id="containerId"
            required
            value={form.containerId}
            onChange={updateField('containerId')}
            placeholder="MAEU3483419"
            className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm outline-none focus:border-[#123a5c] focus:ring-1 focus:ring-[#123a5c]"
          />
        </div>

        <div className="sm:col-span-1">
          <label htmlFor="carrier" className="block text-sm font-medium text-gray-700">
            Carrier Company
          </label>
          <select
            id="carrier"
            value={form.carrier}
            onChange={updateField('carrier')}
            className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm outline-none focus:border-[#123a5c] focus:ring-1 focus:ring-[#123a5c]"
          >
            {CARRIERS.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>

        <div className="sm:col-span-1">
          <label htmlFor="cargoCategory" className="block text-sm font-medium text-gray-700">
            Cargo Category
          </label>
          <select
            id="cargoCategory"
            value={form.cargoCategory}
            onChange={updateField('cargoCategory')}
            className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm outline-none focus:border-[#123a5c] focus:ring-1 focus:ring-[#123a5c]"
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

        <div className="sm:col-span-1">
          <label htmlFor="preferredDate" className="block text-sm font-medium text-gray-700">
            Planned Arrival Date
          </label>
          <input
            id="preferredDate"
            type="date"
            value={form.preferredDate}
            onChange={updateField('preferredDate')}
            className={INPUT_CLASS}
          />
        </div>

        <div className="sm:col-span-1">
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

        <div className="sm:col-span-1">
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

        <div className="sm:col-span-1">
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
                Assigning gate & time slot...
              </>
            ) : (
              'Request Appointment'
            )}
          </button>
        </div>
      </form>

      {status === 'error' && error && (
        <div className="mt-6 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {status === 'assigned' && assignment && (
        <div className="mt-6 rounded-xl border border-green-200 bg-green-50 p-6">
          <p className="text-sm font-semibold uppercase tracking-wide text-green-700">
            Appointment Confirmed
          </p>

          <div className="mt-4 grid gap-4 sm:grid-cols-4">
            <ResultStat icon={MapPin} label="Gate Lane" value={`Gate ${assignment.lane}`} />
            <ResultStat
              icon={Clock}
              label={`Gate entry (after ~${assignment.waitMinutes} min queue)`}
              value={assignment.gateEntry}
            />
            <ResultStat
              icon={CalendarDays}
              label="Predicted Clearance"
              value={`~${assignment.predictedMinutes} min`}
            />
            <ResultStat icon={Truck} label="Expected Departure" value={assignment.finishTime} />
          </div>

          <div className="mt-6 grid gap-4 md:grid-cols-2">
            <div className="rounded-lg border border-green-200 bg-white p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                Congestion model: forecast queue at arrival hour
              </p>
              <ul className="mt-3 space-y-2">
                {assignment.lanes.map((l) => {
                  const chosen = l.lane === assignment.lane
                  const width = Math.min(100, (l.predicted_queue_length / maxQueue) * 100)
                  return (
                    <li key={l.lane} className="flex items-center gap-2 text-xs">
                      <span className={`w-12 ${chosen ? 'font-bold text-[#123a5c]' : 'text-gray-600'}`}>
                        Gate {l.lane}
                      </span>
                      <span className="h-2.5 flex-1 rounded bg-gray-100">
                        <span
                          className={`block h-2.5 rounded ${chosen ? 'bg-green-600' : 'bg-[#123a5c]/40'}`}
                          style={{ width: `${width}%` }}
                        />
                      </span>
                      <span className="w-20 text-right text-gray-600">
                        {l.predicted_queue_length} trucks
                      </span>
                    </li>
                  )
                })}
              </ul>
              <p className="mt-3 text-xs text-gray-500">
                Gate {assignment.lane} has the shortest forecast queue, so it is assigned.
              </p>
            </div>

            <div className="rounded-lg border border-green-200 bg-white p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                Clearance model: inputs it received
              </p>
              <dl className="mt-3 grid grid-cols-2 gap-x-3 gap-y-1.5 text-xs">
                {Object.entries(assignment.modelInputs).map(([key, value]) => (
                  <div key={key} className="contents">
                    <dt className="text-gray-500">{key.replaceAll('_', ' ')}</dt>
                    <dd className="font-medium text-gray-800">{String(value)}</dd>
                  </div>
                ))}
              </dl>
              <p className="mt-3 text-xs text-gray-500">
                Change any input above and resubmit to see the prediction move.
              </p>
            </div>
          </div>

          <Link
            to="/document-upload"
            state={{
              containerId: form.containerId,
              truckId: form.truckId,
              containerType: form.containerType,
            }}
            className="mt-5 inline-flex items-center gap-2 rounded-md bg-[#123a5c] px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-[#0e2d47]"
          >
            Continue to Document Upload
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      )}
    </div>
  )
}
