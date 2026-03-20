import { create } from 'zustand'
import type { SkillGraph, CandidateResult } from '../types'

interface AppStore {
  currentRunId: string | null
  skillGraph: SkillGraph | null
  jobTitle: string
  roleType: string
  candidates: CandidateResult[]
  isStreaming: boolean
  setRun: (runId: string, skillGraph: SkillGraph, jobTitle: string, roleType: string) => void
  addCandidate: (candidate: CandidateResult) => void
  setCandidates: (candidates: CandidateResult[]) => void
  setStreaming: (v: boolean) => void
  reset: () => void
}

export const useAppStore = create<AppStore>((set) => ({
  currentRunId: null,
  skillGraph: null,
  jobTitle: '',
  roleType: 'mixed',
  candidates: [],
  isStreaming: false,

  setRun: (runId, skillGraph, jobTitle, roleType) =>
    set({ currentRunId: runId, skillGraph, jobTitle, roleType, candidates: [] }),

  addCandidate: (candidate) =>
    set(state => ({
      candidates: [...state.candidates, candidate]
        .sort((a, b) => b.final_score - a.final_score),
    })),

  setCandidates: (candidates) =>
    set({ candidates: [...candidates].sort((a, b) => b.final_score - a.final_score) }),

  setStreaming: (v) => set({ isStreaming: v }),
  reset: () => set({ currentRunId: null, skillGraph: null, jobTitle: '', candidates: [], isStreaming: false }),
}))
