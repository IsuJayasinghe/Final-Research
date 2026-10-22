import { AlertTriangle, CheckCircle2, CircleDashed, FileWarning, XCircle } from 'lucide-react'
import { dayAndHour } from '../../lib/status'

const WEATHER = ['clear', 'light rain', 'heavy rain', 'storm']

const DOC_STATUS = {
  cleared: { label: 'Cleared', style: 'bg-green-50 text-green-700', icon: CheckCircle2 },
  flagged: { label: 'Flagged', style: 'bg-red-50 text-red-700', icon: XCircle },
  unreadable: { label: 'Unreadable', style: 'bg-red-50 text-red-700', icon: FileWarning },
  missing: { label: 'Not uploaded', style: 'bg-gray-100 text-gray-500', icon: CircleDashed },
}

const pct = (v) => (v === null || v === undefined ? '--' : `${Math.round(v * 100)}%`)

function Fact({ label, children }) {
  return (
    <div className="min-w-0">
      <p className="text-[11px] uppercase tracking-wide text-gray-400">{label}</p>
      <p className="mt-0.5 break-words text-sm font-medium text-gray-800">{children ?? '--'}</p>
    </div>
  )
}

function DocumentCard({ doc }) {
  const status = DOC_STATUS[doc.status] ?? DOC_STATUS.missing
  const Icon = status.icon
  return (
    <li className="rounded-lg border border-gray-200 bg-white p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-semibold text-[#123a5c]">{doc.label}</p>
        <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${status.style}`}>
          <Icon className="h-3.5 w-3.5" />
          {status.label}
        </span>
      </div>
      {doc.filename && (
        <p className="mt-1 text-xs text-gray-500">
          {doc.filename} · OCR {pct(doc.ocr_confidence)}
          {doc.completeness !== null && doc.completeness !== undefined && <> · {pct(doc.completeness)} of the required details found</>}
        </p>
      )}
      {doc.details.length > 0 && (
        <dl className="mt-2 grid gap-x-4 gap-y-1 text-xs sm:grid-cols-2">
          {doc.details
            .filter((d) => d.value || d.required)
            .map((d) => (
              <div key={d.label} className="flex gap-1.5">
                <dt className="shrink-0 text-gray-500">{d.label}:</dt>
                <dd className={`break-words font-medium ${d.status === 'ok' ? 'text-gray-800' : 'text-red-600'}`}>
                  {d.value ?? 'missing'}
                </dd>
              </div>
            ))}
        </dl>
      )}
      {doc.customs && (
        <p className="mt-2 text-xs text-gray-700">
          <b>Customs risk {doc.customs.level}.</b> {doc.customs.reasons.join(' ')}
        </p>
      )}
      {doc.issues.length > 0 && (
        <ul className="mt-2 space-y-0.5 text-xs">
          {doc.issues.map((i, n) => (
            <li key={n} className={i.level === 'error' ? 'text-red-600' : 'text-amber-600'}>
              {i.level === 'error' ? 'Problem' : 'Note'}: {i.message}
            </li>
          ))}
        </ul>
      )}
    </li>
  )
}

/** The full booking and its uploaded documents, for the gate officer. */
export default function BookingDetails({ b }) {
  const summary = b.document_summary
  // what the uploaded documents say, before the driver has submitted them (submitting updates the booking itself)
  const readVessel = summary.documents.find((d) => d.doc_key === 'booking_confirmation')?.details.find((x) => x.label === 'Vessel name')?.value
  const readCustoms = summary.documents.find((d) => d.doc_key === 'cusdec')?.customs?.level
  return (
    <div className="border-t border-gray-100 bg-gray-50 p-4">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-500">Booking details</h3>
      <div className="mt-2 grid gap-3 sm:grid-cols-3 lg:grid-cols-4">
        <Fact label="Request">#{b.id}, made {dayAndHour(b.created_at)}</Fact>
        <Fact label="Truck">{b.truck_id}</Fact>
        <Fact label="Container">{b.container_id}</Fact>
        <Fact label="Carrier">
          {b.carrier} (reliability {pct(b.carrier_reliability)})
        </Fact>
        <Fact label="Cargo">
          {b.container_type}, {b.cargo_category}
        </Fact>
        <Fact label="Slot">
          {dayAndHour(b.assigned_slot)}, Gate {b.lane}
          {b.assigned_slot !== b.requested_slot && <> (asked {dayAndHour(b.requested_slot)})</>}
        </Fact>
        <Fact label="Vessel">
          {b.vessel_name
            ? `${b.vessel_name}: ${b.vessel_delay ? `delayed ${b.vessel_delay_hours ?? ''} h` : 'on schedule'}`
            : readVessel
              ? `${readVessel} (read from the booking confirmation; the schedule is checked when the driver submits)`
              : 'not known yet (needs the booking confirmation)'}
        </Fact>
        <Fact label="Weather">{b.weather_severity === null ? 'not known' : WEATHER[b.weather_severity]}</Fact>
        <Fact label="Customs risk">
          {b.customs_risk_flag ??
            (readCustoms ? `${readCustoms} (read from the customs declaration; applied when the driver submits)` : 'not known yet (needs the customs declaration)')}
        </Fact>
        <Fact label="No-show / late risk">
          {pct(b.p_no_show)} / {pct(b.p_late)}
        </Fact>
        <Fact label="Predicted clearance">{b.predicted_clearance_minutes ? `${Math.round(b.predicted_clearance_minutes)} min` : '--'}</Fact>
        <Fact label="Overbooked slot">{b.overbooked ? 'yes' : 'no'}</Fact>
      </div>
      {b.decision_reason && <p className="mt-2 text-xs text-gray-600">Why this slot: {b.decision_reason}</p>}
      {b.risk_summary && <p className="mt-1 text-xs text-gray-500">{b.risk_summary}</p>}

      <h3 className="mt-5 text-xs font-semibold uppercase tracking-wide text-gray-500">
        Uploaded documents ({summary.cleared} of {summary.total} cleared)
      </h3>
      {summary.cross_checks.length > 0 && (
        <div className="mt-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">
          <p className="flex items-center gap-1.5 font-semibold">
            <AlertTriangle className="h-3.5 w-3.5" />
            The documents disagree with each other
          </p>
          <ul className="mt-1 list-disc space-y-0.5 pl-5">
            {summary.cross_checks.map((c) => (
              <li key={c.code}>{c.message}</li>
            ))}
          </ul>
        </div>
      )}
      <ul className="mt-2 grid gap-2 lg:grid-cols-2">
        {summary.documents.map((d) => (
          <DocumentCard key={d.doc_key} doc={d} />
        ))}
      </ul>
      <p className="mt-2 text-[11px] text-gray-400">
        Only the checks are kept (what was read, and any problem), not the uploaded files. They are held while the system is running.
      </p>
    </div>
  )
}
