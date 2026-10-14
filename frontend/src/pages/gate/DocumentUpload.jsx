import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  FileText,
  Loader2,
  ScanText,
  UploadCloud,
} from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useRole } from '../../lib/role'
import {
  checkDocument,
  getAppointmentDocuments,
  getDocumentTemplates,
  listAppointments,
  submitDocuments,
} from '../../lib/gateApi'

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
  vessel_name: 'Vessel',
  voyage: 'Voyage',
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

// Field-by-field check of a document against its template: is every required detail present and valid?
function TemplateChecklist({ template }) {
  const done = Math.round(template.completeness * 100)
  return (
    <div>
      <div className="flex items-center justify-between text-xs">
        <span className="font-semibold text-gray-700">
          Required details: {template.required_ok} of {template.required_total}
        </span>
        <span className={`font-semibold ${template.complete ? 'text-green-700' : 'text-red-700'}`}>
          {template.complete ? 'Document complete' : `${done}% complete`}
        </span>
      </div>
      <div className="mt-1 h-1.5 rounded-full bg-gray-200">
        <div
          className={`h-1.5 rounded-full ${template.complete ? 'bg-green-500' : 'bg-amber-500'}`}
          style={{ width: `${done}%` }}
        />
      </div>
      <ul className="mt-3 grid gap-x-4 gap-y-2 sm:grid-cols-2">
        {template.fields.map((f) => (
          <li key={f.key} className="flex items-start gap-1.5 text-xs">
            {f.status === 'ok' ? (
              <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-green-600" />
            ) : f.status === 'invalid' ? (
              <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-red-600" />
            ) : f.required ? (
              <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-red-600" />
            ) : (
              <span className="mt-0.5 w-3.5 shrink-0 text-center text-gray-300">-</span>
            )}
            <span className="min-w-0">
              <span className="font-medium text-gray-800">{f.label}</span>
              {!f.required && <span className="text-gray-400"> (optional)</span>}
              <span
                className={`block truncate ${
                  f.status === 'ok' ? 'text-gray-600' : f.status === 'invalid' || f.required ? 'text-red-600' : 'text-gray-400'
                }`}
              >
                {f.status === 'ok' ? f.value : f.status === 'invalid' ? f.message : f.required ? 'missing' : 'not found'}
              </span>
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}

function DocumentRow({ doc, entry, template, disabled, onFile }) {
  const [open, setOpen] = useState(false)
  const inputId = `file-${doc.id}`
  const status = entry?.status ?? 'pending'
  const hasDetails = entry && entry.status !== 'checking' && entry.status !== 'error'
  const errors = entry?.issues?.filter((i) => i.level === 'error') ?? []
  const warnings = entry?.issues?.filter((i) => i.level === 'warning') ?? []
  const checked = entry?.template ?? null
  // an incomplete document shows its checklist straight away, so the user sees what is missing
  const showChecklist = checked && hasDetails && (open || !checked.complete)
  const mustContain = (template?.fields ?? []).filter((f) => f.required).map((f) => f.label)

  return (
    <div className="rounded-lg border border-gray-200 bg-white">
      <div className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-gray-800">{doc.label}</p>
          <p className="text-xs text-gray-500">{doc.purpose}</p>
          {!entry && mustContain.length > 0 && (
            <p className="mt-1 text-xs text-gray-500">
              <span className="font-medium text-[#123a5c]">Must contain:</span> {mustContain.join(' · ')}
            </p>
          )}
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

      {showChecklist && (
        <div className="border-t border-gray-100 bg-gray-50 px-4 py-3">
          <TemplateChecklist template={checked} />
        </div>
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

  const { role, myTruck } = useRole()
  const [appointments, setAppointments] = useState([])
  const [loaded, setLoaded] = useState(false)
  const [appointmentId, setAppointmentId] = useState(passed.appointmentId ? String(passed.appointmentId) : '')
  const [results, setResults] = useState({})
  const [submitting, setSubmitting] = useState(false)
  const [outcome, setOutcome] = useState(null)
  const [error, setError] = useState(null)

  // a driver sees their own bookings; documents can only be uploaded once the gate admin has approved one
  useEffect(() => {
    listAppointments(role === 'driver' && myTruck ? { truckId: myTruck } : {})
      .then((rows) => setAppointments(rows.filter((r) => r.status === 'PENDING' || r.status === 'CONFIRMED')))
      .catch(() => setError('Could not reach the gate appointment service. Is the backend running?'))
      .finally(() => setLoaded(true))
  }, [role, myTruck])

  const approved = appointments.filter((a) => a.status === 'CONFIRMED')
  const waiting = appointments.filter((a) => a.status === 'PENDING')
  const appointment = approved.find((a) => String(a.id) === appointmentId)
  const containerType = appointment?.container_type ?? 'standard'

  // default to the approved appointment named in the link, otherwise the first approved one
  useEffect(() => {
    if (!loaded) return
    if (!approved.some((a) => String(a.id) === appointmentId)) {
      setAppointmentId(approved[0] ? String(approved[0].id) : '')
    }
  }, [loaded, appointments]) // eslint-disable-line react-hooks/exhaustive-deps

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

  // the template of each document: what it must contain (depends on the container type)
  const [templates, setTemplates] = useState({})
  useEffect(() => {
    getDocumentTemplates(containerType)
      .then((list) => setTemplates(Object.fromEntries(list.map((t) => [t.doc_key, t]))))
      .catch(() => setTemplates({}))
  }, [containerType])

  const handleFile = async (docKey, file) => {
    setError(null)
    setOutcome(null)
    setResults((prev) => ({ ...prev, [docKey]: { status: 'checking', filename: file.name } }))
    try {
      const verdict = await checkDocument({
        file,
        docKey,
        appointmentId,
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

      {loaded && approved.length === 0 ? (
        <div className="mt-6 rounded-xl border border-blue-100 bg-blue-50 p-6 text-sm text-blue-900">
          <p className="text-base font-semibold">Document upload opens once the gate admin approves your appointment</p>
          {waiting.length > 0 ? (
            <ul className="mt-3 space-y-1 text-xs">
              {waiting.map((a) => (
                <li key={a.id}>
                  Request #{a.id} · {a.truck_id} · {a.container_id} · {slotLabel(a.assigned_slot)} -{' '}
                  <b>waiting for approval</b>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 text-xs">You have no appointment waiting. Book one first.</p>
          )}
          <div className="mt-4 flex flex-wrap gap-3">
            <Link
              to="/my-trip"
              className="rounded-md bg-[#123a5c] px-3 py-1.5 text-xs font-semibold text-white hover:bg-[#0e2d47]"
            >
              Follow my request on My Trip
            </Link>
            <Link to="/gate-appointment" className="rounded-md border border-[#123a5c] px-3 py-1.5 text-xs font-semibold text-[#123a5c]">
              Request an appointment
            </Link>
          </div>
        </div>
      ) : (
        <div className="mt-6 rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <label htmlFor="appointment" className="block text-sm font-medium text-gray-700">
            Approved appointment
          </label>
          <select
            id="appointment"
            value={appointmentId}
            onChange={(e) => setAppointmentId(e.target.value)}
            className={INPUT_CLASS}
          >
            {approved.map((a) => (
              <option key={a.id} value={a.id}>
                #{a.id} · {a.truck_id} · {a.container_id} · {a.container_type} · {slotLabel(a.assigned_slot)}
              </option>
            ))}
          </select>
          {appointment && (
            <p className="mt-3 text-xs text-gray-600">
              Documents are checked against this booking: container <b>{appointment.container_id}</b>, truck{' '}
              <b>{appointment.truck_id}</b>, date <b>{appointment.assigned_slot?.slice(0, 10)}</b>.
            </p>
          )}
          {waiting.length > 0 && (
            <p className="mt-2 text-xs text-gray-500">{waiting.length} other request(s) are still waiting for approval.</p>
          )}
          {(containerType === 'reefer' || containerType === 'hazardous') && (
            <p className="mt-3 text-xs text-amber-600">
              This cargo type requires an additional special cargo document below.
            </p>
          )}
        </div>
      )}

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
          <DocumentRow
            key={doc.id}
            doc={doc}
            entry={results[doc.id]}
            template={templates[doc.id]}
            disabled={submitting}
            onFile={handleFile}
          />
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
          {outcome.missing > 0 && (
            <ul className="mt-3 space-y-1 text-xs text-amber-900">
              {outcome.required
                .filter((r) => r.status !== 'cleared')
                .map((r) => (
                  <li key={r.doc_key}>
                    <b>{r.label}:</b>{' '}
                    {r.status === 'missing'
                      ? 'not uploaded'
                      : r.missing_details?.length
                        ? `incomplete (${Math.round((r.completeness ?? 0) * 100)}%), missing ${r.missing_details.join(', ')}`
                        : 'flagged - see the issues on the document'}
                  </li>
                ))}
            </ul>
          )}
          <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
            <RiskDelta
              label="Missing documents"
              before={outcome.before.missing_documents}
              after={outcome.after.missing_documents}
              format={(v) => String(v)}
            />
            <RiskDelta
              label="Linked vessel"
              before={outcome.before.vessel_delay}
              after={outcome.after.vessel_delay}
              format={(v) => (v ? 'Delayed' : 'On time')}
              order={(v) => (v ? 1 : 0)}
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
          {outcome.vessel && outcome.vessel.delayed !== null && (
            <p className="mt-3 text-xs text-gray-700">
              <b>Vessel {outcome.vessel.vessel}</b> (read from your booking confirmation):{' '}
              {outcome.vessel.delayed ? `delayed ${outcome.vessel.delay_hours} h` : 'on schedule'} - {outcome.vessel.source}.
              {outcome.vessel.delayed && (
                <>
                  {' '}
                  <Link to="/gate-optimization" className="font-medium text-[#123a5c] hover:underline">
                    Re-plan affected slots
                  </Link>
                </>
              )}
            </p>
          )}
          {!outcome.vessel && (
            <p className="mt-3 text-xs text-amber-700">
              No booking confirmation was checked, so the linked vessel&apos;s delay is still unknown.
            </p>
          )}
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
            Document completeness and the customs risk read from the declaration feed the no-show and
            clearance-time models: a complete, low-risk set lowers both; high-risk goods raise clearance time.
          </p>
          <Link to="/appointments" className="mt-3 inline-block text-sm font-medium text-[#123a5c] hover:underline">
            View appointment history
          </Link>
        </div>
      )}
    </div>
  )
}
