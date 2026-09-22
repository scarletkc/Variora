# deepseek-v4.1-flash

| Field | Value |
| --- | --- |
| Model | `deepseek-v4.1-flash` |
| Provider | DeepSeek |
| Harness | WorkBuddy AI (Kite), agent mode |

## Assistance used

- Skills: `none` — the scene, the animation layer, and the audio graph were all written directly.
- Tools and plugins: `Read`, `Write`, `Edit`, `Glob`, `Grep`, and `Bash`. Bash was used only to drive a
  headless Chrome for rendering checks, and `git` for branching and commits. No asset-generation service
  and no external visual or audio assets were used.
- Subagents: `none`.

## Run

Open `app/index.html` in any modern browser. It is a single self-contained file with no build step, no
dependencies, and no network requests — the SVG, the CSS animations, and the WebAudio graph are all inline.

```bash
# from the repository root
start projects/rainy-ramen/models/deepseek-v4.1-flash/app/index.html
```

The rain ambience is muted by default. Click **Rain sound** in the bottom-right corner to start it
(browsers require a gesture before audio can play).

## Notes

**Approach.** One `viewBox="0 0 1200 800"` SVG scene, drawn back-to-front in sixteen numbered layers:
sky, far city, far rain, neighbouring buildings, the shop, the interior, the noren curtain, the wet street,
the cat, the counter, the bowl, the robot, the umbrella, the hanging lanterns, the near rain, and the
atmosphere pass. The page fills the viewport with `preserveAspectRatio` switching between `slice` and
`meet` based on the window aspect ratio, so wide screens get a full-bleed frame and narrow ones get the
whole illustration.

**Composition.** The shop is centred; the cat sits behind the counter on the left and the robot stands on
the wet street on the right, so the bowl and the cat's outstretched paw land on the diagonal between them.
The transparent umbrella is the largest single shape in the frame and reads as glass because the background
stays visible through it — only a gradient fill, ribs, and specular streaks are drawn.

**Everything is code.** No images, fonts, or audio files are loaded. The Japanese signage uses a system CJK
font stack. The rain is three tiling `<pattern>` fills on oversized rects, each translated vertically by
exactly one tile height so the loop is seamless; the streaks are drawn at an angle, so the fall reads as
slanted without needing a horizontal offset. Deterministic decoration (city windows, puddle ripples, ground
splashes, umbrella drips) is generated at load from a seeded `mulberry32` PRNG, so every load produces the
identical scene — useful when comparing implementations side by side.

**Audio** is a WebAudio graph built at first click: brown noise through a high-pass and low-pass pair, a
0.068 Hz LFO on the gain for natural gusting, a 46 Hz sine bed for weight, and a low-passed noise burst
that swells every 22–48 seconds like distant thunder.

**Checks performed.**

- Rendered in headless Chrome at 1600×1000 and 480×900; the full scene and the letterboxed narrow layout
  were both inspected visually, and the characters were re-inspected at 2–3× zoom.
- Confirmed the script-generated decoration is present in the DOM (64 splashes, 27 ripples, 8 drips, and
  the city window grid), i.e. the script runs to completion without throwing.
- Confirmed the animation layer actually advances: sampling the same page at 700 ms, 1500 ms and 2600 ms
  produced three different frames.
- Note for anyone re-running these checks: headless Chrome reports `prefers-reduced-motion: reduce`, so the
  accessibility override in the stylesheet disables all animation during a screenshot. The animated frames
  above were captured with that media block removed from a temporary copy.

**Known limitations.**

- The rain is a 2D layer, not a particle system; it does not interact with the umbrella geometry, and the
  canopy blocks nothing.
- Reflections on the street are stylised. A geometrically true mirror of the shop sign compresses into a
  band too thin to read at this camera angle, so the wet asphalt is built from vertical neon smears plus a
  deliberately squashed `<use>` reflection of the sign and lanterns.
- The ambient rain mix is a single continuous bed; it is not spatialised to the scene.
