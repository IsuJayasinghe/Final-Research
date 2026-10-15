import { useEffect } from 'react'
import { AlertTriangle, ArrowDownToLine, Boxes, Clock, PieChart, RotateCw, Truck } from 'lucide-react'
import { api } from '../api/client'
import ErrorMessage from '../components/ErrorMessage'
import Loading from '../components/Loading'
import PageHeader from '../components/PageHeader'
import StatCard from '../components/StatCard'
import { useApi } from '../hooks/useApi'
import { formatNumber, formatPct } from '../utils/format'

export default function DashboardPage() {
  const summary = useApi(() => api.dashboard())

  // keep the overview current while it is open
  useEffect(() => {
    const timer = setInterval(summary.reload, 30000)
    return () => clearInterval(timer)
  }, [summary.reload])

  const s = summary.data
  return (
    <>
      <PageHeader
        title="Yard Overview"
        subtitle="Real-time container yard monitoring and AI-powered allocation."
        actions={
          <button className="btn-ghost" onClick={summary.reload} disabled={summary.loading}>
            <RotateCw size={14} className={summary.loading ? 'animate-spin' : ''} /> Refresh
          </button>
        }
      />

      {summary.error && <ErrorMessage message={summary.error} onRetry={summary.reload} />}
      {!s && summary.loading && <Loading text="Loading yard overview..." />}

      {s && (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
          <StatCard label="Total containers" value={formatNumber(s.total_containers)} icon={Boxes}
                    hint="currently in the yard" />
          <StatCard label="Yard occupancy" value={formatPct(s.yard_occupancy_pct)} icon={PieChart}
                    hint={s.yard_occupancy_pct >= 85 ? 'above the 85% threshold' : 'of total slot capacity'}
                    tone={s.yard_occupancy_pct >= 85 ? 'danger' : 'default'} />
          <StatCard label="Arrived today" value={formatNumber(s.arrived_today)} icon={ArrowDownToLine}
                    hint="new allocations today" tone="accent" />
          <StatCard label="Departing today" value={formatNumber(s.expected_departures_today)} icon={Truck}
                    hint={`${formatNumber(s.departed_today)} already left`} tone="ok" />
          <StatCard label="Overstaying" value={formatNumber(s.overstaying)} icon={Clock}
                    hint={s.overstaying ? <span className="inline-flex items-center gap-1"><AlertTriangle size={12} /> past predicted departure</span> : 'none'}
                    tone={s.overstaying ? 'danger' : 'ok'} />
        </div>
      )}
    </>
  )
}
