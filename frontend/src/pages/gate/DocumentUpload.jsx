import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  FileText,
  Loader2,
  Package,
  Snowflake,
  Truck,
  UploadCloud,
  X,
} from 'lucide-react'
import { useMemo, useState } from 'react'
import { useLocation } from 'react-router-dom'

const CONTAINER_TYPES = [
  { value: 'standard', label: 'Standard', icon: Package },
  { value: 'reefer', label: 'Reefer', icon: Snowflake },
  { value: 'hazardous', label: 'Hazardous', icon: AlertTriangle },
  { value: 'oversized', label: 'Oversized', icon: Truck },
]

const BASE_DOCUMENTS = [
  {
    id: 'booking_confirmation',
    label: 'Booking Confirmation',
    purpose: 'Confirms container is booked to a specific vessel',
  },
  {
    id: 'cusdec',
    label: 'Customs Clearance Document (CUSDEC)',
    purpose: 'Legal export/import clearance',
  },
  {
    id: 'gate_pass',
    label: 'Gate Pass',
    purpose: 'Terminal-issued entry permit for the truck/container',
  },
  {
    id: 'vgm',
    label: 'Weight Declaration (VGM)',
    purpose: 'Verified Gross Mass — legally required before loading',
  },
  {
    id: 'seal_match',
    label: 'Container Number & Seal Number',
    purpose: 'Photo of container/seal for physical match verification',
  },
  {
    id: 'driver_docs',
    label: 'Driver / Vehicle Documents',
    purpose: "Driver's license and vehicle registration",
  },
]

const SPECIAL_CARGO_DOCUMENT = {
  id: 'special_cargo',
  label: 'Special Cargo Documents',
  purpose: 'Temperature/refrigeration certs (reefer) or dangerous goods declaration (hazardous)',
}

// Simulated OCR/NLP pre-check — the real pipeline (Tesseract/EasyOCR + a
// completeness classifier) runs server-side; this stands in until that's wired up.
function simulateCheck() {
  return Math.random() < 0.85 ? 'cleared' : 'flagged'
}

function DocumentRow({ doc, file, status, onFileChange, onRemove }) {
  const inputId = `file-${doc.id}`

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-gray-200 bg-white p-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0">
        <p className="text-sm font-semibold text-gray-800">{doc.label}</p>
        <p className="text-xs text-gray-500">{doc.purpose}</p>
        {file && (
          <p className="mt-1 flex items-center gap-1 truncate text-xs text-gray-600">
            <FileText className="h-3.5 w-3.5 shrink-0" />
            {file.name}
          </p>
        )}
      </div>

      <div className="flex shrink-0 items-center gap-3">
        <StatusBadge status={status} />

        {file ? (
          <button
            type="button"
            onClick={() => onRemove(doc.id)}
            aria-label={`Remove ${doc.label}`}
            className="flex h-8 w-8 items-center justify-center rounded-full text-gray-400 hover:bg-gray-100 hover:text-gray-600"
          >
            <X className="h-4 w-4" />
          </button>
        ) : (
          <label
            htmlFor={inputId}
            className="flex cursor-pointer items-center gap-1.5 rounded-md border border-[#123a5c] px-3 py-1.5 text-xs font-semibold text-[#123a5c] hover:bg-[#123a5c]/5"
          >
            <UploadCloud className="h-4 w-4" />
            Upload
            <input
              id={inputId}
              type="file"
              accept="image/*,.pdf"
              className="sr-only"
              onChange={(e) => onFileChange(doc.id, e.target.files?.[0] ?? null)}
            />
          </label>
        )}
      </div>
    </div>
  )
}

function StatusBadge({ status }) {
  const map = {
    pending: { label: 'Not uploaded', cls: 'bg-gray-100 text-gray-500', icon: null },
    uploaded: { label: 'Uploaded', cls: 'bg-blue-50 text-blue-700', icon: null },
    checking: {
      label: 'Checking...',
      cls: 'bg-blue-50 text-blue-700',
      icon: <Loader2 className="h-3.5 w-3.5 animate-spin" />,
    },
    cleared: {
      label: 'Cleared',
      cls: 'bg-green-50 text-green-700',
      icon: <CheckCircle2 className="h-3.5 w-3.5" />,
    },
    flagged: {
      label: 'Flagged',
      cls: 'bg-red-50 text-red-700',
      icon: <AlertCircle className="h-3.5 w-3.5" />,
    },
  }
  const { label, cls, icon } = map[status] ?? map.pending

  return (
    <span className={`flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium ${cls}`}>
      {icon}
      {label}
    </span>
  )
}

export default function DocumentUpload() {
  const location = useLocation()
  const passedState = location.state ?? {}

  const [truckId, setTruckId] = useState(passedState.truckId ?? '')
  const [containerId, setContainerId] = useState(passedState.containerId ?? '')
  const [containerType, setContainerType] = useState(passedState.containerType ?? 'standard')
  const [files, setFiles] = useState({})
  const [statuses, setStatuses] = useState({})
  const [submitting, setSubmitting] = useState(false)

  const documents = useMemo(() => {
    const needsSpecialCargo = containerType === 'reefer' || containerType === 'hazardous'
    return needsSpecialCargo ? [...BASE_DOCUMENTS, SPECIAL_CARGO_DOCUMENT] : BASE_DOCUMENTS
  }, [containerType])

  const handleFileChange = (docId, file) => {
    setFiles((prev) => ({ ...prev, [docId]: file }))
    setStatuses((prev) => ({ ...prev, [docId]: file ? 'uploaded' : 'pending' }))
  }

  const handleRemove = (docId) => {
    setFiles((prev) => {
      const next = { ...prev }
      delete next[docId]
      return next
    })
    setStatuses((prev) => ({ ...prev, [docId]: 'pending' }))
  }

  const uploadedCount = documents.filter((d) => files[d.id]).length
  const allUploaded = uploadedCount === documents.length

  const handleSubmitForCheck = () => {
    setSubmitting(true)
    setStatuses((prev) => {
      const next = { ...prev }
      documents.forEach((d) => {
        if (files[d.id]) next[d.id] = 'checking'
      })
      return next
    })

    setTimeout(() => {
      setStatuses((prev) => {
        const next = { ...prev }
        documents.forEach((d) => {
          if (files[d.id]) next[d.id] = simulateCheck()
        })
        return next
      })
      setSubmitting(false)
    }, 1200)
  }

  const flaggedCount = documents.filter((d) => statuses[d.id] === 'flagged').length
  const clearedCount = documents.filter((d) => statuses[d.id] === 'cleared').length
  const checked = clearedCount + flaggedCount > 0

  return (
    <div className="mx-auto max-w-3xl px-4 py-10 sm:px-6 lg:px-8">
      <h1 className="text-2xl font-bold text-[#123a5c]">Upload Pre-Clearance Documents</h1>
      <p className="mt-1 text-sm text-gray-600">
        Upload your documents before the appointment window so the gate step is a fast
        final verification instead of a full document check.
      </p>

      <div className="mt-6 grid gap-4 rounded-xl border border-gray-200 bg-white p-6 shadow-sm sm:grid-cols-2">
        <div>
          <label htmlFor="truckId" className="block text-sm font-medium text-gray-700">
            Truck ID
          </label>
          <input
            id="truckId"
            value={truckId}
            onChange={(e) => setTruckId(e.target.value)}
            placeholder="TRK-80579"
            className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm outline-none focus:border-[#123a5c] focus:ring-1 focus:ring-[#123a5c]"
          />
        </div>
        <div>
          <label htmlFor="containerId" className="block text-sm font-medium text-gray-700">
            Container ID
          </label>
          <input
            id="containerId"
            value={containerId}
            onChange={(e) => setContainerId(e.target.value)}
            placeholder="MAEU3483419"
            className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm outline-none focus:border-[#123a5c] focus:ring-1 focus:ring-[#123a5c]"
          />
        </div>

        <div className="sm:col-span-2">
          <span className="block text-sm font-medium text-gray-700">Container Type</span>
          <div className="mt-2 grid grid-cols-2 gap-3 sm:grid-cols-4">
            {CONTAINER_TYPES.map(({ value, label, icon: Icon }) => (
              <label
                key={value}
                className={`flex cursor-pointer flex-col items-center gap-1.5 rounded-lg border px-3 py-3 text-sm transition-colors ${
                  containerType === value
                    ? 'border-[#123a5c] bg-[#123a5c]/5 text-[#123a5c]'
                    : 'border-gray-200 text-gray-600 hover:border-gray-300'
                }`}
              >
                <input
                  type="radio"
                  name="containerType"
                  value={value}
                  checked={containerType === value}
                  onChange={(e) => setContainerType(e.target.value)}
                  className="sr-only"
                />
                <Icon className="h-5 w-5" />
                {label}
              </label>
            ))}
          </div>
          {(containerType === 'reefer' || containerType === 'hazardous') && (
            <p className="mt-2 text-xs text-amber-600">
              This cargo type requires an additional special cargo document below.
            </p>
          )}
        </div>
      </div>

      <div className="mt-6 flex items-center justify-between">
        <p className="text-sm font-medium text-gray-700">
          {uploadedCount} / {documents.length} documents uploaded
        </p>
      </div>

      <div className="mt-3 space-y-3">
        {documents.map((doc) => (
          <DocumentRow
            key={doc.id}
            doc={doc}
            file={files[doc.id]}
            status={statuses[doc.id] ?? 'pending'}
            onFileChange={handleFileChange}
            onRemove={handleRemove}
          />
        ))}
      </div>

      <button
        type="button"
        onClick={handleSubmitForCheck}
        disabled={!allUploaded || submitting}
        className="mt-6 flex w-full items-center justify-center gap-2 rounded-md bg-[#123a5c] px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-[#0e2d47] disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
      >
        {submitting ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            Running document pre-check...
          </>
        ) : (
          'Submit for Pre-Check'
        )}
      </button>
      {!allUploaded && (
        <p className="mt-2 text-xs text-gray-500">
          Upload all {documents.length} documents to run the pre-check.
        </p>
      )}

      {checked && (
        <div
          className={`mt-6 rounded-xl border p-5 ${
            flaggedCount > 0 ? 'border-red-200 bg-red-50' : 'border-green-200 bg-green-50'
          }`}
        >
          {flaggedCount > 0 ? (
            <p className="text-sm font-semibold text-red-700">
              {flaggedCount} document{flaggedCount > 1 ? 's' : ''} flagged for correction.
              Please review and re-upload before your appointment window.
            </p>
          ) : (
            <p className="text-sm font-semibold text-green-700">
              All documents cleared. You're ready for a fast final verification at the gate.
            </p>
          )}
        </div>
      )}
    </div>
  )
}
