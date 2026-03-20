export default function CandidateCardSkeleton() {
  return (
    <div style={{
      background: 'var(--bg-surface)',
      borderRadius: 14,
      border: '1px solid var(--border)',
      borderLeft: '3px solid transparent',
      padding: '24px 28px',
    }}>
      {/* Top row */}
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 20, marginBottom: 20 }}>
        {/* Rank placeholder */}
        <div className="shimmer" style={{ width: 40, height: 36, borderRadius: 4 }} />

        {/* Name + bars */}
        <div style={{ flex: 1 }}>
          <div className="shimmer" style={{ width: '40%', height: 22, borderRadius: 4, marginBottom: 16 }} />
          <div style={{ display: 'flex', gap: 20, marginBottom: 14 }}>
            <div style={{ flex: 1 }}>
              <div className="shimmer" style={{ width: 50, height: 11, borderRadius: 3, marginBottom: 4 }} />
              <div className="shimmer" style={{ height: 6, borderRadius: 3 }} />
            </div>
            <div style={{ flex: 1 }}>
              <div className="shimmer" style={{ width: 50, height: 11, borderRadius: 3, marginBottom: 4 }} />
              <div className="shimmer" style={{ height: 6, borderRadius: 3 }} />
            </div>
          </div>
          {/* Skill pills */}
          <div style={{ display: 'flex', gap: 6 }}>
            {[80, 70, 90, 65, 75].map((w, i) => (
              <div key={i} className="shimmer" style={{ width: w, height: 24, borderRadius: 20 }} />
            ))}
          </div>
        </div>

        {/* Score placeholder */}
        <div style={{ textAlign: 'right', minWidth: 80 }}>
          <div className="shimmer" style={{ width: 70, height: 48, borderRadius: 4, marginLeft: 'auto' }} />
        </div>
      </div>
    </div>
  )
}
