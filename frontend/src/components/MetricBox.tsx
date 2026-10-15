export default function MetricBox({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className="rounded-lg border border-line bg-surface px-3 py-3 text-center">
      <p className="label">{label}</p>
      <p className={`mt-1 text-lg font-bold ${highlight ? 'text-ok' : ''}`}>{value}</p>
    </div>
  )
}
