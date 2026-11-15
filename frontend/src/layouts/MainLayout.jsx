import { LogOut, Menu, Shield, Ticket, User, X, Search, Home as HomeIcon } from 'lucide-react'
import { useState } from 'react'
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import Logo from '../components/Logo'
import { useAuth } from '../context/AuthContext'

const linkCls = ({ isActive }) => `rounded-lg px-3 py-2 text-sm font-medium transition ${isActive ? 'bg-white/15 text-white' : 'text-navy-100 hover:bg-white/10 hover:text-white'}`

export default function MainLayout() {
  const { user, logout, isAdmin } = useAuth()
  const [open, setOpen] = useState(false)
  const nav = useNavigate()
  const doLogout = async () => { await logout(); setOpen(false); nav('/') }
  const close = () => setOpen(false)
  return (
    <div className="flex min-h-screen flex-col">
      <header className="no-print sticky top-0 z-40 bg-navy-900 shadow-md">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4">
          <Link to="/" className="flex items-center gap-2.5 text-white" onClick={close}><Logo /><span className="text-lg font-bold tracking-tight">VoiceRoute</span></Link>
          <nav className="hidden items-center gap-1 md:flex" aria-label="Main">
            <NavLink to="/" end className={linkCls}>Home</NavLink>
            <NavLink to="/search" className={linkCls}>Search Buses</NavLink>
            <NavLink to="/my-tickets" className={linkCls}>My Tickets</NavLink>
            {isAdmin && <NavLink to="/admin" className={linkCls}>Admin</NavLink>}
          </nav>
          <div className="hidden items-center gap-2 md:flex">
            {user ? (
              <>
                <span className="flex items-center gap-1.5 text-sm text-navy-100"><User className="h-4 w-4" />{user.full_name.split(' ')[0]}</span>
                <button onClick={doLogout} className="btn bg-white/10 text-white hover:bg-white/20"><LogOut className="h-4 w-4" />Logout</button>
              </>
            ) : (
              <>
                <Link to="/login" className="rounded-lg px-3 py-2 text-sm font-medium text-white hover:bg-white/10">Login</Link>
                <Link to="/register" className="btn-accent">Register</Link>
              </>
            )}
          </div>
          <button className="rounded-lg p-2 text-white md:hidden" onClick={() => setOpen((v) => !v)} aria-label="Toggle menu" aria-expanded={open}>{open ? <X /> : <Menu />}</button>
        </div>
        {open && (
          <nav className="space-y-1 border-t border-white/10 px-4 pb-4 pt-2 md:hidden" aria-label="Mobile">
            <NavLink to="/" end className={linkCls} onClick={close}><span className="flex items-center gap-2"><HomeIcon className="h-4 w-4" />Home</span></NavLink>
            <NavLink to="/search" className={linkCls} onClick={close}><span className="flex items-center gap-2"><Search className="h-4 w-4" />Search Buses</span></NavLink>
            <NavLink to="/my-tickets" className={linkCls} onClick={close}><span className="flex items-center gap-2"><Ticket className="h-4 w-4" />My Tickets</span></NavLink>
            {isAdmin && <NavLink to="/admin" className={linkCls} onClick={close}><span className="flex items-center gap-2"><Shield className="h-4 w-4" />Admin</span></NavLink>}
            <div className="pt-2">
              {user ? <button onClick={doLogout} className="btn w-full bg-white/10 text-white"><LogOut className="h-4 w-4" />Logout ({user.full_name.split(' ')[0]})</button>
                : <div className="flex gap-2"><Link to="/login" onClick={close} className="btn flex-1 bg-white/10 text-white">Login</Link><Link to="/register" onClick={close} className="btn-accent flex-1">Register</Link></div>}
            </div>
          </nav>
        )}
      </header>
      <main className="flex-1"><Outlet /></main>
      <footer className="no-print mt-16 bg-navy-950 text-navy-200">
        <div className="mx-auto grid max-w-6xl gap-6 px-4 py-10 sm:grid-cols-3">
          <div><div className="flex items-center gap-2 text-white"><Logo className="h-7 w-7" /><span className="font-bold">VoiceRoute</span></div>
            <p className="mt-3 text-sm text-navy-300">Voice-based bus enquiry and booking for Bangladesh.</p></div>
          <div className="text-sm"><p className="mb-2 font-semibold text-white">Explore</p>
            <ul className="space-y-1.5"><li><Link className="hover:text-white" to="/search">Search buses</Link></li><li><Link className="hover:text-white" to="/my-tickets">My tickets</Link></li><li><Link className="hover:text-white" to="/login">Login</Link></li></ul></div>
          <p className="text-xs leading-relaxed text-navy-300"><strong className="text-navy-100">Academic demonstration.</strong> VoiceRoute is a Database Management Systems course project. All operators, buses, fares and schedules are fictional sample data and are not affiliated with any real transport company. Not for real ticket sales.</p>
        </div>
      </footer>
    </div>
  )
}
