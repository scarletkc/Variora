import { messages } from "@/lib/i18n";
import { themeScript } from "@/lib/theme";
import { Arrow } from "@/components/icons";
import "./globals.css";

export default function NotFound() {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <title>Page not found - Variora</title>
        <link rel="icon" href="/icon.svg" />
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body>
        <main className="entry-page">
          <h1>Variora</h1>
          <p className="entry-message">404 - {messages.en.pageNotFound}</p>
          <a className="text-link" href="/">
            {messages.en.goHome}
            <Arrow />
          </a>
        </main>
      </body>
    </html>
  );
}
