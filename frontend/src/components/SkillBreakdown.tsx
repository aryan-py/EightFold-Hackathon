import { motion } from 'framer-motion'
import type { SkillScore } from '../types'
import AdjacencyPanel from './AdjacencyPanel'

interface Props {
  skillScores: SkillScore[]
  githubProvided: boolean
  hasGaps: boolean
  candidateId: string
  runId: string
}

export default function SkillBreakdown({ skillScores, githubProvided, hasGaps, candidateId, runId }: Props) {
  const sorted = [...skillScores].sort((a, b) => b.weighted_contribution - a.weighted_contribution)
  const top3 = sorted.slice(0, 3)

  const confidenceColor = (v: number) =>
    v >= 0.7 ? 'var(--accent-teal)' : v >= 0.4 ? 'var(--accent-amber)' : v > 0 ? 'var(--accent-coral)' : 'var(--text-tertiary)'

  return (
    <motion.div
      initial={{ height: 0, opacity: 0 }}
      animate={{ height: 'auto', opacity: 1 }}
      exit={{ height: 0, opacity: 0 }}
      transition={{ duration: 0.35, ease: 'easeInOut' }}
      style={{ overflow: 'hidden' }}
    >
      <div style={{ padding: '24px 0 8px' }}>
        {/* Skill table */}
        <div style={{ overflowX: 'auto', marginBottom: 28 }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                {['Skill', 'JD weight', 'Resume', 'GitHub', 'Combined', 'Contribution'].map(h => (
                  <th key={h} className="font-mono" style={{
                    padding: '6px 10px', textAlign: 'left', fontSize: 11,
                    color: 'var(--text-tertiary)', fontWeight: 400,
                    textTransform: 'uppercase', letterSpacing: '0.06em',
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sorted.map((s, i) => (
                <tr key={s.skill} style={{ borderBottom: '1px solid var(--border)', background: i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.01)' }}>
                  <td style={{ padding: '10px 10px', color: 'var(--text-primary)', fontWeight: 500 }} className="font-syne">{s.skill}</td>
                  <td style={{ padding: '10px 10px' }}>
                    <BarCell value={s.jd_weight} color="var(--text-secondary)" />
                  </td>
                  <td style={{ padding: '10px 10px' }}>
                    {s.resume_confidence > 0
                      ? <BarCell value={s.resume_confidence} color="var(--accent-amber)" />
                      : <span style={{ color: 'var(--text-tertiary)', fontSize: 12 }}>—</span>}
                  </td>
                  <td style={{ padding: '10px 10px' }}>
                    {!githubProvided
                      ? <span style={{ color: 'var(--text-tertiary)', fontSize: 12 }}>n/a</span>
                      : s.github_confidence > 0
                        ? <BarCell value={s.github_confidence} color="var(--accent-teal)" />
                        : <span style={{ color: 'var(--text-tertiary)', fontSize: 12 }}>—</span>}
                  </td>
                  <td style={{ padding: '10px 10px' }}>
                    <span className="font-mono" style={{ color: confidenceColor(s.combined_confidence), fontWeight: 700 }}>
                      {(s.combined_confidence * 100).toFixed(0)}%
                    </span>
                  </td>
                  <td style={{ padding: '10px 10px' }}>
                    <span className="font-mono" style={{ color: 'var(--text-secondary)', fontSize: 12 }}>
                      {s.weighted_contribution.toFixed(3)}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Evidence paragraphs for top 3 */}
        <div style={{ marginBottom: 8 }}>
          <h4 className="font-syne" style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 16, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
            Top skill evidence
          </h4>
          {top3.map(s => (
            <div key={s.skill} style={{ marginBottom: 20 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                <span className="font-syne" style={{ fontWeight: 600, fontSize: 15 }}>{s.skill}</span>
                <span className="font-mono" style={{ fontSize: 12, color: confidenceColor(s.combined_confidence) }}>
                  {(s.combined_confidence * 100).toFixed(0)}%
                </span>
              </div>
              <EvidenceParagraph text={s.evidence_paragraph} />
            </div>
          ))}
        </div>

        <AdjacencyPanel candidateId={candidateId} runId={runId} hasGaps={hasGaps} />
      </div>
    </motion.div>
  )
}

function BarCell({ value, color }: { value: number; color: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <div style={{ width: 60, height: 4, background: 'var(--bg-elevated)', borderRadius: 2, overflow: 'hidden' }}>
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${value * 100}%` }}
          transition={{ duration: 0.6, ease: 'easeOut' }}
          style={{ height: '100%', background: color, borderRadius: 2 }}
        />
      </div>
      <span className="font-mono" style={{ fontSize: 11, color }}>{(value * 100).toFixed(0)}</span>
    </div>
  )
}

function EvidenceParagraph({ text }: { text: string }) {
  if (!text) return null
  const parts = text.split(/(Resume:|GitHub:)/)
  return (
    <div style={{ fontSize: 14, lineHeight: 1.7, color: 'var(--text-secondary)' }}>
      {parts.map((p, i) => {
        if (p === 'Resume:') return (
          <span key={i} className="font-mono" style={{ fontSize: 11, color: 'var(--accent-amber)', display: 'block', marginTop: 8, marginBottom: 2 }}>RESUME</span>
        )
        if (p === 'GitHub:') return (
          <span key={i} className="font-mono" style={{ fontSize: 11, color: 'var(--accent-teal)', display: 'block', marginTop: 8, marginBottom: 2 }}>GITHUB</span>
        )
        return <span key={i}>{p}</span>
      })}
    </div>
  )
}
