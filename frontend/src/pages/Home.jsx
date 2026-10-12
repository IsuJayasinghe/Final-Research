import { ArrowRight, BarChart3, CalendarClock, FileCheck2, ListChecks, MapPinned, SlidersHorizontal } from 'lucide-react'
import { Link } from 'react-router-dom'

const CARDS = [
  {
    to: '/gate-appointment',
    icon: MapPinned,
    title: 'Request Gate Appointment',
    text: 'Submit your container details. The system scores no-show risk, picks the slot and lane, and saves the booking.',
    cta: 'Get started',
  },
  {
    to: '/appointments',
    icon: ListChecks,
    title: 'My Appointments',
    text: 'Review saved bookings, confirm or cancel them, and see why each slot decision was made.',
    cta: 'View bookings',
  },
  {
    to: '/gate-optimization',
    icon: SlidersHorizontal,
    title: 'Slot Optimization',
    text: 'See hourly slot load and re-optimize unconfirmed bookings after a vessel delay or queue spike.',
    cta: 'Open optimizer',
  },
  {
    to: '/gate-allocation',
    icon: CalendarClock,
    title: 'Gate Allocation & Lanes',
    text: 'Live per-lane congestion forecast for the Port Authority operations view.',
    cta: 'Open lane monitor',
  },
  {
    to: '/model-results',
    icon: BarChart3,
    title: 'Model Results',
    text: 'Accuracy of the congestion and no-show models, SHAP drivers, and the framework evaluation.',
    cta: 'See results',
  },
  {
    to: '/document-upload',
    icon: FileCheck2,
    title: 'Upload Pre-Clearance Documents',
    text: 'Upload booking, customs, and cargo documents ahead of your appointment window.',
    cta: 'Upload now',
  },
]

export default function Home() {
  return (
    <div className="mx-auto max-w-5xl px-4 py-16 text-center sm:px-6 lg:px-8">
      <h1 className="text-3xl font-bold text-[#123a5c] sm:text-4xl">
        AI-Powered Multi-Gate Appointment System
      </h1>
      <p className="mx-auto mt-4 max-w-2xl text-gray-600">
        Predict gate congestion and no-show risk, overbook slots safely, and keep every booking
        explainable - before the truck reaches the terminal.
      </p>

      <div className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {CARDS.map(({ to, icon: Icon, title, text, cta }) => (
          <Link
            key={to}
            to={to}
            className="group flex flex-col items-start gap-3 rounded-xl border border-gray-200 bg-white p-6 text-left shadow-sm transition-shadow hover:shadow-md"
          >
            <span className="flex h-11 w-11 items-center justify-center rounded-full bg-[#123a5c]/10 text-[#123a5c]">
              <Icon className="h-6 w-6" />
            </span>
            <span className="text-lg font-semibold text-[#123a5c]">{title}</span>
            <span className="text-sm text-gray-600">{text}</span>
            <span className="mt-auto flex items-center gap-1 text-sm font-medium text-[#123a5c]">
              {cta}
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
            </span>
          </Link>
        ))}
      </div>
    </div>
  )
}
