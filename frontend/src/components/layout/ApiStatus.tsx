import { useEffect, useState } from 'react'
import { api } from '../../api/client'

type Status = 'checking' | 'online' | 'no-db' | 'offline'

const LABEL: Record<Status, { text: string; dot: string }> = {
  checking: { text: 'Connecting...', dot: 'bg-muted' },
  online: { text: 'Live', dot: 'bg-ok' },
  'no-db': { text: 'Database offline', dot: 'bg-warn' },
  offline: { text: 'API offline', dot: 'bg-danger' },
}

// Small indicator in the header: is the yard API (and its database) reachable?
export default function ApiStatus() {
  const [status, setStatus] = useState<Status>('checking')

  useEffect(() => {
    const check = () =>
      api
        .health()
        .then((h) => setStatus(h.database === 'connected' ? 'online' : 'no-db'))
        .catch(() => setStatus('offline'))
    check()
    const timer = setInterval(check, 30000)
    return () => clearInterval(timer)
  }, [])

  const { text, dot } = LABEL[status]
  return (
    <span className="hidden items-center gap-2 text-xs text-muted lg:flex" title="Yard API status">
      <span className={`h-2 w-2 rounded-full ${dot}`} />
      {text}
    </span>
  )
}
