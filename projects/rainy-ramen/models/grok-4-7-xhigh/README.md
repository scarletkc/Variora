# Grok 4.7 xhigh, run 01

## Generation record

| Field | Value |
| --- | --- |
| Model | Grok 4.7. The session identified the model as Grok 4.7; the user addressed this run as Grok 4.7 xhigh. An API model slug was not printed by the harness. |
| Provider | xAI |
| Harness | Grok Build, grok CLI 1.0.40 (eb1a2256660d) |
| Generated on | 2026-09-22, UTC+08. Syntax validation of `app/scene.svg` finished at 09:23:03 +08. |
| Shared inputs revision | `c022580b958f964985dbf96782b4e2812485f320` |
| Model settings | Reasoning: xhigh, as named for this run. Temperature: unknown. Output limit: unknown. |
| Available capabilities | File, search, and shell tools; web fetch and search; image and video generation; subagents; workflows; scheduler. MCP servers connected but unused: cursor, github, tasks. Skills were listed in the session prompt and were not opened. Image generation was available and was not used. |
| Additional instructions | Repository `AGENTS.md` isolation rule and implementation workflow. User instruction: implement `projects/rainy-ramen` as Grok 4.7 xhigh in Grok Build. Other hidden system instructions: unknown. |
| Time and cost | First recorded clock 2026-09-22 09:04:43 +08, after the prompt had already been read. SVG syntax validation finished 09:23:03 +08. Interval between those clocks: 18 minutes 20 seconds. Total time from prompt receipt is longer than that interval and was not measured separately. The 10-minute generation budget was exceeded. Cost: not measured. |

## Assistance used

- Skills: none. No skill document was read or applied. Listed-but-unused skill names included build-with-ai, create-skill, create-workflow, design, docx, execute-plan, game-assets, imagine, learn, long-running-background-tasks, pdf, pptx, resume-claude, resume-codex, resume-cursor, review, skill-design-principles, statusline, threejs-frame-conventions, academy-guide, algorithmic-art, brand-guidelines, canvas-design, claude-api, discernment-nudge, doc-coauthoring, frontend-design, internal-comms, mcp-builder, slack-gif-creator, theme-factory, web-artifacts-builder, and webapp-testing. Versions: unknown.
- Tools and plugins: `list_dir` and `read_file` to read the brief, workflow, and model template. `run_terminal_command` to inspect git, create `feat/rainy-ramen/grok-4-7-xhigh-run-01`, copy `templates/model`, read the clock, run `grok --version`, XML-validate the SVG, and hash it. `search_replace` to write `app/scene.svg` and this record. No MCP tool was called. Image, browser, and web tools were not used. Git commit, push, and pull-request creation happen after this freeze and do not change the SVG.
- Subagents: none.

## Run

Source: [app](app/).

- Prerequisites: a browser that can open a local SVG file.
- Working directory: this implementation's `app/` directory.
- Install: not required.
- Start: open `scene.svg`.
- Open: `scene.svg` directly. No server, build, or network access is required.

Submitted file: `app/scene.svg`. SHA-256 at freeze: `5C25113525497F95A969628E509AD4A6346C24A45EA2930D4B765B11DA03D702`. Size: 26142 bytes.

## Verification

The brief allows code inspection and nonvisual syntax checks, and forbids rendering or visual preview before submission. No browser, screenshot, or rasterizer was used. Visual criteria were not judged from an image.

| Acceptance criterion | Result | Evidence |
| --- | --- | --- |
| A1. Standalone 1024×1024 SVG, full background, no missing external resources | Structural inspection passed. Opening it in a browser was not checked. | `System.Xml.XmlDocument` parsed the file. Root `svg`, namespace `http://www.w3.org/2000/svg`, `width="1024"`, `height="1024"`, `viewBox="0 0 1024 1024"`. Five full-canvas rects, including the sky background. URL scan found only the SVG and XLink namespace identifiers. |
| A2. Recognizable shop, cat chef, and robot; three-quarter shop with interior depth | not checked | No render. The file draws a front wall, side wall, and roof, an interior clipped to the serving window, a cat, and a robot. |
| A3. Cat hands over a steaming bowl; robot holds a transparent umbrella and reaches with the other hand | not checked | No render. The file draws those poses: cat paw under the bowl, steam paths, one robot hand on the umbrella handle, and the other extended toward the bowl. |
| A4. Lantern, Japanese neon sign, rain, wet reflections, warm interior against cool night | not checked | No render. The file includes a paper lantern, stroked ラーメン paths on a sign, rain patterns, blurred pavement reflections, and separate warm and cool gradients. |
| A5. Vector-only SVG, time limit, and no-preview rule | Vector restrictions passed inspection. Time limit failed. No-preview rule followed. | 363 elements and no `image`, `foreignObject`, `script`, animation, `style`, or embedded binary. Generation exceeded 10 minutes. The file was not opened or rasterized before submission. |
| A6. Generation record names model, provider, harness, and assistance, and marks unknown items | Pass | This record. |

Screenshots: [screenshots](screenshots/). None captured. The brief says the evaluator renders the submitted SVG after submission.

## Follow-up prompts and human edits

None. This is the first response. The SVG was not revised after the freeze hash above.

## Observations

The illustration is a single static vector scene: a corner-view ramen shop at night, a cat chef leaning through the service window, and a robot customer under a clear umbrella. The sign spells ラーメン with stroke paths so it does not depend on an installed font.

The 10-minute budget was missed, so this run does not satisfy the timing part of A5. Character readability, the handoff, perspective, and thumbnail legibility were not confirmed visually.
