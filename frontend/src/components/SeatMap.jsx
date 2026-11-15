import { Armchair } from 'lucide-react'

export default function SeatMap({ seats, selected, onToggle, maxSeats = 6 }) {
  const rows = []
  seats.forEach((s) => { (rows[s.row] = rows[s.row] || []).push(s) })
  return (
    <div>
      <div className="mb-4 flex flex-wrap gap-4 text-xs text-slate-600">
        <Legend cls="border-slate-300 bg-white" label="Available" />
        <Legend cls="border-accent-600 bg-accent-500" label="Selected" />
        <Legend cls="border-slate-300 bg-slate-200" label="Booked" />
      </div>
      <div className="mx-auto w-full max-w-xs rounded-[2rem] border-2 border-slate-200 bg-slate-50 p-4">
        <div className="mb-3 flex justify-end text-xs text-slate-400"><span className="rounded-lg border border-slate-200 bg-white px-2 py-1">Driver</span></div>
        <div className="space-y-2">
          {rows.map((row, r) => (
            <div key={r} className="flex items-center justify-center gap-2">
              {row.map((s) => {
                const isSel = selected.includes(s.seat_number)
                const booked = s.status === 'BOOKED'
                const blocked = !booked && !isSel && selected.length >= maxSeats
                return (
                  <div key={s.seat_number} className={s.col === 2 ? 'ml-6' : ''}>
                    <button
                      type="button" disabled={booked || blocked} onClick={() => onToggle(s.seat_number)}
                      aria-pressed={isSel} aria-label={`Seat ${s.label}, ${booked ? 'booked' : isSel ? 'selected' : 'available'}`}
                      className={`flex h-11 w-11 flex-col items-center justify-center rounded-lg border text-[10px] font-bold transition sm:h-10 sm:w-10
                        ${booked ? 'cursor-not-allowed border-slate-300 bg-slate-200 text-slate-400'
                          : isSel ? 'border-accent-600 bg-accent-500 text-white shadow'
                          : 'border-slate-300 bg-white text-navy-800 hover:border-accent-500 hover:bg-accent-50 disabled:opacity-40'}`}>
                      <Armchair className="h-3.5 w-3.5" />{s.label}
                    </button>
                  </div>
                )
              })}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
const Legend = ({ cls, label }) => <span className="flex items-center gap-1.5"><span className={`h-4 w-4 rounded border ${cls}`} />{label}</span>
