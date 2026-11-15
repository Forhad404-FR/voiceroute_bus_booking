import { Bus, MapPin } from 'lucide-react'
import Logo from './Logo'
import { StatusBadge } from './ui'
import { prettyDate, prettyDateTimeUtc, seatList, taka, time12 } from '../utils/format'

/** Printable ticket. The .print-area class isolates it when the user chooses Print / Save as PDF. */
export default function TicketView({ b }) {
  return (
    <article className="print-area card overflow-hidden">
      <header className="flex items-center justify-between bg-navy-900 px-5 py-4 text-white">
        <div className="flex items-center gap-2.5"><Logo className="h-8 w-8" /><span className="font-semibold">VoiceRoute</span></div>
        <StatusBadge status={b.booking_status} />
      </header>
      <div className="space-y-5 p-5 sm:p-6">
        <div className="flex flex-wrap items-end justify-between gap-2">
          <div><p className="label">Booking reference</p><p className="font-mono text-xl font-bold tracking-wider text-navy-900">{b.booking_reference}</p></div>
          <div className="text-right"><p className="label">Passenger</p><p className="font-semibold text-navy-900">{b.passenger_name}</p></div>
        </div>
        <div className="flex items-center gap-3 rounded-xl bg-slate-50 p-4">
          <MapPin className="h-5 w-5 text-accent-500" />
          <div className="flex-1"><p className="text-lg font-bold text-navy-900">{b.origin}</p><p className="text-xs text-slate-500">{b.origin_station}</p></div>
          <Bus className="h-5 w-5 text-slate-400" />
          <div className="flex-1 text-right"><p className="text-lg font-bold text-navy-900">{b.destination}</p><p className="text-xs text-slate-500">{b.destination_station}</p></div>
        </div>
        <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm sm:grid-cols-3">
          <Item k="Date" v={prettyDate(b.departure_date)} />
          <Item k="Departure" v={time12(b.departure_time)} />
          <Item k="Arrival (est.)" v={time12(b.arrival_time)} />
          <Item k="Operator" v={b.operator_name} />
          <Item k="Bus" v={`${b.bus_name} (${b.bus_type_label})`} />
          <Item k="Seats" v={`${seatList(b)} (${b.seat_count})`} />
          <Item k="Fare per seat" v={taka(b.fare_per_seat)} />
          <Item k="Total fare" v={taka(b.total_fare)} strong />
          <Item k="Booked on" v={prettyDateTimeUtc(b.booked_at)} />
        </dl>
        <p className="border-t border-dashed border-slate-200 pt-3 text-[11px] leading-relaxed text-slate-400">
          Academic demonstration ticket. Operators, buses, fares and schedules are fictional sample data and this ticket is not valid for real travel.
        </p>
      </div>
    </article>
  )
}
const Item = ({ k, v, strong }) => (
  <div><dt className="label !mb-0">{k}</dt><dd className={strong ? 'text-base font-bold text-navy-900' : 'font-medium text-slate-800'}>{v}</dd></div>
)
