# cursor-grok-4-7-xhigh

| Field | Value |
| --- | --- |
| Model | cursor-grok-4-7-xhigh |
| Reasoning effort | unknown |
| Provider | unknown |
| Harness | Cursor (version unknown) |

## Assistance used

- Skills: frontend-design (local skill, version unknown) for the coastal palette and the rider's silhouette. motion (local skill, version unknown) for scrolling in SVG user units and for keeping the pedal math in one frame callback.
- Tools and plugins: Cursor's browser, to watch the ride and save a screenshot.
- Subagents: none

## Run

Open `app/index.html` in a browser. The coast moves past the pelican on its own. No server and no extra files.

## Notes

One HTML file. Clouds, hills, water, and the path are duplicated tiles translated in SVG units, so the loop does not depend on the window size. The wheels, chainring, and feet share one pedal cycle. The wing and the pouch move on their own.

The prompt does not ask for tests. The page was still opened in Cursor's browser at a desktop width to confirm the shore scrolls and the pelican keeps pedaling. Screenshot: `screenshots/coast.png`.

`prefers-reduced-motion` freezes the scroll and holds one pedal position.
