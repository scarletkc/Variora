# GPT-6 Sol · xhigh

| Field | Value |
| --- | --- |
| Model | `gpt-6-sol` |
| Reasoning effort | `xhigh` |
| Provider | OpenAI |
| Harness | Codex CLI `0.156.1` |

## Assistance used

- Skills: `computer-use` from the OpenAI bundled plugin, version `26.917.51856`, used to guide browser QA.
- Tools and plugins: shell commands for branch, dependency, build and syntax checks; `apply_patch` for source edits; `unified-computer-use` in Chrome for local gameplay and visual checks. No image, audio or asset generation service was used.
- Subagents: none.
- Other models or human code edits: none. One implementation attempt with autonomous inspection and iteration during this run.
- Provider and harness fields were confirmed by the user.

## Run

The shared prompt was `projects/neon-serpent/PROMPT.md` at starting commit `a85a8ace1b1e4b340bc4de96994a3c123b54c0f5`. The app uses Three.js `0.180.0` and Vite `7.1.7`; dependencies are locked in `app/package-lock.json`. Visuals, textures and optional sound effects are generated in code.

From `projects/neon-serpent/models/gpt-6-sol-xhigh/app/`:

```sh
npm ci
npm run dev
```

Open the local URL printed by Vite (normally `http://127.0.0.1:5173/`) in a WebGL-capable browser. Click **Initiate Run**. Use **A/D** or **Left/Right** to turn relative to the current heading, hold **W** or **Up** to boost, and use **Space** or **Escape** to pause. Touch steering buttons appear on narrow screens. Sound starts off and can be toggled on the start panel or top bar. For a production build, run `npm run build`.

This run used Windows, Node.js `22.22.3`, npm `12.0.1`, and Chrome. The sandboxed install used `npm install --no-audit --no-fund --cache .npm-cache`; Vite development serving and the production build both ran locally.

A prebuilt static bundle in `preview/` opens `index.html` directly (any static server or `file://`) and is what the site preview serves.

## Notes

- `node --check src/main.js`, `npm run build`, and `git diff --check` passed after the final source edits. Vite reported a nonfatal warning that the JavaScript chunk is over 500 kB.
- In Chrome, the game rendered the generated city and first-person view. The initial energy core raised the score from `00000` to `00100` and length from `04` to `05`; relative turning, obstacle and boundary collision, game-over display, pause/resume overlay, score reset on restart, and sound-toggle UI were checked.
- The final desktop visuals were inspected from the submitted app. Touch controls, self-collision, and audible output were not directly checked.
- `preview/` is a static repackaging added during review: the site preview serves files verbatim and cannot run the Vite dev source (`/src/main.js` absolute path, bare `three` import). `preview/bundle.js` and `preview/bundle.css` were built from the unmodified `app/src/` sources with esbuild (`--bundle --minify --format=iife`), and `preview/index.html` is `app/index.html` with only the resource references changed to relative paths. The original implementation in `app/` is unchanged.
- `screenshots/` were captured during review from the `preview/` repackaging in headless Chromium at 1440×900: the intro overlay and a live run at score `00100` after the first energy core, matching this run's own check. The repackaged build booted and played with zero console or page errors.
