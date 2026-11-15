import { createContext, useContext } from 'react'
import { useSpeaker } from '../hooks/useSpeech'

const VoiceContext = createContext(null)
export function VoiceProvider({ children }) {
  const speaker = useSpeaker()
  return <VoiceContext.Provider value={speaker}>{children}</VoiceContext.Provider>
}
export const useVoice = () => useContext(VoiceContext)
