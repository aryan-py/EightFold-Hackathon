import { useLocation, Link } from 'react-router-dom'
import { useAppStore } from '../store/store'

export default function NavBar() {
  const location = useLocation()
  const { jobTitle } = useAppStore()
  if (location.pathname === '/') return null

  return (
    <nav style={{
      position: 'fixed', top: 0, left: 0, right: 0, zIndex: 100,
      height: 48, background: 'var(--bg-base)',
      borderBottom: '1px solid var(--border)',
      display: 'flex', alignItems: 'center',
      padding: '0 32px', justifyContent: 'space-between',
    }}>
      <Link to="/" style={{ textDecoration: 'none' }}>
        <span className="font-syne" style={{ fontSize: 16, fontWeight: 800, letterSpacing: '0.05em', color: 'var(--text-primary)' }}>
          TALENT<span style={{ color: 'var(--accent-teal)' }}>.</span>AI
        </span>
      </Link>
      {jobTitle && (
        <span className="font-mono" style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
          {jobTitle}
        </span>
      )}
    </nav>
  )
}
