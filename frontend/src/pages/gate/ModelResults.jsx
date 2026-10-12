import { Loader2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { getModelMetrics } from '../../lib/gateApi'

const POLICY_LABELS = {
  static_tas: 'Static TAS',
  blind_overbooking: 'Blind +20% overbooking',
  framework: 'No-show-aware framework',
}

function Card({ title, subtitle, children }) {
  return (
    <section className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      <h2 className="text-base font-bold text-[#123a5c]">{title}</h2>
      {subtitle && <p className="mt-1 text-xs text-gray-500">{subtitle}</p>}
      <div className="mt-4 overflow-x-auto">{children}</div>
    </section>
  )
}

function Table({ head, rows, highlightRow }) {
  return (
    <table className="w-full text-left text-sm">
      <thead className="text-xs uppercase tracking-wide text-gray-500">
        <tr>
          {head.map((h) => (
            <th key={h} className="px-2 py-2 font-medium">
              {h}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((r, i) => (
          <tr
            key={i}
            className={`border-t border-gray-100 ${i === highlightRow ? 'bg-[#123a5c]/5 font-semibold text-[#123a5c]' : 'text-gray-700'}`}
          >
            {r.map((c, j) => (
              <td key={j} className="px-2 py-2">
                {c}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  )
}

const f1 = (v) => Number(v).toFixed(1)
const f2 = (v) => Number(v).toFixed(2)
const f3 = (v) => Number(v).toFixed(3)
const signed = (v, d = 1) => `${v > 0 ? '+' : ''}${Number(v).toFixed(d)}`

function ClearanceSection({ m }) {
  const rows = [
    ['Mean predictor (baseline)', f2(m.baseline_mean.rmse), f2(m.baseline_mean.mae), `${f1(m.baseline_mean.mape)}%`],
    ['Random Forest', f2(m.random_forest.rmse), f2(m.random_forest.mae), `${f1(m.random_forest.mape)}%`],
    ['XGBoost (selected)', f2(m.xgboost.rmse), f2(m.xgboost.mae), `${f1(m.xgboost.mape)}%`],
  ]
  return (
    <Card
      title="Clearance-time model"
      subtitle="Predicts minutes a truck spends clearing the gate. Chronological hold-out; lower is better."
    >
      <Table head={['Model', 'RMSE (min)', 'MAE (min)', 'MAPE']} rows={rows} highlightRow={2} />
    </Card>
  )
}

function CongestionSection({ m }) {
  const lanes = Object.keys(m.sarimax)
  const rows = lanes.map((l) => [
    l.replace('lane_', 'Gate '),
    f2(m.naive_baseline[l].rmse),
    f2(m.sarimax[l].rmse),
    `${Math.round((1 - m.sarimax[l].rmse / m.naive_baseline[l].rmse) * 100)}%`,
  ])
  return (
    <Card
      title="Congestion forecast (Model 1)"
      subtitle="One SARIMAX per lane with a 24-hour seasonal cycle, scored on a 14-day hold-out."
    >
      <Table head={['Lane', 'Naive RMSE', 'SARIMAX RMSE', 'Error reduction']} rows={rows} />
    </Card>
  )
}

function NoShowSection({ m, shap }) {
  const lr = m.class_balanced_test_metrics.logistic_regression
  const xgb = m.class_balanced_test_metrics.xgboost
  const row = (name, r) => [
    name,
    f3(r.per_class.no_show.precision),
    f3(r.per_class.no_show.recall),
    f3(r.per_class.no_show['f1-score']),
    f3(r.roc_auc_no_show),
    f3(r.pr_auc_no_show),
    f3(r.roc_auc_macro_ovr),
  ]
  const cal = m.serving_model_calibration
  const top = (shap ?? []).slice(0, 8)
  const maxShap = Math.max(...top.map((s) => s.mean_abs_shap_no_show), 0.0001)
  return (
    <Card
      title="No-show / late-arrival risk (Model 2)"
      subtitle={`Predicts on-time, late or no-show per booking. Test period: ${m.test_rows} bookings, ${Math.round(
        m.test_class_share.no_show * 1000,
      ) / 10}% no-shows. Class-balanced models shown for recall.`}
    >
      <Table
        head={['Model', 'No-show precision', 'No-show recall', 'No-show F1', 'No-show ROC-AUC', 'No-show PR-AUC', 'Macro ROC-AUC']}
        rows={[row('Logistic Regression (baseline)', lr), row('XGBoost', xgb)]}
        highlightRow={m.serving_model === 'xgboost' ? 1 : 0}
      />
      <p className="mt-3 text-xs text-gray-600">
        Serving model: <b>{m.serving_model}</b> (chosen on a validation slice), trained without class
        weights so probabilities are calibrated for the overbooking rule: mean predicted no-show{' '}
        <b>{(cal.mean_predicted_no_show * 100).toFixed(1)}%</b> vs observed{' '}
        <b>{(cal.observed_no_show_rate * 100).toFixed(1)}%</b>; Brier {cal.brier_no_show} vs{' '}
        {cal.brier_no_show_constant_baseline} for a constant guess.
      </p>
      <h3 className="mt-5 text-xs font-semibold uppercase tracking-wide text-gray-500">
        What drives no-show risk (SHAP)
      </h3>
      <ul className="mt-2 space-y-1.5">
        {top.map((s) => (
          <li key={s.feature} className="grid grid-cols-[14rem_1fr] items-center gap-2 text-xs">
            <span className="truncate text-gray-700">{s.feature.replaceAll('_', ' ')}</span>
            <span className="block h-2.5 rounded bg-gray-100">
              <span
                className="block h-2.5 rounded bg-[#123a5c]"
                style={{ width: `${(s.mean_abs_shap_no_show / maxShap) * 100}%` }}
              />
            </span>
          </li>
        ))}
      </ul>
    </Card>
  )
}

function FrameworkSection({ e }) {
  const names = ['static_tas', 'blind_overbooking', 'framework']
  const r = e.results_per_day
  const rows = names.map((n) => [
    POLICY_LABELS[n],
    f1(r[n].accepted.mean),
    f1(r[n].served.mean),
    f2(r[n].avg_wait_min.mean),
    f1(r[n].p90_wait_min.mean),
    f1(r[n].avg_turn_min.mean),
    `${(r[n].adherence.mean * 100).toFixed(1)}%`,
  ])
  const sens = Object.entries(e.sensitivity_by_slot_capacity)
  const sensRows = sens.map(([cap, v]) => [
    `${cap} per slot`,
    f1(v.static_tas.served),
    f1(v.framework.served),
    `${signed(v.framework_vs_static_served.mean)} ± ${f1(v.framework_vs_static_served.ci95)}`,
    `${signed(v.framework_vs_static_wait_min.mean, 2)} min`,
    `${signed(v.blind_overbooking.avg_wait_min - v.static_tas.avg_wait_min, 2)} min`,
  ])
  return (
    <Card
      title="Framework evaluation (end-to-end simulation)"
      subtitle={`${e.setup.days} simulated days, ${e.setup.requests_per_day} requests/day, ${e.setup.lanes} lanes, ${e.setup.slot_capacity} bookings per slot. Same demand and outcomes for every policy.`}
    >
      <Table
        head={['Policy', 'Accepted/day', 'Served/day', 'Avg wait (min)', 'P90 wait', 'Avg turn (min)', 'Slot adherence']}
        rows={rows}
        highlightRow={2}
      />
      <h3 className="mt-5 text-xs font-semibold uppercase tracking-wide text-gray-500">
        Sensitivity to slot capacity
      </h3>
      <Table
        head={['Slot capacity', 'Static served', 'Framework served', 'Framework gain/day', 'Framework extra wait', 'Blind +20% extra wait']}
        rows={sensRows}
      />
      <ul className="mt-4 list-disc space-y-1 pl-5 text-xs text-gray-600">
        {e.assumptions.map((a) => (
          <li key={a}>{a}</li>
        ))}
      </ul>
    </Card>
  )
}

export default function ModelResults() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    getModelMetrics()
      .then(setData)
      .catch((err) =>
        setError(
          err instanceof TypeError
            ? 'Could not reach the gate appointment service. Is the backend running?'
            : err.message,
        ),
      )
  }, [])

  return (
    <div className="mx-auto max-w-5xl px-4 py-10 sm:px-6 lg:px-8">
      <h1 className="text-2xl font-bold text-[#123a5c]">Model Results</h1>
      <p className="mt-1 text-sm text-gray-600">
        Evaluation of the two prediction models and the full appointment framework. Booking data is
        synthetic (as the technical plan allows); all scores are on held-out periods.
      </p>

      {error && (
        <div className="mt-4 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}
      {!data && !error && (
        <div className="mt-6 flex items-center gap-2 text-sm text-gray-500">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading results...
        </div>
      )}

      {data && (
        <div className="mt-6 space-y-6">
          {data.framework_evaluation && <FrameworkSection e={data.framework_evaluation} />}
          {data.no_show && <NoShowSection m={data.no_show} shap={data.shap_importance} />}
          {data.congestion_forecast && <CongestionSection m={data.congestion_forecast} />}
          {data.clearance_time && <ClearanceSection m={data.clearance_time} />}
        </div>
      )}
    </div>
  )
}
