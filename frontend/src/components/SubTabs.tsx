import { NavLink } from 'react-router-dom'

interface Props {
  tabs: { to: string; label: string }[]
}

// Second-level navigation for sections with more than one page (Containers, Predictions)
export default function SubTabs({ tabs }: Props) {
  return (
    <div className="mb-6 flex gap-1 overflow-x-auto rounded-lg border border-line bg-surface p-1">
      {tabs.map(({ to, label }) => (
        <NavLink
          key={to}
          to={to}
          end
          className={({ isActive }) =>
            `whitespace-nowrap rounded-md px-4 py-1.5 text-sm transition ${
              isActive ? 'bg-card text-accent shadow' : 'text-muted hover:text-ink'
            }`
          }
        >
          {label}
        </NavLink>
      ))}
    </div>
  )
}

export const CONTAINER_TABS = [
  { to: '/containers', label: 'Container Tracking' },
  { to: '/containers/new', label: 'New Arrival' },
]

export const PREDICTION_TABS = [
  { to: '/predictions/dwell', label: 'Dwell Time' },
  { to: '/predictions/occupancy', label: 'Yard Occupancy' },
]
