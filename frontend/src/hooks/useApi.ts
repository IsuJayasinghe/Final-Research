import { useCallback, useEffect, useRef, useState } from 'react'

interface ApiState<T> {
  data: T | null
  error: string | null
  loading: boolean
  reload: () => void
}

/** Load data from the API when the component mounts (and again when `deps` change). */
export function useApi<T>(load: () => Promise<T>, deps: unknown[] = []): ApiState<T> {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const requestId = useRef(0)

  const run = useCallback(load, deps)

  const reload = useCallback(() => {
    const id = ++requestId.current
    setLoading(true)
    setError(null)
    run()
      .then((result) => id === requestId.current && setData(result))
      .catch((e: Error) => id === requestId.current && setError(e.message))
      .finally(() => id === requestId.current && setLoading(false))
  }, [run])

  useEffect(() => {
    reload()
  }, [reload])

  return { data, error, loading, reload }
}
