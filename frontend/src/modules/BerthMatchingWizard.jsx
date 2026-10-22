import React, { useState, useEffect, useMemo } from 'react';
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
  Building2,
  RefreshCw,
  Eye,
  EyeOff,
  AlertTriangle,
  ChevronRight
} from 'lucide-react';
import { 
  getAvailableBerths, 
  bookBerth, 
  getBerthMatrix, 
  getBookings,
  getIncomingVessels,
  FALLBACK_FLEET
} from '../services/api';
import TerminalMatrix from './TerminalMatrix';

/**
 * Format occupied schedule according to standard operational display:
 * e.g., "Occupied until Oct 23, 02 AM"
 */
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

const formatWindowTime = (isoString) => {
  if (!isoString) return '';
  try {
    const d = new Date(isoString);
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', timeZone: 'UTC' }) + ' UTC';
  } catch (e) {
    return isoString;
  }
};

export default function BerthMatchingWizard({ initialVessel, onBookingSuccess }) {
  // 1. Incoming vessels fleet & vessel selection state
  const [vesselsList, setVesselsList] = useState([]);
  const [loadingVessels, setLoadingVessels] = useState(true);
  const [selectedVesselImo, setSelectedVesselImo] = useState(initialVessel?.imo_number || 9321483);
  const [isManualMode, setIsManualMode] = useState(false);
  const [isAutofilled, setIsAutofilled] = useState(true);

  // 2. Physical constraints form states
  const [vesselName, setVesselName] = useState(initialVessel?.vessel_name || 'EMMA MAERSK');
  const [vesselImo, setVesselImo] = useState(initialVessel?.imo_number || 9321483);
  const [lengthM, setLengthM] = useState(initialVessel?.length_m || 397.0);
  const [draftM, setDraftM] = useState(initialVessel?.draft_m || 14.9);
  
  // 3. Target schedule window defaults: start 4 hours from now, duration 12 hours
  const now = new Date();
  const defaultStart = new Date(now.getTime() + 4 * 3600 * 1000).toISOString().slice(0, 16);
  const defaultEnd = new Date(now.getTime() + 16 * 3600 * 1000).toISOString().slice(0, 16);

  const [startTime, setStartTime] = useState(defaultStart);
  const [endTime, setEndTime] = useState(defaultEnd);

  // 4. Terminal filter constraint state
  const [terminalFilter, setTerminalFilter] = useState('');

  // 5. Temporal window filtering state (active when user clicks find/filter or toggles)
  const [temporalFilterActive, setTemporalFilterActive] = useState(false);

  // 6. Berth data & allocation states
  const [berthMatrix, setBerthMatrix] = useState(null);
  const [availableBerths, setAvailableBerths] = useState([]);
  const [selectedBerth, setSelectedBerth] = useState(null);
  const [loading, setLoading] = useState(false);
  const [bookingInProgress, setBookingInProgress] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [duplicateBookingError, setDuplicateBookingError] = useState(null);
  const [activeTab, setActiveTab] = useState('wizard'); // 'wizard' | 'matrix'

  // Fetch incoming vessels from backend database API
  useEffect(() => {
    let isMounted = true;
    const fetchVessels = async () => {
      setLoadingVessels(true);
      try {
        const fleet = await getIncomingVessels();
        if (isMounted && fleet && fleet.length > 0) {
          setVesselsList(fleet);
          // If no initial vessel was passed via navigation, sync to default EMMA MAERSK or first vessel
          if (!initialVessel) {
            const matched = fleet.find(v => v.imo_number === parseInt(vesselImo, 10)) ||
                            fleet.find(v => v.vessel_name === 'EMMA MAERSK') ||
                            fleet[0];
            if (matched) {
              setSelectedVesselImo(matched.imo_number);
              setVesselName(matched.vessel_name);
              setVesselImo(matched.imo_number);
              setLengthM(matched.length_m);
              setDraftM(matched.draft_m);
              setIsAutofilled(true);
            }
          }
        }
      } catch (err) {
        console.warn('Error fetching fleet in BerthMatchingWizard:', err);
      } finally {
        if (isMounted) setLoadingVessels(false);
      }
    };

    fetchVessels();
    return () => { isMounted = false; };
  }, []);

  // Requirement 1: Handle incoming GIS map context transfers and external vessel changes
  useEffect(() => {
    if (initialVessel) {
      setVesselName(initialVessel.vessel_name || '');
      setVesselImo(initialVessel.imo_number || '');
      setLengthM(initialVessel.length_m || 300);
      setDraftM(initialVessel.draft_m || 12);
      if (initialVessel.imo_number) {
        setSelectedVesselImo(initialVessel.imo_number);
        setIsManualMode(false);
      } else {
        setSelectedVesselImo('custom');
        setIsManualMode(true);
      }
      setIsAutofilled(true);
    }
  }, [initialVessel]);

  // Load initial berth characteristics & matrix
  useEffect(() => {
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

  // Group vessels by vessel_type for clean categorized dropdown
  const groupedVessels = useMemo(() => {
    const groups = {};
    vesselsList.forEach((v) => {
      const type = v.vessel_type || 'Cargo Vessels';
      if (!groups[type]) groups[type] = [];
      groups[type].push(v);
    });
    return groups;
  }, [vesselsList]);

  // Requirement 1: Dropdown selection handler with instant autofill of IMO, Length, Draft
  const handleVesselSelectChange = (e) => {
    const val = e.target.value;
    if (val === 'custom') {
      setSelectedVesselImo('custom');
      setIsManualMode(true);
      setIsAutofilled(false);
      return;
    }

    const imoNum = parseInt(val, 10);
    setSelectedVesselImo(imoNum);
    setIsManualMode(false);

    const found = vesselsList.find(v => v.imo_number === imoNum);
    if (found) {
      setVesselName(found.vessel_name);
      setVesselImo(found.imo_number);
      setLengthM(found.length_m);
      setDraftM(found.draft_m);
      setIsAutofilled(true);
    }
  };

  // Telemetry details of selected vessel
  const selectedVesselDetails = useMemo(() => {
    if (selectedVesselImo === 'custom') return null;
    return vesselsList.find(v => v.imo_number === parseInt(vesselImo, 10)) || null;
  }, [vesselsList, selectedVesselImo, vesselImo]);

  const currentLengthNum = parseFloat(lengthM) || 0;
  const currentDraftNum = parseFloat(draftM) || 0;

  // Flatten all physical berths across terminals
  const allPhysicalBerths = useMemo(() => {
    if (!berthMatrix?.terminal_matrix) return [];
    const list = [];
    Object.values(berthMatrix.terminal_matrix).forEach((termBerths) => {
      termBerths.forEach((b) => list.push(b));
    });
    return list;
  }, [berthMatrix]);

  // Requirement 2: Dynamic Terminal Filter Constraint
  // Filter terminals capable of handling the vessel (max_length_m >= length, max_draft_m >= draft)
  const capableTerminals = useMemo(() => {
    if (!berthMatrix?.terminal_matrix) {
      return [
        { code: 'CICT', name: 'Colombo International Container Terminal (CICT)', berthCount: 5 },
        { code: 'CWIT', name: 'Colombo West International Terminal (CWIT)', berthCount: 12 },
        { code: 'ECT', name: 'East Container Terminal (ECT)', berthCount: 10 },
        { code: 'JCT', name: 'Jaya Container Terminal (JCT)', berthCount: 10 },
        { code: 'SAGT', name: 'South Asia Gateway Terminals (SAGT)', berthCount: 8 },
        { code: 'UCT', name: 'Unity Container Terminal (UCT)', berthCount: 4 }
      ];
    }

    const capable = [];
    Object.entries(berthMatrix.terminal_matrix).forEach(([termName, berths]) => {
      const matchingBerths = berths.filter(
        (b) => b.max_length_m >= currentLengthNum && b.max_draft_m >= currentDraftNum
      );
      if (matchingBerths.length > 0) {
        let code = termName;
        if (termName.includes('(CICT)')) code = 'CICT';
        else if (termName.includes('(CWIT)')) code = 'CWIT';
        else if (termName.includes('(ECT)')) code = 'ECT';
        else if (termName.includes('(JCT)')) code = 'JCT';
        else if (termName.includes('(SAGT)')) code = 'SAGT';
        else if (termName.includes('(UCT)')) code = 'UCT';

        capable.push({
          code,
          name: termName,
          berthCount: matchingBerths.length,
          totalBerths: berths.length,
          maxDraft: Math.max(...berths.map(b => b.max_draft_m)),
          maxLength: Math.max(...berths.map(b => b.max_length_m))
        });
      }
    });

    return capable;
  }, [berthMatrix, currentLengthNum, currentDraftNum]);

  // Automatically reset terminal filter if the current selection becomes physically incompatible
  useEffect(() => {
    if (terminalFilter && capableTerminals.length > 0) {
      const isCapable = capableTerminals.some(
        (t) => t.code === terminalFilter || t.name === terminalFilter || t.name.includes(terminalFilter)
      );
      if (!isCapable) {
        setTerminalFilter('');
      }
    }
  }, [capableTerminals, terminalFilter]);

  // Requirement 3: Filter physical berths matching length, draft, and terminal filter
  const physicallyMatchedBerths = useMemo(() => {
    if (!allPhysicalBerths.length) return [];
    return allPhysicalBerths.filter((b) => {
      const fitsLength = b.max_length_m >= currentLengthNum;
      const fitsDraft = b.max_draft_m >= currentDraftNum;
      const matchesTerminal = !terminalFilter || 
        b.terminal_name.includes(terminalFilter) || 
        (terminalFilter === 'CICT' && b.berth_id.startsWith('CICT')) ||
        (terminalFilter === 'CWIT' && b.berth_id.startsWith('CWIT')) ||
        (terminalFilter === 'ECT' && b.berth_id.startsWith('ECT')) ||
        (terminalFilter === 'JCT' && b.berth_id.startsWith('JCT')) ||
        (terminalFilter === 'SAGT' && b.berth_id.startsWith('SAGT')) ||
        (terminalFilter === 'UCT' && b.berth_id.startsWith('UCT'));
      return fitsLength && fitsDraft && matchesTerminal;
    });
  }, [allPhysicalBerths, currentLengthNum, currentDraftNum, terminalFilter]);

  // Conflict evaluation against target temporal window [startTime, endTime]
  const checkBerthWindowConflict = (berth, reqStartStr, reqEndStr) => {
    if (!reqStartStr || !reqEndStr) return { hasConflict: false, conflictBooking: null };
    const reqStart = new Date(reqStartStr).getTime();
    const reqEnd = new Date(reqEndStr).getTime();
    if (isNaN(reqStart) || isNaN(reqEnd)) return { hasConflict: false, conflictBooking: null };

    // Check current booking
    if (berth.current_booking) {
      const bStart = new Date(berth.current_booking.start_time).getTime();
      const bEnd = new Date(berth.current_booking.end_time).getTime();
      if (bStart < reqEnd && bEnd > reqStart) {
        return { hasConflict: true, conflictBooking: berth.current_booking };
      }
    }

    // Check upcoming bookings
    if (berth.upcoming_bookings && berth.upcoming_bookings.length > 0) {
      for (const bk of berth.upcoming_bookings) {
        const bStart = new Date(bk.start_time).getTime();
        const bEnd = new Date(bk.end_time).getTime();
        if (bStart < reqEnd && bEnd > reqStart) {
          return { hasConflict: true, conflictBooking: bk };
        }
      }
    }

    return { hasConflict: false, conflictBooking: null };
  };

  // Requirement 3: Granular Berth Status Display with live occupancy and schedule
  const berthsWithLiveStatus = useMemo(() => {
    return physicallyMatchedBerths.map((b) => {
      const windowConflict = checkBerthWindowConflict(b, startTime, endTime);
      const isOccupied = windowConflict.hasConflict || b.is_occupied;
      const occupiedBooking = windowConflict.conflictBooking || b.current_booking;

      return {
        ...b,
        draft_clearance_m: +(b.max_draft_m - currentDraftNum).toFixed(1),
        length_clearance_m: +(b.max_length_m - currentLengthNum).toFixed(1),
        isWindowConflict: windowConflict.hasConflict,
        isOccupied,
        occupiedBooking
      };
    });
  }, [physicallyMatchedBerths, startTime, endTime, currentLengthNum, currentDraftNum]);

  // Requirement 4: Temporal Window Filtering
  // When temporal filtering is active, dynamically hide occupied slots overlapping that window
  const displayedBerths = useMemo(() => {
    if (!temporalFilterActive) {
      return berthsWithLiveStatus;
    }
    return berthsWithLiveStatus.filter((b) => !b.isOccupied && !b.isWindowConflict);
  }, [berthsWithLiveStatus, temporalFilterActive]);

  // Form submit handler: Triggers Temporal Window Filtering & updates available berths
  const handleFindQualifiedBerths = async (e) => {
    if (e) e.preventDefault();
    setErrorMsg('');
    setSuccessMsg('');
    setLoading(true);
    setTemporalFilterActive(true); // Activate temporal window filter

    try {
      const formattedStart = new Date(startTime).toISOString();
      const formattedEnd = new Date(endTime).toISOString();

      const res = await getAvailableBerths({
        length_m: currentLengthNum,
        draft_m: currentDraftNum,
        start_time: formattedStart,
        end_time: formattedEnd,
        terminal_name: terminalFilter || undefined
      });

      setAvailableBerths(res.available_berths || []);
      // If berths are available, pre-select the first one
      if (res.available_berths?.length > 0) {
        setSelectedBerth(res.available_berths[0]);
      } else {
        setSelectedBerth(null);
      }
      // Refresh matrix to sync latest reservations
      loadMatrix();
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || err.message || 'Error executing constraint matching.');
    } finally {
      setLoading(false);
    }
  };

  // Booking confirmation
  const handleConfirmBooking = async () => {
    if (!selectedBerth) return;
    setBookingInProgress(true);
    setErrorMsg('');
    setSuccessMsg('');

    try {
      const formattedStart = new Date(startTime).toISOString();
      const formattedEnd = new Date(endTime).toISOString();

      const bookingPayload = {
        vessel_imo: parseInt(vesselImo, 10),
        vessel_name: vesselName,
        berth_id: selectedBerth.berth_id,
        start_time: formattedStart,
        end_time: formattedEnd,
        length_m: currentLengthNum,
        draft_m: currentDraftNum
      };

      const result = await bookBerth(bookingPayload);
      setSuccessMsg(`Berth ${selectedBerth.berth_id} (${selectedBerth.terminal_name}) successfully confirmed for ${vesselName}! Booking ID: #${result.booking?.booking_id}`);
      setDuplicateBookingError(null);
      
      // Refresh live matrix & search
      await loadMatrix();
      await handleFindQualifiedBerths();

      if (onBookingSuccess) {
        onBookingSuccess(result.booking);
      }
    } catch (err) {
      const detail = err.response?.data?.detail || err.message;
      if (
        detail.includes('already has an active conflicting berth reservation') ||
        detail.includes('Validation Error: Vessel')
      ) {
        setDuplicateBookingError({
          title: 'Duplicate Booking / Time-Overlap Violation',
          message: detail,
          explanation: `Operational Constraint: Vessel "${vesselName}" (IMO ${vesselImo}) already holds an active conflicting berth reservation elsewhere in the port during this time window. A vessel cannot occupy multiple berths simultaneously.`
        });
        setErrorMsg(detail);
      } else {
        setErrorMsg(`Booking Collision / Constraint Violation: ${detail}`);
        setDuplicateBookingError(null);
      }
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
      {duplicateBookingError && (
        <div style={{
          background: 'linear-gradient(135deg, rgba(239, 68, 68, 0.18) 0%, rgba(185, 28, 28, 0.22) 100%)',
          border: '2px solid #ef4444',
          borderRadius: '10px',
          padding: '1rem 1.25rem',
          color: '#fee2e2',
          display: 'flex',
          flexDirection: 'column',
          gap: '0.6rem',
          boxShadow: '0 4px 20px rgba(239, 68, 68, 0.3)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
              <div style={{
                background: '#ef4444',
                borderRadius: '8px',
                width: '32px',
                height: '32px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#fff',
                boxShadow: '0 0 10px rgba(239, 68, 68, 0.5)'
              }}>
                <AlertTriangle size={18} />
              </div>
              <div>
                <h4 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 700, color: '#fff' }}>
                  {duplicateBookingError.title}
                </h4>
                <span style={{ fontSize: '0.72rem', color: '#fca5a5' }}>
                  Validation Rule Enforced: Same Vessel Cannot Be Allocated to Multiple Berths Concurrently
                </span>
              </div>
            </div>
            <button
              type="button"
              onClick={() => setDuplicateBookingError(null)}
              style={{
                background: 'rgba(255, 255, 255, 0.1)',
                border: 'none',
                color: '#fee2e2',
                borderRadius: '6px',
                width: '24px',
                height: '24px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}
            >
              <X size={15} />
            </button>
          </div>

          <div style={{ fontSize: '0.85rem', color: '#fecaca', background: 'rgba(0, 0, 0, 0.3)', padding: '0.6rem 0.85rem', borderRadius: '6px', border: '1px solid rgba(239, 68, 68, 0.3)' }}>
            <strong>{duplicateBookingError.message}</strong>
          </div>

          <p style={{ margin: 0, fontSize: '0.78rem', color: '#fca5a5', lineHeight: '1.4' }}>
            {duplicateBookingError.explanation}
          </p>

          <div style={{ fontSize: '0.74rem', color: '#fda4af', borderTop: '1px solid rgba(239, 68, 68, 0.25)', paddingTop: '0.4rem' }}>
            Operator Notice: Please adjust the Target Arrival / Departure window or verify existing reservation records in the Berth Matrix before attempting reassignment.
          </div>
        </div>
      )}

      {errorMsg && !duplicateBookingError && (
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
        <div className="allocation-wizard-grid">
          {/* Form Controls Card */}
          <div className="panel-card">
            <div className="card-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Ship size={18} color="#38bdf8" />
                <h3 style={{ fontSize: '0.95rem', fontWeight: 600 }}>Vessel & Physical Constraints</h3>
              </div>
              {isAutofilled && (
                <span className="badge badge-ocean" style={{ fontSize: '0.65rem' }}>
                  Auto-filled
                </span>
              )}
            </div>

            <form onSubmit={handleFindQualifiedBerths} className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: '0.9rem' }}>
              {/* 1. Unified Vessel Selection Dropdown & GIS Transfer Sync */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                  <label htmlFor="vessel-select-dropdown" style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                    Select Incoming Vessel
                    {loadingVessels && (
                      <span style={{ color: 'var(--ocean-cyan)', display: 'inline-flex', alignItems: 'center', gap: '3px' }}>
                        (fetching...)
                      </span>
                    )}
                  </label>
                  <button
                    type="button"
                    onClick={() => {
                      const nextMode = !isManualMode;
                      setIsManualMode(nextMode);
                      if (nextMode) setSelectedVesselImo('custom');
                    }}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: '#38bdf8',
                      fontSize: '0.7rem',
                      cursor: 'pointer',
                      textDecoration: 'underline',
                      padding: 0
                    }}
                  >
                    {isManualMode ? 'Choose from Fleet' : 'Custom Vessel'}
                  </button>
                </div>

                {!isManualMode ? (
                  <select
                    id="vessel-select-dropdown"
                    className="input-control"
                    value={selectedVesselImo || ''}
                    onChange={handleVesselSelectChange}
                    style={{
                      cursor: 'pointer',
                      backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%2338bdf8' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E")`,
                      backgroundRepeat: 'no-repeat',
                      backgroundPosition: 'right 0.75rem center',
                      paddingRight: '2.5rem',
                      appearance: 'none',
                      WebkitAppearance: 'none'
                    }}
                  >
                    <option value="" disabled>-- Select an incoming vessel from fleet --</option>
                    {Object.entries(groupedVessels).map(([type, vList]) => (
                      <optgroup
                        key={type}
                        label={`── ${type.toUpperCase()} ──`}
                        style={{ background: '#0c142b', color: '#38bdf8', fontWeight: 600 }}
                      >
                        {vList.map((v) => (
                          <option
                            key={v.imo_number}
                            value={v.imo_number}
                            style={{ background: '#070d1e', color: '#f8fafc' }}
                          >
                            {v.vessel_name} (IMO: {v.imo_number} • {v.length_m}m × {v.draft_m}m)
                          </option>
                        ))}
                      </optgroup>
                    ))}
                    <optgroup label="── MANUAL ENTRY ──" style={{ background: '#0c142b', color: '#a855f7' }}>
                      <option value="custom" style={{ background: '#070d1e', color: '#f8fafc' }}>
                        ✏️ Custom / Unlisted Vessel (Manual Input)
                      </option>
                    </optgroup>
                  </select>
                ) : (
                  <div>
                    <input
                      type="text"
                      id="vessel-select-dropdown"
                      className="input-control"
                      placeholder="Enter vessel name..."
                      value={vesselName}
                      onChange={(e) => {
                        setVesselName(e.target.value);
                        setIsAutofilled(false);
                      }}
                      required
                    />
                  </div>
                )}
              </div>

              {/* Vessel Telemetry Quick Insights Badge */}
              {selectedVesselDetails && !isManualMode && (
                <div style={{
                  background: 'rgba(2, 132, 199, 0.08)',
                  border: '1px solid rgba(56, 189, 248, 0.2)',
                  borderRadius: '8px',
                  padding: '0.5rem 0.75rem',
                  fontSize: '0.72rem',
                  display: 'grid',
                  gridTemplateColumns: 'repeat(3, 1fr)',
                  gap: '0.4rem'
                }}>
                  <div>
                    <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.65rem' }}>Class</span>
                    <strong style={{ color: '#f8fafc' }}>{selectedVesselDetails.vessel_type || 'Cargo'}</strong>
                  </div>
                  <div>
                    <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.65rem' }}>Dist to Port</span>
                    <strong style={{ color: '#38bdf8' }}>{selectedVesselDetails.distance_to_port_nmi ?? '—'} nmi</strong>
                  </div>
                  <div>
                    <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.65rem' }}>Speed (SOG)</span>
                    <strong style={{ color: '#10b981' }}>{selectedVesselDetails.sog ?? '—'} kts</strong>
                  </div>
                </div>
              )}

              {/* IMO Number (Editable) */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                  <label htmlFor="vessel-imo-input" style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    IMO Number
                  </label>
                  {isAutofilled && (
                    <span style={{ fontSize: '0.68rem', color: '#94a3b8' }}>Autofilled (editable)</span>
                  )}
                </div>
                <input
                  id="vessel-imo-input"
                  type="number"
                  className="input-control"
                  value={vesselImo}
                  onChange={(e) => {
                    setVesselImo(e.target.value);
                    setIsAutofilled(false);
                  }}
                  required
                />
              </div>

              {/* Length & Draft (Editable Numeric Inputs) */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                    <label htmlFor="vessel-length-input" style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      Length (meters)
                    </label>
                    <span style={{ fontSize: '0.65rem', color: 'var(--text-dim)' }}>Editable</span>
                  </div>
                  <input
                    id="vessel-length-input"
                    type="number"
                    step="0.1"
                    className="input-control"
                    value={lengthM}
                    onChange={(e) => {
                      setLengthM(e.target.value);
                      setIsAutofilled(false);
                    }}
                    required
                  />
                </div>

                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                    <label htmlFor="vessel-draft-input" style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      Draft (meters)
                    </label>
                    <span style={{ fontSize: '0.65rem', color: 'var(--text-dim)' }}>Editable</span>
                  </div>
                  <input
                    id="vessel-draft-input"
                    type="number"
                    step="0.1"
                    className="input-control"
                    value={draftM}
                    onChange={(e) => {
                      setDraftM(e.target.value);
                      setIsAutofilled(false);
                    }}
                    required
                  />
                </div>
              </div>

              {/* Target Arrival & Departure Window */}
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

              {/* Requirement 2: Dynamic Terminal Filter Constraint */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                  <label htmlFor="terminal-filter-select" style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    Terminal Filter (Physical Feasibility Constrained)
                  </label>
                  <span style={{ fontSize: '0.68rem', color: 'var(--ocean-cyan)', fontWeight: 600 }}>
                    {capableTerminals.length} capable terminals
                  </span>
                </div>
                <select
                  id="terminal-filter-select"
                  className="input-control"
                  value={terminalFilter}
                  onChange={(e) => setTerminalFilter(e.target.value)}
                  style={{
                    cursor: 'pointer',
                    backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%2338bdf8' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E")`,
                    backgroundRepeat: 'no-repeat',
                    backgroundPosition: 'right 0.75rem center',
                    paddingRight: '2.5rem',
                    appearance: 'none',
                    WebkitAppearance: 'none'
                  }}
                >
                  <option value="">All Terminals (Colombo Port - {capableTerminals.length} Capable)</option>
                  {capableTerminals.map((t) => (
                    <option key={t.code} value={t.code}>
                      {t.name} ({t.berthCount} matching berths)
                    </option>
                  ))}
                </select>
                {capableTerminals.length < 6 && (
                  <div style={{ fontSize: '0.68rem', color: 'var(--amber-warning)', marginTop: '4px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <Filter size={11} />
                    <span>Excluded {6 - capableTerminals.length} terminals unable to accommodate vessel draft ({draftM}m) or length ({lengthM}m).</span>
                  </div>
                )}
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

          {/* Requirement 3 & 4: Qualified Berths Results Container */}
          <div className="panel-card" style={{ display: 'flex', flexDirection: 'column' }}>
            <div className="card-header" style={{ flexWrap: 'wrap', gap: '0.75rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <ShieldCheck size={18} color="#10b981" />
                <h3 style={{ fontSize: '0.95rem', fontWeight: 600 }}>
                  Qualified Berths ({displayedBerths.length})
                </h3>
                {temporalFilterActive && (
                  <span className="badge badge-ocean" style={{ fontSize: '0.65rem' }}>
                    Temporal Window Filter Active
                  </span>
                )}
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                {/* Temporal Filter Mode Toggle */}
                <button
                  type="button"
                  onClick={() => setTemporalFilterActive(!temporalFilterActive)}
                  className="btn-secondary"
                  style={{ fontSize: '0.75rem', padding: '0.35rem 0.75rem' }}
                  title="Toggle between clean available berths and all physical berths with live occupancy"
                >
                  {temporalFilterActive ? (
                    <>
                      <Eye size={13} /> Show All (Inc. Occupied)
                    </>
                  ) : (
                    <>
                      <Filter size={13} /> Filter By Time Window
                    </>
                  )}
                </button>

                {/* Confirm Allocation Button */}
                {selectedBerth && !selectedBerth.isOccupied && (
                  <button
                    onClick={handleConfirmBooking}
                    disabled={bookingInProgress}
                    className="btn-primary"
                    style={{ background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)', fontSize: '0.8rem', padding: '0.45rem 0.9rem' }}
                  >
                    <Check size={15} />
                    {bookingInProgress ? 'Securing Slot...' : `Confirm: ${selectedBerth.berth_id}`}
                  </button>
                )}
              </div>
            </div>

            {/* Active Constraints Summary Bar */}
            <div style={{
              background: 'rgba(12, 20, 43, 0.5)',
              borderBottom: '1px solid var(--border-secondary)',
              padding: '0.5rem 1.25rem',
              fontSize: '0.75rem',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: '0.5rem'
            }}>
              <div style={{ color: 'var(--text-muted)', display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                <span>Vessel: <strong style={{ color: '#fff' }}>{vesselName}</strong></span>
                <span>Dim: <strong style={{ color: '#38bdf8' }}>{lengthM}m × {draftM}m</strong></span>
                <span>Terminal: <strong style={{ color: '#fff' }}>{terminalFilter || 'All Capable Terminals'}</strong></span>
              </div>
              <div style={{ color: 'var(--text-dim)', fontSize: '0.7rem' }}>
                Target Window: {formatWindowTime(startTime)} → {formatWindowTime(endTime)}
              </div>
            </div>

            <div className="card-body" style={{ flex: 1, overflowY: 'auto' }}>
              {displayedBerths.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '3rem 1rem', color: 'var(--text-muted)' }}>
                  <Anchor size={48} color="#64748b" style={{ margin: '0 auto 1rem auto', opacity: 0.5 }} />
                  <p style={{ fontWeight: 600, color: '#f8fafc', fontSize: '0.95rem' }}>
                    No Berths Match Active Filter Criteria
                  </p>
                  <p style={{ fontSize: '0.8rem', marginTop: '6px', maxWidth: '420px', margin: '6px auto 0 auto' }}>
                    {temporalFilterActive 
                      ? `All physically compatible berths are occupied during the requested window. Click "Show All (Inc. Occupied)" to view schedule vacancies or adjust your time window.`
                      : `Vessel dimensions (${lengthM}m length, ${draftM}m draft) exceed available terminal constraints.`
                    }
                  </p>
                  {temporalFilterActive && (
                    <button
                      type="button"
                      onClick={() => setTemporalFilterActive(false)}
                      className="btn-secondary"
                      style={{ marginTop: '1rem', fontSize: '0.8rem' }}
                    >
                      <Eye size={14} /> Show All Physical Berths With Schedules
                    </button>
                  )}
                </div>
              ) : (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(290px, 1fr))', gap: '1rem' }}>
                  {displayedBerths.map((berth) => {
                    const isSelected = selectedBerth?.berth_id === berth.berth_id;
                    const isOccupied = berth.isOccupied;
                    const occupiedBooking = berth.occupiedBooking;

                    return (
                      <div
                        key={berth.berth_id}
                        onClick={() => {
                          if (!isOccupied) {
                            setSelectedBerth(berth);
                          } else {
                            setErrorMsg(`Berth ${berth.berth_id} is currently occupied (${formatOccupiedSchedule(occupiedBooking)}). Choose a free berth or adjust target arrival/departure window.`);
                          }
                        }}
                        style={{
                          background: isSelected 
                            ? 'rgba(2, 132, 199, 0.18)' 
                            : isOccupied 
                              ? 'rgba(244, 63, 94, 0.05)' 
                              : 'var(--bg-card-secondary)',
                          border: isSelected 
                            ? '2px solid #38bdf8' 
                            : isOccupied 
                              ? '1px solid rgba(244, 63, 94, 0.3)' 
                              : '1px solid var(--border-secondary)',
                          borderRadius: '10px',
                          padding: '1rem',
                          cursor: isOccupied ? 'not-allowed' : 'pointer',
                          transition: 'all 0.2s ease',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '0.65rem',
                          boxShadow: isSelected ? '0 0 15px rgba(56, 189, 248, 0.25)' : 'none'
                        }}
                      >
                        {/* Header: Berth ID & Live Occupancy Status Indicator */}
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <span style={{ fontSize: '1.15rem', fontWeight: 700, color: '#f8fafc', letterSpacing: '-0.01em' }}>
                            {berth.berth_id}
                          </span>

                          {/* Requirement 3: Live Occupancy Status Display */}
                          {isOccupied ? (
                            <span 
                              className="badge badge-infeasible" 
                              style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.7rem' }}
                            >
                              <span className="pulse-dot danger" style={{ width: '6px', height: '6px' }} />
                              OCCUPIED
                            </span>
                          ) : (
                            <span 
                              className="badge badge-feasible" 
                              style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.7rem' }}
                            >
                              <span className="pulse-dot online" style={{ width: '6px', height: '6px' }} />
                              FREE
                            </span>
                          )}
                        </div>

                        {/* Terminal Name */}
                        <div style={{ fontSize: '0.78rem', color: 'var(--ocean-cyan)', fontWeight: 500 }}>
                          {berth.terminal_name}
                        </div>

                        {/* Requirement 3: Detailed Occupied Schedule Banner if Occupied */}
                        {isOccupied && occupiedBooking && (
                          <div style={{
                            background: 'rgba(244, 63, 94, 0.12)',
                            border: '1px solid rgba(244, 63, 94, 0.25)',
                            borderRadius: '6px',
                            padding: '0.45rem 0.65rem',
                            fontSize: '0.72rem',
                            color: '#fca5a5'
                          }}>
                            <div style={{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                              <Clock size={12} color="#f43f5e" />
                              {formatOccupiedSchedule(occupiedBooking)}
                            </div>
                            {occupiedBooking.vessel_name && (
                              <div style={{ fontSize: '0.68rem', color: '#fda4af', marginTop: '2px' }}>
                                Vessel: <strong>{occupiedBooking.vessel_name}</strong> {occupiedBooking.vessel_imo ? `(IMO ${occupiedBooking.vessel_imo})` : ''}
                              </div>
                            )}
                          </div>
                        )}

                        {/* If FREE: Show Ready Indicator */}
                        {!isOccupied && (
                          <div style={{
                            background: 'rgba(16, 185, 129, 0.08)',
                            border: '1px solid rgba(16, 185, 129, 0.2)',
                            borderRadius: '6px',
                            padding: '0.35rem 0.6rem',
                            fontSize: '0.72rem',
                            color: '#6ee7b7',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.35rem'
                          }}>
                            <CheckCircle2 size={13} color="#10b981" />
                            <span>Available for Immediate Allocation</span>
                          </div>
                        )}

                        {/* Physical Clearances & Berth Specifications */}
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px', fontSize: '0.75rem', color: 'var(--text-muted)', paddingTop: '6px', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
                          <div>Max Draft: <strong style={{ color: '#fff' }}>{berth.max_draft_m}m</strong></div>
                          <div>Draft Clearance: <strong style={{ color: berth.draft_clearance_m >= 0 ? '#10b981' : '#f43f5e' }}>+{berth.draft_clearance_m}m</strong></div>
                          <div>Max Length: <strong style={{ color: '#fff' }}>{berth.max_length_m}m</strong></div>
                          <div>Length Clearance: <strong style={{ color: berth.length_clearance_m >= 0 ? '#10b981' : '#f43f5e' }}>+{berth.length_clearance_m}m</strong></div>
                          <div>Cranes: <strong style={{ color: '#fff' }}>{berth.crane_count} units</strong></div>
                          <div>Handling: <strong style={{ color: '#fff' }}>{berth.crane_handling_rate_teu_hr} TEU/h</strong></div>
                        </div>

                        {isSelected && !isOccupied && (
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
        /* Terminal Berth Matrix & Occupancy Grid View */
        <TerminalMatrix
          onBerthReleased={() => {
            loadMatrix();
            handleFindQualifiedBerths();
          }}
        />
      )}
    </div>
  );
}
