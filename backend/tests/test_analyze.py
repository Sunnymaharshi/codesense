"""
Tests for POST /api/analyze.
GitHub API calls are mocked with pytest-mock so no real network calls.
"""

from unittest.mock import AsyncMock, patch

import pytest

MOCK_GH_USER = {
    "login": "testuser",
    "name": "Test User",
    "avatar_url": "https://github.com/avatar.png",
    "bio": "A developer",
    "html_url": "https://github.com/testuser",
    "location": "Hyderabad",
    "company": None,
    "followers": 42,
    "following": 10,
    "public_repos": 2,
    "created_at": "2019-01-01T00:00:00Z",
}

MOCK_GH_REPOS = [
    {
        "id": 1001,
        "name": "awesome-api",
        "full_name": "testuser/awesome-api",
        "description": "A FastAPI project",
        "html_url": "https://github.com/testuser/awesome-api",
        "homepage": None,
        "fork": False,
        "archived": False,
        "language": "Python",
        "stargazers_count": 12,
        "forks_count": 2,
        "open_issues_count": 1,
        "pushed_at": "2025-01-15T10:00:00Z",
        "created_at": "2024-01-01T00:00:00Z",
        "topics": ["fastapi", "python"],
        "owner": {"login": "testuser"},
    }
]

MOCK_SIGNALS = {
    "has_readme": True,
    "has_tests": True,
    "has_ci": True,
    "has_docker": True,
    "has_license": False,
    "has_contributing": False,
}


@pytest.mark.asyncio
async def test_analyze_creates_developer(client):
    with (
        patch("app.api.routes.analyze.GitHubClient.get_user", new_callable=AsyncMock) as mock_user,
        patch(
            "app.api.routes.analyze.GitHubClient.get_repos", new_callable=AsyncMock
        ) as mock_repos,
        patch(
            "app.api.routes.analyze.GitHubClient.get_languages", new_callable=AsyncMock
        ) as mock_langs,
        patch(
            "app.api.routes.analyze.GitHubClient.get_repo_signals", new_callable=AsyncMock
        ) as mock_signals,
        patch(
            "app.api.routes.analyze.GitHubClient.get_commit_count", new_callable=AsyncMock
        ) as mock_commits,
    ):
        mock_user.return_value = MOCK_GH_USER
        mock_repos.return_value = MOCK_GH_REPOS
        mock_langs.return_value = {"Python": 14000}
        mock_signals.return_value = MOCK_SIGNALS
        mock_commits.return_value = 47

        response = await client.post("/api/analyze", json={"github_username": "testuser"})

    assert response.status_code == 200
    data = response.json()
    assert data["github_username"] == "testuser"
    assert "developer_id" in data
    assert "job_id" in data


@pytest.mark.asyncio
async def test_analyze_returns_404_for_unknown_user(client):
    import httpx

    with patch("app.api.routes.analyze.GitHubClient.get_user", new_callable=AsyncMock) as mock_user:
        mock_user.side_effect = httpx.HTTPStatusError(
            "Not found",
            request=httpx.Request("GET", "https://api.github.com/users/nobody"),
            response=httpx.Response(404),
        )
        response = await client.post("/api/analyze", json={"github_username": "nobody"})

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_analyze_idempotent(client):
    """Calling analyze twice for the same user should upsert, not duplicate."""
    with (
        patch("app.api.routes.analyze.GitHubClient.get_user", new_callable=AsyncMock) as mock_user,
        patch(
            "app.api.routes.analyze.GitHubClient.get_repos", new_callable=AsyncMock
        ) as mock_repos,
        patch(
            "app.api.routes.analyze.GitHubClient.get_languages", new_callable=AsyncMock
        ) as mock_langs,
        patch(
            "app.api.routes.analyze.GitHubClient.get_repo_signals", new_callable=AsyncMock
        ) as mock_signals,
        patch(
            "app.api.routes.analyze.GitHubClient.get_commit_count", new_callable=AsyncMock
        ) as mock_commits,
    ):
        mock_user.return_value = MOCK_GH_USER
        mock_repos.return_value = MOCK_GH_REPOS
        mock_langs.return_value = {"Python": 14000}
        mock_signals.return_value = MOCK_SIGNALS
        mock_commits.return_value = 47

        r1 = await client.post("/api/analyze", json={"github_username": "testuser"})
        r2 = await client.post("/api/analyze", json={"github_username": "testuser"})

    assert r1.status_code == 200
    assert r2.status_code == 200
    # Same developer_id both times
    assert r1.json()["developer_id"] == r2.json()["developer_id"]
