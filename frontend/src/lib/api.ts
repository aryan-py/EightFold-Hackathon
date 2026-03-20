import axios from 'axios'
import type { RunResponse, CandidateResult, BiasCheckResult, AdjacencyResult } from '../types'

const baseURL = import.meta.env.PROD ? '' : 'http://localhost:8000'

export const api = axios.create({ baseURL })

export async function createRun(jdText: string): Promise<RunResponse> {
  const { data } = await api.post<RunResponse>('/api/run', { jd_text: jdText })
  return data
}

export async function submitCandidates(
  runId: string,
  candidates: Array<{
    name: string
    resumeText: string
    resumeFile: File | null
    githubUrl: string
  }>
): Promise<{ candidate_ids: string[]; run_id: string }> {
  const form = new FormData()
  candidates.forEach((c, _i) => {
    form.append('names', c.name || '')
    form.append('github_urls', c.githubUrl || '')
    if (c.resumeFile) {
      form.append('resume_files', c.resumeFile)
      form.append('resume_texts', '')
    } else {
      form.append('resume_texts', c.resumeText || '')
    }
  })
  const { data } = await api.post(`/api/run/${runId}/candidates`, form)
  return data
}

export async function getResults(runId: string): Promise<CandidateResult[]> {
  const { data } = await api.get(`/api/run/${runId}/results`)
  return data.candidates ?? []
}

export async function getAdjacency(
  runId: string,
  candidateId: string
): Promise<AdjacencyResult> {
  const { data } = await api.get<AdjacencyResult>(
    `/api/run/${runId}/candidates/${candidateId}/adjacency`
  )
  return data
}

export async function runBiasCheck(
  runId: string,
  candidateId: string
): Promise<BiasCheckResult> {
  const { data } = await api.post<BiasCheckResult>(
    `/api/run/${runId}/candidates/${candidateId}/bias-check`
  )
  return data
}
