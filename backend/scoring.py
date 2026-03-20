from __future__ import annotations
from typing import TypedDict


class RoleWeights(TypedDict):
    resume_weight: float
    github_weight: float


ROLE_WEIGHTS: dict[str, RoleWeights] = {
    "coding":        {"resume_weight": 0.35, "github_weight": 0.65},
    "mixed":         {"resume_weight": 0.55, "github_weight": 0.45},
    "non_technical": {"resume_weight": 1.00, "github_weight": 0.00},
}

DURATION_BONUSES = [
    (48, 0.08),
    (24, 0.05),
    (12, 0.02),
]


def get_role_weights(role_type: str, github_provided: bool) -> tuple[float, float]:
    """
    Returns (resume_weight, github_weight).
    If github_provided is False, always returns (1.0, 0.0).
    Falls back to "mixed" weights for unknown role_type.
    """
    if not github_provided:
        return 1.0, 0.0
    weights = ROLE_WEIGHTS.get(role_type, ROLE_WEIGHTS["mixed"])
    return weights["resume_weight"], weights["github_weight"]


def apply_duration_bonus(
    resume_confidence: float,
    duration_months: int | None,
) -> float:
    """
    Applies duration bonus to resume_confidence.
    Returns adjusted confidence clamped to [0.0, 1.0].
    """
    if duration_months is None:
        return resume_confidence
    for threshold, bonus in DURATION_BONUSES:
        if duration_months >= threshold:
            return min(1.0, resume_confidence + bonus)
    return resume_confidence


def calculate_combined_confidence(
    resume_confidence: float,
    github_confidence: float,
    resume_weight: float,
    github_weight: float,
) -> float:
    """Blended confidence clamped to [0.0, 1.0]."""
    return min(1.0, max(0.0,
        resume_confidence * resume_weight +
        github_confidence * github_weight
    ))


def calculate_final_score(
    resume_evidence: dict,
    github_evidence: dict,
    skill_graph: dict,
    github_provided: bool,
) -> dict:
    """
    Core scoring function. Takes evidence from Agents 2 and 3,
    the skill graph from Agent 1, and produces the full scored result
    matching the output contract in agent4_skills.md.

    Returns dict with:
      final_score, resume_subscore, github_subscore,
      resume_weight_applied, github_weight_applied,
      skill_scores (list of per-skill dicts)
    """
    role_type = skill_graph.get("role_type", "mixed")
    W_r, W_g = get_role_weights(role_type, github_provided)

    # Build lookup dicts from evidence lists
    resume_map = {
        e["skill"]: e
        for e in resume_evidence.get("skill_evidence", [])
    }
    github_map = {
        e["skill"]: e
        for e in github_evidence.get("skill_evidence", [])
    }

    skill_scores = []
    total_weight = 0.0
    weighted_score_sum = 0.0
    weighted_resume_sum = 0.0
    weighted_github_sum = 0.0

    for category in skill_graph.get("skill_graph", {}).get("categories", []):
        for skill_node in category.get("skills", []):
            skill_name = skill_node["name"]
            jd_weight = skill_node.get("jd_weight", 0.5)

            r_ev = resume_map.get(skill_name, {})
            g_ev = github_map.get(skill_name, {})

            r_conf = float(r_ev.get("confidence", 0.0))
            g_conf = float(g_ev.get("confidence", 0.0))
            duration = r_ev.get("duration_months")

            bonus_applied = False
            if duration is not None:
                r_conf_boosted = apply_duration_bonus(r_conf, duration)
                bonus_applied = r_conf_boosted > r_conf
                r_conf = r_conf_boosted

            combined = calculate_combined_confidence(r_conf, g_conf, W_r, W_g)
            contribution = combined * jd_weight

            r_text = r_ev.get("evidence", "no signal found")
            g_text = g_ev.get("evidence", "no signal found")
            paragraph = _build_evidence_paragraph(
                skill_name, r_text, g_text, combined, github_provided, bonus_applied
            )

            skill_scores.append({
                "skill": skill_name,
                "jd_weight": jd_weight,
                "resume_confidence": r_conf,
                "github_confidence": g_conf,
                "combined_confidence": round(combined, 4),
                "weighted_contribution": round(contribution, 4),
                "duration_bonus_applied": bonus_applied,
                "evidence_paragraph": paragraph,
            })

            total_weight += jd_weight
            weighted_score_sum += contribution
            weighted_resume_sum += r_conf * jd_weight
            weighted_github_sum += g_conf * jd_weight

    if total_weight == 0:
        final_score = 0.0
        resume_sub = 0.0
        github_sub = 0.0
    else:
        final_score = round(weighted_score_sum / total_weight, 4)
        resume_sub = round(weighted_resume_sum / total_weight, 4)
        github_sub = round(weighted_github_sum / total_weight, 4)

    return {
        "final_score": final_score,
        "resume_subscore": resume_sub,
        "github_subscore": github_sub,
        "resume_weight_applied": W_r,
        "github_weight_applied": W_g,
        "skill_scores": skill_scores,
    }


def _build_evidence_paragraph(
    skill: str,
    resume_evidence: str,
    github_evidence: str,
    combined_confidence: float,
    github_provided: bool,
    duration_bonus: bool,
) -> str:
    """
    Builds a recruiter-readable evidence paragraph for a skill.
    Follows the format specified in agent4_skills.md Section 5.
    """
    lines = []

    if resume_evidence and resume_evidence != "no signal found":
        lines.append(f"Resume: {resume_evidence}.")
    else:
        lines.append("No resume evidence found for this skill.")

    if not github_provided:
        lines.append(
            "GitHub was not provided — score reflects resume evidence only "
            "and may underestimate practical coding ability."
        )
    elif github_evidence and github_evidence != "no signal found":
        lines.append(f"GitHub: {github_evidence}.")
    else:
        lines.append("No GitHub evidence found for this skill.")

    conf_label = (
        "strong" if combined_confidence >= 0.7
        else "moderate" if combined_confidence >= 0.4
        else "weak"
    )
    lines.append(
        f"Combined confidence: {combined_confidence:.0%} ({conf_label})."
        + (" Duration bonus applied." if duration_bonus else "")
    )

    return " ".join(lines)


def resolve_tiebreaker(
    candidate_a: dict,
    candidate_b: dict,
) -> tuple[dict, dict]:
    """
    Resolves a tie between two candidates following agent4_skills.md rules.
    Returns (higher_ranked, lower_ranked) with tiebreaker fields set.
    """
    def sources_available(c: dict) -> int:
        return sum([
            c.get("resume_available", False),
            c.get("github_provided", False),
        ])

    rules = [
        ("github_subscore", "Higher GitHub sub-score"),
        ("resume_subscore", "Higher resume sub-score"),
    ]

    for field, reason in rules:
        a_val = candidate_a.get(field, 0.0)
        b_val = candidate_b.get(field, 0.0)
        if abs(a_val - b_val) > 0.001:
            winner, loser = (
                (candidate_a, candidate_b) if a_val > b_val
                else (candidate_b, candidate_a)
            )
            winner["tiebreaker_applied"] = True
            winner["tiebreaker_reason"] = reason
            return winner, loser

    # Tiebreaker: more data sources
    a_sources = sources_available(candidate_a)
    b_sources = sources_available(candidate_b)
    if a_sources != b_sources:
        winner, loser = (
            (candidate_a, candidate_b) if a_sources > b_sources
            else (candidate_b, candidate_a)
        )
        winner["tiebreaker_applied"] = True
        winner["tiebreaker_reason"] = "More data sources available"
        return winner, loser

    # Final fallback: alphabetical
    winner = min(candidate_a, candidate_b,
                 key=lambda c: c.get("candidate_id", ""))
    loser = candidate_b if winner is candidate_a else candidate_a
    winner["tiebreaker_applied"] = True
    winner["tiebreaker_reason"] = "Alphabetical fallback"
    return winner, loser
