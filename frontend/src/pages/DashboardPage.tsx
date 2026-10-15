import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { AlertTriangle, ArrowDownToLine, Boxes, Clock, PieChart, RotateCw, Truck } from 'lucide-react'
import { api } from '../api/client'
import OccupancyTrend from '../components/charts/OccupancyTrend'
import ErrorMessage from '../components/ErrorMessage'
import Loading from '../components/Loading'
import PageHeader from '../components/PageHeader'
import RecentAllocations from '../components/RecentAllocations'
import StatCard from '../components/StatCard'
import ZoneBars from '../components/ZoneBars'
import { useApi } from '../hooks/useApi'
import { formatNumber, formatPct } from '../utils/format'

export default function DashboardPage() {
  const summary = useApi(() => api.dashboard())
  const trend = useApi(() => api.occupancyForecast(7))

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

      {s && s.alerts.length > 0 && (
        <div className="mt-6 flex flex-wrap items-center gap-3 rounded-xl border border-danger/40 bg-danger/10 p-4 text-sm text-danger">
          <AlertTriangle size={18} />
          <span className="flex-1">{s.alerts.map((a) => a.message).join(' · ')}</span>
          <Link to="/alerts" className="underline">View alerts</Link>
        </div>
      )}

      {s && (
        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <div className="card">
            <div className="mb-2 flex items-center justify-between">
              <h2 className="card-title mb-0">7-Day Occupancy Forecast</h2>
              <Link to="/predictions/occupancy" className="text-xs text-accent hover:underline">Details</Link>
            </div>
            {trend.data ? <OccupancyTrend points={trend.data.predictions} />
              : trend.error ? <ErrorMessage message={trend.error} onRetry={trend.reload} /> : <Loading />}
            <p className="mt-2 text-[11px] text-muted">XGBoost forecast of total yard occupancy · red line = 85% alert threshold</p>
          </div>
          <div className="card">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="card-title mb-0">Zone-wise Occupancy</h2>
              <Link to="/yard-map" className="text-xs text-accent hover:underline">Yard map</Link>
            </div>
            <ZoneBars zones={s.zone_occupancy} />
          </div>
        </div>
      )}

      {s && (
        <div className="card mt-6">
          <div className="mb-2 flex items-center justify-between">
            <h2 className="card-title mb-0">Recent Container Allocations</h2>
            <Link to="/containers" className="text-xs text-accent hover:underline">View all</Link>
          </div>
          <RecentAllocations rows={s.recent_allocations} />
        </div>
      )}
    </>
  )
}
