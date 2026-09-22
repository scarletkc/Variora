# Grok 4.7 xhigh

| Field | Value |
| --- | --- |
| Model | Grok 4.7 |
| Provider | xAI |
| Harness | Grok Build, grok CLI 1.0.40 (eb1a2256660d) |

## Assistance used

- Skills: frontend-design, for the page's visual direction. webapp-testing, for the browser check. Both came from the local Claude plugin cache `document-skills/0a64e398ec6b`. Skill versions: unknown.
- Tools and plugins: file editing and the shell, to build the page. Python Playwright driving headless Chromium 149.0.7827.55, against a local static server, to open the page, click Listen, and capture stills. No image or audio generation service was used.
- Subagents: none.

## Run

Open [app/index.html](app/index.html) in a browser. The picture fills a square in the window. Choose Listen to start the rain and hum; choose Quiet to stop them. Nothing to install, and the file does not need a server.

## Notes

This replaces the earlier static SVG on the same branch after the shared prompt changed. The page is one HTML file: an inline SVG scene, CSS motion, and audio synthesized with the Web Audio API. Rain streaks are drawn by the page script. No external picture, font, or sound file is loaded.

Checked on 2026-09-22 in headless Chromium:

- At 1280×900 and 390×844 the shop, cat, bowl, robot, clear umbrella, lantern, neon sign, rain, and warm light on the street were visible. The sign's strokes read as ラーメン.
- The page reported no console or page errors.
- Listen switched the control to Quiet and back. `aria-pressed` followed the clicks.
- With reduced motion requested, the umbrella sway and rain movement styles computed to `none`, while the rain marks stayed on screen.

Sound stays off until Listen, because browsers block audio until a gesture. On a tall phone the square picture sits between dark bands.
