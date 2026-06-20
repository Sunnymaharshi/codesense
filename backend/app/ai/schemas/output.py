"""
AI output schema — the JSON contract between the LLM and the frontend.

The LLM is prompted to return ONLY valid JSON matching AIMessage.
The frontend registry maps `type` → React component.
"""
from typing import Any, Literal
from pydantic import BaseModel


ComponentType = Literal[
    "commit_heatmap",
    "skill_radar",
    "growth_timeline",
    "code_pattern",
    "repo_comparison",
    "developer_persona",
    "hire_recommendation",
    "text",
]


class CommitHeatmapData(BaseModel):
    cells: list[dict] = []     # [{date, count, intensity: 0-4}] — can be empty; component generates from metadata
    peak_day: str | None = None
    total_commits: int = 0
    commits_per_week: float = 0.0
    weeks: int = 52


class SkillRadarData(BaseModel):
    axes: list[dict]           # [{label, score: 0-100}]
    summary: str


class GrowthTimelineData(BaseModel):
    milestones: list[dict]     # [{year, tech, description, repo}]


class CodePatternData(BaseModel):
    file_path: str
    language: str
    snippet: str
    insight: str


class RepoComparisonData(BaseModel):
    repos: list[dict]          # [{name, health_score, grade, stars, ...}]


class DeveloperPersonaData(BaseModel):
    headline: str
    summary: str
    traits: list[dict]         # [{label, score: 0-100}]


class HireRecommendationData(BaseModel):
    verdict: Literal["strong_yes", "yes", "maybe", "no"]
    headline: str
    reasoning: str
    strengths: list[str]
    gaps: list[str]


class AIMessage(BaseModel):
    type: ComponentType
    text: str                  # always present — narrative text
    data: dict[str, Any]       # component-specific payload
