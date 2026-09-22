# GPT-6 Astra (Max)

| Field | Value |
| --- | --- |
| Model | gpt-6-astra (GPT-6 Astra) |
| Reasoning effort | Max |
| Provider | OpenAI |
| Harness | Codex desktop; version unknown |

Model identity and reasoning effort are recorded from the user's supplied run information. The original generation took place on 2026-09-14 in a Windows environment with PowerShell.

## Assistance used

- Skills: none during the original generation. Submission documentation used [ux-writing](https://github.com/scarletkc/agents); skill version or commit unknown.
- Tools and plugins: Codex `apply_patch` through `functions.exec` created the original HTML, and the Codex app file-opening tool opened it in the desktop panel. Git, GitHub CLI, and Codex GitHub/app tools package the existing result and submit the PR.
- Subagents: none.
- External assets, network dependencies, and reference implementations: none used during generation.

## Run

Open [app/index.html](app/index.html) in a browser with JavaScript enabled. There are no dependencies to install or build commands to run.

The page includes a pause/resume button and a speed slider. The animation starts paused when the browser reports a reduced-motion preference.

## Notes

- Prompt revision: the original user request is preserved verbatim in [PROMPT.md](../../PROMPT.md), introduced with this implementation.
- Attempts: one generation, with no retries or selection among candidates. No follow-up revisions were made to the HTML.
- Submission: imported on 2026-09-22 from the original `pelican-cycle.html` produced in this conversation. The file is copied unchanged to `app/index.html` for the repository's preview discovery.
- Follow-up instruction: submit the prompt and existing implementation to Variora, recording GPT-6 Astra, Max reasoning, and Codex desktop as the run metadata.
- Implementation: inline SVG artwork, CSS animation, and JavaScript that keeps the pelican's feet aligned with the bicycle pedals. The scene includes rotating wheels, a moving coastal background, and a fluttering scarf.
- Checks: no automated tests, browser inspection, visual checks, or site build were run. The original prompt explicitly said tests were unnecessary. Opening the file in a Codex panel was not a validation step.
- Limitations: rendering, animation behavior, mobile layout, and browser compatibility have not been verified. No screenshots or performance measurements were captured.
- Additional generation settings and resource limits: unknown. This record does not establish a controlled comparison with other models.
