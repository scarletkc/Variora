import type { Metadata } from "next";
import { themeScript } from "@/components/shell";
import "../globals.css";

export const metadata: Metadata = {
  title: "Variora — Different models. The same brief.",
  description: "Explore model implementations of shared creative prompts.",
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
