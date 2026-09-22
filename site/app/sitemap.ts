import type { MetadataRoute } from "next";
import { projects, siteUrl } from "@/lib/catalog";
import { locales } from "@/lib/i18n";
export const dynamic = "force-static";
export default function sitemap(): MetadataRoute.Sitemap {
  return locales.flatMap((locale) => [
    { url: `${siteUrl}/${locale}/` },
    ...projects.map((project) => ({
      url: `${siteUrl}/${locale}/projects/${project.id}/`,
    })),
  ]);
}
