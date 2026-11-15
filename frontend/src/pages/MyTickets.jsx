import { ArrowRight, Eye, Printer, Ticket, XCircle } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import VoiceControls from '../components/VoiceControls'
import { Alert, ConfirmDialog, Empty, Spinner, StatusBadge } from '../components/ui'
import { useVoice } from '../context/VoiceContext'
import { api } from '../services/api'
import { prettyDate, prettyDateTimeUtc, seatList, taka, time12, timeSpoken } from '../utils/format'

export const speakTicket = (b) =>
  `Ticket ${b.booking_reference.split('').join(' ')}. ${b.status.toLowerCase()}. ${b.operator_name}, ${b.bus_name}, from ${b.origin} to ${b.destination}, on ${prettyDate(b.departure_date)} at ${timeSpoken(b.departure_time)}. Seats ${seatList(b)}. Total fare ${Math.round(b.total_fare)} taka.`

export default function MyTickets() {
  const [items, setItems] = useState(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [target, setTarget] = useState(null) // booking awaiting cancel confirmation
  const [busy, setBusy] = useState(false)
  const [filter, setFilter] = useState('ALL')
  const voice = useVoice()
  const nav = useNavigate()
  const spokeRef = useRef(false)

  const load = useCallback(async () => {
    try { const d = await api.get('/bookings/my'); setItems(d.bookings); setError('') } catch (e) { setError(e.message); setItems([]) }
  }, [])
  useEffect(() => { load() }, [load])

  useEffect(() => {
    if (items && !spokeRef.current) {
      spokeRef.current = true
      const up = items.filter((b) => b.status === 'CONFIRMED').length
      voice.speak(items.length ? `You have ${items.length} booking${items.length > 1 ? 's' : ''}, ${up} confirmed. Say read my ticket to hear the latest one.` : 'You have no bookings yet.')
    }
  }, [items, voice])

  const askCancel = (b) => { setTarget(b); voice.speak(`Do you want to cancel booking ${b.booking_reference.split('').join(' ')}, ${b.origin} to ${b.destination}? Say confirm to cancel, or no to keep it.`) }

  const doCancel = useCallback(async () => {
    if (!target) return
    setBusy(true)
    try {
      const d = await api.post(`/bookings/${target.id}/cancel`)
      setNotice(d.message); voice.speak(`Booking ${target.booking_reference.split('').join(' ')} has been cancelled and your seats were released.`)
      setTarget(null); await load()
    } catch (e) { setError(e.message); voice.speak(e.message); setTarget(null); await load() } finally { setBusy(false) }
  }, [target, load, voice])

  const latestConfirmed = items?.find((b) => b.status === 'CONFIRMED') || items?.[0]
  const onCommand = (cmd) => {
    if (cmd.type === 'read_ticket') return latestConfirmed ? voice.speak(speakTicket(latestConfirmed), { force: true }) : voice.speak('You have no tickets to read.', { force: true })
    if (cmd.type === 'show_tickets') return voice.speak('You are already on your tickets page.', { force: true })
    if (cmd.type === 'cancel_booking') { // always asks for explicit confirmation first
      const b = items?.find((x) => x.can_cancel)
      return b ? askCancel(b) : voice.speak('You have no bookings that can be cancelled.', { force: true })
    }
    if (cmd.type === 'confirm') return target ? doCancel() : voice.speak('There is nothing waiting for confirmation.', { force: true })
    if (cmd.type === 'decline') { setTarget(null); return voice.speak('Okay, your booking was kept.', { force: true }) }
    voice.speak('That command is not available on this page.', { force: true })
  }

  const shown = (items || []).filter((b) => filter === 'ALL' || b.status === filter)
  return (
    <div className="mx-auto max-w-5xl space-y-5 px-4 py-8">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div><h1 className="text-2xl font-bold text-navy-900">My Tickets</h1><p className="text-sm text-slate-500">Only your own bookings are shown.</p></div>
        <select aria-label="Filter by status" className="input !w-auto" value={filter} onChange={(e) => setFilter(e.target.value)}>
          <option value="ALL">All statuses</option><option value="CONFIRMED">Confirmed</option><option value="CANCELLED">Cancelled</option><option value="COMPLETED">Completed</option>
        </select>
      </div>
      <VoiceControls onCommand={onCommand} hint='Say "read my ticket" or "cancel booking" (you will be asked to confirm).' />
      {notice && <Alert kind="success" onClose={() => setNotice('')}>{notice}</Alert>}
      {error && <Alert onClose={() => setError('')}>{error}</Alert>}
      {!items && <Spinner />}
      {items && items.length === 0 && !error && <Empty icon={Ticket} title="No tickets yet" action={<Link to="/" className="btn-primary">Search buses</Link>}>Book your first journey and it will appear here.</Empty>}
      {items && items.length > 0 && shown.length === 0 && <Empty icon={Ticket} title="No tickets with this status" />}
      <div className="space-y-3">
        {shown.map((b) => (
          <article key={b.id} className="card p-4 animate-rise sm:p-5">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div><p className="font-mono text-sm font-bold tracking-wider text-navy-900">{b.booking_reference}</p>
                <p className="text-xs text-slate-500">Booked {prettyDateTimeUtc(b.booked_at)}</p></div>
              <StatusBadge status={b.status} />
            </div>
            <div className="mt-3 flex items-center gap-2 text-lg font-bold text-navy-900">{b.origin}<ArrowRight className="h-4 w-4 text-accent-500" />{b.destination}</div>
            <dl className="mt-3 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
              <div><dt className="label !mb-0">Passenger</dt><dd>{b.passenger_name}</dd></div>
              <div><dt className="label !mb-0">Bus</dt><dd>{b.operator_name}<br /><span className="text-slate-500">{b.bus_name}</span></dd></div>
              <div><dt className="label !mb-0">Departure</dt><dd>{prettyDate(b.departure_date)}<br />{time12(b.departure_time)}</dd></div>
              <div><dt className="label !mb-0">Seats ({b.seat_count})</dt><dd>{seatList(b)}<br /><strong>{taka(b.total_fare)}</strong></dd></div>
            </dl>
            <div className="mt-4 flex flex-wrap gap-2">
              <Link to={`/tickets/${b.id}`} className="btn-primary"><Eye className="h-4 w-4" />View ticket</Link>
              <button className="btn-ghost" onClick={() => nav(`/tickets/${b.id}?print=1`)}><Printer className="h-4 w-4" />Download / Print</button>
              <button className="btn-ghost" onClick={() => voice.speak(speakTicket(b), { force: true })}>Read aloud</button>
              {b.can_cancel && <button className="btn-ghost text-red-600" onClick={() => askCancel(b)}><XCircle className="h-4 w-4" />Cancel ticket</button>}
            </div>
          </article>
        ))}
      </div>
      <ConfirmDialog open={!!target} danger title="Cancel this ticket?" confirmLabel="Yes, cancel ticket" cancelLabel="Keep ticket" busy={busy} onConfirm={doCancel} onCancel={() => { setTarget(null); voice.stop() }}>
        {target && <><p className="font-mono font-semibold text-navy-900">{target.booking_reference}</p><p>{target.origin} to {target.destination} · {prettyDate(target.departure_date)} {time12(target.departure_time)}</p><p className="mt-2">Seats {seatList(target)} will be released. This cannot be undone.</p></>}
      </ConfirmDialog>
    </div>
  )
}
