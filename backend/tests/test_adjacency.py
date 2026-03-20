from backend.adjacency import find_adjacencies, _build_learning_path, _build_rationale

MOCK_SKILL_GRAPH = {
    "role_type": "coding",
    "skill_graph": {
        "categories": [
            {"name": "Frameworks", "skills": [
                {"name": "PyTorch", "jd_weight": 0.95, "relationships": [
                    {"type": "requires", "skill": "Python"}
                ]},
                {"name": "FastAPI", "jd_weight": 0.7, "relationships": []},
                {"name": "Vue",     "jd_weight": 0.5, "relationships": [
                    {"type": "sibling", "skill": "React"}
                ]},
            ]}
        ]
    }
}

STRONG_SCORES = [
    {"skill": "Python",  "combined_confidence": 0.85, "jd_weight": 1.0},
    {"skill": "PyTorch", "combined_confidence": 0.80, "jd_weight": 0.95},
    {"skill": "FastAPI", "combined_confidence": 0.60, "jd_weight": 0.70},
    {"skill": "Vue",     "combined_confidence": 0.05, "jd_weight": 0.50},
]

PARTIAL_SCORES = [
    {"skill": "Python",  "combined_confidence": 0.80, "jd_weight": 1.0},
    {"skill": "PyTorch", "combined_confidence": 0.10, "jd_weight": 0.95},
    {"skill": "FastAPI", "combined_confidence": 0.60, "jd_weight": 0.70},
    {"skill": "Vue",     "combined_confidence": 0.05, "jd_weight": 0.50},
]

NO_SKILLS_SCORES = [
    {"skill": "Python",  "combined_confidence": 0.10, "jd_weight": 1.0},
    {"skill": "PyTorch", "combined_confidence": 0.05, "jd_weight": 0.95},
    {"skill": "FastAPI", "combined_confidence": 0.05, "jd_weight": 0.70},
]


def test_finds_gap_with_bridge():
    results = find_adjacencies(STRONG_SCORES, MOCK_SKILL_GRAPH)
    gap_skills = [r.missing_skill for r in results]
    assert "Vue" in gap_skills
    vue_gap = next(r for r in results if r.missing_skill == "Vue")
    assert vue_gap.bridge_skill is not None


def test_ttp_is_positive_when_bridge_found():
    results = find_adjacencies(PARTIAL_SCORES, MOCK_SKILL_GRAPH)
    pytorch_gap = next((r for r in results if r.missing_skill == "PyTorch"), None)
    assert pytorch_gap is not None
    if pytorch_gap.ttp_weeks_low:
        assert pytorch_gap.ttp_weeks_low > 0
        assert pytorch_gap.ttp_weeks_high >= pytorch_gap.ttp_weeks_low


def test_cold_gap_when_no_bridge():
    results = find_adjacencies(NO_SKILLS_SCORES, MOCK_SKILL_GRAPH)
    for r in results:
        assert r.bridge_skill is None or r.bridge_skill_confidence < 0.4


def test_sorted_by_ttp_ascending():
    results = find_adjacencies(PARTIAL_SCORES, MOCK_SKILL_GRAPH)
    ttps = [r.ttp_weeks_low for r in results if r.ttp_weeks_low is not None]
    assert ttps == sorted(ttps)


def test_above_threshold_not_in_gaps():
    results = find_adjacencies(STRONG_SCORES, MOCK_SKILL_GRAPH)
    gap_skills = {r.missing_skill for r in results}
    assert "Python" not in gap_skills
    assert "FastAPI" not in gap_skills


def test_learning_path_has_five_steps():
    path = _build_learning_path("Python", "FastAPI")
    assert len(path) == 5
    assert all(isinstance(s, str) and len(s) > 10 for s in path)


def test_rationale_mentions_both_skills():
    rationale = _build_rationale(
        candidate_has="Python", candidate_lacks="FastAPI",
        bridge_conf=0.85, relationship="sibling",
        ttp_low=1, ttp_high=2,
    )
    assert "Python" in rationale
    assert "FastAPI" in rationale
    assert "1" in rationale
