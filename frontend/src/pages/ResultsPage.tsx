import { useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { useSSE } from '../hooks/useSSE'
import { useAppStore } from '../store/store'
import { getResults } from '../lib/api'
import CandidateCard from '../components/CandidateCard'
import CandidateCardSkeleton from '../components/CandidateCardSkeleton'
import StreamingIndicator from '../components/StreamingIndicator'
import SkillGraphView from '../components/SkillGraphView'
import { showToast } from '../components/Toast'

export default function ResultsPage() {
  const { runId } = useParams<{ runId: string }>()
  const navigate = useNavigate()
  const { skillGraph, jobTitle, roleType, setCandidates } = useAppStore()
  const { candidates, isComplete, error } = useSSE(runId ?? null)

  useEffect(() => { document.title = `Results — ${jobTitle}` }, [jobTitle])

  // On page refresh — fetch from DB instead of re-streaming
  useEffect(() => {
    if (!runId || candidates.length > 0) return
    getResults(runId).then(setCandidates).catch(() => {})
  }, [runId])

  useEffect(() => {
    if (error) showToast(error, 'error')
  }, [error])

  useEffect(() => {
    if (isComplete && candidates.length > 0) showToast('All candidates scored', 'success')
  }, [isComplete])

  const ROLE_COLORS: Record<string, string> = {
    coding: 'var(--accent-teal)',
    mixed: 'var(--accent-amber)',
    non_technical: 'var(--accent-coral)',
  }

  return (
    <div style={{ display: 'flex', minHeight: '100vh', paddingTop: 48 }}>
      {/* Sticky left rail */}
      {skillGraph && (
        <div style={{ width: 280, flexShrink: 0, position: 'sticky', top: 48, height: 'calc(100vh - 48px)', overflowY: 'auto', borderRight: '1px solid var(--border)', padding: 20 }}>
          <div className="font-syne" style={{ fontSize: 15, fontWeight: 600, marginBottom: 4 }}>{jobTitle}</div>
          <div className="font-mono" style={{ fontSize: 11, color: ROLE_COLORS[roleType] ?? 'var(--accent-teal)', marginBottom: 16, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
            {roleType?.replace('_', ' ')}
          </div>
          <SkillGraphView skillGraph={skillGraph} mini />
        </div>
      )}

      {/* Main content */}
      <div style={{ flex: 1, padding: '32px 48px', maxWidth: 800 }}>
        {/* Header */}
        <button
          onClick={() => navigate(`/run/${runId}/candidates`)}
          style={{
            display: 'flex', alignItems: 'center', gap: 6,
            background: 'transparent', border: 'none',
            color: 'var(--text-tertiary)', fontSize: 13, cursor: 'pointer',
            padding: 0, marginBottom: 20,
            transition: 'color 0.2s',
          }}
          className="font-mono"
          onMouseEnter={e => (e.currentTarget.style.color = 'var(--accent-teal)')}
          onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-tertiary)')}
        >
          ← back to candidates
        </button>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 28 }}>
          <div>
            <h1 className="font-syne" style={{ fontSize: 28, fontWeight: 700, marginBottom: 4 }}>Candidate rankings</h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: 14 }}>
              {candidates.length > 0 ? `${candidates.length} candidate${candidates.length > 1 ? 's' : ''} analysed` : 'Waiting for results...'}
            </p>
          </div>
          {isComplete && (
            <motion.div initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <div style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--accent-teal)' }} />
              <span className="font-mono" style={{ fontSize: 13, color: 'var(--accent-teal)' }}>Complete</span>
            </motion.div>
          )}
        </div>

        <StreamingIndicator total={candidates.length || 1} completed={candidates.length} isComplete={isComplete} />

        {error && (
          <div style={{ padding: '12px 16px', background: 'rgba(255,107,107,0.1)', border: '1px solid var(--accent-coral)', borderRadius: 8, color: 'var(--accent-coral)', fontSize: 14, marginBottom: 20 }}>
            {error}
          </div>
        )}

        {/* Empty state */}
        {candidates.length === 0 && !isComplete && (
          <div style={{ textAlign: 'center', padding: '80px 0' }}>
            <motion.div animate={{ opacity: [0.3, 1, 0.3] }} transition={{ repeat: Infinity, duration: 2 }}>
              <svg width="64" height="64" viewBox="0 0 64 64" fill="none" style={{ margin: '0 auto 24px', display: 'block' }}>
                <circle cx="32" cy="32" r="28" stroke="var(--accent-teal)" strokeWidth="1" opacity="0.4" />
                <circle cx="32" cy="20" r="4" fill="var(--accent-teal)" opacity="0.6" />
                <circle cx="20" cy="40" r="4" fill="var(--accent-teal)" opacity="0.6" />
                <circle cx="44" cy="40" r="4" fill="var(--accent-teal)" opacity="0.6" />
                <line x1="32" y1="24" x2="20" y2="36" stroke="var(--accent-teal)" strokeWidth="1" opacity="0.3" />
                <line x1="32" y1="24" x2="44" y2="36" stroke="var(--accent-teal)" strokeWidth="1" opacity="0.3" />
              </svg>
            </motion.div>
            <h3 className="font-syne" style={{ fontSize: 20, fontWeight: 600, marginBottom: 8 }}>Agents are working...</h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: 14 }}>Results will appear here as each candidate is scored</p>
          </div>
        )}

        {/* Skeleton loading */}
        {!isComplete && candidates.length === 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <CandidateCardSkeleton />
            <CandidateCardSkeleton />
          </div>
        )}

        {/* Candidate cards */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <AnimatePresence>
            {candidates.map((c, i) => (
              <CandidateCard key={c.candidate_id} candidate={c} rank={i + 1} />
            ))}
          </AnimatePresence>
        </div>
      </div>
    </div>
  )
}
