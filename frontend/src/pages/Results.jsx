import { ArrowRight, Bus, Clock, Snowflake, SearchX, Users } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import SearchCard from '../components/SearchCard'
import VoiceControls from '../components/VoiceControls'
import { Alert, Empty, SampleBanner, Spinner } from '../components/ui'
import { useVoice } from '../context/VoiceContext'
import { api } from '../services/api'
import { duration, prettyDate, taka, time12, timeSpoken, todayBD } from '../utils/format'

const num = (n) => ['no', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten'][n] ?? String(n)

function describe(data) {
  const list = data.schedules
  if (!data.direct) return `${data.message} ${data.hubs.length ? `You could travel via ${data.hubs.map((h) => h.hub).join(' or ')}.` : ''}`
  if (!list.length) return `There are no buses from ${data.origin} to ${data.destination} on ${prettyDate(data.date)}. Try another date.`
  const first = list.slice(0, 3).map((s) => `${s.operator_name} departs at ${timeSpoken(s.departure_time)}. The fare is ${Math.round(s.fare)} taka. There ${s.available_seats === 1 ? 'is one seat' : `are ${s.available_seats} seats`} available.`).join(' ')
  return `I found ${num(list.length)} bus${list.length === 1 ? '' : 'es'} from ${data.origin} to ${data.destination}. ${first}${list.length > 3 ? ' Showing the first three. Say book the first bus, or choose one on screen.' : ' Say book the first bus, or choose one on screen.'}`
}

export default function Results() {
  const [sp] = useSearchParams()
  const origin = sp.get('origin') || '', destination = sp.get('destination') || '', date = sp.get('date') || todayBD()
  const [sort, setSort] = useState('departure')
  const [busType, setBusType] = useState('')
  const [onlyAvail, setOnlyAvail] = useState(false)
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const voice = useVoice()
  const nav = useNavigate()
  const ready = origin && destination

  useEffect(() => {
    if (!ready) return
    let alive = true
    setLoading(true); setError('')
    api.get('/schedules/search', { origin, destination, date, sort, bus_type: busType || undefined, only_available: onlyAvail || undefined })
      .then((d) => { if (!alive) return; setData(d); voice.speak(describe(d)) })
      .catch((e) => { if (alive) { setData(null); setError(e.message) } })
      .finally(() => alive && setLoading(false))
    return () => { alive = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [origin, destination, date, sort, busType, onlyAvail])

  const list = useMemo(() => data?.schedules || [], [data])

  const onCommand = useCallback((cmd) => {
    if (cmd.type === 'read_results') return data && voice.speak(describe(data), { force: true })
    if (cmd.type === 'show_tickets') return nav('/my-tickets')
    if (cmd.type === 'book_bus') {
      if (!list.length) return voice.speak('There are no buses to book yet. Please search first.', { force: true })
      let pick = list[0]
      if (cmd.nth === 'cheapest') pick = [...list].sort((a, b) => a.fare - b.fare)[0]
      else if (typeof cmd.nth === 'number') pick = list[cmd.nth]
      if (!pick) return voice.speak('I could not find that bus.', { force: true })
      voice.speak(`Opening seat selection for ${pick.operator_name} at ${timeSpoken(pick.departure_time)}. You will confirm before anything is booked.`, { force: true })
      return nav(`/book/${pick.id}`)
    }
    voice.speak('That command is not available on this page.', { force: true })
  }, [data, list, nav, voice])

  return (
    <div className="mx-auto max-w-6xl space-y-5 px-4 py-8">
      <SearchCard compact initial={{ origin, destination, date }} />
      <VoiceControls onCommand={onCommand} hint='Say "read results", "book the first bus", "book the cheapest" or "show my tickets".' />
      <SampleBanner />
      {!ready && <Empty icon={SearchX} title="Choose a route">Pick a From and To district above to see buses.</Empty>}
      {ready && loading && <Spinner label="Finding buses..." />}
      {ready && error && <Alert>{error}</Alert>}

      {ready && data && !loading && (
        <>
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <h1 className="flex items-center gap-2 text-2xl font-bold text-navy-900">{data.origin}<ArrowRight className="h-5 w-5 text-accent-500" />{data.destination}</h1>
              <p className="text-sm text-slate-500">{prettyDate(data.date)}{data.direct ? ` · ${list.length} bus${list.length === 1 ? '' : 'es'} found` : ''}</p>
            </div>
            {data.direct && (
              <div className="flex flex-wrap items-center gap-2 text-sm">
                <select aria-label="Sort" className="input !w-auto" value={sort} onChange={(e) => setSort(e.target.value)}>
                  <option value="departure">Earliest departure</option><option value="price">Lowest price</option>
                </select>
                <select aria-label="Bus type" className="input !w-auto" value={busType} onChange={(e) => setBusType(e.target.value)}>
                  <option value="">AC &amp; Non-AC</option><option value="AC">AC only</option><option value="NON_AC">Non-AC only</option>
                </select>
                <label className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2.5"><input type="checkbox" checked={onlyAvail} onChange={(e) => setOnlyAvail(e.target.checked)} />Seats available</label>
              </div>
            )}
          </div>

          {!data.direct && (
            <Empty icon={SearchX} title="No direct bus available">
              <p>There is no direct bus from <strong>{data.origin}</strong> to <strong>{data.destination}</strong>. VoiceRoute only lists direct buses from its hubs, Dhaka and Chattogram, and does not invent schedules.</p>
              {data.hubs.length > 0 && <div className="mt-3 text-left">
                <p className="font-semibold text-navy-900">Connect through a hub:</p>
                <ul className="mt-1 space-y-1">{data.hubs.map((h) => (
                  <li key={h.hub}>Take <Link className="font-medium text-accent-600 hover:underline" to={`/search?origin=${encodeURIComponent(data.origin)}&destination=${encodeURIComponent(h.hub)}&date=${date}`}>{h.leg1}</Link>, then <Link className="font-medium text-accent-600 hover:underline" to={`/search?origin=${encodeURIComponent(h.hub)}&destination=${encodeURIComponent(data.destination)}&date=${date}`}>{h.leg2}</Link>.</li>
                ))}</ul></div>}
            </Empty>
          )}
          {data.direct && list.length === 0 && <Empty icon={SearchX} title="No buses match">No buses on this date with the current filters. Try another date or clear the filters.</Empty>}

          <div className="space-y-3">
            {list.map((s) => (
              <article key={s.id} className="card flex flex-col gap-4 p-4 animate-rise sm:flex-row sm:items-center sm:p-5">
                <div className="flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-semibold text-navy-900">{s.operator_name}</span>
                    <span className="text-sm text-slate-500">· {s.bus_name}</span>
                    <span className={`badge ${s.bus_type === 'AC' ? 'bg-accent-100 text-accent-700' : 'bg-slate-100 text-slate-600'}`}>{s.bus_type === 'AC' && <Snowflake className="mr-1 h-3 w-3" />}{s.bus_type_label}</span>
                  </div>
                  <div className="mt-3 flex items-center gap-3">
                    <div><p className="text-xl font-bold text-navy-900">{time12(s.departure_time)}</p><p className="text-xs text-slate-500">{s.origin}</p></div>
                    <div className="flex flex-1 flex-col items-center text-xs text-slate-400"><Clock className="h-3.5 w-3.5" />{duration(s.duration_minutes)}<div className="mt-1 h-px w-full bg-slate-200" /></div>
                    <div className="text-right"><p className="text-xl font-bold text-navy-900">{time12(s.arrival_time)}{s.arrival_day_offset > 0 && <sup className="ml-0.5 text-xs text-accent-600">+{s.arrival_day_offset}</sup>}</p><p className="text-xs text-slate-500">{s.destination}</p></div>
                  </div>
                </div>
                <div className="flex items-center justify-between gap-4 border-t border-slate-100 pt-3 sm:w-56 sm:flex-col sm:items-end sm:border-l sm:border-t-0 sm:pl-5 sm:pt-0">
                  <div className="sm:text-right"><p className="text-2xl font-extrabold text-navy-900">{taka(s.fare)}</p><p className="text-xs text-slate-500">per seat</p></div>
                  <div className="text-right">
                    <p className={`mb-2 flex items-center justify-end gap-1 text-xs font-medium ${s.available_seats <= 5 ? 'text-red-600' : 'text-slate-500'}`}><Users className="h-3.5 w-3.5" />{s.available_seats} of {s.total_seats} seats left</p>
                    <Link to={`/book/${s.id}`} className={`btn-primary ${s.available_seats === 0 ? 'pointer-events-none opacity-50' : ''}`} aria-disabled={s.available_seats === 0}><Bus className="h-4 w-4" />{s.available_seats === 0 ? 'Sold out' : 'View seats'}</Link>
                  </div>
                </div>
              </article>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
