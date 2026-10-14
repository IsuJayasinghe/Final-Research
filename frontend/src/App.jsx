import { Route, Routes } from 'react-router-dom'
import Footer from './components/Footer'
import Navbar from './components/Navbar'
import Appointments from './pages/gate/Appointments'
import Approvals from './pages/gate/Approvals'
import DocumentUpload from './pages/gate/DocumentUpload'
import GateAllocationView from './pages/gate/GateAllocationView'
import GateAppointment from './pages/gate/GateAppointment'
import ModelResults from './pages/gate/ModelResults'
import MyTrip from './pages/gate/MyTrip'
import Optimization from './pages/gate/Optimization'
import { AdminOnly } from './lib/role'
import Home from './pages/Home'

function App() {
  return (
    <div className="flex min-h-screen flex-col bg-gray-200">
      <Navbar />
      <main className="flex-1 bg-white">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/gate-appointment" element={<GateAppointment />} />
          <Route path="/appointments" element={<AdminOnly><Appointments /></AdminOnly>} />
          <Route path="/admin/approvals" element={<AdminOnly><Approvals /></AdminOnly>} />
          <Route path="/my-trip" element={<MyTrip />} />
          <Route path="/gate-optimization" element={<AdminOnly><Optimization /></AdminOnly>} />
          <Route path="/model-results" element={<AdminOnly><ModelResults /></AdminOnly>} />
          <Route path="/document-upload" element={<DocumentUpload />} />
          <Route path="/gate-allocation" element={<GateAllocationView />} />
        </Routes>
      </main>
      <Footer />
    </div>
  )
}

export default App
