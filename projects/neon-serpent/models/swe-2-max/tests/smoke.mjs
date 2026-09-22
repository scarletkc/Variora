// Smoke test: boot the game headless, play it, collect an orb, die, restart.
// Saves screenshots into ../screenshots. Run: npm test
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";
import { serve } from "../serve.mjs";

const root = fileURLToPath(new URL("..", import.meta.url));
const shots = path.join(root, "screenshots");

const results = [];
const check = (name, ok, extra = "") => {
  results.push([name, ok]);
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${extra ? ` — ${extra}` : ""}`);
};

const server = await serve(0);
const port = server.address().port;
const browser = await chromium.launch({
  args: ["--enable-unsafe-swiftshader", "--disable-gpu-sandbox"],
});
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 810 } });
  const errors = [];
  page.on("pageerror", (e) => errors.push(`pageerror: ${e.message}`));
  page.on("console", (m) => {
    if (m.type() === "error") errors.push(`console: ${m.text()}`);
  });

  await page.goto(`http://localhost:${port}/`, { waitUntil: "load" });
  await page.waitForFunction(() => window.__NEON, null, { timeout: 15000 });
  await page.waitForTimeout(1200);
  check("boots to intro", await page.evaluate(() => __NEON.state === "intro"));
  check("webgl canvas rendering", await page.evaluate(() => {
    const gl = document.getElementById("gl");
    return gl.width > 0 && gl.height > 0;
  }));
  await page.screenshot({ path: path.join(shots, "01-intro.png") });

  await page.click("#start");
  check("start enters countdown", await page.evaluate(() => __NEON.state === "countdown"));
  await page.waitForFunction(() => __NEON.state === "playing", null, { timeout: 8000 });
  check("countdown reaches playing", true);

  const p0 = await page.evaluate(() => ({ x: __NEON.snake.pos.x, z: __NEON.snake.pos.z }));
  await page.waitForTimeout(1500);
  const p1 = await page.evaluate(() => ({ x: __NEON.snake.pos.x, z: __NEON.snake.pos.z }));
  check("snake moves", Math.hypot(p1.x - p0.x, p1.z - p0.z) > 5,
    `moved ${Math.hypot(p1.x - p0.x, p1.z - p0.z).toFixed(1)}u`);

  // Gameplay screenshot while still alive, driving down the avenue.
  check("still playing", await page.evaluate(() => __NEON.state === "playing"));
  await page.screenshot({ path: path.join(shots, "02-gameplay.png") });

  // Teleport next to a live orb and confirm the collection path works.
  const collected = await page.evaluate(async () => {
    const before = __NEON.score;
    const orb = __NEON.orbs.items.find((i) => i.alive);
    __NEON.teleport(orb.pos.x - 1, orb.pos.z);
    const t0 = performance.now();
    while (__NEON.score === before && performance.now() - t0 < 3000) {
      await new Promise((r) => requestAnimationFrame(r));
    }
    return __NEON.score > before;
  });
  check("orb collection scores", collected);

  // Autopilot for a few seconds to exercise steering and growth.
  // It ignores obstacles, so it may die — that's fine for this check.
  await page.evaluate(() => __NEON.setAuto(true));
  await page.waitForTimeout(3500);
  const st = await page.evaluate(() => __NEON.state);
  const grown = await page.evaluate(() => __NEON.snake.segments);
  check("autopilot ran", st === "playing" || st === "dying" || st === "dead",
    `state=${st} segments=${grown}`);
  await page.evaluate(() => __NEON.setAuto(false));
  if (st === "dying") {
    await page.waitForFunction(() => __NEON.state === "dead", null, { timeout: 5000 });
  }
  if (st !== "playing") {
    await page.click("#retry");
    await page.waitForFunction(() => __NEON.state === "playing", null, { timeout: 8000 });
  }

  await page.evaluate(() => __NEON.die("building"));
  await page.waitForFunction(() => __NEON.state === "dead", null, { timeout: 5000 });
  check("death reaches game over", true);
  await page.waitForTimeout(900);
  await page.screenshot({ path: path.join(shots, "03-gameover.png") });

  await page.click("#retry");
  await page.waitForFunction(() => __NEON.state === "playing", null, { timeout: 8000 });
  check("retry restarts", true);

  // file:// regression: classic bundle must boot with no server at all.
  const fileUrl = "file:///" + path.join(root, "app", "index.html").replace(/\\/g, "/");
  await page.goto(fileUrl, { waitUntil: "load" });
  await page.waitForFunction(() => window.__NEON, null, { timeout: 15000 });
  check("boots over file://", true);
  await page.click("#start");
  await page.waitForFunction(() => __NEON.state === "countdown", null, { timeout: 8000 });
  check("file:// start works", true);

  // Sandboxed iframe (site preview): opaque origin, localStorage throws.
  await page.goto(`http://localhost:${port}/tests/sandboxed.html`, { waitUntil: "load" });
  const frame = page.frames().find((f) => f.url().includes("/app/index.html"));
  check("sandboxed frame loaded", !!frame);
  if (frame) {
    await frame.waitForFunction(() => window.__NEON, null, { timeout: 15000 });
    check("boots in sandboxed iframe", true);
    await page.frameLocator("#f").locator("#start").click();
    await frame.waitForFunction(
      () => __NEON.state === "countdown" || __NEON.state === "playing",
      null, { timeout: 8000 },
    );
    check("sandboxed start works", true);
  }

  check("no console/page errors", errors.length === 0, errors.slice(0, 4).join(" | "));
} finally {
  await browser.close();
  server.close();
}

const failed = results.filter(([, ok]) => !ok);
console.log(`\n${results.length - failed.length}/${results.length} checks passed`);
process.exit(failed.length ? 1 : 0);
