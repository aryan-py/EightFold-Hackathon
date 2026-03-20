import { useEffect, useRef, useState } from 'react'
import type { SkillGraph, SkillNode } from '../types'

const CATEGORY_COLORS: Record<string, string> = {
  'Languages':        '#00E5CC',
  'Frameworks':       '#F59E0B',
  'Tools':            '#60A5FA',
  'Domain Knowledge': '#A78BFA',
  'Soft Skills':      '#FF6B6B',
}

interface Props {
  skillGraph: SkillGraph
  mini?: boolean
  highlightSkill?: string | null
}

export default function SkillGraphView({ skillGraph, mini = false, highlightSkill }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [ForceGraph, setForceGraph] = useState<any>(null)
  const [hiddenCategories, setHiddenCategories] = useState<Set<string>>(new Set())
  const [showInferred, setShowInferred] = useState(true)
  const [weightThreshold, setWeightThreshold] = useState(0)

  useEffect(() => {
    import('react-force-graph-2d').then(m => setForceGraph(() => m.default))
  }, [])

  const allSkills = skillGraph.skill_graph.categories.flatMap(cat =>
    cat.skills.map(s => ({ ...s, category: cat.name }))
  )

  const filteredSkills = allSkills.filter(s =>
    !hiddenCategories.has(s.category) &&
    (showInferred || s.source === 'explicit') &&
    s.jd_weight >= weightThreshold
  )

  const nodes = filteredSkills.map(s => ({
    id: s.name,
    name: s.name,
    category: (s as any).category,
    source: s.source,
    jd_weight: s.jd_weight,
    required: s.required,
    color: CATEGORY_COLORS[(s as any).category] ?? '#8B9CB8',
    val: 1 + s.jd_weight * 4,
  }))

  const nodeIds = new Set(nodes.map(n => n.id))
  const explicitLinks = filteredSkills.flatMap(s =>
    s.relationships
      .filter(r => nodeIds.has(r.skill))
      .map(r => ({ source: s.name, target: r.skill, type: r.type }))
  )

  // Fallback: auto-generate links when agent returns no relationships
  const links = (() => {
    if (explicitLinks.length > 0) return explicitLinks

    const generated: { source: string; target: string; type: string }[] = []
    const byCategory: Record<string, typeof nodes> = {}
    nodes.forEach(n => {
      byCategory[n.category] = byCategory[n.category] ?? []
      byCategory[n.category].push(n)
    })

    // Connect skills within same category (chain)
    Object.values(byCategory).forEach(catNodes => {
      for (let i = 0; i < catNodes.length - 1; i++) {
        generated.push({ source: catNodes[i].id, target: catNodes[i + 1].id, type: 'related_to' })
      }
    })

    // Connect the highest-weight node in each category to the highest-weight node overall
    const anchor = [...nodes].sort((a, b) => b.jd_weight - a.jd_weight)[0]
    if (anchor) {
      Object.values(byCategory).forEach(catNodes => {
        const top = [...catNodes].sort((a, b) => b.jd_weight - a.jd_weight)[0]
        if (top && top.id !== anchor.id) {
          generated.push({ source: anchor.id, target: top.id, type: 'complements' })
        }
      })
    }

    return generated
  })()

  const categories = skillGraph.skill_graph.categories.map(c => c.name)

  if (mini) {
    return (
      <div style={{ padding: 16 }}>
        {categories.map(cat => {
          const catSkills = allSkills.filter(s => (s as any).category === cat)
          return (
            <div key={cat} style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.08em' }}>{cat}</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {catSkills.map(s => (
                  <SkillPill key={s.name} skill={s} highlighted={s.name === highlightSkill} />
                ))}
              </div>
            </div>
          )
        })}
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {/* Controls */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center', padding: '0 4px' }}>
        {categories.map(cat => (
          <button
            key={cat}
            onClick={() => setHiddenCategories(prev => {
              const next = new Set(prev)
              next.has(cat) ? next.delete(cat) : next.add(cat)
              return next
            })}
            style={{
              padding: '4px 10px',
              borderRadius: 20,
              border: `1px solid ${CATEGORY_COLORS[cat] ?? '#8B9CB8'}`,
              background: hiddenCategories.has(cat) ? 'transparent' : `${CATEGORY_COLORS[cat]}22`,
              color: hiddenCategories.has(cat) ? 'var(--text-tertiary)' : (CATEGORY_COLORS[cat] ?? '#8B9CB8'),
              fontSize: 12,
              cursor: 'pointer',
            }}
            className="font-mono"
          >
            {cat}
          </button>
        ))}
        <label style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}>
          <input type="checkbox" checked={showInferred} onChange={e => setShowInferred(e.target.checked)} />
          Show inferred
        </label>
        <label style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: 6 }}>
          Min weight
          <input
            type="range" min={0} max={0.8} step={0.1} value={weightThreshold}
            onChange={e => setWeightThreshold(Number(e.target.value))}
            style={{ width: 80 }}
          />
          <span className="font-mono">{weightThreshold.toFixed(1)}</span>
        </label>
      </div>

      {/* Graph */}
      <div ref={containerRef} style={{ background: 'var(--bg-surface)', borderRadius: 12, overflow: 'hidden', height: 340, border: '1px solid var(--border)' }}>
        {ForceGraph && (
          <ForceGraph
            graphData={{ nodes, links }}
            width={containerRef.current?.offsetWidth ?? 600}
            height={340}
            backgroundColor="transparent"
            nodeColor={(n: any) => n.color}
            nodeVal={(n: any) => n.val}
            nodeOpacity={(n: any) => n.source === 'inferred' ? 0.5 : 0.9}
            linkColor={(l: any) =>
              l.type === 'requires' ? '#00E5CC66' :
              l.type === 'complements' ? '#F59E0B66' : '#4A556888'
            }
            linkWidth={1}
            linkLineDash={(l: any) => l.type === 'complements' ? [3, 3] : l.type === 'related_to' ? [1, 4] : undefined}
            nodeLabel={(n: any) => `${n.name} (weight: ${n.jd_weight.toFixed(2)})`}
            nodeCanvasObjectMode={() => 'after'}
            nodeCanvasObject={(node: any, ctx: CanvasRenderingContext2D) => {
              const label = node.name
              ctx.font = '10px DM Mono, monospace'
              ctx.fillStyle = node.name === highlightSkill ? '#FFFFFF' : node.color
              ctx.textAlign = 'center'
              ctx.fillText(label, node.x, node.y + node.val * 2 + 10)
            }}
            cooldownTicks={80}
            d3AlphaDecay={0.03}
          />
        )}
      </div>

      {/* Legend */}
      <div style={{ display: 'flex', gap: 16, padding: '4px 8px', flexWrap: 'wrap' }}>
        {Object.entries(CATEGORY_COLORS).map(([cat, color]) => (
          <div key={cat} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
            <div style={{ width: 8, height: 8, borderRadius: '50%', background: color }} />
            <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{cat}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function SkillPill({ skill, highlighted }: { skill: SkillNode & { category?: string }, highlighted?: boolean }) {
  const conf = skill.jd_weight
  const color = conf >= 0.7 ? 'var(--accent-teal)' : conf >= 0.4 ? 'var(--accent-amber)' : 'var(--accent-coral)'
  return (
    <span className="font-mono" style={{
      padding: '2px 8px',
      borderRadius: 20,
      fontSize: 11,
      border: `1px solid ${color}`,
      background: highlighted ? color + '33' : 'transparent',
      color,
      transition: 'all 0.2s',
    }}>
      {skill.name}
    </span>
  )
}
