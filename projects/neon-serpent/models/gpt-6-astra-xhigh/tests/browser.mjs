import { chromium } from "@playwright/test";
import assert from "node:assert/strict";
import { mkdir } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { startServer } from "../serve.mjs";

const server = await startServer(0);
const origin = `http://127.0.0.1:${server.address().port}`;
const screenshots = fileURLToPath(new URL("../screenshots/", import.meta.url));
await mkdir(screenshots, { recursive: true });
const browser = await chromium.launch({
  args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"],
});
const errors = [],
  externalRequests = [];
const track = (page) => {
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  page.on("request", (request) => {
    if (!request.url().startsWith(origin) && !request.url().startsWith("data:"))
      externalRequests.push(request.url());
  });
};

try {
  const page = await browser.newPage({
    viewport: { width: 1440, height: 960 },
    deviceScaleFactor: 1,
  });
  track(page);
  await page.goto(origin);
  await page.waitForFunction(
    () => document.body.dataset.state === "intro",
    null,
    { timeout: 30000 },
  );
  await page.screenshot({ path: `${screenshots}/desktop-intro.png` });
  assert.equal(await page.locator("#start").isEnabled(), true);
  await page.getByRole("button", { name: "Turn sound on" }).click();
  assert.equal(
    await page.locator("#sound").getAttribute("aria-pressed"),
    "true",
  );
  await page.getByRole("button", { name: "Turn sound off" }).click();
  await page.locator("#start").click();
  await page.waitForFunction(
    () => Number(document.getElementById("score").textContent) >= 100,
    null,
    { timeout: 20000 },
  );
  assert.ok(Number(await page.locator("#length").textContent()) >= 18);
  await page.screenshot({ path: `${screenshots}/desktop-run.png` });
  await page.keyboard.press("Escape");
  assert.equal(await page.locator("body").getAttribute("data-state"), "paused");
  const pausedScore = await page.locator("#score").textContent();
  const pausedMap = await page
    .locator("#map")
    .evaluate((canvas) => canvas.toDataURL());
  await page.waitForTimeout(350);
  assert.equal(await page.locator("#score").textContent(), pausedScore);
  assert.ok(
    (await page.locator("#map").evaluate((canvas) => canvas.toDataURL())) ===
      pausedMap,
    "Paused minimap must remain stationary",
  );
  await page.keyboard.press("Tab");
  assert.equal(
    await page
      .locator("#restart")
      .evaluate((element) => element === document.activeElement),
    true,
  );
  await page.keyboard.press("Tab");
  assert.equal(
    await page
      .locator("#resume")
      .evaluate((element) => element === document.activeElement),
    true,
  );
  await page.locator("#resume").click();
  await page.keyboard.down("KeyW");
  await page.waitForFunction(
    () => Number(document.getElementById("speed").textContent) > 40,
  );
  await page.keyboard.up("KeyW");
  await page.keyboard.down("ArrowRight");
  await page.waitForFunction(
    () => document.body.dataset.state === "over",
    null,
    { timeout: 20000 },
  );
  await page.keyboard.up("ArrowRight");
  assert.match(await page.locator("#modal-kicker").textContent(), /COLLISION/);
  await page.screenshot({ path: `${screenshots}/desktop-game-over.png` });
  await page.keyboard.press("Enter");
  assert.equal(
    await page.locator("body").getAttribute("data-state"),
    "playing",
  );
  assert.equal(await page.locator("#score").textContent(), "000000");
  await page.evaluate(() => window.dispatchEvent(new Event("blur")));
  assert.equal(await page.locator("body").getAttribute("data-state"), "paused");
  await page.close();
  console.log("PASS: desktop gameplay, audio, pause and restart");

  const mobile = await browser.newPage({
    viewport: { width: 390, height: 844 },
    deviceScaleFactor: 1,
    isMobile: true,
    hasTouch: true,
    reducedMotion: "reduce",
  });
  track(mobile);
  await mobile.goto(origin);
  await mobile.waitForFunction(() => document.body.dataset.state === "intro");
  await mobile.screenshot({ path: `${screenshots}/mobile-intro.png` });
  assert.equal(
    await mobile.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
    true,
  );
  await mobile.locator("#start").tap();
  assert.equal(await mobile.locator("#touch-controls").isVisible(), true);
  const touchSession = await mobile.context().newCDPSession(mobile);
  const boostButton = await mobile
    .locator('[data-control="boost"]')
    .boundingBox();
  await touchSession.send("Input.dispatchTouchEvent", {
    type: "touchStart",
    touchPoints: [
      {
        x: boostButton.x + boostButton.width / 2,
        y: boostButton.y + boostButton.height / 2,
      },
    ],
  });
  await mobile.waitForFunction(
    () => Number(document.getElementById("speed").textContent) > 40,
  );
  await touchSession.send("Input.dispatchTouchEvent", {
    type: "touchEnd",
    touchPoints: [],
  });
  await mobile.waitForFunction(
    () => Number(document.getElementById("speed").textContent) < 35,
  );
  await mobile.screenshot({ path: `${screenshots}/mobile-run.png` });
  await mobile.locator("#pause").tap();
  assert.equal(
    await mobile.locator("body").getAttribute("data-state"),
    "paused",
  );
  await mobile.close();
  console.log("PASS: mobile layout and touch boost");

  // Same opaque-origin iframe policy used by the Variora preview.
  const host = await browser.newPage({
    viewport: { width: 1280, height: 800 },
  });
  track(host);
  await host.route(`${origin}/`, (route) =>
    route.fulfill({
      contentType: "text/html",
      body: `<html><body style="margin:0"><iframe sandbox="allow-scripts allow-pointer-lock" src="${origin}/index.html" style="width:100vw;height:100vh;border:0"></iframe></body></html>`,
    }),
  );
  await host.goto(origin);
  const preview = host.frameLocator("iframe");
  await preview.locator('body[data-state="intro"]').waitFor({ timeout: 30000 });
  await preview.locator("#start").click();
  await preview.locator('body[data-state="playing"]').waitFor();
  await preview.locator("#pause").click();
  await preview.locator('body[data-state="paused"]').waitFor();
  await host.close();
  console.log("PASS: opaque-origin sandboxed iframe");

  const standalone = await browser.newPage({
    viewport: { width: 960, height: 720 },
  });
  standalone.on("pageerror", (error) => errors.push(error.message));
  await standalone.goto(new URL("../app/index.html", import.meta.url).href);
  await standalone.waitForFunction(
    () => document.body.dataset.state === "intro",
  );
  await standalone.keyboard.press("Enter");
  assert.equal(
    await standalone.locator("body").getAttribute("data-state"),
    "playing",
  );
  await standalone.close();

  const fallback = await browser.newPage();
  await fallback.addInitScript(() => {
    const original = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function (type, ...args) {
      return type.startsWith("webgl")
        ? null
        : original.call(this, type, ...args);
    };
  });
  await fallback.goto(origin);
  await fallback.waitForFunction(() => document.body.dataset.state === "error");
  assert.match(
    await fallback.locator("#start").textContent(),
    /RELOAD CITY\s*↗/,
  );
  await fallback.close();
  assert.deepEqual(errors, [], `Browser errors: ${errors.join("\n")}`);
  assert.deepEqual(externalRequests, []);
  console.log(
    "PASS: desktop controls, collection/growth, boost, collision/restart, pause/focus, audio, touch, responsive layout, sandboxed iframe, direct file opening, WebGL fallback, no external requests or unexpected browser errors.",
  );
} finally {
  await browser.close();
  await new Promise((resolve) => server.close(resolve));
}
