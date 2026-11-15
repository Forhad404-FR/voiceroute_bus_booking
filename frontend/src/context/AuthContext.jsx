import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { api } from '../services/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let alive = true
    api.get('/auth/me').then((d) => alive && setUser(d.user)).catch(() => alive && setUser(null)).finally(() => alive && setLoading(false))
    return () => { alive = false }
  }, [])

  const login = useCallback(async (payload) => { const d = await api.post('/auth/login', payload); setUser(d.user); return d.user }, [])
  const register = useCallback(async (payload) => { const d = await api.post('/auth/register', payload); setUser(d.user); return d.user }, [])
  const logout = useCallback(async () => { try { await api.post('/auth/logout') } finally { setUser(null) } }, [])

  const value = useMemo(() => ({ user, loading, login, register, logout, isAdmin: user?.role === 'ADMIN' }), [user, loading, login, register, logout])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export const useAuth = () => useContext(AuthContext)
