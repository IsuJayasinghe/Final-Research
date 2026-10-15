import { useState } from 'react'
import { Info } from 'lucide-react'
import { api } from '../api/client'
import type { DwellModelMetrics } from '../api/types'
import DwellComparisonChart from '../components/charts/DwellComparisonChart'
import ErrorMessage from '../components/ErrorMessage'
import Loading from '../components/Loading'
import MetricBox from '../components/MetricBox'
import PageHeader from '../components/PageHeader'
import SubTabs, { PREDICTION_TABS } from '../components/SubTabs'
import { useApi } from '../hooks/useApi'

function ModelCard({ name, role, metrics, other, best, accent }: {
  name: string; role: string; metrics: DwellModelMetrics; other: DwellModelMetrics; best: boolean; accent: string
}) {
  const r = metrics.rolling_7d
  const better = (k: 'rmse' | 'mae' | 'mape') => r[k] < other.rolling_7d[k]
  return (
    <div className="card border-t-4" style={{ borderTopColor: accent }}>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg">{name}</h2>
        <span className={`badge ${best ? 'border-ok/40 bg-ok/10 text-ok' : 'border-line text-muted'}`}>{best ? 'BEST' : role}</span>
      </div>
      <p className="label mb-2">Rolling 7-day forecast (test period)</p>
      <div className="grid grid-cols-3 gap-2">
        <MetricBox label="RMSE" value={r.rmse.toFixed(3)} highlight={better('rmse')} />
        <MetricBox label="MAE" value={r.mae.toFixed(3)} highlight={better('mae')} />
        <MetricBox label="MAPE" value={`${r.mape.toFixed(1)}%`} highlight={better('mape')} />
      </div>
      <p className="mt-3 text-xs text-muted">
        Hold-out test: RMSE {metrics.holdout.rmse.toFixed(3)} · MAE {metrics.holdout.mae.toFixed(3)} · MAPE {metrics.holdout.mape.toFixed(1)}%
      </p>
      <p className="mt-1 text-xs text-muted">{role === 'PRIMARY' ? 'Uses container characteristics (customs, quarantine, red lane, arrivals)' : 'Uses past daily averages only'}</p>
    </div>
  )
}

export default function DwellPredictionPage() {
  const [days, setDays] = useState(14)
  const forecast = useApi(() => api.dwellForecast(days), [days])
  const metrics = useApi(() => api.modelMetrics())

  const f = forecast.data
  const m = metrics.data?.metrics
  const comparison = f?.model_comparison

  return (
    <>
      <PageHeader title="Dwell Time Prediction" subtitle="Prophet vs ARIMA model comparison." />
      <SubTabs tabs={PREDICTION_TABS} />

      {forecast.error && <ErrorMessage message={forecast.error} onRetry={forecast.reload} />}
      {!f && forecast.loading && <Loading text="Running dwell forecasts..." />}

      {comparison && (
        <div className="grid gap-4 lg:grid-cols-3">
          <ModelCard name="Facebook Prophet" role="PRIMARY" metrics={comparison.prophet} other={comparison.arima}
                     best={comparison.recommended === 'Prophet'} accent="#22d3ee" />
          <ModelCard name="ARIMA" role="BASELINE" metrics={comparison.arima} other={comparison.prophet}
                     best={comparison.recommended === 'ARIMA'} accent="#a78bfa" />
          <div className="card border-t-4" style={{ borderTopColor: '#10b981' }}>
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg">Per-container model</h2>
              <span className="badge border-line text-muted">XGBOOST</span>
            </div>
            {m ? (
              <>
                <p className="label mb-2">Individual container dwell (test containers)</p>
                <div className="grid grid-cols-3 gap-2">
                  <MetricBox label="MAE" value={m.per_container_dwell.mae.toFixed(2)} highlight />
                  <MetricBox label="RMSE" value={m.per_container_dwell.rmse.toFixed(2)} />
                  <MetricBox label="R²" value={m.per_container_dwell.r2.toFixed(2)} />
                </div>
                <p className="mt-3 text-xs text-muted">
                  Baseline MAE {m.per_container_dwell.baseline_mae.toFixed(2)} days ·{' '}
                  {(((m.per_container_dwell.baseline_mae - m.per_container_dwell.mae) / m.per_container_dwell.baseline_mae) * 100).toFixed(1)}% lower error
                </p>
                <p className="mt-1 text-xs text-muted">Gives each arriving container its own prediction</p>
              </>
            ) : metrics.error ? <ErrorMessage message={metrics.error} /> : <Loading />}
          </div>
        </div>
      )}

      {f && (
        <div className="card mt-6">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <h2 className="border-l-4 border-accent pl-3 text-lg">Prophet vs ARIMA — Predicted Average Dwell</h2>
            <div className="flex gap-1 rounded-lg border border-line bg-surface p-1">
              {[7, 14, 30].map((d) => (
                <button key={d} onClick={() => setDays(d)}
                        className={`rounded-md px-3 py-1 text-xs ${days === d ? 'bg-card text-accent' : 'text-muted hover:text-ink'}`}>
                  {d} days
                </button>
              ))}
            </div>
          </div>
          <DwellComparisonChart prophet={f.prophet_predictions} arima={f.arima_predictions} />
          {comparison && (
            <p className="mt-3 text-sm">
              <span className="font-semibold text-ok">Recommended: {comparison.recommended}</span>
              <span className="text-muted"> — {comparison.reason}</span>
            </p>
          )}
        </div>
      )}

      {f && (
        <div className="card mt-6 flex gap-3 text-sm text-muted">
          <Info size={18} className="mt-0.5 shrink-0 text-accent" />
          <div className="space-y-1">
            <p className="text-ink">How the comparison was made</p>
            <p>Both models were tested on the same 17 days (1 Jul – 20 Sep 2021 data, 80/20 split) with a rolling 7-day forecast.
               Prophet's settings were tuned on a validation period from the training data only.</p>
            <p>Forecast days continue from the end of the training data; "Day 1" is the first day after it.</p>
          </div>
        </div>
      )}
    </>
  )
}
