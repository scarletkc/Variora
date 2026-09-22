import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { projects, projectSource, modelSource, summary } from "@/lib/catalog";
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
            {t[project.category as "illustration" | "game" | "experiment"] ||
              t.experiment}
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
        <div className="section-heading">
          <h2>{t.implementations}</h2>
        </div>
        {project.models.length === 0 ? (
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
        ) : (
          <div className="model-grid">
            {project.models.map((model) => (
              <article key={model.id} className="model-card">
                <div className="model-topline">
                  <span className="model-status">
                    {model.preview ? t.preview : t.noPreview}
                  </span>
                </div>
                <h3>{model.name}</h3>
                <dl>
                  <div>
                    <dt>{t.provider}</dt>
                    <dd>{model.provider || t.unspecified}</dd>
                  </div>
                  <div>
                    <dt>{t.harness}</dt>
                    <dd>{model.harness || t.unspecified}</dd>
                  </div>
                </dl>
                <div className="model-actions">
                  {model.preview && (
                    <Link
                      className="button primary"
                      href={`/${locale}/preview/?project=${encodeURIComponent(project.id)}&model=${encodeURIComponent(model.id)}`}
                    >
                      {t.preview}
                      <Arrow />
                    </Link>
                  )}
                  <a
                    className="text-link"
                    href={modelSource(project, model)}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {t.record}
                    <Arrow diagonal />
                  </a>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
