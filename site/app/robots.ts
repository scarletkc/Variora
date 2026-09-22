import type { MetadataRoute } from "next";
import { siteUrl } from "@/lib/catalog";
export const dynamic = "force-static";
export default function robots(): MetadataRoute.Robots {
  return {
    rules: { userAgent: "*", allow: "/", disallow: "/previews/" },
    sitemap: `${siteUrl}/sitemap.xml`,
  };
}
