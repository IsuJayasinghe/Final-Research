import type { LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'

interface Props {
  label: string
  value: ReactNode
  icon: LucideIcon
  hint?: ReactNode
  tone?: 'default' | 'ok' | 'warn' | 'danger' | 'accent'
}

const TONE = {
  default: 'text-muted',
  ok: 'text-ok',
  warn: 'text-warn',
  danger: 'text-danger',
  accent: 'text-accent',
}

export default function StatCard({ label, value, icon: Icon, hint, tone = 'default' }: Props) {
  return (
    <div className="card">
      <div className="flex items-start justify-between">
        <p className="label">{label}</p>
        <Icon size={18} className="text-muted" />
      </div>
      <p className="mt-3 text-3xl font-bold">{value}</p>
      {hint && <p className={`mt-1 text-xs ${TONE[tone]}`}>{hint}</p>}
    </div>
  )
}
