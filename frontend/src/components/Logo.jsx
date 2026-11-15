export default function Logo({ className = 'h-9 w-9' }) {
  return (
    <svg className={className} viewBox="0 0 64 64" aria-hidden="true">
      <rect width="64" height="64" rx="16" fill="#0f1b3d" />
      <rect x="13" y="17" width="38" height="26" rx="7" fill="#fff" />
      <rect x="18" y="22" width="12" height="9" rx="2" fill="#2f80ed" />
      <rect x="34" y="22" width="12" height="9" rx="2" fill="#2f80ed" />
      <circle cx="22" cy="46" r="4" fill="#4f9bff" /><circle cx="42" cy="46" r="4" fill="#4f9bff" />
      <path d="M20 37h24" stroke="#0f1b3d" strokeWidth="2.5" strokeLinecap="round" />
      <path d="M52 24c3 2.5 3 8.5 0 11M56 20c5.5 4.5 5.5 14.5 0 19" stroke="#4f9bff" strokeWidth="2.4" fill="none" strokeLinecap="round" />
    </svg>
  )
}
