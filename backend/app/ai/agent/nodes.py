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
    total = len(repos)
    has_tests_rate = round(sum(1 for r in repos if r.get("has_tests")) / total * 100) if total else 0
    has_ci_rate = round(sum(1 for r in repos if r.get("has_ci")) / total * 100) if total else 0
    avg_health = round(sum(r.get("health_score") or 0 for r in repos) / total) if total else 0

    ALLOWED_SKILLS = {"Backend", "Frontend", "AI/ML", "Systems Programming", "Testing", "DevOps"}

    # Merge code-sample languages with repo primary_language so C/C++ devs aren't invisible
    sample_langs = analysis.get("languages", [])
    repo_langs = [r.get("primary_language") for r in repos if r.get("primary_language")]
    seen = set(sample_langs)
    languages = sample_langs + [l for l in repo_langs if l not in seen]

    prompt = (
        f"Score this developer on ALL of the following 6 skill dimensions (0-100 each):\n"
        f"Backend, Frontend, AI/ML, Systems Programming, Testing, DevOps\n\n"
        f"Developer: @{state['username']}\n"
        f"Languages: {languages[:8]}\n"
        f"Repos: {total}, Stars: {sum(r.get('stars', 0) for r in repos)}, "
        f"Commits: {sum(r.get('commit_count', 0) for r in repos)}\n"
        f"Repos with tests: {has_tests_rate}%, Repos with CI: {has_ci_rate}%\n"
        f"Code quality: type hints {analysis.get('type_hint_rate', 0)}%, "
        f"error handling {analysis.get('error_handling_rate', 0)}%, "
        f"docs {analysis.get('docstring_rate', 0)}%\n"
        f"Avg health score: {avg_health}/100\n\n"
        f"Scoring guidance:\n"
        f"- Backend: Python/Go/Java/Ruby/PHP/C# used for web/API services — NOT general-purpose C/C++ code\n"
        f"- Frontend: TypeScript/JavaScript/HTML/CSS\n"
        f"- AI/ML: Python/Jupyter/R with clear data/ML focus\n"
        f"- Systems Programming: C/C++/Rust/Zig/Assembly — if ANY of these appear in languages, score 70+\n"
        f"- Testing: based on repos-with-tests signal\n"
        f"- DevOps: based on CI signal + Shell/Bash/Docker usage\n"
        f"IMPORTANT: C and C++ count toward Systems Programming ONLY, not Backend.\n"
        f"Score 10-25 if there is no evidence for a dimension, never zero.\n"
        f"Return ONLY valid JSON with exactly these 6 keys, no explanation.\n"
        f'Example: {{"Backend": 82, "Frontend": 45, "AI/ML": 30, "Systems Programming": 20, "Testing": 55, "DevOps": 61}}'
    )

    try:
        client = OpenAI(api_key=state["groq_api_key"], base_url=GROQ_BASE)
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=120,
            temperature=0.1,
        )
        raw = resp.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.rstrip("`").strip()
        parsed = json.loads(raw)
        scores = {
            k: max(0, min(100, int(v)))
            for k, v in parsed.items()
            if k in ALLOWED_SKILLS and isinstance(v, (int, float))
        }

        # Heuristic correction: primary langs get a floor, secondary langs get a cap
        _be  = {"Python", "Go", "Java", "Ruby", "C#", "PHP"}
        _fe  = {"TypeScript", "JavaScript", "HTML", "CSS"}
        _ai  = {"Python", "Jupyter Notebook", "R"}
        _sys = {"C", "C++", "Rust", "Zig", "Assembly"}

        primary   = set(languages[:3])
        secondary = set(languages[3:8])

        # (langs, primary_floor, secondary_cap)
        corrections = {
            "Systems Programming": (_sys, 70, 25),
            "Backend":             (_be,  55, 40),
            "Frontend":            (_fe,  60, 45),
            "AI/ML":               (_ai,  55, 30),
        }
        for skill, (langs, pri_floor, sec_cap) in corrections.items():
            current = scores.get(skill, 15)
            if primary & langs:
                scores[skill] = max(current, pri_floor)
            elif secondary & langs:
                scores[skill] = max(min(current, sec_cap), 15)
            else:
                scores[skill] = max(min(current, 15), 10)

        # Sys lang dominant: Systems Programming must clearly lead Backend
        if primary & _sys:
            scores["Systems Programming"] = max(scores.get("Systems Programming", 0), 75)
            scores["Backend"] = min(scores.get("Backend", 0), 35)

        testing_floor = max(15, has_tests_rate + 15)
        devops_floor  = max(15, has_ci_rate + 20)
        scores["Testing"] = max(scores.get("Testing", 0), testing_floor)
        scores["DevOps"]  = max(scores.get("DevOps", 0), devops_floor)

    except Exception as exc:
        logger.warning(f"[score_node] Groq failed, using heuristics: {exc}")
        be_langs = {"Python", "Go", "Java", "Ruby", "C#", "PHP"}
        fe_langs = {"TypeScript", "JavaScript", "HTML", "CSS"}
        ai_langs = {"Python", "Jupyter Notebook", "R"}
        sys_langs = {"C", "C++", "Rust", "Zig", "Assembly"}
        lang_set = set(languages[:8])

        scores = {
            "Backend": min(85, 50 + len(lang_set & be_langs) * 8) if lang_set & be_langs else 15,
            "Frontend": min(85, 50 + len(lang_set & fe_langs) * 8) if lang_set & fe_langs else 15,
            "AI/ML": min(85, 55 + (10 if "Jupyter Notebook" in lang_set else 0)) if lang_set & ai_langs else 15,
            "Systems Programming": min(85, 55 + len(lang_set & sys_langs) * 8) if lang_set & sys_langs else 15,
            "Testing": min(90, has_tests_rate + 20),
            "DevOps": min(90, has_ci_rate + 30),
        }

    logger.info(f"[score_node] @{state['username']}: scores={scores}")
    return {"skill_scores": scores}
