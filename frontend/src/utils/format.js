export const taka = (n) => `৳${Number(n).toLocaleString('en-BD', { maximumFractionDigits: 0 })}`

export function time12(hhmm) {
  if (!hhmm) return ''
  const [h, m] = String(hhmm).split(':').map(Number)
  const suffix = h >= 12 ? 'PM' : 'AM'
  const hh = h % 12 === 0 ? 12 : h % 12
  return `${hh}:${String(m).padStart(2, '0')} ${suffix}`
}

// Spoken form: "10 PM" / "6:30 AM"
export function timeSpoken(hhmm) {
  const [h, m] = String(hhmm).split(':').map(Number)
  const suffix = h >= 12 ? 'PM' : 'AM'
  const hh = h % 12 === 0 ? 12 : h % 12
  return m === 0 ? `${hh} ${suffix}` : `${hh}:${String(m).padStart(2, '0')} ${suffix}`
}

export function duration(mins) {
  if (!mins) return ''
  const h = Math.floor(mins / 60), m = mins % 60
  return `${h}h${m ? ` ${m}m` : ''}`
}

export function prettyDate(iso) {
  if (!iso) return ''
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d).toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' })
}

export function prettyDateTimeUtc(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString('en-GB', { timeZone: 'Asia/Dhaka', day: 'numeric', month: 'short', year: 'numeric', hour: 'numeric', minute: '2-digit' })
}

// Today's date in Bangladesh time as YYYY-MM-DD (independent of the device time zone)
export function todayBD(offsetDays = 0) {
  const now = new Date(Date.now() + 6 * 3600 * 1000 + offsetDays * 86400000)
  return now.toISOString().slice(0, 10)
}

export const seatList = (b) => (b.seat_labels || []).join(', ')
export const statusLabel = (s) => ({ CONFIRMED: 'Confirmed', CANCELLED: 'Cancelled', COMPLETED: 'Completed' }[s] || s)
