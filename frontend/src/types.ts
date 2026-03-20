export interface SkillRelationship {
  type: 'requires' | 'complements' | 'related_to'
  skill: string
}

export interface SkillNode {
  name: string
  aliases: string[]
  source: 'explicit' | 'inferred'
  required: boolean
  jd_weight: number
  relationships: SkillRelationship[]
}

export interface SkillCategory {
  name: string
  skills: SkillNode[]
}

export interface SkillGraph {
  run_id: string
  job_title: string
  role_type: 'coding' | 'mixed' | 'non_technical'
  search_status: 'success' | 'failed' | 'partial'
  resume_weight: number
  github_weight: number
  skill_graph: {
    categories: SkillCategory[]
  }
}

export interface SkillScore {
  skill: string
  jd_weight: number
  resume_confidence: number
  github_confidence: number
  combined_confidence: number
  weighted_contribution: number
  duration_bonus_applied: boolean
  evidence_paragraph: string
}

export interface CandidateResult {
  candidate_id: string
  run_id: string
  name: string | null
  final_score: number
  resume_subscore: number
  github_subscore: number
  resume_weight_applied: number
  github_weight_applied: number
  github_provided: boolean
  resume_available: boolean
  tiebreaker_applied: boolean
  tiebreaker_reason: string | null
  data_gaps: string[]
  skill_scores: SkillScore[]
}

export interface RunResponse {
  run_id: string
  job_title: string
  role_type: string
  resume_weight: number
  github_weight: number
  skill_graph: SkillGraph
}

export interface CandidateFormData {
  name: string
  resumeText: string
  resumeFile: File | null
  githubUrl: string
}

export interface AdjacencyItem {
  missing_skill: string
  bridge_skill: string | null
  bridge_skill_confidence: number
  relationship_type: string | null
  ttp_weeks_low: number | null
  ttp_weeks_high: number | null
  learning_path: string[]
  rationale: string
}

export interface AdjacencyResult {
  candidate_id: string
  run_id: string
  gap_count: number
  adjacencies: AdjacencyItem[]
  overall_ttp_weeks_low: number | null
  overall_ttp_weeks_high: number | null
}

export interface BiasCheckResult {
  candidate_id: string
  run_id: string
  score_original: number
  score_masked: number
  delta: number
  delta_percent: number
  is_biased: boolean
  masked_fields: string[]
  explanation: string
  checked_at: string
}
