import json
import asyncio
import logging
from crewai import Crew, Process
from backend.scoring import calculate_final_score
from backend.crew.agents import (
    make_skill_graph_builder, make_resume_parser,
    make_github_analyser, make_scorer,
)
from backend.crew.tasks import (
    build_skill_graph_task, parse_resume_task,
    analyse_github_task, score_candidate_task,
)

logger = logging.getLogger(__name__)

def _parse_json(raw: str) -> dict:
    """Safely extract JSON from agent output, handling markdown fences and stray text."""
    if isinstance(raw, dict):
        return raw
    text = str(raw).strip()

    # Strip markdown fences first
    for fence in ["```json", "```"]:
        if fence in text:
            text = text.split(fence)[1].split("```")[0].strip()
            break

    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Find the outermost JSON object in the string
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return json.loads(text[start:end + 1])

    raise ValueError(f"No valid JSON found in agent output: {text[:200]}")

async def run_skill_graph_crew(jd_text: str, run_id: str) -> dict:
    """Agent 1 only — builds the skill graph. Returns parsed dict."""
    agent = make_skill_graph_builder()
    task = build_skill_graph_task(agent, jd_text, run_id)
    crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=True)
    try:
        result = await asyncio.to_thread(crew.kickoff)
        return _parse_json(result.raw)
    except Exception as e:
        logger.error(f"Skill graph crew failed: {e}")
        raise

async def run_candidate_crew(
    skill_graph: dict,
    resume_content: str,
    resume_format: str,
    github_url: str | None,
    candidate_id: str,
) -> dict:
    """
    Runs Agents 2 and 3 in parallel, then Agent 4 to score.
    Returns the final scored candidate dict from Agent 4.
    """
    github_provided = bool(github_url and github_url.strip())

    # Agent 2: resume parser
    resume_agent = make_resume_parser()
    resume_task = parse_resume_task(
        resume_agent, resume_content, resume_format, skill_graph, candidate_id
    )
    resume_crew = Crew(agents=[resume_agent], tasks=[resume_task],
                       process=Process.sequential, verbose=True)

    # Agent 3: GitHub analyser (skip if no URL)
    if github_provided:
        github_agent = make_github_analyser()
        github_task = analyse_github_task(
            github_agent, github_url, skill_graph, candidate_id
        )
        github_crew = Crew(agents=[github_agent], tasks=[github_task],
                           process=Process.sequential, verbose=True)

        # Run Agents 2 and 3 in parallel
        try:
            resume_result, github_result = await asyncio.gather(
                asyncio.to_thread(resume_crew.kickoff),
                asyncio.to_thread(github_crew.kickoff),
            )
            resume_evidence = _parse_json(resume_result.raw)
            github_evidence = _parse_json(github_result.raw)
        except Exception as e:
            logger.error(f"Parallel agent execution failed: {e}")
            raise
    else:
        # Resume only
        try:
            resume_result = await asyncio.to_thread(resume_crew.kickoff)
            resume_evidence = _parse_json(resume_result.raw)
            github_evidence = {"skill_evidence": []}
        except Exception as e:
            logger.error(f"Resume agent failed: {e}")
            raise

    # Agent 4: scorer
    scorer_agent = make_scorer()
    score_task = score_candidate_task(
        scorer_agent, skill_graph,
        resume_evidence, github_evidence,
        candidate_id, github_provided,
    )
    score_crew = Crew(agents=[scorer_agent], tasks=[score_task],
                      process=Process.sequential, verbose=True)
    try:
        score_result = await asyncio.to_thread(score_crew.kickoff)
        agent_out = _parse_json(score_result.raw)

        # Agent 4 sometimes wraps output in ranked_candidates — unwrap it
        if "ranked_candidates" in agent_out and agent_out["ranked_candidates"]:
            agent_out = agent_out["ranked_candidates"][0]

        # Always compute scores via scoring.py — don't trust agent maths
        computed = calculate_final_score(
            resume_evidence, github_evidence, skill_graph, github_provided
        )

        # Merge: use computed scores, take evidence_paragraphs from agent if present
        agent_skill_scores = {s["skill"]: s for s in agent_out.get("skill_scores", [])}
        for ss in computed["skill_scores"]:
            if ss["skill"] in agent_skill_scores:
                ss["evidence_paragraph"] = agent_skill_scores[ss["skill"]].get(
                    "evidence_paragraph", ss["evidence_paragraph"]
                )

        computed["candidate_id"] = candidate_id
        computed["name"] = agent_out.get("name")
        computed["github_provided"] = github_provided
        computed["resume_available"] = True
        computed["data_gaps"] = agent_out.get("data_gaps", computed.get("data_gaps", []))
        return computed
    except Exception as e:
        logger.error(f"Scorer agent failed: {e}")
        raise
