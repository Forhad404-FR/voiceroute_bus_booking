import { ArrowRight, Mic, Search, Ticket, Armchair, ShieldCheck, Database } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import SearchCard from '../components/SearchCard'
import { SampleBanner, Spinner } from '../components/ui'
import { api } from '../services/api'
import { taka, todayBD } from '../utils/format'

const STEPS = [
  { icon: Mic, t: 'Speak or type', d: 'Say "Dhaka to Sylhet" or use the district suggestions.' },
  { icon: Search, t: 'Compare buses', d: 'See live seat counts, times and fares from the database.' },
  { icon: Armchair, t: 'Pick your seats', d: 'Choose seats on the layout; the server re-checks every one.' },
  { icon: Ticket, t: 'Travel with a ticket', d: 'Get a booking reference, printable ticket and spoken confirmation.' },
]

export default function Home() {
  const [popular, setPopular] = useState(null)
  const nav = useNavigate()
  useEffect(() => { api.get('/routes/popular', { limit: 8 }).then((d) => setPopular(d.routes)).catch(() => setPopular([])) }, [])
  return (
    <>
      <section className="bg-navy-900 pb-28 pt-12 text-white sm:pt-16">
        <div className="mx-auto max-w-6xl px-4">
          <p className="mb-3 inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-xs font-medium text-navy-100"><Mic className="h-3.5 w-3.5" />Voice-powered transport booking</p>
          <h1 className="max-w-3xl text-4xl font-extrabold leading-tight tracking-tight sm:text-5xl">Your Journey Starts With Your Voice.</h1>
          <p className="mt-4 max-w-2xl text-base text-navy-100 sm:text-lg">Find buses, explore routes and book your next journey across Bangladesh with simple voice commands.</p>
        </div>
      </section>
      <div className="relative z-10 mx-auto -mt-20 max-w-6xl px-4"><SearchCard /></div>
      <div className="mx-auto mt-4 max-w-6xl px-4"><SampleBanner /></div>

      <section className="mx-auto mt-14 max-w-6xl px-4">
        <h2 className="text-2xl font-bold text-navy-900">Popular routes</h2>
        <p className="mt-1 text-sm text-slate-500">Direct routes from our two demonstration hubs, Dhaka and Chattogram.</p>
        {!popular ? <Spinner /> : (
          <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {popular.map((r) => (
              <button key={`${r.origin}-${r.destination}`} onClick={() => nav(`/search?origin=${encodeURIComponent(r.origin)}&destination=${encodeURIComponent(r.destination)}&date=${todayBD()}`)}
                className="card group p-4 text-left transition hover:-translate-y-0.5 hover:shadow-pop">
                <p className="flex items-center gap-2 font-semibold text-navy-900">{r.origin}<ArrowRight className="h-4 w-4 text-accent-500" />{r.destination}</p>
                <p className="mt-1 text-xs text-slate-500">{r.distance_km} km (sample){r.bookings > 0 ? ` · ${r.bookings} booking${r.bookings > 1 ? 's' : ''}` : ''}</p>
                {r.from_fare != null && <p className="mt-3 text-sm text-slate-600">from <span className="font-bold text-navy-900">{taka(r.from_fare)}</span></p>}
              </button>
            ))}
          </div>
        )}
      </section>

      <section className="mx-auto mt-14 max-w-6xl px-4">
        <h2 className="text-2xl font-bold text-navy-900">How it works</h2>
        <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map((s, i) => (
            <div key={s.t} className="card p-5">
              <div className="mb-3 flex items-center gap-3"><span className="flex h-10 w-10 items-center justify-center rounded-xl bg-navy-50 text-navy-700"><s.icon className="h-5 w-5" /></span><span className="text-xs font-bold text-slate-400">STEP {i + 1}</span></div>
              <h3 className="font-semibold text-navy-900">{s.t}</h3><p className="mt-1 text-sm text-slate-500">{s.d}</p>
            </div>
          ))}
        </div>
        <div className="mt-6 grid gap-4 sm:grid-cols-2">
          <div className="card flex gap-3 p-5"><ShieldCheck className="h-6 w-6 shrink-0 text-accent-500" /><p className="text-sm text-slate-600"><strong className="text-navy-900">Booking integrity.</strong> Seats are locked inside a database transaction, so two people can never hold the same seat.</p></div>
          <div className="card flex gap-3 p-5"><Database className="h-6 w-6 shrink-0 text-accent-500" /><p className="text-sm text-slate-600"><strong className="text-navy-900">Direct hub routes.</strong> Between two non-hub districts we tell you honestly that no direct bus exists and suggest a connecting hub.</p></div>
        </div>
        <p className="mt-6 text-center text-sm text-slate-500">New here? <Link className="font-semibold text-accent-600 hover:underline" to="/register">Create an account</Link> to book.</p>
      </section>
    </>
  )
}
