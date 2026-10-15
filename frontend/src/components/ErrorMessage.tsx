import { AlertTriangle, RotateCw } from 'lucide-react'

export default function ErrorMessage({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex flex-wrap items-center gap-3 rounded-xl border border-danger/40 bg-danger/10 p-4 text-sm text-danger">
      <AlertTriangle size={18} />
      <span className="flex-1">{message}</span>
      {onRetry && (
        <button onClick={onRetry} className="btn-ghost py-1 text-ink">
          <RotateCw size={14} /> Retry
        </button>
      )}
    </div>
  )
}
