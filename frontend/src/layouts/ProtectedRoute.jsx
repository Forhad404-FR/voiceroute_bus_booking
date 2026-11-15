import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { Spinner } from '../components/ui'
import { useAuth } from '../context/AuthContext'

// UX guard only. Real protection is enforced by the API (401/403 on every protected endpoint).
export default function ProtectedRoute({ admin = false }) {
  const { user, loading } = useAuth()
  const loc = useLocation()
  if (loading) return <Spinner label="Checking your session..." />
  if (!user) return <Navigate to="/login" replace state={{ from: loc.pathname + loc.search }} />
  if (admin && user.role !== 'ADMIN') return <Navigate to="/" replace />
  return <Outlet />
}
