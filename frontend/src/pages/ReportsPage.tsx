import { CheckCircle2, Download, Info, Layers, Repeat, ShieldCheck, TrendingDown, XCircle } from 'lucide-react'
import { api } from '../api/client'
import ReshuffleChart from '../components/charts/ReshuffleChart'
import ErrorMessage from '../components/ErrorMessage'
import Loading from '../components/Loading'
import PageHeader from '../components/PageHeader'
import StatCard from '../components/StatCard'
import { useApi } from '../hooks/useApi'
import { downloadCsv } from '../utils/csv'

interface Row {
  area: string
  metric: string
  target: string
  achieved: string
  met: boolean | null              // null = no target in the proposal
}

export default function ReportsPage() {
  const sim = useApi(() => api.reshuffling())
  const metrics = useApi(() => api.modelMetrics())

  const s = sim.data?.simulation_results
  const m = metrics.data?.metrics

  const rows: Row[] = m && s ? [
    { area: 'Dwell time (Prophet)', metric: 'MAPE, rolling 7-day', target: '< 15%',
      achieved: `${m.dwell_time.prophet.rolling_7d.mape.toFixed(1)}%`, met: m.dwell_time.prophet.rolling_7d.mape < 15 },
    { area: 'Dwell time (Prophet)', metric: 'RMSE / MAE (days)', target: '< 2.0 / < 1.5',
      achieved: `${m.dwell_time.prophet.rolling_7d.rmse.toFixed(3)} / ${m.dwell_time.prophet.rolling_7d.mae.toFixed(3)}`,
      met: m.dwell_time.prophet.rolling_7d.rmse < 2 && m.dwell_time.prophet.rolling_7d.mae < 1.5 },
    { area: 'Prophet vs ARIMA', metric: 'Lower error than baseline (MAE)', target: 'Prophet < ARIMA',
      achieved: `${m.dwell_time.prophet.rolling_7d.mae.toFixed(3)} vs ${m.dwell_time.arima.rolling_7d.mae.toFixed(3)}`,
      met: m.dwell_time.prophet.rolling_7d.mae < m.dwell_time.arima.rolling_7d.mae },
    { area: 'Yard occupancy (XGBoost)', metric: 'R², next-day', target: '> 0.80',
      achieved: m.occupancy.next_day.r2.toFixed(3), met: m.occupancy.next_day.r2 > 0.8 },
    { area: 'Yard occupancy (XGBoost)', metric: 'MAPE, 7-14 days ahead', target: '7-14 day forecast',
      achieved: `${Math.min(...Object.entries(m.occupancy.horizon_mape).filter(([d]) => +d >= 7).map(([, v]) => v)).toFixed(1)}-${Math.max(...Object.entries(m.occupancy.horizon_mape).filter(([d]) => +d >= 7).map(([, v]) => v)).toFixed(1)}%`,
      met: true },
    { area: 'Reshuffling simulation', metric: 'Reshuffle reduction vs random', target: '>= 25%',
      achieved: `${s.reshuffle_reduction_pct.toFixed(1)}%`, met: s.reshuffle_reduction_pct >= 25 },
    { area: 'Yard-type rules', metric: 'Reefer / hazmat misplacements (AI)', target: '0',
      achieved: String(Math.round(s.type_violations.ai)), met: s.type_violations.ai === 0 },
    { area: 'Per-container dwell (XGBoost)', metric: 'MAE vs median baseline (days)', target: 'Better than baseline',
      achieved: `${m.per_container_dwell.mae.toFixed(2)} vs ${m.per_container_dwell.baseline_mae.toFixed(2)}`,
      met: m.per_container_dwell.mae < m.per_container_dwell.baseline_mae },
    ...(m.zone_engine ? [{ area: 'Zone classification', metric: 'Zone matches actual dwell (DRY)', target: '—',
      achieved: `${m.zone_engine.zone_match_pct.toFixed(1)}% (always Fast-Access: ${m.zone_engine.always_fast_access_pct.toFixed(1)}%)`,
      met: null }] : []),
  ] : []

  const exportCsv = () => downloadCsv('yard-evaluation.csv', rows.map((r) => ({
    area: r.area, metric: r.metric, proposal_target: r.target, achieved: r.achieved,
    status: r.met === null ? 'n/a' : r.met ? 'met' : 'not met',
  })))

  const error = sim.error ?? metrics.error
  return (
    <>
      <PageHeader
        title="Reports"
        subtitle="Reshuffling simulation and model evaluation results."
        actions={rows.length > 0 && <button className="btn-ghost" onClick={exportCsv}><Download size={14} /> Export CSV</button>}
      />
      {error && <ErrorMessage message={error} onRetry={() => { sim.reload(); metrics.reload() }} />}
      {(!s || !m) && !error && <Loading text="Loading evaluation results..." />}

      {s && (
        <>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <StatCard label="Reshuffle reduction" value={`${s.reshuffle_reduction_pct.toFixed(1)}%`} icon={TrendingDown}
                      hint="target: at least 25%" tone="ok" />
            <StatCard label="Reshuffles saved" value={s.reshuffles_saved.toLocaleString()} icon={Repeat}
                      hint={`${Math.round(s.reshuffles_random).toLocaleString()} → ${Math.round(s.reshuffles_ai).toLocaleString()}`} tone="accent" />
            <StatCard label="Retrievals without reshuffle" value={`${s.retrievals_without_reshuffle_pct.ai.toFixed(1)}%`} icon={Layers}
                      hint={`random placement: ${s.retrievals_without_reshuffle_pct.random.toFixed(1)}%`} />
            <StatCard label="Yard-type violations" value={Math.round(s.type_violations.ai)} icon={ShieldCheck}
                      hint={`random placement: ${Math.round(s.type_violations.random).toLocaleString()}`} tone="ok" />
          </div>

          <div className="card mt-6">
            <h2 className="card-title">Yard Stacking Simulation — Total Reshuffles</h2>
            <ReshuffleChart random={s.reshuffles_random} ai={s.reshuffles_ai}
                            perfect={s.reshuffles_random * (1 - s.perfect_knowledge_reduction_pct / 100)} />
            <p className="mt-2 flex gap-2 text-xs text-muted">
              <Info size={14} className="mt-0.5 shrink-0" />
              Yard Block 01: about {s.containers_simulated.toLocaleString()} containers per run (its share of the test period), {s.runs} runs. {sim.data!.method}. The AI only sees
              predicted dwell times; "perfect knowledge" shows the limit if dwell were known exactly.
            </p>
          </div>
        </>
      )}

      {rows.length > 0 && (
        <div className="card mt-6 p-0">
          <h2 className="card-title px-5 pt-5">Results vs Proposal Targets</h2>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px]">
              <thead>
                <tr>{['Area', 'Metric', 'Proposal target', 'Achieved', 'Status'].map((h) => <th key={h} className="table-head">{h}</th>)}</tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.area + r.metric}>
                    <td className="table-cell">{r.area}</td>
                    <td className="table-cell text-muted">{r.metric}</td>
                    <td className="table-cell text-muted">{r.target}</td>
                    <td className="table-cell font-medium">{r.achieved}</td>
                    <td className="table-cell">
                      {r.met === null ? <span className="text-xs text-muted">reported</span>
                        : r.met ? <span className="inline-flex items-center gap-1 text-ok"><CheckCircle2 size={14} /> Met</span>
                        : <span className="inline-flex items-center gap-1 text-danger"><XCircle size={14} /> Not met</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {m && (
        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <div className="card text-sm">
            <h2 className="card-title">Data</h2>
            <ul className="space-y-1.5 text-muted">
              <li><span className="text-ink">{m.data.containers.toLocaleString()}</span> containers from the Kaggle container terminal event log</li>
              <li>Modelling window: <span className="text-ink">{m.data.window_start}</span> to <span className="text-ink">{m.data.window_end}</span></li>
              <li>Scope: one yard block (Yard Block 01), receiving {Math.round((m.block?.share_of_terminal ?? 0.25) * 100)}% of the terminal's containers</li>
              <li>Container type mix from Colombo Port data</li>
              <li>Chronological train / test split; settings tuned on validation data only</li>
            </ul>
          </div>
          <div className="card text-sm">
            <h2 className="card-title">Limitations</h2>
            <ul className="list-disc space-y-1.5 pl-5 text-muted">
              <li>About 3 months of data, so the test period is short (17 days).</li>
              <li>Kaggle data has no container type; the simulation assigns types following the Colombo mix.</li>
              <li>The data covers the whole terminal and does not record blocks; the block is assumed to receive a fixed share of containers.</li>
              <li>Zone classification alone is close to the "always Fast-Access" baseline; the gain comes from stacking order and yard-type rules.</li>
              <li>Future arrivals and container characteristics use weekday averages until vessel data from Component 1 is connected.</li>
            </ul>
          </div>
        </div>
      )}
    </>
  )
}
