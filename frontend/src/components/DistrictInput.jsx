import { MapPin, X } from 'lucide-react'
import { useEffect, useId, useRef, useState } from 'react'
import { api } from '../services/api'

/**
 * District autocomplete. Suggestions come from GET /api/districts/search (MySQL-backed) on every
 * keystroke; nothing is hard-coded. `exclude` removes the other field's district from the list.
 */
export default function DistrictInput({ label, value, onChange, exclude, placeholder, inputId }) {
  const [text, setText] = useState(value || '')
  const [open, setOpen] = useState(false)
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(false)
  const [active, setActive] = useState(0)
  const boxRef = useRef(null)
  const reqRef = useRef(0)
  const listId = useId()

  useEffect(() => { setText(value || '') }, [value])

  useEffect(() => {
    if (!open) return
    const id = ++reqRef.current
    setLoading(true)
    api.get('/districts/search', { q: value && text === value ? '' : text, exclude })
      .then((d) => { if (id === reqRef.current) { setItems(d.districts); setActive(0) } })
      .catch(() => { if (id === reqRef.current) setItems([]) })
      .finally(() => { if (id === reqRef.current) setLoading(false) })
  }, [text, open, exclude, value])

  useEffect(() => {
    const onDoc = (e) => { if (boxRef.current && !boxRef.current.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', onDoc); document.addEventListener('touchstart', onDoc)
    return () => { document.removeEventListener('mousedown', onDoc); document.removeEventListener('touchstart', onDoc) }
  }, [])

  const choose = (name) => { onChange(name); setText(name); setOpen(false) }
  const clear = () => { onChange(''); setText(''); setOpen(true) }

  const onKeyDown = (e) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); setOpen(true); setActive((a) => Math.min(a + 1, Math.max(items.length - 1, 0))) }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setActive((a) => Math.max(a - 1, 0)) }
    else if (e.key === 'Enter') { if (open && items[active]) { e.preventDefault(); choose(items[active].name) } }
    else if (e.key === 'Escape') { setOpen(false) }
  }

  return (
    <div ref={boxRef} className="relative">
      <label className="label" htmlFor={inputId || listId + '-i'}>{label}</label>
      <div className="relative">
        <MapPin className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-accent-500" />
        <input
          id={inputId || listId + '-i'} className={`input pl-9 pr-9 ${value ? 'font-semibold text-navy-900' : ''}`}
          placeholder={placeholder} autoComplete="off" value={text}
          role="combobox" aria-expanded={open} aria-controls={listId} aria-autocomplete="list"
          aria-activedescendant={open && items[active] ? `${listId}-${active}` : undefined}
          onFocus={() => setOpen(true)}
          onChange={(e) => { setText(e.target.value); if (value) onChange(''); setOpen(true) }}
          onKeyDown={onKeyDown}
        />
        {(text || value) && (
          <button type="button" aria-label={`Clear ${label}`} onClick={clear} className="absolute right-2 top-1/2 -translate-y-1/2 rounded-full p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700">
            <X className="h-4 w-4" />
          </button>
        )}
      </div>
      {open && (
        <ul id={listId} role="listbox" className="absolute z-30 mt-1 max-h-64 w-full overflow-auto rounded-xl border border-slate-200 bg-white py-1 shadow-pop animate-rise">
          {loading && items.length === 0 && <li className="px-3.5 py-2.5 text-sm text-slate-400">Searching...</li>}
          {!loading && items.length === 0 && (
            <li className="px-3.5 py-2.5 text-sm text-slate-500">No district matches "{text}". Check the spelling or pick from the list.</li>
          )}
          {items.map((d, i) => (
            <li key={d.id} id={`${listId}-${i}`} role="option" aria-selected={i === active}
              onMouseDown={(e) => { e.preventDefault(); choose(d.name) }} onMouseEnter={() => setActive(i)}
              className={`cursor-pointer px-3.5 py-2 text-sm ${i === active ? 'bg-accent-50 text-navy-900' : 'text-slate-700'}`}>
              {d.name}
            </li>
          ))}
        </ul>
      )}
      {value && <p className="mt-1 text-xs font-medium text-emerald-700">Selected: {value}</p>}
    </div>
  )
}
