import { lazy } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/layout/Layout'

// Pages load on demand so the first screen opens quickly (charts are only loaded where used)
const DashboardPage = lazy(() => import('./pages/DashboardPage'))
const ContainerTrackingPage = lazy(() => import('./pages/ContainerTrackingPage'))
const ContainerEntryPage = lazy(() => import('./pages/ContainerEntryPage'))
const DwellPredictionPage = lazy(() => import('./pages/DwellPredictionPage'))
const OccupancyForecastPage = lazy(() => import('./pages/OccupancyForecastPage'))
const YardMapPage = lazy(() => import('./pages/YardMapPage'))
const ReportsPage = lazy(() => import('./pages/ReportsPage'))
const AlertsPage = lazy(() => import('./pages/AlertsPage'))
const NotFoundPage = lazy(() => import('./pages/NotFoundPage'))

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<DashboardPage />} />
          <Route path="containers" element={<ContainerTrackingPage />} />
          <Route path="containers/new" element={<ContainerEntryPage />} />
          <Route path="predictions" element={<Navigate to="/predictions/dwell" replace />} />
          <Route path="predictions/dwell" element={<DwellPredictionPage />} />
          <Route path="predictions/occupancy" element={<OccupancyForecastPage />} />
          <Route path="yard-map" element={<YardMapPage />} />
          <Route path="reports" element={<ReportsPage />} />
          <Route path="alerts" element={<AlertsPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
