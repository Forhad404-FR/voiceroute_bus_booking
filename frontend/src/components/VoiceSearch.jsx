import { Mic, MicOff, Search } from 'lucide-react'
import { useState } from 'react'
import { useRecognizer } from '../hooks/useSpeech'
import { useVoice } from '../context/VoiceContext'
import { api } from '../services/api'
import { Alert } from './ui'

/**
 * Voice / natural-language route search. The recognised text stays editable; "Fill fields" sends it to
 * GET /api/routes/parse (server-side parser, aliases like Chittagong -> Chattogram) and fills From/To.
 * The same parser powers typed phrases such as "Dhaka to C".
 */
export default function VoiceSearch({ onParsed }) {
  const voice = useVoice()
  const [text, setText] = useState('')
  const [msg, setMsg] = useState(null)
  const [busy, setBusy] = useState(false)

  const run = async (phrase) => {
    const q = (phrase ?? text).trim()
    if (!q) { setMsg({ kind: 'info', text: 'Say or type a route, for example "Dhaka to Sylhet".' }); return }
    setBusy(true); setMsg(null)
    try {
      const p = await api.get('/routes/parse', { q })
      if (!p.understood) {
        const m = "Sorry, I couldn't understand that route. Please say it again, like \"Dhaka to Sylhet\", or use the fields."
        setMsg({ kind: 'warn', text: m }); voice.speak(m); return
      }
      onParsed(p)
      const bits = []
      if (p.origin) bits.push(`from ${p.origin}`)
      if (p.destination) bits.push(`to ${p.destination}`)
      let said
      if (p.origin && p.destination) said = `Got it. Buses ${bits.join(' ')}. Choose a date and press Search.`
      else if (p.origin) said = `Starting from ${p.origin}. Where would you like to go?`
      else if (p.destination) said = `Going to ${p.destination}. Where are you starting from?`
      else said = 'I found several matching districts. Please choose from the suggestions.'
      setMsg({ kind: 'success', text: said }); voice.speak(said)
    } catch (e) { setMsg({ kind: 'error', text: e.message }) } finally { setBusy(false) }
  }

  const rec = useRecognizer({ onResult: (t) => { setText(t); run(t) } })

  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 p-3.5">
      <div className="flex items-center gap-2">
        {rec.supported ? (
          <button type="button" onClick={rec.listening ? rec.stop : rec.start} aria-pressed={rec.listening} aria-label={rec.listening ? 'Stop listening' : 'Start voice search'}
            className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-full text-white transition ${rec.listening ? 'bg-red-600 animate-pulseRing' : 'bg-accent-500 hover:bg-accent-600'}`}>
            {rec.listening ? <MicOff className="h-5 w-5" /> : <Mic className="h-5 w-5" />}
          </button>
        ) : null}
        <input className="input" value={rec.listening ? rec.transcript : text} onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); run() } }}
          placeholder={rec.supported ? 'Tap the mic and say "Dhaka to Sylhet" - or type it' : 'Type a route, e.g. "Dhaka to Sylhet"'} aria-label="Voice or text route search" />
        <button type="button" className="btn-primary shrink-0" onClick={() => run()} disabled={busy}><Search className="h-4 w-4" /><span className="hidden sm:inline">Fill fields</span></button>
      </div>
      <p className="mt-2 text-xs text-slate-500" aria-live="polite">
        {rec.listening ? 'Listening... speak now.' : rec.supported ? 'Try: "I want to go from Dhaka to Sylhet", "Show me buses to Cox\'s Bazar".' : 'Voice recognition is not available in this browser (Chrome/Edge recommended) - typing works everywhere.'}
      </p>
      {(rec.error || msg) && <div className="mt-2"><Alert kind={rec.error ? 'error' : msg.kind}>{rec.error || msg.text}</Alert></div>}
    </div>
  )
}
