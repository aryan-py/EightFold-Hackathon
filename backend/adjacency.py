from __future__ import annotations
import uuid
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ── Static TTP estimates (weeks to reach working proficiency)
# Format: ("from_skill", "to_skill", weeks_low, weeks_high, relationship)
STATIC_TTP_TABLE: list[tuple[str, str, int, int, str]] = [
    # Languages → Languages
    ("Python",       "R",          2,  4,  "sibling"),
    ("Python",       "JavaScript", 4,  8,  "sibling"),
    ("JavaScript",   "TypeScript", 1,  2,  "extension"),
    ("JavaScript",   "Python",     4,  8,  "sibling"),
    ("C++",          "Rust",       8, 16,  "sibling"),
    ("C++",          "C",          1,  2,  "subset"),
    ("Java",         "Kotlin",     2,  4,  "extension"),
    ("Java",         "Scala",      6, 12,  "sibling"),

    # Frameworks → Frameworks (same language family)
    ("React",        "Vue",        2,  3,  "sibling"),
    ("React",        "Angular",    4,  6,  "sibling"),
    ("Django",       "FastAPI",    1,  2,  "sibling"),
    ("Django",       "Flask",      1,  2,  "sibling"),
    ("FastAPI",      "Django",     2,  4,  "sibling"),
    ("PyTorch",      "TensorFlow", 2,  4,  "sibling"),
    ("TensorFlow",   "PyTorch",    2,  4,  "sibling"),
    ("scikit-learn", "PyTorch",    6, 10,  "advanced"),
    ("PyTorch",      "JAX",        4,  8,  "sibling"),

    # Frontend
    ("JavaScript",   "Vue",        2,  3,  "sibling"),
    ("JavaScript",   "React",      2,  4,  "sibling"),
    ("Python",       "Vue",        8, 12,  "related_to"),
    ("Python",       "React",      8, 12,  "related_to"),

    # Tools / Infra
    ("Docker",       "Kubernetes", 4,  8,  "advanced"),
    ("Git",          "GitHub Actions", 1, 2, "extension"),
    ("SQL",          "PostgreSQL", 1,  2,  "extension"),
    ("SQL",          "MongoDB",    2,  4,  "sibling"),
    ("AWS",          "GCP",        2,  4,  "sibling"),
    ("AWS",          "Azure",      2,  4,  "sibling"),

    # ML / Data
    ("Machine Learning",  "Deep Learning",    6, 12, "advanced"),
    ("Machine Learning",  "NLP",              4,  8, "specialisation"),
    ("Machine Learning",  "Computer Vision",  4,  8, "specialisation"),
    ("Data Analysis",     "Machine Learning", 8, 16, "advanced"),
    ("Statistics",        "Machine Learning", 6, 12, "advanced"),
    ("scikit-learn",      "NLP",              4,  8, "specialisation"),
]


def _build_ttp_index(table: list) -> dict[str, list[dict]]:
    """Returns dict: target_skill (lowercase) → [{"from", "to", ttp_weeks_low, ttp_weeks_high, relationship_type}, ...]"""
    idx: dict[str, list[dict]] = {}
    for from_s, to_s, low, high, rel in table:
        idx.setdefault(to_s.lower(), []).append({
            "from": from_s, "to": to_s,
            "ttp_weeks_low": low, "ttp_weeks_high": high,
            "relationship_type": rel,
        })
    return idx


TTP_INDEX = _build_ttp_index(STATIC_TTP_TABLE)

RELATIONSHIP_WEIGHTS = {
    "extension":      0.95,
    "subset":         0.90,
    "sibling":        0.75,
    "advanced":       0.50,
    "specialisation": 0.60,
    "related_to":     0.55,
    "complements":    0.65,
    "requires":       0.40,
}


@dataclass
class AdjacencyResult:
    missing_skill: str
    bridge_skill: str | None
    bridge_skill_confidence: float
    relationship_type: str | None
    ttp_weeks_low: int | None
    ttp_weeks_high: int | None
    learning_path: list[str]
    rationale: str


def find_adjacencies(
    skill_scores: list[dict],
    skill_graph: dict,
    gap_threshold: float = 0.4,
) -> list[AdjacencyResult]:
    """
    For each skill with combined_confidence < gap_threshold, finds the best
    bridge skill the candidate already has and estimates TTP.
    Returns list sorted by ttp_weeks_low ascending.
    """
    owned: dict[str, float] = {
        s["skill"].lower(): s.get("combined_confidence", 0.0)
        for s in skill_scores
        if s.get("combined_confidence", 0.0) >= gap_threshold
    }

    missing = [
        s for s in skill_scores
        if s.get("combined_confidence", 0.0) < gap_threshold
        and s.get("jd_weight", 0.0) >= 0.3
    ]

    # Extract Agent 1 graph relationships for runtime lookup.
    # relationship: skill_node "has relationship" rel["skill"]
    # For gap-filling we want: "if candidate has rel['skill'], they can learn skill_node"
    # So index by skill_node (the missing target), from = rel["skill"] (the bridge).
    graph_relationships: dict[str, list[dict]] = {}
    for cat in skill_graph.get("skill_graph", {}).get("categories", []):
        for skill_node in cat.get("skills", []):
            target = skill_node["name"].lower()
            for rel in skill_node.get("relationships", []):
                rel_type = rel.get("type", "related_to")
                graph_relationships.setdefault(target, []).append({
                    "from": rel["skill"],
                    "to": skill_node["name"],
                    "ttp_weeks_low": _default_ttp_from_rel(rel_type),
                    "ttp_weeks_high": _default_ttp_from_rel(rel_type) * 2,
                    "relationship_type": rel_type,
                })

    results: list[AdjacencyResult] = []

    for gap_skill in missing:
        target = gap_skill["skill"].lower()
        best: dict | None = None
        best_score = -1.0

        routes = TTP_INDEX.get(target, []) + graph_relationships.get(target, [])

        for route in routes:
            from_skill_lower = route["from"].lower()
            if from_skill_lower not in owned:
                continue
            bridge_conf = owned[from_skill_lower]
            rel_weight = RELATIONSHIP_WEIGHTS.get(route["relationship_type"], 0.5)
            route_score = bridge_conf * rel_weight

            if route_score > best_score:
                best_score = route_score
                best = {**route, "bridge_conf": bridge_conf}

        if best:
            learning_path = _build_learning_path(best["from"], gap_skill["skill"])
            rationale = _build_rationale(
                candidate_has=best["from"],
                candidate_lacks=gap_skill["skill"],
                bridge_conf=best["bridge_conf"],
                relationship=best["relationship_type"],
                ttp_low=best["ttp_weeks_low"],
                ttp_high=best["ttp_weeks_high"],
            )
            results.append(AdjacencyResult(
                missing_skill=gap_skill["skill"],
                bridge_skill=best["from"],
                bridge_skill_confidence=round(best["bridge_conf"], 3),
                relationship_type=best["relationship_type"],
                ttp_weeks_low=best["ttp_weeks_low"],
                ttp_weeks_high=best["ttp_weeks_high"],
                learning_path=learning_path,
                rationale=rationale,
            ))
        else:
            results.append(AdjacencyResult(
                missing_skill=gap_skill["skill"],
                bridge_skill=None,
                bridge_skill_confidence=0.0,
                relationship_type=None,
                ttp_weeks_low=None,
                ttp_weeks_high=None,
                learning_path=[],
                rationale=(
                    f"No adjacent skill found for {gap_skill['skill']}. "
                    f"This represents a cold learning gap — expect 12+ weeks to reach proficiency."
                ),
            ))

    results.sort(key=lambda r: r.ttp_weeks_low if r.ttp_weeks_low else 999)
    return results


def _default_ttp_from_rel(rel_type: str) -> int:
    defaults = {
        "requires": 4, "complements": 3, "related_to": 6,
        "extension": 1, "sibling": 4, "advanced": 8,
    }
    return defaults.get(rel_type, 6)


def _build_learning_path(bridge: str, target: str) -> list[str]:
    return [
        f"Leverage existing {bridge} knowledge as foundation",
        f"Complete an introductory {target} course (Coursera/Udemy, ~10 hrs)",
        f"Build one small project combining {bridge} and {target}",
        f"Contribute to an open-source {target} project or solve 3 Leetcode/Kaggle problems using {target}",
        f"Apply {target} in a real work task or side project",
    ]


def _build_rationale(
    candidate_has: str, candidate_lacks: str,
    bridge_conf: float, relationship: str,
    ttp_low: int, ttp_high: int,
) -> str:
    rel_desc = {
        "extension":      f"{candidate_has} and {candidate_lacks} are closely related — same ecosystem, different syntax.",
        "sibling":        f"{candidate_has} and {candidate_lacks} share core concepts and a similar mental model.",
        "advanced":       f"{candidate_has} is a prerequisite for {candidate_lacks} — this is a natural progression.",
        "specialisation": f"{candidate_has} provides the foundation; {candidate_lacks} is a domain specialisation.",
        "requires":       f"{candidate_has} directly requires {candidate_lacks} in most production contexts.",
        "complements":    f"{candidate_has} and {candidate_lacks} are typically used together.",
        "related_to":     f"{candidate_has} and {candidate_lacks} share overlapping concepts.",
    }.get(relationship, f"{candidate_has} provides transferable knowledge toward {candidate_lacks}.")

    return (
        f"Candidate demonstrates {bridge_conf:.0%} confidence in {candidate_has}. "
        f"{rel_desc} "
        f"Estimated time to working proficiency in {candidate_lacks}: "
        f"{ttp_low}–{ttp_high} weeks with focused learning."
    )


async def compute_and_save_adjacency(
    candidate_id: str,
    run_id: str,
    skill_scores: list[dict],
    skill_graph: dict,
) -> list[dict]:
    """Compute adjacency, save to DB, return serialisable list."""
    from backend.db import save_adjacency_results, get_adjacency_results

    existing = await get_adjacency_results(candidate_id)
    if existing:
        return existing

    results = find_adjacencies(skill_scores, skill_graph)

    db_rows = [
        {
            "result_id": str(uuid.uuid4()),
            "candidate_id": candidate_id,
            "run_id": run_id,
            "missing_skill": r.missing_skill,
            "bridge_skill": r.bridge_skill,
            "bridge_skill_confidence": r.bridge_skill_confidence,
            "relationship_type": r.relationship_type,
            "ttp_weeks_low": r.ttp_weeks_low,
            "ttp_weeks_high": r.ttp_weeks_high,
            "learning_path": r.learning_path,
            "rationale": r.rationale,
        }
        for r in results
    ]

    await save_adjacency_results(db_rows)
    return db_rows
