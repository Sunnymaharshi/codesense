"""
Repo health scorer.

Pure function — no DB calls, no API calls.
Takes repo metadata dict + signals dict, returns (score: int, grade: str).

Scoring rubric (total 100 points):
  has_readme      → +20   (essential for any public repo)
  has_tests       → +25   (biggest signal of code maturity)
  has_ci          → +20   (automated quality gate)
  has_docker      → +15   (production mindset)
  has_license     → +10   (open source hygiene)
  commit recency  → +10   (< 3 months active)
                    + 5   (< 12 months, but > 3)
                    + 0   (older than 12 months / never committed)

Grade:
  80–100  →  A
  50–79   →  B
  0–49    →  C
"""

from datetime import datetime, timezone
from typing import TypedDict


class RepoSignals(TypedDict):
    has_readme: bool
    has_tests: bool
    has_ci: bool
    has_docker: bool
    has_license: bool
    has_contributing: bool
    stars: int
    forks: int
    open_issues: int
    commit_count: int


def compute_health_score(
    signals: RepoSignals,
    last_commit_at: datetime | str | None,
) -> tuple[int, str]:
    """
    Returns (score, grade).

    Args:
        signals:        output of GitHubClient.get_repo_signals()
        last_commit_at: timezone-aware datetime or ISO string of last push, or None
    """
    score = 0

    if signals.get("has_readme"):
        score += 20
    if signals.get("has_tests"):
        score += 25
    if signals.get("has_ci"):
        score += 20
    if signals.get("has_docker"):
        score += 15
    if signals.get("has_license"):
        score += 10

    # Recency bonus
    if last_commit_at is not None:
        now = datetime.now(timezone.utc)
        # Parse ISO string if needed
        if isinstance(last_commit_at, str):
            last_commit_at = datetime.fromisoformat(last_commit_at.replace("Z", "+00:00"))
        # Ensure timezone-aware comparison
        if last_commit_at.tzinfo is None:
            last_commit_at = last_commit_at.replace(tzinfo=timezone.utc)
        days_since = (now - last_commit_at).days
        if days_since < 90:
            score += 10
        elif days_since < 365:
            score += 5

    grade = score_to_grade(score)
    return score, grade


def score_to_grade(score: int) -> str:
    if score >= 80:
        return "A"
    if score >= 50:
        return "B"
    return "C"


def compute_language_percentages(
    all_languages: dict[str, int],
) -> dict[str, float]:
    """
    Convert raw byte counts to percentages.

    Args:
        all_languages: { "Python": 14200, "TypeScript": 3400 }
    Returns:
        { "Python": 80.7, "TypeScript": 19.3 }
    """
    if not all_languages:
        return {}
    total = sum(all_languages.values())
    if total == 0:
        return {}
    return {
        lang: round((bytes_ / total) * 100, 1)
        for lang, bytes_ in sorted(all_languages.items(), key=lambda x: x[1], reverse=True)
    }


def get_top_language(all_languages: dict[str, int]) -> str | None:
    """Return the language with the most bytes, or None."""
    if not all_languages:
        return None
    return max(all_languages, key=all_languages.get)  # type: ignore[arg-type]
