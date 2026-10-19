import React from 'react';
import { 
  BarChart3, 
  Binary, 
  CheckCircle2, 
  ShieldCheck, 
  Award, 
  FileText, 
  Compass, 
  Layers, 
  Cpu
} from 'lucide-react';

export default function ResearchObservatory() {
  const etaMetrics = {
    mae: '8.5714 hrs',
    rmse: '9.9600 hrs',
    mse: '99.2024',
    r2: '0.4707',
    samples: '344 test instances (20% split)',
    features: ['Speed Over Ground (SOG)', 'Distance to Port (nmi)', 'Draft (m)', 'Wind Speed (knots)', 'Wave Height (m)']
  };

  const feasibilityMetrics = {
    accuracy: '99.00%',
    precision: '0.9903',
    recall: '0.9900',
    f1: '0.9900',
    rocAuc: '0.9999',
    classes: ['Feasible', 'Conditionally Feasible', 'Infeasible'],
    cm: [
      [97, 0, 3],
      [0, 114, 0],
      [0, 0, 86]
    ]
  };

  const delayMetrics = {
    accuracy: '78.78%',
    precision: '1.0000 (100.0%)',
    recall: '0.6798',
    f1: '0.8094',
    rocAuc: '0.9747',
    cm: [
      [116, 0],
      [73, 155]
    ]
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Research Header Banner */}
      <div className="panel-card" style={{ background: 'linear-gradient(135deg, rgba(2, 132, 199, 0.12) 0%, rgba(12, 20, 43, 0.85) 100%)' }}>
        <div className="card-body" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '4px' }}>
              <Award size={20} color="#38bdf8" />
              <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#f8fafc' }}>
                Academic Research Model Observatory & Rigorous Benchmark Suite
              </h2>
            </div>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
              Component 1: Intelligent Vessel ETA Prediction & Dynamic Berth Allocation Framework | 4th-Year Undergraduate Research Thesis
            </p>
          </div>
          <span className="badge badge-feasible" style={{ padding: '0.4rem 0.85rem' }}>
            <CheckCircle2 size={14} /> Production Audited
          </span>
        </div>
      </div>

      {/* Grid of ML Performance Metrics */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.25rem' }}>
        {/* 1. Continuous ETA Regression */}
        <div className="panel-card">
          <div className="card-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Cpu size={18} color="#38bdf8" />
              <h3 style={{ fontSize: '0.95rem', fontWeight: 600 }}>1. Continuous Voyage ETA Travel-Time Regression</h3>
            </div>
            <span className="badge badge-ocean">Gradient Boosting & RF</span>
          </div>

          <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.75rem' }}>
              <div style={{ background: 'var(--bg-card-secondary)', padding: '0.75rem', borderRadius: '8px', border: '1px solid var(--border-secondary)' }}>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Mean Absolute Error (MAE)</div>
                <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#38bdf8', marginTop: '2px' }}>{etaMetrics.mae}</div>
                <div style={{ fontSize: '0.68rem', color: 'var(--text-dim)' }}>Average residual error</div>
              </div>

              <div style={{ background: 'var(--bg-card-secondary)', padding: '0.75rem', borderRadius: '8px', border: '1px solid var(--border-secondary)' }}>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Root Mean Squared Error</div>
                <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#38bdf8', marginTop: '2px' }}>{etaMetrics.rmse}</div>
                <div style={{ fontSize: '0.68rem', color: 'var(--text-dim)' }}>Penalizes large variance</div>
              </div>

              <div style={{ background: 'var(--bg-card-secondary)', padding: '0.75rem', borderRadius: '8px', border: '1px solid var(--border-secondary)' }}>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Mean Squared Error (MSE)</div>
                <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#cbd5e1', marginTop: '2px' }}>{etaMetrics.mse}</div>
                <div style={{ fontSize: '0.68rem', color: 'var(--text-dim)' }}>Baseline variance metric</div>
              </div>

              <div style={{ background: 'var(--bg-card-secondary)', padding: '0.75rem', borderRadius: '8px', border: '1px solid var(--border-secondary)' }}>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Coefficient of Determination (R²)</div>
                <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#10b981', marginTop: '2px' }}>{etaMetrics.r2}</div>
                <div style={{ fontSize: '0.68rem', color: 'var(--text-dim)' }}>Explained voyage variance</div>
              </div>
            </div>

            <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', background: 'rgba(255,255,255,0.02)', padding: '0.75rem', borderRadius: '8px' }}>
              <strong>Regression Input Feature Vector:</strong>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem', marginTop: '6px' }}>
                {etaMetrics.features.map((f, i) => (
                  <span key={i} className="badge" style={{ background: 'rgba(56, 189, 248, 0.1)', color: '#38bdf8' }}>
                    {f}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* 2. Berth Operational Feasibility Classifier */}
        <div className="panel-card">
          <div className="card-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <ShieldCheck size={18} color="#10b981" />
              <h3 style={{ fontSize: '0.95rem', fontWeight: 600 }}>2. Berth Feasibility 3-State Classifier</h3>
            </div>
            <span className="badge badge-feasible">Multi-Class OvR</span>
          </div>

          <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.75rem' }}>
              <div style={{ background: 'var(--bg-card-secondary)', padding: '0.75rem', borderRadius: '8px', border: '1px solid var(--border-secondary)' }}>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Accuracy</div>
                <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#10b981', marginTop: '2px' }}>{feasibilityMetrics.accuracy}</div>
                <div style={{ fontSize: '0.68rem', color: 'var(--text-dim)' }}>Overall classification</div>
              </div>

              <div style={{ background: 'var(--bg-card-secondary)', padding: '0.75rem', borderRadius: '8px', border: '1px solid var(--border-secondary)' }}>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Weighted F1-Score</div>
                <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#10b981', marginTop: '2px' }}>{feasibilityMetrics.f1}</div>
                <div style={{ fontSize: '0.68rem', color: 'var(--text-dim)' }}>Harmonic balance</div>
              </div>

              <div style={{ background: 'var(--bg-card-secondary)', padding: '0.75rem', borderRadius: '8px', border: '1px solid var(--border-secondary)' }}>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Multi-Class ROC-AUC</div>
                <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#38bdf8', marginTop: '2px' }}>{feasibilityMetrics.rocAuc}</div>
                <div style={{ fontSize: '0.68rem', color: 'var(--text-dim)' }}>One-vs-Rest AUC</div>
              </div>
            </div>

            {/* Confusion Matrix Table */}
            <div style={{ background: 'var(--bg-card-secondary)', padding: '0.75rem', borderRadius: '8px', border: '1px solid var(--border-secondary)' }}>
              <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#cbd5e1', marginBottom: '6px' }}>
                Confusion Matrix [Rows: Ground Truth, Columns: Model Prediction]
              </div>
              <table style={{ width: '100%', fontSize: '0.72rem', borderCollapse: 'collapse', textAlign: 'center' }}>
                <thead>
                  <tr style={{ color: 'var(--text-muted)', borderBottom: '1px solid var(--border-secondary)' }}>
                    <th style={{ textAlign: 'left', padding: '4px' }}>Actual \ Pred</th>
                    <th style={{ padding: '4px' }}>Cond. Feasible</th>
                    <th style={{ padding: '4px' }}>Feasible</th>
                    <th style={{ padding: '4px' }}>Infeasible</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td style={{ textAlign: 'left', color: '#f59e0b', fontWeight: 600, padding: '4px' }}>Cond. Feasible</td>
                    <td style={{ color: '#10b981', fontWeight: 700 }}>97</td>
                    <td>0</td>
                    <td>3</td>
                  </tr>
                  <tr>
                    <td style={{ textAlign: 'left', color: '#10b981', fontWeight: 600, padding: '4px' }}>Feasible</td>
                    <td>0</td>
                    <td style={{ color: '#10b981', fontWeight: 700 }}>114</td>
                    <td>0</td>
                  </tr>
                  <tr>
                    <td style={{ textAlign: 'left', color: '#f43f5e', fontWeight: 600, padding: '4px' }}>Infeasible</td>
                    <td>0</td>
                    <td>0</td>
                    <td style={{ color: '#10b981', fontWeight: 700 }}>86</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      {/* 3. Delay Risk Operational Classifier */}
      <div className="panel-card">
        <div className="card-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <BarChart3 size={18} color="#f59e0b" />
            <h3 style={{ fontSize: '0.95rem', fontWeight: 600 }}>3. Delay & Operational Disruption Risk Classifier</h3>
          </div>
          <span className="badge badge-conditionally">Unbooking Decision Engine</span>
        </div>

        <div className="card-body">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem' }}>
            <div style={{ background: 'var(--bg-card-secondary)', padding: '0.85rem', borderRadius: '8px', border: '1px solid var(--border-secondary)' }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Precision (Positive Class)</div>
              <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#10b981', marginTop: '2px' }}>{delayMetrics.precision}</div>
              <div style={{ fontSize: '0.68rem', color: 'var(--text-dim)' }}>Zero false unbooking triggers</div>
            </div>

            <div style={{ background: 'var(--bg-card-secondary)', padding: '0.85rem', borderRadius: '8px', border: '1px solid var(--border-secondary)' }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>ROC-AUC Metric</div>
              <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#38bdf8', marginTop: '2px' }}>{delayMetrics.rocAuc}</div>
              <div style={{ fontSize: '0.68rem', color: 'var(--text-dim)' }}>High risk discriminatory power</div>
            </div>

            <div style={{ background: 'var(--bg-card-secondary)', padding: '0.85rem', borderRadius: '8px', border: '1px solid var(--border-secondary)' }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Harmonic F1-Score</div>
              <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#10b981', marginTop: '2px' }}>{delayMetrics.f1}</div>
              <div style={{ fontSize: '0.68rem', color: 'var(--text-dim)' }}>F-measure balance</div>
            </div>

            <div style={{ background: 'var(--bg-card-secondary)', padding: '0.85rem', borderRadius: '8px', border: '1px solid var(--border-secondary)' }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Reallocation Threshold Policy</div>
              <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#f43f5e', marginTop: '2px' }}>&ge; 65% Prob</div>
              <div style={{ fontSize: '0.68rem', color: 'var(--text-dim)' }}>Or wind &ge; 28 kts, wave &ge; 3m</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
