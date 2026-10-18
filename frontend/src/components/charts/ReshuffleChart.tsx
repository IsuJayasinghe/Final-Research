import { Bar, BarChart, CartesianGrid, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { colors } from '../../theme'

interface Props {
  random: number
  ai: number
  perfect: number
}

// Total reshuffles in the stacking simulation: random placement vs AI vs AI with perfect dwell knowledge
export default function ReshuffleChart({ random, ai, perfect }: Props) {
  const data = [
    { name: 'Random placement', value: random, color: colors.danger },
    { name: 'AI (predicted dwell)', value: ai, color: colors.ok },
    { name: 'AI (perfect knowledge)', value: perfect, color: '#38bdf8' },
  ]
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} margin={{ top: 24, right: 10, left: -5, bottom: 0 }}>
        <CartesianGrid stroke={colors.line} strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="name" stroke={colors.muted} fontSize={11} tickLine={false} />
        <YAxis stroke={colors.muted} fontSize={11} tickLine={false} />
        <Tooltip contentStyle={{ background: colors.surface, border: `1px solid ${colors.line}`, borderRadius: 8, fontSize: 12 }}
                 formatter={(v: number) => [Math.round(v).toLocaleString(), 'Reshuffles']} cursor={{ fill: '#ffffff08' }} />
        <Bar dataKey="value" radius={[4, 4, 0, 0]} isAnimationActive={false}>
          {data.map((d) => <Cell key={d.name} fill={d.color} />)}
          <LabelList dataKey="value" position="top" fill={colors.ink} fontSize={12}
                     formatter={(v: number) => Math.round(v).toLocaleString()} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
