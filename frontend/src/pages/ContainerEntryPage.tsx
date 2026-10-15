import { useState } from 'react'
import { Sparkles } from 'lucide-react'
import { api } from '../api/client'
import type { AllocationResult, ArrivalRequest } from '../api/types'
import ArrivalForm from '../components/entry/ArrivalForm'
import RecommendationPanel from '../components/entry/RecommendationPanel'
import ErrorMessage from '../components/ErrorMessage'
import PageHeader from '../components/PageHeader'
import SubTabs, { CONTAINER_TABS } from '../components/SubTabs'

export default function ContainerEntryPage() {
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<AllocationResult | null>(null)
  const [formKey, setFormKey] = useState(0)          // changing it clears the form

  const submit = async (request: ArrivalRequest) => {
    setSubmitting(true)
    setError(null)
    setResult(null)
    try {
      setResult(await api.arrival(request))
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setSubmitting(false)
    }
  }

  const startNew = () => {
    setResult(null)
    setError(null)
    setFormKey((k) => k + 1)
  }

  return (
    <>
      <PageHeader title="New Container Arrival" subtitle="Enter container details to get an AI-powered zone recommendation." />
      <SubTabs tabs={CONTAINER_TABS} />
      <div className="grid items-start gap-6 lg:grid-cols-[1.4fr_1fr]">
        <ArrivalForm key={formKey} onSubmit={submit} submitting={submitting} />
        <div className="space-y-4">
          {error && <ErrorMessage message={error} />}
          {!result && !error && (
            <div className="card flex min-h-[200px] flex-col items-center justify-center gap-2 border-dashed text-center text-sm text-muted">
              <Sparkles className="text-accent" />
              <p>Fill in the container details and click <span className="text-ink">Get AI Recommendation</span>.</p>
            </div>
          )}
          {result && <RecommendationPanel key={result.allocation_id} result={result} onNew={startNew} />}
        </div>
      </div>
    </>
  )
}
