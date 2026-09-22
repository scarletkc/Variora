import type { Metadata } from "next";
import { Gallery } from "@/components/gallery";
import { Arrow } from "@/components/icons";
import { HeroArtwork } from "@/components/artwork";
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
      languages: Object.fromEntries(locales.map((key) => [key, `/${key}/`])),
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
      <section className="hero wrap">
        <div className="hero-copy">
          <p className="eyebrow">
            <span className="status-dot" />
            {t.eyebrow}
          </p>
          <h1>
            {t.heroFirst}
            <br />
            <em>{t.heroSecond}</em>
          </h1>
          <p className="hero-intro">{t.intro}</p>
          <div className="hero-actions">
            <a className="button primary" href="#projects">
              {t.explore}
              <Arrow />
            </a>
            <a className="text-link" href="#about">
              {t.aboutLink}
              <span aria-hidden="true">↙</span>
            </a>
          </div>
        </div>
        <HeroArtwork />
        <div className="hero-stats">
          <div>
            <strong>{String(projects.length).padStart(2, "0")}</strong>
            <span>{t.projectCount}</span>
          </div>
          <div>
            <strong>{String(modelCount).padStart(2, "0")}</strong>
            <span>{t.modelCount}</span>
          </div>
          <div>
            <strong>{String(locales.length).padStart(2, "0")}</strong>
            <span>{t.languageCount}</span>
          </div>
          <span className="stats-note">{t.indexLabel}</span>
        </div>
      </section>
      <Gallery locale={locale} />
      <section id="about" className="about wrap">
        <div className="about-intro">
          <p className="eyebrow">{t.aboutEyebrow}</p>
          <h2>{t.aboutTitle}</h2>
          <p>{t.aboutBody}</p>
        </div>
        <ol className="about-steps">
          {[
            [t.stepOne, t.stepOneBody],
            [t.stepTwo, t.stepTwoBody],
            [t.stepThree, t.stepThreeBody],
          ].map(([title, body], index) => (
            <li key={title}>
              <span className="step-number">0{index + 1}</span>
              <div>
                <h3>{title}</h3>
                <p>{body}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>
    </main>
  );
}
