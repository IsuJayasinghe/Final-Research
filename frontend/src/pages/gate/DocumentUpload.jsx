import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  FileText,
  Loader2,
  Package,
  ScanText,
  Snowflake,
  Truck,
  UploadCloud,
} from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import {
  checkDocument,
  getAppointmentDocuments,
  listAppointments,
  submitDocuments,
} from '../../lib/gateApi'

const CONTAINER_TYPES = [
  { value: 'standard', label: 'Standard', icon: Package },
  { value: 'reefer', label: 'Reefer', icon: Snowflake },
  { value: 'hazardous', label: 'Hazardous', icon: AlertTriangle },
  { value: 'oversized', label: 'Oversized', icon: Truck },
]

const BASE_DOCUMENTS = [
  { id: 'booking_confirmation', label: 'Booking Confirmation', purpose: 'Confirms container is booked to a specific vessel' },
  { id: 'cusdec', label: 'Customs Clearance Document (CUSDEC)', purpose: 'Legal export/import clearance' },
  { id: 'gate_pass', label: 'Gate Pass', purpose: 'Terminal-issued entry permit for the truck/container' },
  { id: 'vgm', label: 'Weight Declaration (VGM)', purpose: 'Verified Gross Mass - legally required before loading' },
  { id: 'seal_match', label: 'Container Number & Seal Number', purpose: 'Photo of container/seal for physical match verification' },
  { id: 'driver_docs', label: 'Driver / Vehicle Documents', purpose: "Driver's license and vehicle registration" },
]

const SPECIAL_CARGO_DOCUMENT = {
  id: 'special_cargo',
  label: 'Special Cargo Documents',
  purpose: 'Temperature/refrigeration certs (reefer) or dangerous goods declaration (hazardous)',
}

const INPUT_CLASS =
  'mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm outline-none focus:border-[#123a5c] focus:ring-1 focus:ring-[#123a5c]'

const FIELD_LABELS = {
  container_numbers: 'Container',
  seal_number: 'Seal',
  weight_kg: 'Weight (kg)',
  booking_no: 'Booking no.',
  truck_id: 'Truck',
  plate: 'Vehicle reg.',
  licence_no: 'Licence no.',
  hs_code: 'HS code',
  declaration_no: 'Declaration no.',
  goods_description: 'Goods',
  un_number: 'UN number',
  temperature_c: 'Set point (C)',
  dates: 'Dates',
}

const pct = (v) => `${Math.round(v * 100)}%`
const slotLabel = (iso) => (iso ? `${iso.slice(5, 10)} ${iso.slice(11, 16)}` : '--')

function StatusBadge({ status }) {
  const map = {
    pending: { label: 'Not uploaded', cls: 'bg-gray-100 text-gray-500' },
    checking: {
      label: 'Reading document...',
      cls: 'bg-blue-50 text-blue-700',
      icon: <Loader2 className="h-3.5 w-3.5 animate-spin" />,
    },
    cleared: { label: 'Cleared', cls: 'bg-green-50 text-green-700', icon: <CheckCircle2 className="h-3.5 w-3.5" /> },
    flagged: { label: 'Flagged', cls: 'bg-red-50 text-red-700', icon: <AlertCircle className="h-3.5 w-3.5" /> },
    unreadable: { label: 'Unreadable', cls: 'bg-red-50 text-red-700', icon: <AlertCircle className="h-3.5 w-3.5" /> },
    error: { label: 'Upload failed', cls: 'bg-red-50 text-red-700', icon: <AlertCircle className="h-3.5 w-3.5" /> },
  }
  const { label, cls, icon } = map[status] ?? map.pending
  return (
    <span className={`flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium ${cls}`}>
      {icon}
      {label}
    </span>
  )
}

function ExtractedFields({ fields }) {
  const entries = Object.entries(fields ?? {}).filter(([k]) => FIELD_LABELS[k])
  if (entries.length === 0) return <p className="text-xs text-gray-500">No fields could be extracted.</p>
  return (
    <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs sm:grid-cols-3">
      {entries.map(([key, value]) => (
        <div key={key}>
          <dt className="text-gray-500">{FIELD_LABELS[key]}</dt>
          <dd className="font-medium text-gray-800">{Array.isArray(value) ? value.join(', ') : String(value)}</dd>
        </div>
      ))}
    </dl>
  )
}

function DocumentRow({ doc, entry, disabled, onFile }) {
  const [open, setOpen] = useState(false)
  const inputId = `file-${doc.id}`
  const status = entry?.status ?? 'pending'
  const hasDetails = entry && entry.status !== 'checking' && entry.status !== 'error'
  const errors = entry?.issues?.filter((i) => i.level === 'error') ?? []
  const warnings = entry?.issues?.filter((i) => i.level === 'warning') ?? []

  return (
    <div className="rounded-lg border border-gray-200 bg-white">
      <div className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-gray-800">{doc.label}</p>
          <p className="text-xs text-gray-500">{doc.purpose}</p>
          {entry?.filename && (
            <p className="mt-1 flex items-center gap-1 truncate text-xs text-gray-600">
              <FileText className="h-3.5 w-3.5 shrink-0" />
              {entry.filename}
              {hasDetails && entry.ocr_confidence != null && (
                <span className="ml-1 text-gray-400">
                  · {entry.engine === 'pdf-text' ? 'PDF text' : `OCR ${pct(entry.ocr_confidence)}`}
                </span>
              )}
            </p>
          )}
        </div>
        <div className="flex shrink-0 items-center gap-3">
          <StatusBadge status={status} />
          {hasDetails && (
            <button
              type="button"
              aria-label={open ? 'Hide details' : 'Show details'}
              onClick={() => setOpen((o) => !o)}
              className="text-gray-400 hover:text-[#123a5c]"
            >
              {open ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
            </button>
          )}
          <label
            htmlFor={inputId}
            className={`flex items-center gap-1.5 rounded-md border border-[#123a5c] px-3 py-1.5 text-xs font-semibold text-[#123a5c] ${
              disabled || status === 'checking' ? 'cursor-not-allowed opacity-50' : 'cursor-pointer hover:bg-[#123a5c]/5'
            }`}
          >
            <UploadCloud className="h-4 w-4" />
            {entry ? 'Replace' : 'Upload'}
            <input
              id={inputId}
              type="file"
              accept="image/*,.pdf"
              disabled={disabled || status === 'checking'}
              className="sr-only"
              onChange={(e) => {
                const file = e.target.files?.[0]
                if (file) onFile(doc.id, file)
                e.target.value = ''
              }}
            />
          </label>
        </div>
      </div>

      {/* issues are always visible so the user sees what to fix without expanding */}
      {(errors.length > 0 || warnings.length > 0 || status === 'error') && (
        <ul className="space-y-1 border-t border-gray-100 px-4 py-3 text-xs">
          {status === 'error' && <li className="text-red-700">{entry.message}</li>}
          {errors.map((i) => (
            <li key={i.code} className="flex gap-1.5 text-red-700">
              <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              {i.message}
            </li>
          ))}
          {warnings.map((i) => (
            <li key={i.code} className="flex gap-1.5 text-amber-700">
              <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              {i.message}
            </li>
          ))}
        </ul>
      )}

      {open && hasDetails && (
        <div className="space-y-3 border-t border-gray-100 bg-gray-50 px-4 py-3">
          <p className="text-xs text-gray-600">
            Recognised as: <b>{entry.detected_label ?? 'unknown document'}</b>
          </p>
          <ExtractedFields fields={entry.fields} />
          {entry.customs_assessment && (
            <p className="rounded-md bg-white p-2 text-xs text-gray-700">
              <b>Customs risk: {cap(entry.customs_assessment.level)}.</b> {entry.customs_assessment.reasons.join(' ')}
            </p>
          )}
          {entry.text_preview && (
            <details className="text-xs text-gray-600">
              <summary className="cursor-pointer font-medium text-[#123a5c]">Text read by OCR</summary>
              <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap rounded bg-white p-2 text-[11px] text-gray-700">
                {entry.text_preview}
              </pre>
            </details>
          )}
        </div>
      )}
    </div>
  )
}

const RISK_ORDER = { low: 0, medium: 1, high: 2 }
const cap = (s) => (s ? s[0].toUpperCase() + s.slice(1) : s)

// before === null means "not known / not checked yet" (e.g. a booking made before its documents were read)
function RiskDelta({ label, before, after, format, order = (v) => v }) {
  const known = before !== null && before !== undefined
  const better = known && order(after) < order(before)
  const worse = known && order(after) > order(before)
  return (
    <div className="rounded-md bg-gray-50 p-3 text-center">
      <p className="text-xs text-gray-500">{label}</p>
      <p className="mt-1 text-sm text-gray-500">{known ? <span className="line-through">{format(before)}</span> : 'not checked'}</p>
      <p className={`text-xl font-bold ${better ? 'text-green-700' : worse ? 'text-red-600' : 'text-[#123a5c]'}`}>
        {after === null || after === undefined ? 'unknown' : format(after)}
      </p>
    </div>
  )
}

export default function DocumentUpload() {
  const location = useLocation()
  const passed = location.state ?? {}

  const [appointments, setAppointments] = useState([])
  const [appointmentId, setAppointmentId] = useState(passed.appointmentId ? String(passed.appointmentId) : '')
  const [manual, setManual] = useState({
    containerId: passed.containerId ?? '',
    truckId: passed.truckId ?? '',
    containerType: passed.containerType ?? 'standard',
  })
  const [results, setResults] = useState({})
  const [submitting, setSubmitting] = useState(false)
  const [outcome, setOutcome] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    listAppointments()
      .then((rows) => setAppointments(rows.filter((r) => r.status === 'PENDING' || r.status === 'CONFIRMED')))
      .catch(() => setError('Could not reach the gate appointment service. Is the backend running?'))
  }, [])

  const appointment = appointments.find((a) => String(a.id) === appointmentId)
  const containerType = appointment?.container_type ?? manual.containerType

  // restore verdicts already recorded for the chosen appointment
  useEffect(() => {
    setOutcome(null)
    if (!appointmentId) {
      setResults({})
      return
    }
    getAppointmentDocuments(appointmentId)
      .then((stored) => setResults(stored))
      .catch(() => setResults({}))
  }, [appointmentId])

  const documents = useMemo(
    () =>
      containerType === 'reefer' || containerType === 'hazardous'
        ? [...BASE_DOCUMENTS, SPECIAL_CARGO_DOCUMENT]
        : BASE_DOCUMENTS,
    [containerType],
  )

  const handleFile = async (docKey, file) => {
    setError(null)
    setOutcome(null)
    setResults((prev) => ({ ...prev, [docKey]: { status: 'checking', filename: file.name } }))
    try {
      const verdict = await checkDocument({
        file,
        docKey,
        appointmentId: appointmentId || null,
        containerId: manual.containerId,
        truckId: manual.truckId,
        containerType,
      })
      setResults((prev) => ({ ...prev, [docKey]: verdict }))
    } catch (err) {
      setResults((prev) => ({
        ...prev,
        [docKey]: {
          status: 'error',
          filename: file.name,
          message: err instanceof TypeError ? 'Could not reach the service. Is the backend running?' : err.message,
        },
      }))
    }
  }

  const checkedCount = documents.filter((d) => ['cleared', 'flagged', 'unreadable'].includes(results[d.id]?.status)).length
  const clearedCount = documents.filter((d) => results[d.id]?.status === 'cleared').length
  const busy = documents.some((d) => results[d.id]?.status === 'checking')

  const handleSubmit = async () => {
    setSubmitting(true)
    setError(null)
    try {
      setOutcome(await submitDocuments(appointmentId))
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-10 sm:px-6 lg:px-8">
      <h1 className="text-2xl font-bold text-[#123a5c]">Upload Pre-Clearance Documents</h1>
      <p className="mt-1 text-sm text-gray-600">
        Each document is read with OCR, recognised, checked against your booking, and any problem is
        shown immediately - so the gate step is a quick final verification, not a full document check.
      </p>

      <div className="mt-6 rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <label htmlFor="appointment" className="block text-sm font-medium text-gray-700">
          Appointment
        </label>
        <select
          id="appointment"
          value={appointmentId}
          onChange={(e) => setAppointmentId(e.target.value)}
          className={INPUT_CLASS}
        >
          <option value="">No appointment yet - just check my documents</option>
          {appointments.map((a) => (
            <option key={a.id} value={a.id}>
              #{a.id} · {a.truck_id} · {a.container_id} · {a.container_type} · {slotLabel(a.assigned_slot)}
            </option>
          ))}
        </select>

        {appointment ? (
          <p className="mt-3 text-xs text-gray-600">
            Documents are checked against this booking: container <b>{appointment.container_id}</b>, truck{' '}
            <b>{appointment.truck_id}</b>, date <b>{appointment.assigned_slot?.slice(0, 10)}</b>.
          </p>
        ) : (
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="containerId" className="block text-sm font-medium text-gray-700">
                Container ID
              </label>
              <input
                id="containerId"
                value={manual.containerId}
                onChange={(e) => setManual((m) => ({ ...m, containerId: e.target.value }))}
                placeholder="CSQU3054383"
                className={INPUT_CLASS}
              />
            </div>
            <div>
              <label htmlFor="truckId" className="block text-sm font-medium text-gray-700">
                Truck ID
              </label>
              <input
                id="truckId"
                value={manual.truckId}
                onChange={(e) => setManual((m) => ({ ...m, truckId: e.target.value }))}
                placeholder="TRK-80579"
                className={INPUT_CLASS}
              />
            </div>
            <div className="sm:col-span-2">
              <span className="block text-sm font-medium text-gray-700">Container Type</span>
              <div className="mt-2 grid grid-cols-2 gap-3 sm:grid-cols-4">
                {CONTAINER_TYPES.map(({ value, label, icon: Icon }) => (
                  <label
                    key={value}
                    className={`flex cursor-pointer flex-col items-center gap-1.5 rounded-lg border px-3 py-3 text-sm transition-colors ${
                      manual.containerType === value
                        ? 'border-[#123a5c] bg-[#123a5c]/5 text-[#123a5c]'
                        : 'border-gray-200 text-gray-600 hover:border-gray-300'
                    }`}
                  >
                    <input
                      type="radio"
                      name="containerType"
                      value={value}
                      checked={manual.containerType === value}
                      onChange={(e) => setManual((m) => ({ ...m, containerType: e.target.value }))}
                      className="sr-only"
                    />
                    <Icon className="h-5 w-5" />
                    {label}
                  </label>
                ))}
              </div>
            </div>
          </div>
        )}
        {(containerType === 'reefer' || containerType === 'hazardous') && (
          <p className="mt-3 text-xs text-amber-600">
            This cargo type requires an additional special cargo document below.
          </p>
        )}
      </div>

      <div className="mt-6 flex items-center justify-between">
        <p className="flex items-center gap-2 text-sm font-medium text-gray-700">
          <ScanText className="h-4 w-4 text-[#123a5c]" />
          {clearedCount} / {documents.length} documents cleared
        </p>
      </div>

      {error && (
        <div className="mt-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div>
      )}

      <div className="mt-3 space-y-3">
        {documents.map((doc) => (
          <DocumentRow key={doc.id} doc={doc} entry={results[doc.id]} disabled={submitting} onFile={handleFile} />
        ))}
      </div>

      <button
        type="button"
        onClick={handleSubmit}
        disabled={!appointmentId || checkedCount === 0 || busy || submitting}
        className="mt-6 flex w-full items-center justify-center gap-2 rounded-md bg-[#123a5c] px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-[#0e2d47] disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
      >
        {submitting ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            Submitting...
          </>
        ) : (
          'Submit documents for pre-clearance'
        )}
      </button>
      {!appointmentId && (
        <p className="mt-2 text-xs text-gray-500">
          Choose an appointment to submit.{' '}
          <Link to="/gate-appointment" className="font-medium text-[#123a5c] hover:underline">
            Book one first
          </Link>
          .
        </p>
      )}

      {outcome && (
        <div
          className={`mt-6 rounded-xl border p-5 ${
            outcome.missing > 0 ? 'border-amber-200 bg-amber-50' : 'border-green-200 bg-green-50'
          }`}
        >
          <p className={`text-sm font-semibold ${outcome.missing > 0 ? 'text-amber-800' : 'text-green-700'}`}>
            {outcome.missing > 0
              ? `${outcome.summary} Fix the flagged or missing documents and resubmit.`
              : 'All documents cleared. Your booking has been updated - you are ready for a fast final verification at the gate.'}
          </p>
          <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <RiskDelta
              label="Missing documents"
              before={outcome.before.missing_documents}
              after={outcome.after.missing_documents}
              format={(v) => String(v)}
            />
            <RiskDelta
              label="Customs risk"
              before={outcome.before.customs_risk}
              after={outcome.after.customs_risk}
              format={cap}
              order={(v) => RISK_ORDER[v] ?? 0}
            />
            <RiskDelta label="No-show risk" before={outcome.before.p_no_show} after={outcome.after.p_no_show} format={pct} />
            <RiskDelta
              label="Predicted clearance"
              before={outcome.before.clearance_minutes}
              after={outcome.after.clearance_minutes}
              format={(v) => `${Math.round(v)} min`}
            />
          </div>
          {outcome.customs_assessment && (
            <p className="mt-3 text-xs text-gray-700">
              <b>Customs risk {outcome.customs_assessment.level}</b> (read from your customs declaration):{' '}
              {outcome.customs_assessment.reasons.join(' ')}
            </p>
          )}
          {!outcome.customs_assessment && (
            <p className="mt-3 text-xs text-amber-700">
              No customs declaration was checked, so customs risk is still unknown. Upload the CUSDEC to establish it.
            </p>
          )}
          <p className="mt-3 text-xs text-gray-600">
            Document completeness feeds the no-show and clearance-time models, so a complete, readable
            document set lowers both.
          </p>
          <Link to="/appointments" className="mt-3 inline-block text-sm font-medium text-[#123a5c] hover:underline">
            View appointment history
          </Link>
        </div>
      )}
    </div>
  )
}
