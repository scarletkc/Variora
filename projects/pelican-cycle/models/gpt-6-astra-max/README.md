# GPT-6 Astra · Max

| Field | Value |
| --- | --- |
| Model | `gpt-6-astra` |
| Reasoning effort | `max` |
| Provider | OpenAI |
| Harness | Codex desktop; application version unknown |

## Assistance used

- Skills: none during the original generation. Submission documentation used `ux-writing`. Source: [scarletkc/agents](https://github.com/scarletkc/agents), locally installed skill; version unknown.
- Tools and plugins: Codex file patching for the original implementation; PowerShell, Git, GitHub CLI, and the GitHub connector for packaging and the pull request; Codex app tools for opening the file and attaching the PR.
- Subagents: none.

## Run

Open [app/index.html](app/index.html) directly in a browser with JavaScript enabled. There is no build step, package installation, or network dependency. The same file can be served by any static HTTP server.

Use **歇一会儿** to pause the animation and **继续兜风** to resume. The **慢慢骑** slider adjusts the speed. Reduced motion preferences start the animation paused; the resume button enables it.

## Notes

The page uses inline SVG for the pelican, bicycle, and coastal scenery. CSS animates the wheels, scarf, clouds, blinking, and background. JavaScript keeps the pelican's webbed feet aligned with the pedals and controls playback. All visual assets are drawn in code.

Generation record:

- The original user request is preserved verbatim in [PROMPT.md](../../PROMPT.md). The repository-rules link was added when submitting the result.
- Generated on 2026-09-14 in Codex desktop on Windows, in one attempt, with no retries, manual edits, or assistance from other models. Model identity and reasoning effort were supplied by the user; additional generation settings and resource limits are unknown.
- Imported on 2026-09-22 from the original `pelican-cycle.html`, copied unchanged to `app/index.html`. Follow-up instructions requested the PR and alignment with the Rainy Ramen documentation format.

No automated tests, browser inspection, visual checks, or site build were run. The original prompt explicitly said tests were unnecessary. Rendering, animation controls, mobile layout, and browser compatibility remain unverified. No screenshots or performance measurements were captured.
