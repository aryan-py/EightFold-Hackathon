import json
from crewai import Task
from crewai import Agent


def _skill_names_summary(skill_graph: dict) -> str:
    """Human-readable skill names for task description only (not passed to tools)."""
    names = []
    for cat in skill_graph.get("skill_graph", {}).get("categories", []):
        for s in cat.get("skills", []):
            names.append(s["name"])
    return ", ".join(names)


def _slim_evidence_for_scoring(evidence: dict) -> str:
    """Keep only what Agent 4 needs — drop repo_signals, topics, recency, etc."""
    slim = [
        {
            "skill": e.get("skill"),
            "confidence": e.get("confidence", 0.0),
            "evidence": e.get("evidence", "no signal found"),
            "duration_months": e.get("duration_months"),
        }
        for e in evidence.get("skill_evidence", [])
    ]
    return json.dumps({"candidate_id": evidence.get("candidate_id"), "skill_evidence": slim})


def build_skill_graph_task(agent: Agent, jd_text: str, run_id: str) -> Task:
    return Task(
        description=f"""Analyse this JD and build a skill graph JSON.
Run ID: {run_id}

JD:
{jd_text}

Steps: extract title, web-search role skills, cross-validate against JD, build graph, set role_type and weights.

Return ONLY valid JSON with this structure — no markdown, no explanation:
{{
  "run_id": "{run_id}",
  "job_title": "<string>",
  "role_type": "coding|mixed|non_technical",
  "search_status": "success|failed|partial",
  "resume_weight": 0.0,
  "github_weight": 0.0,
  "skill_graph": {{
    "categories": [
      {{
        "name": "Languages|Frameworks|Tools|Domain Knowledge|Soft Skills",
        "skills": [
          {{
            "name": "<string>",
            "aliases": ["<string>"],
            "source": "explicit|inferred",
            "required": true,
            "jd_weight": 0.0,
            "relationships": [{{"type": "requires|complements|related_to", "skill": "<string>"}}]
          }}
        ]
      }}
    ]
  }}
}}""",
        expected_output="Valid JSON skill graph",
        agent=agent,
    )


def parse_resume_task(agent: Agent, resume_content: str,
                       resume_format: str, skill_graph: dict,
                       candidate_id: str) -> Task:
    graph_str = json.dumps(skill_graph)
    return Task(
        description=f"""Extract skill evidence from this resume.
Candidate: {candidate_id} | Format: {resume_format}
Skills to score: {_skill_names_summary(skill_graph)}

Use resume_parser tool with these exact args:
- resume_content: the resume text below
- resume_format: "{resume_format}"
- skill_graph: {graph_str}
- candidate_id: "{candidate_id}"

RESUME:
{resume_content[:3000]}

Return ONLY the tool's JSON output. Every skill must have an entry. Use "no signal found" if absent.""",
        expected_output="Valid JSON resume evidence",
        agent=agent,
    )


def analyse_github_task(agent: Agent, github_url: str,
                         skill_graph: dict, candidate_id: str) -> Task:
    graph_str = json.dumps(skill_graph)
    return Task(
        description=f"""Analyse this GitHub profile for skill evidence.
Candidate: {candidate_id} | URL: {github_url}
Skills to score: {_skill_names_summary(skill_graph)}

Use github_analyser tool with these exact args:
- github_url: "{github_url}"
- skill_graph: {graph_str}
- candidate_id: "{candidate_id}"

Return ONLY the tool's JSON output. Every skill must have an entry.""",
        expected_output="Valid JSON GitHub evidence",
        agent=agent,
    )


def score_candidate_task(agent: Agent, skill_graph: dict,
                          resume_evidence: dict, github_evidence: dict,
                          candidate_id: str, github_provided: bool) -> Task:
    return Task(
        description=f"""Score this candidate.
Candidate: {candidate_id} | GitHub provided: {github_provided}

SKILL GRAPH:
{json.dumps(skill_graph)}

RESUME EVIDENCE:
{_slim_evidence_for_scoring(resume_evidence)}

GITHUB EVIDENCE:
{_slim_evidence_for_scoring(github_evidence)}

Formula: combined[i]=resume_conf[i]*W_r+github_conf[i]*W_g; final_score=sum(combined[i]*jd_weight[i])/sum(jd_weight[i])
Write a 2-4 sentence evidence_paragraph per skill for non-technical recruiters.
Return ONLY valid JSON — no markdown.""",
        expected_output="Valid JSON scored candidate",
        agent=agent,
    )
