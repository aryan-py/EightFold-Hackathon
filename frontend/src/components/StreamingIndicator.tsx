import { motion } from 'framer-motion'

interface Props { total: number; completed: number; isComplete: boolean }

export default function StreamingIndicator({ total, completed, isComplete }: Props) {
  if (isComplete) return null

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      style={{
        background: 'var(--bg-surface)', border: '1px solid var(--border-active)',
        borderRadius: 10, padding: '14px 20px', marginBottom: 20,
        display: 'flex', alignItems: 'center', gap: 16,
      }}
    >
      <motion.div
        animate={{ rotate: 360 }}
        transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
        style={{ width: 16, height: 16, border: '2px solid var(--accent-teal)', borderTopColor: 'transparent', borderRadius: '50%', flexShrink: 0 }}
      />
      <span style={{ fontSize: 14, color: 'var(--text-secondary)' }}>
        Analysing candidates...
      </span>
      <span className="font-mono" style={{ fontSize: 13, color: 'var(--accent-teal)', marginLeft: 'auto' }}>
        {completed} / {total} complete
      </span>
    </motion.div>
  )
}
