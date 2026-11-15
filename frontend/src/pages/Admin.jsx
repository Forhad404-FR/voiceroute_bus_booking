import { AlertTriangle, BarChart3, Bus, CalendarClock, ClipboardList, Pencil, Plus, ScrollText, Trash2, Users, Building2 } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { Alert, ConfirmDialog, Empty, Spinner, StatusBadge } from '../components/ui'
import { api } from '../services/api'
import { prettyDate, prettyDateTimeUtc, taka, time12 } from '../utils/format'

const TABS = [
  ['overview', 'Overview', BarChart3], ['bookings', 'Bookings', ClipboardList], ['buses', 'Buses', Bus],
  ['schedules', 'Schedules', CalendarClock], ['catalog', 'Districts & Operators', Building2],
  ['alerts', 'Low-seat alerts', AlertTriangle], ['audit', 'Audit log', ScrollText], ['users', 'Users', Users],
]

export default function Admin() {
  const [tab, setTab] = useState('overview')
  return (
    <div className="mx-auto max-w-6xl space-y-5 px-4 py-8">
      <div><h1 className="text-2xl font-bold text-navy-900">Admin dashboard</h1><p className="text-sm text-slate-500">Every request here is authorised on the server; hiding buttons is not the security layer.</p></div>
      <div className="flex gap-1 overflow-x-auto rounded-xl bg-white p-1 shadow-card" role="tablist">
        {TABS.map(([k, label, Icon]) => (
          <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)}
            className={`flex shrink-0 items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium ${tab === k ? 'bg-navy-900 text-white' : 'text-slate-600 hover:bg-slate-100'}`}><Icon className="h-4 w-4" />{label}</button>
        ))}
      </div>
      {tab === 'overview' && <Overview />}
      {tab === 'bookings' && <Bookings />}
      {tab === 'buses' && <Buses />}
      {tab === 'schedules' && <Schedules />}
      {tab === 'catalog' && <Catalog />}
      {tab === 'alerts' && <Alerts />}
      {tab === 'audit' && <Audit />}
      {tab === 'users' && <UsersTab />}
    </div>
  )
}

function useLoad(path, key) {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const reload = useCallback(() => api.get(path).then((d) => { setData(key ? d[key] : d); setError('') }).catch((e) => setError(e.message)), [path, key])
  useEffect(() => { reload() }, [reload])
  return { data, error, reload }
}

function Table({ cols, rows, empty = 'Nothing to show.' }) {
  if (!rows.length) return <Empty title={empty} />
  return (
    <div className="card overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500"><tr>{cols.map((c) => <th key={c.h} className="whitespace-nowrap px-3 py-2.5 font-semibold">{c.h}</th>)}</tr></thead>
        <tbody className="divide-y divide-slate-100">{rows.map((r, i) => <tr key={r.id ?? i} className="hover:bg-slate-50/60">{cols.map((c) => <td key={c.h} className="whitespace-nowrap px-3 py-2.5">{c.r(r)}</td>)}</tr>)}</tbody>
      </table>
    </div>
  )
}

function Stat({ label, value, tone = 'text-navy-900' }) {
  return <div className="card p-4"><p className="label !mb-1">{label}</p><p className={`text-2xl font-extrabold ${tone}`}>{value}</p></div>
}

function Overview() {
  const { data, error } = useLoad('/admin/dashboard')
  if (error) return <Alert>{error}</Alert>
  if (!data) return <Spinner />
  const t = data.totals
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="Total users" value={t.total_users} /><Stat label="Total buses" value={t.total_buses} />
        <Stat label="Total routes" value={t.total_routes} /><Stat label="Total schedules" value={t.total_schedules} />
        <Stat label="Total bookings" value={t.total_bookings} /><Stat label="Confirmed" value={t.confirmed_bookings} tone="text-emerald-700" />
        <Stat label="Cancelled" value={t.cancelled_bookings} tone="text-red-600" /><Stat label="Revenue" value={taka(t.total_revenue)} />
      </div>
      <section><h2 className="mb-2 font-semibold text-navy-900">Popular routes</h2>
        <Table empty="No bookings yet." rows={data.popular_routes} cols={[{ h: 'Route', r: (r) => `${r.origin} → ${r.destination}` }, { h: 'Bookings', r: (r) => r.bookings }, { h: 'Seats sold', r: (r) => r.seats_sold }, { h: 'Revenue', r: (r) => taka(r.revenue) }]} /></section>
      <section><h2 className="mb-2 font-semibold text-navy-900">Recent bookings</h2><BookingTable rows={data.recent_bookings} /></section>
      <section><h2 className="mb-2 font-semibold text-navy-900">Low-seat alerts ({t.open_low_seat_alerts} open)</h2><AlertTable rows={data.low_seat_alerts} /></section>
    </div>
  )
}

const BookingTable = ({ rows }) => (
  <Table empty="No bookings yet." rows={rows} cols={[
    { h: 'Reference', r: (r) => <span className="font-mono font-semibold">{r.booking_reference}</span> }, { h: 'Passenger', r: (r) => r.passenger_name },
    { h: 'Route', r: (r) => `${r.origin} → ${r.destination}` }, { h: 'Departure', r: (r) => `${prettyDate(r.departure_date)} ${time12(r.departure_time)}` },
    { h: 'Seats', r: (r) => r.seats }, { h: 'Fare', r: (r) => taka(r.total_fare) }, { h: 'Status', r: (r) => <StatusBadge status={r.booking_status} /> },
    { h: 'Booked', r: (r) => prettyDateTimeUtc(r.booked_at) }]} />
)
const AlertTable = ({ rows }) => (
  <Table empty="No low-seat alerts." rows={rows} cols={[
    { h: 'Route', r: (r) => `${r.origin} → ${r.destination}` }, { h: 'Bus', r: (r) => r.bus_name }, { h: 'Departure', r: (r) => `${prettyDate(r.departure_date)} ${time12(r.departure_time)}` },
    { h: 'Seats left', r: (r) => <strong className={r.resolved_at ? '' : 'text-red-600'}>{r.available_seats}</strong> }, { h: 'Raised', r: (r) => prettyDateTimeUtc(r.created_at) },
    { h: 'State', r: (r) => (r.resolved_at ? <span className="badge bg-slate-100 text-slate-600">Resolved</span> : <span className="badge bg-red-100 text-red-700">Open</span>) }]} />
)

function Bookings() {
  const [status, setStatus] = useState('')
  const { data, error } = useLoad(`/admin/bookings${status ? `?status=${status}` : ''}`, 'bookings')
  return (<div className="space-y-3">
    <select aria-label="Status" className="input !w-auto" value={status} onChange={(e) => setStatus(e.target.value)}><option value="">All statuses</option><option>CONFIRMED</option><option>CANCELLED</option><option>COMPLETED</option></select>
    {error ? <Alert>{error}</Alert> : !data ? <Spinner /> : <BookingTable rows={data} />}</div>)
}

function Alerts() { const { data, error } = useLoad('/admin/low-seat-alerts', 'alerts'); return error ? <Alert>{error}</Alert> : !data ? <Spinner /> : <AlertTable rows={data} /> }
function Audit() {
  const { data, error } = useLoad('/admin/audit-logs', 'audit_logs')
  if (error) return <Alert>{error}</Alert>; if (!data) return <Spinner />
  return <Table empty="No audit entries yet." rows={data} cols={[{ h: 'When', r: (r) => prettyDateTimeUtc(r.created_at) }, { h: 'Action', r: (r) => <span className="badge bg-navy-50 text-navy-700">{r.action}</span> }, { h: 'Reference', r: (r) => r.booking_reference || '-' }, { h: 'User', r: (r) => r.user_name || '-' }, { h: 'Details', r: (r) => <span className="whitespace-normal">{r.details}</span> }]} />
}
function UsersTab() {
  const { data, error } = useLoad('/admin/users', 'users')
  if (error) return <Alert>{error}</Alert>; if (!data) return <Spinner />
  return <Table rows={data} cols={[{ h: 'Name', r: (r) => r.full_name }, { h: 'Phone', r: (r) => r.phone_number }, { h: 'Role', r: (r) => r.role }, { h: 'Bookings', r: (r) => r.bookings }, { h: 'Joined', r: (r) => prettyDateTimeUtc(r.created_at) }]} />
}
function Catalog() {
  const d = useLoad('/admin/districts', 'districts'); const o = useLoad('/admin/operators', 'operators')
  if (d.error || o.error) return <Alert>{d.error || o.error}</Alert>; if (!d.data || !o.data) return <Spinner />
  return (<div className="grid gap-6 lg:grid-cols-2">
    <section><h2 className="mb-2 font-semibold text-navy-900">Districts ({d.data.length})</h2><Table rows={d.data} cols={[{ h: '#', r: (r) => r.id }, { h: 'District', r: (r) => r.district_name }, { h: 'Stations', r: (r) => r.stations }]} /></section>
    <section><h2 className="mb-2 font-semibold text-navy-900">Operators ({o.data.length}) <span className="text-xs font-normal text-amber-700">fictional demo data</span></h2><Table rows={o.data} cols={[{ h: 'Operator', r: (r) => r.operator_name }, { h: 'Buses', r: (r) => r.buses }, { h: 'Contact', r: (r) => r.contact_phone }]} /></section></div>)
}

// ---------------------------------------------------------------- buses CRUD
const EMPTY_BUS = { operator_id: '', bus_name: '', bus_type: 'AC', registration_number: '', total_seats: 40, is_active: true }
function Buses() {
  const { data, error, reload } = useLoad('/admin/buses', 'buses')
  const ops = useLoad('/admin/operators', 'operators')
  const [form, setForm] = useState(null)
  const [del, setDel] = useState(null)
  const [msg, setMsg] = useState(null)
  const save = async (e) => {
    e.preventDefault(); setMsg(null)
    const body = { ...form, operator_id: Number(form.operator_id), total_seats: Number(form.total_seats) }
    try { form.id ? await api.put(`/admin/buses/${form.id}`, body) : await api.post('/admin/buses', body); setForm(null); setMsg({ k: 'success', t: 'Bus saved.' }); reload() }
    catch (err) { setMsg({ k: 'error', t: err.message }) }
  }
  const remove = async () => { try { await api.del(`/admin/buses/${del.id}`); setMsg({ k: 'success', t: 'Bus deleted.' }); reload() } catch (err) { setMsg({ k: 'error', t: err.message }) } setDel(null) }
  if (error) return <Alert>{error}</Alert>; if (!data || !ops.data) return <Spinner />
  return (<div className="space-y-3">
    <div className="flex items-center justify-between"><p className="text-sm text-slate-500">Existing schedules keep their seat capacity when a bus is edited.</p><button className="btn-primary" onClick={() => setForm({ ...EMPTY_BUS, operator_id: ops.data[0]?.id })}><Plus className="h-4 w-4" />Add bus</button></div>
    {msg && <Alert kind={msg.k} onClose={() => setMsg(null)}>{msg.t}</Alert>}
    {form && (
      <form onSubmit={save} className="card grid gap-3 p-4 sm:grid-cols-3">
        <div><label className="label">Operator</label><select className="input" value={form.operator_id} onChange={(e) => setForm({ ...form, operator_id: e.target.value })}>{ops.data.map((o) => <option key={o.id} value={o.id}>{o.operator_name}</option>)}</select></div>
        <div><label className="label">Bus name</label><input className="input" required minLength={2} value={form.bus_name} onChange={(e) => setForm({ ...form, bus_name: e.target.value })} /></div>
        <div><label className="label">Registration</label><input className="input" required minLength={3} value={form.registration_number} onChange={(e) => setForm({ ...form, registration_number: e.target.value })} /></div>
        <div><label className="label">Type</label><select className="input" value={form.bus_type} onChange={(e) => setForm({ ...form, bus_type: e.target.value })}><option value="AC">AC</option><option value="NON_AC">Non-AC</option></select></div>
        <div><label className="label">Total seats (8-60)</label><input type="number" min={8} max={60} className="input" required value={form.total_seats} onChange={(e) => setForm({ ...form, total_seats: e.target.value })} /></div>
        <label className="flex items-end gap-2 pb-2 text-sm"><input type="checkbox" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} />Active</label>
        <div className="flex gap-2 sm:col-span-3"><button className="btn-primary">Save</button><button type="button" className="btn-ghost" onClick={() => setForm(null)}>Cancel</button></div>
      </form>)}
    <Table rows={data} cols={[{ h: 'Operator', r: (r) => r.operator_name }, { h: 'Bus', r: (r) => r.bus_name }, { h: 'Type', r: (r) => (r.bus_type === 'AC' ? 'AC' : 'Non-AC') }, { h: 'Reg.', r: (r) => r.registration_number }, { h: 'Seats', r: (r) => r.total_seats }, { h: 'Schedules', r: (r) => r.schedules }, { h: 'Active', r: (r) => (r.is_active ? 'Yes' : 'No') },
      { h: 'Actions', r: (r) => <div className="flex gap-1"><button aria-label="Edit bus" className="btn-ghost !px-2 !py-1" onClick={() => setForm({ ...r, is_active: !!r.is_active })}><Pencil className="h-4 w-4" /></button><button aria-label="Delete bus" className="btn-ghost !px-2 !py-1 text-red-600" onClick={() => setDel(r)}><Trash2 className="h-4 w-4" /></button></div> }]} />
    <ConfirmDialog open={!!del} danger title="Delete bus?" confirmLabel="Delete" onConfirm={remove} onCancel={() => setDel(null)}>{del?.bus_name} will be removed. Buses with schedules cannot be deleted (database foreign key) - deactivate them instead.</ConfirmDialog>
  </div>)
}

// ---------------------------------------------------------------- schedules CRUD
function Schedules() {
  const { data, error, reload } = useLoad('/admin/schedules', 'schedules')
  const buses = useLoad('/admin/buses', 'buses'); const routes = useLoad('/admin/routes', 'routes')
  const [form, setForm] = useState(null); const [del, setDel] = useState(null); const [msg, setMsg] = useState(null)
  const save = async (e) => {
    e.preventDefault(); setMsg(null)
    try {
      if (form.id) await api.put(`/admin/schedules/${form.id}`, { departure_date: form.departure_date, departure_time: form.departure_time, arrival_time: form.arrival_time, fare: Number(form.fare), status: form.status })
      else await api.post('/admin/schedules', { bus_id: Number(form.bus_id), route_id: Number(form.route_id), departure_date: form.departure_date, departure_time: form.departure_time, arrival_time: form.arrival_time, fare: Number(form.fare), status: form.status })
      setForm(null); setMsg({ k: 'success', t: 'Schedule saved.' }); reload()
    } catch (err) { setMsg({ k: 'error', t: err.message }) }
  }
  const remove = async () => { try { await api.del(`/admin/schedules/${del.id}`); setMsg({ k: 'success', t: 'Schedule deleted.' }); reload() } catch (err) { setMsg({ k: 'error', t: err.message }) } setDel(null) }
  if (error) return <Alert>{error}</Alert>; if (!data || !buses.data || !routes.data) return <Spinner />
  const blank = { bus_id: buses.data[0]?.id, route_id: routes.data[0]?.id, departure_date: '', departure_time: '08:00', arrival_time: '14:00', fare: 800, status: 'ACTIVE' }
  return (<div className="space-y-3">
    <div className="flex items-center justify-between"><p className="text-sm text-slate-500">Upcoming schedules (first 200). Sample data.</p><button className="btn-primary" onClick={() => setForm(blank)}><Plus className="h-4 w-4" />Add schedule</button></div>
    {msg && <Alert kind={msg.k} onClose={() => setMsg(null)}>{msg.t}</Alert>}
    {form && (
      <form onSubmit={save} className="card grid gap-3 p-4 sm:grid-cols-3">
        {!form.id && <>
          <div><label className="label">Bus</label><select className="input" value={form.bus_id} onChange={(e) => setForm({ ...form, bus_id: e.target.value })}>{buses.data.filter((b) => b.is_active).map((b) => <option key={b.id} value={b.id}>{b.operator_name} - {b.bus_name}</option>)}</select></div>
          <div className="sm:col-span-2"><label className="label">Route</label><select className="input" value={form.route_id} onChange={(e) => setForm({ ...form, route_id: e.target.value })}>{routes.data.map((r) => <option key={r.id} value={r.id}>{r.origin} → {r.destination}</option>)}</select></div></>}
        <div><label className="label">Date</label><input type="date" required className="input" value={form.departure_date} onChange={(e) => setForm({ ...form, departure_date: e.target.value })} /></div>
        <div><label className="label">Departure</label><input type="time" required className="input" value={String(form.departure_time).slice(0, 5)} onChange={(e) => setForm({ ...form, departure_time: e.target.value })} /></div>
        <div><label className="label">Arrival</label><input type="time" required className="input" value={String(form.arrival_time).slice(0, 5)} onChange={(e) => setForm({ ...form, arrival_time: e.target.value })} /></div>
        <div><label className="label">Fare (BDT)</label><input type="number" min={0} step="1" required className="input" value={form.fare} onChange={(e) => setForm({ ...form, fare: e.target.value })} /></div>
        <div><label className="label">Status</label><select className="input" value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}><option>ACTIVE</option><option>CANCELLED</option></select></div>
        <div className="flex items-end gap-2"><button className="btn-primary">Save</button><button type="button" className="btn-ghost" onClick={() => setForm(null)}>Cancel</button></div>
      </form>)}
    <Table rows={data} cols={[{ h: 'Route', r: (r) => `${r.origin} → ${r.destination}` }, { h: 'Bus', r: (r) => `${r.operator_name} · ${r.bus_name}` }, { h: 'Date', r: (r) => prettyDate(r.departure_date) }, { h: 'Time', r: (r) => time12(r.departure_time) }, { h: 'Fare', r: (r) => taka(r.fare) }, { h: 'Seats', r: (r) => `${r.available_seats}/${r.total_seats}` }, { h: 'Status', r: (r) => <StatusBadge status={r.status} /> },
      { h: 'Actions', r: (r) => <div className="flex gap-1"><button aria-label="Edit schedule" className="btn-ghost !px-2 !py-1" onClick={() => setForm({ ...r })}><Pencil className="h-4 w-4" /></button><button aria-label="Delete schedule" className="btn-ghost !px-2 !py-1 text-red-600" onClick={() => setDel(r)}><Trash2 className="h-4 w-4" /></button></div> }]} />
    <ConfirmDialog open={!!del} danger title="Delete schedule?" confirmLabel="Delete" onConfirm={remove} onCancel={() => setDel(null)}>Schedules that already have bookings cannot be deleted - set them to CANCELLED instead.</ConfirmDialog>
  </div>)
}
