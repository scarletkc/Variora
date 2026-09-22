"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useId, useRef, useState } from "react";
import { localeNames, locales, messages, type Locale } from "@/lib/i18n";
import { repository } from "@/lib/catalog";
import { Arrow, Mark } from "./icons";

export const themeScript = `(()=>{let t='system';try{t=localStorage.getItem('variora-theme')||t}catch{}document.documentElement.dataset.theme=t==='dark'||(t!=='light'&&matchMedia('(prefers-color-scheme: dark)').matches)?'dark':'light'})()`;

type MenuOption = { value: string; label: string };

function Menu({
  label,
  icon,
  value,
  options,
  onChange,
}: {
  label: string;
  icon: React.ReactNode;
  value: string;
  options: MenuOption[];
  onChange: (value: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const wrapRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const listRef = useRef<HTMLUListElement>(null);
  const id = useId();
  const selected = options.findIndex((option) => option.value === value);

  const pick = (index: number) => {
    onChange(options[index].value);
    setOpen(false);
    buttonRef.current?.focus();
  };
  const openMenu = () => {
    setActive(selected < 0 ? 0 : selected);
    setOpen(true);
  };

  useEffect(() => {
    if (!open) return;
    listRef.current?.focus();
    const onPointerDown = (event: MouseEvent) => {
      if (!wrapRef.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onPointerDown);
    return () => document.removeEventListener("mousedown", onPointerDown);
  }, [open]);

  const onButtonKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      openMenu();
    } else if (event.key === "Escape") {
      setOpen(false);
    }
  };
  const onListKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      setActive(
        (index) =>
          (index + (event.key === "ArrowDown" ? 1 : options.length - 1)) %
          options.length,
      );
    } else if (event.key === "Home" || event.key === "End") {
      event.preventDefault();
      setActive(event.key === "Home" ? 0 : options.length - 1);
    } else if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      pick(active);
    } else if (event.key === "Escape") {
      setOpen(false);
      buttonRef.current?.focus();
    } else if (event.key === "Tab") {
      setOpen(false);
    }
  };

  return (
    <div className="menu-wrap" ref={wrapRef}>
      <button
        ref={buttonRef}
        type="button"
        className="menu-button"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={label}
        onClick={() => (open ? setOpen(false) : openMenu())}
        onKeyDown={onButtonKeyDown}
      >
        {icon}
        <span>{options[selected]?.label ?? value}</span>
        <svg
          className="chevron"
          viewBox="0 0 10 6"
          width="10"
          height="6"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          aria-hidden="true"
        >
          <path d="m1 1 4 4 4-4" />
        </svg>
      </button>
      {open && (
        <ul
          ref={listRef}
          role="listbox"
          aria-label={label}
          aria-activedescendant={`${id}-${active}`}
          tabIndex={-1}
          className="menu"
          onKeyDown={onListKeyDown}
        >
          {options.map((option, index) => (
            <li
              key={option.value}
              id={`${id}-${index}`}
              role="option"
              aria-selected={option.value === value}
              className={index === active ? "active" : undefined}
              onMouseEnter={() => setActive(index)}
              onClick={() => pick(index)}
            >
              {option.label}
              <svg
                className="check"
                viewBox="0 0 12 10"
                width="12"
                height="10"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <path d="m1.5 5 3 3 6-7" />
              </svg>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

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
    window.location.assign(segments.join("/") + window.location.search);
  }
  return (
    <>
      <a className="skip-link" href="#content">
        {t.skip}
      </a>
      <header className="header wrap">
        <Link className="wordmark" href={`/${locale}/`} aria-label="Variora">
          <Mark />
          Variora
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
          <Menu
            label={t.language}
            value={locale}
            onChange={changeLocale}
            options={locales.map((key) => ({
              value: key,
              label: localeNames[key],
            }))}
            icon={
              <svg
                viewBox="0 0 20 20"
                width="15"
                height="15"
                fill="none"
                stroke="currentColor"
                aria-hidden="true"
              >
                <circle cx="10" cy="10" r="7.5" />
                <ellipse cx="10" cy="10" rx="3" ry="7.5" />
                <path d="M3 7h14M3 13h14" />
              </svg>
            }
          />
          <Menu
            label={t.theme}
            value={theme}
            onChange={changeTheme}
            options={[
              { value: "system", label: t.system },
              { value: "light", label: t.light },
              { value: "dark", label: t.dark },
            ]}
            icon={
              <svg
                viewBox="0 0 20 20"
                width="15"
                height="15"
                aria-hidden="true"
              >
                <circle
                  cx="10"
                  cy="10"
                  r="7"
                  fill="none"
                  stroke="currentColor"
                />
                <path d="M10 3a7 7 0 0 1 0 14Z" fill="currentColor" />
              </svg>
            }
          />
        </div>
      </header>
    </>
  );
}

export function Footer({ locale }: { locale: Locale }) {
  const t = messages[locale];
  return (
    <footer className="footer wrap">
      <Link className="wordmark small" href={`/${locale}/`}>
        <Mark />
        Variora
      </Link>
      <a
        href={`${repository}#add-a-comparison`}
        target="_blank"
        rel="noreferrer"
      >
        {t.contribute}
        <Arrow diagonal />
      </a>
    </footer>
  );
}
