"""
LangGraph node functions for the Phase 4 analysis agent.
All functions are sync — graph is invoked via graph.invoke() inside a Celery worker.
"""

import json
import logging

from openai import OpenAI

from .tools import analyse_patterns, compute_growth, fetch_code_samples

logger = logging.getLogger(__name__)

GROQ_BASE = "https://api.groq.com/openai/v1"
MODEL = "llama-3.3-70b-versatile"


def fetch_node(state: dict) -> dict:
    """Fetch source files from top repos. Retries with wider search on second attempt."""
    samples = fetch_code_samples(
        username=state["username"],
        repos=state["repos"],
        github_token=state["github_token"],
        max_repos=8 if state["fetch_attempts"] == 0 else 15,
        files_per_repo=3,
    )
    logger.info(
        f"[fetch_node] @{state['username']}: {len(samples)} samples "
        f"(attempt {state['fetch_attempts'] + 1})"
    )
    return {
        "code_samples": samples,
        "fetch_attempts": state["fetch_attempts"] + 1,
        "is_data_sufficient": len(samples) >= 5,
    }


def analyse_node(state: dict) -> dict:
    """Run pure-Python pattern detection on fetched code samples."""
    analysis = analyse_patterns(state["code_samples"])
    growth = compute_growth(state["repos"])
    logger.info(
        f"[analyse_node] @{state['username']}: "
        f"patterns={analysis}, milestones={len(growth)}"
    )
    return {"analysis": analysis, "growth": growth}


def persona_node(state: dict) -> dict:
    """Call Groq (sync) to generate a 2-3 sentence developer persona."""
    repos = state["repos"]
    analysis = state["analysis"]
    top_repos = sorted(repos, key=lambda r: r.get("health_score") or 0, reverse=True)[:5]
    repo_summary = ", ".join(
        f"{r['name']}({r.get('primary_language', '?')})" for r in top_repos
    )
    total_stars = sum(r.get("stars", 0) for r in repos)
    total_commits = sum(r.get("commit_count", 0) for r in repos)

    prompt = (
        f"You are a developer analyst. Write a 2-3 sentence developer persona for "
        f"@{state['username']}.\n\n"
        f"Data:\n"
        f"- {len(repos)} public repos, {total_stars} total stars, {total_commits} total commits\n"
        f"- Top repos: {repo_summary}\n"
        f"- Languages: {', '.join(analysis.get('languages', [])[:5])}\n"
        f"- Code quality: type hints in {analysis.get('type_hint_rate', 0)}% of files, "
        f"error handling in {analysis.get('error_handling_rate', 0)}%, "
        f"docs in {analysis.get('docstring_rate', 0)}%\n\n"
        f"Write ONLY the persona paragraph. No preamble, no labels, no JSON. 2-3 sentences max."
    )

    try:
        client = OpenAI(api_key=state["groq_api_key"], base_url=GROQ_BASE)
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.5,
        )
        persona = resp.choices[0].message.content.strip()
    except Exception as exc:
        logger.warning(f"[persona_node] Groq failed, using fallback: {exc}")
        langs = ", ".join(analysis.get("languages", [])[:3]) or "various languages"
        persona = (
            f"Full-stack developer with {len(repos)} public repositories across {langs}. "
            f"Demonstrates consistent code quality with {analysis.get('type_hint_rate', 0)}% "
            f"type-annotated files and {analysis.get('error_handling_rate', 0)}% error-handled files."
        )

    logger.info(f"[persona_node] @{state['username']}: persona generated")
    return {"ai_persona": persona}


def score_node(state: dict) -> dict:
    """Call Groq (sync) to compute structured skill scores 0-100."""
    repos = state["repos"]
    analysis = state["analysis"]
    languages = analysis.get("languages", [])
    total = len(repos)
    has_tests_rate = round(sum(1 for r in repos if r.get("has_tests")) / total * 100) if total else 0
    has_ci_rate = round(sum(1 for r in repos if r.get("has_ci")) / total * 100) if total else 0
    avg_health = round(sum(r.get("health_score") or 0 for r in repos) / total) if total else 0

    prompt = (
        f"Score this developer's skills from 0-100. Return ONLY valid JSON, no explanation.\n\n"
        f"Developer: @{state['username']}\n"
        f"Languages: {languages[:8]}\n"
        f"Repos: {total}, Stars: {sum(r.get('stars', 0) for r in repos)}, "
        f"Commits: {sum(r.get('commit_count', 0) for r in repos)}\n"
        f"Repos with tests: {has_tests_rate}%, Repos with CI: {has_ci_rate}%\n"
        f"Code quality: type hints {analysis.get('type_hint_rate', 0)}%, "
        f"error handling {analysis.get('error_handling_rate', 0)}%, "
        f"docs {analysis.get('docstring_rate', 0)}%\n"
        f"Avg health score: {avg_health}/100\n\n"
        f'Return exactly this JSON (scores 0-100):\n'
        f'{{"backend": <int>, "frontend": <int>, "devops": <int>, "testing": <int>, "ai_ml": <int>}}'
    )

    try:
        client = OpenAI(api_key=state["groq_api_key"], base_url=GROQ_BASE)
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
            temperature=0.1,
        )
        raw = resp.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.rstrip("`").strip()
        scores = json.loads(raw)
        scores = {
            k: max(0, min(100, int(v)))
            for k, v in scores.items()
            if k in ("backend", "frontend", "devops", "testing", "ai_ml")
        }
    except Exception as exc:
        logger.warning(f"[score_node] Groq failed, using heuristics: {exc}")
        be_langs = {"Python", "Go", "Java", "Rust", "Ruby", "C#", "PHP"}
        fe_langs = {"TypeScript", "JavaScript", "HTML", "CSS"}
        ai_langs = {"Python", "Jupyter Notebook", "R"}
        lang_set = set(languages[:5])
        scores = {
            "backend": 70 if lang_set & be_langs else 40,
            "frontend": 70 if lang_set & fe_langs else 30,
            "devops": min(90, has_ci_rate + 30),
            "testing": min(90, has_tests_rate + 20),
            "ai_ml": 65 if lang_set & ai_langs else 20,
        }

    logger.info(f"[score_node] @{state['username']}: scores={scores}")
    return {"skill_scores": scores}
