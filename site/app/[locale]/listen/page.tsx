import { Suspense } from "react";
import { Listen } from "@/components/listen";
import { messages, type Locale } from "@/lib/i18n";

export const metadata = {
  title: null,
  robots: { index: false, follow: true },
};
export default async function ListenPage({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}) {
  const { locale } = await params;
  return (
    <main id="content" className="wrap preview-page">
      <Suspense
        fallback={
          <>
            <title>{`${messages[locale].listening} - Variora`}</title>
            <p className="preview-loading" role="status">
              {messages[locale].loading}
            </p>
          </>
        }
      >
        <Listen locale={locale} />
      </Suspense>
    </main>
  );
}
