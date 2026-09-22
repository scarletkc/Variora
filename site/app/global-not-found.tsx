import { localeNames, locales } from "@/lib/i18n";
import "./globals.css";

export default function NotFound() {
  return (
    <html lang="en">
      <head>
        <title>Page not found · Variora</title>
      </head>
      <body>
        <main className="entry-page">
          <p className="eyebrow">VARIORA / 404</p>
          <h1>Page not found.</h1>
          <nav aria-label="Language">
            {locales.map((locale) => (
              <a className="button" key={locale} href={`/${locale}/`}>
                {localeNames[locale]}
              </a>
            ))}
          </nav>
        </main>
      </body>
    </html>
  );
}
