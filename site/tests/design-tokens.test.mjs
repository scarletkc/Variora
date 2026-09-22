// Guards the UI design system: chrome styles in globals.css must use the
// shared scales defined in :root. Artwork scenes live in artwork.css and are
// intentionally exempt (they are content illustrations, not interface).
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const css = readFileSync(
  new URL("../app/globals.css", import.meta.url),
  "utf8",
);

const RADIUS_TOKENS = new Set([
  "var(--radius-sm)",
  "var(--radius-md)",
  "var(--radius-lg)",
  "50%",
  "0",
]);

test("border radii come from the shared scale", () => {
  const offenders = [];
  for (const match of css.matchAll(/border-radius:\s*([^;]+);/g)) {
    const value = match[1].trim();
    if (!RADIUS_TOKENS.has(value)) offenders.push(value);
  }
  assert.deepEqual(
    offenders,
    [],
    `Use --radius-sm/md/lg (4/6/8px) instead of: ${offenders.join(", ")}`,
  );
});

const FONT_SCALE = new Set([
  "10",
  "11",
  "12",
  "13",
  "14",
  "15",
  "18",
  "20",
  "22",
  "27",
  "28",
  "32",
  "34",
  "36",
  "40",
  "42",
  "52",
]);

test("font sizes come from the shared scale", () => {
  const offenders = [];
  for (const match of css.matchAll(/font-size:\s*([^;]+);/g)) {
    for (const size of match[1].matchAll(/([\d.]+)px/g)) {
      if (!FONT_SCALE.has(size[1])) offenders.push(`${size[1]}px`);
    }
  }
  assert.deepEqual(
    offenders,
    [],
    `Pick a size from the existing scale instead of: ${offenders.join(", ")}`,
  );
});

test("hover states change color, not position (card art may lift)", () => {
  const offenders = [];
  for (const match of css.matchAll(/([^{}]+):hover[^{}]*\{([^}]*)\}/g)) {
    if (
      match[2].includes("transform") &&
      !match[1].includes("project-art-link")
    )
      offenders.push(match[1].trim());
  }
  assert.deepEqual(
    offenders,
    [],
    `Hover should not move controls; offending selectors: ${offenders.join(", ")}`,
  );
});
