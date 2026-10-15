import { Area, AreaChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { OccupancyPoint } from '../../api/types'
import { colors } from '../../theme'

// Predicted yard utilisation for the coming days (XGBoost), with the 85% alert line (FR08)
export default function OccupancyTrend({ points, height = 240 }: { points: OccupancyPoint[]; height?: number }) {
  const data = points.map((p) => ({ day: `Day ${p.day_ahead}`, utilization: p.utilization_pct, containers: p.predicted_containers }))
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
        <defs>
          <linearGradient id="occFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={colors.accent} stopOpacity={0.35} />
            <stop offset="100%" stopColor={colors.accent} stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke={colors.line} strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="day" stroke={colors.muted} fontSize={11} tickLine={false} />
        <YAxis stroke={colors.muted} fontSize={11} tickLine={false} unit="%" domain={[0, 100]} />
        <Tooltip
          contentStyle={{ background: '#111c30', border: `1px solid ${colors.line}`, borderRadius: 8, fontSize: 12 }}
          formatter={(value: number, name) => (name === 'utilization' ? [`${value}%`, 'Predicted occupancy'] : [value, name])}
        />
        <ReferenceLine y={85} stroke={colors.danger} strokeDasharray="4 4"
                       label={{ value: '85% alert', fill: colors.danger, fontSize: 10, position: 'insideTopRight' }} />
        <Area type="monotone" dataKey="utilization" stroke={colors.accent} strokeWidth={2} fill="url(#occFill)"
              isAnimationActive={false} dot={{ r: 3, fill: colors.accent }} />
      </AreaChart>
    </ResponsiveContainer>
  )
}
