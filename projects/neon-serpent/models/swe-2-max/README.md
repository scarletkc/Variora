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
- Tools and plugins: Devin CLI built-in file/shell/search tools; Playwright 1.63.0 (devDependency) for the headless smoke test and screenshots.
- Subagents: none

## Run

The game is a self-contained static page — open `app/index.html` from any static file server, or:

```sh
npm install    # only needed for serve/test tooling; the app has no runtime deps
npm run serve  # → http://localhost:8080/
npm test       # headless Playwright smoke test, writes screenshots/
```

`npm run vendor` re-copies `three@0.186.0` from `node_modules` into `app/vendor/` after changing the pinned version.

## Notes

- First-person snake: continuous steering via pointer-lock mouse, A/D or arrow keys, or touch drag; boost on Shift/W/Space; 3-2-1 countdown; pause on P/Esc or pointer-lock loss; restart on R; mute on M; best score persists in localStorage.
- The body is an arc-length-sampled instanced bead chain with a cyan→magenta gradient. Death comes from buildings, torii pillars, the boundary field, or biting your own body.
- The 13×13-block city is procedural: merged towers with canvas lit-window emissive textures, a single merged neon edge-lines mesh, canvas-generated Japanese sign boards (霓虹文字), torii gates spanning avenues, holo poles, rain, a gradient sky dome with stars and moon, and a glowing boundary wall.
- All textures are generated in canvas at runtime; all audio is synthesized Web Audio (saw pad drone, speed-following engine hum and wind noise, pickup chimes, noise-burst crash). No external assets.
- Checks performed: `npm test` — 11/11 Playwright checks passed on Windows 11, headless Chromium (SwiftShader): boot to intro, WebGL canvas, countdown → playing, movement, orb collection, autopilot run, death → game over, retry, zero console/page errors. Screenshots in `screenshots/` are captures from that run.
- Known limitations: pointer-lock steering is desktop-only (touch drag steers on mobile); the `__NEON` debug hooks (teleport/autopilot) exposed for tests ignore obstacles and can crash the snake.
- Revision history: original run merged in PR #14; post-merge review follow-up aligned the lockfile `name` with `package.json` and recorded the prompt revision. No game code changed.
