const API_BASE_URL = 'http://localhost:8000'

async function request(path, options) {
  const res = await fetch(`${API_BASE_URL}${path}`, options)
  if (!res.ok) {
    let detail = `${path} failed with ${res.status}`
    try {
      const body = await res.json()
      if (typeof body.detail === 'string') detail = body.detail
    } catch {
      // body was not JSON; keep the generic message
    }
    throw new Error(detail)
  }
  return res.json()
}

const postJson = (path, body) =>
  request(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body ?? {}),
  })

const getJson = (path) => request(path)

// Legacy single-shot assignment (no persistence, no no-show model).
export function requestAppointment(form) {
  return postJson('/api/assign-appointment', {
    truck_id: form.truckId,
    container_id: form.containerId,
    carrier: form.carrier,
    cargo_category: form.cargoCategory,
    container_type: form.containerType,
    customs_risk_flag: form.customsRiskFlag,
    carrier_reliability: Number(form.carrierReliability),
    missing_documents: Number(form.missingDocuments),
    arrival_date: form.preferredDate,
    arrival_hour: Number(form.arrivalHour),
  })
}

// Saved, no-show-aware booking: risk score, overbooking decision, lane, clearance time.
export function createAppointment(form) {
  return postJson('/api/appointments', {
    truck_id: form.truckId,
    container_id: form.containerId,
    carrier: form.carrier,
    cargo_category: form.cargoCategory,
    container_type: form.containerType,
    customs_risk_flag: form.customsRiskFlag,
    carrier_reliability: Number(form.carrierReliability),
    missing_documents: Number(form.missingDocuments),
    arrival_date: form.preferredDate,
    arrival_hour: Number(form.arrivalHour),
    weather_severity: Number(form.weatherSeverity),
    vessel_delay: Boolean(form.vesselDelay),
  })
}

export const listAppointments = () => getJson('/api/appointments')
export const getAppointmentEvents = (id) => getJson(`/api/appointments/${id}/events`)
export const confirmAppointment = (id) => postJson(`/api/appointments/${id}/confirm`)
export const cancelAppointment = (id) => postJson(`/api/appointments/${id}/cancel`)

export const getSlots = (date) => getJson(`/api/slots?date=${encodeURIComponent(date)}`)

export const reoptimize = ({ vesselDelayHours, queueSpikePct, windowHours, start }) =>
  postJson('/api/reoptimize', {
    vessel_delay_hours: Number(vesselDelayHours),
    queue_spike_pct: Number(queueSpikePct),
    window_hours: Number(windowHours),
    start: start || null,
  })

export const clearDisruption = () => request('/api/disruption', { method: 'DELETE' })

// OCR document check: the booking (if given) supplies the expected container / truck / date.
export function checkDocument({ file, docKey, appointmentId, containerId, truckId, containerType }) {
  const body = new FormData()
  body.append('file', file)
  body.append('doc_key', docKey)
  if (appointmentId) {
    body.append('appointment_id', appointmentId)
  } else {
    if (containerId) body.append('expected_container_id', containerId)
    if (truckId) body.append('expected_truck_id', truckId)
    if (containerType) body.append('container_type', containerType)
  }
  return request('/api/documents/check', { method: 'POST', body })
}

export const getAppointmentDocuments = (id) => getJson(`/api/appointments/${id}/documents`)
export const submitDocuments = (id) => postJson(`/api/appointments/${id}/documents/submit`)

export const getModelMetrics = () => getJson('/api/model-metrics')

export function getCongestion() {
  return getJson('/api/congestion')
}
