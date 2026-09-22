import { createServer, type Server } from "node:http";
import { test, expect, type Page } from "@playwright/test";

const preview = "/en/preview/?project=rainy-ramen&model=e2e-fixture";
const assets = "/previews/rainy-ramen/e2e-fixture";

let controls: string;
let server: Server;

test.beforeAll(async ({ baseURL }) => {
  // Playwright's route.fulfill() adds CORS headers, so denial cases need real HTTP.
  server = createServer(async (request, response) => {
    const match = request.url?.match(
      /^\/(none|entry-only|mime)\/(index\.html|main\.js|counter\.mjs|classic\.html|classic\.js)$/,
    );
    if (!match) {
      response.writeHead(404).end();
      return;
    }
    const [, mode, file] = match;
    try {
      const upstream = await fetch(new URL(`${assets}/${file}`, baseURL));
      const body = Buffer.from(await upstream.arrayBuffer());
      response.setHeader("Cache-Control", "no-store");
      response.setHeader(
        "Content-Type",
        mode === "mime" && file === "counter.mjs"
          ? "text/html"
          : upstream.headers.get("content-type")!,
      );
      if (mode === "mime" || (mode === "entry-only" && file === "main.js"))
        response.setHeader("Access-Control-Allow-Origin", "*");
      response.writeHead(upstream.status).end(body);
    } catch {
      response.writeHead(502).end();
    }
  });
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  const address = server.address();
  if (!address || typeof address === "string")
    throw new Error("Missing test port");
  controls = `http://127.0.0.1:${address.port}`;
});

test.afterAll(async () => {
  server?.closeAllConnections();
  if (server)
    await new Promise<void>((resolve) => server.close(() => resolve()));
});

async function openControl(page: Page, file: string) {
  await page.locator("iframe").evaluate((frame, src) => {
    (frame as HTMLIFrameElement).src = src;
  }, `${controls}/${file}`);
}

test("module entries and relative .mjs imports run with parent isolation", async ({
  page,
}) => {
  const loaded = Promise.all(
    ["main.js", "counter.mjs"].map((file) =>
      page.waitForResponse((response) =>
        response.url().endsWith(`${assets}/${file}`),
      ),
    ),
  );
  await page.goto(preview);
  for (const response of await loaded) {
    expect(response.status()).toBe(200);
    expect(response.headers()["access-control-allow-origin"]).toBe("*");
    expect(response.headers()["content-type"]).toMatch(
      /^(?:text|application)\/javascript(?:;|$)/,
    );
    expect((await response.request().allHeaders()).origin).toBe("null");
  }
  await expect(page).toHaveTitle("E2E fixture - Rainy Ramen - Variora");
  await expect(page.locator("iframe")).toHaveAttribute(
    "sandbox",
    "allow-scripts allow-pointer-lock",
  );
  const frame = page.frameLocator("iframe");
  await expect(frame.getByText("Parent isolated")).toBeVisible();
  await frame.getByRole("button", { name: "Count: 0" }).click();
  await expect(frame.getByRole("button")).toHaveText("Count: 1");
  await page.getByRole("button", { name: "Reload" }).click();
  await expect(frame.getByRole("button")).toHaveText("Count: 0");
  await page.getByRole("button", { name: "Full screen", exact: false }).click();
  await expect(
    page.getByRole("button", { name: "Exit full screen", exact: false }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Exit full screen", exact: false })
    .click();
  await page.getByRole("link", { name: "Back to project" }).click();
  await expect(page.locator("h1")).toHaveText("Rainy Ramen");
  await expect(page).toHaveTitle("Rainy Ramen - Variora");
});

test("direct navigation runs the module graph without CORS headers", async ({
  page,
}) => {
  await page.goto(`${controls}/none/index.html`);
  await page.getByRole("button", { name: "Count: 0" }).click();
  await expect(page.getByRole("button")).toHaveText("Count: 1");
});

for (const { name, mode, blocked } of [
  {
    name: "the whole module graph lacks CORS headers",
    mode: "none",
    blocked: "main.js",
  },
  {
    name: "only the entry has CORS headers",
    mode: "entry-only",
    blocked: "counter.mjs",
  },
]) {
  test(`sandbox blocks execution when ${name}`, async ({ page }) => {
    await page.goto(preview);
    const requested: string[] = [];
    page.on("request", (request) => requested.push(request.url()));
    const failure = page.waitForEvent(
      "console",
      (message) =>
        message.text().includes(`${controls}/${mode}/${blocked}`) &&
        message.text().includes("CORS policy"),
    );
    await openControl(page, `${mode}/index.html`);
    await failure;
    await expect(page.frameLocator("iframe").locator("#isolation")).toBeEmpty();
    expect(requested.includes(`${controls}/${mode}/counter.mjs`)).toBe(
      blocked === "counter.mjs",
    );
  });
}

test("sandbox rejects a dependency with a non-JavaScript MIME type", async ({
  page,
}) => {
  await page.goto(preview);
  const failure = page.waitForEvent(
    "console",
    (message) =>
      message.text().includes("MIME type") &&
      message.text().includes("text/html"),
  );
  await openControl(page, "mime/index.html");
  await failure;
  await expect(page.frameLocator("iframe").locator("#isolation")).toBeEmpty();
});

test("self-contained classic scripts run in the sandbox without CORS headers", async ({
  page,
}) => {
  await page.goto(preview);
  await openControl(page, "none/classic.html");
  await expect(page.frameLocator("iframe").locator("#ready")).toHaveText(
    "Ready",
  );
});
