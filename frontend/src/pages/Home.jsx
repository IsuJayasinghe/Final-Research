import {
  ArrowRight,
  BarChart3,
  CalendarClock,
  ClipboardCheck,
  DoorOpen,
  FileCheck2,
  ListChecks,
  MapPinned,
  Navigation,
  SlidersHorizontal,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { useRole } from '../lib/role'

const DRIVER_CARDS = [
  {
    to: '/gate-allocation',
    icon: CalendarClock,
    title: '1. Check the gate',
    text: 'See how busy each hour is expected to be, and pick a quieter time.',
    cta: 'See gate status',
  },
  {
    to: '/gate-appointment',
    icon: MapPinned,
    title: '2. Request an appointment',
    text: 'Choose your hour and enter your truck. The gate admin then reviews your request.',
    cta: 'Get started',
  },
  {
    to: '/document-upload',
    icon: FileCheck2,
    title: '3. Upload documents',
    text: 'Opens once your request is approved. Each document is read and checked straight away.',
    cta: 'Upload now',
  },
  {
    to: '/my-trip',
    icon: Navigation,
    title: '4. Follow your trip live',
    text: 'Your gate, the queue at your hour, delays and any gate change, with the reason.',
    cta: 'Open My Trip',
  },
]

const ADMIN_CARDS = [
  {
    to: '/admin/approvals',
    icon: ClipboardCheck,
    title: 'Approvals',
    text: 'Review driver requests with their risk and the hour load. Approve or reject with a reason.',
    cta: 'Review requests',
  },
  {
    to: '/admin/gate-desk',
    icon: DoorOpen,
    title: 'Gate Desk',
    text: 'Pick your gate, see its approved trucks in slot order, check them in and complete the gate process.',
    cta: 'Open my gate',
  },
  {
    to: '/gate-allocation',
    icon: CalendarClock,
    title: 'Gate Allocation & Lanes',
    text: 'Forecast congestion per lane and hour, the booked trucks, lane closures and rebalancing.',
    cta: 'Open lane monitor',
  },
  {
    to: '/gate-optimization',
    icon: SlidersHorizontal,
    title: 'Slot Optimization',
    text: 'Hourly slot load. Inject a vessel delay or a queue spike on the gate or one lane.',
    cta: 'Open optimizer',
  },
  {
    to: '/appointments',
    icon: ListChecks,
    title: 'All Appointments',
    text: 'Every request with its decision reason and full history.',
    cta: 'View all',
  },
  {
    to: '/model-results',
    icon: BarChart3,
    title: 'Model Results',
    text: 'Accuracy of the congestion and no-show models, SHAP drivers, and the framework evaluation.',
    cta: 'See results',
  },
]

export default function Home() {
  const { role } = useRole()
  const cards = role === 'admin' ? ADMIN_CARDS : DRIVER_CARDS

  return (
    <div className="mx-auto max-w-5xl px-4 py-16 text-center sm:px-6 lg:px-8">
      <h1 className="text-3xl font-bold text-[#123a5c] sm:text-4xl">AI-Powered Multi-Gate Appointment System</h1>
      <p className="mx-auto mt-4 max-w-2xl text-gray-600">
        {role === 'admin'
          ? 'Approve driver requests and run the gate: predicted congestion, no-show-aware overbooking, automatic gate changes and delay notices.'
          : 'Check the gate, book a slot, upload your documents once approved, and follow your trip live - with the reason for any delay or gate change.'}
      </p>
      <p className="mt-2 text-xs font-medium uppercase tracking-wide text-[#123a5c]/70">
        Viewing as {role === 'admin' ? 'gate admin' : 'driver'} - switch in the top bar
      </p>

      <div className={`mt-10 grid gap-6 sm:grid-cols-2 ${role === 'admin' ? 'lg:grid-cols-3' : 'lg:grid-cols-4'}`}>
        {cards.map(({ to, icon: Icon, title, text, cta }) => (
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
