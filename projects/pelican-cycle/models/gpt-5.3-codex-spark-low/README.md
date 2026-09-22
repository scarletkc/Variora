# GPT-5.3 Codex Spark · Light

| Field | Value |
| --- | --- |
| Model | `gpt-5.3-codex-spark` |
| Reasoning effort | `low` (Light) |
| Provider | OpenAI |
| Harness | Codex desktop; application version unknown |
| Environment | Windows with PowerShell; the same environment as the GPT-6 Astra run, as reported by the contributor |

Model identity, reasoning effort, and environment information were supplied by the contributor.

## Assistance used

- Skills: unknown for the original generation. Submission documentation used `ux-writing`. Source: [scarletkc/agents](https://github.com/scarletkc/agents), locally installed skill; version unknown.
- Tools and plugins: unknown for the original generation. Submission used PowerShell, file patching, Git, GitHub CLI, the GitHub connector, and Codex app tools to package the supplied file and submit the PR.
- Subagents: unknown for the original generation; none for submission.

## Run

Open [app/index.html](app/index.html) directly in a browser. The file contains inline SVG and CSS, with no build step, package installation, JavaScript, or external assets. It can also be served by a static HTTP server.

## Notes

The scene contains a pelican on a yellow bicycle against a sky and road background. CSS defines wheel rotation, horizontal rider movement, body bobbing, and wing and tail motion.

Generation record:

- The supplied `pelican-bike.html` is imported unchanged as `app/index.html`. The submission does not regenerate or revise the implementation.
- The contributor confirms one implementation attempt using the original Chinese prompt quoted below. [PROMPT.md](../../PROMPT.md) contains its English translation. The generation date, manual edits, and assistance from other models are unknown.
- The shared environment is contributor-reported. Detailed tool availability and additional generation settings are unknown, so this record does not establish a controlled model-only comparison.

Original generation prompt:

> 创建一个HTML，内容是SVG绘制一个鹈鹕骑自行车的2D动画，你不需要任何测试

The source was inspected for packaging. No automated tests, browser inspection, or visual checks were run on this implementation during submission. Checks performed during the original generation are unknown. Its rendering, animation behavior, mobile layout, and browser compatibility remain unverified.

The shared project cover is separate CSS/SVG artwork authored during submission. It is not a screenshot or output of this model.
