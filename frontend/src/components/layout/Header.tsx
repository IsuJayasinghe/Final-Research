import { useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { BarChart3, Container, FileText, LineChart, Map, Menu, Ship, X } from 'lucide-react'
import AlertBell from './AlertBell'
import ApiStatus from './ApiStatus'

const NAV = [
  { to: '/', label: 'Dashboard', icon: BarChart3, match: (p: string) => p === '/' },
  { to: '/containers', label: 'Containers', icon: Container, match: (p: string) => p.startsWith('/containers') },
  { to: '/predictions/dwell', label: 'Predictions', icon: LineChart, match: (p: string) => p.startsWith('/predictions') },
  { to: '/yard-map', label: 'Yard Map', icon: Map, match: (p: string) => p.startsWith('/yard-map') },
  { to: '/reports', label: 'Reports', icon: FileText, match: (p: string) => p.startsWith('/reports') },
]

export default function Header() {
  const { pathname } = useLocation()
  const [open, setOpen] = useState(false)

  const links = NAV.map(({ to, label, icon: Icon, match }) => {
    const active = match(pathname)
    return (
      <NavLink
        key={to}
        to={to}
        onClick={() => setOpen(false)}
        className={`flex items-center gap-2 border-b-2 px-1 py-2 text-sm transition ${
          active ? 'border-accent text-accent' : 'border-transparent text-muted hover:text-ink'
        }`}
      >
        <Icon size={16} />
        {label}
      </NavLink>
    )
  })

  return (
    <header className="sticky top-0 z-30 border-b border-line bg-surface/95 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-7xl items-center gap-6 px-4 sm:px-6">
        <NavLink to="/" className="flex items-center gap-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent-soft text-accent">
            <Ship size={20} />
          </span>
          <span className="leading-tight">
            <span className="block text-base font-bold">SmartYard</span>
            <span className="block text-[11px] text-accent">AI-Powered</span>
          </span>
        </NavLink>

        <nav className="hidden flex-1 justify-center gap-6 md:flex">{links}</nav>

        <div className="ml-auto flex items-center gap-3 md:ml-0">
          <ApiStatus />
          <AlertBell />
          <span className="hidden rounded-full border border-line px-3 py-1 text-xs sm:inline">Yard Manager</span>
          <button className="rounded-lg p-2 text-muted hover:bg-card md:hidden" onClick={() => setOpen(!open)} aria-label="Menu">
            {open ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </div>
      {open && <nav className="flex flex-col gap-1 border-t border-line px-4 py-2 md:hidden">{links}</nav>}
    </header>
  )
}
