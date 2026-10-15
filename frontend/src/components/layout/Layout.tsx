import { Outlet } from 'react-router-dom'
import { ToastProvider } from '../Toast'
import Header from './Header'

export default function Layout() {
  return (
    <ToastProvider>
      <div className="flex min-h-screen flex-col">
        <Header />
        <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-8 sm:px-6">
          <Outlet />
        </main>
        <footer className="border-t border-line bg-surface py-4 text-center text-xs text-muted">
          Smart Container Yard Allocation &amp; Space Utilization Optimization System · Smart Port Management System
        </footer>
      </div>
    </ToastProvider>
  )
}
