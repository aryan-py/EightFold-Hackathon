import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { getAdjacency } from '../lib/api'
import GapCard from './GapCard'
import type { AdjacencyResult } from '../types'

interface Props {
  candidateId: string
  runId: string
  hasGaps: boolean
}

export default function AdjacencyPanel({ candidateId, runId, hasGaps }: Props) {
  const [data, setData] = useState<AdjacencyResult | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!hasGaps) return
    setLoading(true)
    getAdjacency(runId, candidateId)
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [candidateId, runId, hasGaps])

  if (!hasGaps) return null

  return (
    <div style={{ marginTop: 28, paddingTop: 20, borderTop: '1px solid var(--border)' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <h4 className="font-syne" style={{
          fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)',
          textTransform: 'uppercase', letterSpacing: '0.08em', margin: 0,
        }}>
          Skill gaps + learning velocity
        </h4>
        {data && (
          <div style={{ display: 'flex', gap: 16 }}>
            <span className="font-mono" style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>
              {data.gap_count} gap{data.gap_count !== 1 ? 's' : ''}
            </span>
            {data.overall_ttp_weeks_low != null && (
              <span className="font-mono" style={{ fontSize: 12, color: 'var(--accent-amber)' }}>
                ~{data.overall_ttp_weeks_low}–{data.overall_ttp_weeks_high} wks total
              </span>
            )}
          </div>
        )}
      </div>

      {loading && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '12px 0' }}>
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 0.8, repeat: Infinity, ease: 'linear' }}
            style={{ width: 14, height: 14, border: '2px solid var(--accent-teal)', borderTopColor: 'transparent', borderRadius: '50%' }}
          />
          <span style={{ fontSize: 13, color: 'var(--text-tertiary)' }}>Analysing skill adjacency...</span>
        </div>
      )}

      {data && data.adjacencies.length === 0 && (
        <p style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
          No significant skill gaps found against the job description.
        </p>
      )}

      {data && data.adjacencies.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {data.adjacencies.map((gap, i) => (
            <GapCard key={gap.missing_skill} gap={gap} index={i} />
          ))}
        </div>
      )}
    </div>
  )
}
