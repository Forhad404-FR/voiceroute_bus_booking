import { ArrowLeft, Printer, Volume2, XCircle } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import TicketView from '../components/TicketView'
import { Alert, ConfirmDialog, Spinner } from '../components/ui'
import { useVoice } from '../context/VoiceContext'
import { api } from '../services/api'
import { speakTicket } from './MyTickets'

export default function TicketPage() {
  const { bookingId } = useParams()
  const [sp] = useSearchParams()
  const [b, setB] = useState(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [asking, setAsking] = useState(false)
  const [busy, setBusy] = useState(false)
  const voice = useVoice()
  const nav = useNavigate()

  const load = () => api.get(`/bookings/${bookingId}`).then((d) => setB(d.booking)).catch((e) => setError(e.message))
  useEffect(() => { load() }, [bookingId]) // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (b && sp.get('print') === '1') setTimeout(() => window.print(), 400) }, [b]) // eslint-disable-line react-hooks/exhaustive-deps

  const cancel = async () => {
    setBusy(true)
    try { const d = await api.post(`/bookings/${bookingId}/cancel`); setNotice(d.message); voice.speak('Your booking has been cancelled and the seats were released.'); setB(d.booking) }
    catch (e) { setError(e.message) } finally { setBusy(false); setAsking(false) }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-4 px-4 py-8">
      <div className="no-print flex flex-wrap items-center justify-between gap-2">
        <Link to="/my-tickets" className="btn-ghost"><ArrowLeft className="h-4 w-4" />My tickets</Link>
        {b && <div className="flex gap-2">
          <button className="btn-ghost" onClick={() => voice.speak(speakTicket(b), { force: true })}><Volume2 className="h-4 w-4" />Read aloud</button>
          <button className="btn-primary" onClick={() => window.print()}><Printer className="h-4 w-4" />Print / Save PDF</button>
        </div>}
      </div>
      {notice && <Alert kind="success">{notice}</Alert>}
      {error && <Alert>{error} <button className="underline" onClick={() => nav('/my-tickets')}>Back to my tickets</button></Alert>}
      {!b && !error && <Spinner />}
      {b && <TicketView b={b} />}
      {b?.can_cancel && <div className="no-print"><button className="btn-ghost text-red-600" onClick={() => { setAsking(true); voice.speak('Do you want to cancel this booking? Please confirm on screen.') }}><XCircle className="h-4 w-4" />Cancel ticket</button></div>}
      <ConfirmDialog open={asking} danger title="Cancel this ticket?" confirmLabel="Yes, cancel ticket" cancelLabel="Keep ticket" busy={busy} onConfirm={cancel} onCancel={() => setAsking(false)}>
        Your seats will be released and this cannot be undone.
      </ConfirmDialog>
    </div>
  )
}
