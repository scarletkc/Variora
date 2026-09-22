"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { projects, modelSource } from "@/lib/catalog";
import { messages, type Locale } from "@/lib/i18n";
import { Arrow } from "./icons";

export function Preview({ locale }: { locale: Locale }) {
  const query = useSearchParams();
  const project = projects.find((item) => item.id === query.get("project"));
  const model = project?.models.find((item) => item.id === query.get("model"));
  const t = messages[locale];
  const frame = useRef<HTMLDivElement>(null);
  const [version, setVersion] = useState(0);
  const [full, setFull] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    const changed = () => setFull(Boolean(document.fullscreenElement));
    document.addEventListener("fullscreenchange", changed);
    return () => document.removeEventListener("fullscreenchange", changed);
  }, []);
  if (!project || !model?.preview)
    return (
      <div className="empty-state">
        <h1>{t.invalidPreview}</h1>
        <p>{t.invalidPreviewBody}</p>
        <Link className="button primary" href={`/${locale}/`}>
          {t.goHome}
          <Arrow />
        </Link>
      </div>
    );
  async function toggleFullscreen() {
    try {
      if (document.fullscreenElement) await document.exitFullscreen();
      else await frame.current?.requestFullscreen();
      setError("");
    } catch {
      setError(t.fullscreenError);
    }
  }
  return (
    <>
      <Link className="back-link" href={`/${locale}/projects/${project.id}/`}>
        ← {t.returnProject}
      </Link>
      <div className="preview-heading">
        <div>
          <p className="eyebrow">
            {project.title} / {t.previewTitle}
          </p>
          <h1>{model.name}</h1>
          <p>{t.previewHelp}</p>
        </div>
        <a
          className="text-link"
          href={modelSource(project, model)}
          target="_blank"
          rel="noreferrer"
        >
          {t.source}
          <Arrow diagonal />
        </a>
      </div>
      <div className="preview-container" ref={frame}>
        <div className="preview-toolbar">
          <span className="preview-identity">
            <span className="status-dot" />
            {project.title}
          </span>
          <div>
            <button onClick={() => setVersion((value) => value + 1)}>
              {t.reload} ↻
            </button>
            <button onClick={toggleFullscreen}>
              {full ? t.exitFullscreen : t.fullscreen} ⛶
            </button>
          </div>
        </div>
        <iframe
          key={version}
          src={model.preview}
          title={`${project.title} — ${model.name}`}
          sandbox="allow-scripts allow-pointer-lock"
          allow="fullscreen; autoplay"
          referrerPolicy="no-referrer"
        />
      </div>
      {error && <p role="status">{error}</p>}
    </>
  );
}
