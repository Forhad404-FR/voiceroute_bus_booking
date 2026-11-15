import { ArrowRight, CheckCircle2, Ticket } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import SeatMap from '../components/SeatMap'
import VoiceControls from '../components/VoiceControls'
import { Alert, ConfirmDialog, SampleBanner, Spinner } from '../components/ui'
import { useVoice } from '../context/VoiceContext'
import { api } from '../services/api'
import { prettyDate, seatList, taka, time12, timeSpoken } from '../utils/format'

export default function Booking() {
  const { scheduleId } = useParams()
  const nav = useNavigate()
  const voice = useVoice()
  const [data, setData] = useState(null)
  const [selected, setSelected] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [confirming, setConfirming] = useState(false)
  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState(null)
  const submittingRef = useRef(false)

  const load = useCallback(async () => {
    try { setData(await api.get(`/schedules/${scheduleId}/seats`)); setError('') }
    catch (e) { setError(e.message) } finally { setLoading(false) }
  }, [scheduleId])
  useEffect(() => { load() }, [load])

  const s = data?.schedule
  const total = s ? selected.length * s.fare : 0
  const labelOf = (n) => data.seats.find((x) => x.seat_number === n)?.label
  const selectedLabels = data ? [...selected].sort((a, b) => a - b).map(labelOf) : []
  const toggle = (n) => setSelected((cur) => (cur.includes(n) ? cur.filter((x) => x !== n) : [...cur, n]))

  const summary = () => s && `Booking summary. ${s.operator_name}, ${s.origin} to ${s.destination}, on ${prettyDate(s.departure_date)} at ${timeSpoken(s.departure_time)}. Seats ${selectedLabels.join(', ')}. Total fare ${Math.round(total)} taka. Say confirm to book, or no to go back.`

  const review = () => {
    if (!selected.length) return setError('Select at least one seat first.')
    setError(''); setConfirming(true); voice.speak(summary())
  }

  const confirm = useCallback(async () => {
    if (submittingRef.current) return
    submittingRef.current = true; setBusy(true); setError('')
    try {
      const d = await api.post('/bookings', { schedule_id: Number(scheduleId), seat_numbers: selected })
      setDone(d.booking); setConfirming(false)
      voice.speak(`Your booking is confirmed. Booking reference ${d.booking.booking_reference.split('').join(' ')}. Seats ${seatList(d.booking)}. Total fare ${Math.round(d.booking.total_fare)} taka. Have a safe journey.`)
    } catch (e) {
      setConfirming(false)
      setError(e.message)
      voice.speak(e.message)
      await load() // the server is the source of truth: refresh seat states
      if (e.data?.seats?.length) setSelected((cur) => cur.filter((n) => !e.data.seats.includes(n)))
      if (e.status === 401) nav('/login')
    } finally { submittingRef.current = false; setBusy(false) }
  }, [scheduleId, selected, voice, load, nav])

  const onCommand = (cmd) => {
    if (cmd.type === 'book_bus') return review()
    if (cmd.type === 'confirm') return confirming ? confirm() : voice.speak('There is nothing to confirm yet. Select seats and say book this bus.', { force: true })
    if (cmd.type === 'decline') { setConfirming(false); return voice.speak('Okay, nothing was booked.', { force: true }) }
    if (cmd.type === 'show_tickets') return nav('/my-tickets')
    voice.speak('That command is not available on this page.', { force: true })
  }

  if (loading) return <Spinner label="Loading seats..." />
  if (!data) return <div className="mx-auto max-w-xl px-4 py-10"><Alert>{error || 'Schedule not found.'}</Alert></div>

  if (done) {
    return (
      <div className="mx-auto max-w-lg px-4 py-12">
        <div className="card p-8 text-center animate-rise">
          <CheckCircle2 className="mx-auto h-14 w-14 text-emerald-500" />
          <h1 className="mt-3 text-2xl font-bold text-navy-900">Booking confirmed</h1>
          <p className="mt-1 text-sm text-slate-500">Your reference</p>
          <p className="font-mono text-2xl font-bold tracking-widest text-navy-900">{done.booking_reference}</p>
          <p className="mt-4 text-sm text-slate-600">{done.origin} to {done.destination} · {prettyDate(done.departure_date)} · {time12(done.departure_time)}<br />Seats {seatList(done)} · {taka(done.total_fare)}</p>
          <div className="mt-6 flex flex-col gap-2 sm:flex-row sm:justify-center">
            <Link to={`/tickets/${done.id}`} className="btn-primary"><Ticket className="h-4 w-4" />View ticket</Link>
            <Link to="/my-tickets" className="btn-ghost">My tickets</Link>
            <button className="btn-ghost" onClick={() => voice.repeat()}>Repeat confirmation</button>
          </div>
        </div>
      </div>
    )
  }

  const unavailable = s.status !== 'ACTIVE'
  return (
    <div className="mx-auto max-w-5xl space-y-5 px-4 py-8">
      <VoiceControls onCommand={onCommand} hint='Say "book this bus" to review your seats, then "confirm" or "no".' />
      <SampleBanner />
      {error && <Alert onClose={() => setError('')}>{error}</Alert>}
      <div className="grid gap-5 lg:grid-cols-[1fr_20rem]">
        <section className="card p-5">
          <h1 className="text-xl font-bold text-navy-900">Select your seats</h1>
          <p className="mb-5 text-sm text-slate-500">Up to 6 seats per booking. Availability is re-checked by the server when you confirm.</p>
          {unavailable ? <Alert kind="warn">This schedule is no longer available for booking.</Alert>
            : <SeatMap seats={data.seats} selected={selected} onToggle={toggle} />}
        </section>
        <aside className="card h-fit space-y-4 p-5 lg:sticky lg:top-24">
          <div>
            <p className="font-semibold text-navy-900">{s.operator_name}</p>
            <p className="text-sm text-slate-500">{s.bus_name} · {s.bus_type_label}</p>
          </div>
          <div className="flex items-center gap-2 font-semibold text-navy-900">{s.origin}<ArrowRight className="h-4 w-4 text-accent-500" />{s.destination}</div>
          <p className="text-sm text-slate-600">{prettyDate(s.departure_date)}<br />Departs {time12(s.departure_time)} · Arrives ~{time12(s.arrival_time)}</p>
          <dl className="space-y-2 border-t border-slate-100 pt-3 text-sm">
            <div className="flex justify-between"><dt className="text-slate-500">Fare per seat</dt><dd className="font-medium">{taka(s.fare)}</dd></div>
            <div className="flex justify-between"><dt className="text-slate-500">Seats left</dt><dd className="font-medium">{s.available_seats} / {s.total_seats}</dd></div>
            <div className="flex justify-between"><dt className="text-slate-500">Selected</dt><dd className="max-w-[10rem] text-right font-medium">{selectedLabels.length ? selectedLabels.join(', ') : '-'}</dd></div>
            <div className="flex justify-between border-t border-slate-100 pt-2 text-base"><dt className="font-semibold">Total</dt><dd className="font-extrabold text-navy-900">{taka(total)}</dd></div>
          </dl>
          <button className="btn-primary w-full py-3" disabled={!selected.length || unavailable} onClick={review}>Review booking</button>
          <p className="text-[11px] text-slate-400">Final price is calculated by the server from the schedule fare.</p>
        </aside>
      </div>
      <ConfirmDialog open={confirming} title="Confirm your booking" confirmLabel="Confirm booking" busy={busy} onConfirm={confirm} onCancel={() => { setConfirming(false); voice.stop() }}>
        <p className="font-medium text-navy-900">{s.operator_name} · {s.bus_name}</p>
        <p>{s.origin} to {s.destination}</p>
        <p>{prettyDate(s.departure_date)} at {time12(s.departure_time)}</p>
        <p className="mt-2">Seats: <strong>{selectedLabels.join(', ')}</strong></p>
        <p>Total fare: <strong>{taka(total)}</strong></p>
        <p className="mt-2 text-xs text-slate-400">You can also say "confirm" or "no".</p>
      </ConfirmDialog>
    </div>
  )
}
