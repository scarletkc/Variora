import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Header, Footer, themeScript } from "@/components/shell";
import { isLocale, locales, messages } from "@/lib/i18n";
import { siteUrl } from "@/lib/catalog";
import "../globals.css";

export function generateStaticParams() {
  return locales.map((locale) => ({ locale }));
}
export const dynamicParams = false;

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  if (!isLocale(locale)) return {};
  return {
    metadataBase: new URL(siteUrl),
    title: {
      default: "Variora — " + messages[locale].footer,
      template: "%s · Variora",
    },
    description: messages[locale].intro,
    icons: { icon: "/icon.svg" },
  };
}

export default async function Layout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  return (
    <html lang={locale === "zh" ? "zh-Hans" : locale} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body>
        <Header locale={locale} />
        {children}
        <Footer locale={locale} />
      </body>
    </html>
  );
}
