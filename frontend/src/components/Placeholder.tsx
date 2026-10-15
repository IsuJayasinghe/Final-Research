// Shown on pages that are not built yet
export default function Placeholder({ text }: { text: string }) {
  return (
    <div className="card flex min-h-[240px] items-center justify-center border-dashed text-sm text-muted">{text}</div>
  )
}
