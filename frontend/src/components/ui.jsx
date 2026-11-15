import { AlertTriangle, CheckCircle2, Inbox, Loader2, XCircle } from 'lucide-react'
import { useEffect } from 'react'
import { statusLabel } from '../utils/format'

export function Spinner({ label = 'Loading...' }) {
  return (
    <div className="flex items-center justify-center gap-2 py-16 text-slate-500" role="status">
      <Loader2 className="h-5 w-5 animate-spin" /> <span className="text-sm">{label}</span>
    </div>
  )
}

export function Empty({ icon: Icon = Inbox, title, children, action }) {
  return (
    <div className="card mx-auto flex max-w-lg flex-col items-center px-6 py-12 text-center animate-rise">
      <div className="mb-3 rounded-full bg-navy-50 p-3 text-navy-600"><Icon className="h-6 w-6" /></div>
      <h3 className="text-lg font-semibold text-navy-900">{title}</h3>
      {children && <div className="mt-1 text-sm text-slate-500">{children}</div>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  )
}

export function Alert({ kind = 'error', children, onClose }) {
  const styles = { error: 'bg-red-50 text-red-800 border-red-200', success: 'bg-emerald-50 text-emerald-800 border-emerald-200', info: 'bg-accent-50 text-accent-700 border-accent-100', warn: 'bg-amber-50 text-amber-800 border-amber-200' }
  const Icon = kind === 'success' ? CheckCircle2 : kind === 'error' ? XCircle : AlertTriangle
  return (
    <div role={kind === 'error' ? 'alert' : 'status'} className={`flex items-start gap-2 rounded-xl border px-3.5 py-3 text-sm ${styles[kind]}`}>
      <Icon className="mt-0.5 h-4 w-4 shrink-0" /><div className="flex-1">{children}</div>
      {onClose && <button onClick={onClose} className="text-xs font-semibold underline">Dismiss</button>}
    </div>
  )
}

export function StatusBadge({ status }) {
  const map = { CONFIRMED: 'bg-emerald-100 text-emerald-800', CANCELLED: 'bg-red-100 text-red-700', COMPLETED: 'bg-slate-200 text-slate-700', ACTIVE: 'bg-emerald-100 text-emerald-800' }
  return <span className={`badge ${map[status] || 'bg-slate-100 text-slate-700'}`}>{statusLabel(status)}</span>
}

export function SampleBanner() {
  return (
    <div className="rounded-xl border border-amber-200 bg-amber-50 px-3.5 py-2 text-xs text-amber-800">
      <strong>Demonstration data.</strong> Operators, buses, fares and schedules are fictional sample data for an academic project - not live operator information.
    </div>
  )
}

export function ConfirmDialog({ open, title, children, confirmLabel = 'Confirm', cancelLabel = 'Go back', danger, busy, onConfirm, onCancel }) {
  useEffect(() => {
    if (!open) return
    const onKey = (e) => { if (e.key === 'Escape') onCancel?.() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onCancel])
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-navy-950/50 p-4 sm:items-center" role="dialog" aria-modal="true" aria-label={title}>
      <div className="card w-full max-w-md p-6 shadow-pop animate-rise">
        <h3 className="text-lg font-semibold text-navy-900">{title}</h3>
        <div className="mt-2 text-sm text-slate-600">{children}</div>
        <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <button className="btn-ghost" onClick={onCancel} disabled={busy}>{cancelLabel}</button>
          <button className={danger ? 'btn-danger' : 'btn-primary'} onClick={onConfirm} disabled={busy}>
            {busy && <Loader2 className="h-4 w-4 animate-spin" />}{confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
