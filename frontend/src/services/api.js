import axios from 'axios';

// FastAPI Backend Base URL
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Fallback baseline fleet for GIS map visualization if backend is initializing
export const FALLBACK_FLEET = [
  {
    mmsi: 409321483,
    imo_number: 9321483,
    vessel_name: 'EMMA MAERSK',
    vessel_type: 'Container Ship',
    latitude: 6.6878,
    longitude: 79.6253,
    sog: 18.6,
    cog: 195.4,
    distance_to_port_nmi: 22.4,
    draft_m: 14.9,
    length_m: 397.0,
    wind_speed_knots: 24.5,
    wave_height_m: 2.8,
    status: 'Conditionally Feasible',
    risk_level: 'MODERATE'
  },
  {
    mmsi: 408420804,
    imo_number: 8420804,
    vessel_name: 'BERGE STAHL',
    vessel_type: 'Bulk Carrier',
    latitude: 6.9784,
    longitude: 80.0077,
    sog: 17.5,
    cog: 177.8,
    distance_to_port_nmi: 14.8,
    draft_m: 12.8,
    length_m: 342.0,
    wind_speed_knots: 14.2,
    wave_height_m: 1.2,
    status: 'Feasible',
    risk_level: 'LOW'
  },
  {
    mmsi: 409690121,
    imo_number: 9690121,
    vessel_name: 'VALIANT',
    vessel_type: 'Bulk Carrier',
    latitude: 6.1179,
    longitude: 79.4989,
    sog: 9.8,
    cog: 305.1,
    distance_to_port_nmi: 58.2,
    draft_m: 13.5,
    length_m: 292.0,
    wind_speed_knots: 29.4,
    wave_height_m: 3.2,
    status: 'Infeasible',
    risk_level: 'CRITICAL'
  },
  {
    mmsi: 409839179,
    imo_number: 9839179,
    vessel_name: 'CMA CGM JACQUES SAADE',
    vessel_type: 'Container Ship',
    latitude: 6.8200,
    longitude: 79.7100,
    sog: 19.2,
    cog: 210.0,
    distance_to_port_nmi: 11.5,
    draft_m: 15.6,
    length_m: 400.0,
    wind_speed_knots: 18.0,
    wave_height_m: 1.8,
    status: 'Conditionally Feasible',
    risk_level: 'MODERATE'
  },
  {
    mmsi: 409776171,
    imo_number: 9776171,
    vessel_name: 'OOCL HONG KONG',
    vessel_type: 'Container Ship',
    latitude: 7.2100,
    longitude: 79.5500,
    sog: 16.4,
    cog: 160.0,
    distance_to_port_nmi: 32.0,
    draft_m: 14.2,
    length_m: 399.9,
    wind_speed_knots: 11.0,
    wave_height_m: 0.9,
    status: 'Feasible',
    risk_level: 'LOW'
  }
];

// 1. Health & Status
export const checkHealth = async () => {
  try {
    const res = await apiClient.get('/health');
    return res.data;
  } catch (err) {
    return { status: 'offline', error: err.message, database_connected: false };
  }
};

// 2. Berths Endpoints
export const getBerthsList = async () => {
  const res = await apiClient.get('/berths');
  return res.data;
};

export const getBerthMatrix = async () => {
  const res = await apiClient.get('/berths/matrix');
  return res.data;
};

export const getBerthDetail = async (berthId) => {
  const res = await apiClient.get(`/berths/${encodeURIComponent(berthId)}`);
  return res.data;
};

export const getAvailableBerths = async ({ length_m, draft_m, start_time, end_time, terminal_name }) => {
  const params = { length_m, draft_m, start_time, end_time };
  if (terminal_name) params.terminal_name = terminal_name;
  const res = await apiClient.get('/berths/available', { params });
  return res.data;
};

export const bookBerth = async (bookingData) => {
  const res = await apiClient.post('/berths/book', bookingData);
  return res.data;
};

export const cancelAndReassignBerth = async (payload) => {
  const res = await apiClient.post('/berths/cancel-reassign', payload);
  return res.data;
};

export const getBookings = async (filters = {}) => {
  const res = await apiClient.get('/berths/bookings', { params: filters });
  return res.data;
};

// 3. Vessel ML Inference & Telemetry Endpoints
export const predictVesselEta = async (telemetryPayload, autoTriggerReassignment = false) => {
  const res = await apiClient.post('/vessels/predict-eta', telemetryPayload, {
    params: { auto_trigger_reassignment: autoTriggerReassignment }
  });
  return res.data;
};

export const assessDelayRisk = async (telemetryPayload) => {
  const res = await apiClient.post('/vessels/assess-delay-risk', telemetryPayload);
  return res.data;
};

export const getSampleTelemetry = async () => {
  try {
    const res = await apiClient.get('/vessels/sample');
    return res.data;
  } catch (e) {
    return FALLBACK_FLEET[0];
  }
};

export default apiClient;
