import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Circle, Polyline, Tooltip } from 'react-leaflet';
import L from 'leaflet';
import { 
  Navigation, 
  Wind, 
  Waves, 
  Compass, 
  Gauge, 
  Anchor, 
  AlertTriangle, 
  CheckCircle2, 
  Info,
  Clock,
  ArrowRight
} from 'lucide-react';
import { FALLBACK_FLEET, predictVesselEta } from '../services/api';

// Reference Port of Colombo coordinates
const PORT_COLOMBO = [6.9480, 79.8450];

// Custom Leaflet SVG Ship Marker Generator
const createShipIcon = (status, heading = 0) => {
  let color = '#10b981'; // Feasible / Nominal (Emerald)
  let glow = 'rgba(16, 185, 129, 0.4)';
  if (status === 'Conditionally Feasible') {
    color = '#f59e0b'; // Amber
    glow = 'rgba(245, 158, 11, 0.4)';
  } else if (status === 'Infeasible' || status === 'CRITICAL' || status === 'HIGH') {
    color = '#f43f5e'; // Crimson
    glow = 'rgba(244, 63, 94, 0.4)';
  }

  const svgHtml = `
    <div style="transform: rotate(${heading}deg); width: 36px; height: 36px; display: flex; align-items: center; justify-content: center; filter: drop-shadow(0 0 6px ${glow});">
      <svg width="28" height="28" viewBox="0 0 24 24" fill="${color}" stroke="#020617" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
        <polygon points="12 2 19 21 12 17 5 21 12 2" />
      </svg>
    </div>
  `;

  return L.divIcon({
    html: svgHtml,
    className: 'custom-ship-marker',
    iconSize: [36, 36],
    iconAnchor: [18, 18],
    popupAnchor: [0, -18],
  });
};

// Port of Colombo Icon
const portIcon = L.divIcon({
  html: `
    <div style="background: #0284c7; width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; border: 2px solid #38bdf8; box-shadow: 0 0 15px rgba(56, 189, 248, 0.6);">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="5" r="3"></circle>
        <line x1="12" y1="22" x2="12" y2="8"></line>
        <path d="M5 12H2a10 10 0 0 0 20 0h-3"></path>
      </svg>
    </div>
  `,
  className: 'port-marker-icon',
  iconSize: [32, 32],
  iconAnchor: [16, 16],
  popupAnchor: [0, -16]
});

export default function VesselTrackingMap({ onSelectVessel }) {
  const [fleet, setFleet] = useState(FALLBACK_FLEET);
  const [selectedVessel, setSelectedVessel] = useState(FALLBACK_FLEET[0]);
  const [etaDetails, setEtaDetails] = useState(null);
  const [loadingEta, setLoadingEta] = useState(false);

  // Fetch prediction details for selected vessel
  useEffect(() => {
    if (!selectedVessel) return;
    let isMounted = true;
    setLoadingEta(true);

    predictVesselEta(selectedVessel, false)
      .then((data) => {
        if (isMounted) {
          setEtaDetails(data);
          setLoadingEta(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setLoadingEta(false);
        }
      });

    return () => { isMounted = false; };
  }, [selectedVessel]);

  const handleVesselClick = (vessel) => {
    setSelectedVessel(vessel);
    if (onSelectVessel) {
      onSelectVessel(vessel);
    }
  };

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 380px', gap: '1.25rem', height: '680px' }}>
      {/* 1. Leaflet Interactive GIS Map Container */}
      <div className="panel-card" style={{ display: 'flex', flexDirection: 'column' }}>
        <div className="card-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <Navigation size={18} color="#38bdf8" />
            <h2 style={{ fontSize: '1rem', fontWeight: 600 }}>Real-Time GIS Vessel Tracking Matrix</h2>
            <span className="badge badge-ocean">Port of Colombo & Approaches</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', fontSize: '0.75rem' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <span className="pulse-dot online" /> Feasible
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <span className="pulse-dot warning" /> Conditionally Feasible
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <span className="pulse-dot danger" /> High Delay Risk / Infeasible
            </span>
          </div>
        </div>

        <div style={{ flex: 1, position: 'relative' }}>
          <MapContainer
            center={[6.88, 79.72]}
            zoom={9}
            scrollWheelZoom={true}
            style={{ width: '100%', height: '100%' }}
          >
            {/* Dark Matter CartoDB Basemap tiles */}
            <TileLayer
              attribution='&copy; <a href="https://carto.com/">CARTO</a>'
              url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            />

            {/* Port Colombo Operational Exclusion & Anchorage Outer Limit */}
            <Circle
              center={PORT_COLOMBO}
              radius={18520} // 10 Nautical miles
              pathOptions={{
                color: '#0284c7',
                fillColor: '#0284c7',
                fillOpacity: 0.05,
                weight: 1.5,
                dashArray: '4, 8'
              }}
            >
              <Tooltip sticky>Port of Colombo VTS Radar Coverage (10 nmi)</Tooltip>
            </Circle>

            {/* Port Centroid Marker */}
            <Marker position={PORT_COLOMBO} icon={portIcon}>
              <Popup>
                <div style={{ padding: '4px' }}>
                  <h4 style={{ fontWeight: 700, color: '#38bdf8', marginBottom: '4px' }}>Port of Colombo</h4>
                  <p style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                    Major transshipment hub. Terminals: JCT, CICT, SAGT, CWIT, ECT.
                  </p>
                  <div style={{ marginTop: '6px', fontSize: '0.75rem' }}>
                    <strong>Centroid:</strong> 06°56.88'N, 079°50.70'E
                  </div>
                </div>
              </Popup>
            </Marker>

            {/* Live Vessels Markers & Approaching Track Vectors */}
            {fleet.map((v) => {
              const isSelected = selectedVessel?.imo_number === v.imo_number;
              return (
                <React.Fragment key={v.imo_number}>
                  {/* Dashed Navigation Vector into Port */}
                  <Polyline
                    positions={[
                      [v.latitude, v.longitude],
                      PORT_COLOMBO
                    ]}
                    pathOptions={{
                      color: isSelected ? '#38bdf8' : 'rgba(255,255,255,0.15)',
                      weight: isSelected ? 2.5 : 1,
                      dashArray: isSelected ? '6, 6' : '3, 6'
                    }}
                  />

                  <Marker
                    position={[v.latitude, v.longitude]}
                    icon={createShipIcon(v.status, v.cog || 0)}
                    eventHandlers={{
                      click: () => handleVesselClick(v)
                    }}
                  >
                    <Popup>
                      <div style={{ minWidth: '220px', padding: '6px 2px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                          <h4 style={{ fontSize: '0.9rem', fontWeight: 700, color: '#f8fafc' }}>
                            {v.vessel_name}
                          </h4>
                          <span className={`badge ${
                            v.status === 'Feasible' ? 'badge-feasible' :
                            v.status === 'Conditionally Feasible' ? 'badge-conditionally' : 'badge-infeasible'
                          }`}>
                            {v.status}
                          </span>
                        </div>

                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px', fontSize: '0.78rem', color: '#cbd5e1' }}>
                          <div><strong>IMO:</strong> {v.imo_number}</div>
                          <div><strong>Type:</strong> {v.vessel_type}</div>
                          <div><strong>SOG:</strong> {v.sog} kts</div>
                          <div><strong>Draft:</strong> {v.draft_m} m</div>
                          <div><strong>Wind:</strong> {v.wind_speed_knots} kts</div>
                          <div><strong>Waves:</strong> {v.wave_height_m} m</div>
                        </div>

                        <div style={{ marginTop: '10px', paddingTop: '8px', borderTop: '1px solid rgba(255,255,255,0.1)' }}>
                          <button
                            onClick={() => handleVesselClick(v)}
                            className="btn-primary"
                            style={{ width: '100%', fontSize: '0.75rem', padding: '0.45rem' }}
                          >
                            Select for Dynamic Berth Match <ArrowRight size={14} />
                          </button>
                        </div>
                      </div>
                    </Popup>
                  </Marker>
                </React.Fragment>
              );
            })}
          </MapContainer>
        </div>
      </div>

      {/* 2. Vessel Telemetry & AI Diagnostic Inspector Sidebar */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', overflowY: 'auto' }}>
        {selectedVessel && (
          <div className="panel-card" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
            <div className="card-header">
              <div>
                <h3 style={{ fontSize: '0.95rem', fontWeight: 700, color: '#fff' }}>
                  {selectedVessel.vessel_name}
                </h3>
                <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                  IMO: {selectedVessel.imo_number} | MMSI: {selectedVessel.mmsi}
                </span>
              </div>
              <span className={`badge ${
                selectedVessel.status === 'Feasible' ? 'badge-feasible' :
                selectedVessel.status === 'Conditionally Feasible' ? 'badge-conditionally' : 'badge-infeasible'
              }`}>
                {selectedVessel.status}
              </span>
            </div>

            <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: '1rem', flex: 1 }}>
              {/* Telemetry Metrics Grid */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.65rem' }}>
                <div style={{ background: 'var(--bg-card-secondary)', padding: '0.65rem', borderRadius: '8px', border: '1px solid var(--border-secondary)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--text-muted)', fontSize: '0.72rem' }}>
                    <Gauge size={13} color="#38bdf8" /> Speed Over Ground
                  </div>
                  <div style={{ fontSize: '1.15rem', fontWeight: 700, color: '#f8fafc', marginTop: '2px' }}>
                    {selectedVessel.sog} <span style={{ fontSize: '0.75rem', fontWeight: 400 }}>knots</span>
                  </div>
                </div>

                <div style={{ background: 'var(--bg-card-secondary)', padding: '0.65rem', borderRadius: '8px', border: '1px solid var(--border-secondary)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--text-muted)', fontSize: '0.72rem' }}>
                    <Compass size={13} color="#38bdf8" /> Distance to Port
                  </div>
                  <div style={{ fontSize: '1.15rem', fontWeight: 700, color: '#f8fafc', marginTop: '2px' }}>
                    {selectedVessel.distance_to_port_nmi || 22.4} <span style={{ fontSize: '0.75rem', fontWeight: 400 }}>nmi</span>
                  </div>
                </div>

                <div style={{ background: 'var(--bg-card-secondary)', padding: '0.65rem', borderRadius: '8px', border: '1px solid var(--border-secondary)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--text-muted)', fontSize: '0.72rem' }}>
                    <Wind size={13} color="#06b6d4" /> Wind Velocity
                  </div>
                  <div style={{ fontSize: '1.15rem', fontWeight: 700, color: '#f8fafc', marginTop: '2px' }}>
                    {selectedVessel.wind_speed_knots} <span style={{ fontSize: '0.75rem', fontWeight: 400 }}>kts</span>
                  </div>
                </div>

                <div style={{ background: 'var(--bg-card-secondary)', padding: '0.65rem', borderRadius: '8px', border: '1px solid var(--border-secondary)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--text-muted)', fontSize: '0.72rem' }}>
                    <Waves size={13} color="#06b6d4" /> Wave Height
                  </div>
                  <div style={{ fontSize: '1.15rem', fontWeight: 700, color: '#f8fafc', marginTop: '2px' }}>
                    {selectedVessel.wave_height_m} <span style={{ fontSize: '0.75rem', fontWeight: 400 }}>m</span>
                  </div>
                </div>
              </div>

              {/* Dynamic ETA Prediction Inference */}
              <div style={{ background: 'rgba(2, 132, 199, 0.08)', padding: '0.85rem', borderRadius: '8px', border: '1px solid rgba(56, 189, 248, 0.25)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: '#38bdf8', fontSize: '0.78rem', fontWeight: 600, marginBottom: '6px' }}>
                  <Clock size={14} /> AI Continuous ETA Prediction
                </div>
                {loadingEta ? (
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Calculating hydrodynamic ETA...</div>
                ) : etaDetails ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem' }}>
                      <span style={{ color: 'var(--text-muted)' }}>Baseline Transit:</span>
                      <strong style={{ color: '#fff' }}>{etaDetails.eta_prediction.baseline_remaining_hours} hrs</strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem' }}>
                      <span style={{ color: 'var(--text-muted)' }}>Weather Drag Penalty:</span>
                      <strong style={{ color: '#f59e0b' }}>+{etaDetails.eta_prediction.weather_delay_hours} hrs</strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem', marginTop: '4px', paddingTop: '4px', borderTop: '1px solid rgba(255,255,255,0.1)' }}>
                      <span style={{ color: '#38bdf8', fontWeight: 600 }}>Dynamic ETA:</span>
                      <strong style={{ color: '#38bdf8' }}>
                        {new Date(etaDetails.eta_prediction.dynamic_eta).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', timeZoneName: 'short' })}
                      </strong>
                    </div>
                  </div>
                ) : (
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Telemetry nominal.</div>
                )}
              </div>

              {/* Operational Risk Diagnostic */}
              <div style={{ background: 'var(--bg-card-secondary)', padding: '0.85rem', borderRadius: '8px', border: '1px solid var(--border-secondary)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: '#cbd5e1', fontSize: '0.78rem', fontWeight: 600, marginBottom: '6px' }}>
                  <AlertTriangle size={14} color="#f59e0b" /> Berth Feasibility Diagnostic
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', lineHeight: '1.4' }}>
                  {selectedVessel.draft_m > 14.5 ? (
                    <span style={{ color: '#f59e0b' }}>
                      Deep draft vessel ({selectedVessel.draft_m}m). Strict assignment required for deep-water berths (e.g. CICT / SAGT).
                    </span>
                  ) : (
                    <span style={{ color: '#10b981' }}>
                      Nominal draft ({selectedVessel.draft_m}m). Compatible with all Colombo Container Terminals.
                    </span>
                  )}
                </div>
              </div>

              {/* Quick Action Button */}
              <button 
                onClick={() => handleVesselClick(selectedVessel)}
                className="btn-primary" 
                style={{ width: '100%', marginTop: 'auto' }}
              >
                Proceed to Berth Allocation <ArrowRight size={16} />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
