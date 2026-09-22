# SWE-2

| Field | Value |
| --- | --- |
| Model | SWE-2 |
| Reasoning effort | max |
| Provider | Cognition |
| Harness | Devin CLI 3000.11.1 |
| Prompt | [PROMPT.md](../../PROMPT.md) @ `184d49a` (2026-09-22) |

## Assistance used

- Skills: none
- Tools and plugins: Devin CLI built-in file/shell/search tools; esbuild 0.28.2 (bundler); Playwright 1.63.0 (headless smoke test and screenshots).
- Subagents: none

## Run

The game is a self-contained static page. `app/bundle.js` is a classic script, so `app/index.html` works when opened directly (`file://`), from any static server, and inside the site's sandboxed preview iframe.

```sh
npm install    # only needed for build/serve/test tooling; the app has no runtime deps
npm run build  # esbuild: src modules in app/ + vendored three → app/bundle.js
npm run serve  # → http://localhost:8080/
npm test       # rebuilds the bundle, then runs the headless Playwright suite
```

`npm run vendor` re-copies `three@0.186.0` from `node_modules` into `app/vendor/` after changing the pinned version; run `npm run build` afterward.

## Notes

- First-person snake: continuous steering via pointer-lock mouse, A/D or arrow keys, or touch drag; boost on Shift/W/Space; 3-2-1 countdown; pause on P/Esc or pointer-lock loss; restart on R; mute on M; best score persists in localStorage.
- The body is an arc-length-sampled instanced bead chain with a cyan→magenta gradient. Death comes from buildings, torii pillars, the boundary field, or biting your own body.
- The 13×13-block city is procedural: merged towers with canvas lit-window emissive textures, a single merged neon edge-lines mesh, canvas-generated Japanese sign boards (霓虹文字), torii gates spanning avenues, holo poles, rain, a gradient sky dome with stars and moon, and a glowing boundary wall.
- All textures are generated in canvas at runtime; all audio is synthesized Web Audio (saw pad drone, speed-following engine hum and wind noise, pickup chimes, noise-burst crash). No external assets.
- Storage: `app/store.js` wraps `localStorage` so sandboxed/opaque-origin previews (where storage throws) and `file://` work; falls back to in-memory values.
- Checks performed: `npm test` — 16/16 Playwright checks passed on Windows 11, headless Chromium (SwiftShader): boot to intro, WebGL canvas, countdown → playing, movement, orb collection, autopilot run, death → game over, retry, boot + JACK IN over `file://`, boot + JACK IN inside a `sandbox="allow-scripts allow-pointer-lock"` iframe, zero console/page errors. Screenshots in `screenshots/` are captures from that run.
- Known limitations: pointer-lock steering is desktop-only (touch drag steers on mobile); the `__NEON` debug hooks (teleport/autopilot) exposed for tests ignore obstacles and can crash the snake.
- Revision history: this result was **not** produced in a single shot — it went through several fix iterations after the original merged run:
  1. PR #14 — original implementation (prompt `PROMPT.md @ 184d49a`).
  2. PR #15 — post-merge static review: lockfile `name` aligned with `package.json` after the directory rename; prompt revision recorded.
  3. This PR — runtime boot fix: the original page used `<script type="module">`, which is blocked over `file://` and fails in the site's opaque-origin sandbox preview (where `localStorage` also throws) — the JACK IN button was dead. Repackaged as a classic esbuild bundle, added the storage guard and a boot-failure overlay, and extended the smoke test to cover `file://` and sandboxed-iframe boot.
