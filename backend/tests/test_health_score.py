"""
Unit tests for health_score.py.
No DB, no GitHub API, no fixtures — pure function tests.
These should always be the first tests you write and run.
"""

from datetime import datetime, timedelta, timezone

from app.services.health_score import (
    compute_health_score,
    compute_language_percentages,
    get_top_language,
    score_to_grade,
)

# ── Fixtures ──────────────────────────────────────────────


def signals(**overrides) -> dict:
    """Default signals with everything False — override as needed."""
    base = {
        "has_readme": False,
        "has_tests": False,
        "has_ci": False,
        "has_docker": False,
        "has_license": False,
        "has_contributing": False,
    }
    return {**base, **overrides}


def recent(days: int = 30) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days)


# ── score_to_grade ────────────────────────────────────────


def test_grade_a_at_80():
    assert score_to_grade(80) == "A"


def test_grade_a_at_100():
    assert score_to_grade(100) == "A"


def test_grade_b_at_50():
    assert score_to_grade(50) == "B"


def test_grade_b_at_79():
    assert score_to_grade(79) == "B"


def test_grade_c_at_0():
    assert score_to_grade(0) == "C"


def test_grade_c_at_49():
    assert score_to_grade(49) == "C"


# ── compute_health_score ─────────────────────────────────


def test_empty_repo_scores_zero():
    score, grade = compute_health_score(signals(), last_commit_at=None)
    assert score == 0
    assert grade == "C"


def test_readme_adds_20():
    score, _ = compute_health_score(signals(has_readme=True), last_commit_at=None)
    assert score == 20


def test_tests_adds_25():
    score, _ = compute_health_score(signals(has_tests=True), last_commit_at=None)
    assert score == 25


def test_ci_adds_20():
    score, _ = compute_health_score(signals(has_ci=True), last_commit_at=None)
    assert score == 20


def test_docker_adds_15():
    score, _ = compute_health_score(signals(has_docker=True), last_commit_at=None)
    assert score == 15


def test_license_adds_10():
    score, _ = compute_health_score(signals(has_license=True), last_commit_at=None)
    assert score == 10


def test_recent_commit_adds_10():
    score, _ = compute_health_score(signals(), last_commit_at=recent(days=30))
    assert score == 10


def test_older_commit_adds_5():
    score, _ = compute_health_score(signals(), last_commit_at=recent(days=200))
    assert score == 5


def test_stale_commit_adds_0():
    score, _ = compute_health_score(signals(), last_commit_at=recent(days=400))
    assert score == 0


def test_perfect_repo_scores_100():
    score, grade = compute_health_score(
        signals(has_readme=True, has_tests=True, has_ci=True, has_docker=True, has_license=True),
        last_commit_at=recent(days=10),
    )
    assert score == 100
    assert grade == "A"


def test_good_repo_is_grade_b():
    # readme(20) + tests(25) = 45 → C ... add ci(20) = 65 → B
    score, grade = compute_health_score(
        signals(has_readme=True, has_tests=True, has_ci=True),
        last_commit_at=None,
    )
    assert score == 65
    assert grade == "B"


def test_naive_datetime_handled():
    # Should not raise even if datetime has no timezone
    naive_dt = datetime.now() - timedelta(days=10)
    score, _ = compute_health_score(signals(), last_commit_at=naive_dt)
    assert score == 10


# ── compute_language_percentages ─────────────────────────


def test_language_percentages_sum_to_100():
    langs = {"Python": 7000, "TypeScript": 2000, "Shell": 1000}
    result = compute_language_percentages(langs)
    assert abs(sum(result.values()) - 100.0) < 0.5


def test_language_percentages_sorted_descending():
    langs = {"Shell": 100, "Python": 7000, "TypeScript": 2000}
    result = compute_language_percentages(langs)
    values = list(result.values())
    assert values == sorted(values, reverse=True)


def test_empty_languages_returns_empty():
    assert compute_language_percentages({}) == {}


def test_zero_total_returns_empty():
    assert compute_language_percentages({"Python": 0}) == {}


# ── get_top_language ──────────────────────────────────────


def test_top_language_correct():
    assert get_top_language({"Python": 9000, "JS": 1000}) == "Python"


def test_top_language_empty_returns_none():
    assert get_top_language({}) is None
