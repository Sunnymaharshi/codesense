"""
GitHub REST API client.
All methods are async. Raises httpx.HTTPStatusError on non-2xx responses.

Usage:
    client = GitHubClient(token=settings.GITHUB_TOKEN)
    user = await client.get_user("torvalds")
    repos = await client.get_repos("torvalds")
"""

import asyncio
import base64
import os
from typing import Any

import httpx


class GitHubClient:
    BASE_URL = "https://api.github.com"
    # How many repos to fetch per page (max 100)
    PER_PAGE = 100

    def __init__(self, token: str) -> None:
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    # ── Internal helper ───────────────────────────────────

    async def _get(self, path: str, params: dict | None = None) -> Any:
        """Make a GET request. Returns parsed JSON."""
        async with httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers=self._headers,
            timeout=30.0,
        ) as client:
            response = await client.get(path, params=params)
            response.raise_for_status()
            return response.json()

    def _get_sync(self, path: str, params: dict | None = None, timeout: float = 30.0) -> Any:
        """Make a GET request synchronously. Returns parsed JSON."""
        with httpx.Client(
            base_url=self.BASE_URL,
            headers=self._headers,
            timeout=timeout,
        ) as client:
            response = client.get(path, params=params)
            response.raise_for_status()
            return response.json()

    # ── Public methods ────────────────────────────────────

    async def get_user(self, username: str) -> dict:
        """
        Fetch a GitHub user's public profile.
        Returns: { login, name, avatar_url, bio, company, location,
                   followers, following, public_repos, created_at, ... }
        """
        return await self._get(f"/users/{username}")

    async def get_repos(self, username: str) -> list[dict]:
        """
        Fetch all public repos for a user (handles pagination).
        Excludes forks by default — set include_forks=True to include them.
        Returns list sorted by pushed_at descending.
        """
        repos: list[dict] = []
        page = 1

        while True:
            page_data = await self._get(
                f"/users/{username}/repos",
                params={
                    "type": "public",
                    "sort": "pushed",
                    "direction": "desc",
                    "per_page": self.PER_PAGE,
                    "page": page,
                },
            )
            if not page_data:
                break
            repos.extend(page_data)
            if len(page_data) < self.PER_PAGE:
                break
            page += 1

        return repos

    async def get_languages(self, owner: str, repo: str) -> dict[str, int]:
        """
        Fetch language breakdown for a repo.
        Returns: { "Python": 14200, "TypeScript": 3400, ... }
        (values are bytes of code)
        """
        try:
            return await self._get(f"/repos/{owner}/{repo}/languages")
        except httpx.HTTPStatusError:
            return {}

    async def get_commit_count(self, owner: str, repo: str) -> int:
        """
        Estimate total commit count via the contributors stats endpoint.
        Falls back to 0 if the repo is empty or stats aren't ready yet.
        """
        try:
            # contributors/stats returns per-contributor weekly stats
            # sum of all .total gives total commits
            data = await self._get(f"/repos/{owner}/{repo}/contributors")
            if isinstance(data, list):
                return sum(c.get("contributions", 0) for c in data)
            return 0
        except httpx.HTTPStatusError:
            return 0

    async def check_file_exists(self, owner: str, repo: str, path: str) -> bool:
        """
        Check whether a file exists in the repo root.
        Used by health_score to detect README, Dockerfile, etc.
        """
        try:
            await self._get(f"/repos/{owner}/{repo}/contents/{path}")
            return True
        except httpx.HTTPStatusError:
            return False

    async def get_repo_signals(self, owner: str, repo: str) -> dict[str, bool]:
        """
        Detect health signals for a single repo in parallel.
        Returns: { has_readme, has_tests, has_ci, has_docker, has_license, has_contributing }

        Checks run concurrently — single repo takes ~1s not 6s.
        """
        checks = await asyncio.gather(
            # README — GitHub surfaces this directly on the repo object
            # but we check explicitly for accuracy
            self.check_file_exists(owner, repo, "README.md"),
            self.check_file_exists(owner, repo, "readme.md"),
            # Tests — common patterns
            self.check_file_exists(owner, repo, "tests"),
            self.check_file_exists(owner, repo, "test"),
            self.check_file_exists(owner, repo, "__tests__"),
            # CI
            self.check_file_exists(owner, repo, ".github/workflows"),
            self.check_file_exists(owner, repo, ".travis.yml"),
            self.check_file_exists(owner, repo, ".circleci"),
            # Docker
            self.check_file_exists(owner, repo, "Dockerfile"),
            self.check_file_exists(owner, repo, "docker-compose.yml"),
            # License
            self.check_file_exists(owner, repo, "LICENSE"),
            self.check_file_exists(owner, repo, "LICENSE.md"),
            # Contributing guide
            self.check_file_exists(owner, repo, "CONTRIBUTING.md"),
            return_exceptions=True,
        )

        def ok(result: Any) -> bool:
            return result is True

        return {
            "has_readme": ok(checks[0]) or ok(checks[1]),
            "has_tests": ok(checks[2]) or ok(checks[3]) or ok(checks[4]),
            "has_ci": ok(checks[5]) or ok(checks[6]) or ok(checks[7]),
            "has_docker": ok(checks[8]) or ok(checks[9]),
            "has_license": ok(checks[10]) or ok(checks[11]),
            "has_contributing": ok(checks[12]),
        }

    def get_repos_sync(self, username: str) -> list[dict[str, Any]]:
        """Fetch all public repos synchronously (for Celery workers)."""
        repos = []
        page = 1
        while True:
            batch = self._get_sync(
                f"/users/{username}/repos",
                params={"per_page": 100, "page": page, "type": "public", "sort": "updated"},
            )
            if not batch:
                break
            repos.extend(batch)
            page += 1
            if len(batch) < 100:
                break
        return repos

    def get_languages_sync(self, username: str, repo_name: str) -> dict[str, int]:
        """Fetch language breakdown synchronously."""
        try:
            return self._get_sync(f"/repos/{username}/{repo_name}/languages", timeout=15)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {}
            raise

    def get_commit_count_sync(self, username: str, repo_name: str) -> int:
        """Approximate commit count via the contributors endpoint synchronously."""
        try:
            data = self._get_sync(
                f"/repos/{username}/{repo_name}/contributors",
                params={"per_page": 1, "anon": "true"},
                timeout=15,
            )
            if isinstance(data, list) and data:
                return data[0].get("contributions", 0)
            return 0
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (404, 409):
                return 0
            raise

    def get_repo_signals_sync(self, username: str, repo_name: str) -> dict[str, bool]:
        """Check for presence of key files synchronously."""
        checks = {
            "has_readme": ["README.md", "README.rst", "README"],
            "has_license": ["LICENSE", "LICENSE.md", "LICENSE.txt"],
            "has_docker": ["Dockerfile", "docker-compose.yml"],
            "has_ci": [
                ".github/workflows",
                ".circleci/config.yml",
                ".travis.yml",
                "Jenkinsfile",
            ],
            "has_tests": [
                "tests/",
                "test/",
                "spec/",
                "__tests__/",
                "pytest.ini",
                "jest.config.js",
                "jest.config.ts",
            ],
            "has_contributing": ["CONTRIBUTING.md"],
        }

        results: dict[str, bool] = {k: False for k in checks}

        for signal, paths in checks.items():
            for path in paths:
                try:
                    self._get_sync(f"/repos/{username}/{repo_name}/contents/{path}", timeout=15)
                    results[signal] = True
                    break
                except httpx.HTTPStatusError as e:
                    if e.response.status_code != 404:
                        break
                    continue

        return results

    def get_repo_files_sync(
        self,
        owner: str,
        repo: str,
        extensions: set[str],
        skip_paths: set[str],
        max_files: int,
    ) -> list[tuple[str, str, str]]:
        """
        Returns list of (file_path, content, language) tuples.
        Language is inferred from extension.
        """
        EXT_TO_LANG = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".tsx": "TypeScript",
            ".jsx": "JavaScript",
            ".go": "Go",
            ".rs": "Rust",
            ".java": "Java",
            ".rb": "Ruby",
            ".php": "PHP",
            ".cs": "C#",
            ".cpp": "C++",
            ".c": "C",
            ".swift": "Swift",
            ".kt": "Kotlin",
            ".sh": "Shell",
            ".yaml": "YAML",
            ".yml": "YAML",
            ".toml": "TOML",
        }

        try:
            tree = self._get_sync(
                f"/repos/{owner}/{repo}/git/trees/HEAD",
                params={"recursive": "1"},
                timeout=30,
            ).get("tree", [])
        except httpx.HTTPStatusError:
            return []

        results: list[tuple[str, str, str]] = []
        candidates: list[tuple[str, str]] = []

        for item in tree:
            if item.get("type") != "blob":
                continue

            path = item["path"]

            if any(part in skip_paths for part in path.split("/")):
                continue

            ext = os.path.splitext(path)[1].lower()
            if ext not in extensions:
                continue

            candidates.append((path, ext))
            if len(candidates) >= max_files:
                break

        for path, ext in candidates:
            try:
                item = self._get_sync(
                    f"/repos/{owner}/{repo}/contents/{path}",
                    timeout=30,
                )
            except httpx.HTTPStatusError:
                continue

            if item.get("encoding") != "base64":
                continue

            try:
                content = base64.b64decode(item["content"]).decode(
                    "utf-8",
                    errors="replace",
                )
            except Exception:
                continue

            results.append((path, content, EXT_TO_LANG.get(ext, "text")))

        return results
