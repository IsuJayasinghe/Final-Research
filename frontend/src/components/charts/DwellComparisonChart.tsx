import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { DwellPoint } from '../../api/types'
import { colors } from '../../theme'

// Prophet (primary) vs ARIMA (baseline) daily average dwell forecast
export default function DwellComparisonChart({ prophet, arima }: { prophet: DwellPoint[]; arima: DwellPoint[] }) {
  const data = prophet.map((p, i) => ({
    day: `Day ${p.day_ahead}`, prophet: p.predicted_dwell_days, arima: arima[i]?.predicted_dwell_days,
  }))
  return (
    <ResponsiveContainer width="100%" height={320}>
      <LineChart data={data} margin={{ top: 10, right: 16, left: -6, bottom: 0 }}>
        <CartesianGrid stroke={colors.line} strokeDasharray="3 3" />
        <XAxis dataKey="day" stroke={colors.muted} fontSize={11} tickLine={false} />
        <YAxis stroke={colors.muted} fontSize={11} tickLine={false} domain={['auto', 'auto']}
               label={{ value: 'Avg dwell (days)', angle: -90, position: 'insideLeft', fill: colors.muted, fontSize: 11, dx: 14 }} />
        <Tooltip contentStyle={{ background: colors.surface, border: `1px solid ${colors.line}`, borderRadius: 8, fontSize: 12 }}
                 formatter={(v: number) => `${v.toFixed(2)} days`} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Line type="monotone" dataKey="prophet" name="Prophet (Primary)" stroke={colors.accent} strokeWidth={2.5}
              dot={{ r: 3 }} isAnimationActive={false} />
        <Line type="monotone" dataKey="arima" name="ARIMA (Baseline)" stroke="#a78bfa" strokeWidth={2}
              strokeDasharray="6 4" dot={{ r: 3 }} isAnimationActive={false} />
      </LineChart>
    </ResponsiveContainer>
  )
}
