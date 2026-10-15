import { Link } from 'react-router-dom'

export default function NotFoundPage() {
  return (
    <div className="card mx-auto max-w-md text-center">
      <p className="text-4xl font-bold text-accent">404</p>
      <p className="mt-2 text-sm text-muted">This page does not exist.</p>
      <Link to="/" className="btn-primary mt-6">Back to dashboard</Link>
    </div>
  )
}
