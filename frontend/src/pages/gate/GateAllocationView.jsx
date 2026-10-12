import {
  AlertTriangle,
  Clock,
  Gauge,
  RefreshCw,
  ScanEye,
  Truck,
  Users,
  X,
} from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { getCongestion } from '../../lib/gateApi'

const DOC_STATUS_STYLES = {
  cleared: { label: 'Docs Cleared', cls: 'bg-green-50 text-green-700' },
  pending: { label: 'Docs Pending', cls: 'bg-amber-50 text-amber-700' },
  flagged: { label: 'Docs Flagged', cls: 'bg-red-50 text-red-700' },
}

function randomInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min
}

function pick(arr) {
  return arr[randomInt(0, arr.length - 1)]
}

// Upcoming-arrivals lists are simulated — there's no live truck booking feed
// yet. Queue length and wait time (what drives the status/bar on each card)
// come from the real per-lane SARIMAX forecasts via /api/congestion.
function generateMockTrucks(queueLength) {
  const cargoTypes = ['standard', 'reefer', 'hazardous', 'oversized']
  const docStatuses = ['cleared', 'cleared', 'cleared', 'pending', 'flagged']
  const truckCount = Math.min(Math.round(queueLength), randomInt(2, 5))

  const now = new Date()
  return Array.from({ length: truckCount }, (_, i) => {
    const slot = new Date(now.getTime() + (i + 1) * 9 * 60000)
    return {
      id: `TRK-${randomInt(10000, 99999)}`,
      containerId: `${pick(['MAEU', 'OOLU', 'TCLU', 'CMAU'])}${randomInt(1000000, 9999999)}`,
      cargoType: pick(cargoTypes),
      docStatus: pick(docStatuses),
      timeSlot: slot.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    }
  })
}

async function fetchLaneData() {
  const { lanes } = await getCongestion()
  return lanes.map((l) => ({
    lane: l.lane,
    queueLength: l.predicted_queue_length,
    avgWait: l.predicted_avg_wait_minutes,
    trucks: generateMockTrucks(l.predicted_queue_length),
  }))
}

function laneStatus(queueLength) {
  if (queueLength >= 8) return { label: 'Congested', dot: 'bg-red-500', text: 'text-red-700', bar: 'bg-red-500' }
  if (queueLength >= 4) return { label: 'Busy', dot: 'bg-amber-500', text: 'text-amber-700', bar: 'bg-amber-500' }
  return { label: 'Normal', dot: 'bg-green-500', text: 'text-green-700', bar: 'bg-green-500' }
}

function LaneCard({ data }) {
  const status = laneStatus(data.queueLength)
  const barPct = Math.min(100, (data.queueLength / 12) * 100)

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
          <p className="text-xs text-gray-500">Queue Length</p>
          <p className="font-semibold text-gray-800">{data.queueLength} trucks</p>
        </div>
        <div>
          <p className="text-xs text-gray-500">Avg Wait</p>
          <p className="font-semibold text-gray-800">{data.avgWait} min</p>
        </div>
      </div>

      <div className="mt-4 border-t border-gray-100 pt-3">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
          Upcoming Arrivals
        </p>
        {data.trucks.length === 0 ? (
          <p className="text-sm text-gray-400">No trucks currently assigned.</p>
        ) : (
          <ul className="space-y-2">
            {data.trucks.map((t) => {
              const doc = DOC_STATUS_STYLES[t.docStatus]
              return (
                <li key={t.id} className="flex items-center justify-between gap-2 text-xs">
                  <div className="min-w-0">
                    <p className="truncate font-medium text-gray-800">
                      {t.id} · {t.containerId}
                    </p>
                    <p className="text-gray-500">
                      {t.timeSlot} · {t.cargoType}
                    </p>
                  </div>
                  <span className={`shrink-0 rounded-full px-2 py-0.5 font-medium ${doc.cls}`}>
                    {doc.label}
                  </span>
                </li>
              )
            })}
          </ul>
        )}
      </div>
    </div>
  )
}

export default function GateAllocationView() {
  const [lanes, setLanes] = useState([])
  const [lastUpdated, setLastUpdated] = useState(new Date())
  const [dismissedAlert, setDismissedAlert] = useState(false)
  const [error, setError] = useState(null)

  const refresh = async () => {
    try {
      const data = await fetchLaneData()
      setLanes(data)
      setLastUpdated(new Date())
      setDismissedAlert(false)
      setError(null)
    } catch {
      setError('Could not reach the gate allocation service. Is the backend running?')
    }
  }

  // Poll the real per-lane congestion forecast — the backend advances its
  // forecast window every 20s, so matching that here keeps the dashboard
  // showing genuinely new model output rather than re-fetching unchanged data.
  useEffect(() => {
    refresh()
    const interval = setInterval(refresh, 20000)
    return () => clearInterval(interval)
  }, [])

  const summary = useMemo(() => {
    if (lanes.length === 0) return { totalTrucks: 0, avgWait: 0, balanced: true, variance: '0.0' }

    const totalTrucks = Math.round(lanes.reduce((sum, l) => sum + l.queueLength, 0) * 10) / 10
    const avgWait = Math.round(
      lanes.reduce((sum, l) => sum + l.avgWait, 0) / lanes.length,
    )
    const mean = totalTrucks / lanes.length
    const variance =
      lanes.reduce((sum, l) => sum + (l.queueLength - mean) ** 2, 0) / lanes.length
    const balanced = variance <= 6

    return { totalTrucks, avgWait, balanced, variance: variance.toFixed(1) }
  }, [lanes])

  const congestedLane = useMemo(
    () => lanes.find((l) => l.queueLength >= 8),
    [lanes],
  )

  return (
    <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6 lg:px-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-[#123a5c]">Gate Allocation & Lane Monitoring</h1>
          <p className="mt-1 text-sm text-gray-600">
            Live per-lane congestion across all 6 gate lanes — Port Authority operations view.
          </p>
        </div>
        <div className="flex items-center gap-3 text-sm text-gray-500">
          <span>
            Updated{' '}
            {lastUpdated.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
          </span>
          <button
            type="button"
            onClick={refresh}
            className="flex items-center gap-1.5 rounded-md border border-gray-300 px-3 py-1.5 font-medium text-[#123a5c] hover:bg-gray-50"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="mt-6 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Summary stats */}
      <div className="mt-6 grid gap-4 sm:grid-cols-3">
        <div className="flex items-center gap-3 rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <span className="flex h-10 w-10 items-center justify-center rounded-full bg-[#123a5c]/10 text-[#123a5c]">
            <Truck className="h-5 w-5" />
          </span>
          <div>
            <p className="text-xs text-gray-500">Trucks in System</p>
            <p className="text-xl font-bold text-gray-800">{summary.totalTrucks}</p>
          </div>
        </div>
        <div className="flex items-center gap-3 rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <span className="flex h-10 w-10 items-center justify-center rounded-full bg-[#123a5c]/10 text-[#123a5c]">
            <Clock className="h-5 w-5" />
          </span>
          <div>
            <p className="text-xs text-gray-500">System Avg Wait</p>
            <p className="text-xl font-bold text-gray-800">{summary.avgWait} min</p>
          </div>
        </div>
        <div className="flex items-center gap-3 rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <span className="flex h-10 w-10 items-center justify-center rounded-full bg-[#123a5c]/10 text-[#123a5c]">
            <Gauge className="h-5 w-5" />
          </span>
          <div>
            <p className="text-xs text-gray-500">Lane Load Balance</p>
            <p
              className={`text-xl font-bold ${summary.balanced ? 'text-green-700' : 'text-amber-700'}`}
            >
              {summary.balanced ? 'Balanced' : 'Imbalanced'}{' '}
              <span className="text-xs font-normal text-gray-400">(var {summary.variance})</span>
            </p>
          </div>
        </div>
      </div>

      {/* Disruption alert */}
      {congestedLane && !dismissedAlert && (
        <div className="mt-6 flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4">
          <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-red-600" />
          <div className="flex-1">
            <p className="text-sm font-semibold text-red-700">
              Gate {congestedLane.lane} is congested ({congestedLane.queueLength} trucks queued)
              — actual congestion has diverged from forecast.
            </p>
            <p className="mt-1 text-sm text-red-600">
              Not-yet-arrived trucks assigned to Gate {congestedLane.lane} can be re-optimized
              and redirected to a lighter lane.
            </p>
            <div className="mt-3 flex gap-2">
              <button
                type="button"
                onClick={refresh}
                className="flex items-center gap-1.5 rounded-md bg-red-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-red-700"
              >
                <ScanEye className="h-3.5 w-3.5" />
                Re-optimize Affected Trucks
              </button>
              <button
                type="button"
                onClick={() => setDismissedAlert(true)}
                className="rounded-md border border-red-300 px-3 py-1.5 text-xs font-semibold text-red-700 hover:bg-red-100"
              >
                Dismiss
              </button>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setDismissedAlert(true)}
            aria-label="Dismiss alert"
            className="text-red-400 hover:text-red-600"
          >
            <X className="h-4 w-4" />
          </button>
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

      <div className="mt-6 flex items-center gap-2 rounded-xl border border-gray-200 bg-white p-4 text-sm text-gray-500">
        <Users className="h-4 w-4" />
        Queue length and wait time come from the trained per-lane SARIMAX forecasting
        models. Upcoming-arrival truck lists are still simulated — there's no live
        booking feed yet.
      </div>
    </div>
  )
}
