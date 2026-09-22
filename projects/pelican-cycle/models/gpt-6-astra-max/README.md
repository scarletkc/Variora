# GPT-6 Astra · Max

| Field | Value |
| --- | --- |
| Model | `gpt-6-astra` |
| Reasoning effort | `max` |
| Provider | OpenAI |
| Harness | Codex desktop; application version unknown |

## Assistance used

- Skills: none during the original generation. Follow-up documentation, prompt translation, and English interface copy used `ux-writing` and `talk-like-scarletkc`. Source: [scarletkc/agents](https://github.com/scarletkc/agents), locally installed skills; versions unknown.
- Tools and plugins: Codex file patching for the original implementation and English text update; PowerShell, Git, GitHub CLI, and the GitHub connector for packaging and the pull request; Codex app tools for opening the file and attaching the PR.
- Subagents: none.

## Run

Open [app/index.html](app/index.html) directly in a browser with JavaScript enabled. There is no build step, package installation, or network dependency. The same file can be served by any static HTTP server.

Use **Take a break** to pause the animation and **Keep riding** to resume. The **Pace** slider adjusts the speed. Reduced motion preferences start the animation paused; the resume button enables it.

## Notes

The page uses inline SVG for the pelican, bicycle, and coastal scenery. CSS animates the wheels, scarf, clouds, blinking, and background. JavaScript keeps the pelican's webbed feet aligned with the pedals and controls playback. All visual assets are drawn in code.

Generation record:

- This implementation used the original Chinese request quoted below. [PROMPT.md](../../PROMPT.md) contains its English translation, prepared after generation, followed by the repository-rules link added during submission.
- Generated on 2026-09-14 in Codex desktop on Windows, in one attempt, with no retries or assistance from other models. Model identity and reasoning effort were supplied by the user; additional generation settings and resource limits are unknown.
- Imported on 2026-09-22 from the original `pelican-cycle.html`, initially copied unchanged to `app/index.html`.
- Follow-up edits translated the visible and accessibility text into English and set the document language to `en`. The SVG artwork, styling, and animation logic remain as generated.

Original generation prompt:

> 创建一个HTML，内容是SVG绘制一个鹈鹕骑自行车的2D动画，你不需要任何测试

No automated tests, browser inspection, visual checks, or site build were run. The original prompt explicitly said tests were unnecessary. Rendering, animation controls, mobile layout, and browser compatibility remain unverified. No screenshots or performance measurements were captured.
