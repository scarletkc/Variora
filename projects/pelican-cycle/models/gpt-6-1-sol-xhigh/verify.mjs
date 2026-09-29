import assert from "node:assert/strict";
import { chromium } from "@playwright/test";

const url =
  process.argv[2] ?? new URL("./app/index.html", import.meta.url).href;
const browser = await chromium.launch();
const problems = [];
const snapshot = (page) =>
  page.evaluate(() =>
    [
      "front-spokes",
      "rear-spokes",
      "cranks",
      "front-leg",
      "rear-leg",
      "front-foot",
      "rear-foot",
      "pelican",
      "scarf-tail",
      "scarf-tip",
      "path-marks",
      "ripples",
      "clouds",
      "sailboat",
      "breeze",
    ].map((id) => {
      const element = document.getElementById(id);
      return [
        id,
        element.getAttribute("d"),
        element.getAttribute("transform"),
        element.getAttribute("x"),
      ];
    }),
  );
const state = (page) => page.locator("#postcard").getAttribute("data-state");
const observe = (page) => {
  page.on("pageerror", (error) => problems.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") problems.push(message.text());
  });
  page.on("requestfailed", (request) => problems.push(request.url()));
};

try {
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1000 },
  });
  observe(page);
  await page.clock.install({ time: new Date("2026-09-30T12:00:00Z") });
  await page.goto(url);
  await page.clock.pauseAt(new Date("2026-09-30T12:00:02Z"));
  assert.equal(await page.title(), "The scenic route — Pelican Cycle");
  assert.equal(await state(page), "running");
  assert.equal(await page.getByRole("img").count(), 1);
  const before = await snapshot(page);
  await page.clock.runFor(200);
  assert.notDeepEqual(await snapshot(page), before);
  console.log("PASS: page loads and animation advances");

  await page.getByRole("button", { name: "Pause animation" }).click();
  assert.equal(await state(page), "paused");
  const still = await snapshot(page);
  await page.clock.runFor(250);
  assert.deepEqual(await snapshot(page), still);
  await page.getByRole("button", { name: "Breezy", exact: true }).click();
  assert.equal(await state(page), "paused");
  assert.equal(
    await page
      .getByRole("button", { name: "Breezy", exact: true })
      .getAttribute("aria-pressed"),
    "true",
  );
  assert.deepEqual(await snapshot(page), still);
  await page.getByRole("button", { name: "Play animation" }).click();
  await page.clock.runFor(100);
  assert.notDeepEqual(await snapshot(page), still);
  console.log(
    "PASS: pause freezes every animated part, pace changes do not resume playback",
  );

  for (const [name, speed] of [
    ["Easy", 0.65],
    ["Cruise", 1],
    ["Breezy", 1.5],
  ]) {
    await page.getByRole("button", { name, exact: true }).click();
    const angle = () =>
      page.evaluate(() => ({
        degrees: Number(
          document
            .getElementById("cranks")
            .getAttribute("transform")
            .match(/rotate\(([^)]+)\)/)[1],
        ),
        now: performance.now(),
      }));
    const first = await angle();
    await page.clock.runFor(300);
    const second = await angle();
    const actual = (second.degrees - first.degrees + 360) % 360;
    const expected = ((second.now - first.now) / 1000) * 150 * speed;
    assert.ok(
      Math.abs(actual - expected) < expected * 0.25,
      `${name}: ${actual} vs ${expected}`,
    );
    assert.equal(await page.locator('.paces [aria-pressed="true"]').count(), 1);
  }
  console.log("PASS: all three paces produce their expected crank speeds");

  const geometry = await page.evaluate(() => {
    const degrees = Number(
      document
        .getElementById("cranks")
        .getAttribute("transform")
        .match(/rotate\(([^)]+)\)/)[1],
    );
    const point = (id) =>
      document.getElementById(id).transform.baseVal.consolidate().matrix;
    const front = point("front-foot");
    const rear = point("rear-foot");
    return {
      front: [front.e, front.f],
      rear: [rear.e, rear.f],
      degrees,
      invalid: [...document.querySelectorAll("path")].some(
        (path) =>
          !Number.isFinite(path.getTotalLength()) ||
          /NaN|Infinity/.test(path.getAttribute("d")),
      ),
      duplicateIds:
        [...document.querySelectorAll("[id]")].length !==
        new Set(
          [...document.querySelectorAll("[id]")].map((element) => element.id),
        ).size,
      danglingReferences: [...document.querySelectorAll("use")].some(
        (element) => !document.querySelector(element.getAttribute("href")),
      ),
    };
  });
  const phase = (geometry.degrees * Math.PI) / 180;
  assert.ok(Math.abs(geometry.front[0] - 590 - Math.cos(phase) * 24) < 0.001);
  assert.ok(Math.abs(geometry.front[1] - 488 - Math.sin(phase) * 24) < 0.001);
  assert.ok(Math.abs(geometry.front[0] + geometry.rear[0] - 1180) < 0.001);
  assert.ok(Math.abs(geometry.front[1] + geometry.rear[1] - 976) < 0.001);
  assert.equal(geometry.invalid, false);
  assert.equal(geometry.duplicateIds, false);
  assert.equal(geometry.danglingReferences, false);
  console.log(
    "PASS: feet stay on opposing pedals, SVG paths and references are valid",
  );

  await page.locator("h1").click();
  await page.keyboard.press("Space");
  assert.equal(await state(page), "paused");
  await page.keyboard.press("Space");
  assert.equal(await state(page), "running");
  await page.getByRole("button", { name: "Pause animation" }).focus();
  await page.keyboard.press("Space");
  assert.equal(await state(page), "paused");
  console.log(
    "PASS: page and focused-button keyboard controls do not double-toggle",
  );

  for (const width of [320, 390, 640, 768, 1024, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    assert.equal(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
      true,
      `Overflow at ${width}px`,
    );
    const stage = await page.locator(".stage").boundingBox();
    const bird = await page.evaluate(() => {
      const group = document.getElementById("bicycle");
      const box = group.getBBox();
      const matrix = group.getScreenCTM();
      return [
        new DOMPoint(box.x, box.y).matrixTransform(matrix).x,
        new DOMPoint(box.x + box.width, box.y).matrixTransform(matrix).x,
      ];
    });
    assert.ok(
      bird[0] >= stage.x - 1 && bird[1] <= stage.x + stage.width + 1,
      `Cyclist cropped at ${width}px`,
    );
  }
  console.log(
    "PASS: six viewport widths, no horizontal overflow or cropped cyclist",
  );

  const reduced = await browser.newPage({ reducedMotion: "reduce" });
  observe(reduced);
  await reduced.clock.install({ time: new Date("2026-09-30T12:00:00Z") });
  await reduced.goto(url);
  await reduced.clock.pauseAt(new Date("2026-09-30T12:00:02Z"));
  assert.equal(await state(reduced), "paused");
  assert.equal(await reduced.locator("#motion-note").isVisible(), true);
  const reducedStill = await snapshot(reduced);
  await reduced.clock.runFor(200);
  assert.deepEqual(await snapshot(reduced), reducedStill);
  await reduced.getByRole("button", { name: "Play animation" }).click();
  await reduced.clock.runFor(100);
  assert.equal(await state(reduced), "running");
  assert.notDeepEqual(await snapshot(reduced), reducedStill);
  for (const preference of ["no-preference", "reduce"]) {
    await reduced.evaluate(() => {
      window.preferenceChanged = new Promise((resolve) => {
        matchMedia("(prefers-reduced-motion: reduce)").addEventListener(
          "change",
          (event) => resolve(event.matches),
          { once: true },
        );
      });
    });
    await reduced.emulateMedia({ reducedMotion: preference });
    await reduced.clock.runFor(48);
    assert.equal(
      await reduced.evaluate(() => window.preferenceChanged),
      preference === "reduce",
    );
  }
  assert.equal(await state(reduced), "paused");
  console.log(
    "PASS: reduced motion starts still, permits explicit play, responds to preference changes",
  );

  const noScript = await browser.newPage({ javaScriptEnabled: false });
  observe(noScript);
  await noScript.goto(url);
  assert.equal(await noScript.locator("noscript").isVisible(), true);
  assert.equal(await noScript.locator("button:enabled").count(), 0);
  assert.match(
    (await noScript.locator("#front-foot").getAttribute("transform")) ?? "",
    /translate\(/,
  );
  assert.match(
    (await noScript.locator("#rear-foot").getAttribute("transform")) ?? "",
    /translate\(/,
  );
  console.log(
    "PASS: JavaScript-disabled page preserves the complete still illustration",
  );

  if (url.startsWith("http")) {
    await page.setContent(
      `<iframe title="Sandbox check" sandbox="allow-scripts" src="${url}"></iframe>`,
    );
    const preview = page.frameLocator("iframe");
    await preview.getByRole("button", { name: "Pause animation" }).click();
    assert.equal(
      await preview.locator("#postcard").getAttribute("data-state"),
      "paused",
    );
    await preview.getByRole("button", { name: "Play animation" }).click();
    assert.equal(
      await preview.locator("#postcard").getAttribute("data-state"),
      "running",
    );
    console.log(
      "PASS: opaque-origin sandbox preview supports animation and playback controls",
    );
  }

  assert.deepEqual(problems, []);
  console.log("PASS: no browser errors or failed requests");
} finally {
  await browser.close();
}
