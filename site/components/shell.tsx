"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { localeNames, locales, messages, type Locale } from "@/lib/i18n";
import { repository } from "@/lib/catalog";
import { Arrow, Mark } from "./icons";

export const themeScript = `(()=>{let t='system';try{t=localStorage.getItem('variora-theme')||t}catch{}document.documentElement.dataset.theme=t==='dark'||(t!=='light'&&matchMedia('(prefers-color-scheme: dark)').matches)?'dark':'light'})()`;

export function Header({ locale }: { locale: Locale }) {
  const t = messages[locale];
  const pathname = usePathname();
  const [theme, setTheme] = useState("system");
  const currentTheme = useRef("system");
  useEffect(() => {
    let saved = "system";
    try {
      saved = localStorage.getItem("variora-theme") || "system";
    } catch {}
    currentTheme.current = ["light", "dark"].includes(saved) ? saved : "system";
    setTheme(currentTheme.current);
    const media = matchMedia("(prefers-color-scheme: dark)");
    const apply = () => {
      const current = currentTheme.current;
      document.documentElement.dataset.theme =
        current === "dark" || (current !== "light" && media.matches)
          ? "dark"
          : "light";
    };
    media.addEventListener("change", apply);
    return () => media.removeEventListener("change", apply);
  }, []);
  function changeTheme(value: string) {
    currentTheme.current = value;
    setTheme(value);
    try {
      localStorage.setItem("variora-theme", value);
    } catch {}
    document.documentElement.dataset.theme =
      value === "dark" ||
      (value === "system" && matchMedia("(prefers-color-scheme: dark)").matches)
        ? "dark"
        : "light";
  }
  function changeLocale(value: string) {
    try {
      localStorage.setItem("variora-locale", value);
    } catch {}
    const segments = pathname.split("/");
    segments[1] = value;
    window.location.assign(
      segments.join("/") + window.location.search + window.location.hash,
    );
  }
  return (
    <>
      <a className="skip-link" href="#content">
        {t.skip}
      </a>
      <header className="header wrap">
        <Link className="wordmark" href={`/${locale}/`} aria-label="Variora">
          <Mark />
          variora<span className="brand-dot">.</span>
        </Link>
        <nav aria-label={t.projects} className="nav">
          <Link href={`/${locale}/#projects`}>{t.projects}</Link>
          <a
            className="repo-link"
            href={repository}
            target="_blank"
            rel="noreferrer"
          >
            {t.github}
            <Arrow diagonal />
          </a>
        </nav>
        <div className="preferences">
          <label className="select-wrap">
            <span className="sr-only">{t.language}</span>
            <svg
              viewBox="0 0 20 20"
              width="17"
              height="17"
              fill="none"
              stroke="currentColor"
              aria-hidden="true"
            >
              <circle cx="10" cy="10" r="7.5" />
              <ellipse cx="10" cy="10" rx="3" ry="7.5" />
              <path d="M3 7h14M3 13h14" />
            </svg>
            <select
              value={locale}
              onChange={(event) => changeLocale(event.target.value)}
            >
              {locales.map((key) => (
                <option key={key} value={key}>
                  {localeNames[key]}
                </option>
              ))}
            </select>
          </label>
          <label className="select-wrap theme-select">
            <span className="sr-only">{t.theme}</span>
            <svg viewBox="0 0 20 20" width="17" height="17" aria-hidden="true">
              <circle cx="10" cy="10" r="7" fill="none" stroke="currentColor" />
              <path d="M10 3a7 7 0 0 1 0 14Z" fill="currentColor" />
            </svg>
            <select
              value={theme}
              onChange={(event) => changeTheme(event.target.value)}
            >
              <option value="system">{t.system}</option>
              <option value="light">{t.light}</option>
              <option value="dark">{t.dark}</option>
            </select>
          </label>
        </div>
      </header>
    </>
  );
}

export function Footer({ locale }: { locale: Locale }) {
  const t = messages[locale];
  return (
    <footer className="footer wrap">
      <div>
        <Link className="wordmark small" href={`/${locale}/`}>
          <Mark />
          variora.
        </Link>
        <p>{t.footer}</p>
      </div>
      <a
        href={`${repository}#add-a-comparison`}
        target="_blank"
        rel="noreferrer"
      >
        {t.contribute}
        <Arrow diagonal />
      </a>
      <span className="footer-note">{t.openness}</span>
    </footer>
  );
}
