import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import NavBar from './components/NavBar'
import { ToastContainer } from './components/Toast'

const HomePage = lazy(() => import('./pages/HomePage'))
const CandidatesPage = lazy(() => import('./pages/CandidatesPage'))
const ResultsPage = lazy(() => import('./pages/ResultsPage'))

function Loading() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh' }}>
      <div style={{ width: 24, height: 24, border: '2px solid var(--accent-teal)', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <NavBar />
      <ToastContainer />
      <Suspense fallback={<Loading />}>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/run/:runId/candidates" element={<CandidatesPage />} />
          <Route path="/run/:runId/results" element={<ResultsPage />} />
          <Route path="*" element={
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100vh', gap: 16 }}>
              <span className="font-mono" style={{ fontSize: 64, color: 'var(--accent-coral)' }}>404</span>
              <span className="font-syne" style={{ fontSize: 20 }}>Page not found</span>
              <a href="/" style={{ color: 'var(--accent-teal)', fontSize: 14 }}>← Back home</a>
            </div>
          } />
        </Routes>
      </Suspense>
    </BrowserRouter>
  )
}
