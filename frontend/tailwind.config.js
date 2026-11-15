/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        navy: { 50: '#f1f4f9', 100: '#dde4f0', 200: '#b9c6df', 300: '#8fa3c8', 400: '#5f7bab', 500: '#3d5a8f', 600: '#2b4472', 700: '#1f3359', 800: '#16264a', 900: '#0f1b3d', 950: '#0a1230' },
        accent: { 50: '#eff6ff', 100: '#dbeafe', 400: '#4f9bff', 500: '#2f80ed', 600: '#1f6bd6', 700: '#1a56ad' },
      },
      fontFamily: { sans: ['Inter', 'ui-sans-serif', 'system-ui', 'Segoe UI', 'Roboto', 'sans-serif'] },
      boxShadow: { card: '0 1px 2px rgba(15,27,61,.05), 0 8px 24px rgba(15,27,61,.08)', pop: '0 12px 40px rgba(15,27,61,.18)' },
      keyframes: {
        rise: { '0%': { opacity: 0, transform: 'translateY(8px)' }, '100%': { opacity: 1, transform: 'translateY(0)' } },
        pulseRing: { '0%': { boxShadow: '0 0 0 0 rgba(239,68,68,.5)' }, '100%': { boxShadow: '0 0 0 16px rgba(239,68,68,0)' } },
      },
      animation: { rise: 'rise .35s ease-out both', pulseRing: 'pulseRing 1.3s ease-out infinite' },
    },
  },
  plugins: [],
}
