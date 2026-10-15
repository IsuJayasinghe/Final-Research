import { Loader2 } from 'lucide-react'

export default function Loading({ text = 'Loading...' }: { text?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-12 text-sm text-muted">
      <Loader2 size={18} className="animate-spin text-accent" />
      {text}
    </div>
  )
}
