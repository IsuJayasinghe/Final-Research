// How an appointment's status is shown. The internal values are unchanged (PENDING = the request is waiting for the
// gate admin, CONFIRMED = approved); only the words and colours are in one place.

export const STATUS_LABEL = {
  PENDING: 'Awaiting approval',
  CONFIRMED: 'Approved',
  REJECTED: 'Rejected',
  WAITLISTED: 'Waitlisted',
  CANCELLED: 'Cancelled',
}

export const STATUS_STYLES = {
  PENDING: 'bg-blue-50 text-blue-700',
  CONFIRMED: 'bg-green-50 text-green-700',
  REJECTED: 'bg-red-50 text-red-700',
  WAITLISTED: 'bg-amber-50 text-amber-700',
  CANCELLED: 'bg-gray-100 text-gray-500',
}

export const statusLabel = (status) => STATUS_LABEL[status] ?? status
export const hhmm = (iso) => (iso ? iso.slice(11, 16) : '--')
export const dayAndHour = (iso) => (iso ? `${iso.slice(5, 10)} ${iso.slice(11, 16)}` : '--')
