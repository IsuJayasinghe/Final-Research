// Response types of the yard API (backend/yard/app.py)
import type { ZoneName } from '../theme'

export type ContainerType = 'DRY' | 'REEFER' | 'HAZMAT' | 'OVERSIZED'
export type DwellClass = 'Short-stay' | 'Medium-stay' | 'Long-stay'
export type AllocationStatus = 'RECOMMENDED' | 'ACCEPTED' | 'OVERRIDDEN' | 'RELEASED' | 'CANCELLED'
export type ContainerStatus = 'Active' | 'Overstaying' | 'Released'

export interface Health {
  status: string
  component: string
  database: 'connected' | 'unavailable'
  containers_in_yard: number
  models_loaded: string[]
  endpoints: string[]
}

export interface ZoneOccupancy {
  used: number
  capacity: number
  utilization_pct: number
}

export interface ContainerRecord {
  allocation_id: number
  container_id: string
  container_type: ContainerType | null
  container_size: string | null
  cargo_type: string | null
  shipping_line: string | null
  recommended_zone: ZoneName | null
  zone: ZoneName | null
  block: string | null
  slot: string | null
  predicted_dwell_days: number | null
  dwell_class: DwellClass | null
  arrival: string | null
  predicted_departure: string | null
  released_at: string | null
  allocation_status: AllocationStatus
  status: ContainerStatus
  override_reason: string | null
  reason: string | null
  model_used: string | null
}

export interface ArrivalRequest {
  container_id: string
  container_type: ContainerType
  container_size?: string
  cargo_type?: string
  shipping_line?: string
  weight_category?: string
  customs_cleared?: number
  quarantine_flag?: number
  customs_red_lane?: number
  vessel_call_size?: number
  hours_since_berthing?: number
  dwell_days?: number
}

export interface Relocation {
  container_id: string
  new_slot: string
}

export interface AllocationResult {
  allocation_id: number
  container_id: string
  container_type: ContainerType
  predicted_dwell_days: number
  model_used: string
  dwell_class: DwellClass
  compatibility: { reefer: boolean; hazardous: boolean; oversized: boolean }
  recommended_zone: ZoneName
  block: string
  slot: string
  reason: string
  allocation_status: AllocationStatus
  relocated: Relocation[]
  zone_occupancy: ZoneOccupancy
}

export interface AcceptResult {
  allocation_id: number
  container_id: string
  allocation_status: 'ACCEPTED'
  block: string
  slot: string
}

export interface OverrideResult {
  allocation_id: number
  container_id: string
  allocation_status: 'OVERRIDDEN'
  zone: ZoneName
  block: string
  slot: string
  override_reason: string
  relocated: Relocation[]
  reshuffles: number
}

export interface DepartResult {
  container_id: string
  allocation_status: 'RELEASED'
  freed_slot: string
  reshuffles: number
  relocated: Relocation[]
}

export interface ContainerSearch {
  total: number
  page: number
  limit: number
  containers: ContainerRecord[]
  counts: { active: number; overstaying: number }
}

export interface ContainerFilters {
  search?: string
  type?: string
  zone?: string
  status?: string
  page?: number
  limit?: number
}

export interface ZoneSummary extends ZoneOccupancy {
  zone: ZoneName
  description: string
}

export interface BlockSummary extends ZoneOccupancy {
  block: string
  zone: ZoneName
  stacks: number
  tier_height: number
  stack_heights: number[]
}

export interface YardZones {
  zones: ZoneSummary[]
  blocks: BlockSummary[]
  total: ZoneOccupancy
}

export interface Alert {
  type: 'zone_capacity' | 'forecast_capacity'
  message: string
  utilization_pct: number
  zone?: ZoneName
  date?: string
  day_ahead?: number
}

export interface DashboardSummary {
  total_containers: number
  yard_occupancy_pct: number
  arrived_today: number
  departed_today: number
  expected_departures_today: number
  overstaying: number
  zone_occupancy: ZoneSummary[]
  recent_allocations: ContainerRecord[]
  alerts: Alert[]
}

export interface ErrorMetrics {
  rmse: number
  mae: number
  mape: number
}

export interface DwellModelMetrics {
  holdout: ErrorMetrics
  rolling_7d: ErrorMetrics
  [key: string]: unknown
}

export interface DwellPoint {
  date: string
  day_ahead: number
  predicted_dwell_days: number
}

export interface DwellForecast {
  prophet_predictions: DwellPoint[]
  arima_predictions: DwellPoint[]
  model_comparison: {
    recommended: 'Prophet' | 'ARIMA'
    reason: string
    prophet: DwellModelMetrics
    arima: DwellModelMetrics
  }
  note: string
}

export interface OccupancyPoint {
  date: string
  day_ahead: number
  predicted_containers: number
  planned_arrivals: number
  utilization_pct: number
  capacity_alert: boolean
}

export interface OccupancyForecast {
  model: string
  capacity: number
  metrics: { r2: number; rmse: number; mae: number; mape: number }
  horizon_mape: Record<string, number>
  features_used: string[]
  predictions: OccupancyPoint[]
  alerts: Alert[]
}

export interface AlertsResponse {
  threshold_pct: number
  alerts: Alert[]
}

export interface ReshufflingStats {
  simulation_results: {
    containers_simulated: number
    runs: number
    reshuffles_random: number
    reshuffles_ai: number
    reshuffles_saved: number
    reshuffle_reduction_pct: number
    perfect_knowledge_reduction_pct: number
    retrievals_without_reshuffle_pct: { random: number; ai: number }
    type_violations: { random: number; ai: number }
  }
  method: string
  conclusion: string
}

export interface ModelMetrics {
  metrics: {
    dwell_time: {
      arima: DwellModelMetrics
      prophet: DwellModelMetrics
      best_model: string
      mae_difference_pct: number
    }
    per_container_dwell: { mae: number; rmse: number; r2: number; baseline_mae: number; features: string[] }
    occupancy: {
      model: string
      features: string[]
      next_day: { r2: number; rmse: number; mae: number; mape: number }
      horizon_mape: Record<string, number>
    }
    zone_engine?: { zone_match_pct: number; always_fast_access_pct: number }
    data: { containers: number; window_start: string; window_end: string }
  }
}
