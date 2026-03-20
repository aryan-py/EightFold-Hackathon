import asyncio, json, uuid
from datetime import datetime
from backend.db import (
    init_db, create_run, update_run_status, save_skill_graph,
    create_candidate, update_candidate_score, save_skill_scores,
)

RUN_ID = "demo-run-eightfold-2024"

SKILL_GRAPH = {
    "run_id": RUN_ID,
    "job_title": "Senior ML Engineer",
    "role_type": "coding",
    "search_status": "success",
    "resume_weight": 0.35,
    "github_weight": 0.65,
    "skill_graph": {
        "categories": [
            {"name": "Languages", "skills": [
                {"name": "Python", "aliases": ["py"], "source": "explicit", "required": True, "jd_weight": 1.0,
                 "relationships": []},
                {"name": "SQL", "aliases": [], "source": "inferred", "required": False, "jd_weight": 0.5,
                 "relationships": []}
            ]},
            {"name": "Frameworks", "skills": [
                {"name": "PyTorch", "aliases": ["torch"], "source": "explicit", "required": True, "jd_weight": 0.95,
                 "relationships": [{"type": "requires", "skill": "Python"}]},
                {"name": "FastAPI", "aliases": [], "source": "explicit", "required": False, "jd_weight": 0.7,
                 "relationships": []},
                {"name": "scikit-learn", "aliases": ["sklearn"], "source": "inferred", "required": False, "jd_weight": 0.6,
                 "relationships": [{"type": "complements", "skill": "PyTorch"}]},
            ]},
            {"name": "Tools", "skills": [
                {"name": "Docker", "aliases": [], "source": "inferred", "required": False, "jd_weight": 0.4,
                 "relationships": []},
                {"name": "Git", "aliases": [], "source": "inferred", "required": False, "jd_weight": 0.3,
                 "relationships": []},
            ]},
            {"name": "Domain Knowledge", "skills": [
                {"name": "Machine Learning", "aliases": ["ML"], "source": "explicit", "required": True, "jd_weight": 0.9,
                 "relationships": [{"type": "related_to", "skill": "PyTorch"}]},
                {"name": "System Design", "aliases": [], "source": "inferred", "required": False, "jd_weight": 0.5,
                 "relationships": []},
            ]},
        ]
    }
}

CANDIDATES = [
    {
        "name": "Arjun Mehta",
        "github_url": "https://github.com/arjunm",
        "final_score": 0.91,
        "resume_subscore": 0.88,
        "github_subscore": 0.93,
        "github_provided": True,
        "skill_scores": [
            {"skill": "Python", "jd_weight": 1.0, "resume_confidence": 0.90, "github_confidence": 0.92, "combined_confidence": 0.91, "weighted_contribution": 0.91, "duration_bonus_applied": True,
             "evidence_paragraph": "Resume: 4 years Python at two ML companies, built production ETL pipelines and model serving APIs. Duration bonus applied (48 months). GitHub: ml-experiments repo is 84% Python with 62 commits over 18 months, last active 3 weeks ago. Combined confidence 91% — strong corroborated evidence from both sources."},
            {"skill": "PyTorch", "jd_weight": 0.95, "resume_confidence": 0.82, "github_confidence": 0.88, "combined_confidence": 0.86, "weighted_contribution": 0.82, "duration_bonus_applied": False,
             "evidence_paragraph": "Resume: Describes training and deploying a custom transformer for NLP classification, 2 years usage. GitHub: PyTorch found in requirements.txt across 3 repos; ml-experiments has 4 Jupyter notebooks demonstrating training loops, 38 commits. Combined confidence 86%."},
            {"skill": "FastAPI", "jd_weight": 0.7, "resume_confidence": 0.75, "github_confidence": 0.80, "combined_confidence": 0.78, "weighted_contribution": 0.55, "duration_bonus_applied": False,
             "evidence_paragraph": "Resume: Led backend development of ML inference API using FastAPI and PostgreSQL at fintech startup (Jan 2022–Mar 2024). GitHub: api-service repo has FastAPI in requirements.txt with 28 commits and a Dockerfile, last active 5 months ago. Combined confidence 78%."},
            {"skill": "Machine Learning", "jd_weight": 0.9, "resume_confidence": 0.85, "github_confidence": 0.90, "combined_confidence": 0.88, "weighted_contribution": 0.79, "duration_bonus_applied": True,
             "evidence_paragraph": "Resume: 4 years applied ML experience, mentions model evaluation, hyperparameter tuning, and A/B testing of models in production. GitHub: 5 repos with ML topics, notebooks covering classification, regression, and NLP tasks. Combined confidence 88%."},
            {"skill": "Docker", "jd_weight": 0.4, "resume_confidence": 0.50, "github_confidence": 0.70, "combined_confidence": 0.63, "weighted_contribution": 0.25, "duration_bonus_applied": False,
             "evidence_paragraph": "Resume: Docker mentioned in tools section alongside Kubernetes. GitHub: Dockerfile and docker-compose.yml present in api-service repo, CI workflow references Docker build step. Combined confidence 63%."},
            {"skill": "SQL", "jd_weight": 0.5, "resume_confidence": 0.65, "github_confidence": 0.40, "combined_confidence": 0.49, "weighted_contribution": 0.25, "duration_bonus_applied": False,
             "evidence_paragraph": "Resume: Mentions PostgreSQL and data querying experience in fintech role. GitHub: SQL files found in data-pipeline repo but limited commit depth (8 commits). Combined confidence 49%."},
            {"skill": "scikit-learn", "jd_weight": 0.6, "resume_confidence": 0.70, "github_confidence": 0.65, "combined_confidence": 0.67, "weighted_contribution": 0.40, "duration_bonus_applied": False,
             "evidence_paragraph": "Resume: scikit-learn listed alongside PyTorch in skills section, referenced in a model comparison project. GitHub: present in requirements.txt across 2 repos. Combined confidence 67%."},
            {"skill": "Git", "jd_weight": 0.3, "resume_confidence": 0.60, "github_confidence": 1.0, "combined_confidence": 0.86, "weighted_contribution": 0.26, "duration_bonus_applied": False,
             "evidence_paragraph": "Resume: Git mentioned in tools. GitHub: Extensive commit history across 7 repos demonstrates consistent Git usage over 3+ years. Combined confidence 86%."},
            {"skill": "System Design", "jd_weight": 0.5, "resume_confidence": 0.55, "github_confidence": 0.45, "combined_confidence": 0.49, "weighted_contribution": 0.25, "duration_bonus_applied": False,
             "evidence_paragraph": "Resume: Describes designing a microservices ML platform — moderate evidence of system design thinking. GitHub: architecture.md found in api-service repo. Combined confidence 49%."},
        ],
    },
    {
        "name": "Priya Sharma",
        "github_url": "https://github.com/priya-s",
        "final_score": 0.74,
        "resume_subscore": 0.76,
        "github_subscore": 0.73,
        "github_provided": True,
        "skill_scores": [
            {"skill": "Python", "jd_weight": 1.0, "resume_confidence": 0.80, "github_confidence": 0.75, "combined_confidence": 0.77, "weighted_contribution": 0.77, "duration_bonus_applied": True, "evidence_paragraph": "Resume: 3 years Python at data consultancy, data analysis and automation scripts. GitHub: Python primary language across 5 repos, 38 total commits. Combined confidence 77%."},
            {"skill": "PyTorch", "jd_weight": 0.95, "resume_confidence": 0.60, "github_confidence": 0.65, "combined_confidence": 0.63, "weighted_contribution": 0.60, "duration_bonus_applied": False, "evidence_paragraph": "Resume: PyTorch used in MSc dissertation project on image segmentation. GitHub: found in requirements.txt of thesis-code repo, 14 commits. Combined confidence 63%."},
            {"skill": "FastAPI", "jd_weight": 0.7, "resume_confidence": 0.45, "github_confidence": 0.35, "combined_confidence": 0.39, "weighted_contribution": 0.27, "duration_bonus_applied": False, "evidence_paragraph": "Resume: FastAPI briefly mentioned in personal project description. GitHub: found in one repo README but no dependency file. Moderate confidence — evidence is shallow. Combined confidence 39%."},
            {"skill": "Machine Learning", "jd_weight": 0.9, "resume_confidence": 0.78, "github_confidence": 0.72, "combined_confidence": 0.74, "weighted_contribution": 0.67, "duration_bonus_applied": False, "evidence_paragraph": "Resume: MSc in Machine Learning, internship at ML team. GitHub: Several repos with ML notebooks. Combined confidence 74%."},
            {"skill": "Docker", "jd_weight": 0.4, "resume_confidence": 0.25, "github_confidence": 0.30, "combined_confidence": 0.28, "weighted_contribution": 0.11, "duration_bonus_applied": False, "evidence_paragraph": "Resume: Docker mentioned once in tools list. GitHub: No Dockerfile found in any repo. Weak evidence. Combined confidence 28%."},
            {"skill": "SQL", "jd_weight": 0.5, "resume_confidence": 0.80, "github_confidence": 0.50, "combined_confidence": 0.61, "weighted_contribution": 0.30, "duration_bonus_applied": True, "evidence_paragraph": "Resume: 2 years data analysis role with heavy SQL usage. GitHub: SQL files in data-analysis repo. Combined confidence 61%."},
            {"skill": "scikit-learn", "jd_weight": 0.6, "resume_confidence": 0.72, "github_confidence": 0.68, "combined_confidence": 0.70, "weighted_contribution": 0.42, "duration_bonus_applied": False, "evidence_paragraph": "Resume: scikit-learn used extensively in data consultancy work. GitHub: present in 3 repos. Combined confidence 70%."},
            {"skill": "Git", "jd_weight": 0.3, "resume_confidence": 0.55, "github_confidence": 0.90, "combined_confidence": 0.78, "weighted_contribution": 0.23, "duration_bonus_applied": False, "evidence_paragraph": "Resume: Git in tools. GitHub: consistent commit history. Combined confidence 78%."},
            {"skill": "System Design", "jd_weight": 0.5, "resume_confidence": 0.30, "github_confidence": 0.20, "combined_confidence": 0.24, "weighted_contribution": 0.12, "duration_bonus_applied": False, "evidence_paragraph": "Resume: Limited system design evidence — mainly data analysis background. GitHub: No architecture documentation found. Weak signal. Combined confidence 24%."},
        ],
    },
    {
        "name": "Vikram Nair",
        "github_url": None,
        "final_score": 0.62,
        "resume_subscore": 0.62,
        "github_subscore": 0.0,
        "github_provided": False,
        "skill_scores": [
            {"skill": "Python", "jd_weight": 1.0, "resume_confidence": 0.75, "github_confidence": 0.0, "combined_confidence": 0.75, "weighted_contribution": 0.75, "duration_bonus_applied": True, "evidence_paragraph": "Resume: 3 years Python across backend and ML projects. Duration bonus applied (36 months). GitHub was not provided — score reflects resume evidence only and may underestimate practical coding ability. Combined confidence 75%."},
            {"skill": "PyTorch", "jd_weight": 0.95, "resume_confidence": 0.55, "github_confidence": 0.0, "combined_confidence": 0.55, "weighted_contribution": 0.52, "duration_bonus_applied": False, "evidence_paragraph": "Resume: PyTorch listed in skills section with one project reference. No further context. GitHub was not provided. Combined confidence 55% — resume-only signal is moderate."},
            {"skill": "FastAPI", "jd_weight": 0.7, "resume_confidence": 0.70, "github_confidence": 0.0, "combined_confidence": 0.70, "weighted_contribution": 0.49, "duration_bonus_applied": False, "evidence_paragraph": "Resume: Built REST APIs with FastAPI for an internal tool at current employer. GitHub was not provided. Combined confidence 70%."},
            {"skill": "Machine Learning", "jd_weight": 0.9, "resume_confidence": 0.60, "github_confidence": 0.0, "combined_confidence": 0.60, "weighted_contribution": 0.54, "duration_bonus_applied": False, "evidence_paragraph": "Resume: ML mentioned in job titles and project descriptions. GitHub was not provided. Combined confidence 60%."},
            {"skill": "Docker", "jd_weight": 0.4, "resume_confidence": 0.40, "github_confidence": 0.0, "combined_confidence": 0.40, "weighted_contribution": 0.16, "duration_bonus_applied": False, "evidence_paragraph": "Resume: Docker listed in tools section. GitHub was not provided. Combined confidence 40%."},
            {"skill": "SQL", "jd_weight": 0.5, "resume_confidence": 0.65, "github_confidence": 0.0, "combined_confidence": 0.65, "weighted_contribution": 0.33, "duration_bonus_applied": False, "evidence_paragraph": "Resume: SQL experience at data-heavy role. GitHub not provided. Combined confidence 65%."},
            {"skill": "scikit-learn", "jd_weight": 0.6, "resume_confidence": 0.45, "github_confidence": 0.0, "combined_confidence": 0.45, "weighted_contribution": 0.27, "duration_bonus_applied": False, "evidence_paragraph": "Resume: scikit-learn in skills list, no project context. GitHub not provided. Combined confidence 45%."},
            {"skill": "Git", "jd_weight": 0.3, "resume_confidence": 0.55, "github_confidence": 0.0, "combined_confidence": 0.55, "weighted_contribution": 0.17, "duration_bonus_applied": False, "evidence_paragraph": "Resume: Git in tools. GitHub not provided. Combined confidence 55%."},
            {"skill": "System Design", "jd_weight": 0.5, "resume_confidence": 0.50, "github_confidence": 0.0, "combined_confidence": 0.50, "weighted_contribution": 0.25, "duration_bonus_applied": False, "evidence_paragraph": "Resume: Mentions designing a microservices architecture. GitHub not provided. Combined confidence 50%."},
        ],
    },
    {
        "name": "Sneha Patel",
        "github_url": "https://github.com/snehap",
        "final_score": 0.38,
        "resume_subscore": 0.35,
        "github_subscore": 0.40,
        "github_provided": True,
        "skill_scores": [
            {"skill": "Python", "jd_weight": 1.0, "resume_confidence": 0.40, "github_confidence": 0.45, "combined_confidence": 0.43, "weighted_contribution": 0.43, "duration_bonus_applied": False, "evidence_paragraph": "Resume: Python listed in skills with no experience duration or project context. GitHub: 2 Python repos with fewer than 10 commits each — exploratory rather than production work. Combined confidence 43% — shallow evidence from both sources."},
            {"skill": "PyTorch", "jd_weight": 0.95, "resume_confidence": 0.15, "github_confidence": 0.20, "combined_confidence": 0.18, "weighted_contribution": 0.17, "duration_bonus_applied": False, "evidence_paragraph": "Resume: PyTorch mentioned in objective statement only — no project or usage context. GitHub: one unfinished tutorial notebook in a repo with 2 commits. Combined confidence 18% — very weak signal from both sources."},
            {"skill": "FastAPI", "jd_weight": 0.7, "resume_confidence": 0.0, "github_confidence": 0.0, "combined_confidence": 0.0, "weighted_contribution": 0.0, "duration_bonus_applied": False, "evidence_paragraph": "No FastAPI evidence found in resume. No FastAPI evidence found in GitHub profile. Score is 0.0."},
            {"skill": "Machine Learning", "jd_weight": 0.9, "resume_confidence": 0.30, "github_confidence": 0.35, "combined_confidence": 0.33, "weighted_contribution": 0.30, "duration_bonus_applied": False, "evidence_paragraph": "Resume: One ML course mentioned under education. GitHub: A Kaggle competition notebook found but with minimal commits. Combined confidence 33%."},
            {"skill": "Docker", "jd_weight": 0.4, "resume_confidence": 0.0, "github_confidence": 0.0, "combined_confidence": 0.0, "weighted_contribution": 0.0, "duration_bonus_applied": False, "evidence_paragraph": "No Docker evidence found in resume or GitHub profile. Score is 0.0."},
            {"skill": "SQL", "jd_weight": 0.5, "resume_confidence": 0.55, "github_confidence": 0.30, "combined_confidence": 0.39, "weighted_contribution": 0.19, "duration_bonus_applied": False, "evidence_paragraph": "Resume: SQL mentioned in a data analysis internship. GitHub: one SQL file found. Combined confidence 39%."},
            {"skill": "scikit-learn", "jd_weight": 0.6, "resume_confidence": 0.20, "github_confidence": 0.15, "combined_confidence": 0.17, "weighted_contribution": 0.10, "duration_bonus_applied": False, "evidence_paragraph": "Resume: scikit-learn in skills list, no project reference. GitHub: found in one requirements.txt but repo has 3 commits. Combined confidence 17%."},
            {"skill": "Git", "jd_weight": 0.3, "resume_confidence": 0.40, "github_confidence": 0.50, "combined_confidence": 0.47, "weighted_contribution": 0.14, "duration_bonus_applied": False, "evidence_paragraph": "Resume: Git in tools. GitHub: some activity but sparse. Combined confidence 47%."},
            {"skill": "System Design", "jd_weight": 0.5, "resume_confidence": 0.10, "github_confidence": 0.0, "combined_confidence": 0.04, "weighted_contribution": 0.02, "duration_bonus_applied": False, "evidence_paragraph": "Resume: No system design evidence — recent graduate with limited work experience. GitHub: No architecture documentation. Combined confidence 4%."},
        ],
    },
]

async def seed():
    await init_db()
    await create_run(RUN_ID, "Senior ML Engineer", "Senior ML Engineer at a fintech startup. Required: Python, PyTorch, FastAPI. Nice to have: Docker, SQL.")
    await update_run_status(RUN_ID, "complete", role_type="coding", resume_weight=0.35, github_weight=0.65)
    await save_skill_graph(RUN_ID, SKILL_GRAPH, "success")
    print(f"Created run: {RUN_ID}")

    for i, c in enumerate(CANDIDATES):
        cid = f"demo-candidate-{i+1:03d}"
        await create_candidate(cid, RUN_ID, c["name"], "pdf", "", c.get("github_url"))
        await update_candidate_score(cid, {
            "final_score": c["final_score"],
            "resume_subscore": c["resume_subscore"],
            "github_subscore": c["github_subscore"],
            "data_gaps": [] if c["github_provided"] else ["github_not_provided"],
        })
        await save_skill_scores(cid, RUN_ID, c["skill_scores"])
        print(f"  Seeded: {c['name']} — score {c['final_score']}")

    print(f"\nDemo data ready. Visit: /run/{RUN_ID}/results")

if __name__ == "__main__":
    asyncio.run(seed())
