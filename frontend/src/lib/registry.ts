/**
 * Component registry — maps AI-returned `type` string to React component.
 * The LLM decides which component to render; this map wires it to the UI.
 */
import { lazy } from "react";

export const REGISTRY = {
  commit_heatmap:      lazy(() => import("@/components/ai-components/CommitHeatmap").then(m => ({ default: m.CommitHeatmap }))),
  skill_radar:         lazy(() => import("@/components/ai-components/SkillRadar").then(m => ({ default: m.SkillRadar }))),
  growth_timeline:     lazy(() => import("@/components/ai-components/GrowthTimeline").then(m => ({ default: m.GrowthTimeline }))),
  repo_comparison:     lazy(() => import("@/components/ai-components/RepoComparison").then(m => ({ default: m.RepoComparison }))),
  developer_persona:   lazy(() => import("@/components/ai-components/DeveloperPersona").then(m => ({ default: m.DeveloperPersona }))),
  hire_recommendation: lazy(() => import("@/components/ai-components/HireRecommendation").then(m => ({ default: m.HireRecommendation }))),
  text:                lazy(() => import("@/components/ai-components/TextMessage").then(m => ({ default: m.TextMessage }))),
} as const;

export type RegistryKey = keyof typeof REGISTRY;
