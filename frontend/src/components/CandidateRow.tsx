import { useState, useRef } from 'react'
import { motion } from 'framer-motion'
import type { CandidateFormData } from '../types'

interface Props {
  index: number
  data: CandidateFormData
  onChange: (data: CandidateFormData) => void
  onRemove: () => void
  canRemove: boolean
}

export default function CandidateRow({ index, data, onChange, onRemove, canRemove }: Props) {
  const [tab, setTab] = useState<'pdf' | 'text'>('pdf')
  const fileRef = useRef<HTMLInputElement>(null)

  const num = String(index + 1).padStart(2, '0')

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.3 }}
      style={{
        background: 'var(--bg-surface)',
        borderRadius: 12,
        border: '1px solid var(--border)',
        padding: 24,
        transition: 'border-color 0.2s',
      }}
      whileHover={{ borderColor: 'var(--border-active)' } as any}
    >
      {/* Header row */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
        <span className="font-mono" style={{ fontSize: 24, fontWeight: 700, color: 'var(--accent-teal)' }}>{num}</span>
        <input
          value={data.name}
          onChange={e => onChange({ ...data, name: e.target.value })}
          placeholder="Candidate name (optional)"
          style={{ flex: 1, margin: '0 16px', background: 'transparent', border: 'none', borderBottom: '1px solid var(--border)', color: 'var(--text-primary)', padding: '4px 0', fontSize: 15, outline: 'none' }}
        />
        {canRemove && (
          <button onClick={onRemove} style={{ background: 'transparent', border: 'none', color: 'var(--text-tertiary)', cursor: 'pointer', fontSize: 18, padding: 4 }}>×</button>
        )}
      </div>

      {/* Resume tabs */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', gap: 0, marginBottom: 12, border: '1px solid var(--border)', borderRadius: 8, overflow: 'hidden', width: 'fit-content' }}>
          {(['pdf', 'text'] as const).map(t => (
            <button key={t} onClick={() => setTab(t)} style={{
              padding: '8px 20px', background: tab === t ? 'var(--accent-teal)' : 'transparent',
              color: tab === t ? '#0A0E1A' : 'var(--text-secondary)',
              border: 'none', cursor: 'pointer', fontSize: 13, fontWeight: tab === t ? 700 : 400,
              transition: 'all 0.2s',
            }} className="font-syne">
              {t === 'pdf' ? 'Upload PDF' : 'Paste Text'}
            </button>
          ))}
        </div>

        {tab === 'pdf' ? (
          <div
            onClick={() => fileRef.current?.click()}
            onDrop={e => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f) onChange({ ...data, resumeFile: f, resumeText: '' }) }}
            onDragOver={e => e.preventDefault()}
            style={{
              border: `2px dashed ${data.resumeFile ? 'var(--accent-teal)' : 'var(--border)'}`,
              borderRadius: 8, padding: 28, textAlign: 'center', cursor: 'pointer',
              transition: 'border-color 0.2s', background: data.resumeFile ? 'rgba(0,229,204,0.05)' : 'transparent',
            }}
          >
            <input ref={fileRef} type="file" accept=".pdf" style={{ display: 'none' }}
              onChange={e => { const f = e.target.files?.[0]; if (f) onChange({ ...data, resumeFile: f, resumeText: '' }) }} />
            {data.resumeFile ? (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10 }}>
                <span style={{ color: 'var(--accent-teal)', fontSize: 18 }}>✓</span>
                <span className="font-mono" style={{ fontSize: 13, color: 'var(--text-primary)' }}>{data.resumeFile.name}</span>
                <button onClick={e => { e.stopPropagation(); onChange({ ...data, resumeFile: null }) }}
                  style={{ background: 'transparent', border: 'none', color: 'var(--text-tertiary)', cursor: 'pointer' }}>×</button>
              </div>
            ) : (
              <div>
                <div style={{ fontSize: 28, marginBottom: 8, color: 'var(--text-tertiary)' }}>⬆</div>
                <div style={{ color: 'var(--text-secondary)', fontSize: 14 }}>Drop PDF here or click to browse</div>
              </div>
            )}
          </div>
        ) : (
          <textarea
            value={data.resumeText}
            onChange={e => onChange({ ...data, resumeText: e.target.value, resumeFile: null })}
            placeholder="Paste resume text here..."
            style={{
              width: '100%', minHeight: 120, background: 'var(--bg-elevated)',
              border: '1px solid var(--border)', borderRadius: 8, color: 'var(--text-primary)',
              padding: '12px 14px', fontSize: 14, resize: 'vertical', outline: 'none',
            }}
          />
        )}
      </div>

      {/* GitHub URL */}
      <div>
        <input
          value={data.githubUrl}
          onChange={e => onChange({ ...data, githubUrl: e.target.value })}
          placeholder="https://github.com/username  (optional)"
          style={{
            width: '100%', background: 'var(--bg-elevated)',
            border: `1px solid ${data.githubUrl ? 'var(--border-active)' : 'var(--border)'}`,
            borderRadius: 8, color: 'var(--text-primary)', padding: '10px 14px',
            fontSize: 14, outline: 'none', transition: 'border-color 0.2s',
          }}
        />
        {!data.githubUrl && (
          <p style={{ fontSize: 12, color: 'var(--text-tertiary)', marginTop: 6 }}>
            GitHub optional — score will use resume only if not provided
          </p>
        )}
      </div>
    </motion.div>
  )
}
