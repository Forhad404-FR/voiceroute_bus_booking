import { ArrowLeftRight, Calendar, Search } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { todayBD } from '../utils/format'
import DistrictInput from './DistrictInput'
import VoiceSearch from './VoiceSearch'
import { Alert } from './ui'

export default function SearchCard({ initial = {}, compact = false }) {
  const nav = useNavigate()
  const [origin, setOrigin] = useState(initial.origin || '')
  const [destination, setDestination] = useState(initial.destination || '')
  const [date, setDate] = useState(initial.date || todayBD())
  const [error, setError] = useState('')

  const swap = () => { setOrigin(destination); setDestination(origin) }
  const onParsed = (p) => {
    if (p.origin) setOrigin(p.origin)
    if (p.destination) setDestination(p.destination)
  }
  const submit = (e) => {
    e.preventDefault()
    if (!origin || !destination) return setError('Please choose both a From and a To district from the suggestions.')
    if (origin === destination) return setError('From and To must be different districts.')
    if (date < todayBD()) return setError('Journey date cannot be in the past.')
    setError('')
    nav(`/search?origin=${encodeURIComponent(origin)}&destination=${encodeURIComponent(destination)}&date=${date}`)
  }
  return (
    <form onSubmit={submit} className={`card ${compact ? 'p-4' : 'p-5 sm:p-6'} space-y-4`} aria-label="Route search">
      <div className="grid gap-3 md:grid-cols-[1fr_auto_1fr_11rem] md:items-start">
        <DistrictInput label="From District" value={origin} onChange={setOrigin} exclude={destination} placeholder="e.g. Dhaka" inputId="from-district" />
        <button type="button" onClick={swap} aria-label="Swap origin and destination" className="mt-6 hidden rounded-full border border-slate-200 p-2 text-slate-500 hover:bg-slate-50 md:block"><ArrowLeftRight className="h-4 w-4" /></button>
        <DistrictInput label="To District" value={destination} onChange={setDestination} exclude={origin} placeholder="e.g. Chattogram" inputId="to-district" />
        <div>
          <label className="label" htmlFor="journey-date">Journey date</label>
          <div className="relative">
            <Calendar className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-accent-500" />
            <input id="journey-date" type="date" className="input pl-9" min={todayBD()} max={todayBD(29)} value={date} onChange={(e) => setDate(e.target.value)} required />
          </div>
        </div>
      </div>
      {error && <Alert>{error}</Alert>}
      <VoiceSearch onParsed={onParsed} />
      <button type="submit" className="btn-primary w-full py-3 text-base"><Search className="h-5 w-5" />Search Buses</button>
    </form>
  )
}
