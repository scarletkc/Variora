import type { Metadata } from "next";
import { Gallery } from "@/components/gallery";
import { projects } from "@/lib/catalog";
import { locales, messages, type Locale } from "@/lib/i18n";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}): Promise<Metadata> {
  const { locale } = await params;
  return {
    alternates: {
      canonical: `/${locale}/`,
      languages: {
        ...Object.fromEntries(locales.map((key) => [key, `/${key}/`])),
        "x-default": "/",
      },
    },
  };
}

export default async function Home({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}) {
  const { locale } = await params;
  const t = messages[locale];
  const modelCount = projects.reduce(
    (count, project) => count + project.models.length,
    0,
  );
  return (
    <main id="content">
      <section className="page-head wrap">
        <h1>{t.projects}</h1>
        <p>{t.intro}</p>
        <div className="page-stats">
          <span>
            <strong>{projects.length}</strong> {t.projectCount}
          </span>
          <span>
            <strong>{modelCount}</strong> {t.modelCount}
          </span>
        </div>
      </section>
      <Gallery locale={locale} />
    </main>
  );
}
