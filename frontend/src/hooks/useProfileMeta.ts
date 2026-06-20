/**
 * useProfileMeta — sets document title + OG meta tags for shareable
 * profile link previews. No external library needed — vanilla DOM API.
 *
 * Call this in Profile.tsx once `data` is loaded.
 */
import { useEffect } from "react";
import type { ProfileResponse } from "@/lib/types";

function setMeta(property: string, content: string) {
  let tag = document.querySelector(`meta[property="${property}"]`);
  if (!tag) {
    tag = document.createElement("meta");
    tag.setAttribute("property", property);
    document.head.appendChild(tag);
  }
  tag.setAttribute("content", content);
}

export function useProfileMeta(data: ProfileResponse | undefined) {
  useEffect(() => {
    if (!data) return;
    const { developer, stats } = data;
    const name = developer.display_name ?? developer.github_username;

    const title = `${name} (@${developer.github_username}) — codesense`;
    const description =
      developer.ai_persona ??
      `${stats.total_repos} repos analyzed · avg health score ${stats.avg_health_score}/100 on codesense`;
    const image = developer.avatar_url ?? "";

    document.title = title;
    setMeta("og:title", title);
    setMeta("og:description", description);
    setMeta("og:type", "profile");
    setMeta("og:url", window.location.href);
    if (image) setMeta("og:image", image);
    setMeta("twitter:card", "summary");
    setMeta("twitter:title", title);
    setMeta("twitter:description", description);

    return () => {
      document.title = "codesense";
    };
  }, [data]);
}
