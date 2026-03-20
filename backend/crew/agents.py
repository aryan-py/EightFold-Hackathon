from pathlib import Path
from crewai import Agent
from crewai_tools import SerperDevTool
from backend.tools.resume_tool import ResumeParserTool
from backend.tools.github_tool import GitHubAnalyserTool

def _load_skills(agent_num: int) -> str:
    path = Path(__file__).parent.parent / "agent_skills" / f"agent{agent_num}_skills.md"
    return path.read_text(encoding="utf-8")

def make_skill_graph_builder() -> Agent:
    return Agent(
        role="Job Description Analyst and Skill Graph Architect",
        goal="Parse a job description, search the web for role-specific skills, and build a structured skill graph JSON",
        backstory=_load_skills(1),
        tools=[SerperDevTool()],
        llm="gpt-4o-mini",
        temperature=0.1,
        max_iter=3,
        verbose=True,
    )

def make_resume_parser() -> Agent:
    return Agent(
        role="Resume Analyst and Skill Evidence Extractor",
        goal="Extract structured skill evidence from a candidate resume matched against the skill graph",
        backstory=_load_skills(2),
        tools=[ResumeParserTool()],
        llm="gpt-4o-mini",
        temperature=0.1,
        max_iter=2,
        verbose=True,
    )

def make_github_analyser() -> Agent:
    return Agent(
        role="Code Profile Analyst and Technical Evidence Extractor",
        goal="Extract structured skill evidence from a candidate GitHub profile matched against the skill graph",
        backstory=_load_skills(3),
        tools=[GitHubAnalyserTool()],
        llm="gpt-4o-mini",
        temperature=0.1,
        max_iter=2,
        verbose=True,
    )

def make_scorer() -> Agent:
    return Agent(
        role="Candidate Evaluator and Final Score Generator",
        goal="Combine resume and GitHub evidence to produce a final scored candidate output with full evidence paragraphs",
        backstory=_load_skills(4),
        tools=[],
        llm="gpt-4o-mini",
        temperature=0.1,
        max_iter=2,
        verbose=True,
    )
