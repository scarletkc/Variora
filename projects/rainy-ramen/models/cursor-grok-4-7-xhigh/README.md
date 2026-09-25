# cursor-grok-4-7-xhigh

| Field | Value |
| --- | --- |
| Model | cursor-grok-4-7-xhigh |
| Reasoning effort | unknown |
| Provider | unknown |
| Harness | Cursor (version unknown) |

## Assistance used

- Skills: frontend-design (local skill, version unknown) for palette, type, and layout. motion (local skill, version unknown) for keeping the rain loop on simple attribute updates and for pausing motion when requested.
- Tools and plugins: Cursor's browser, to view the page, start the rain, and save a screenshot.
- Subagents: none

## Run

Open `app/index.html` in a browser. The picture scales with the window. Choose Play rain to start a synthesized shower and a low hum. Choose Stop rain to fade them out. Nothing is loaded from another server.

## Notes

One HTML file. The shop, cat, robot, bowl, and clear umbrella are inline SVG. Rain is redrawn in SVG coordinates so it stays aligned as the page scales. Steam, the cat's tail, and the puddle rings are SVG animations. The sign flickers with CSS.

Play rain builds a looping noise buffer, sends it through a band-pass filter, and adds two quiet sine tones. The button is the only control, because browsers block audio until a gesture.

`prefers-reduced-motion` stops the rain movement and the SVG animations. The still picture stays.

Checked in Cursor's browser at a desktop width: the cat, bowl, robot, and umbrella read as one handoff, rain moves, and Play rain changes the button to Stop rain. Screenshot: `screenshots/scene.png`.
