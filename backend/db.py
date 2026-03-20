from pathlib import Path
from typing import Any
import aiosqlite
import json
import os
import uuid
from datetime import datetime

DB_PATH = Path(os.getenv("DB_PATH", "backend/talent.db"))


async def init_db() -> None:
    """Create all tables on startup. Safe to call multiple times."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS runs (
                run_id      TEXT PRIMARY KEY,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                job_title   TEXT NOT NULL,
                jd_text     TEXT NOT NULL,
                role_type   TEXT,
                resume_weight REAL,
                github_weight REAL,
                status      TEXT DEFAULT 'pending'
            );

            CREATE TABLE IF NOT EXISTS skill_graphs (
                run_id       TEXT PRIMARY KEY,
                graph_json   TEXT NOT NULL,
                search_status TEXT,
                created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (run_id) REFERENCES runs(run_id)
            );

            CREATE TABLE IF NOT EXISTS candidates (
                candidate_id   TEXT PRIMARY KEY,
                run_id         TEXT NOT NULL,
                name           TEXT,
                resume_format  TEXT,
                resume_content TEXT,
                github_url     TEXT,
                github_provided BOOLEAN DEFAULT FALSE,
                final_score    REAL DEFAULT 0.0,
                resume_subscore REAL DEFAULT 0.0,
                github_subscore REAL DEFAULT 0.0,
                status         TEXT DEFAULT 'pending',
                data_gaps      TEXT DEFAULT '[]',
                created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (run_id) REFERENCES runs(run_id)
            );

            CREATE TABLE IF NOT EXISTS skill_scores (
                id                    TEXT PRIMARY KEY,
                candidate_id          TEXT NOT NULL,
                run_id                TEXT NOT NULL,
                skill                 TEXT NOT NULL,
                jd_weight             REAL,
                resume_confidence     REAL DEFAULT 0.0,
                github_confidence     REAL DEFAULT 0.0,
                combined_confidence   REAL DEFAULT 0.0,
                weighted_contribution REAL DEFAULT 0.0,
                evidence_paragraph    TEXT,
                duration_bonus_applied BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (candidate_id) REFERENCES candidates(candidate_id)
            );

            CREATE TABLE IF NOT EXISTS bias_checks (
                check_id        TEXT PRIMARY KEY,
                candidate_id    TEXT NOT NULL,
                run_id          TEXT NOT NULL,
                score_original  REAL NOT NULL,
                score_masked    REAL NOT NULL,
                delta           REAL NOT NULL,
                is_biased       BOOLEAN NOT NULL,
                masked_fields   TEXT NOT NULL DEFAULT '[]',
                checked_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (candidate_id) REFERENCES candidates(candidate_id)
            );

            CREATE TABLE IF NOT EXISTS adjacency_results (
                result_id               TEXT PRIMARY KEY,
                candidate_id            TEXT NOT NULL,
                run_id                  TEXT NOT NULL,
                missing_skill           TEXT NOT NULL,
                bridge_skill            TEXT,
                bridge_skill_confidence REAL,
                relationship_type       TEXT,
                ttp_weeks_low           INTEGER,
                ttp_weeks_high          INTEGER,
                learning_path           TEXT NOT NULL DEFAULT '[]',
                rationale               TEXT,
                created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (candidate_id) REFERENCES candidates(candidate_id)
            );

            CREATE INDEX IF NOT EXISTS idx_candidates_run
                ON candidates(run_id);
            CREATE INDEX IF NOT EXISTS idx_skill_scores_candidate
                ON skill_scores(candidate_id);
            CREATE INDEX IF NOT EXISTS idx_bias_candidate
                ON bias_checks(candidate_id);
            CREATE INDEX IF NOT EXISTS idx_adjacency_candidate
                ON adjacency_results(candidate_id);
        """)
        # Migration: add resume_content column if missing (existing DBs)
        try:
            await db.execute("ALTER TABLE candidates ADD COLUMN resume_content TEXT")
            await db.commit()
        except Exception:
            pass  # Column already exists

        # Migration: recreate bias_checks if it has old JSON-blob schema
        try:
            await db.execute("SELECT check_id FROM bias_checks LIMIT 1")
        except Exception:
            await db.execute("DROP TABLE IF EXISTS bias_checks")
            await db.execute("""
                CREATE TABLE bias_checks (
                    check_id        TEXT PRIMARY KEY,
                    candidate_id    TEXT NOT NULL,
                    run_id          TEXT NOT NULL,
                    score_original  REAL NOT NULL,
                    score_masked    REAL NOT NULL,
                    delta           REAL NOT NULL,
                    is_biased       BOOLEAN NOT NULL,
                    masked_fields   TEXT NOT NULL DEFAULT '[]',
                    checked_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (candidate_id) REFERENCES candidates(candidate_id)
                )
            """)
            await db.commit()

        # Migration: recreate adjacency_results if it has old JSON-blob schema
        try:
            await db.execute("SELECT result_id FROM adjacency_results LIMIT 1")
        except Exception:
            await db.execute("DROP TABLE IF EXISTS adjacency_results")
            await db.execute("""
                CREATE TABLE adjacency_results (
                    result_id               TEXT PRIMARY KEY,
                    candidate_id            TEXT NOT NULL,
                    run_id                  TEXT NOT NULL,
                    missing_skill           TEXT NOT NULL,
                    bridge_skill            TEXT,
                    bridge_skill_confidence REAL,
                    relationship_type       TEXT,
                    ttp_weeks_low           INTEGER,
                    ttp_weeks_high          INTEGER,
                    learning_path           TEXT NOT NULL DEFAULT '[]',
                    rationale               TEXT,
                    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (candidate_id) REFERENCES candidates(candidate_id)
                )
            """)
            await db.commit()

        await db.commit()


async def create_run(run_id: str, job_title: str, jd_text: str) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            "INSERT INTO runs (run_id, job_title, jd_text) VALUES (?, ?, ?)",
            (run_id, job_title, jd_text)
        )
        await db.commit()
        async with db.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)) as cur:
            row = await cur.fetchone()
            return dict(row)


async def update_run_status(
    run_id: str,
    status: str,
    role_type: str | None = None,
    resume_weight: float | None = None,
    github_weight: float | None = None,
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        if role_type is not None:
            await db.execute(
                """UPDATE runs SET status=?, role_type=?,
                   resume_weight=?, github_weight=? WHERE run_id=?""",
                (status, role_type, resume_weight, github_weight, run_id)
            )
        else:
            await db.execute(
                "UPDATE runs SET status=? WHERE run_id=?",
                (status, run_id)
            )
        await db.commit()


async def save_skill_graph(
    run_id: str,
    graph: dict,
    search_status: str = "success",
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT OR REPLACE INTO skill_graphs
               (run_id, graph_json, search_status) VALUES (?, ?, ?)""",
            (run_id, json.dumps(graph), search_status)
        )
        await db.commit()


async def get_skill_graph(run_id: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT graph_json FROM skill_graphs WHERE run_id = ?", (run_id,)
        ) as cur:
            row = await cur.fetchone()
            return json.loads(row["graph_json"]) if row else None


async def create_candidate(
    candidate_id: str,
    run_id: str,
    name: str | None,
    resume_format: str,
    resume_content: str,
    github_url: str | None,
) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            """INSERT INTO candidates
               (candidate_id, run_id, name, resume_format, resume_content, github_url, github_provided)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                candidate_id, run_id, name, resume_format,
                resume_content,
                github_url,
                github_url is not None and github_url.strip() != "",
            )
        )
        await db.commit()
        async with db.execute(
            "SELECT * FROM candidates WHERE candidate_id = ?", (candidate_id,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row)


async def update_candidate_score(candidate_id: str, score_data: dict) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """UPDATE candidates SET
               final_score=?, resume_subscore=?, github_subscore=?,
               status=?, data_gaps=?
               WHERE candidate_id=?""",
            (
                score_data.get("final_score", 0.0),
                score_data.get("resume_subscore", 0.0),
                score_data.get("github_subscore", 0.0),
                "complete",
                json.dumps(score_data.get("data_gaps", [])),
                candidate_id,
            )
        )
        await db.commit()


async def save_skill_scores(
    candidate_id: str,
    run_id: str,
    skill_scores: list[dict],
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        for s in skill_scores:
            await db.execute(
                """INSERT OR REPLACE INTO skill_scores
                   (id, candidate_id, run_id, skill, jd_weight,
                    resume_confidence, github_confidence,
                    combined_confidence, weighted_contribution,
                    evidence_paragraph, duration_bonus_applied)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    str(uuid.uuid4()), candidate_id, run_id,
                    s["skill"], s["jd_weight"],
                    s.get("resume_confidence", 0.0),
                    s.get("github_confidence", 0.0),
                    s.get("combined_confidence", 0.0),
                    s.get("weighted_contribution", 0.0),
                    s.get("evidence_paragraph", ""),
                    s.get("duration_bonus_applied", False),
                )
            )
        await db.commit()


async def get_run_results(run_id: str) -> list[dict]:
    """Returns all candidates for a run with skill scores, sorted by final_score desc."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM candidates WHERE run_id = ? ORDER BY final_score DESC",
            (run_id,)
        ) as cur:
            candidates = [dict(r) for r in await cur.fetchall()]

        for c in candidates:
            async with db.execute(
                "SELECT * FROM skill_scores WHERE candidate_id = ?",
                (c["candidate_id"],)
            ) as cur:
                c["skill_scores"] = [dict(r) for r in await cur.fetchall()]
            c["data_gaps"] = json.loads(c.get("data_gaps", "[]"))

        return candidates


async def save_bias_check(
    check_id: str,
    candidate_id: str,
    run_id: str,
    score_original: float,
    score_masked: float,
    masked_fields: list[str],
) -> dict:
    delta = abs(score_original - score_masked)
    is_biased = delta > 0.005
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            """INSERT OR REPLACE INTO bias_checks
               (check_id, candidate_id, run_id, score_original, score_masked,
                delta, is_biased, masked_fields)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (check_id, candidate_id, run_id, score_original, score_masked,
             delta, is_biased, json.dumps(masked_fields))
        )
        await db.commit()
        async with db.execute(
            "SELECT * FROM bias_checks WHERE check_id = ?", (check_id,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row)


async def get_bias_check(candidate_id: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM bias_checks WHERE candidate_id = ? ORDER BY checked_at DESC LIMIT 1",
            (candidate_id,)
        ) as cur:
            row = await cur.fetchone()
            if not row:
                return None
            result = dict(row)
            result["masked_fields"] = json.loads(result.get("masked_fields", "[]"))
            return result


async def save_adjacency_results(results: list[dict]) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        for r in results:
            await db.execute(
                """INSERT OR REPLACE INTO adjacency_results
                   (result_id, candidate_id, run_id, missing_skill, bridge_skill,
                    bridge_skill_confidence, relationship_type,
                    ttp_weeks_low, ttp_weeks_high, learning_path, rationale)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    r["result_id"], r["candidate_id"], r["run_id"],
                    r["missing_skill"], r.get("bridge_skill"),
                    r.get("bridge_skill_confidence", 0.0),
                    r.get("relationship_type"),
                    r.get("ttp_weeks_low"), r.get("ttp_weeks_high"),
                    json.dumps(r.get("learning_path", [])),
                    r.get("rationale"),
                )
            )
        await db.commit()


async def get_adjacency_results(candidate_id: str) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT * FROM adjacency_results
               WHERE candidate_id = ? ORDER BY ttp_weeks_low ASC""",
            (candidate_id,)
        ) as cur:
            rows = await cur.fetchall()
            results = []
            for row in rows:
                r = dict(row)
                r["learning_path"] = json.loads(r.get("learning_path", "[]"))
                results.append(r)
            return results
