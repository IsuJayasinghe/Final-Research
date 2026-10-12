import { Anchor, Bell, ChevronDown, Search, User } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'

const NAV_LINKS = [
  { label: 'Home', to: '/' },
  { label: 'Solutions', dropdown: true },
  { label: 'Features', to: '/#features' },
  { label: 'Contact', to: '/#contact' },
  { label: 'About', to: '/#about' },
]

const SOLUTIONS = [
  { label: 'Gate Appointment', to: '/gate-appointment' },
  { label: 'Document Upload', to: '/document-upload' },
  { label: 'Gate Allocation (Port Authority)', to: '/gate-allocation' },
]

export default function Navbar() {
  const [solutionsOpen, setSolutionsOpen] = useState(false)

  return (
    <header className="bg-[#123a5c] text-white">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
        {/* Brand */}
        <Link to="/" className="flex items-center gap-2 shrink-0">
          <Anchor className="h-6 w-6" strokeWidth={2} />
          <span className="leading-tight">
            <span className="block text-sm font-bold tracking-wide">SMART PORT</span>
            <span className="block text-[10px] font-medium tracking-wide text-white/70">
              AI MANAGEMENT SYSTEM
            </span>
          </span>
        </Link>

        {/* Nav links */}
        <nav className="hidden md:flex items-center gap-8">
          {NAV_LINKS.map((link) =>
            link.dropdown ? (
              <div
                key={link.label}
                className="relative"
                onMouseEnter={() => setSolutionsOpen(true)}
                onMouseLeave={() => setSolutionsOpen(false)}
              >
                <button
                  type="button"
                  className="flex items-center gap-1 text-sm font-medium text-white/90 transition-colors hover:text-white"
                  aria-expanded={solutionsOpen}
                >
                  {link.label}
                  <ChevronDown className="h-4 w-4" />
                </button>
                {solutionsOpen && (
                  <div className="absolute left-0 top-full w-56 rounded-md bg-white py-2 text-[#123a5c] shadow-lg">
                    {SOLUTIONS.map((item) => (
                      <Link
                        key={item.label}
                        to={item.to}
                        className="block px-4 py-2 text-sm hover:bg-gray-100"
                      >
                        {item.label}
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <Link
                key={link.label}
                to={link.to}
                className="text-sm font-medium text-white/90 transition-colors hover:text-white"
              >
                {link.label}
              </Link>
            ),
          )}
        </nav>

        {/* Right side: search, notifications, profile */}
        <div className="flex items-center gap-4">
          <div className="relative hidden sm:block">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#123a5c]/60" />
            <input
              type="search"
              placeholder="Search"
              className="w-48 lg:w-64 rounded-full bg-[#cfe0f0] py-2 pl-9 pr-4 text-sm text-[#123a5c] placeholder-[#123a5c]/60 outline-none focus:ring-2 focus:ring-white/50"
            />
          </div>

          <button
            type="button"
            aria-label="Notifications"
            className="relative flex h-8 w-8 items-center justify-center rounded-full transition-colors hover:bg-white/10"
          >
            <Bell className="h-5 w-5" />
            <span className="absolute -top-0.5 -right-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[10px] font-semibold leading-none">
              0
            </span>
          </button>

          <button
            type="button"
            aria-label="Profile"
            className="flex h-9 w-9 items-center justify-center rounded-full bg-white text-[#123a5c] transition-opacity hover:opacity-90"
          >
            <User className="h-5 w-5" />
          </button>
        </div>
      </div>
    </header>
  )
}
