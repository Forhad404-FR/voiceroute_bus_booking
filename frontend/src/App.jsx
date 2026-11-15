import { Route, Routes } from 'react-router-dom'
import MainLayout from './layouts/MainLayout'
import ProtectedRoute from './layouts/ProtectedRoute'
import Home from './pages/Home'
import Results from './pages/Results'
import Booking from './pages/Booking'
import MyTickets from './pages/MyTickets'
import TicketPage from './pages/TicketPage'
import AuthPage from './pages/AuthPage'
import Admin from './pages/Admin'
import NotFound from './pages/NotFound'

export default function App() {
  return (
    <Routes>
      <Route element={<MainLayout />}>
        <Route index element={<Home />} />
        <Route path="search" element={<Results />} />
        <Route path="login" element={<AuthPage mode="login" />} />
        <Route path="register" element={<AuthPage mode="register" />} />
        <Route element={<ProtectedRoute />}>
          <Route path="book/:scheduleId" element={<Booking />} />
          <Route path="my-tickets" element={<MyTickets />} />
          <Route path="tickets/:bookingId" element={<TicketPage />} />
        </Route>
        <Route element={<ProtectedRoute admin />}>
          <Route path="admin" element={<Admin />} />
        </Route>
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}
