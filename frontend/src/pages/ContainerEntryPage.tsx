import { useState } from 'react'
import { Sparkles } from 'lucide-react'
import { api } from '../api/client'
import type { AllocationResult, ArrivalRequest } from '../api/types'
import ArrivalForm from '../components/entry/ArrivalForm'
import ErrorMessage from '../components/ErrorMessage'
import PageHeader from '../components/PageHeader'
import SubTabs, { CONTAINER_TABS } from '../components/SubTabs'
import { formatDays } from '../utils/format'

export default function ContainerEntryPage() {
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<AllocationResult | null>(null)

  const submit = async (request: ArrivalRequest) => {
    setSubmitting(true)
    setError(null)
    try {
      setResult(await api.arrival(request))
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <>
      <PageHeader title="New Container Arrival" subtitle="Enter container details to get an AI-powered zone recommendation." />
      <SubTabs tabs={CONTAINER_TABS} />
      <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
        <ArrivalForm onSubmit={submit} submitting={submitting} />
        <div className="space-y-4">
          {error && <ErrorMessage message={error} />}
          {!result && !error && (
            <div className="card flex min-h-[200px] flex-col items-center justify-center gap-2 border-dashed text-center text-sm text-muted">
              <Sparkles className="text-accent" />
              <p>Fill in the container details and click <span className="text-ink">Get AI Recommendation</span>.</p>
            </div>
          )}
          {result && (
            <div className="card">
              <p className="label">AI recommendation</p>
              <p className="mt-2 text-2xl font-bold">{result.recommended_zone} · {result.slot}</p>
              <p className="mt-1 text-sm text-muted">
                {result.container_id} · predicted dwell {formatDays(result.predicted_dwell_days)}
              </p>
            </div>
          )}
        </div>
      </div>
    </>
  )
}
