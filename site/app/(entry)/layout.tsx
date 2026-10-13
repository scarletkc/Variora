import type { Metadata } from "next";
import { messages } from "@/lib/i18n";
import { themeScript } from "@/lib/theme";
import "../globals.css";

export const metadata: Metadata = {
  title: "Variora - " + messages.en.tagline,
  description: messages.en.intro,
  icons: { icon: "/icon.svg" },
};
export default function EntryLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body>{children}</body>
    </html>
  );
}
