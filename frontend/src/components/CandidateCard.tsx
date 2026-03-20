import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useScoreCounter } from '../hooks/useScoreCounter'
import SkillBreakdown from './SkillBreakdown'
import BiasCheckBadge from './BiasCheckBadge'
import type { CandidateResult } from '../types'

interface Props { candidate: CandidateResult; rank: number }

function CandidateCard({ candidate: c, rank }: Props) {
  const [expanded, setExpanded] = useState(false)
  const [hoveredSkill, setHoveredSkill] = useState<string | null>(null)
  const score = useScoreCounter(c.final_score)
  const isTop = rank === 1
  const topSkills = [...c.skill_scores]
    .sort((a, b) => b.weighted_contribution - a.weighted_contribution)
    .slice(0, 5)

  const hasGaps = c.skill_scores.some(s => s.combined_confidence < 0.4)

  const skillColor = (conf: number) =>
    conf >= 0.7 ? 'var(--accent-teal)' : conf >= 0.4 ? 'var(--accent-amber)' : 'var(--accent-coral)'

  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: 'easeOut' }}
      style={{
        background: 'var(--bg-surface)',
        borderRadius: 14,
        border: `1px solid ${isTop ? 'rgba(0,229,204,0.3)' : 'var(--border)'}`,
        borderLeft: `3px solid ${isTop ? 'var(--accent-teal)' : expanded ? 'var(--accent-teal)' : 'transparent'}`,
        boxShadow: isTop ? 'var(--shadow-teal)' : 'none',
        padding: '24px 28px',
        cursor: 'pointer',
        transition: 'border-color 0.2s, box-shadow 0.2s',
      }}
      whileHover={{ borderColor: 'rgba(0,229,204,0.2)' } as any}
      onClick={() => setExpanded(e => !e)}
    >
      {/* Top row */}
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 20, marginBottom: 20 }}>
        {/* Rank */}
        <span className="font-mono" style={{
          fontSize: 32, fontWeight: 700, lineHeight: 1,
          color: isTop ? 'var(--accent-teal)' : 'var(--text-tertiary)',
          minWidth: 40,
        }}>
          {String(rank).padStart(2, '0')}
        </span>

        {/* Name + badges */}
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6, flexWrap: 'wrap' }}>
            <h3 className="font-syne" style={{ fontSize: 18, fontWeight: 600, margin: 0 }}>
              {c.name || `Candidate ${String(rank).padStart(2, '0')}`}
            </h3>
            {!c.github_provided && (
              <span className="font-mono" style={{
                padding: '2px 8px', borderRadius: 4, fontSize: 10,
                background: 'rgba(255,107,107,0.15)', color: 'var(--accent-coral)',
                border: '1px solid var(--accent-coral)', letterSpacing: '0.06em',
              }}>NO GITHUB</span>
            )}
            {c.data_gaps?.length > 0 && (
              <span className="font-mono" style={{
                padding: '2px 8px', borderRadius: 4, fontSize: 10,
                background: 'rgba(245,158,11,0.15)', color: 'var(--accent-amber)',
                border: '1px solid var(--accent-amber)',
              }}>DATA GAPS</span>
            )}
            <BiasCheckBadge candidateId={c.candidate_id} runId={c.run_id} />
          </div>

          {/* Score bars */}
          <div style={{ display: 'flex', gap: 20, marginBottom: 14 }}>
            {[
              { label: 'Resume', value: c.resume_subscore, color: 'var(--accent-amber)' },
              { label: 'GitHub', value: c.github_subscore, color: 'var(--accent-teal)', show: c.github_provided },
            ].filter(b => b.show !== false).map(bar => (
              <div key={bar.label} style={{ flex: 1 }}>
                <div className="font-mono" style={{ fontSize: 11, color: 'var(--text-tertiary)', marginBottom: 4 }}>{bar.label}</div>
                <div style={{ height: 6, background: 'var(--bg-elevated)', borderRadius: 3, overflow: 'hidden' }}>
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${bar.value * 100}%` }}
                    transition={{ duration: 0.8, delay: 0.3, ease: 'easeOut' }}
                    style={{ height: '100%', background: bar.color, borderRadius: 3 }}
                  />
                </div>
              </div>
            ))}
          </div>

          {/* Top skills */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {topSkills.map(s => (
              <span
                key={s.skill}
                className="font-mono"
                onMouseEnter={() => setHoveredSkill(s.skill)}
                onMouseLeave={() => setHoveredSkill(null)}
                style={{
                  padding: '3px 10px', borderRadius: 20, fontSize: 11,
                  border: `1px solid ${skillColor(s.combined_confidence)}`,
                  background: `${skillColor(s.combined_confidence)}18`,
                  color: skillColor(s.combined_confidence),
                  transition: 'box-shadow 0.2s',
                  boxShadow: hoveredSkill === s.skill
                    ? `0 0 12px ${skillColor(s.combined_confidence)}55`
                    : 'none',
                }}
              >
                {s.skill} · {(s.combined_confidence * 100).toFixed(0)}%
              </span>
            ))}
          </div>
        </div>

        {/* Score */}
        <div style={{ textAlign: 'right', minWidth: 80 }}>
          <motion.span
            className="font-mono"
            initial={{ textShadow: 'none' }}
            animate={{ textShadow: '0 0 20px rgba(245,158,11,0.3)' }}
            transition={{ duration: 0.6, delay: 0.2 }}
            style={{ fontSize: 44, fontWeight: 700, color: 'var(--accent-amber)', lineHeight: 1 }}
          >
            {score}
          </motion.span>
          <span className="font-mono" style={{ fontSize: 18, color: 'var(--accent-amber)', opacity: 0.7 }}>%</span>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 6, marginTop: 8 }}>
            <span style={{ fontSize: 13, color: 'var(--text-tertiary)' }}>{expanded ? '▲' : '▼'}</span>
            <span style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>breakdown</span>
          </div>
        </div>
      </div>

      {/* Expanded breakdown */}
      <AnimatePresence>
        {expanded && (
          <SkillBreakdown
            skillScores={c.skill_scores}
            githubProvided={c.github_provided}
            hasGaps={hasGaps}
            candidateId={c.candidate_id}
            runId={c.run_id}
          />
        )}
      </AnimatePresence>
    </motion.div>
  )
}

export default React.memo(CandidateCard)
