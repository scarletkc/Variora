# GPT-6 Astra · xhigh

| Field | Value |
| --- | --- |
| Model | `gpt-6-astra` |
| Reasoning effort | `xhigh` |
| Provider | OpenAI |
| Harness | Codex desktop; application version unknown |

## Assistance used

- Skills: `ux-writing`, for interface copy and documentation. Source: [scarletkc/agents](https://github.com/scarletkc/agents), locally installed skill; version unknown.
- Tools and plugins: PowerShell, Node.js, and file patching for implementation; the Codex app workspace dependency tool for locating the bundled Playwright runtime; Playwright with Google Chrome for browser checks and screenshots; image viewing for visual review; Git and GitHub CLI for version control and the pull request; Codex app tools for attaching the PR and opening the preview.
- Subagents: none.

## Run

Open [app/index.html](app/index.html) directly in a browser. There is no build step, package installation, or network dependency. The same files can be served by any static HTTP server.

Use **Sound off** to enable the synthesized rain ambience, the **Rain** slider to choose drizzle, steady rain, or a downpour, and **Pause** to stop the animation. Sound and animation are controlled separately. Reduced motion preferences disable animation, and a hidden page suspends its sound and animation.

## Notes

The illustration uses inline SVG with code-drawn characters, architecture, transparent umbrella panels, warm and cool lighting, wet pavement, and procedural grain. CSS animates rain, steam, lantern sway, blinking, and ripples. JavaScript adds reproducible incidental details and generates the stereo rain and quiet hum through Web Audio. All visual and audio assets are generated in code.

Validation performed in Google Chrome 153.0.8010.48 on Windows:

- Direct file and local HTTP loading; no external requests or browser script errors.
- Rain density and labels, keyboard slider and pause operation, and animation pause/resume.
- Audio starts only after user interaction, produces a measurable signal, and suspends when switched off. Hidden-page suspension and restoration were checked with simulated visibility events.
- Reduced motion on initial load and preference changes; static illustration with JavaScript disabled; error feedback when Web Audio is unavailable.
- No horizontal overflow at 320, 390, 768, 1024, 1440, and 1920px viewport widths.
- Desktop and mobile visual review, JavaScript syntax, SVG references, and Git whitespace checks.

Other browser engines and physical mobile devices were not tested. Japanese lettering uses system fonts, so its appearance can vary by device.

[Desktop page](screenshots/desktop.png) · [Mobile page](screenshots/mobile.png)

![A cat serves ramen to a small robot under a transparent umbrella outside a neon-lit shop.](screenshots/illustration.png)
