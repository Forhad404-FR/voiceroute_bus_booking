import { Compass } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Empty } from '../components/ui'

export default function NotFound() {
  return <div className="px-4 py-20"><Empty icon={Compass} title="Page not found" action={<Link to="/" className="btn-primary">Back to home</Link>}>The page you are looking for does not exist.</Empty></div>
}
