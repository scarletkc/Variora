# cursor-grok-4-7-xhigh

| Field | Value |
| --- | --- |
| Model | cursor-grok-4-7-xhigh |
| Reasoning effort | unknown |
| Provider | unknown |
| Harness | Cursor (version unknown) |

## Assistance used

- Skills: frontend-design (local skill, version unknown) for the city palette and the on-screen type. motion (local skill, version unknown) for the frame loop: reused objects, no per-frame allocations on the hot path, and a capped timestep.
- Tools and plugins: Shell, to download Three.js 0.170.0 from the npm registry and bundle the official module build into one classic script with esbuild. Cursor's browser, to play the game and save a screenshot.
- Subagents: none

## Run

Open `app/index.html` in a browser. No install step. Choose Start, then turn with the mouse or with A and D. Click the view if the pointer is not captured. Eat the teal lights. After a hit, choose Run again, or press R. On a narrow window, Left and Right steer as well.

Three.js r170 is in `app/vendor/three.min.js`. That release has no separate UMD file, so the official `three.module.js` was bundled into one classic script. The preview sandbox can load it without module CORS. `app/vendor/LICENSE` is the MIT license.

## Notes

The camera sits at the snake's head and looks forward. There is no visor in the submitted file. The body is the trail behind the head, drawn in the world and on the corner map. Length starts at 16 and grows by 4 each light. Buildings, the outer wall, and the torii posts block the way. Crossing the older part of the trail ends the run. The end of a run uses the same side panel as the start screen.

Buildings, windows, and trim are made in code. The blocks share one window texture. No image or audio files are fetched. Start begins a quiet two-note bed. Eating a light plays a short tone. A hit plays a noise burst.

Known limitations of this run:

- Going straight, the body stays behind the camera, so the main view does not show it growing. The length text and the corner map do. `screenshots/street.png` is that forward view.
- A sharp turn in the browser hit a building near (5.1, 4.4) before the trail crossed itself. Self-collision was not observed.
- The avenues are narrow, so steering into a wall is easy.

This file is the first committed generation. Before that commit, a cyan visor parented to the camera filled the lower center of the view, and the walls were dark. The visor was removed and the walls were switched to an unlit material with a brighter window texture. A temporary pause flag and a line that printed the collision coordinates were used while checking and were not left in `app/`. The page was reloaded several times because the script URL had been cached.

After that version was committed, a follow-up asked to keep revising until the result seemed finished. That revision changed the camera, the city, and the end screen. It was reverted so the app and screenshot match this record.

Checked in Cursor's browser at a desktop width: the city renders, Start begins the run, eating teal lights raises the score and the length (one run went from 16 to 20; a straight run reached score 3 and the outer wall near (45.3, 0)), and a building hit shows Run again. Run again starts a fresh run. A sandboxed iframe with `allow-scripts` and `allow-pointer-lock`, the same permissions as the site preview, also rendered the street and Start.
