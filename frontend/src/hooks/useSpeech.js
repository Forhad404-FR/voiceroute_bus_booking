import { useCallback, useEffect, useRef, useState } from 'react'

const SR = typeof window !== 'undefined' ? window.SpeechRecognition || window.webkitSpeechRecognition : null
export const speechRecognitionSupported = !!SR
export const speechSynthesisSupported = typeof window !== 'undefined' && 'speechSynthesis' in window

/** Text-to-speech (browser SpeechSynthesis). Remembers the last utterance for "repeat". */
export function useSpeaker() {
  const lastRef = useRef('')
  const [speaking, setSpeaking] = useState(false)
  const [enabled, setEnabled] = useState(() => { try { return localStorage.getItem('vr_voice') !== 'off' } catch { return true } })

  const stop = useCallback(() => { if (speechSynthesisSupported) window.speechSynthesis.cancel(); setSpeaking(false) }, [])

  const speak = useCallback((text, { force = false } = {}) => {
    if (!text) return
    lastRef.current = text
    if (!speechSynthesisSupported || (!enabled && !force)) return
    window.speechSynthesis.cancel()
    const u = new SpeechSynthesisUtterance(text)
    u.lang = 'en-US'; u.rate = 0.98
    u.onstart = () => setSpeaking(true)
    u.onend = () => setSpeaking(false)
    u.onerror = () => setSpeaking(false)
    window.speechSynthesis.speak(u)
  }, [enabled])

  const repeat = useCallback(() => { if (lastRef.current) speak(lastRef.current, { force: true }) }, [speak])
  const toggle = useCallback(() => {
    setEnabled((v) => { const n = !v; try { localStorage.setItem('vr_voice', n ? 'on' : 'off') } catch { /* ignore */ } if (!n) stop(); return n })
  }, [stop])

  useEffect(() => () => { if (speechSynthesisSupported) window.speechSynthesis.cancel() }, [])
  return { speak, stop, repeat, speaking, enabled, toggle, supported: speechSynthesisSupported, last: () => lastRef.current }
}

/** Speech-to-text (browser SpeechRecognition). One utterance per start(). */
export function useRecognizer({ lang = 'en-US', onResult } = {}) {
  const recRef = useRef(null)
  const cbRef = useRef(onResult)
  cbRef.current = onResult
  const [listening, setListening] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [error, setError] = useState('')

  const stop = useCallback(() => { try { recRef.current?.stop() } catch { /* ignore */ } }, [])

  const start = useCallback(() => {
    setError('')
    if (!SR) { setError('Voice recognition is not supported in this browser. Please type instead (Chrome or Edge work best).'); return }
    if (speechSynthesisSupported) window.speechSynthesis.cancel() // do not listen to ourselves
    try { recRef.current?.abort() } catch { /* ignore */ }
    const rec = new SR()
    rec.lang = lang; rec.interimResults = true; rec.maxAlternatives = 1; rec.continuous = false
    let finalText = ''
    rec.onstart = () => { setListening(true); setTranscript('') }
    rec.onresult = (e) => {
      let interim = ''
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const t = e.results[i][0].transcript
        if (e.results[i].isFinal) finalText += t; else interim += t
      }
      setTranscript((finalText + ' ' + interim).trim())
    }
    rec.onerror = (e) => {
      const map = {
        'not-allowed': 'Microphone access was blocked. Allow the microphone in your browser settings, or type instead.',
        'service-not-allowed': 'Microphone access was blocked. Allow the microphone in your browser settings, or type instead.',
        'no-speech': "I didn't hear anything. Tap the microphone and try again.",
        'audio-capture': 'No microphone was found on this device.',
        network: 'Voice recognition needs an internet connection.',
      }
      if (e.error !== 'aborted') setError(map[e.error] || 'Voice recognition failed. Please try again or type instead.')
    }
    rec.onend = () => { setListening(false); const t = finalText.trim(); if (t) cbRef.current?.(t) }
    recRef.current = rec
    try { rec.start() } catch { setError('Could not start the microphone. Please try again.') }
  }, [lang])

  useEffect(() => () => { try { recRef.current?.abort() } catch { /* ignore */ } }, [])
  return { start, stop, listening, transcript, setTranscript, error, setError, supported: !!SR }
}
