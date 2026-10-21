import React, { useState, useEffect } from 'react';
import { 
  Anchor, 
  Navigation, 
  Layers, 
  RefreshCw, 
  BarChart3, 
  ShieldCheck, 
  Clock, 
  Activity, 
  Radio, 
  Cpu, 
  ChevronRight,
  Database
} from 'lucide-react';

import { checkHealth, getBerthMatrix, getBookings } from './services/api';
import VesselTrackingMap from './modules/VesselTrackingMap';
import BerthAllocationPanel from './modules/BerthAllocationPanel';
import DynamicRescheduling from './modules/DynamicRescheduling';
import ResearchObservatory from './modules/ResearchObservatory';

export default function App() {
  const [activeModule, setActiveModule] = useState('overview'); // 'overview' | 'tracking' | 'allocation' | 'rescheduling' | 'research'
  const [systemHealth, setSystemHealth] = useState({ status: 'checking', database_connected: false });
  const [utcTime, setUtcTime] = useState(new Date().toUTCString());
  const [selectedVesselForAllocation, setSelectedVesselForAllocation] = useState(null);
  const [stats, setStats] = useState({ totalBerths: 49, activeBookings: 0 });

  // Ticking UTC clock
  useEffect(() => {
    const timer = setInterval(() => {
      setUtcTime(new Date().toUTCString());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Poll backend health & quick stats
  useEffect(() => {
    const fetchStats = async () => {
      const health = await checkHealth();
      setSystemHealth(health);

      try {
        const matrix = await getBerthMatrix();
        setStats({
          totalBerths: matrix.total_berths || 49,
          activeBookings: matrix.total_occupied_slots || 0
        });
      } catch (err) {
        // Fallback
      }
    };

    fetchStats();
    const interval = setInterval(fetchStats, 15000);
    return () => clearInterval(interval);
  }, []);

  const handleVesselSelectedFromMap = (vessel) => {
    setSelectedVesselForAllocation(vessel);
  };

  const handleProceedToAllocation = (vessel) => {
    if (vessel) {
      setSelectedVesselForAllocation(vessel);
    }
    setActiveModule('allocation');
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Top Marine Command Header */}
      <header style={{
        background: 'rgba(7, 13, 30, 0.95)',
        borderBottom: '1px solid var(--border-primary)',
        backdropFilter: 'blur(10px)',
        position: 'sticky',
        top: 0,
        zIndex: 1000,
        padding: '0.75rem 1.5rem'
      }}>
        <div style={{
          maxWidth: '1600px',
          margin: '0 auto',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          {/* Logo & Research Identity */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
            <div style={{
              width: '40px',
              height: '40px',
              borderRadius: '10px',
              background: 'linear-gradient(135deg, #0284c7 0%, #0369a1 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 15px rgba(2, 132, 199, 0.4)',
              border: '1px solid #38bdf8'
            }}>
              <Anchor size={22} color="#ffffff" />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <h1 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#f8fafc', letterSpacing: '-0.01em' }}>
                  Smart Port Management System
                </h1>
                <span className="badge badge-ocean" style={{ fontSize: '0.68rem', padding: '0.15rem 0.5rem' }}>
                  Component 1: Research Framework
                </span>
              </div>
              <p style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                Intelligent Vessel ETA Prediction & Dynamic Berth Allocation | Port of Colombo
              </p>
            </div>
          </div>

          {/* Real-time System Indicators */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              background: 'var(--bg-card-secondary)',
              padding: '0.35rem 0.75rem',
              borderRadius: '9999px',
              border: '1px solid var(--border-secondary)',
              fontSize: '0.75rem'
            }}>
              <span className={`pulse-dot ${systemHealth.database_connected ? 'online' : 'danger'}`} />
              <span style={{ color: systemHealth.database_connected ? 'var(--emerald-success)' : 'var(--rose-danger)', fontWeight: 600 }}>
                {systemHealth.database_connected ? 'FASTAPI CORE ONLINE' : 'DISCONNECTED'}
              </span>
            </div>

            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              color: 'var(--text-muted)',
              fontSize: '0.75rem',
              fontFamily: 'var(--font-mono)'
            }}>
              <Clock size={14} color="#38bdf8" />
              <span>{utcTime}</span>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation Sub-Bar */}
      <nav style={{
        background: 'rgba(12, 20, 43, 0.7)',
        borderBottom: '1px solid rgba(255, 255, 255, 0.06)',
        padding: '0.5rem 1.5rem'
      }}>
        <div style={{
          maxWidth: '1600px',
          margin: '0 auto',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button
              onClick={() => setActiveModule('overview')}
              className={activeModule === 'overview' ? 'btn-primary' : 'btn-secondary'}
              style={{ fontSize: '0.8rem', padding: '0.45rem 0.9rem' }}
            >
              <Activity size={15} /> Command Center Overview
            </button>

            <button
              onClick={() => setActiveModule('tracking')}
              className={activeModule === 'tracking' ? 'btn-primary' : 'btn-secondary'}
              style={{ fontSize: '0.8rem', padding: '0.45rem 0.9rem' }}
            >
              <Navigation size={15} /> Real-Time GIS Fleet Tracking
            </button>

            <button
              onClick={() => setActiveModule('allocation')}
              className={activeModule === 'allocation' ? 'btn-primary' : 'btn-secondary'}
              style={{ fontSize: '0.8rem', padding: '0.45rem 0.9rem' }}
            >
              <Layers size={15} /> Intelligent Berth Matching & Matrix
            </button>

            <button
              onClick={() => setActiveModule('rescheduling')}
              className={activeModule === 'rescheduling' ? 'btn-primary' : 'btn-secondary'}
              style={{ fontSize: '0.8rem', padding: '0.45rem 0.9rem' }}
            >
              <RefreshCw size={15} /> Adaptive Rescheduling & Delay Logs
            </button>

            <button
              onClick={() => setActiveModule('research')}
              className={activeModule === 'research' ? 'btn-primary' : 'btn-secondary'}
              style={{ fontSize: '0.8rem', padding: '0.45rem 0.9rem' }}
            >
              <BarChart3 size={15} /> Research Observatory (Metrics)
            </button>
          </div>

          <div style={{ display: 'flex', gap: '0.75rem', fontSize: '0.75rem' }}>
            <span style={{ color: 'var(--text-muted)' }}>
              Physical Berths: <strong style={{ color: '#fff' }}>{stats.totalBerths}</strong>
            </span>
            <span style={{ color: 'var(--text-dim)' }}>|</span>
            <span style={{ color: 'var(--text-muted)' }}>
              Active Slots: <strong style={{ color: '#38bdf8' }}>{stats.activeBookings}</strong>
            </span>
          </div>
        </div>
      </nav>

      {/* Main Command Center Body */}
      <main className="command-container" style={{ flex: 1, marginTop: '1.25rem' }}>
        {activeModule === 'overview' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            {/* Quick Metrics Bar */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem' }}>
              <div className="panel-card" style={{ padding: '1rem' }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>VTS Fleet Under Surveillance</div>
                <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#f8fafc', marginTop: '2px' }}>
                  5 Vessels <span style={{ fontSize: '0.75rem', color: '#10b981', fontWeight: 500 }}>(Nominal)</span>
                </div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', marginTop: '4px' }}>Approaching Port of Colombo</div>
              </div>

              <div className="panel-card" style={{ padding: '1rem' }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Continuous ETA Model Error</div>
                <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#38bdf8', marginTop: '2px' }}>
                  MAE 8.57 <span style={{ fontSize: '0.8rem', fontWeight: 400 }}>hrs</span>
                </div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', marginTop: '4px' }}>RMSE: 9.96 hrs | R²: 0.4707</div>
              </div>

              <div className="panel-card" style={{ padding: '1rem' }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Berth Feasibility Precision</div>
                <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#10b981', marginTop: '2px' }}>
                  99.03%
                </div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', marginTop: '4px' }}>Multi-Class ROC-AUC: 0.9999</div>
              </div>

              <div className="panel-card" style={{ padding: '1rem' }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Self-Healing Reallocations</div>
                <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#f59e0b', marginTop: '2px' }}>
                  Autonomous
                </div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', marginTop: '4px' }}>Event-driven unbooking active</div>
              </div>
            </div>

            {/* Vessel Tracking GIS Module */}
            <VesselTrackingMap 
              initialVessel={selectedVesselForAllocation}
              onSelectVessel={handleVesselSelectedFromMap}
              onProceedToAllocation={handleProceedToAllocation}
            />

            {/* Quick Link Banner to Allocation Wizard */}
            <div className="panel-card" style={{ padding: '1.25rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(2, 132, 199, 0.08)' }}>
              <div>
                <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#f8fafc' }}>
                  Need to allocate an arriving vessel or check terminal slot availability?
                </h3>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  Use the Intelligent Berth Matching Wizard to evaluate length and draft constraints against Colombo's 49 berths.
                </p>
              </div>
              <button onClick={() => setActiveModule('allocation')} className="btn-primary">
                Open Berth Matching Wizard <ChevronRight size={16} />
              </button>
            </div>
          </div>
        )}

        {activeModule === 'tracking' && (
          <VesselTrackingMap 
            initialVessel={selectedVesselForAllocation}
            onSelectVessel={handleVesselSelectedFromMap}
            onProceedToAllocation={handleProceedToAllocation}
          />
        )}

        {activeModule === 'allocation' && (
          <BerthAllocationPanel initialVessel={selectedVesselForAllocation} />
        )}

        {activeModule === 'rescheduling' && (
          <DynamicRescheduling />
        )}

        {activeModule === 'research' && (
          <ResearchObservatory />
        )}
      </main>

      {/* Footer */}
      <footer style={{
        background: 'var(--bg-darkest)',
        borderTop: '1px solid var(--border-secondary)',
        padding: '1.25rem 1.5rem',
        marginTop: 'auto',
        fontSize: '0.75rem',
        color: 'var(--text-dim)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <div style={{ maxWidth: '1600px', margin: '0 auto', width: '100%', display: 'flex', justifyContent: 'space-between' }}>
          <div>
            <strong>Smart Port Autonomous Management System</strong> | Component 1: Intelligent Vessel ETA & Dynamic Berth Allocation
          </div>
          <div>
            Geodetic Datum: WGS 84 | Reference: Port of Colombo (06°56.88'N, 079°50.70'E) | Final Year Research Thesis
          </div>
        </div>
      </footer>
    </div>
  );
}
