"""
GitHub REST API client.
All methods are async. Raises httpx.HTTPStatusError on non-2xx responses.

Usage:
    client = GitHubClient(token=settings.GITHUB_TOKEN)
    user = await client.get_user("torvalds")
    repos = await client.get_repos("torvalds")
"""

import asyncio
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
