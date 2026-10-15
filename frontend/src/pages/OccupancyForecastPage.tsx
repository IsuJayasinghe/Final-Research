import { useState, type FormEvent } from 'react'
import { AlertTriangle, CheckCircle2 } from 'lucide-react'
import { api } from '../api/client'
import ArrivalsChart from '../components/charts/ArrivalsChart'
import HorizonErrorChart from '../components/charts/HorizonErrorChart'
import OccupancyTrend from '../components/charts/OccupancyTrend'
import ErrorMessage from '../components/ErrorMessage'
import Loading from '../components/Loading'
import MetricBox from '../components/MetricBox'
import PageHeader from '../components/PageHeader'
import SubTabs, { PREDICTION_TABS } from '../components/SubTabs'
import { useApi } from '../hooks/useApi'

function r2Label(r2: number) {
  if (r2 >= 0.85) return 'EXCELLENT'
  if (r2 >= 0.8) return 'MEETS TARGET'
  return 'BELOW TARGET'
}

export default function OccupancyForecastPage() {
  const [days, setDays] = useState(14)
  const [capacity, setCapacity] = useState<number | undefined>(undefined)
  const [capacityInput, setCapacityInput] = useState('')
  const forecast = useApi(() => api.occupancyForecast(days, capacity), [days, capacity])
  const f = forecast.data

  // what-if: forecast against a smaller yard (e.g. when blocks are closed for maintenance)
  const applyCapacity = (e: FormEvent) => {
    e.preventDefault()
    const value = Number(capacityInput)
    setCapacity(capacityInput.trim() && value > 0 ? value : undefined)
  }

  return (
    <>
      <PageHeader title="Yard Occupancy Forecast" subtitle={`XGBoost ${days}-day prediction with 85% capacity alerts.`} />
      <SubTabs tabs={PREDICTION_TABS} />

      {forecast.error && <ErrorMessage message={forecast.error} onRetry={forecast.reload} />}
      {!f && forecast.loading && <Loading text="Running occupancy forecast..." />}

      {f && (
        <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
          <div className="space-y-6">
            <div className="card">
              <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
                <h2 className="border-l-4 border-accent pl-3 text-lg">XGBoost — {days}-Day Occupancy Forecast</h2>
                <div className="flex gap-1 rounded-lg border border-line bg-surface p-1">
                  {[7, 14].map((d) => (
                    <button key={d} onClick={() => setDays(d)}
                            className={`rounded-md px-3 py-1 text-xs ${days === d ? 'bg-card text-accent' : 'text-muted hover:text-ink'}`}>
                      {d} days
                    </button>
                  ))}
                </div>
              </div>
              <OccupancyTrend points={f.predictions} height={300} />

              {f.alerts.length > 0 ? (
                <div className="mt-4 flex gap-3 rounded-lg border border-danger/40 bg-danger/10 p-3 text-sm text-danger">
                  <AlertTriangle size={16} className="mt-0.5 shrink-0" />
                  <div>
                    <p className="font-semibold">
                      Capacity warning: yard predicted above 85% on {f.alerts.length} of {f.predictions.length} days
                    </p>
                    <p className="mt-0.5 text-danger/90">
                      First on Day {f.alerts[0].day_ahead} ({f.alerts[0].utilization_pct}%) · peak{' '}
                      {(() => {
                        const peak = f.alerts.reduce((m, x) => (x.utilization_pct > m.utilization_pct ? x : m))
                        return `Day ${peak.day_ahead} (${peak.utilization_pct}%)`
                      })()}. Consider expediting departures or limiting gate appointments.
                    </p>
                  </div>
                </div>
              ) : (
                <div className="mt-4 flex items-center gap-3 rounded-lg border border-ok/40 bg-ok/10 p-3 text-sm text-ok">
                  <CheckCircle2 size={16} /> No day in the next {days} days is predicted to pass 85% of capacity.
                </div>
              )}
            </div>

            <div className="card">
              <h2 className="card-title">Predicted containers and planned arrivals</h2>
              <ArrivalsChart points={f.predictions} />
              <p className="mt-2 text-[11px] text-muted">
                Planned arrivals are the average incoming volume per weekday; in the integrated system they come from
                vessel discharge plans (Component 1).
              </p>
            </div>
          </div>

          <div className="space-y-6">
            <div className="card">
              <h2 className="card-title">XGBoost Model Metrics</h2>
              <div className="rounded-lg border border-line bg-surface p-4 text-center">
                <p className="label">R² score (next-day)</p>
                <p className="mt-1 text-3xl font-bold text-ok">{f.metrics.r2.toFixed(2)}</p>
                <span className="badge mt-1 border-ok/40 bg-ok/10 text-ok">{r2Label(f.metrics.r2)}</span>
                <p className="mt-1 text-[11px] text-muted">Target &gt; 0.80</p>
              </div>
              <div className="mt-3 grid grid-cols-3 gap-2">
                <MetricBox label="MAPE" value={`${f.metrics.mape.toFixed(1)}%`} />
                <MetricBox label="MAE" value={f.metrics.mae.toFixed(0)} />
                <MetricBox label="RMSE" value={f.metrics.rmse.toFixed(0)} />
              </div>
              <p className="label mb-1 mt-5">Error by days ahead</p>
              <HorizonErrorChart horizonMape={f.horizon_mape} />
              <p className="label mb-2 mt-4">Features used</p>
              <div className="flex flex-wrap gap-1.5">
                {f.features_used.map((name) => <span key={name} className="badge border-line text-muted">{name}</span>)}
              </div>
            </div>

            <form onSubmit={applyCapacity} className="card">
              <h2 className="card-title">Capacity scenario</h2>
              <p className="mb-3 text-xs text-muted">
                Yard capacity used: <span className="text-ink">{f.capacity.toLocaleString()} slots</span>.
                Try a smaller capacity to see when alerts would trigger.
              </p>
              <div className="flex gap-2">
                <input className="input" inputMode="numeric" placeholder="e.g. 3500" value={capacityInput}
                       onChange={(e) => setCapacityInput(e.target.value)} />
                <button className="btn-primary" type="submit">Apply</button>
              </div>
              {capacity && (
                <button type="button" className="mt-2 text-xs text-accent hover:underline"
                        onClick={() => { setCapacity(undefined); setCapacityInput('') }}>
                  Reset to full yard capacity
                </button>
              )}
            </form>
          </div>
        </div>
      )}
    </>
  )
}
