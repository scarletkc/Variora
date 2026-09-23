# Contributing to Variora

Issues and pull requests are welcome: propose a shared prompt, contribute a model implementation, report a problem, or improve the website and documentation. You can submit a prompt idea without implementing it yourself.

Contributions should be authentic, reproducible, and clear about the conditions behind each result.

## Propose a prompt

Open an issue with the task, expected deliverable, and any constraints on tools, dependencies, or assets. Keep the brief clear enough for different models to attempt independently and for readers to assess the results against the same requirements.

To add a project, use the [project template](templates/project/). Keep the shared brief in `PROMPT.md`. If a prompt changes after implementations exist, identify which revision each run used; results from different briefs should not be presented as the same comparison.

## Contribute an implementation

The rules in this section apply to model implementations under `projects/`. Website, infrastructure, and documentation changes follow the [general pull request requirements](#submit-a-pull-request); they are not subject to the original-result preservation policy. Model records may be completed or corrected while preserving an accurate account of the original output and run history.

Follow the [model implementation rules](projects/AGENTS.md) and use the [model record template](templates/model/README.md). Place the implementation in `projects/<project>/models/<model>/app/` and link it from the project README.

Use a separate branch and PR for each model implementation in each project, even when using the same model across projects. Keep the implementation's record, optional screenshots, and project README link in that PR.

We collect one implementation per model per project, including across different harnesses. A submission with more complete provenance, run details, and parameters may replace an older, incomplete record. To discuss significant differences between runs, open an issue with the comparison and relevant run details.

### Keep comparisons controlled

- Use the same shared prompt and starting inputs. Keep the harness, available tools, skills, resource limits, and other run conditions consistent where possible, so the model is the variable being compared.
- Record differences that cannot be held constant, including reasoning settings or provider restrictions. Explain which conditions changed rather than attributing every difference in the output to the model.
- Record follow-up instructions, retries, manual edits, and help from other models. If you select one result from multiple attempts, state how many attempts were made and how the result was selected.
- Preserve the independence required by the model implementation rules.

Different setups are welcome when their differences are disclosed. They should not be described as a controlled model-only comparison.

### Preserve the original result

Preserve the result when the original task run ends, including its mistakes and limitations. The model may autonomously inspect and iterate on its work during that run. Later feedback from people or other models should be recorded as known issues rather than used to improve the generated code, visuals, or behavior, whether or not a PR has been opened.

An entirely unusable result may receive the minimum repair needed to load, start, or enter its core interaction. Stop once basic operation is restored. Visual flaws, incomplete requirements, and bugs that do not prevent basic use remain part of the result; this exception does not permit polishing, tuning, or adding features.

For a repair, link the original commit or preserved artifact in the model record. Record the original failure, each repair attempt and its changes, the assistance used, the total attempt count, and the outcome. Label the result as repaired and identify whether each screenshot shows the original or repaired version. Retain the original failure in the record even if the repair succeeds.

### Make results verifiable

- Provide the actual source and enough setup and run instructions for another person to run the submitted result, including required dependencies and environment details.
- Record the exact model ID, provider, harness, and assistance used. Use `none` when absent and `unknown` when information is unavailable; do not guess.
- Check available logs, settings, and version information first. Before submitting, agents must ask their user about any unresolved Model, Provider, Harness, or Reasoning effort fields; explain any information that remains unknown.
- Include the prompt revision and relevant settings needed to repeat the procedure. Model generation may vary between runs; reproducibility means a traceable procedure and runnable result, not a promise of identical generated output.
- Report checks you actually performed, their results, and known failures or limitations. Label expectations and untested claims clearly.
- Include screenshots of the running result whenever you can; they feed the site's comparison view and let readers assess the output without running it. `scripts/screenshot.mjs` captures pages headlessly if you want a helper, but any capture method is fine. Screenshots and measurements must come from the submitted implementation. For measurements, include the method and conditions; retain failures that affect the interpretation rather than presenting only favorable evidence.

### Submit music results

For music projects, keep the generating code and its outputs in `app/` and list them in `output.json` beside the model record, using the [music output format](site/README.md#music-outputs). The site plays the rendered audio and offers the MIDI file and source for inspection and download.

- Keep the original MIDI and any rendering produced during the run. Mark each file's `origin`: `model` for files produced during the run, `contributor` for anything rendered, converted, normalized, mixed, or edited afterwards.
- Describe the renderer, instrument set or sound bank, settings, and post-processing in `rendering` and in the model record. When a project compares composition, render every MIDI file with the renderer and instrument set named in its README. When the task includes synthesis or sound design, keep each model's own rendering and disclose how instruments and rendering differ.
- Record runtimes, dependencies, random seeds, external samples or sound banks, retries, continuation prompts, and manual assistance. For bundled samples and instrument assets, state their source and license, and include only assets that may be redistributed.
- If there is no playable audio, provide the source and run instructions; the listening view explains what is available. Mark incomplete or failed outputs in the model record.

### Keep the site preview runnable

The site copies `app/` — or the directory named in `preview.json` — verbatim into the published previews; it does not run a build. The entry page is served inside a sandboxed iframe with an opaque origin. For the preview link to work:

- Reference assets with relative paths (`./bundle.js`, not `/src/main.js`).
- Ship a classic script bundle. Module scripts need CORS headers the static host does not send, and bare imports such as `import "three"` have no bundler to resolve them.
- If the submitted form needs a build step, keep the source in `app/` and commit the built output alongside, with `preview.json` pointing at it, e.g. `{ "directory": "dist", "entry": "index.html" }`.
- Check the result from a plain static server, not only through a dev server.

When `app/index.html` exists it is published as the preview whether or not it can run; there is no opt-out.

## Report a problem

For bugs or disputed results, include the affected project or model, the revision if known, steps to reproduce, expected and actual behavior, and relevant environment details. Logs, screenshots, and a minimal example help others verify the issue. If you have not reproduced the problem, say so; questions and suspected issues are welcome too.

## Submit a pull request

Describe what changed, why, and how you checked it. Keep the scope focused, update affected documentation, and include any limitations reviewers need to reproduce or assess the result. Use Conventional Commits for commit messages and PR titles.

For website changes, follow the [website development and checks guide](site/README.md). For model implementations, include the checks appropriate to the app and its run instructions. Documentation-only changes should be checked for accurate wording and working links.
