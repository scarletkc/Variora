# Site development manual

Multi-language static showcase (Next.js 16, React 19, static export to `out/`).
The site is a compact demo gallery — not a marketing page. Keep it that way: no
hero blocks, slogans, or decorative copy that doesn't help a visitor open a
demo.

## Commands

- `npm run dev` — dev server
- `npm run build` — static export (`out/`)
- `npm run check` — catalog generation + `tsc --noEmit`
- `npm test` — unit + design-token guard tests (`tests/*.test.mjs`)
- `npm run format:check` — Prettier (run from repo root)
- `node scripts/e2e.mjs` — Playwright browser suite (port 4173 must be free)
- `node scripts/serve.mjs` — serve `out/` on :4173

## Design system (`app/globals.css`)

Interface chrome must use the shared tokens — the guard tests
(`tests/design-tokens.test.mjs`) fail otherwise:

- **Radius**: `var(--radius-sm)` 4px badges · `var(--radius-md)` 6px controls ·
  `var(--radius-lg)` 8px containers. Only exceptions: `50%` circles, `0`.
- **Focus ring**: `border-color: var(--ink)` + `box-shadow: var(--ring)` on the
  control container (`:focus-within`), or the global 2px `outline` for links /
  plain buttons. Never a blurry multi-pixel halo.
- **Hover**: color/border changes only — controls do not translate. The single
  allowed lift is `.project-art-link:hover` (thumbnail affordance).
- **Palette**: monochrome only — `--bg/--surface/--ink/--muted/--line/--soft`,
  `--button/--button-ink`. Both light and dark themes exist; keep them pure
  neutral (white/black base).
- **Type scale** (px): 10/11/12 micro-labels & controls · 13/14/15 body ·
  18/20/22 cards · 27/28/32/34/36/40/42/52 headings. Body is DM Sans 15px.
- **Controls**: ~33px tall pills (`padding: 6-7px` + border), 12px text, icon
  `var(--muted)` + label `var(--ink)`. Dropdowns use the `Menu` component in
  `components/shell.tsx` — never a bare `<select>`.

## Layout of the CSS

- `app/globals.css` — UI chrome only (enforced by the tests above).
- `app/artwork.css` — project concept illustrations (`.ramen`, `.serpent`,
  `.generic`, `.art-*`). These are content art: exempt from tokens, may use any
  colors/sizes. Frame styles (`.project-art-link`, `.detail-art`) stay in
  globals.

## i18n

Locales: `en zh ja ko` (`lib/i18n.ts`). Every user-facing string is a key in
`messages`; remove keys when their UI is deleted — the key list is the content
inventory. `localeNames` are native names shown in the language menu.

Locale switching (`components/shell.tsx`) preserves pathname + query but drops
the URL hash on purpose — preserving it caused a scroll-to-bottom bug.

## Content

Projects/models come from `scripts/catalog.mjs` scanning the project
directories; `npm run check`/build regenerates `lib/catalog.ts`.
