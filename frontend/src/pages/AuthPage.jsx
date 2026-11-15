import { Loader2, Lock, Phone, User } from 'lucide-react'
import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import Logo from '../components/Logo'
import { Alert } from '../components/ui'
import { useAuth } from '../context/AuthContext'

export default function AuthPage({ mode }) {
  const isReg = mode === 'register'
  const { login, register } = useAuth()
  const nav = useNavigate()
  const loc = useLocation()
  const [f, setF] = useState({ full_name: '', phone_number: '', password: '', confirm_password: '', remember_me: true })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const set = (k) => (e) => setF((s) => ({ ...s, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value }))

  const validate = () => {
    if (isReg && f.full_name.trim().length < 2) return 'Please enter your full name.'
    if (!/^(?:\+?880|0)?1[3-9]\d{8}$/.test(f.phone_number.replace(/[\s-]/g, ''))) return 'Enter a valid Bangladeshi mobile number, e.g. 01712345678.'
    if (isReg) {
      if (f.password.length < 8 || !/[A-Za-z]/.test(f.password) || !/\d/.test(f.password)) return 'Password must be at least 8 characters with a letter and a number.'
      if (f.password !== f.confirm_password) return 'Passwords do not match.'
    } else if (!f.password) return 'Please enter your password.'
    return ''
  }

  const submit = async (e) => {
    e.preventDefault()
    const v = validate(); if (v) return setError(v)
    setBusy(true); setError('')
    try {
      const phone = f.phone_number.replace(/[\s-]/g, '')
      if (isReg) await register({ ...f, phone_number: phone })
      else await login({ phone_number: phone, password: f.password, remember_me: f.remember_me })
      nav(loc.state?.from || '/', { replace: true })
    } catch (err) { setError(err.message) } finally { setBusy(false) }
  }

  return (
    <div className="mx-auto flex max-w-md flex-col px-4 py-12">
      <div className="card p-6 shadow-pop animate-rise sm:p-8">
        <div className="mb-6 flex flex-col items-center text-center"><Logo className="h-12 w-12" />
          <h1 className="mt-3 text-2xl font-bold text-navy-900">{isReg ? 'Create your account' : 'Welcome back'}</h1>
          <p className="text-sm text-slate-500">{isReg ? 'Register to book and manage tickets.' : 'Log in to book and view your tickets.'}</p></div>
        <form onSubmit={submit} className="space-y-4" noValidate>
          {isReg && <Field icon={User} label="Full name" value={f.full_name} onChange={set('full_name')} autoComplete="name" placeholder="Your full name" />}
          <Field icon={Phone} label="Phone number" type="tel" value={f.phone_number} onChange={set('phone_number')} autoComplete="tel" placeholder="01712345678" />
          <Field icon={Lock} label="Password" type="password" value={f.password} onChange={set('password')} autoComplete={isReg ? 'new-password' : 'current-password'} placeholder={isReg ? 'At least 8 characters, letters and numbers' : 'Your password'} />
          {isReg && <Field icon={Lock} label="Confirm password" type="password" value={f.confirm_password} onChange={set('confirm_password')} autoComplete="new-password" placeholder="Repeat password" />}
          <label className="flex items-center gap-2 text-sm text-slate-600"><input type="checkbox" checked={f.remember_me} onChange={set('remember_me')} />Remember me</label>
          {error && <Alert>{error}</Alert>}
          <button className="btn-primary w-full py-3" disabled={busy}>{busy && <Loader2 className="h-4 w-4 animate-spin" />}{isReg ? 'Create account' : 'Log in'}</button>
        </form>
        <p className="mt-5 text-center text-sm text-slate-500">
          {isReg ? <>Already registered? <Link to="/login" state={loc.state} className="font-semibold text-accent-600 hover:underline">Log in</Link></>
            : <>New to VoiceRoute? <Link to="/register" state={loc.state} className="font-semibold text-accent-600 hover:underline">Create an account</Link></>}
        </p>
      </div>
    </div>
  )
}

function Field({ icon: Icon, label, ...props }) {
  return (
    <div><label className="label">{label}</label>
      <div className="relative"><Icon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" /><input className="input pl-9" {...props} /></div></div>
  )
}
