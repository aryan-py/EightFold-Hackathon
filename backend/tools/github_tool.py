from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from pathlib import Path
from typing import Any
import httpx
import json
import logging
import os
import re
import asyncio

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

DEPENDENCY_FILES = {
    "requirements.txt": "python",
    "pyproject.toml": "python",
    "Pipfile": "python",
    "package.json": "javascript",
    "pom.xml": "java",
    "build.gradle": "java",
    "go.mod": "go",
    "Cargo.toml": "rust",
    "Gemfile": "ruby",
}

QUALITY_INDICATORS = [
    (r'readme', "has_readme"),
    (r'tests?/|__tests__|_test\.|\.test\.', "has_tests"),
    (r'\.github/workflows|\.circleci|\.travis', "has_ci"),
    (r'dockerfile|docker-compose', "has_docker"),
    (r'^docs?/', "has_docs"),
]

class GitHubAnalyserInput(BaseModel):
    github_url: str = Field(description="GitHub profile or repo URL")
    skill_graph: str = Field(description="JSON string of the skill graph from Agent 1")
    candidate_id: str = Field(description="Candidate identifier")

class GitHubAnalyserTool(BaseTool):
    name: str = "github_analyser"
    description: str = (
        "Analyse a candidate's GitHub profile and extract evidence for each "
        "skill in the provided skill graph. Returns structured JSON matching "
        "the agent3 output contract."
    )
    args_schema: type[BaseModel] = GitHubAnalyserInput

    def _run(self, github_url: str, skill_graph: str, candidate_id: str) -> str:
        try:
            return asyncio.run(self._async_run(github_url, skill_graph, candidate_id))
        except RuntimeError:
            loop = asyncio.new_event_loop()
            result = loop.run_until_complete(
                self._async_run(github_url, skill_graph, candidate_id)
            )
            loop.close()
            return result

    async def _async_run(self, github_url: str, skill_graph: str,
                          candidate_id: str) -> str:
        graph = json.loads(skill_graph) if isinstance(skill_graph, str) else skill_graph
        skills = self._extract_skills(graph)
        username = self._extract_username(github_url)

        if not username:
            return json.dumps(self._empty_result(
                candidate_id, skills, "unavailable", github_url
            ))

        async with httpx.AsyncClient(headers=HEADERS, timeout=30) as client:
            repos, status = await self._fetch_repos(client, username)
            if status != "success":
                return json.dumps(self._empty_result(
                    candidate_id, skills, status, github_url
                ))

            pinned = await self._get_pinned_repos(client, username)
            analysed = await self._analyse_repos(client, username, repos, pinned)

        evidence = self._match_skills(skills, analysed, pinned)
        return json.dumps({
            "candidate_id": candidate_id,
            "parse_status": "success",
            "source": "github",
            "github_username": username,
            "repos_analysed": len(analysed),
            "repos_skipped_unmodified_forks": sum(
                1 for r in repos if r.get("fork") and r.get("_skip", False)
            ),
            "skill_evidence": evidence,
        })

    def _extract_username(self, url: str) -> str | None:
        patterns = [
            r'github\.com/([a-zA-Z0-9_-]+)',
            r'^([a-zA-Z0-9_-]+)$',
        ]
        for pat in patterns:
            m = re.search(pat, url.strip())
            if m:
                return m.group(1)
        return None

    async def _fetch_repos(self, client: httpx.AsyncClient,
                            username: str) -> tuple[list, str]:
        try:
            resp = await client.get(
                f"{GITHUB_API}/users/{username}/repos",
                params={"per_page": 100, "type": "all", "sort": "updated"}
            )
            if resp.status_code == 404:
                return [], "unavailable"
            if resp.status_code == 403:
                return [], "rate_limited"
            resp.raise_for_status()
            return resp.json(), "success"
        except httpx.HTTPError as e:
            logger.error(f"GitHub fetch error: {e}")
            return [], "unavailable"

    async def _get_pinned_repos(self, client: httpx.AsyncClient,
                                  username: str) -> set[str]:
        """Get pinned repo names via GraphQL."""
        try:
            query = """
            query($login: String!) {
              user(login: $login) {
                pinnedItems(first: 6, types: REPOSITORY) {
                  nodes { ... on Repository { name } }
                }
              }
            }"""
            resp = await client.post(
                "https://api.github.com/graphql",
                json={"query": query, "variables": {"login": username}},
            )
            if resp.status_code == 200:
                data = resp.json()
                nodes = (data.get("data", {}).get("user", {})
                         .get("pinnedItems", {}).get("nodes", []))
                return {n["name"] for n in nodes if n}
        except Exception:
            pass
        return set()

    async def _analyse_repos(self, client: httpx.AsyncClient,
                              username: str, repos: list,
                              pinned: set[str]) -> list[dict]:
        """Prioritise and analyse up to 20 repos."""
        def priority(r: dict) -> int:
            if r["name"] in pinned:
                return 0
            if not r.get("fork"):
                return 1 if r.get("stargazers_count", 0) > 0 else 2
            return 3  # forks last

        sorted_repos = sorted(repos, key=priority)[:20]
        results = []

        for repo in sorted_repos:
            owner = repo.get("owner", {}).get("login", username)
            name = repo["name"]
            is_fork = repo.get("fork", False)

            if is_fork:
                has_commits = await self._fork_has_commits(client, owner, name, username)
                if not has_commits:
                    repo["_skip"] = True
                    continue

            data = await self._get_repo_signals(client, owner, name, username)
            data["is_fork"] = is_fork
            data["is_pinned"] = name in pinned
            data["name"] = name
            data["stars"] = repo.get("stargazers_count", 0)
            data["description"] = repo.get("description", "") or ""
            data["topics"] = repo.get("topics", [])
            data["primary_language"] = repo.get("language", "") or ""
            results.append(data)

        return results

    async def _fork_has_commits(self, client: httpx.AsyncClient,
                                  owner: str, repo: str,
                                  username: str) -> bool:
        try:
            resp = await client.get(
                f"{GITHUB_API}/repos/{owner}/{repo}/commits",
                params={"author": username, "per_page": 1}
            )
            return resp.status_code == 200 and len(resp.json()) > 0
        except Exception:
            return False

    async def _get_repo_signals(self, client: httpx.AsyncClient,
                                  owner: str, repo: str,
                                  username: str) -> dict:
        signals: dict = {
            "languages": {},
            "dependencies": [],
            "readme_text": "",
            "commit_count": 0,
            "active_weeks": 0,
            "last_commit_days_ago": 999,
            "quality_score": 0,
            "file_tree": [],
        }

        # Languages
        try:
            r = await client.get(f"{GITHUB_API}/repos/{owner}/{repo}/languages")
            if r.status_code == 200:
                signals["languages"] = r.json()
        except Exception:
            pass

        # README
        try:
            r = await client.get(f"{GITHUB_API}/repos/{owner}/{repo}/readme",
                                  headers={**HEADERS, "Accept": "application/vnd.github.raw"})
            if r.status_code == 200:
                signals["readme_text"] = r.text[:3000]
        except Exception:
            pass

        # Commit activity
        try:
            r = await client.get(
                f"{GITHUB_API}/repos/{owner}/{repo}/commits",
                params={"author": username, "per_page": 100}
            )
            if r.status_code == 200:
                commits = r.json()
                signals["commit_count"] = len(commits)
                if commits:
                    from datetime import datetime, timezone
                    last_date_str = commits[0].get("commit", {}).get(
                        "committer", {}).get("date", "")
                    if last_date_str:
                        last_dt = datetime.fromisoformat(
                            last_date_str.replace("Z", "+00:00")
                        )
                        delta = datetime.now(timezone.utc) - last_dt
                        signals["last_commit_days_ago"] = delta.days
        except Exception:
            pass

        # File tree (top level)
        try:
            r = await client.get(
                f"{GITHUB_API}/repos/{owner}/{repo}/git/trees/HEAD",
                params={"recursive": "0"}
            )
            if r.status_code == 200:
                tree = r.json().get("tree", [])
                signals["file_tree"] = [f["path"] for f in tree]
        except Exception:
            pass

        # Quality score
        tree_str = " ".join(signals["file_tree"]).lower()
        readme_str = signals["readme_text"].lower()
        q = 0
        if signals["readme_text"] and len(signals["readme_text"]) > 200:
            q += 1
        if re.search(r'tests?/|__tests__|_test\.|\.test\.', tree_str):
            q += 1
        if re.search(r'\.github/workflows|\.circleci|\.travis', tree_str):
            q += 1
        if re.search(r'dockerfile|docker-compose', tree_str + readme_str):
            q += 1
        if re.search(r'^docs?/', tree_str):
            q += 1
        signals["quality_score"] = q

        return signals

    def _match_skills(self, skills: list[dict], repos: list[dict],
                       pinned: set[str]) -> list[dict]:
        evidence_list = []
        for skill in skills:
            names = [skill["name"]] + skill.get("aliases", [])
            best: dict = {
                "skill": skill["name"],
                "confidence": 0.0,
                "evidence": "no signal found",
                "primary_repo": None,
                "commit_count": None,
                "recency": "unknown",
                "quality_score": None,
                "is_pinned_repo": False,
                "is_fork": False,
                "match_type": "none",
            }

            for repo in repos:
                conf, match_type, evidence_str = self._score_skill_in_repo(
                    skill, names, repo
                )
                if conf > best["confidence"]:
                    recency = self._recency_label(repo.get("last_commit_days_ago", 999))
                    is_fork = repo.get("is_fork", False)
                    if is_fork:
                        conf = min(0.70, conf)

                    # Apply modifiers
                    if repo["name"] in pinned:
                        conf = min(1.0, conf + 0.10)
                    if repo.get("last_commit_days_ago", 999) <= 90:
                        conf = min(1.0, conf + 0.05)
                    elif repo.get("last_commit_days_ago", 999) > 730:
                        conf = max(0.0, conf - 0.10)

                    best = {
                        "skill": skill["name"],
                        "confidence": round(conf, 4),
                        "evidence": evidence_str,
                        "primary_repo": repo["name"],
                        "commit_count": repo.get("commit_count"),
                        "recency": recency,
                        "quality_score": repo.get("quality_score"),
                        "is_pinned_repo": repo["name"] in pinned,
                        "is_fork": is_fork,
                        "match_type": match_type,
                    }

            evidence_list.append(best)
        return evidence_list

    def _score_skill_in_repo(self, skill: dict, names: list[str],
                               repo: dict) -> tuple[float, str, str]:
        name_lower = [n.lower() for n in names]
        skill_name = skill["name"]
        commits = repo.get("commit_count", 0)

        # Language match
        languages = repo.get("languages", {})
        total_bytes = sum(languages.values()) or 1
        for lang, bytes_count in languages.items():
            if any(n in lang.lower() or lang.lower() in n for n in name_lower):
                pct = bytes_count / total_bytes
                if pct >= 0.20:
                    base = 0.72 if commits >= 30 else 0.60 if commits >= 10 else 0.45
                    evidence = (
                        f"{repo['name']}: {lang} primary language ({pct:.0%}), "
                        f"{commits} commits, last active {repo.get('last_commit_days_ago', '?')}d ago"
                    )
                    return base, "language", evidence
                elif pct >= 0.05:
                    evidence = (
                        f"{repo['name']}: {lang} secondary language ({pct:.0%}), "
                        f"{commits} commits"
                    )
                    return 0.40, "language", evidence

        # README / dependency match
        readme = repo.get("readme_text", "").lower()
        for n in name_lower:
            if n in readme:
                base = 0.55 if commits >= 10 else 0.40
                evidence = (
                    f"{repo['name']}: '{names[0]}' found in README, "
                    f"{commits} commits, quality={repo.get('quality_score', 0)}/5"
                )
                return base, "framework", evidence

        # Topic/description match
        topics = " ".join(repo.get("topics", [])).lower()
        desc = repo.get("description", "").lower()
        for n in name_lower:
            if n in topics or n in desc:
                evidence = f"{repo['name']}: mentioned in repo topics/description"
                return 0.25, "implicit", evidence

        return 0.0, "none", "no signal found"

    def _recency_label(self, days: int) -> str:
        if days <= 30: return "active"
        if days <= 365: return "recent"
        if days <= 730: return "stale"
        return "stale"

    def _extract_skills(self, graph: dict) -> list[dict]:
        skills = []
        for cat in graph.get("skill_graph", {}).get("categories", []):
            for s in cat.get("skills", []):
                skills.append({"name": s["name"], "aliases": s.get("aliases", [])})
        return skills

    def _empty_result(self, candidate_id: str, skills: list[dict],
                       status: str, url: str) -> dict:
        return {
            "candidate_id": candidate_id,
            "parse_status": status,
            "source": "github",
            "github_username": url,
            "repos_analysed": 0,
            "repos_skipped_unmodified_forks": 0,
            "skill_evidence": [
                {
                    "skill": s["name"],
                    "confidence": 0.0,
                    "evidence": "no signal found",
                    "primary_repo": None,
                    "commit_count": None,
                    "recency": "unknown",
                    "quality_score": None,
                    "is_pinned_repo": False,
                    "is_fork": False,
                    "match_type": "none",
                }
                for s in skills
            ],
        }
