import { useEffect, useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { Bell } from 'lucide-react'
import { api } from '../../api/client'

// Header bell with the number of active capacity alerts (FR08), refreshed every minute
export default function AlertBell() {
  const [count, setCount] = useState(0)
  const { pathname } = useLocation()

  useEffect(() => {
    const check = () => api.alerts().then((r) => setCount(r.alerts.length)).catch(() => setCount(0))
    check()
    const timer = setInterval(check, 60000)
    return () => clearInterval(timer)
  }, [pathname])

  return (
    <NavLink to="/alerts" className="relative rounded-lg p-2 text-muted hover:bg-card hover:text-ink"
             aria-label={`Alerts (${count})`} title={count ? `${count} capacity alert(s)` : 'No alerts'}>
      <Bell size={18} />
      {count > 0 && (
        <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-danger px-1 text-[10px] font-bold text-white">
          {count > 9 ? '9+' : count}
        </span>
      )}
    </NavLink>
  )
}
