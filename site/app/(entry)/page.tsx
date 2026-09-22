import Link from "next/link";
import { locales, localeNames } from "@/lib/i18n";

const languageScript = `(()=>{let l;try{l=localStorage.getItem('variora-locale')}catch{}const supported=['en','zh','ja','ko'];if(!supported.includes(l))l=navigator.languages.map(x=>x.split('-')[0]).find(x=>supported.includes(x))||'en';location.replace('/'+l+'/'+location.search+location.hash)})()`;
export default function Entry() {
  return (
    <main className="entry-page">
      <p className="eyebrow">VARIORA</p>
      <h1>
        One prompt.
        <br />
        Many possibilities.
      </h1>
      <nav aria-label="Language">
        {locales.map((locale) => (
          <Link className="button" key={locale} href={`/${locale}/`}>
            {localeNames[locale]}
          </Link>
        ))}
      </nav>
      <script dangerouslySetInnerHTML={{ __html: languageScript }} />
    </main>
  );
}
