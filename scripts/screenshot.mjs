// Capture a page in headless Chromium: a site URL, a local file, or a
// directory containing index.html. See CONTRIBUTING.md and
// site/docs/development.md for usage.
import { chromium } from "@playwright/test";
import { mkdir, stat } from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";

const usage = `Usage: node scripts/screenshot.mjs <url-or-file> <out.png> [options]

Options:
  --viewport WxH   Viewport size (default 1440x900)
  --dark|--light   Emulate prefers-color-scheme
  --full-page      Capture the full scrollable page
  --wait ms        Extra settle time after load and each click (default 2500)
  --click sel      Click a selector after load; repeatable, applied in order
  --strict         Exit 1 on console errors, page errors, or failed requests
  --help           Show this message
`;

function fail(message) {
  console.error(`screenshot: ${message}\n\n${usage}`);
  process.exit(2);
}

const args = process.argv.slice(2);
const positional = [];
const clicks = [];
let viewport = { width: 1440, height: 900 };
let colorScheme;
let fullPage = false;
let wait = 2500;
let strict = false;

for (let i = 0; i < args.length; i++) {
  const arg = args[i];
  const value = () => args[++i] ?? fail(`${arg} needs a value`);
  if (arg === "--help") {
    console.log(usage);
    process.exit(0);
  } else if (arg === "--viewport") {
    const match = value().match(/^(\d+)x(\d+)$/);
    if (!match) fail("--viewport must look like 1440x900");
    viewport = { width: Number(match[1]), height: Number(match[2]) };
  } else if (arg === "--dark" || arg === "--light") {
    colorScheme = arg.slice(2);
  } else if (arg === "--full-page") {
    fullPage = true;
  } else if (arg === "--wait") {
    wait = Number(value());
    if (!Number.isFinite(wait) || wait < 0) fail("--wait must be milliseconds");
  } else if (arg === "--click") {
    clicks.push(value());
  } else if (arg === "--strict") {
    strict = true;
  } else if (arg.startsWith("--")) {
    fail(`unknown option ${arg}`);
  } else {
    positional.push(arg);
  }
}

const [target, out] = positional;
if (!target || !out) fail("need a URL or file to capture and an output path");

let url = target;
if (!/^[a-z]+:\/\//i.test(target)) {
  let file = path.resolve(target);
  if ((await stat(file).catch(() => null))?.isDirectory())
    file = path.join(file, "index.html");
  if (!(await stat(file).catch(() => null))?.isFile())
    fail(`no such file or directory: ${target}`);
  url = pathToFileURL(file).href;
}
await mkdir(path.dirname(path.resolve(out)), { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({ viewport, colorScheme });
const problems = [];
page.on("pageerror", (error) => problems.push(`pageerror: ${error.message}`));
page.on("console", (message) => {
  if (message.type() === "error") problems.push(`console: ${message.text()}`);
});
page.on("requestfailed", (request) =>
  problems.push(`request failed: ${request.url()}`),
);

try {
  await page.goto(url);
  for (const selector of clicks) {
    await page.click(selector);
    await page.waitForTimeout(500);
  }
  await page.waitForTimeout(wait);
  await page.screenshot({ path: out, fullPage });
} finally {
  await browser.close();
}

for (const problem of problems) console.error(problem);
console.log(
  `${out} (${problems.length ? `${problems.length} problem(s)` : "clean"})`,
);
if (strict && problems.length) process.exit(1);
