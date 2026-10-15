import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/layout/Layout'
import AlertsPage from './pages/AlertsPage'
import ContainerEntryPage from './pages/ContainerEntryPage'
import ContainerTrackingPage from './pages/ContainerTrackingPage'
import DashboardPage from './pages/DashboardPage'
import DwellPredictionPage from './pages/DwellPredictionPage'
import NotFoundPage from './pages/NotFoundPage'
import OccupancyForecastPage from './pages/OccupancyForecastPage'
import ReportsPage from './pages/ReportsPage'
import YardMapPage from './pages/YardMapPage'

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
