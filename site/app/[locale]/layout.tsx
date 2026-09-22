import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Header, Footer, themeScript } from "@/components/shell";
import { isLocale, locales, messages, type Locale } from "@/lib/i18n";
import { siteUrl } from "@/lib/catalog";
import "../globals.css";

export function generateStaticParams() {
  return locales.map((locale) => ({ locale }));
}
export const dynamicParams = false;

const ogLocales: Record<Locale, string> = {
  en: "en_US",
  zh: "zh_CN",
  ja: "ja_JP",
  ko: "ko_KR",
};

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  if (!isLocale(locale)) return {};
  const title = "Variora — " + messages[locale].tagline;
  const description = messages[locale].intro;
  return {
    metadataBase: new URL(siteUrl),
    title: {
      default: title,
      template: "%s · Variora",
    },
    description,
    openGraph: {
      type: "website",
      siteName: "Variora",
      title,
      description,
      url: `/${locale}/`,
      locale: ogLocales[locale],
      alternateLocale: locales
        .filter((key) => key !== locale)
        .map((key) => ogLocales[key]),
      images: [{ url: "/og.png", width: 1200, height: 630, alt: "Variora" }],
    },
    twitter: { card: "summary_large_image", title, description },
    themeColor: [
      { media: "(prefers-color-scheme: light)", color: "#ffffff" },
      { media: "(prefers-color-scheme: dark)", color: "#000000" },
    ],
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
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              "@context": "https://schema.org",
              "@type": "WebSite",
              name: "Variora",
              url: `${siteUrl}/${locale}/`,
              description: messages[locale].intro,
              inLanguage: locale,
            }),
          }}
        />
        <Header locale={locale} />
        {children}
        <Footer locale={locale} />
      </body>
    </html>
  );
}
