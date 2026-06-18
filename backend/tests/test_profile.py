"""
Tests for GET /api/profile/{username}.
"""

from unittest.mock import AsyncMock, patch

import pytest

from tests.test_analyze import MOCK_GH_REPOS, MOCK_GH_USER, MOCK_SIGNALS


async def seed_profile(client):
    """Helper: run analyze first so profile exists."""
    with (
        patch("app.api.routes.analyze.GitHubClient.get_user", new_callable=AsyncMock) as mu,
        patch("app.api.routes.analyze.GitHubClient.get_repos", new_callable=AsyncMock) as mr,
        patch("app.api.routes.analyze.GitHubClient.get_languages", new_callable=AsyncMock) as ml,
        patch("app.api.routes.analyze.GitHubClient.get_repo_signals", new_callable=AsyncMock) as ms,
        patch("app.api.routes.analyze.GitHubClient.get_commit_count", new_callable=AsyncMock) as mc,
    ):
        mu.return_value = MOCK_GH_USER
        mr.return_value = MOCK_GH_REPOS
        ml.return_value = {"Python": 14000}
        ms.return_value = MOCK_SIGNALS
        mc.return_value = 47
        await client.post("/api/analyze", json={"github_username": "testuser"})


@pytest.mark.asyncio
async def test_profile_returns_developer(client):
    await seed_profile(client)
    response = await client.get("/api/profile/testuser")
    assert response.status_code == 200
    data = response.json()
    assert data["developer"]["github_username"] == "testuser"
    assert data["developer"]["display_name"] == "Test User"


@pytest.mark.asyncio
async def test_profile_returns_repos(client):
    await seed_profile(client)
    response = await client.get("/api/profile/testuser")
    data = response.json()
    assert len(data["repos"]) == 1
    repo = data["repos"][0]
    assert repo["name"] == "awesome-api"
    assert repo["health_grade"] in ("A", "B", "C")


@pytest.mark.asyncio
async def test_profile_returns_stats(client):
    await seed_profile(client)
    response = await client.get("/api/profile/testuser")
    stats = response.json()["stats"]
    assert stats["total_repos"] == 1
    assert "top_language" in stats
    assert "language_percentages" in stats
    assert "grade_counts" in stats


@pytest.mark.asyncio
async def test_profile_404_for_unknown(client):
    response = await client.get("/api/profile/nobody_xyz_123")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_profile_case_insensitive(client):
    await seed_profile(client)
    response = await client.get("/api/profile/TESTUSER")
    assert response.status_code == 200
