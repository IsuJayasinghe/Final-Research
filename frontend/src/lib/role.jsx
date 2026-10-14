import { createContext, useCallback, useContext, useMemo, useState } from 'react'

// Who is using the app: a driver (books, waits for approval, uploads documents, follows the trip) or the gate admin
// (approves requests, watches the gate, handles disruptions). This is a demo switch, not authentication: a real
// deployment would sign users in through the team's shared backend.

const RoleContext = createContext(null)

function read(key, fallback) {
  try {
    return localStorage.getItem(key) ?? fallback
  } catch {
    return fallback
  }
}

function write(key, value) {
  try {
    localStorage.setItem(key, value)
  } catch {
    // storage unavailable (private window): the choice just lasts until reload
  }
}

export function RoleProvider({ children }) {
  const [role, setRoleState] = useState(() => (read('gateRole', 'driver') === 'admin' ? 'admin' : 'driver'))
  const [myTruck, setMyTruckState] = useState(() => read('gateMyTruck', ''))

  const setRole = useCallback((next) => {
    setRoleState(next)
    write('gateRole', next)
  }, [])

  const setMyTruck = useCallback((truck) => {
    const clean = (truck ?? '').trim().toUpperCase()
    setMyTruckState(clean)
    write('gateMyTruck', clean)
  }, [])

  const value = useMemo(() => ({ role, setRole, myTruck, setMyTruck }), [role, setRole, myTruck, setMyTruck])
  return <RoleContext.Provider value={value}>{children}</RoleContext.Provider>
}

export function useRole() {
  const ctx = useContext(RoleContext)
  if (!ctx) throw new Error('useRole must be used inside <RoleProvider>')
  return ctx
}

// Pages that only make sense for the gate admin: a driver sees a clear message instead of admin controls.
export function AdminOnly({ children }) {
  const { role, setRole } = useRole()
  if (role === 'admin') return children
  return (
    <div className="mx-auto max-w-2xl px-4 py-16 text-center">
      <h1 className="text-xl font-bold text-[#123a5c]">This page is for the gate admin</h1>
      <p className="mt-2 text-sm text-gray-600">
        Drivers book, follow their trip and upload documents. Approving requests and handling the gate is done by the
        gate admin.
      </p>
      <button
        type="button"
        onClick={() => setRole('admin')}
        className="mt-5 rounded-md bg-[#123a5c] px-4 py-2 text-sm font-semibold text-white hover:bg-[#0e2d47]"
      >
        Switch to Gate admin
      </button>
    </div>
  )
}
