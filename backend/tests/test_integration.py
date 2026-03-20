import asyncio, json, pytest, uuid
from backend.scoring import calculate_final_score, get_role_weights
from backend.db import init_db, create_run, save_skill_graph, get_skill_graph

SAMPLE_SKILL_GRAPH = {
    "run_id": "test-run-001",
    "job_title": "Senior ML Engineer",
    "role_type": "coding",
    "search_status": "success",
    "resume_weight": 0.35,
    "github_weight": 0.65,
    "skill_graph": {
        "categories": [
            {
                "name": "Languages",
                "skills": [
                    {"name": "Python", "aliases": ["py", "python3"], "source": "explicit",
                     "required": True, "jd_weight": 1.0, "relationships": []}
                ]
            },
            {
                "name": "Frameworks",
                "skills": [
                    {"name": "PyTorch", "aliases": ["torch"], "source": "explicit",
                     "required": True, "jd_weight": 0.95, "relationships": [
                         {"type": "requires", "skill": "Python"}
                     ]},
                    {"name": "FastAPI", "aliases": [], "source": "explicit",
                     "required": False, "jd_weight": 0.7, "relationships": []},
                ]
            },
            {
                "name": "Tools",
                "skills": [
                    {"name": "Docker", "aliases": [], "source": "inferred",
                     "required": False, "jd_weight": 0.4, "relationships": []}
                ]
            }
        ]
    }
}

MOCK_RESUME_STRONG = {
    "skill_evidence": [
        {"skill": "Python", "confidence": 0.85, "evidence": "3 years Python at ML startup, built data pipelines", "duration_months": 36},
        {"skill": "PyTorch", "confidence": 0.75, "evidence": "Built image classification model with PyTorch, deployed to AWS", "duration_months": 18},
        {"skill": "FastAPI", "confidence": 0.60, "evidence": "Listed FastAPI in skills section with project reference", "duration_months": 12},
        {"skill": "Docker", "confidence": 0.0, "evidence": "no signal found", "duration_months": None},
    ]
}

MOCK_GITHUB_STRONG = {
    "skill_evidence": [
        {"skill": "Python", "confidence": 0.90, "evidence": "ml-pipeline: Python primary (82%), 47 commits, last active 2 weeks ago"},
        {"skill": "PyTorch", "confidence": 0.80, "evidence": "ml-pipeline: PyTorch in requirements.txt, 3 notebooks training CNNs"},
        {"skill": "FastAPI", "confidence": 0.70, "evidence": "api-service: FastAPI in requirements.txt, 22 commits"},
        {"skill": "Docker", "confidence": 0.65, "evidence": "api-service: Dockerfile present, docker-compose.yml found"},
    ]
}

MOCK_RESUME_WEAK = {
    "skill_evidence": [
        {"skill": "Python", "confidence": 0.35, "evidence": "Python listed in skills section", "duration_months": None},
        {"skill": "PyTorch", "confidence": 0.10, "evidence": "Mentions AI interest in summary", "duration_months": None},
        {"skill": "FastAPI", "confidence": 0.0, "evidence": "no signal found", "duration_months": None},
        {"skill": "Docker", "confidence": 0.0, "evidence": "no signal found", "duration_months": None},
    ]
}

@pytest.mark.asyncio
async def test_db_init():
    await init_db()

@pytest.mark.asyncio
async def test_create_and_retrieve_run():
    run_id = str(uuid.uuid4())
    await init_db()
    await create_run(run_id, "Test Job", "Test JD text")
    await save_skill_graph(run_id, SAMPLE_SKILL_GRAPH, "success")
    graph = await get_skill_graph(run_id)
    assert graph is not None
    assert graph["job_title"] == "Senior ML Engineer"
    assert graph["role_type"] == "coding"
    categories = graph["skill_graph"]["categories"]
    assert len(categories) >= 3

def test_role_weights_coding_with_github():
    W_r, W_g = get_role_weights("coding", True)
    assert abs(W_r + W_g - 1.0) < 1e-9
    assert W_g > W_r  # coding roles are GitHub-heavier

def test_role_weights_no_github_always_resume():
    for role in ["coding", "mixed", "non_technical"]:
        W_r, W_g = get_role_weights(role, False)
        assert W_r == 1.0
        assert W_g == 0.0

def test_strong_candidate_scores_high():
    result = calculate_final_score(
        MOCK_RESUME_STRONG, MOCK_GITHUB_STRONG, SAMPLE_SKILL_GRAPH, True
    )
    assert result["final_score"] >= 0.70
    assert result["resume_weight_applied"] == 0.35
    assert result["github_weight_applied"] == 0.65
    assert len(result["skill_scores"]) == 4  # one per skill in graph

def test_weak_candidate_scores_low():
    result = calculate_final_score(
        MOCK_RESUME_WEAK, {}, SAMPLE_SKILL_GRAPH, False
    )
    assert result["final_score"] < 0.50
    assert result["github_subscore"] == 0.0

def test_no_github_uses_resume_weight_1():
    result = calculate_final_score(
        MOCK_RESUME_STRONG, {}, SAMPLE_SKILL_GRAPH, False
    )
    assert result["resume_weight_applied"] == 1.0
    assert result["github_weight_applied"] == 0.0

def test_evidence_paragraphs_all_non_empty():
    result = calculate_final_score(
        MOCK_RESUME_STRONG, MOCK_GITHUB_STRONG, SAMPLE_SKILL_GRAPH, True
    )
    for skill in result["skill_scores"]:
        assert skill["evidence_paragraph"], f"Empty paragraph for {skill['skill']}"
        assert len(skill["evidence_paragraph"]) > 30

def test_strong_candidate_ranks_above_weak():
    strong = calculate_final_score(MOCK_RESUME_STRONG, MOCK_GITHUB_STRONG, SAMPLE_SKILL_GRAPH, True)
    weak = calculate_final_score(MOCK_RESUME_WEAK, {}, SAMPLE_SKILL_GRAPH, False)
    assert strong["final_score"] > weak["final_score"]

def test_weighted_contributions_sum_to_final():
    result = calculate_final_score(MOCK_RESUME_STRONG, MOCK_GITHUB_STRONG, SAMPLE_SKILL_GRAPH, True)
    total_weight = sum(
        s["jd_weight"]
        for cat in SAMPLE_SKILL_GRAPH["skill_graph"]["categories"]
        for s in cat["skills"]
    )
    contrib_sum = sum(s["weighted_contribution"] for s in result["skill_scores"])
    assert abs(contrib_sum / total_weight - result["final_score"]) < 0.001
