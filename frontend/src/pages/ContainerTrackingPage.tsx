import { useEffect, useState, type FormEvent } from 'react'
import { useSearchParams } from 'react-router-dom'
import { ChevronLeft, ChevronRight, Download, LogOut, Search } from 'lucide-react'
import { api } from '../api/client'
import type { ContainerFilters, ContainerRecord } from '../api/types'
import { StatusBadge, TypeBadge, ZoneBadge } from '../components/Badges'
import ErrorMessage from '../components/ErrorMessage'
import Loading from '../components/Loading'
import PageHeader from '../components/PageHeader'
import SubTabs, { CONTAINER_TABS } from '../components/SubTabs'
import { useToast } from '../components/Toast'
import { useApi } from '../hooks/useApi'
import { ZONE_ORDER } from '../theme'
import { downloadCsv } from '../utils/csv'
import { formatDateTime, formatDays } from '../utils/format'

const PAGE_SIZE = 20

export default function ContainerTrackingPage() {
  const toast = useToast()
  const [params, setParams] = useSearchParams()
  const filters: ContainerFilters = {
    search: params.get('search') ?? '', type: params.get('type') ?? '', zone: params.get('zone') ?? '',
    status: params.get('status') ?? 'active', page: Number(params.get('page') ?? 1), limit: PAGE_SIZE,
  }
  const [draft, setDraft] = useState(filters)
  const [departing, setDeparting] = useState<string | null>(null)
  const [exporting, setExporting] = useState(false)
  const key = params.toString()
  const result = useApi(() => api.containers(filters), [key])
  // keep the filter inputs in step with the URL (e.g. after clicking the Active / Overstaying chips)
  useEffect(() => setDraft(filters), [key]) // eslint-disable-line react-hooks/exhaustive-deps

  // filters live in the URL so a search can be linked to (e.g. from the dashboard)
  const apply = (next: ContainerFilters) => {
    const p = new URLSearchParams()
    for (const [k, v] of Object.entries(next)) if (v && k !== 'limit' && !(k === 'page' && v === 1)) p.set(k, String(v))
    setParams(p)
  }
  const submit = (e: FormEvent) => {
    e.preventDefault()
    apply({ ...draft, page: 1 })
  }

  const depart = async (row: ContainerRecord) => {
    if (!window.confirm(`Release ${row.container_id} from slot ${row.slot}? This records the container leaving the yard.`)) return
    setDeparting(row.container_id)
    try {
      const r = await api.depart(row.container_id)
      toast(`${r.container_id} left the yard (slot ${r.freed_slot} freed${r.reshuffles ? `, ${r.reshuffles} reshuffle(s)` : ''})`)
      result.reload()
    } catch (e) {
      toast((e as Error).message, 'error')
    } finally {
      setDeparting(null)
    }
  }

  const exportCsv = async () => {
    setExporting(true)
    try {
      const rows: ContainerRecord[] = []
      for (let page = 1; ; page++) {
        const r = await api.containers({ ...filters, page, limit: 100 })
        rows.push(...r.containers)
        if (rows.length >= r.total || r.containers.length === 0) break
      }
      downloadCsv(`containers-${new Date().toISOString().slice(0, 10)}.csv`, rows.map((r) => ({
        container_id: r.container_id, type: r.container_type, cargo: r.cargo_type, shipping_line: r.shipping_line,
        zone: r.zone, block: r.block, slot: r.slot, arrival: r.arrival, predicted_dwell_days: r.predicted_dwell_days,
        predicted_departure: r.predicted_departure, status: r.status, allocation_status: r.allocation_status,
        override_reason: r.override_reason,
      })))
    } catch (e) {
      toast((e as Error).message, 'error')
    } finally {
      setExporting(false)
    }
  }

  const data = result.data
  const pages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1
  const page = filters.page ?? 1

  return (
    <>
      <PageHeader
        title="Container Tracking"
        subtitle="Search, filter, and track all containers in the yard."
        actions={data && (
          <>
            <button className="badge border-ok/40 bg-ok/10 px-3 py-1 text-ok" onClick={() => apply({ ...filters, status: 'active', page: 1 })}>
              ● Active: {data.counts.active.toLocaleString()}
            </button>
            <button className="badge border-danger/40 bg-danger/10 px-3 py-1 text-danger" onClick={() => apply({ ...filters, status: 'overstaying', page: 1 })}>
              ● Overstaying: {data.counts.overstaying.toLocaleString()}
            </button>
          </>
        )}
      />
      <SubTabs tabs={CONTAINER_TABS} />

      <form onSubmit={submit} className="card mb-6 flex flex-wrap gap-3 p-4">
        <div className="relative min-w-[220px] flex-1">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
          <input className="input pl-9" placeholder="Search by container ID or slot..." value={draft.search}
                 onChange={(e) => setDraft({ ...draft, search: e.target.value })} />
        </div>
        <select className="input w-auto" value={draft.type} onChange={(e) => setDraft({ ...draft, type: e.target.value })}>
          <option value="">All types</option>
          {['DRY', 'REEFER', 'HAZMAT', 'OVERSIZED'].map((t) => <option key={t}>{t}</option>)}
        </select>
        <select className="input w-auto" value={draft.zone} onChange={(e) => setDraft({ ...draft, zone: e.target.value })}>
          <option value="">All zones</option>
          {ZONE_ORDER.map((z) => <option key={z}>{z}</option>)}
        </select>
        <select className="input w-auto" value={draft.status} onChange={(e) => setDraft({ ...draft, status: e.target.value })}>
          <option value="all">All status</option>
          <option value="active">Active</option>
          <option value="overstaying">Overstaying</option>
          <option value="released">Released</option>
        </select>
        <button type="submit" className="btn-primary">Apply filter</button>
      </form>

      {result.error && <ErrorMessage message={result.error} onRetry={result.reload} />}
      {!data && result.loading && <Loading text="Loading containers..." />}

      {data && (
        <div className="card p-0">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[960px]">
              <thead>
                <tr>
                  {['Container ID', 'Type', 'Cargo', 'Zone / slot', 'Shipping line', 'Arrival', 'Predicted dwell', 'Status', ''].map((h) => (
                    <th key={h} className="table-head">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.containers.map((r) => (
                  <tr key={r.allocation_id} className={r.status === 'Overstaying' ? 'bg-danger/5' : ''}
                      title={r.override_reason ? `Override: ${r.override_reason}` : r.reason ?? ''}>
                    <td className="table-cell font-mono text-accent">{r.container_id}</td>
                    <td className="table-cell"><TypeBadge type={r.container_type} /></td>
                    <td className="table-cell text-muted">{r.cargo_type ?? '—'}</td>
                    <td className="table-cell whitespace-nowrap">
                      <ZoneBadge zone={r.zone} />
                      <span className="ml-2 font-mono text-xs text-muted">{r.slot}</span>
                      {r.allocation_status === 'OVERRIDDEN' && <span className="ml-2 text-[10px] text-warn">overridden</span>}
                    </td>
                    <td className="table-cell text-muted">{r.shipping_line ?? '—'}</td>
                    <td className="table-cell whitespace-nowrap text-muted">{formatDateTime(r.arrival)}</td>
                    <td className={`table-cell ${r.status === 'Overstaying' ? 'font-semibold text-danger' : ''}`}>{formatDays(r.predicted_dwell_days)}</td>
                    <td className="table-cell"><StatusBadge status={r.status} /></td>
                    <td className="table-cell text-right">
                      {r.status !== 'Released' && (
                        <button className="btn-ghost px-2 py-1 text-xs" onClick={() => depart(r)} disabled={departing === r.container_id}>
                          <LogOut size={12} /> Depart
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
                {data.containers.length === 0 && (
                  <tr><td colSpan={9} className="table-cell py-10 text-center text-muted">No containers match these filters.</td></tr>
                )}
              </tbody>
            </table>
          </div>
          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line px-4 py-3 text-sm text-muted">
            <span>Showing {data.containers.length} of {data.total.toLocaleString()} containers</span>
            <div className="flex items-center gap-2">
              <button className="btn-ghost px-2 py-1" disabled={page <= 1} onClick={() => apply({ ...filters, page: page - 1 })}>
                <ChevronLeft size={14} />
              </button>
              <span>Page {page} of {pages}</span>
              <button className="btn-ghost px-2 py-1" disabled={page >= pages} onClick={() => apply({ ...filters, page: page + 1 })}>
                <ChevronRight size={14} />
              </button>
              <button className="ml-2 flex items-center gap-1 text-accent hover:underline disabled:opacity-50" onClick={exportCsv}
                      disabled={exporting || data.total === 0}>
                <Download size={14} /> {exporting ? 'Exporting...' : 'Export CSV'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
