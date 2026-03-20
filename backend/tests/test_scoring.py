import pytest
from backend.scoring import (
    get_role_weights,
    apply_duration_bonus,
    calculate_combined_confidence,
    calculate_final_score,
    resolve_tiebreaker,
)

# ─── get_role_weights ─────────────────────────────────────────────────────────

def test_coding_role_weights():
    W_r, W_g = get_role_weights("coding", github_provided=True)
    assert W_r == 0.35
    assert W_g == 0.65
    assert abs(W_r + W_g - 1.0) < 1e-9


def test_mixed_role_weights():
    W_r, W_g = get_role_weights("mixed", github_provided=True)
    assert W_r == 0.55
    assert W_g == 0.45


def test_non_technical_role_weights():
    W_r, W_g = get_role_weights("non_technical", github_provided=True)
    assert W_r == 1.00
    assert W_g == 0.00


def test_no_github_always_resume_only():
    for role_type in ["coding", "mixed", "non_technical"]:
        W_r, W_g = get_role_weights(role_type, github_provided=False)
        assert W_r == 1.0
        assert W_g == 0.0


def test_unknown_role_falls_back_to_mixed():
    W_r, W_g = get_role_weights("unknown_role", github_provided=True)
    assert W_r == 0.55
    assert W_g == 0.45


# ─── apply_duration_bonus ─────────────────────────────────────────────────────

def test_duration_bonus_4_years():
    result = apply_duration_bonus(0.7, 48)
    assert result == pytest.approx(0.78)


def test_duration_bonus_2_years():
    result = apply_duration_bonus(0.7, 24)
    assert result == pytest.approx(0.75)


def test_duration_bonus_1_year():
    result = apply_duration_bonus(0.7, 12)
    assert result == pytest.approx(0.72)


def test_duration_bonus_none():
    assert apply_duration_bonus(0.7, None) == 0.7


def test_duration_bonus_clamps_at_1():
    assert apply_duration_bonus(0.95, 48) == 1.0


def test_duration_bonus_below_threshold():
    # 11 months → no bonus
    assert apply_duration_bonus(0.5, 11) == pytest.approx(0.5)


# ─── calculate_combined_confidence ────────────────────────────────────────────

def test_combined_confidence_coding_with_github():
    result = calculate_combined_confidence(0.8, 0.9, 0.35, 0.65)
    assert result == pytest.approx(0.8 * 0.35 + 0.9 * 0.65)


def test_combined_clamps_above_1():
    assert calculate_combined_confidence(1.0, 1.0, 1.0, 0.0) == 1.0


def test_combined_clamps_below_0():
    assert calculate_combined_confidence(-0.1, -0.1, 0.5, 0.5) == 0.0


def test_combined_no_github_weight():
    # resume-only scenario
    result = calculate_combined_confidence(0.8, 0.0, 1.0, 0.0)
    assert result == pytest.approx(0.8)


# ─── calculate_final_score ────────────────────────────────────────────────────

MOCK_SKILL_GRAPH = {
    "role_type": "coding",
    "skill_graph": {
        "categories": [
            {
                "name": "Languages",
                "skills": [
                    {"name": "Python", "jd_weight": 1.0, "required": True},
                    {"name": "JavaScript", "jd_weight": 0.5, "required": False},
                ],
            }
        ]
    },
}

MOCK_RESUME_EVIDENCE = {
    "skill_evidence": [
        {
            "skill": "Python",
            "confidence": 0.9,
            "evidence": "3 years Python at fintech startup",
            "duration_months": 36,
        },
        {
            "skill": "JavaScript",
            "confidence": 0.3,
            "evidence": "briefly mentioned in skills section",
            "duration_months": None,
        },
    ]
}

MOCK_GITHUB_EVIDENCE = {
    "skill_evidence": [
        {
            "skill": "Python",
            "confidence": 0.85,
            "evidence": "ml-pipeline repo: 40 commits, pinned",
        },
        {
            "skill": "JavaScript",
            "confidence": 0.0,
            "evidence": "no signal found",
        },
    ]
}


def test_final_score_with_github():
    result = calculate_final_score(
        MOCK_RESUME_EVIDENCE, MOCK_GITHUB_EVIDENCE,
        MOCK_SKILL_GRAPH, github_provided=True
    )
    assert 0.0 <= result["final_score"] <= 1.0
    assert result["resume_weight_applied"] == 0.35
    assert result["github_weight_applied"] == 0.65
    assert len(result["skill_scores"]) == 2


def test_final_score_no_github():
    result = calculate_final_score(
        MOCK_RESUME_EVIDENCE, {},
        MOCK_SKILL_GRAPH, github_provided=False
    )
    assert result["resume_weight_applied"] == 1.0
    assert result["github_weight_applied"] == 0.0
    assert result["github_subscore"] == 0.0


def test_final_score_empty_graph():
    empty_graph = {"role_type": "coding", "skill_graph": {"categories": []}}
    result = calculate_final_score({}, {}, empty_graph, github_provided=True)
    assert result["final_score"] == 0.0


def test_evidence_paragraph_not_empty():
    result = calculate_final_score(
        MOCK_RESUME_EVIDENCE, MOCK_GITHUB_EVIDENCE,
        MOCK_SKILL_GRAPH, github_provided=True
    )
    for skill in result["skill_scores"]:
        assert skill["evidence_paragraph"] != ""
        assert len(skill["evidence_paragraph"]) > 20


def test_duration_bonus_reflected_in_scores():
    # Python has 36 months → +0.05 bonus should be applied
    result = calculate_final_score(
        MOCK_RESUME_EVIDENCE, MOCK_GITHUB_EVIDENCE,
        MOCK_SKILL_GRAPH, github_provided=True
    )
    python_score = next(s for s in result["skill_scores"] if s["skill"] == "Python")
    assert python_score["duration_bonus_applied"] is True
    # 0.9 + 0.05 = 0.95 resume_confidence after bonus
    assert python_score["resume_confidence"] == pytest.approx(0.95)
