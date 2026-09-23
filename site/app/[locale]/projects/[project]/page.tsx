import { Implementations } from "@/components/implementations";
import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { isCategory, projects, projectSource, summary } from "@/lib/catalog";
import { locales, messages, type Locale } from "@/lib/i18n";
import { Artwork } from "@/components/artwork";
import { Arrow } from "@/components/icons";

type Params = { locale: Locale; project: string };
export function generateStaticParams() {
  return projects.map((project) => ({ project: project.id }));
}
export const dynamicParams = false;
export async function generateMetadata({
  params,
}: {
  params: Promise<Params>;
}): Promise<Metadata> {
  const { locale, project: id } = await params;
  const project = projects.find((item) => item.id === id);
  if (!project) return {};
  return {
    title: project.title,
    description: summary(project, locale),
    alternates: {
      canonical: `/${locale}/projects/${id}/`,
      languages: {
        ...Object.fromEntries(
          locales.map((key) => [key, `/${key}/projects/${id}/`]),
        ),
        "x-default": `/en/projects/${id}/`,
      },
    },
  };
}

export default async function ProjectPage({
  params,
}: {
  params: Promise<Params>;
}) {
  const { locale, project: id } = await params;
  const project = projects.find((item) => item.id === id);
  if (!project) notFound();
  const t = messages[locale];
  return (
    <main id="content" className="wrap project-page">
      <Link className="back-link" href={`/${locale}/#projects`}>
        ← {t.back}
      </Link>
      <section className="project-intro">
        <div>
          <p className="eyebrow">
            {isCategory(project.category) ? t[project.category] : t.experiment}
          </p>
          <h1>{project.title}</h1>
          <p>{summary(project, locale)}</p>
          <div className="hero-actions">
            <a
              className="button primary"
              href={`${projectSource(project)}/PROMPT.md`}
              target="_blank"
              rel="noreferrer"
            >
              {t.sharedPrompt}
              <Arrow diagonal />
            </a>
            <a
              className="text-link"
              href={projectSource(project)}
              target="_blank"
              rel="noreferrer"
            >
              {t.source}
              <Arrow diagonal />
            </a>
          </div>
        </div>
        <div className="detail-art">
          <Artwork id={project.id} />
          <span className="artwork-tag">{t.concept}</span>
        </div>
      </section>
      <section className="implementations">
        {project.models.length === 0 ? (
          <>
            <div className="section-heading">
              <h2>{t.implementations}</h2>
            </div>
            <div className="empty-state">
              <span className="empty-orbit" aria-hidden="true">
                <Arrow diagonal />
              </span>
              <h3>{t.emptyTitle}</h3>
              <p>{t.emptyBody}</p>
              <a
                className="text-link"
                href={`${projectSource(project)}/PROMPT.md`}
                target="_blank"
                rel="noreferrer"
              >
                {t.sharedPrompt}
                <Arrow diagonal />
              </a>
            </div>
          </>
        ) : (
          <Implementations key={project.id} project={project} locale={locale} />
        )}
      </section>
    </main>
  );
}
