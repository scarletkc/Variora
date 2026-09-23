"use client";

import Link from "next/link";
import { useState } from "react";
import { isCategory, projects, summary } from "@/lib/catalog";
import { messages, type Locale } from "@/lib/i18n";
import { Artwork } from "./artwork";
import { Arrow } from "./icons";

export function Gallery({ locale }: { locale: Locale }) {
  const t = messages[locale];
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");
  const categories = Array.from(
    new Set(projects.map((project) => project.category)),
  );
  const categoryName = (category: string) =>
    isCategory(category) ? t[category] : category;
  const filtered = projects.filter(
    (project) =>
      (filter === "all" || project.category === filter) &&
      `${project.title} ${summary(project, locale)} ${project.models.map((model) => model.name).join(" ")}`
        .toLocaleLowerCase(locale)
        .includes(search.trim().toLocaleLowerCase(locale)),
  );
  return (
    <section id="projects" className="collection wrap" aria-label={t.projects}>
      <div className="filters">
        <label className="search">
          <svg
            width="15"
            height="15"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.6"
            aria-hidden="true"
          >
            <circle cx="10" cy="10" r="6.5" />
            <path d="m15 15 6 6" />
          </svg>
          <span className="sr-only">{t.search}</span>
          <input
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder={t.search}
          />
        </label>
        <div className="filter-tabs" aria-label={t.projects}>
          <button
            aria-pressed={filter === "all"}
            onClick={() => setFilter("all")}
          >
            {t.all}
            <span>{projects.length}</span>
          </button>
          {categories.map((category) => (
            <button
              key={category}
              aria-pressed={filter === category}
              onClick={() => setFilter(category)}
            >
              {categoryName(category)}
            </button>
          ))}
        </div>
      </div>
      <div className="project-grid">
        {filtered.map((project) => (
          <article className="project-card" key={project.id}>
            <Link
              className="project-art-link"
              href={`/${locale}/projects/${project.id}/`}
              aria-label={`${t.browse}: ${project.title}`}
            >
              <Artwork id={project.id} />
              <span className="artwork-tag">{t.concept}</span>
              <span className="artwork-arrow">
                <Arrow diagonal />
              </span>
            </Link>
            <div className="project-meta">
              <span>{categoryName(project.category)}</span>
              <span>
                {project.models.length
                  ? `${project.models.length} ${t.modelCount}`
                  : t.awaiting}
              </span>
            </div>
            <h3>
              <Link href={`/${locale}/projects/${project.id}/`}>
                {project.title}
              </Link>
            </h3>
            <p className="project-summary">{summary(project, locale)}</p>
            <Link
              className="text-link"
              href={`/${locale}/projects/${project.id}/`}
            >
              {t.browse}
              <Arrow />
            </Link>
          </article>
        ))}
      </div>
      {filtered.length === 0 && (
        <div className="empty-state" role="status">
          <h3>{t.noResults}</h3>
          <button
            className="button"
            onClick={() => {
              setSearch("");
              setFilter("all");
            }}
          >
            {t.reset}
          </button>
        </div>
      )}
    </section>
  );
}
