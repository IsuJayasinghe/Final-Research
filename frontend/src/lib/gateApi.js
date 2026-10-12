const API_BASE_URL = 'http://localhost:8000'

async function postJson(path, body) {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`${path} failed with ${res.status}`)
  return res.json()
}

async function getJson(path) {
  const res = await fetch(`${API_BASE_URL}${path}`)
  if (!res.ok) throw new Error(`${path} failed with ${res.status}`)
  return res.json()
}

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

export function getCongestion() {
  return getJson('/api/congestion')
}
