import type {
  AcceptResult,
  AlertsResponse,
  AllocationResult,
  ArrivalRequest,
  ContainerFilters,
  ContainerRecord,
  ContainerSearch,
  DashboardSummary,
  DepartResult,
  DwellForecast,
  Health,
  ModelMetrics,
  OccupancyForecast,
  OverrideResult,
  ReshufflingStats,
  YardZones,
} from './types'

export const API_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:5001'

export class ApiError extends Error {
  constructor(message: string, public status?: number) {
    super(message)
  }
}

async function request<T>(path: string, options?: { method?: string; body?: unknown }): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_URL}${path}`, {
      method: options?.method ?? 'GET',
      headers: options?.body ? { 'Content-Type': 'application/json' } : undefined,
      body: options?.body ? JSON.stringify(options.body) : undefined,
    })
  } catch {
    throw new ApiError(`Cannot reach the yard API at ${API_URL}. Is the backend running?`)
  }
  const data = await response.json().catch(() => null)
  if (!response.ok || data?.status === 'error') {
    throw new ApiError(data?.message ?? `Request failed (${response.status})`, response.status)
  }
  return data as T
}

function query(params: Record<string, string | number | undefined>) {
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== '')
  return entries.length ? `?${new URLSearchParams(entries.map(([k, v]) => [k, String(v)]))}` : ''
}

export const api = {
  health: () => request<Health>('/api/health'),

  // Containers
  arrival: (container: ArrivalRequest) =>
    request<AllocationResult>('/api/containers/arrival', { method: 'POST', body: container }),
  accept: (allocationId: number) =>
    request<AcceptResult>(`/api/allocations/${allocationId}/accept`, { method: 'POST' }),
  override: (allocationId: number, zone: string, reason: string) =>
    request<OverrideResult>(`/api/allocations/${allocationId}/override`, { method: 'POST', body: { zone, reason } }),
  depart: (containerId: string) =>
    request<DepartResult>(`/api/containers/${encodeURIComponent(containerId)}/depart`, { method: 'POST' }),
  containers: (filters: ContainerFilters = {}) =>
    request<ContainerSearch>(`/api/containers${query({ ...filters })}`),
  container: (containerId: string) =>
    request<{ container: ContainerRecord }>(`/api/containers/${encodeURIComponent(containerId)}`),

  // Yard
  yardZones: () => request<YardZones>('/api/yard/zones'),
  dashboard: () => request<DashboardSummary>('/api/dashboard/summary'),
  alerts: () => request<AlertsResponse>('/api/alerts'),

  // Predictions and evaluation
  dwellForecast: (days = 7) => request<DwellForecast>(`/api/predict-dwell${query({ days })}`),
  occupancyForecast: (days = 14, capacity?: number) =>
    request<OccupancyForecast>(`/api/occupancy${query({ days, capacity })}`),
  reshuffling: () => request<ReshufflingStats>('/api/reshuffling-stats'),
  modelMetrics: () => request<ModelMetrics>('/api/models/metrics'),
}
