"use client";
import Link from "next/link";
import { useState } from "react";
import {
  type Project,
  modelSource,
  outputTypes,
  repository,
} from "@/lib/catalog";
import { messages, type Locale } from "@/lib/i18n";
import { MAX_COMPARISON_MODELS, exportComparison } from "@/lib/comparison";
import { Arrow } from "./icons";

export function Implementations({
  project,
  locale,
}: {
  project: Project;
  locale: Locale;
}) {
  const t = messages[locale];
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  // Comparison controls only appear when an export is actually possible.
  const comparable =
    project.models.filter((model) => model.screenshot).length >= 2;
  const query = search.trim().toLocaleLowerCase(locale);
  const filtered = project.models.filter((model) =>
    [model.name, model.provider, model.reasoning, model.harness]
      .join(" ")
      .toLocaleLowerCase(locale)
      .includes(query),
  );
  // Catalog order is stable regardless of selection clicks or current filtering.
  const chosen = project.models.filter((model) => selected.includes(model.id));
  const hidden = chosen.filter((model) => !filtered.includes(model)).length;
  function toggle(id: string) {
    setError("");
    setSelected((current) =>
      current.includes(id)
        ? current.filter((item) => item !== id)
        : [...current, id],
    );
  }
  async function download() {
    setBusy(true);
    setError("");
    try {
      const blob = await exportComparison({
        title: project.title,
        subtitle: t.comparisonSubtitle.replace(
          "{count}",
          String(chosen.length),
        ),
        models: chosen,
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${project.id}-comparison.png`;
      document.body.append(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 60000);
    } catch (failure) {
      setError(
        `${t.exportError} ${failure instanceof Error ? failure.message : ""}`,
      );
    } finally {
      setBusy(false);
    }
  }
  const status = [
    t.selectedCount.replace("{count}", String(selected.length)),
    hidden > 0 && t.hiddenSelected.replace("{count}", String(hidden)),
    selected.length < 2 && t.selectMore,
  ].filter(Boolean);
  return (
    <>
      <div className="section-heading">
        <h2>{t.implementations}</h2>
        {project.models.length > 2 && (
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
            <span className="sr-only">{t.searchModels}</span>
            <input
              type="search"
              placeholder={t.searchModels}
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </label>
        )}
      </div>
      {filtered.length === 0 && (
        <div className="empty-state" role="status">
          <h3>{t.noModels}</h3>
          <button className="button" onClick={() => setSearch("")}>
            {t.reset}
          </button>
        </div>
      )}
      <div className="model-grid">
        {filtered.map((model) => {
          const checked = selected.includes(model.id);
          const params = `?project=${encodeURIComponent(project.id)}&model=${encodeURIComponent(model.id)}`;
          return (
            <article
              key={model.id}
              className="model-card"
              data-selected={checked || undefined}
            >
              {model.screenshot && (
                <img
                  className="model-shot"
                  src={model.screenshot}
                  alt=""
                  loading="lazy"
                />
              )}
              <div className="model-head">
                <h3>{model.name}</h3>
                {comparable && model.screenshot && (
                  <label className="compare-toggle">
                    <input
                      type="checkbox"
                      aria-label={`${t.compare}: ${model.name}`}
                      checked={checked}
                      disabled={
                        busy ||
                        (!checked && selected.length >= MAX_COMPARISON_MODELS)
                      }
                      onChange={() => toggle(model.id)}
                    />
                    <span className="compare-box" aria-hidden="true">
                      <svg
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="3"
                      >
                        <path d="m5 12 5 5 9-10" />
                      </svg>
                    </span>
                    {t.compare}
                  </label>
                )}
              </div>
              <dl>
                {model.output && (
                  <div>
                    <dt>{t.outputs}</dt>
                    <dd>{outputTypes(model, t).join(" · ")}</dd>
                  </div>
                )}
                <div>
                  <dt>{t.provider}</dt>
                  <dd>{model.provider || t.unspecified}</dd>
                </div>
                <div>
                  <dt>{t.reasoning}</dt>
                  <dd>{model.reasoning || t.unspecified}</dd>
                </div>
                <div>
                  <dt>{t.harness}</dt>
                  <dd>{model.harness || t.unspecified}</dd>
                </div>
                <div>
                  <dt>{t.firstCommitted}</dt>
                  <dd>
                    {model.firstCommittedAt && model.commit ? (
                      <a
                        href={`${repository}/commit/${model.commit}`}
                        target="_blank"
                        rel="noreferrer"
                      >
                        <time dateTime={model.firstCommittedAt}>
                          {model.firstCommittedAt.slice(0, 10)}
                        </time>
                      </a>
                    ) : (
                      t.unspecified
                    )}
                  </dd>
                </div>
                <div>
                  <dt>{t.author}</dt>
                  <dd>
                    {model.author?.login ? (
                      <a
                        href={`https://github.com/${model.author.login}`}
                        target="_blank"
                        rel="noreferrer"
                      >
                        @{model.author.login}
                      </a>
                    ) : (
                      model.author?.name || t.unspecified
                    )}
                  </dd>
                </div>
              </dl>
              <div className="model-actions">
                {model.output && (
                  <Link
                    className="button primary"
                    href={`/${locale}/listen/${params}`}
                  >
                    {t.listen}
                    <Arrow />
                  </Link>
                )}
                {model.preview && (
                  <Link
                    className={`button${model.output ? "" : " primary"}`}
                    href={`/${locale}/preview/${params}`}
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
          );
        })}
      </div>
      {comparable && selected.length > 0 && (
        <div className="compare-bar" role="region" aria-label={t.compare}>
          <p role="status">{status.join(" · ")}</p>
          {error && <p role="alert">{error}</p>}
          <div>
            <button
              className="compare-clear"
              disabled={busy}
              onClick={() => {
                setSelected([]);
                setError("");
              }}
            >
              {t.clearSelection}
            </button>
            <button
              className="button primary"
              disabled={busy || selected.length < 2}
              onClick={download}
            >
              {busy ? t.exporting : t.downloadComparison}
            </button>
          </div>
        </div>
      )}
    </>
  );
}
