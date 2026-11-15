// Maps a spoken sentence to an intent. Intents only trigger UI flows; every action that changes
// data still goes through the normal authenticated, server-validated, confirmed paths.
export function parseCommand(text) {
  const t = (text || '').toLowerCase().replace(/[.,!?]/g, ' ').replace(/\s+/g, ' ').trim()
  if (!t) return null
  if (/^(stop|be quiet|stop (speaking|talking)|quiet|silence)$/.test(t)) return { type: 'stop' }
  if (/\b(repeat|say (that )?again|say it again)\b/.test(t)) return { type: 'repeat' }
  if (/^(yes|yeah|confirm|confirmed|yes confirm|yes please|ok confirm|do it)\b/.test(t)) return { type: 'confirm' }
  if (/^(no|nope|cancel that|never mind|go back|don'?t)\b/.test(t)) return { type: 'decline' }
  if (/\b(read|hear|tell me|describe)\b.*\b(my |the )?ticket/.test(t)) return { type: 'read_ticket' }
  if (/\b(show|open|view|see|go to)\b.*\b(my )?(tickets|bookings)\b/.test(t)) return { type: 'show_tickets' }
  if (/\bcancel\b.*\b(booking|ticket)\b/.test(t) || /^cancel( it)?$/.test(t)) return { type: 'cancel_booking' }
  if (/\b(book|reserve|buy)\b.*\b(this|that|it|bus|first|second|third|cheapest)\b/.test(t) || /^book( it)?$/.test(t)) {
    const nth = /first|1st/.test(t) ? 0 : /second|2nd/.test(t) ? 1 : /third|3rd/.test(t) ? 2 : /cheapest/.test(t) ? 'cheapest' : null
    return { type: 'book_bus', nth }
  }
  if (/\b(read|speak|hear)\b.*\b(results|buses)\b/.test(t)) return { type: 'read_results' }
  return null
}
