import React, { useState, useEffect } from 'react';
import { 
  RefreshCw, 
  AlertTriangle, 
  Wind, 
  Waves, 
  Gauge, 
  ArrowRight, 
  Clock, 
  CheckCircle2, 
  Calendar, 
  Sliders, 
  Activity,
  History,
  ShieldAlert,
  Send
} from 'lucide-react';
import { 
  predictVesselEta, 
  assessDelayRisk, 
  cancelAndReassignBerth, 
  getBookings 
} from '../services/api';

export default function DynamicRescheduling({ onAuditAction }) {
  // Environmental simulation parameters
  const [selectedImo, setSelectedImo] = useState(9321483);
  const [vesselName, setVesselName] = useState('EMMA MAERSK');
  const [draftM, setDraftM] = useState(14.9);
  const [sog, setSog] = useState(9.5); // Slowdown
  const [windSpeed, setWindSpeed] = useState(32.0); // Severe storm
  const [waveHeight, setWaveHeight] = useState(3.4); // Rough waves
  const [distanceToPort, setDistanceToPort] = useState(48.0);

  // Dynamic analysis results
  const [riskAssessment, setRiskAssessment] = useState(null);
  const [dynamicPrediction, setDynamicPrediction] = useState(null);
  const [evaluating, setEvaluating] = useState(false);
  const [reassigning, setReassigning] = useState(false);
  
  // Reallocation audit logs & active bookings
  const [bookingsList, setBookingsList] = useState([]);
  const [auditEvents, setAuditEvents] = useState([]);
  const [feedback, setFeedback] = useState(null);

  useEffect(() => {
    loadBookings();
    runRiskEvaluation();
  }, []);

  const loadBookings = async () => {
    try {
      const res = await getBookings();
      setBookingsList(res.bookings || []);
    } catch (err) {
      console.warn('Could not load bookings:', err);
    }
  };

  const runRiskEvaluation = async () => {
    setEvaluating(true);
    setFeedback(null);
    try {
      const payload = {
        imo_number: parseInt(selectedImo),
        vessel_name: vesselName,
        latitude: 6.6878,
        longitude: 79.6253,
        sog: parseFloat(sog),
        draft_m: parseFloat(draftM),
        wind_speed_knots: parseFloat(windSpeed),
        wave_height_m: parseFloat(waveHeight),
        distance_to_port_nmi: parseFloat(distanceToPort)
      };

      const [riskRes, etaRes] = await Promise.all([
        assessDelayRisk(payload),
        predictVesselEta(payload, false)
      ]);

      setRiskAssessment(riskRes);
      setDynamicPrediction(etaRes);
    } catch (err) {
      console.error('Error during delay evaluation:', err);
    } finally {
      setEvaluating(false);
    }
  };

  const handleTriggerAutomatedReassignment = async () => {
    setReassigning(true);
    setFeedback(null);

    try {
      const payload = {
        imo_number: parseInt(selectedImo),
        vessel_name: vesselName,
        latitude: 6.6878,
        longitude: 79.6253,
        sog: parseFloat(sog),
        draft_m: parseFloat(draftM),
        wind_speed_knots: parseFloat(windSpeed),
        wave_height_m: parseFloat(waveHeight),
        distance_to_port_nmi: parseFloat(distanceToPort)
      };

      // Trigger automatic unbooking & reallocation in the backend engine
      const etaRes = await predictVesselEta(payload, true);
      setDynamicPrediction(etaRes);

      const reassignResult = etaRes.automated_reassignment;
      if (reassignResult) {
        const newEvent = {
          id: Date.now(),
          timestamp: new Date().toLocaleTimeString(),
          vessel_name: vesselName,
          old_berth: reassignResult.cancelled_booking?.old_berth_id || 'Previous Berth',
          new_berth: reassignResult.new_booking?.berth_id || 'Assigned Next Free',
          terminal: reassignResult.new_booking?.terminal_name || 'Terminal',
          new_window: reassignResult.new_booking?.start_time,
          delay_hours: reassignResult.delay_hours || etaRes.eta_prediction?.weather_delay_hours,
          reasons: riskAssessment?.trigger_reasons || ['Severe meteo-oceanographic drift']
        };

        setAuditEvents((prev) => [newEvent, ...prev]);
        setFeedback({
          type: 'success',
          message: `Autonomous Reallocation Executed: Released ${newEvent.old_berth} and confirmed slot ${newEvent.new_berth} (${newEvent.terminal}).`
        });
      } else {
        // Fallback explicit cancel-reassign call if not booked
        const fallbackCall = await cancelAndReassignBerth({
          vessel_imo: parseInt(selectedImo),
          new_eta: etaRes.eta_prediction?.dynamic_eta || new Date(Date.now() + 6 * 3600000).toISOString(),
          auto_reassign: true,
          draft_m: parseFloat(draftM)
        });

        const newEvent = {
          id: Date.now(),
          timestamp: new Date().toLocaleTimeString(),
          vessel_name: vesselName,
          old_berth: fallbackCall.cancelled_booking?.old_berth_id,
          new_berth: fallbackCall.new_booking?.berth_id,
          terminal: fallbackCall.new_booking?.terminal_name,
          delay_hours: fallbackCall.delay_hours,
          reasons: ['Dynamic schedule drift past allocated operational slot']
        };

        setAuditEvents((prev) => [newEvent, ...prev]);
        setFeedback({
          type: 'success',
          message: `Autonomous Reallocation: Slot ${newEvent.old_berth} freed, reassigned to ${newEvent.new_berth}.`
        });
      }

      loadBookings();
      if (onAuditAction) onAuditAction();
    } catch (err) {
      const msg = err.response?.data?.detail || err.message;
      setFeedback({ type: 'error', message: `Autonomous Reallocation Note: ${msg}` });
    } finally {
      setReassigning(false);
    }
  };

  return (
    <div className="rescheduling-grid">
      {/* 1. Environmental Drift & Telemetry Variation Simulator */}
      <div className="panel-card" style={{ display: 'flex', flexDirection: 'column' }}>
        <div className="card-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Sliders size={18} color="#38bdf8" />
            <h3 style={{ fontSize: '0.95rem', fontWeight: 600 }}>Environmental Drift Simulator</h3>
          </div>
          <span className="badge badge-ocean">AIS Drift Injector</span>
        </div>

        <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div>
            <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
              Select Vessel IMO Under Surveillance
            </label>
            <select
              className="input-control"
              value={selectedImo}
              onChange={(e) => {
                setSelectedImo(e.target.value);
                const b = bookingsList.find(item => item.vessel_imo === parseInt(e.target.value));
                if (b) setVesselName(b.vessel_name);
              }}
            >
              <option value="9321483">IMO 9321483 - EMMA MAERSK</option>
              <option value="9839179">IMO 9839179 - CMA CGM JACQUES SAADE</option>
              <option value="9690121">IMO 9690121 - VALIANT</option>
              <option value="9776171">IMO 9776171 - OOCL HONG KONG</option>
            </select>
          </div>

          {/* Wind Speed Slider */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}><Wind size={13} color="#06b6d4" /> Wind Speed</span>
              <strong style={{ color: windSpeed >= 28 ? '#f43f5e' : windSpeed >= 20 ? '#f59e0b' : '#38bdf8' }}>{windSpeed} knots</strong>
            </div>
            <input
              type="range"
              min="5"
              max="45"
              step="1"
              value={windSpeed}
              onChange={(e) => setWindSpeed(parseFloat(e.target.value))}
              style={{ width: '100%', accentColor: '#0284c7' }}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.65rem', color: 'var(--text-dim)' }}>
              <span>Calm (5 kts)</span>
              <span>Gale Warning (28 kts)</span>
              <span>Severe (45 kts)</span>
            </div>
          </div>

          {/* Wave Height Slider */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}><Waves size={13} color="#06b6d4" /> Significant Wave Height</span>
              <strong style={{ color: waveHeight >= 3.0 ? '#f43f5e' : waveHeight >= 2.0 ? '#f59e0b' : '#38bdf8' }}>{waveHeight} meters</strong>
            </div>
            <input
              type="range"
              min="0.5"
              max="5.0"
              step="0.1"
              value={waveHeight}
              onChange={(e) => setWaveHeight(parseFloat(e.target.value))}
              style={{ width: '100%', accentColor: '#0284c7' }}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.65rem', color: 'var(--text-dim)' }}>
              <span>Calm (0.5m)</span>
              <span>Rough Sea (2.0m)</span>
              <span>Extreme (5.0m)</span>
            </div>
          </div>

          {/* SOG Speed Drop Slider */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}><Gauge size={13} color="#38bdf8" /> Speed Over Ground</span>
              <strong style={{ color: sog <= 10 ? '#f43f5e' : '#38bdf8' }}>{sog} knots</strong>
            </div>
            <input
              type="range"
              min="4.0"
              max="24.0"
              step="0.5"
              value={sog}
              onChange={(e) => setSog(parseFloat(e.target.value))}
              style={{ width: '100%', accentColor: '#0284c7' }}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.65rem', color: 'var(--text-dim)' }}>
              <span>Drifting / Heavy Drag (4 kts)</span>
              <span>Cruising (18 kts)</span>
            </div>
          </div>

          <button
            onClick={runRiskEvaluation}
            disabled={evaluating}
            className="btn-secondary"
            style={{ width: '100%', justifyContent: 'center' }}
          >
            <Activity size={16} /> {evaluating ? 'Re-evaluating Models...' : 'Run Dynamic ML Risk Evaluation'}
          </button>

          {/* Reassignment Trigger Button */}
          {riskAssessment && (
            <div style={{ marginTop: '0.5rem', paddingTop: '0.75rem', borderTop: '1px solid var(--border-secondary)' }}>
              <button
                onClick={handleTriggerAutomatedReassignment}
                disabled={reassigning}
                className={riskAssessment.trigger_reassignment ? 'btn-danger' : 'btn-primary'}
                style={{ width: '100%', padding: '0.75rem' }}
              >
                <RefreshCw size={16} className={reassigning ? 'spin-icon' : ''} />
                {reassigning ? 'Executing Autonomous Reassignment...' : 'Trigger Autonomous Unbooking & Reallocation'}
              </button>
            </div>
          )}
        </div>
      </div>

      {/* 2. Real-Time Delay Risk Diagnostics & Automated Reallocation Audit Feed */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
        {/* Risk Diagnostic Summary Card */}
        {riskAssessment && dynamicPrediction && (
          <div className="panel-card">
            <div className="card-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <ShieldAlert size={18} color={riskAssessment.risk_level === 'CRITICAL' ? '#f43f5e' : '#f59e0b'} />
                <h3 style={{ fontSize: '0.95rem', fontWeight: 600 }}>
                  Real-Time AI Schedule Violation & Reallocation Assessment
                </h3>
              </div>
              <span className={`badge ${
                riskAssessment.risk_level === 'LOW' ? 'badge-feasible' :
                riskAssessment.risk_level === 'MODERATE' ? 'badge-conditionally' : 'badge-infeasible'
              }`}>
                {riskAssessment.risk_level} DELAY RISK
              </span>
            </div>

            <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem' }}>
                <div style={{ background: 'var(--bg-card-secondary)', padding: '0.85rem', borderRadius: '8px', border: '1px solid var(--border-secondary)' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Delay Probability</div>
                  <div style={{ fontSize: '1.5rem', fontWeight: 700, color: riskAssessment.delay_probability >= 0.65 ? '#f43f5e' : '#10b981', marginTop: '2px' }}>
                    {riskAssessment.delay_probability_percent}%
                  </div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>
                    Trigger Threshold: &ge; 65%
                  </div>
                </div>

                <div style={{ background: 'var(--bg-card-secondary)', padding: '0.85rem', borderRadius: '8px', border: '1px solid var(--border-secondary)' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Dynamic Transit Hours</div>
                  <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#38bdf8', marginTop: '2px' }}>
                    {dynamicPrediction.eta_prediction.dynamic_remaining_hours} <span style={{ fontSize: '0.8rem', fontWeight: 400 }}>hrs</span>
                  </div>
                  <div style={{ fontSize: '0.7rem', color: '#f59e0b' }}>
                    Weather Penalty: +{dynamicPrediction.eta_prediction.weather_delay_hours} hrs
                  </div>
                </div>

                <div style={{ background: 'var(--bg-card-secondary)', padding: '0.85rem', borderRadius: '8px', border: '1px solid var(--border-secondary)' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Autonomous Action Policy</div>
                  <div style={{ fontSize: '1.05rem', fontWeight: 700, color: riskAssessment.trigger_reassignment ? '#f43f5e' : '#10b981', marginTop: '6px' }}>
                    {riskAssessment.trigger_reassignment ? 'UNBOOK & REASSIGN' : 'SCHEDULE NOMINAL'}
                  </div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>
                    Self-healing Berth Engine
                  </div>
                </div>
              </div>

              {/* Detected Triggers */}
              {riskAssessment.trigger_reasons?.length > 0 && (
                <div style={{ background: 'rgba(244, 63, 94, 0.08)', border: '1px solid rgba(244, 63, 94, 0.25)', borderRadius: '8px', padding: '0.85rem' }}>
                  <div style={{ fontSize: '0.78rem', fontWeight: 600, color: '#fca5a5', marginBottom: '4px' }}>
                    Trigger Conditions Detected:
                  </div>
                  <ul style={{ listStyleType: 'disc', paddingLeft: '1.25rem', fontSize: '0.75rem', color: '#f8fafc' }}>
                    {riskAssessment.trigger_reasons.map((r, i) => (
                      <li key={i}>{r}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Feedback Alert */}
        {feedback && (
          <div style={{ 
            background: feedback.type === 'success' ? 'var(--emerald-bg)' : 'var(--rose-bg)',
            border: `1px solid ${feedback.type === 'success' ? 'var(--emerald-success)' : 'var(--rose-danger)'}`,
            padding: '0.85rem 1.25rem',
            borderRadius: '8px',
            color: feedback.type === 'success' ? '#6ee7b7' : '#fca5a5',
            fontSize: '0.85rem'
          }}>
            {feedback.message}
          </div>
        )}

        {/* Automated Unbooking & Reallocation Audit Trail */}
        <div className="panel-card" style={{ flex: 1 }}>
          <div className="card-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <History size={18} color="#38bdf8" />
              <h3 style={{ fontSize: '0.95rem', fontWeight: 600 }}>
                Automated Berth Unbooking & Reallocation Audit Trail
              </h3>
            </div>
            <button onClick={loadBookings} className="btn-secondary" style={{ fontSize: '0.75rem' }}>
              Refresh Bookings Matrix
            </button>
          </div>

          <div className="card-body" style={{ maxHeight: '340px', overflowY: 'auto' }}>
            {auditEvents.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '2rem 1rem', color: 'var(--text-muted)' }}>
                <Clock size={36} color="#64748b" style={{ margin: '0 auto 0.75rem auto', opacity: 0.5 }} />
                <p style={{ fontWeight: 600, color: '#f8fafc' }}>No Reallocation Events Triggered Yet in Session</p>
                <p style={{ fontSize: '0.78rem', marginTop: '4px' }}>
                  Inject high wind/waves or speed degradation to simulate weather delays and observe automated slot unbooking.
                </p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {auditEvents.map((ev) => (
                  <div
                    key={ev.id}
                    style={{
                      background: 'var(--bg-card-secondary)',
                      borderLeft: '4px solid #f43f5e',
                      border: '1px solid var(--border-secondary)',
                      borderRadius: '8px',
                      padding: '0.85rem'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontWeight: 700, color: '#f8fafc', fontSize: '0.85rem' }}>
                        {ev.vessel_name} — Autonomous Reschedule Event
                      </span>
                      <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                        {ev.timestamp}
                      </span>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginTop: '6px', fontSize: '0.8rem' }}>
                      <span style={{ color: '#f43f5e', textDecoration: 'line-through' }}>
                        Slot {ev.old_berth} (UNBOOKED)
                      </span>
                      <ArrowRight size={14} color="#38bdf8" />
                      <span style={{ color: '#10b981', fontWeight: 600 }}>
                        Slot {ev.new_berth} ({ev.terminal}) (CONFIRMED)
                      </span>
                    </div>

                    <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', marginTop: '4px' }}>
                      Delay Overrun: +{ev.delay_hours} hrs | Policy: Automated Berth Unbooking & Dynamic Binding
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
