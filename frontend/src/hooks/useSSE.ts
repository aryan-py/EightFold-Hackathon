import { useEffect, useRef, useState, useCallback } from 'react'
import type { CandidateResult } from '../types'

interface SSEState {
  candidates: CandidateResult[]
  isComplete: boolean
  error: string | null
  processingCount: number
}

export function useSSE(runId: string | null): SSEState {
  const [state, setState] = useState<SSEState>({
    candidates: [],
    isComplete: false,
    error: null,
    processingCount: 0,
  })
  const esRef = useRef<EventSource | null>(null)
  const retryRef = useRef(0)

  const connect = useCallback(() => {
    if (!runId) return
    const baseURL = import.meta.env.PROD ? '' : 'http://localhost:8000'
    const es = new EventSource(`${baseURL}/api/run/${runId}/stream`)
    esRef.current = es

    es.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data)
        if (parsed.type === 'ping') return

        if (parsed.type === 'candidate_result') {
          const candidate = parsed.data as CandidateResult
          setState(prev => {
            const updated = [...prev.candidates, candidate]
              .sort((a, b) => b.final_score - a.final_score)
            return { ...prev, candidates: updated, processingCount: prev.processingCount + 1 }
          })
        }

        if (parsed.type === 'run_complete') {
          setState(prev => ({ ...prev, isComplete: true }))
          es.close()
        }
      } catch {
        // Ignore parse errors — malformed events shouldn't crash the app
      }
    }

    es.onerror = () => {
      es.close()
      if (retryRef.current < 1) {
        retryRef.current += 1
        setTimeout(connect, 2000)
      } else {
        setState(prev => ({ ...prev, error: 'Connection lost. Refresh to retry.', isComplete: true }))
      }
    }
  }, [runId])

  useEffect(() => {
    connect()
    return () => { esRef.current?.close() }
  }, [connect])

  return state
}
