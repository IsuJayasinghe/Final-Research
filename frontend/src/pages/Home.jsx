import { ArrowRight, FileCheck2, MapPinned } from 'lucide-react'
import { Link } from 'react-router-dom'

export default function Home() {
  return (
    <div className="mx-auto max-w-5xl px-4 py-16 text-center sm:px-6 lg:px-8">
      <h1 className="text-3xl font-bold text-[#123a5c] sm:text-4xl">
        AI-Powered Multi-Gate Appointment System
      </h1>
      <p className="mx-auto mt-4 max-w-2xl text-gray-600">
        Request a gate appointment and get a lane + time slot assigned automatically,
        then pre-clear your documents before you arrive at the terminal.
      </p>

      <div className="mt-10 grid gap-6 sm:grid-cols-2">
        <Link
          to="/gate-appointment"
          className="group flex flex-col items-start gap-3 rounded-xl border border-gray-200 bg-white p-6 text-left shadow-sm transition-shadow hover:shadow-md"
        >
          <span className="flex h-11 w-11 items-center justify-center rounded-full bg-[#123a5c]/10 text-[#123a5c]">
            <MapPinned className="h-6 w-6" />
          </span>
          <span className="text-lg font-semibold text-[#123a5c]">Request Gate Appointment</span>
          <span className="text-sm text-gray-600">
            Submit your container details and get an assigned gate lane + arrival time slot.
          </span>
          <span className="flex items-center gap-1 text-sm font-medium text-[#123a5c]">
            Get started
            <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
          </span>
        </Link>

        <Link
          to="/document-upload"
          className="group flex flex-col items-start gap-3 rounded-xl border border-gray-200 bg-white p-6 text-left shadow-sm transition-shadow hover:shadow-md"
        >
          <span className="flex h-11 w-11 items-center justify-center rounded-full bg-[#123a5c]/10 text-[#123a5c]">
            <FileCheck2 className="h-6 w-6" />
          </span>
          <span className="text-lg font-semibold text-[#123a5c]">Upload Pre-Clearance Documents</span>
          <span className="text-sm text-gray-600">
            Upload booking, customs, and cargo documents ahead of your appointment window.
          </span>
          <span className="flex items-center gap-1 text-sm font-medium text-[#123a5c]">
            Upload now
            <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
          </span>
        </Link>
      </div>
    </div>
  )
}
