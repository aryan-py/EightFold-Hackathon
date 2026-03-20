import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { createRun } from '../lib/api'
import { useAppStore } from '../store/store'
import SkillGraphView from '../components/SkillGraphView'

const STEPS = [
  'Searching web for role skills...',
  'Building skill graph...',
  'Finalising weights...',
]

export default function HomePage() {
  const navigate = useNavigate()
  const setRun = useAppStore(s => s.setRun)
  const skillGraph = useAppStore(s => s.skillGraph)
  const [jd, setJd] = useState('')
  const [loading, setLoading] = useState(false)
  const [step, setStep] = useState(-1)
  const [error, setError] = useState('')
  const [runId, setRunId] = useState<string | null>(null)

  useEffect(() => { document.title = 'Talent Discovery — Eightfold AI' }, [])

  const handleSubmit = async () => {
    if (!jd.trim() || loading) return
    setLoading(true)
    setError('')
    setStep(0)

    try {
      const stepTimer = setInterval(() => {
        setStep(s => Math.min(s + 1, STEPS.length - 1))
      }, 4000)

      const result = await createRun(jd)
      clearInterval(stepTimer)
      setRun(result.run_id, result.skill_graph, result.job_title, result.role_type)
      setRunId(result.run_id)
      setLoading(false)
    } catch (e: any) {
      setError(e.message || 'Something went wrong. Check your API keys.')
      setLoading(false)
      setStep(-1)
    }
  }

  return (
    <div style={{
      display: 'flex',
      minHeight: '100vh',
      background: 'var(--bg-base)',
    }}>
      {/* Left panel */}
      <motion.div
        initial={{ opacity: 0, x: -30 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.6, ease: 'easeOut' }}
        style={{
          flex: '0 0 60%',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          padding: '80px 64px',
        }}
      >
        {/* Logo */}
        <div style={{ marginBottom: 48 }}>
          <span className="font-syne" style={{ fontSize: 13, letterSpacing: '0.3em', color: 'var(--accent-teal)', textTransform: 'uppercase' }}>
            Eightfold AI · Hackathon
          </span>
        </div>

        {/* Heading */}
        <h1 className="font-syne" style={{ fontSize: 48, fontWeight: 800, lineHeight: 1.1, marginBottom: 16 }}>
          Discover talent
          <br />
          <span style={{ color: 'var(--accent-teal)' }}>beyond the resume.</span>
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: 16, marginBottom: 48, lineHeight: 1.7, maxWidth: 480 }}>
          Paste a job description. AI agents build a skill graph, analyse resumes and GitHub profiles, and rank candidates with evidence — not guesswork.
        </p>

        {/* JD textarea */}
        <textarea
          value={jd}
          onChange={e => setJd(e.target.value)}
          disabled={loading}
          placeholder="Paste a job description or position title...&#10;&#10;e.g. Senior ML Engineer — Python, PyTorch, FastAPI required..."
          style={{
            width: '100%',
            minHeight: 180,
            background: 'var(--bg-surface)',
            border: `1px solid ${jd ? 'var(--accent-teal)' : 'var(--border)'}`,
            borderRadius: 12,
            color: 'var(--text-primary)',
            padding: '16px 20px',
            fontSize: 15,
            lineHeight: 1.6,
            resize: 'vertical',
            outline: 'none',
            transition: 'border-color 0.2s',
            fontFamily: 'system-ui',
          }}
        />

        {/* Error */}
        {error && (
          <p style={{ color: 'var(--accent-coral)', fontSize: 13, marginTop: 8 }}>{error}</p>
        )}

        {/* Submit / loading / continue */}
        <AnimatePresence mode="wait">
          {runId ? (
            <motion.button
              key="continue"
              initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
              onClick={() => navigate(`/run/${runId}/candidates`)}
              style={{
                marginTop: 20, width: '100%', padding: '16px 32px',
                background: 'var(--accent-teal)', color: '#0A0E1A',
                border: 'none', borderRadius: 10, fontSize: 16, fontWeight: 700,
                cursor: 'pointer', transition: 'all 0.2s',
              }}
              className="font-syne"
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              Add Candidates →
            </motion.button>
          ) : loading ? (
            <motion.div
              key="steps"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              style={{ marginTop: 20, padding: '20px 24px', background: 'var(--bg-surface)', borderRadius: 12, border: '1px solid var(--border)' }}
            >
              {STEPS.map((s, i) => (
                <div key={s} style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: i < STEPS.length - 1 ? 12 : 0 }}>
                  <div style={{
                    width: 8, height: 8, borderRadius: '50%',
                    background: i < step ? 'var(--accent-teal)' : i === step ? 'var(--accent-amber)' : 'var(--text-tertiary)',
                    transition: 'background 0.3s', flexShrink: 0,
                  }} />
                  <span className="font-mono" style={{ fontSize: 13, color: i <= step ? 'var(--text-primary)' : 'var(--text-tertiary)' }}>
                    {s}
                  </span>
                  {i === step && (
                    <motion.span
                      animate={{ opacity: [1, 0.3, 1] }}
                      transition={{ repeat: Infinity, duration: 1.2 }}
                      style={{ fontSize: 13, color: 'var(--accent-amber)' }}
                    >···</motion.span>
                  )}
                </div>
              ))}
            </motion.div>
          ) : (
            <motion.button
              key="btn"
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              onClick={handleSubmit}
              disabled={!jd.trim()}
              style={{
                marginTop: 20, width: '100%', padding: '16px 32px',
                background: jd.trim() ? 'var(--accent-teal)' : 'var(--bg-elevated)',
                color: jd.trim() ? '#0A0E1A' : 'var(--text-tertiary)',
                border: 'none', borderRadius: 10, fontSize: 16, fontWeight: 700,
                cursor: jd.trim() ? 'pointer' : 'not-allowed', transition: 'all 0.2s',
              }}
              className="font-syne"
              whileHover={jd.trim() ? { scale: 1.02 } : {}}
              whileTap={jd.trim() ? { scale: 0.98 } : {}}
            >
              Analyse Position →
            </motion.button>
          )}
        </AnimatePresence>

        <p style={{ marginTop: 16, fontSize: 12, color: 'var(--text-tertiary)', textAlign: 'center' }}>
          AI searches the web for role-specific skills + validates against your JD
        </p>
      </motion.div>

      {/* Right panel — skill graph */}
      <div style={{ flex: 1, position: 'relative', overflow: 'hidden', borderLeft: '1px solid var(--border)' }}>
        <AnimatedGraph />

        <AnimatePresence>
          {!skillGraph && (
            <motion.div
              key="bullets"
              initial={{ opacity: 1 }}
              exit={{ opacity: 0, y: -16 }}
              transition={{ duration: 0.5 }}
              style={{ position: 'absolute', bottom: 60, left: 40, right: 40 }}
            >
              {[
                ['Skill graph', 'Built from web search + JD analysis'],
                ['Parallel analysis', 'Resume and GitHub processed simultaneously'],
                ['Evidence-backed', 'Every score traced to specific data points'],
              ].map(([title, desc]) => (
                <div key={title} style={{ marginBottom: 24, display: 'flex', alignItems: 'flex-start', gap: 12 }}>
                  <div style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--accent-teal)', marginTop: 6, flexShrink: 0 }} />
                  <div>
                    <div className="font-syne" style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>{title}</div>
                    <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 2 }}>{desc}</div>
                  </div>
                </div>
              ))}
            </motion.div>
          )}

          {skillGraph && (
            <motion.div
              key="skillgraph"
              initial={{ opacity: 0, scale: 0.97 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.6, ease: 'easeOut' }}
              style={{ position: 'absolute', inset: 0, padding: 28, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}
            >
              <div className="font-mono" style={{ fontSize: 11, color: 'var(--accent-teal)', letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: 12 }}>
                Skill graph ready
              </div>
              <SkillGraphView skillGraph={skillGraph} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}

const SAMPLE_SKILLS = [
  { label: 'Python',       color: '#00E5CC' },
  { label: 'TypeScript',   color: '#F59E0B' },
  { label: 'React',        color: '#60A5FA' },
  { label: 'FastAPI',      color: '#00E5CC' },
  { label: 'PostgreSQL',   color: '#A78BFA' },
  { label: 'Docker',       color: '#60A5FA' },
  { label: 'Kubernetes',   color: '#60A5FA' },
  { label: 'PyTorch',      color: '#00E5CC' },
  { label: 'Git',          color: '#F59E0B' },
  { label: 'AWS',          color: '#F59E0B' },
  { label: 'GraphQL',      color: '#A78BFA' },
  { label: 'Node.js',      color: '#00E5CC' },
  { label: 'Redis',        color: '#FF6B6B' },
  { label: 'Rust',         color: '#FF6B6B' },
  { label: 'SQL',          color: '#A78BFA' },
  { label: 'Kafka',        color: '#F59E0B' },
  { label: 'scikit-learn', color: '#00E5CC' },
  { label: 'Linux',        color: '#60A5FA' },
  { label: 'CI/CD',        color: '#F59E0B' },
  { label: 'Figma',        color: '#FF6B6B' },
]

function AnimatedGraph() {
  const nodes = SAMPLE_SKILLS.map((s, i) => ({
    ...s,
    id: i,
    x: 8 + (i % 5) * 20 + Math.sin(i * 1.7) * 6,
    y: 10 + Math.floor(i / 5) * 22 + Math.cos(i * 1.3) * 5,
    delay: i * 0.2,
    duration: 3 + (i % 4),
    size: 3 + (i % 3),
  }))

  const edges = nodes.slice(0, 16).map((n, i) => ({ from: n, to: nodes[(i + 3) % nodes.length] }))

  return (
    <svg width="100%" height="100%" style={{ position: 'absolute', inset: 0, opacity: 0.25 }}>
      {edges.map((e, i) => (
        <line key={`l${i}`}
          x1={`${e.from.x}%`} y1={`${e.from.y}%`}
          x2={`${e.to.x}%`} y2={`${e.to.y}%`}
          stroke={e.from.color} strokeWidth="0.6" strokeOpacity="0.5"
        />
      ))}
      {nodes.map(n => (
        <g key={n.id}>
          <motion.circle
            cx={`${n.x}%`} cy={`${n.y}%`} r={n.size}
            fill={n.color}
            animate={{ opacity: [0.4, 0.9, 0.4], r: [n.size, n.size * 1.4, n.size] }}
            transition={{ repeat: Infinity, duration: n.duration, delay: n.delay, ease: 'easeInOut' }}
          />
          <motion.text
            x={`${n.x}%`} y={`${n.y + 3.5}%`}
            textAnchor="middle"
            fill={n.color}
            fontSize="9"
            fontFamily="DM Mono, monospace"
            animate={{ opacity: [0.3, 0.7, 0.3] }}
            transition={{ repeat: Infinity, duration: n.duration, delay: n.delay + 0.3, ease: 'easeInOut' }}
          >
            {n.label}
          </motion.text>
        </g>
      ))}
    </svg>
  )
}
