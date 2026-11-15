import { Mic, MicOff, Repeat, Volume2, VolumeX, Square } from 'lucide-react'
import { useRecognizer } from '../hooks/useSpeech'
import { useVoice } from '../context/VoiceContext'
import { parseCommand } from '../utils/voiceCommands'

/**
 * Compact voice bar used on Results / Booking / Tickets: speak on/off, stop, repeat,
 * and a mic that turns a spoken command into an intent handled by the page (`onCommand`).
 * Commands never act on their own - pages route them into the normal confirmed flows.
 */
export default function VoiceControls({ onCommand, hint }) {
  const voice = useVoice()
  const rec = useRecognizer({
    onResult: (text) => {
      const cmd = parseCommand(text)
      if (cmd?.type === 'stop') return voice.stop()
      if (cmd?.type === 'repeat') return voice.repeat()
      if (!cmd) return voice.speak("Sorry, I didn't understand that command.", { force: true })
      onCommand?.(cmd, text)
    },
  })
  return (
    <div className="no-print card flex flex-wrap items-center gap-2 px-3 py-2.5" aria-label="Voice controls">
      {rec.supported ? (
        <button onClick={rec.listening ? rec.stop : rec.start} aria-pressed={rec.listening}
          className={`btn ${rec.listening ? 'bg-red-600 text-white animate-pulseRing' : 'bg-accent-500 text-white hover:bg-accent-600'}`}>
          {rec.listening ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}{rec.listening ? 'Listening...' : 'Voice command'}
        </button>
      ) : <span className="text-xs text-slate-500">Voice input unavailable in this browser - use the buttons.</span>}
      <button className="btn-ghost" onClick={voice.repeat} title="Repeat the last spoken response"><Repeat className="h-4 w-4" />Repeat</button>
      <button className="btn-ghost" onClick={voice.stop} title="Stop speaking"><Square className="h-4 w-4" />Stop</button>
      {voice.supported && (
        <button className="btn-ghost" onClick={voice.toggle} aria-pressed={voice.enabled}>
          {voice.enabled ? <Volume2 className="h-4 w-4" /> : <VolumeX className="h-4 w-4" />}{voice.enabled ? 'Voice on' : 'Voice off'}
        </button>
      )}
      <p className="w-full text-xs text-slate-500" aria-live="polite">
        {rec.error ? <span className="text-red-600">{rec.error}</span> : rec.listening ? `Heard: "${rec.transcript || '...'}"` : hint}
      </p>
    </div>
  )
}
