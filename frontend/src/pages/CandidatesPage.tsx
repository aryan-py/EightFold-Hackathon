import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { useAppStore } from '../store/store'
import { submitCandidates } from '../lib/api'
import SkillGraphView from '../components/SkillGraphView'
import CandidateRow from '../components/CandidateRow'
import type { CandidateFormData } from '../types'

const emptyCandidate = (): CandidateFormData => ({
  name: '', resumeText: '', resumeFile: null, githubUrl: '',
})

export default function CandidatesPage() {
  const { runId } = useParams<{ runId: string }>()
  const navigate = useNavigate()
  const { skillGraph, jobTitle, roleType } = useAppStore()
  const [candidates, setCandidates] = useState<CandidateFormData[]>([emptyCandidate()])
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const ROLE_COLORS: Record<string, string> = {
    coding: 'var(--accent-teal)',
    mixed: 'var(--accent-amber)',
    non_technical: 'var(--accent-coral)',
  }

  useEffect(() => { document.title = `Add Candidates — ${jobTitle}` }, [jobTitle])

  const isValid = candidates.every(c => c.resumeFile || c.resumeText.trim())

  const handleSubmit = async () => {
    if (!isValid || submitting || !runId) return
    setSubmitting(true)
    try {
      await submitCandidates(runId, candidates)
      navigate(`/run/${runId}/results`)
    } catch (e: any) {
      setError(e.message)
      setSubmitting(false)
    }
  }

  if (!skillGraph) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh' }}>
        <p style={{ color: 'var(--text-secondary)' }}>No active run — <a href="/" style={{ color: 'var(--accent-teal)' }}>start a new one</a></p>
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', minHeight: '100vh', paddingTop: 48 }}>
      {/* Left sticky rail */}
      <div style={{ width: 300, flexShrink: 0, position: 'sticky', top: 48, height: 'calc(100vh - 48px)', overflowY: 'auto', borderRight: '1px solid var(--border)', padding: 24 }}>
        <h2 className="font-syne" style={{ fontSize: 18, fontWeight: 700, marginBottom: 8 }}>{jobTitle}</h2>
        <span className="font-mono" style={{
          padding: '3px 10px', borderRadius: 20, fontSize: 11,
          background: ROLE_COLORS[roleType] + '22',
          color: ROLE_COLORS[roleType],
          border: `1px solid ${ROLE_COLORS[roleType]}`,
          display: 'inline-block', marginBottom: 20,
          textTransform: 'uppercase', letterSpacing: '0.08em',
        }}>
          {roleType.replace('_', ' ')}
        </span>
        <SkillGraphView skillGraph={skillGraph} mini />
      </div>

      {/* Right form area */}
      <div style={{ flex: 1, padding: '32px 48px', maxWidth: 740 }}>
        <button
          onClick={() => navigate('/')}
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
          ← back to job description
        </button>
        <h1 className="font-syne" style={{ fontSize: 28, fontWeight: 700, marginBottom: 8 }}>Add candidates</h1>
        <p style={{ color: 'var(--text-secondary)', marginBottom: 32, fontSize: 15 }}>
          Resume required. GitHub optional but improves scoring for technical roles.
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <AnimatePresence>
            {candidates.map((c, i) => (
              <CandidateRow
                key={i} index={i} data={c}
                onChange={d => setCandidates(prev => prev.map((x, j) => j === i ? d : x))}
                onRemove={() => setCandidates(prev => prev.filter((_, j) => j !== i))}
                canRemove={candidates.length > 1}
              />
            ))}
          </AnimatePresence>
        </div>

        {candidates.length < 20 && (
          <button
            onClick={() => setCandidates(p => [...p, emptyCandidate()])}
            style={{
              marginTop: 16, width: '100%', padding: '14px',
              background: 'transparent', border: '1px dashed var(--border)',
              borderRadius: 10, color: 'var(--accent-teal)', fontSize: 14,
              cursor: 'pointer', transition: 'all 0.2s',
            }}
            className="font-syne"
          >
            + Add candidate
          </button>
        )}

        {error && <p style={{ color: 'var(--accent-coral)', marginTop: 12, fontSize: 13 }}>{error}</p>}

        <button
          onClick={() => navigate(`/run/${runId}/results`)}
          style={{
            display: 'flex', alignItems: 'center', gap: 6,
            background: 'transparent', border: 'none',
            color: 'var(--text-tertiary)', fontSize: 13, cursor: 'pointer',
            padding: '12px 0 0', marginTop: 8,
            transition: 'color 0.2s',
          }}
          className="font-mono"
          onMouseEnter={e => (e.currentTarget.style.color = 'var(--accent-teal)')}
          onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-tertiary)')}
        >
          skip to results →
        </button>

        <motion.button
          onClick={handleSubmit}
          disabled={!isValid || submitting}
          whileHover={isValid ? { scale: 1.01 } : {}}
          whileTap={isValid ? { scale: 0.99 } : {}}
          style={{
            marginTop: 24, width: '100%', padding: '18px',
            background: isValid ? 'var(--accent-teal)' : 'var(--bg-elevated)',
            color: isValid ? '#0A0E1A' : 'var(--text-tertiary)',
            border: 'none', borderRadius: 10, fontSize: 16, fontWeight: 700,
            cursor: isValid ? 'pointer' : 'not-allowed', transition: 'all 0.2s',
          }}
          className="font-syne"
        >
          {submitting ? 'Submitting...' : `Analyse ${candidates.length} candidate${candidates.length > 1 ? 's' : ''} →`}
        </motion.button>
      </div>
    </div>
  )
}
