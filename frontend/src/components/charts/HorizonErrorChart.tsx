import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { colors } from '../../theme'

// Forecast error (MAPE) by number of days ahead - recursive XGBoost forecast
export default function HorizonErrorChart({ horizonMape }: { horizonMape: Record<string, number> }) {
  const data = Object.entries(horizonMape)
    .map(([day, mape]) => ({ day: Number(day), mape }))
    .sort((a, b) => a.day - b.day)
  return (
    <ResponsiveContainer width="100%" height={160}>
      <BarChart data={data} margin={{ top: 5, right: 5, left: -25, bottom: 0 }}>
        <CartesianGrid stroke={colors.line} strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="day" stroke={colors.muted} fontSize={10} tickLine={false} />
        <YAxis stroke={colors.muted} fontSize={10} tickLine={false} unit="%" />
        <Tooltip contentStyle={{ background: colors.surface, border: `1px solid ${colors.line}`, borderRadius: 8, fontSize: 12 }}
                 labelFormatter={(d) => `${d} day(s) ahead`} formatter={(v: number) => [`${v.toFixed(1)}%`, 'MAPE']} />
        <Bar dataKey="mape" fill={colors.accent} radius={[3, 3, 0, 0]} isAnimationActive={false} />
      </BarChart>
    </ResponsiveContainer>
  )
}
