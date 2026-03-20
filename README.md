# EightFold AI — Talent Discovery Platform

> AI-powered candidate ranking that goes beyond the resume. Built for the Eightfold AI Hackathon.

---

## What it does

Paste a job description. The system spins up a multi-agent AI pipeline that:

1. **Builds a skill graph** from the JD + live web search
2. **Parses every resume** — PDF or plain text — extracting evidence per skill
3. **Analyses each GitHub profile** — repos, commit history, languages, quality signals
4. **Scores and ranks candidates** with weighted, evidence-backed confidence scores
5. **Runs a bias check** — masks demographic signals, re-scores, and reports the delta
6. **Maps skill adjacency** — for every gap, finds the closest bridge skill the candidate already has and estimates time-to-proficiency

Results stream to the UI in real time as each candidate is processed.

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + TypeScript, Vite, Framer Motion, Zustand, React Router v7 |
| Backend | Python 3.12, FastAPI, Server-Sent Events (SSE) |
| AI agents | CrewAI 1.x, OpenAI `gpt-4o-mini` |
| Database | SQLite via `aiosqlite` |
| Graph viz | `react-force-graph-2d` |

---

## Project structure

```
├── backend/
│   ├── main.py               # FastAPI app, SSE stream, all API routes
│   ├── db.py                 # aiosqlite schema + CRUD helpers
│   ├── scoring.py            # Deterministic scoring formula (no LLM)
│   ├── bias.py               # Demographic masking + bias delta check
│   ├── adjacency.py          # Skill gap → bridge skill → TTP estimation
│   ├── crew/
│   │   ├── agents.py         # CrewAI agent definitions (4 agents)
│   │   ├── tasks.py          # Task prompts passed to each agent
│   │   └── crew.py           # Orchestration: parallel Agents 2+3, then Agent 4
│   ├── tools/
│   │   ├── resume_tool.py    # PDF/text resume parser tool
│   │   └── github_tool.py    # GitHub API crawler tool
│   ├── agent_skills/         # Backstory / identity files for each agent
│   └── tests/                # pytest suite (43 tests)
│
├── frontend/
│   ├── src/
│   │   ├── pages/            # HomePage, CandidatesPage, ResultsPage
│   │   ├── components/       # CandidateCard, SkillGraphView, BiasCheckBadge,
│   │   │                     #   AdjacencyPanel, GapCard, Toast, ...
│   │   ├── hooks/            # useSSE, useScoreCounter
│   │   ├── lib/api.ts        # All fetch calls to the backend
│   │   ├── store/store.ts    # Zustand global state
│   │   └── types.ts          # Shared TypeScript interfaces
│   └── package.json
│
└── README.md
```

---

## Prerequisites

- Python 3.12+
- Node.js 18+
- An **OpenAI API key** (gpt-4o-mini)
- *(Optional)* A **Serper API key** for web search in Agent 1
- *(Optional)* A **GitHub personal access token** for higher GitHub API rate limits

---

## Setup & run

### 1. Clone the repo

```bash
git clone git@github.com:aryan-py/EightFold-Hackathon.git
cd EightFold-Hackathon
```

### 2. Backend

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install dependencies
pip install -e backend/

# Create the .env file
cp backend/.env backend/.env   # then fill in your keys
```

Edit `backend/.env`:

```env
OPENAI_API_KEY=sk-...
SERPER_API_KEY=...        # optional — Agent 1 falls back gracefully without it
GITHUB_TOKEN=ghp_...      # optional — raises GitHub API rate limit from 60 to 5000 req/hr
```

Start the API:

```bash
python -m uvicorn backend.main:app --reload --port 8000
```

Backend runs at **http://localhost:8000**. Swagger docs at **http://localhost:8000/docs**.

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at **http://localhost:5173**.

---

## Running tests

```bash
source .venv/bin/activate
python -m pytest backend/tests/ -v
```

43 tests covering: DB init, scoring formula, bias masking, skill adjacency, integration.

---

## How it works — core concepts

### Agent pipeline

```
JD text
  │
  ▼
Agent 1 — Skill Graph Builder
  Uses Serper web search to find role-specific skills.
  Outputs a categorised skill graph with JD weights (0.0–1.0)
  and relationship edges (requires / complements / related_to).
  │
  ├──────────────────────┐
  ▼                      ▼
Agent 2                Agent 3          ← run in PARALLEL
Resume Parser          GitHub Analyser
  Extracts confidence    Fetches up to 20 repos via GitHub API.
  scores per skill       Scores each skill by: language bytes,
  from PDF/text.         README mentions, commit count, recency,
                         quality signals (tests, CI, Docker).
  │                      │
  └──────────┬───────────┘
             ▼
          Agent 4 — Scorer
            Writes recruiter-readable evidence paragraphs.
            Scoring.py computes the actual numbers deterministically.
```

### Scoring formula

```
W_r, W_g  = role weights  (coding: 0.35/0.65 | mixed: 0.55/0.45 | non-technical: 1.0/0.0)
            overridden to 1.0/0.0 when no GitHub is provided

combined[i]  = resume_confidence[i] × W_r  +  github_confidence[i] × W_g
final_score  = Σ( combined[i] × jd_weight[i] )  /  Σ( jd_weight[i] )
```

Duration bonuses are applied to `resume_confidence` before combining:
- ≥ 48 months experience → +0.08
- 24–47 months → +0.05
- 12–23 months → +0.02

### Bias check

When triggered, the resume text is passed through a regex masker that removes:
- Full names and titles (Mr/Ms/Dr + two-word names)
- Pronouns (he/she/they and variants)
- Date of birth, age, graduation year
- University names
- Nationality indicators

The masked text is re-scored. If the delta between original and masked score exceeds **0.5%**, the candidate is flagged.

### Skill adjacency & time-to-proficiency

For each skill gap (combined confidence < 40%), the system:
1. Checks a static TTP table of 35+ skill-pair relationships
2. Checks relationships in the Agent 1 skill graph
3. Finds the candidate's strongest "bridge skill" that transfers to the gap
4. Scores bridge routes by: `bridge_confidence × relationship_weight`
5. Returns estimated weeks-to-proficiency (low/high range) and a 5-step learning path

---

## API reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/run` | Submit JD, build skill graph, return run_id |
| `POST` | `/api/run/{run_id}/candidates` | Upload candidate resumes + GitHub URLs |
| `GET`  | `/api/run/{run_id}/stream` | SSE stream — emits scored candidates as they complete |
| `GET`  | `/api/run/{run_id}/results` | Fetch all results (for page refresh) |
| `POST` | `/api/run/{run_id}/candidates/{id}/bias-check` | Run bias check for a candidate |
| `GET`  | `/api/run/{run_id}/candidates/{id}/adjacency` | Get skill gap + TTP analysis |

---

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | ✅ Yes | Used by all 4 agents |
| `SERPER_API_KEY` | Optional | Web search in Agent 1 (falls back to JD-only analysis) |
| `GITHUB_TOKEN` | Optional | GitHub personal access token — raises rate limit to 5,000 req/hr |
