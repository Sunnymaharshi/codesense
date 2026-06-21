"""
Pure-Python analysis tools for the Phase 4 LangGraph agent.
No LLM calls — pattern detection and data transformation only.
"""

import re

from app.services.github import GitHubClient

EMBEDDABLE_EXTENSIONS = {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java", ".rb", ".cs",
                         ".c", ".cpp", ".cc", ".cxx", ".h", ".hpp"}
SKIP_DIRS = {"node_modules", ".git", "dist", "build", "__pycache__", ".venv", "vendor", "coverage"}


def fetch_code_samples(
    username: str,
    repos: list[dict],
    github_token: str,
    max_repos: int = 8,
    files_per_repo: int = 3,
) -> list[dict]:
    """Fetch source files from top repos sorted by health_score."""
    github = GitHubClient(github_token)
    samples = []
    sorted_repos = sorted(repos, key=lambda r: r.get("health_score") or 0, reverse=True)

    for repo in sorted_repos[:max_repos]:
        repo_name = repo.get("name", "")
        if not repo_name:
            continue
        try:
            files = github.get_repo_files_sync(
                owner=username,
                repo=repo_name,
                extensions=EMBEDDABLE_EXTENSIONS,
                skip_paths=SKIP_DIRS,
                max_files=files_per_repo,
            )
            for file_path, content, language in files:
                if len(content) > 200:
                    samples.append({
                        "repo": repo_name,
                        "file_path": file_path,
                        "content": content[:3000],
                        "language": language,
                    })
        except Exception:
            continue

    return samples


def analyse_patterns(samples: list[dict]) -> dict:
    """Detect code quality patterns across all samples."""
    if not samples:
        return {
            "type_hint_rate": 0,
            "error_handling_rate": 0,
            "docstring_rate": 0,
            "test_pattern_rate": 0,
            "languages": [],
            "total_files": 0,
        }

    type_hints = error_handling = docstrings = test_pats = 0
    lang_counts: dict[str, int] = {}

    for s in samples:
        c = s["content"]
        lang = s["language"]
        lang_counts[lang] = lang_counts.get(lang, 0) + 1

        if re.search(r':\s*(str|int|float|bool|list|dict|Optional|Union|Any)\b|-> \w+|\w+\[\w+\]', c):
            type_hints += 1
        if re.search(r'\btry\b[\s\S]{0,200}?\bexcept\b|\.catch\(|if\s+err\b|\.unwrap_or', c):
            error_handling += 1
        if re.search(r'"""[\s\S]{10,}?"""|/\*\*[\s\S]*?\*/', c):
            docstrings += 1
        if re.search(r'\bdef test_\w+|\bit\(["\']|\bdescribe\(["\']|\bexpect\(', c):
            test_pats += 1

    n = len(samples)
    return {
        "type_hint_rate": round(type_hints / n * 100),
        "error_handling_rate": round(error_handling / n * 100),
        "docstring_rate": round(docstrings / n * 100),
        "test_pattern_rate": round(test_pats / n * 100),
        "languages": sorted(lang_counts, key=lambda k: lang_counts[k], reverse=True),
        "total_files": n,
    }


def compute_growth(repos: list[dict]) -> list[dict]:
    """Tech stack milestones by year derived from repo push dates."""
    year_langs: dict[int, dict[str, int]] = {}

    for repo in repos:
        pushed = repo.get("last_commit_at") or repo.get("github_pushed_at")
        if not pushed:
            continue
        try:
            year = int(str(pushed)[:4])
        except (ValueError, TypeError):
            continue
        lang = repo.get("primary_language")
        if not lang:
            continue
        inner = year_langs.setdefault(year, {})
        inner[lang] = inner.get(lang, 0) + 1

    milestones = []
    for year in sorted(year_langs):
        top = max(year_langs[year], key=year_langs[year].get)
        count = year_langs[year][top]
        milestones.append({
            "year": year,
            "tech": top,
            "description": f"{count} repo{'s' if count > 1 else ''} in {top}",
            "repo": None,
        })

    return milestones
