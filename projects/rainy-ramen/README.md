# Rainy Ramen

A static SVG illustration comparison: a cat serves ramen to a robot outside a small Japanese shop on a rainy night. Each result is designed to stand alone and fit into a side-by-side image grid.

## Brief

Give every model the complete [shared prompt](PROMPT.md). It defines the scene, output restrictions, generation budget, and acceptance criteria.

Use the [model record template](../../templates/model/) for each implementation and follow the repository's [comparison records](../../README.md#comparison-records). Save the artwork at `models/<model>/app/scene.svg`.

## Run and capture

1. Start a fresh session with the shared prompt and no other implementations in context. Start the timer when the prompt is submitted and stop the run at the prompt's time limit. Record elapsed time and the harness's configured reasoning and output limits where available.
2. Preserve the final submitted SVG before rendering it. Mark timeouts or missing deliverables as incomplete; retain any partial file as evidence. Record missing content or rendering failures without repairing the submission.
3. After submission, render every SVG in the same browser version on the same machine at 1024 x 1024. Save the full capture at `models/<model>/screenshots/scene.png` and record the browser version.
4. For a four-model comparison, arrange the captures in equal square cells in a 2 x 2 grid. Keep padding and label styling consistent. Add the model and harness names outside the artwork, with a short skills-used label and a link to full records in the accompanying post.
5. Preserve each full canvas and its colors when composing the grid. Label incomplete or failed submissions visibly. Keep the submitted SVG and original capture alongside the presentation image.

## Implementations

Browse [models](models/). Add one row per saved implementation, linking its record.

| Implementation | Criteria met | Visual observations | Evidence |
| --- | --- | --- | --- |
| [grok-4.7-xhigh run 01](models/grok-4-7-xhigh/) | Structural A1 and vector-restriction checks passed. Visual A2–A4 not checked. The 10-minute budget was exceeded. | Not recorded. The brief forbids preview before submission. | [Generation record](models/grok-4-7-xhigh/README.md). Screenshot not captured. |

## Visual comparison

Compare character recognizability, the serving gesture, perspective and occlusion, lighting and color, and readability at thumbnail size. Separate acceptance-criterion results from aesthetic preferences, and interpret each result alongside its recorded harness, skills, and tools.
