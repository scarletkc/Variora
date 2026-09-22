import { test, expect } from "@playwright/test";
import catalog from "../../.generated/catalog.json";

for (const [locale, heading, lang] of [
  ["en", "Projects", "en"],
  ["zh", "项目", "zh-Hans"],
  ["ja", "プロジェクト", "ja"],
  ["ko", "프로젝트", "ko"],
]) {
  test(`${locale} renders localized static pages without overflow`, async ({
    page,
  }) => {
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await page.goto(`/${locale}/`);
    await expect(page.locator("html")).toHaveAttribute("lang", lang);
    await expect(page.locator("h1")).toContainText(heading);
    await expect(page.locator(".project-card")).toHaveCount(catalog.length);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await page.locator('.project-art-link[href$="/neon-serpent/"]').click();
    await expect(page.locator("h1")).toHaveText("Neon Serpent");
    await page.reload();
    await expect(page.locator("h1")).toHaveText("Neon Serpent");
    expect(errors).toEqual([]);
  });
}

test("filters, search, and reset work", async ({ page }) => {
  await page.goto("/en/");
  await page.getByRole("button", { name: "Illustration", exact: true }).click();
  await expect(page.locator(".project-card")).toHaveCount(
    catalog.filter((project) => project.category === "illustration").length,
  );
  await expect(
    page.getByRole("heading", { name: "Rainy Ramen", exact: true }),
  ).toBeVisible();
  await page.getByRole("searchbox").fill("no-such-project");
  await expect(page.getByRole("status")).toContainText("No projects match");
  await page.getByRole("button", { name: "Clear filters" }).click();
  await expect(page.locator(".project-card")).toHaveCount(catalog.length);
});

test("theme follows the system and persists an explicit preference", async ({
  page,
}) => {
  await page.emulateMedia({ colorScheme: "dark" });
  await page.goto("/en/");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.getByLabel("Appearance").click();
  await page.getByRole("option", { name: "Light" }).click();
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await page.getByLabel("Appearance").click();
  await page.getByRole("option", { name: "System" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.emulateMedia({ colorScheme: "light" });
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
});

test("language switching preserves project and preview selection", async ({
  page,
}) => {
  await page.goto("/en/projects/rainy-ramen/");
  await page.getByLabel("Language").click();
  await page.getByRole("option", { name: "日本語" }).click();
  await expect(page).toHaveURL(/\/ja\/projects\/rainy-ramen\//);
  await page
    .locator(".model-card")
    .filter({ hasText: "E2E fixture" })
    .getByRole("link", { name: "プレビューを開く", exact: true })
    .click();
  await page.getByLabel("言語").click();
  await page.getByRole("option", { name: "한국어" }).click();
  await expect(page).toHaveURL(
    /\/ko\/preview\/\?project=rainy-ramen&model=e2e-fixture/,
  );
  await expect(page.locator("h1")).toHaveText("E2E fixture");
  await page.goto("/");
  await expect(page).toHaveURL(/\/ko\/$/);
});

test("previews run module scripts, isolate parent access, and reload", async ({
  page,
}) => {
  await page.goto("/en/preview/?project=rainy-ramen&model=e2e-fixture");
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
});

test("invalid previews show a recoverable empty state", async ({ page }) => {
  await page.goto("/en/preview/?project=missing&model=missing");
  await expect(page.locator("iframe")).toHaveCount(0);
  await expect(
    page.getByRole("heading", { name: "This preview is unavailable." }),
  ).toBeVisible();
  await page
    .getByRole("link", { name: "Explore Variora", exact: true })
    .click();
  await expect(page).toHaveURL(/\/en\/$/);
});

test("root selects browser language and 404 has working language links", async ({
  page,
}) => {
  await page.addInitScript(() =>
    Object.defineProperty(navigator, "languages", { value: ["ja-JP"] }),
  );
  await page.goto("/");
  await expect(page).toHaveURL(/\/ja\/$/);
  const response = await page.goto("/missing-page/");
  expect(response?.status()).toBe(404);
  await page.getByRole("link", { name: "中文" }).click();
  await expect(page).toHaveURL(/\/zh\/$/);
});
