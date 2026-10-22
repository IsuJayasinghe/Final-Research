import React, { useState, useEffect, useMemo } from 'react';
import { 
  Building2, 
  RefreshCw, 
  CheckCircle2, 
  AlertCircle, 
  Clock, 
  Ship, 
  X, 
  AlertTriangle, 
  Filter, 
  Search, 
  Layers, 
  Anchor,
  XCircle,
  ShieldAlert
} from 'lucide-react';
import { getBerthMatrix, releaseBerth } from '../services/api';

export const formatOccupiedSchedule = (booking) => {
  if (!booking?.end_time) return 'Occupied (Active Reservation)';
  try {
    const end = new Date(booking.end_time);
    if (isNaN(end.getTime())) return `Occupied until ${booking.end_time}`;
    
    const month = end.toLocaleDateString('en-US', { month: 'short', timeZone: 'UTC' });
    const day = end.toLocaleDateString('en-US', { day: 'numeric', timeZone: 'UTC' });
    let hours = end.getUTCHours();
    const ampm = hours >= 12 ? 'PM' : 'AM';
    hours = hours % 12;
    hours = hours ? hours : 12;
    const strHours = hours < 10 ? `0${hours}` : `${hours}`;
    return `Occupied until ${month} ${day}, ${strHours} ${ampm}`;
  } catch (e) {
    return `Occupied until ${booking.end_time}`;
  }
};

export default function TerminalMatrix({ onBerthReleased }) {
  const [berthMatrix, setBerthMatrix] = useState(null);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [terminalFilter, setTerminalFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL'); // 'ALL' | 'FREE' | 'OCCUPIED'

  // Modal confirmation state for releasing a berth
  const [releaseModalData, setReleaseModalData] = useState(null);
  const [releasingInProgress, setReleasingInProgress] = useState(false);

  useEffect(() => {
    loadMatrix();
  }, []);

  const loadMatrix = async () => {
    setLoading(true);
    try {
      const data = await getBerthMatrix();
      setBerthMatrix(data);
    } catch (err) {
      setErrorMsg('Could not load terminal berth matrix. Please ensure backend is running.');
    } finally {
      setLoading(false);
    }
  };

  const handleOpenReleaseModal = (berth) => {
    setErrorMsg('');
    setSuccessMsg('');
    setReleaseModalData(berth);
  };

  const handleCloseReleaseModal = () => {
    if (!releasingInProgress) {
      setReleaseModalData(null);
    }
  };

  const handleConfirmRelease = async () => {
    if (!releaseModalData) return;
    setReleasingInProgress(true);
    setErrorMsg('');
    setSuccessMsg('');

    const berthId = releaseModalData.berth_id;
    const booking = releaseModalData.current_booking;
    const bookingId = booking?.booking_id;
    const vesselName = booking?.vessel_name || 'Assigned Vessel';

    try {
      const result = await releaseBerth({ berth_id: berthId, booking_id: bookingId });
      setSuccessMsg(
        result.message || 
        `Berth ${berthId} successfully released! Active reservation for '${vesselName}' has been cancelled.`
      );
      setReleaseModalData(null);

      // Immediately refresh matrix state so the berth turns green (FREE)
      await loadMatrix();

      if (onBerthReleased) {
        onBerthReleased(releaseModalData);
      }
    } catch (err) {
      const detail = err.response?.data?.detail || err.message;
      setErrorMsg(`Failed to release berth: ${detail}`);
    } finally {
      setReleasingInProgress(false);
    }
  };

  // Filtered terminals and berths
  const filteredTerminals = useMemo(() => {
    if (!berthMatrix?.terminal_matrix) return {};

    const filtered = {};
    Object.entries(berthMatrix.terminal_matrix).forEach(([termName, berths]) => {
      if (terminalFilter && !termName.toLowerCase().includes(terminalFilter.toLowerCase())) {
        return;
      }

      const matchingBerths = berths.filter((b) => {
        // Status filter
        if (statusFilter === 'FREE' && b.is_occupied) return false;
        if (statusFilter === 'OCCUPIED' && !b.is_occupied) return false;

        // Search query
        if (searchQuery.trim()) {
          const q = searchQuery.toLowerCase();
          const matchesId = b.berth_id.toLowerCase().includes(q);
          const matchesVessel = b.current_booking?.vessel_name?.toLowerCase().includes(q);
          const matchesImo = String(b.current_booking?.vessel_imo || '').includes(q);
          return matchesId || matchesVessel || matchesImo;
        }

        return true;
      });

      if (matchingBerths.length > 0) {
        filtered[termName] = matchingBerths;
      }
    });

    return filtered;
  }, [berthMatrix, terminalFilter, statusFilter, searchQuery]);

  const totalBerths = berthMatrix?.total_berths || 49;
  const totalOccupied = berthMatrix?.total_occupied_slots || 0;
  const totalFree = Math.max(0, totalBerths - totalOccupied);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Alerts */}
      {errorMsg && (
        <div style={{
          background: 'var(--rose-bg)',
          border: '1px solid var(--rose-danger)',
          padding: '0.85rem 1.25rem',
          borderRadius: '8px',
          color: '#fca5a5',
          fontSize: '0.85rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem'
        }}>
          <AlertCircle size={18} color="#f43f5e" />
          <span>{errorMsg}</span>
        </div>
      )}

      {successMsg && (
        <div style={{
          background: 'var(--emerald-bg)',
          border: '1px solid var(--emerald-success)',
          padding: '0.85rem 1.25rem',
          borderRadius: '8px',
          color: '#6ee7b7',
          fontSize: '0.85rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem'
        }}>
          <CheckCircle2 size={18} color="#10b981" />
          <span>{successMsg}</span>
        </div>
      )}

      {/* Main Terminal Matrix Panel */}
      <div className="panel-card">
        {/* Header & Live Operational Summary */}
        <div className="card-header" style={{ flexWrap: 'wrap', gap: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <Building2 size={20} color="#38bdf8" />
            <div>
              <h3 style={{ fontSize: '1rem', fontWeight: 700, margin: 0, color: '#f8fafc' }}>
                Terminal Berth Matrix & Occupancy Grid
              </h3>
              <p style={{ margin: 0, fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                Real-time Port of Colombo Physical Capacity, Berth Reservations & Active Occupancy
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            {/* Live Stats Indicators */}
            <div style={{ display: 'flex', gap: '0.75rem', fontSize: '0.78rem' }}>
              <span className="badge" style={{ background: 'rgba(2, 132, 199, 0.15)', color: '#38bdf8', border: '1px solid rgba(56, 189, 248, 0.3)' }}>
                Total: {totalBerths}
              </span>
              <span className="badge badge-feasible">
                ● Free: {totalFree}
              </span>
              <span className="badge badge-infeasible">
                ● Occupied: {totalOccupied}
              </span>
            </div>

            <button
              onClick={loadMatrix}
              disabled={loading}
              className="btn-secondary"
              style={{ fontSize: '0.78rem', padding: '0.4rem 0.85rem' }}
            >
              <RefreshCw size={14} className={loading ? 'spin' : ''} />
              {loading ? 'Syncing...' : 'Refresh Matrix'}
            </button>
          </div>
        </div>

        {/* Filter & Search Bar */}
        <div style={{
          background: 'rgba(12, 20, 43, 0.5)',
          borderBottom: '1px solid var(--border-secondary)',
          padding: '0.75rem 1.25rem',
          display: 'flex',
          flexWrap: 'wrap',
          gap: '0.75rem',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'center', flex: 1 }}>
            {/* Search input */}
            <div style={{ position: 'relative', minWidth: '220px' }}>
              <Search size={14} color="#64748b" style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)' }} />
              <input
                type="text"
                placeholder="Search berth ID or vessel..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="input-control"
                style={{ paddingLeft: '2rem', fontSize: '0.8rem', padding: '0.45rem 0.75rem 0.45rem 2rem' }}
              />
            </div>

            {/* Terminal dropdown */}
            <select
              value={terminalFilter}
              onChange={(e) => setTerminalFilter(e.target.value)}
              className="input-control"
              style={{ width: 'auto', minWidth: '180px', fontSize: '0.8rem', padding: '0.45rem 0.75rem' }}
            >
              <option value="">All Terminals</option>
              <option value="CICT">CICT (Container)</option>
              <option value="CWIT">CWIT (West Terminal)</option>
              <option value="ECT">ECT (East Terminal)</option>
              <option value="JCT">JCT (Jaya Terminal)</option>
              <option value="SAGT">SAGT (South Asia Gateway)</option>
              <option value="UCT">UCT (Unity Terminal)</option>
            </select>

            {/* Status pills */}
            <div style={{ display: 'flex', gap: '0.35rem', background: 'rgba(7, 13, 30, 0.8)', padding: '2px', borderRadius: '6px', border: '1px solid var(--border-secondary)' }}>
              {['ALL', 'FREE', 'OCCUPIED'].map((st) => (
                <button
                  key={st}
                  type="button"
                  onClick={() => setStatusFilter(st)}
                  style={{
                    background: statusFilter === st ? 'var(--ocean-cyan)' : 'transparent',
                    color: statusFilter === st ? '#070d1e' : 'var(--text-muted)',
                    border: 'none',
                    borderRadius: '4px',
                    padding: '0.3rem 0.65rem',
                    fontSize: '0.72rem',
                    fontWeight: 700,
                    cursor: 'pointer',
                    transition: 'all 0.15s ease'
                  }}
                >
                  {st}
                </button>
              ))}
            </div>
          </div>

          <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>
            Showing {Object.values(filteredTerminals).reduce((acc, bList) => acc + bList.length, 0)} Berths
          </span>
        </div>

        {/* Terminals & Berths Grid Body */}
        <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', maxHeight: '720px', overflowY: 'auto' }}>
          {Object.keys(filteredTerminals).length === 0 ? (
            <div style={{ textAlign: 'center', padding: '3rem 1rem', color: 'var(--text-muted)' }}>
              <Layers size={40} color="#64748b" style={{ margin: '0 auto 0.75rem auto', opacity: 0.5 }} />
              <p style={{ fontWeight: 600, color: '#f8fafc', fontSize: '0.9rem' }}>
                No Berths Match Filter Criteria
              </p>
              <p style={{ fontSize: '0.78rem', marginTop: '4px' }}>
                Try adjusting your search query, terminal selection, or status filter.
              </p>
            </div>
          ) : (
            Object.entries(filteredTerminals).map(([terminalName, berths]) => {
              const termOccupied = berths.filter(b => b.is_occupied).length;
              const termFree = berths.length - termOccupied;

              return (
                <div
                  key={terminalName}
                  style={{
                    background: 'var(--bg-card-secondary)',
                    borderRadius: '10px',
                    padding: '1.1rem',
                    border: '1px solid var(--border-secondary)'
                  }}
                >
                  {/* Terminal Header */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.85rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <h4 style={{ fontSize: '0.95rem', fontWeight: 700, color: '#38bdf8', margin: 0 }}>
                        {terminalName}
                      </h4>
                      <span className="badge badge-ocean" style={{ fontSize: '0.65rem' }}>
                        {berths.length} Berths
                      </span>
                    </div>

                    <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', display: 'flex', gap: '0.6rem' }}>
                      <span>Free: <strong style={{ color: '#10b981' }}>{termFree}</strong></span>
                      <span>|</span>
                      <span>Occupied: <strong style={{ color: '#f43f5e' }}>{termOccupied}</strong></span>
                    </div>
                  </div>

                  {/* Berths Cards Grid */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: '0.85rem' }}>
                    {berths.map((b) => {
                      const isOccupied = b.is_occupied;
                      const booking = b.current_booking;

                      return (
                        <div
                          key={b.berth_id}
                          style={{
                            background: isOccupied ? 'rgba(244, 63, 94, 0.06)' : 'rgba(16, 185, 129, 0.06)',
                            border: isOccupied ? '1px solid rgba(244, 63, 94, 0.35)' : '1px solid rgba(16, 185, 129, 0.35)',
                            borderRadius: '8px',
                            padding: '0.85rem',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '0.55rem',
                            position: 'relative',
                            transition: 'all 0.2s ease',
                            boxShadow: isOccupied ? '0 2px 8px rgba(244, 63, 94, 0.1)' : '0 2px 8px rgba(16, 185, 129, 0.1)'
                          }}
                        >
                          {/* Top Row: Berth ID & Live Badge */}
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span style={{ fontWeight: 800, color: '#f8fafc', fontSize: '0.95rem', letterSpacing: '-0.01em' }}>
                              {b.berth_id}
                            </span>
                            <span
                              className={`badge ${isOccupied ? 'badge-infeasible' : 'badge-feasible'}`}
                              style={{ fontSize: '0.65rem', padding: '0.15rem 0.5rem' }}
                            >
                              <span className={`pulse-dot ${isOccupied ? 'danger' : 'online'}`} style={{ width: '5px', height: '5px' }} />
                              {isOccupied ? 'OCCUPIED' : 'FREE'}
                            </span>
                          </div>

                          {/* Dimensions & Constraints */}
                          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', display: 'flex', justifyContent: 'space-between' }}>
                            <span>Length: <strong style={{ color: '#fff' }}>{b.max_length_m}m</strong></span>
                            <span>Draft: <strong style={{ color: '#fff' }}>{b.max_draft_m}m</strong></span>
                          </div>

                          {/* Cranes handling */}
                          <div style={{ fontSize: '0.68rem', color: 'var(--text-dim)' }}>
                            Cranes: {b.crane_count} units ({b.crane_handling_rate_teu_hr} TEU/h)
                          </div>

                          {/* Occupied Reservation Details & Release Action Button */}
                          {isOccupied && booking && (
                            <div style={{
                              marginTop: 'auto',
                              paddingTop: '0.55rem',
                              borderTop: '1px solid rgba(244, 63, 94, 0.2)',
                              display: 'flex',
                              flexDirection: 'column',
                              gap: '0.45rem'
                            }}>
                              <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#fca5a5', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                                <Ship size={13} color="#f43f5e" />
                                <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                  {booking.vessel_name}
                                </span>
                              </div>

                              <div style={{ fontSize: '0.68rem', color: 'var(--text-dim)', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                                <Clock size={11} color="#f87171" />
                                <span>{formatOccupiedSchedule(booking)}</span>
                              </div>

                              {/* Requirement 2: Clean intuitive "Release Berth" button */}
                              <button
                                type="button"
                                onClick={() => handleOpenReleaseModal(b)}
                                className="btn-secondary"
                                style={{
                                  background: 'rgba(239, 68, 68, 0.15)',
                                  border: '1px solid rgba(239, 68, 68, 0.4)',
                                  color: '#fca5a5',
                                  fontSize: '0.72rem',
                                  padding: '0.35rem 0.65rem',
                                  borderRadius: '6px',
                                  fontWeight: 600,
                                  cursor: 'pointer',
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'center',
                                  gap: '0.35rem',
                                  marginTop: '0.2rem',
                                  transition: 'all 0.15s ease'
                                }}
                                onMouseEnter={(e) => {
                                  e.currentTarget.style.background = 'rgba(239, 68, 68, 0.3)';
                                  e.currentTarget.style.color = '#fff';
                                }}
                                onMouseLeave={(e) => {
                                  e.currentTarget.style.background = 'rgba(239, 68, 68, 0.15)';
                                  e.currentTarget.style.color = '#fca5a5';
                                }}
                              >
                                <XCircle size={13} color="#f87171" />
                                <span>Release Berth</span>
                              </button>
                            </div>
                          )}

                          {/* Free Berth Callout */}
                          {!isOccupied && (
                            <div style={{
                              marginTop: 'auto',
                              paddingTop: '0.45rem',
                              borderTop: '1px solid rgba(16, 185, 129, 0.15)',
                              fontSize: '0.7rem',
                              color: '#6ee7b7',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '0.3rem'
                            }}>
                              <CheckCircle2 size={12} color="#10b981" />
                              <span>Ready for Allocation</span>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Confirmation Modal for Releasing a Berth */}
      {releaseModalData && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.75)',
          backdropFilter: 'blur(6px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 9999,
          padding: '1rem'
        }}>
          <div style={{
            background: 'var(--bg-card)',
            border: '2px solid rgba(239, 68, 68, 0.5)',
            borderRadius: '12px',
            maxWidth: '460px',
            width: '100%',
            padding: '1.5rem',
            display: 'flex',
            flexDirection: 'column',
            gap: '1rem',
            boxShadow: '0 20px 40px rgba(0, 0, 0, 0.6), 0 0 25px rgba(239, 68, 68, 0.25)',
            animation: 'fadeIn 0.15s ease-out'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                <div style={{
                  background: 'rgba(239, 68, 68, 0.15)',
                  border: '1px solid rgba(239, 68, 68, 0.4)',
                  borderRadius: '8px',
                  width: '36px',
                  height: '36px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#f43f5e'
                }}>
                  <ShieldAlert size={20} />
                </div>
                <div>
                  <h4 style={{ margin: 0, color: '#f8fafc', fontSize: '1rem', fontWeight: 700 }}>
                    Confirm Berth Release
                  </h4>
                  <span style={{ fontSize: '0.72rem', color: '#fca5a5' }}>
                    Deactivate Booking & Free Berth
                  </span>
                </div>
              </div>

              <button
                type="button"
                onClick={handleCloseReleaseModal}
                disabled={releasingInProgress}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--text-muted)',
                  cursor: 'pointer',
                  padding: '4px'
                }}
              >
                <X size={18} />
              </button>
            </div>

            <div style={{ fontSize: '0.85rem', color: '#e2e8f0', lineHeight: '1.45' }}>
              Are you sure you want to release <strong>Berth {releaseModalData.berth_id}</strong> ({releaseModalData.terminal_name})?
            </div>

            {releaseModalData.current_booking && (
              <div style={{
                background: 'rgba(7, 13, 30, 0.8)',
                border: '1px solid var(--border-secondary)',
                borderRadius: '8px',
                padding: '0.75rem',
                fontSize: '0.78rem',
                display: 'flex',
                flexDirection: 'column',
                gap: '0.35rem'
              }}>
                <div>Vessel: <strong style={{ color: '#38bdf8' }}>{releaseModalData.current_booking.vessel_name}</strong> (IMO: {releaseModalData.current_booking.vessel_imo || 'N/A'})</div>
                <div>Booking ID: <strong style={{ color: '#fff' }}>#{releaseModalData.current_booking.booking_id}</strong></div>
                <div>Schedule: <strong style={{ color: '#f87171' }}>{formatOccupiedSchedule(releaseModalData.current_booking)}</strong></div>
              </div>
            )}

            <p style={{ margin: 0, fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Action Outcome: The active booking will be set to 'RELEASED'. The berth will immediately turn green (FREE) and be available for new allocations.
            </p>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '0.5rem' }}>
              <button
                type="button"
                onClick={handleCloseReleaseModal}
                disabled={releasingInProgress}
                className="btn-secondary"
                style={{ fontSize: '0.8rem', padding: '0.5rem 1rem' }}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmRelease}
                disabled={releasingInProgress}
                className="btn-primary"
                style={{
                  background: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
                  boxShadow: '0 4px 12px rgba(239, 68, 68, 0.35)',
                  fontSize: '0.8rem',
                  padding: '0.5rem 1.15rem'
                }}
              >
                {releasingInProgress ? (
                  <>
                    <RefreshCw size={14} className="spin" /> Releasing...
                  </>
                ) : (
                  <>
                    <XCircle size={14} /> Yes, Release Berth
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
