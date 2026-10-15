import { Link } from 'react-router-dom'
import { AlertTriangle, BellOff, CalendarClock, Gauge, RotateCw } from 'lucide-react'
import { api } from '../api/client'
import type { Alert } from '../api/types'
import ErrorMessage from '../components/ErrorMessage'
import Loading from '../components/Loading'
import PageHeader from '../components/PageHeader'
import { useApi } from '../hooks/useApi'

function AlertRow({ alert }: { alert: Alert }) {
  const zone = alert.type === 'zone_capacity'
  return (
    <div className="flex flex-wrap items-center gap-3 rounded-lg border border-danger/40 bg-danger/10 p-4">
      {zone ? <Gauge size={18} className="text-danger" /> : <CalendarClock size={18} className="text-danger" />}
      <div className="flex-1">
        <p className="text-sm font-medium text-danger">{alert.message}</p>
        <p className="text-xs text-muted">
          {zone ? 'Current zone occupancy' : `Forecast date ${alert.date} (day ${alert.day_ahead})`}
        </p>
      </div>
      <Link to={zone ? `/containers?zone=${encodeURIComponent(alert.zone ?? '')}` : '/predictions/occupancy'}
            className="btn-ghost py-1 text-xs">
        {zone ? 'View containers' : 'View forecast'}
      </Link>
    </div>
  )
}

export default function AlertsPage() {
  const result = useApi(() => api.alerts())
  const data = result.data
  const zoneAlerts = data?.alerts.filter((a) => a.type === 'zone_capacity') ?? []
  const forecastAlerts = data?.alerts.filter((a) => a.type === 'forecast_capacity') ?? []

  return (
    <>
      <PageHeader
        title="Alerts"
        subtitle={`Zones at or above ${data?.threshold_pct ?? 85}% capacity now, and days the yard is forecast to pass it (FR08).`}
        actions={<button className="btn-ghost" onClick={result.reload} disabled={result.loading}>
          <RotateCw size={14} className={result.loading ? 'animate-spin' : ''} /> Refresh
        </button>}
      />
      {result.error && <ErrorMessage message={result.error} onRetry={result.reload} />}
      {!data && result.loading && <Loading text="Checking capacity..." />}

      {data && data.alerts.length === 0 && (
        <div className="card flex flex-col items-center gap-2 py-12 text-center text-sm text-muted">
          <BellOff className="text-ok" />
          <p className="text-ink">No capacity alerts</p>
          <p>All zones are below {data.threshold_pct}% and no day in the next 14 days is forecast to pass it.</p>
        </div>
      )}

      {data && data.alerts.length > 0 && (
        <div className="space-y-6">
          <section className="card">
            <h2 className="card-title flex items-center gap-2"><AlertTriangle size={16} className="text-danger" />
              Zone capacity now ({zoneAlerts.length})</h2>
            <div className="space-y-3">
              {zoneAlerts.length ? zoneAlerts.map((a) => <AlertRow key={a.message} alert={a} />)
                : <p className="text-sm text-muted">All zones are below the threshold.</p>}
            </div>
          </section>
          <section className="card">
            <h2 className="card-title flex items-center gap-2"><CalendarClock size={16} className="text-danger" />
              14-day forecast ({forecastAlerts.length})</h2>
            <div className="space-y-3">
              {forecastAlerts.length ? forecastAlerts.map((a) => <AlertRow key={a.message} alert={a} />)
                : <p className="text-sm text-muted">No day in the next 14 days is forecast to pass the threshold.</p>}
            </div>
          </section>
        </div>
      )}
    </>
  )
}
