import { ZONE_ORDER, zoneStyle } from './theme'

// Temporary theme preview - replaced by the real layout and pages
export default function App() {
  return (
    <main className="mx-auto max-w-5xl space-y-6 p-8">
      <div>
        <h1 className="text-2xl">SmartYard</h1>
        <p className="text-sm text-muted">Smart Container Yard Allocation &amp; Space Utilization Optimization System</p>
      </div>
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {['Total containers', 'Yard occupancy', 'Arrived today', 'Overstaying'].map((label) => (
          <div key={label} className="card">
            <p className="label">{label}</p>
            <p className="mt-2 text-3xl font-bold">0</p>
          </div>
        ))}
      </div>
      <div className="card flex flex-wrap gap-2">
        {ZONE_ORDER.map((zone) => (
          <span key={zone} className={`badge ${zoneStyle[zone].badge}`}>{zone}</span>
        ))}
      </div>
      <div className="flex flex-wrap gap-3">
        <button className="btn-primary">Get AI Recommendation</button>
        <button className="btn-success">Accept Recommendation</button>
        <button className="btn-outline">Override Zone</button>
      </div>
    </main>
  )
}
