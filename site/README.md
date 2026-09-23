# Variora website

The Next.js site at [variora.fog.moe](https://variora.fog.moe) is a static catalog of the repository's projects and model implementations.

## Development

See the [development guide](docs/development.md) for setup, local servers, preview compatibility, and checks, and the [site development manual](docs/README.md) for design and content conventions.

## Catalog and previews

The build discovers directories under `projects/` that contain `PROMPT.md`. Project titles and model identity fields come from their existing README files. An optional project `site.json` supplies a `category` (`illustration`, `game`, `music`, or `experiment`) and translated `summaries` keyed by `en`, `zh`, `ja`, and `ko`. Missing summaries fall back to English, then to the first paragraph of the prompt.

Models under `projects/<project>/models/<model>/` appear automatically. An `app/index.html` entry enables a preview; models without it link to their source and run instructions. The build copies static web assets and preserves relative paths. It does not install or execute model build scripts.

For a different static output directory or HTML entry, add `preview.json` beside the model README:

```json
{
  "directory": "app/dist",
  "entry": "index.html"
}
```

The directory must already exist in the checkout. Paths must stay inside the model directory, and the entry must stay inside the preview directory. Explicit invalid configuration fails the build. Dotfiles, dependencies, and unsupported file extensions are excluded; see `extensions` in [scripts/catalog.mjs](scripts/catalog.mjs) for the asset allowlist. Use relative asset URLs so each implementation can run under its own preview path.

Previews run in an iframe that permits scripts, pointer lock, and fullscreen while isolating the parent page. Implementations cannot access the site's DOM, cookies, or local storage. Project artwork on catalog cards is illustrative, not a screenshot of a model result.

## Music outputs

Music results describe their files in `output.json` beside the model README. Paths are relative to the model directory and must stay inside it:

```json
{
  "type": "music",
  "audio": "app/walk.mp3",
  "midi": "app/walk.mid",
  "source": ["app/compose.py"],
  "rendering": "FluidSynth 2.4.0, GeneralUser GS 2.0.1, 44.1 kHz; no mastering."
}
```

- `audio`: one rendered recording (`.mp3`, `.m4a`, `.aac`, `.ogg`, `.oga`, `.opus`, `.wav`, `.flac`, or `.webm`). It is the playable form on the site.
- `midi`: the original `.mid` or `.midi` file. The build reads it for the listening view's length, tempo, meter, key, track, note, and General MIDI instrument summary, and a piano-roll overview. A file the reader cannot parse remains downloadable without those details.
- `source`: files or directories containing the code that generated the music. They are linked on GitHub rather than copied into the site.
- `rendering`: renderer, instruments or sound bank, settings, and any post-processing, shown as written.

At least one of `audio`, `midi`, or `source` is required. A file entry can also be an object, `{ "path": "renders/walk.mp3", "origin": "contributor" }`. `origin` defaults to `"model"`, for files produced during the generation run; use `"contributor"` for anything rendered, converted, normalized, mixed, or edited afterwards. The listening view labels each file with its origin.

The build copies only the named audio and MIDI files to `public/previews/_outputs/`. Missing files, unsupported formats, unknown fields or types, and paths that escape the model directory fail the build with the offending `output.json` path.

Models with `output.json` offer **Listen**, a view with play/pause, restart, seeking, elapsed and total time, volume, and switching between the project's other outputs. Playback starts only after a visitor presses play; switching outputs or leaving the view stops the previous recording. When there is no playable audio, or the browser cannot load it, the view explains this and keeps the files and model record available. Seeking needs a host that honors HTTP range requests; GitHub Pages and `npm --workspace site run serve` do. Browser-based music apps keep using `app/index.html` and the sandboxed preview.

## Model comparison images

Project pages can be searched by model name, provider, reasoning level, and
harness. When at least two implementations have a screenshot, their cards offer
a **Compare** toggle; selecting 2–8 downloads a themed PNG sheet composed
locally in the browser from the original captures. The layout and caption rules
live in [lib/comparison.ts](lib/comparison.ts).

The catalog selects a PNG, JPG, JPEG, or WebP directly under a model's
`screenshots/` directory. It prefers the stems `illustration`, `scene`, `preview`,
then `desktop`, followed by the first filename in sorted order. For an explicit
choice, add `comparison.json` beside the model README:

```json
{ "screenshot": "screenshots/02-gameplay.png" }
```

The path must resolve to a raster file inside that model's directory, including
after resolving symlinks. Invalid explicit configuration fails the build. Use
`{ "screenshot": null }` to opt out. Models without a capture remain browsable
but cannot be selected. The pipeline copies only the chosen file under
`public/previews/_comparisons/`; original captures are never changed. These are
stored captures, not live screenshots of the running iframe.

## Languages and themes

UI translations live in [lib/i18n.ts](lib/i18n.ts). Each language has static routes under `/en/`, `/zh/`, `/ja/`, and `/ko/`. The root chooses a saved language or a supported browser language, falling back to English. Changing languages preserves the page, query, and anchor. Original project names, prompts, and model records retain their source language.

The theme follows the system by default. Visitors can save a light or dark preference. Fonts are served with the site; the bundled [DM Sans](public/licenses/dm-sans.txt) and [Instrument Serif](public/licenses/instrument-serif.txt) licenses are included.

## Publishing

[Website workflow](../.github/workflows/pages.yml) validates pull requests targeting `main` when they change `site/`, root npm manifests, `.gitattributes`, `.prettierignore`, or the workflow itself. PR updates trigger one Website run through `pull_request`; a newer update cancels the previous run for that PR. Push-triggered runs are limited to `main`. The separate Main synchronization workflow checks branch ancestry.

Relevant `main` pushes and manual runs on `main` validate and deploy to GitHub Pages. PR runs validate without uploading a Pages artifact or deploying. New implementations are indexed on the next deployment.

Every run checks formatting, runs unit tests, and builds the production `site/out/` export. Changes limited to project descriptions, model records, screenshots, project `site.json` metadata, or this README skip browser installation and browser tests. Code, app assets, dependencies, tests, configuration, and mixed changes run the full checks. Pushes compare the before and after commits; PRs compare the base commit with GitHub's test merge commit. Manual runs and unavailable change history also run the full checks. The classification is defined by `needsBrowserTests` in [scripts/ci-changes.mjs](scripts/ci-changes.mjs).

The workflow caches npm downloads and `site/.next/cache` between runs. Browser binaries are installed only when browser tests run. Full checks build a fixture site first, discard its export, then build the production site. CI sets `VARIORA_E2E_RESTORE_CATALOG=false` to let that final build regenerate the catalog once; local browser tests restore the catalog by default.

GitHub Pages must use **GitHub Actions** as its source and `variora.fog.moe` as its custom domain. Cloudflare DNS uses a DNS-only CNAME from `variora.fog.moe` to `scarletkc.github.io`. HTTPS is managed and enforced by GitHub Pages. Check the repository's Pages settings and workflow runs for current deployment status.
