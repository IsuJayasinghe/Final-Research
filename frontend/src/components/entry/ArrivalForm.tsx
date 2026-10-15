import { useState, type FormEvent, type ReactNode } from 'react'
import { Bot, ChevronDown, Loader2, Wand2 } from 'lucide-react'
import type { ArrivalRequest, ContainerType } from '../../api/types'

// Options taken from the Colombo Port container data
const TYPES: ContainerType[] = ['DRY', 'REEFER', 'HAZMAT', 'OVERSIZED']
const SIZES = ['20ft', '40ft', '45ft']
const CARGO = ['General Cargo', 'Electronics', 'Apparel & Textiles', 'Perishable Goods', 'Machinery Spare Parts',
  'Industrial Chemicals', 'Tea & Spices', 'Pharmaceuticals', 'Frozen Meat', 'Frozen Seafood',
  'Heavy Industrial Machinery', 'Flammable Liquids', 'Pesticides & Fertilizers', 'Batteries & Corrosives',
  'Compressed Gases', 'Construction Steel/Pipes', 'Fruits & Vegetables', 'Vehicles & Heavy Equipment']
const LINES = ['Maersk Line', 'CMA CGM', 'Ocean Network Express (ONE)', 'OOCL', 'MSC', 'Hapag-Lloyd', 'EVERGREEN', 'SLPA']
const WEIGHTS = ['Light', 'Medium', 'Heavy']
const CONTAINER_ID = /^[A-Z]{4}\d{7}$/                 // owner code + 7 digits, e.g. MSKU1234567

type Flag = '' | '1' | '0'

export interface FormState {
  container_id: string
  container_type: ContainerType
  container_size: string
  cargo_type: string
  shipping_line: string
  weight_category: string
  customs_cleared: Flag
  quarantine_flag: Flag
  customs_red_lane: Flag
  vessel_call_size: string
  hours_since_berthing: string
  dwell_days: string
}

export const EMPTY_FORM: FormState = {
  container_id: '', container_type: 'DRY', container_size: '40ft', cargo_type: 'General Cargo',
  shipping_line: 'Maersk Line', weight_category: 'Medium', customs_cleared: '', quarantine_flag: '',
  customs_red_lane: '', vessel_call_size: '', hours_since_berthing: '', dwell_days: '',
}

const SAMPLE: FormState = {
  ...EMPTY_FORM, container_id: 'MSCU8471293', shipping_line: 'MSC', customs_cleared: '0', quarantine_flag: '0',
  customs_red_lane: '0', vessel_call_size: '850', hours_since_berthing: '6',
}

/** Convert the form into the API request; empty optional fields are left out (model handles missing values). */
export function toRequest(f: FormState): ArrivalRequest {
  const num = (v: string) => (v.trim() === '' ? undefined : Number(v))
  return {
    container_id: f.container_id.trim().toUpperCase(), container_type: f.container_type,
    container_size: f.container_size, cargo_type: f.cargo_type, shipping_line: f.shipping_line,
    weight_category: f.weight_category, customs_cleared: num(f.customs_cleared),
    quarantine_flag: num(f.quarantine_flag), customs_red_lane: num(f.customs_red_lane),
    vessel_call_size: num(f.vessel_call_size), hours_since_berthing: num(f.hours_since_berthing),
    dwell_days: num(f.dwell_days),
  }
}

function validate(f: FormState) {
  const errors: Partial<Record<keyof FormState, string>> = {}
  if (!CONTAINER_ID.test(f.container_id.trim().toUpperCase())) {
    errors.container_id = 'Use 4 letters + 7 digits, e.g. MSKU1234567'
  }
  for (const key of ['vessel_call_size', 'hours_since_berthing', 'dwell_days'] as const) {
    if (f[key].trim() !== '' && (isNaN(Number(f[key])) || Number(f[key]) < 0)) errors[key] = 'Enter a positive number'
  }
  if (f.dwell_days.trim() !== '' && Number(f.dwell_days) > 90) errors.dwell_days = 'Maximum 90 days'
  return errors
}

function Field({ label, error, children }: { label: string; error?: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="label">{label}</span>
      <div className="mt-1.5">{children}</div>
      {error && <span className="mt-1 block text-xs text-danger">{error}</span>}
    </label>
  )
}

interface Props {
  onSubmit: (request: ArrivalRequest) => void
  submitting: boolean
}

export default function ArrivalForm({ onSubmit, submitting }: Props) {
  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [errors, setErrors] = useState<Partial<Record<keyof FormState, string>>>({})
  const [advanced, setAdvanced] = useState(false)

  const set = (key: keyof FormState) => (e: { target: { value: string } }) =>
    setForm((f) => ({ ...f, [key]: e.target.value }))

  const submit = (e: FormEvent) => {
    e.preventDefault()
    const found = validate(form)
    setErrors(found)
    if (Object.keys(found).length === 0) onSubmit(toRequest(form))
  }

  const select = (key: keyof FormState, options: string[], labels?: Record<string, string>) => (
    <select className="input" value={form[key]} onChange={set(key)}>
      {options.map((o) => <option key={o} value={o}>{labels?.[o] ?? o}</option>)}
    </select>
  )
  const flag = (key: keyof FormState, yes = 'Yes', no = 'No') =>
    select(key, ['', '1', '0'], { '': 'Unknown', '1': yes, '0': no })

  return (
    <form onSubmit={submit} className="card" noValidate>
      <div className="mb-5 flex items-center justify-between">
        <h2 className="border-l-4 border-accent pl-3 text-lg">Container Details</h2>
        <button type="button" className="text-xs text-accent hover:underline" onClick={() => { setForm(SAMPLE); setErrors({}) }}>
          <Wand2 size={12} className="mr-1 inline" />Fill sample
        </button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Container ID" error={errors.container_id}>
          <input className="input font-mono uppercase" value={form.container_id} onChange={set('container_id')}
                 placeholder="MSKU1234567" maxLength={11} />
        </Field>
        <Field label="Container type">{select('container_type', TYPES)}</Field>
        <Field label="Cargo category">{select('cargo_type', CARGO)}</Field>
        <Field label="Shipping line">{select('shipping_line', LINES)}</Field>
        <Field label="TEU size">{select('container_size', SIZES)}</Field>
        <Field label="Weight category">{select('weight_category', WEIGHTS)}</Field>
        <Field label="Customs cleared at arrival">{flag('customs_cleared')}</Field>
        <Field label="Quarantine flag">{flag('quarantine_flag')}</Field>
        <Field label="Customs red lane (inspection)">{flag('customs_red_lane')}</Field>
      </div>

      <button type="button" onClick={() => setAdvanced(!advanced)}
              className="mt-5 flex items-center gap-1 text-xs text-muted hover:text-ink">
        <ChevronDown size={14} className={`transition ${advanced ? 'rotate-180' : ''}`} /> Vessel details and known dwell time (optional)
      </button>
      {advanced && (
        <div className="mt-4 grid gap-4 sm:grid-cols-3">
          <Field label="Vessel call size" error={errors.vessel_call_size}>
            <input className="input" inputMode="numeric" value={form.vessel_call_size} onChange={set('vessel_call_size')} placeholder="e.g. 850" />
          </Field>
          <Field label="Hours since berthing" error={errors.hours_since_berthing}>
            <input className="input" inputMode="decimal" value={form.hours_since_berthing} onChange={set('hours_since_berthing')} placeholder="e.g. 6" />
          </Field>
          <Field label="Known dwell (days)" error={errors.dwell_days}>
            <input className="input" inputMode="decimal" value={form.dwell_days} onChange={set('dwell_days')} placeholder="leave empty for AI" />
          </Field>
        </div>
      )}

      <p className="mt-4 text-[11px] text-muted">Unknown values are allowed - the model handles missing information.</p>
      <button type="submit" className="btn-primary mt-4 w-full py-3 text-base" disabled={submitting}>
        {submitting ? <Loader2 size={18} className="animate-spin" /> : <Bot size={18} />}
        {submitting ? 'Getting recommendation...' : 'Get AI Recommendation'}
      </button>
    </form>
  )
}
