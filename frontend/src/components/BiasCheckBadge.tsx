import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { runBiasCheck } from '../lib/api'
import type { BiasCheckResult } from '../types'

interface Props {
  candidateId: string
  runId: string
}

export default function BiasCheckBadge({ candidateId, runId }: Props) {
  const [result, setResult] = useState<BiasCheckResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [expanded, setExpanded] = useState(false)

  const handleCheck = async (e: React.MouseEvent) => {
    e.stopPropagation()
    if (loading || result) { setExpanded(v => !v); return }
    setLoading(true)
    try {
      const data = await runBiasCheck(runId, candidateId)
      setResult(data)
      setExpanded(true)
    } catch {
      // Silently fail — bias check is supplementary
    } finally {
      setLoading(false)
    }
  }

  const passed = result && !result.is_biased
  const badgeColor = result
    ? (passed ? 'var(--accent-teal)' : 'var(--accent-coral)')
    : 'var(--text-tertiary)'

  return (
    <div onClick={e => e.stopPropagation()}>
      <button
        onClick={handleCheck}
        style={{
          display: 'flex', alignItems: 'center', gap: 6,
          background: 'transparent', border: `1px solid ${badgeColor}`,
          borderRadius: 20, padding: '3px 10px', cursor: 'pointer',
          transition: 'all 0.2s',
        }}
      >
        {loading ? (
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 0.8, repeat: Infinity, ease: 'linear' }}
            style={{ width: 10, height: 10, border: `1.5px solid ${badgeColor}`, borderTopColor: 'transparent', borderRadius: '50%' }}
          />
        ) : (
          <span style={{ fontSize: 10, color: badgeColor }}>◈</span>
        )}
        <span className="font-mono" style={{ fontSize: 11, color: badgeColor }}>
          {result
            ? (passed ? `bias-resistant · Δ${result.delta_percent.toFixed(2)}%` : `bias-flag · Δ${result.delta_percent.toFixed(2)}%`)
            : 'run bias check'}
        </span>
      </button>

      <AnimatePresence>
        {expanded && result && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.25 }}
            style={{ overflow: 'hidden' }}
          >
            <div style={{
              marginTop: 10, padding: '14px 16px',
              background: passed ? 'rgba(0,229,204,0.06)' : 'rgba(255,107,107,0.06)',
              border: `1px solid ${passed ? 'var(--border-active)' : 'rgba(255,107,107,0.3)'}`,
              borderRadius: 8,
            }}>
              <div style={{ display: 'flex', gap: 12, marginBottom: 10 }}>
                {[
                  ['Original score', `${(result.score_original * 100).toFixed(1)}%`],
                  ['Masked score', `${(result.score_masked * 100).toFixed(1)}%`],
                  ['Δ delta', `${result.delta_percent.toFixed(3)}%`],
                ].map(([label, val]) => (
                  <div key={label}>
                    <div className="font-mono" style={{ fontSize: 10, color: 'var(--text-tertiary)', marginBottom: 2 }}>{label}</div>
                    <div className="font-mono" style={{ fontSize: 15, fontWeight: 700, color: badgeColor }}>{val}</div>
                  </div>
                ))}
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: 8 }}>
                {result.explanation}
              </div>
              {result.masked_fields.length > 0 && (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                  <span className="font-mono" style={{ fontSize: 10, color: 'var(--text-tertiary)' }}>Masked: </span>
                  {result.masked_fields.map(f => (
                    <span key={f} className="font-mono" style={{
                      fontSize: 10, padding: '1px 7px', borderRadius: 10,
                      background: 'var(--bg-elevated)', color: 'var(--text-secondary)',
                    }}>{f}</span>
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
