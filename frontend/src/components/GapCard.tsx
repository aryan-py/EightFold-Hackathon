import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import type { AdjacencyItem } from '../types'

interface Props { gap: AdjacencyItem; index: number }

const REL_LABELS: Record<string, string> = {
  extension:      'direct extension',
  sibling:        'same domain',
  advanced:       'natural progression',
  specialisation: 'specialisation',
  requires:       'prerequisite',
  complements:    'complements',
  related_to:     'related',
}

export default function GapCard({ gap, index }: Props) {
  const [showPath, setShowPath] = useState(false)
  const hasBridge = !!gap.bridge_skill

  const ttpLabel = gap.ttp_weeks_low
    ? `${gap.ttp_weeks_low}–${gap.ttp_weeks_high} weeks`
    : '12+ weeks'

  const urgencyColor = !gap.ttp_weeks_low
    ? 'var(--accent-coral)'
    : gap.ttp_weeks_low <= 3
      ? 'var(--accent-teal)'
      : gap.ttp_weeks_low <= 8
        ? 'var(--accent-amber)'
        : 'var(--accent-coral)'

  return (
    <motion.div
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.3, delay: index * 0.06 }}
      style={{
        padding: '14px 16px',
        background: 'var(--bg-elevated)',
        borderRadius: 10,
        border: '1px solid var(--border)',
        borderLeft: `3px solid ${urgencyColor}`,
      }}
    >
      {/* Header row */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12, marginBottom: 8 }}>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 6 }}>
            <span className="font-syne" style={{ fontSize: 14, fontWeight: 600 }}>
              {gap.missing_skill}
            </span>
            <span style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>not demonstrated</span>

            {hasBridge && (
              <>
                <span style={{ color: 'var(--text-tertiary)', fontSize: 12 }}>←</span>
                <span className="font-mono" style={{
                  fontSize: 11, padding: '2px 8px', borderRadius: 10,
                  background: 'rgba(0,229,204,0.12)', color: 'var(--accent-teal)',
                  border: '1px solid rgba(0,229,204,0.3)',
                }}>
                  {gap.bridge_skill}
                </span>
                {gap.relationship_type && (
                  <span style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>
                    ({REL_LABELS[gap.relationship_type] ?? gap.relationship_type})
                  </span>
                )}
              </>
            )}
          </div>

          <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6, margin: 0 }}>
            {gap.rationale}
          </p>
        </div>

        {/* TTP badge */}
        <div style={{ textAlign: 'right', flexShrink: 0 }}>
          <div className="font-mono" style={{ fontSize: 18, fontWeight: 700, color: urgencyColor, lineHeight: 1 }}>
            {ttpLabel}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 3 }}>
            to proficiency
          </div>
        </div>
      </div>

      {/* Learning path toggle */}
      {gap.learning_path.length > 0 && (
        <>
          <button
            onClick={() => setShowPath(v => !v)}
            style={{
              background: 'transparent', border: 'none',
              color: 'var(--accent-teal)', fontSize: 12,
              cursor: 'pointer', padding: 0, marginTop: 4,
              display: 'flex', alignItems: 'center', gap: 4,
            }}
            className="font-mono"
          >
            {showPath ? '▲' : '▼'} learning path
          </button>

          <AnimatePresence>
            {showPath && (
              <motion.ol
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.25 }}
                style={{ margin: '10px 0 0', paddingLeft: 20, overflow: 'hidden' }}
              >
                {gap.learning_path.map((step, i) => (
                  <li key={i} style={{
                    fontSize: 13, color: 'var(--text-secondary)',
                    lineHeight: 1.7, marginBottom: 4,
                  }}>
                    {step}
                  </li>
                ))}
              </motion.ol>
            )}
          </AnimatePresence>
        </>
      )}
    </motion.div>
  )
}
