# Variora website

The Next.js site at [variora.fog.moe](https://variora.fog.moe) is a static catalog of the repository's projects and model implementations.

## Development

From the repository root, with Node.js 24:

```sh
npm ci
npm run dev
```

`npm run build` exports the site to `site/out/`. To serve the export locally, run `npm --workspace site run serve` and open `http://127.0.0.1:4173`.

## Catalog and previews

The build discovers directories under `projects/` that contain `PROMPT.md`. Project titles and model identity fields come from their existing README files. An optional project `site.json` supplies a `category` (`illustration`, `game`, or `experiment`) and translated `summaries` keyed by `en`, `zh`, `ja`, and `ko`. Missing summaries fall back to English, then to the first paragraph of the prompt.

Models under `projects/<project>/models/<model>/` appear automatically. An `app/index.html` entry enables a preview; models without it link to their source and run instructions. The build copies static web assets and preserves relative paths. It does not install or execute model build scripts.

For a different static output directory or HTML entry, add `preview.json` beside the model README:

```json
{
  "directory": "app/dist",
  "entry": "index.html"
}
```

The directory must already exist in the checkout. Paths must stay inside the model directory, and the entry must stay inside the preview directory. Explicit invalid configuration fails the build. Dotfiles, dependencies, and unsupported file extensions are excluded; see `extensions` in [scripts/catalog.mjs](scripts/catalog.mjs) for the asset allowlist. Use relative asset URLs so each implementation can run under its own preview path.

Previews run in an iframe that permits scripts, pointer lock, and fullscreen while isolating the parent page. Implementations cannot access the site's DOM, cookies, or local storage. External module and data servers must permit cross-origin requests. Project artwork on catalog cards is illustrative, not a screenshot of a model result.

## Languages and themes

UI translations live in [lib/i18n.ts](lib/i18n.ts). Each language has static routes under `/en/`, `/zh/`, `/ja/`, and `/ko/`. The root chooses a saved language or a supported browser language, falling back to English. Changing languages preserves the page, query, and anchor. Original project names, prompts, and model records retain their source language.

The theme follows the system by default. Visitors can save a light or dark preference. Fonts are served with the site; the bundled [DM Sans](public/licenses/dm-sans.txt) and [Instrument Serif](public/licenses/instrument-serif.txt) licenses are included.

## Checks

```sh
npm test
npm run format:check
npm run check
npx playwright install chromium
npm --workspace site run test:e2e
npm run build
```

Browser tests build a temporary fixture catalog, exercise desktop and mobile views, and remove the fixture export afterward. Run `npm run build` afterward to produce a deployable export. `VARIORA_PROJECTS_DIR` overrides the catalog input directory for isolated test builds.

## Publishing

[Website workflow](../.github/workflows/pages.yml) validates and deploys relevant `main` changes through GitHub Actions to GitHub Pages. Manual runs also require `main`; pull requests do not trigger the workflow. The deployed artifact is the production `site/out/` export, built after the browser fixture checks. New implementations are indexed on the next deployment.

GitHub Pages must use **GitHub Actions** as its source and `variora.fog.moe` as its custom domain. Cloudflare DNS uses a DNS-only CNAME from `variora.fog.moe` to `scarletkc.github.io`. HTTPS is managed and enforced by GitHub Pages. Check the repository's Pages settings and workflow runs for current deployment status.
