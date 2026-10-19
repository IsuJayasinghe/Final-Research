import React, { useState, useEffect } from 'react';
import { 
  Anchor, 
  CheckCircle2, 
  AlertCircle, 
  Ship, 
  Calendar, 
  Layers, 
  Filter, 
  Search, 
  Check, 
  X, 
  Clock, 
  Sparkles,
  ShieldCheck,
  Building2
} from 'lucide-react';
import { 
  getAvailableBerths, 
  bookBerth, 
  getBerthMatrix, 
  getBookings 
} from '../services/api';

export default function BerthAllocationPanel({ initialVessel, onBookingSuccess }) {
  // Input form states
  const [vesselName, setVesselName] = useState(initialVessel?.vessel_name || 'EMMA MAERSK');
  const [vesselImo, setVesselImo] = useState(initialVessel?.imo_number || 9321483);
  const [lengthM, setLengthM] = useState(initialVessel?.length_m || 397.0);
  const [draftM, setDraftM] = useState(initialVessel?.draft_m || 14.9);
  
  // Schedule window defaults: start 4 hours from now, duration 12 hours
  const now = new Date();
  const defaultStart = new Date(now.getTime() + 4 * 3600 * 1000).toISOString().slice(0, 16);
  const defaultEnd = new Date(now.getTime() + 16 * 3600 * 1000).toISOString().slice(0, 16);

  const [startTime, setStartTime] = useState(defaultStart);
  const [endTime, setEndTime] = useState(defaultEnd);
  const [terminalFilter, setTerminalFilter] = useState('');

  // Results & status states
  const [availableBerths, setAvailableBerths] = useState([]);
  const [berthMatrix, setBerthMatrix] = useState(null);
  const [selectedBerth, setSelectedBerth] = useState(null);
  const [loading, setLoading] = useState(false);
  const [bookingInProgress, setBookingInProgress] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [activeTab, setActiveTab] = useState('wizard'); // 'wizard' | 'matrix'

  // Update form if initialVessel changes
  useEffect(() => {
    if (initialVessel) {
      setVesselName(initialVessel.vessel_name || '');
      setVesselImo(initialVessel.imo_number || '');
      setLengthM(initialVessel.length_m || 300);
      setDraftM(initialVessel.draft_m || 12);
    }
  }, [initialVessel]);

  // Load initial available berths and terminal matrix
  useEffect(() => {
    handleSearchAvailableBerths();
    loadMatrix();
  }, []);

  const loadMatrix = async () => {
    try {
      const data = await getBerthMatrix();
      setBerthMatrix(data);
    } catch (err) {
      console.warn('Matrix loading note:', err);
    }
  };

  const handleSearchAvailableBerths = async (e) => {
    if (e) e.preventDefault();
    setErrorMsg('');
    setSuccessMsg('');
    setLoading(true);

    try {
      const formattedStart = new Date(startTime).toISOString();
      const formattedEnd = new Date(endTime).toISOString();

      const res = await getAvailableBerths({
        length_m: parseFloat(lengthM),
        draft_m: parseFloat(draftM),
        start_time: formattedStart,
        end_time: formattedEnd,
        terminal_name: terminalFilter || undefined
      });

      setAvailableBerths(res.available_berths || []);
      if (res.available_berths?.length > 0) {
        setSelectedBerth(res.available_berths[0]);
      } else {
        setSelectedBerth(null);
      }
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || err.message || 'Error querying available berths.');
      setAvailableBerths([]);
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmBooking = async () => {
    if (!selectedBerth) return;
    setBookingInProgress(true);
    setErrorMsg('');
    setSuccessMsg('');

    try {
      const formattedStart = new Date(startTime).toISOString();
      const formattedEnd = new Date(endTime).toISOString();

      const bookingPayload = {
        vessel_imo: parseInt(vesselImo),
        vessel_name: vesselName,
        berth_id: selectedBerth.berth_id,
        start_time: formattedStart,
        end_time: formattedEnd,
        length_m: parseFloat(lengthM),
        draft_m: parseFloat(draftM)
      };

      const result = await bookBerth(bookingPayload);
      setSuccessMsg(`Berth ${selectedBerth.berth_id} (${selectedBerth.terminal_name}) successfully confirmed for ${vesselName}! Booking ID: ${result.booking?.booking_id}`);
      
      // Refresh matrix and search
      loadMatrix();
      handleSearchAvailableBerths();

      if (onBookingSuccess) {
        onBookingSuccess(result.booking);
      }
    } catch (err) {
      const detail = err.response?.data?.detail || err.message;
      setErrorMsg(`Booking Collision / Constraint Violation: ${detail}`);
    } finally {
      setBookingInProgress(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* View Switcher Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button
            onClick={() => setActiveTab('wizard')}
            className={activeTab === 'wizard' ? 'btn-primary' : 'btn-secondary'}
            style={{ fontSize: '0.85rem' }}
          >
            <Sparkles size={16} /> Intelligent Berth Matching Wizard
          </button>
          <button
            onClick={() => { setActiveTab('matrix'); loadMatrix(); }}
            className={activeTab === 'matrix' ? 'btn-primary' : 'btn-secondary'}
            style={{ fontSize: '0.85rem' }}
          >
            <Layers size={16} /> Terminal Berth Matrix & Occupancy Grid
          </button>
        </div>

        {berthMatrix && (
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'flex', gap: '1rem' }}>
            <span>Total Port Berths: <strong style={{ color: '#fff' }}>{berthMatrix.total_berths}</strong></span>
            <span>Active Reservations: <strong style={{ color: '#38bdf8' }}>{berthMatrix.total_occupied_slots}</strong></span>
          </div>
        )}
      </div>

      {/* Alerts */}
      {errorMsg && (
        <div style={{ background: 'var(--rose-bg)', border: '1px solid var(--rose-danger)', padding: '0.85rem 1.25rem', borderRadius: '8px', color: '#fca5a5', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <AlertCircle size={18} color="#f43f5e" />
          <span>{errorMsg}</span>
        </div>
      )}

      {successMsg && (
        <div style={{ background: 'var(--emerald-bg)', border: '1px solid var(--emerald-success)', padding: '0.85rem 1.25rem', borderRadius: '8px', color: '#6ee7b7', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <CheckCircle2 size={18} color="#10b981" />
          <span>{successMsg}</span>
        </div>
      )}

      {activeTab === 'wizard' ? (
        <div style={{ display: 'grid', gridTemplateColumns: '360px 1fr', gap: '1.25rem' }}>
          {/* Form Controls */}
          <div className="panel-card">
            <div className="card-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Ship size={18} color="#38bdf8" />
                <h3 style={{ fontSize: '0.95rem', fontWeight: 600 }}>Vessel & Physical Constraints</h3>
              </div>
            </div>

            <form onSubmit={handleSearchAvailableBerths} className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: '0.9rem' }}>
              <div>
                <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                  Vessel Name
                </label>
                <input
                  type="text"
                  className="input-control"
                  value={vesselName}
                  onChange={(e) => setVesselName(e.target.value)}
                  required
                />
              </div>

              <div>
                <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                  IMO Number
                </label>
                <input
                  type="number"
                  className="input-control"
                  value={vesselImo}
                  onChange={(e) => setVesselImo(e.target.value)}
                  required
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                <div>
                  <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                    Length (meters)
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    className="input-control"
                    value={lengthM}
                    onChange={(e) => setLengthM(e.target.value)}
                    required
                  />
                </div>

                <div>
                  <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                    Draft (meters)
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    className="input-control"
                    value={draftM}
                    onChange={(e) => setDraftM(e.target.value)}
                    required
                  />
                </div>
              </div>

              <div>
                <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                  Target Arrival Window (Start)
                </label>
                <input
                  type="datetime-local"
                  className="input-control"
                  value={startTime}
                  onChange={(e) => setStartTime(e.target.value)}
                  required
                />
              </div>

              <div>
                <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                  Target Departure Window (End)
                </label>
                <input
                  type="datetime-local"
                  className="input-control"
                  value={endTime}
                  onChange={(e) => setEndTime(e.target.value)}
                  required
                />
              </div>

              <div>
                <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                  Terminal Filter (Optional)
                </label>
                <select
                  className="input-control"
                  value={terminalFilter}
                  onChange={(e) => setTerminalFilter(e.target.value)}
                >
                  <option value="">All Terminals (Colombo Port)</option>
                  <option value="CICT">Colombo International Container Terminal (CICT)</option>
                  <option value="JCT">Jaya Container Terminal (JCT)</option>
                  <option value="SAGT">South Asia Gateway Terminals (SAGT)</option>
                  <option value="CWIT">Colombo West International Terminal (CWIT)</option>
                  <option value="ECT">East Container Terminal (ECT)</option>
                </select>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="btn-primary"
                style={{ marginTop: '0.5rem' }}
              >
                <Search size={16} />
                {loading ? 'Evaluating Spatial Constraints...' : 'Find Qualified Berths'}
              </button>
            </form>
          </div>

          {/* Qualified Berths Selection Matrix */}
          <div className="panel-card" style={{ display: 'flex', flexDirection: 'column' }}>
            <div className="card-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <ShieldCheck size={18} color="#10b981" />
                <h3 style={{ fontSize: '0.95rem', fontWeight: 600 }}>
                  Qualified Berths Matching Physical & Temporal Constraints ({availableBerths.length})
                </h3>
              </div>
              {selectedBerth && (
                <button
                  onClick={handleConfirmBooking}
                  disabled={bookingInProgress}
                  className="btn-primary"
                  style={{ background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)' }}
                >
                  <Check size={16} />
                  {bookingInProgress ? 'Securing Allocation...' : `Confirm Reservation: ${selectedBerth.berth_id}`}
                </button>
              )}
            </div>

            <div className="card-body" style={{ flex: 1, overflowY: 'auto' }}>
              {availableBerths.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '3rem 1rem', color: 'var(--text-muted)' }}>
                  <Anchor size={48} color="#64748b" style={{ margin: '0 auto 1rem auto', opacity: 0.5 }} />
                  <p style={{ fontWeight: 600, color: '#f8fafc' }}>No Available Berths Match These Parameters</p>
                  <p style={{ fontSize: '0.8rem', marginTop: '4px' }}>
                    Vessel length ({lengthM}m) or draft ({draftM}m) exceeds available terminals, or time window is double-booked.
                  </p>
                </div>
              ) : (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '1rem' }}>
                  {availableBerths.map((berth) => {
                    const isSelected = selectedBerth?.berth_id === berth.berth_id;
                    return (
                      <div
                        key={berth.berth_id}
                        onClick={() => setSelectedBerth(berth)}
                        style={{
                          background: isSelected ? 'rgba(2, 132, 199, 0.15)' : 'var(--bg-card-secondary)',
                          border: isSelected ? '2px solid #38bdf8' : '1px solid var(--border-secondary)',
                          borderRadius: '10px',
                          padding: '1rem',
                          cursor: 'pointer',
                          transition: 'all 0.2s ease',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '0.65rem'
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <span style={{ fontSize: '1.1rem', fontWeight: 700, color: '#f8fafc' }}>
                            {berth.berth_id}
                          </span>
                          <span className="badge badge-feasible">Available</span>
                        </div>

                        <div style={{ fontSize: '0.78rem', color: 'var(--ocean-cyan)', fontWeight: 500 }}>
                          {berth.terminal_name}
                        </div>

                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px', fontSize: '0.75rem', color: 'var(--text-muted)', paddingTop: '6px', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
                          <div>Max Draft: <strong style={{ color: '#fff' }}>{berth.max_draft_m}m</strong></div>
                          <div>Draft Clearance: <strong style={{ color: '#10b981' }}>+{berth.draft_clearance_m}m</strong></div>
                          <div>Max Length: <strong style={{ color: '#fff' }}>{berth.max_length_m}m</strong></div>
                          <div>Length Clearance: <strong style={{ color: '#10b981' }}>+{berth.length_clearance_m}m</strong></div>
                          <div>Cranes: <strong style={{ color: '#fff' }}>{berth.crane_count} units</strong></div>
                          <div>Handling: <strong style={{ color: '#fff' }}>{berth.crane_handling_rate_teu_hr} TEU/h</strong></div>
                        </div>

                        {isSelected && (
                          <div style={{ marginTop: 'auto', paddingTop: '6px', textAlign: 'center', fontSize: '0.75rem', color: '#38bdf8', fontWeight: 600 }}>
                            ✓ Selected for Immediate Allocation
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      ) : (
        /* Terminal Matrix & Occupancy Grid View */
        <div className="panel-card">
          <div className="card-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Building2 size={18} color="#38bdf8" />
              <h3 style={{ fontSize: '0.95rem', fontWeight: 600 }}>
                Port of Colombo Operational Matrix Grid
              </h3>
            </div>
            <button onClick={loadMatrix} className="btn-secondary" style={{ fontSize: '0.75rem' }}>
              Refresh Matrix
            </button>
          </div>

          <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            {berthMatrix?.terminal_matrix && Object.entries(berthMatrix.terminal_matrix).map(([terminalName, berths]) => (
              <div key={terminalName} style={{ background: 'var(--bg-card-secondary)', borderRadius: '10px', padding: '1rem', border: '1px solid var(--border-secondary)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                  <h4 style={{ fontSize: '0.9rem', fontWeight: 700, color: '#38bdf8' }}>
                    {terminalName}
                  </h4>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    {berths.length} Berths Assigned
                  </span>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '0.75rem' }}>
                  {berths.map((b) => (
                    <div
                      key={b.berth_id}
                      style={{
                        background: b.is_occupied ? 'rgba(244, 63, 94, 0.08)' : 'rgba(16, 185, 129, 0.08)',
                        border: b.is_occupied ? '1px solid rgba(244, 63, 94, 0.3)' : '1px solid rgba(16, 185, 129, 0.3)',
                        borderRadius: '8px',
                        padding: '0.75rem'
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontWeight: 700, color: '#f8fafc', fontSize: '0.85rem' }}>
                          {b.berth_id}
                        </span>
                        <span className={`badge ${b.is_occupied ? 'badge-infeasible' : 'badge-feasible'}`} style={{ fontSize: '0.65rem' }}>
                          {b.is_occupied ? 'OCCUPIED' : 'FREE'}
                        </span>
                      </div>

                      <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                        Length: {b.max_length_m}m | Draft: {b.max_draft_m}m
                      </div>

                      {b.current_booking && (
                        <div style={{ marginTop: '6px', paddingTop: '6px', borderTop: '1px solid rgba(255,255,255,0.06)', fontSize: '0.72rem' }}>
                          <div style={{ color: '#f8fafc', fontWeight: 600 }}>
                            {b.current_booking.vessel_name}
                          </div>
                          <div style={{ color: 'var(--text-dim)', fontSize: '0.68rem' }}>
                            Until {new Date(b.current_booking.end_time).toLocaleDateString([], { month: 'short', day: 'numeric', hour: '2-digit' })}
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
