# SWE-2 Max

| Field | Value |
| --- | --- |
| Model | SWE-2 Max |
| Provider | Cognition |
| Harness | Devin CLI |

## Assistance used

- Skills: none
- Tools and plugins: shell and git for worktree/branch/commit/push; headless Chrome (`--screenshot`) for visual verification; `gh` for the pull request.
- Subagents: none

## Run

Open `app/index.html` in any modern browser, or serve the directory statically (`python -m http.server`). No build step.

- Click **rain sound** (bottom right) for generative WebAudio rain ambience — synthesized noise and droplet plinks, no audio files.
- `prefers-reduced-motion` disables animation and rain generation; append `?animate` to the URL to force motion anyway.

## Notes

- Composition: hand-authored inline SVG in `app/index.html` — ramen shop facade with tiled awning, noren curtain, glowing doorway, shoji window, paper lantern, vertical neon ラーメン sign; background city, power pole, and neon signage (酒場, cyan ring); vending machine; wet-street reflections and puddles.
- The cat (hachimaki + happi coat) holds out a steaming bowl toward the robot; the robot holds a translucent umbrella (ribs, scalloped rim, sliding drop, rim drips) and reaches for the bowl.
- `app/main.js` procedurally generates two depth layers of rain, ground splashes, and distant lit windows; `app/style.css` drives all animation (rain, steam, neon flicker, lantern/noren sway, tail wag, blink, heartbeat, ripples, reflection wobble). Pointer parallax on background layers.
- Verified with headless Chrome screenshots at 1280×800 and 2400×1600 (see `screenshots/preview.png`); no console errors observed.
- Known issue: none noted. The umbrella dome is intentionally translucent — background neon and back-layer rain remain visible through it.
