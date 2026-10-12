import { Route, Routes } from 'react-router-dom'
import Footer from './components/Footer'
import Navbar from './components/Navbar'
import DocumentUpload from './pages/gate/DocumentUpload'
import GateAllocationView from './pages/gate/GateAllocationView'
import GateAppointment from './pages/gate/GateAppointment'
import Home from './pages/Home'

function App() {
  return (
    <div className="flex min-h-screen flex-col bg-gray-200">
      <Navbar />
      <main className="flex-1 bg-white">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/gate-appointment" element={<GateAppointment />} />
          <Route path="/document-upload" element={<DocumentUpload />} />
          <Route path="/gate-allocation" element={<GateAllocationView />} />
        </Routes>
      </main>
      <Footer />
    </div>
  )
}

export default App
