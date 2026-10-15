import { Bar, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { OccupancyPoint } from '../../api/types'
import { colors } from '../../theme'

// Predicted containers in the yard (line) and the incoming volumes used as input (bars)
export default function ArrivalsChart({ points }: { points: OccupancyPoint[] }) {
  const data = points.map((p) => ({ day: `Day ${p.day_ahead}`, containers: p.predicted_containers, arrivals: p.planned_arrivals }))
  return (
    <ResponsiveContainer width="100%" height={240}>
      <ComposedChart data={data} margin={{ top: 10, right: 10, left: -5, bottom: 0 }}>
        <CartesianGrid stroke={colors.line} strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="day" stroke={colors.muted} fontSize={11} tickLine={false} />
        <YAxis stroke={colors.muted} fontSize={11} tickLine={false} />
        <Tooltip contentStyle={{ background: '#111c30', border: `1px solid ${colors.line}`, borderRadius: 8, fontSize: 12 }} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Bar dataKey="arrivals" name="Planned arrivals" fill="#334866" radius={[3, 3, 0, 0]} isAnimationActive={false} />
        <Line type="monotone" dataKey="containers" name="Predicted containers in yard" stroke={colors.accent}
              strokeWidth={2} dot={{ r: 3 }} isAnimationActive={false} />
      </ComposedChart>
    </ResponsiveContainer>
  )
}
