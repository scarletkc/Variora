import type { FullConfig } from "@playwright/test";

export default async function warm(config: FullConfig) {
  const base = config.projects[0].use.baseURL;
  for (const path of ["/en/", "/en/projects/e2e-music/", "/en/listen/"]) {
    const response = await fetch(new URL(path, base));
    if (!response.ok) throw new Error(`Could not compile ${path}`);
  }
}
