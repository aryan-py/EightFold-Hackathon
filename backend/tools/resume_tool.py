from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from pathlib import Path
from typing import Any
import pdfplumber
import base64
import json
import logging
import io
import re

logger = logging.getLogger(__name__)

class ResumeParserInput(BaseModel):
    resume_content: str = Field(description="Base64-encoded PDF or plain text resume")
    resume_format: str = Field(description="'pdf' or 'text'")
    skill_graph: str = Field(description="JSON string of the skill graph from Agent 1")
    candidate_id: str = Field(description="Candidate identifier")

class ResumeParserTool(BaseTool):
    name: str = "resume_parser"
    description: str = (
        "Parse a candidate resume (PDF or plain text) and extract evidence "
        "for each skill in the provided skill graph. Returns structured JSON "
        "matching the agent2 output contract."
    )
    args_schema: type[BaseModel] = ResumeParserInput

    def _run(self, resume_content: str, resume_format: str,
             skill_graph: str, candidate_id: str) -> str:
        try:
            graph = json.loads(skill_graph) if isinstance(skill_graph, str) else skill_graph
            skills = self._extract_skills_from_graph(graph)

            if resume_format == "pdf":
                text = self._extract_pdf_text(resume_content)
            else:
                text = resume_content

            if not text or len(text.strip()) < 100:
                return json.dumps(self._empty_result(candidate_id, skills, "unreadable", resume_format))

            evidence = self._extract_evidence(text, skills)
            return json.dumps({
                "candidate_id": candidate_id,
                "parse_status": "success",
                "source": "resume",
                "resume_format": resume_format,
                "skill_evidence": evidence,
            })

        except Exception as e:
            logger.error(f"Resume parse error for {candidate_id}: {e}")
            graph = json.loads(skill_graph) if isinstance(skill_graph, str) else {}
            skills = self._extract_skills_from_graph(graph)
            return json.dumps(self._empty_result(candidate_id, skills, "unreadable", resume_format))

    def _extract_skills_from_graph(self, graph: dict) -> list[dict]:
        skills = []
        for cat in graph.get("skill_graph", {}).get("categories", []):
            for s in cat.get("skills", []):
                skills.append({
                    "name": s["name"],
                    "aliases": s.get("aliases", []),
                    "category": cat["name"],
                })
        return skills

    def _extract_pdf_text(self, content: str) -> str:
        try:
            pdf_bytes = base64.b64decode(content)
            text_parts = []
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text(x_tolerance=3, y_tolerance=3)
                    if page_text:
                        text_parts.append(page_text)
            return "\n".join(text_parts)
        except Exception as e:
            logger.error(f"PDF extraction failed: {e}")
            return ""

    def _extract_evidence(self, text: str, skills: list[dict]) -> list[dict]:
        """
        Extract evidence for each skill from resume text.
        Detects sections, matches skills by name and alias,
        assigns confidence and section context.
        """
        sections = self._detect_sections(text)
        text_lower = text.lower()
        evidence = []

        for skill in skills:
            names_to_check = [skill["name"]] + skill.get("aliases", [])
            best_evidence = None
            best_confidence = 0.0
            best_section = "none"
            best_match_type = "none"
            best_duration = None

            for section_name, section_text in sections.items():
                section_lower = section_text.lower()
                for name in names_to_check:
                    name_lower = name.lower()
                    if name_lower not in section_lower:
                        continue

                    # Find the sentence containing the match
                    sentences = re.split(r'[.\n]', section_text)
                    context_sentences = [
                        s.strip() for s in sentences
                        if name_lower in s.lower() and len(s.strip()) > 5
                    ]
                    if not context_sentences:
                        continue

                    context = context_sentences[0][:200]
                    duration = self._extract_duration(section_text)
                    confidence, match_type = self._score_evidence(
                        section_name, context, duration
                    )

                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_evidence = context
                        best_section = section_name
                        best_match_type = match_type
                        best_duration = duration

            # Multi-section bonus
            sections_with_match = sum(
                1 for sname, stxt in sections.items()
                if any(n.lower() in stxt.lower() for n in names_to_check)
            )
            if sections_with_match >= 2 and best_confidence > 0:
                best_confidence = min(1.0, best_confidence + 0.08)

            evidence.append({
                "skill": skill["name"],
                "confidence": round(best_confidence, 4),
                "evidence": best_evidence or "no signal found",
                "section": best_section,
                "duration_months": best_duration,
                "match_type": best_match_type,
            })

        return evidence

    def _detect_sections(self, text: str) -> dict[str, str]:
        """Split resume text into named sections."""
        section_patterns = {
            "work_experience": r"(experience|employment|work history|career)",
            "projects": r"(projects?|portfolio|personal projects?)",
            "education": r"(education|academic|university|college)",
            "skills_list": r"(skills?|technical skills?|core competencies)",
            "certifications": r"(certifications?|certificates?|credentials?)",
            "summary": r"(summary|objective|profile|about)",
        }

        lines = text.split("\n")
        sections: dict[str, list[str]] = {"summary": []}
        current = "summary"

        for line in lines:
            line_stripped = line.strip()
            matched = False
            for section_name, pattern in section_patterns.items():
                if re.search(pattern, line_stripped.lower()) and len(line_stripped) < 50:
                    current = section_name
                    if current not in sections:
                        sections[current] = []
                    matched = True
                    break
            if not matched:
                sections.setdefault(current, []).append(line)

        return {k: " ".join(v) for k, v in sections.items() if v}

    def _extract_duration(self, text: str) -> int | None:
        """Extract duration in months from text."""
        # Pattern: "X years" or "X+ years"
        year_match = re.search(r'(\d+)\+?\s*year', text.lower())
        if year_match:
            return int(year_match.group(1)) * 12

        # Pattern: date ranges like "Jan 2020 - Mar 2023"
        date_range = re.findall(
            r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{4})',
            text.lower()
        )
        if len(date_range) >= 2:
            months_map = {
                'jan':1,'feb':2,'mar':3,'apr':4,'may':5,'jun':6,
                'jul':7,'aug':8,'sep':9,'oct':10,'nov':11,'dec':12
            }
            try:
                m1, y1 = months_map[date_range[0][0][:3]], int(date_range[0][1])
                m2, y2 = months_map[date_range[-1][0][:3]], int(date_range[-1][1])
                return max(0, (y2 - y1) * 12 + (m2 - m1))
            except (KeyError, ValueError):
                pass
        return None

    def _score_evidence(self, section: str, context: str,
                         duration: int | None) -> tuple[float, str]:
        """Returns (confidence, match_type)."""
        section_base = {
            "work_experience": 0.72,
            "projects": 0.65,
            "certifications": 0.60,
            "skills_list": 0.35,
            "education": 0.25,
            "summary": 0.15,
            "none": 0.10,
        }
        base = section_base.get(section, 0.35)
        match_type = "direct_with_context" if len(context) > 30 else "direct_no_context"

        # Outcome indicators boost confidence
        outcome_patterns = [r'\d+%', r'\d+x', r'million', r'thousand',
                            r'reduced', r'improved', r'built', r'deployed',
                            r'production', r'launched']
        for pat in outcome_patterns:
            if re.search(pat, context.lower()):
                base = min(1.0, base + 0.10)
                break

        # Vague terms reduce confidence
        vague = ['familiar with', 'exposure to', 'knowledge of', 'understanding of']
        if any(v in context.lower() for v in vague):
            base = max(0.0, base - 0.05)

        return round(base, 4), match_type

    def _empty_result(self, candidate_id: str, skills: list[dict],
                       status: str, fmt: str) -> dict:
        return {
            "candidate_id": candidate_id,
            "parse_status": status,
            "source": "resume",
            "resume_format": fmt,
            "skill_evidence": [
                {
                    "skill": s["name"],
                    "confidence": 0.0,
                    "evidence": "no signal found",
                    "section": "none",
                    "duration_months": None,
                    "match_type": "none",
                }
                for s in skills
            ],
        }
