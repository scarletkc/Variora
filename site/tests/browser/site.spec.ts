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
    await expect(page).toHaveTitle("Neon Serpent - Variora");
    await page.reload();
    await expect(page.locator("h1")).toHaveText("Neon Serpent");
    await expect(page).toHaveTitle("Neon Serpent - Variora");
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
  await expect(page).toHaveTitle("E2E fixture - Rainy Ramen - Variora");
  await page.getByLabel("言語").click();
  await page.getByRole("option", { name: "한국어" }).click();
  await expect(page).toHaveURL(
    /\/ko\/preview\/\?project=rainy-ramen&model=e2e-fixture/,
  );
  await expect(page.locator("h1")).toHaveText("E2E fixture");
  await expect(page).toHaveTitle("E2E fixture - Rainy Ramen - Variora");
  await page.goto("/");
  await expect(page).toHaveURL(/\/ko\/$/);
});

test("invalid previews show a recoverable empty state", async ({ page }) => {
  await page.goto("/en/preview/?project=missing&model=missing");
  await expect(page).toHaveTitle("Implementation preview - Variora");
  await expect(page.locator("iframe")).toHaveCount(0);
  await expect(
    page.getByRole("heading", { name: "This preview is unavailable." }),
  ).toBeVisible();
  await page
    .getByRole("link", { name: "Explore Variora", exact: true })
    .click();
  await expect(page).toHaveURL(/\/en\/$/);
});

test("404 matches the entry layout and returns to the preferred language", async ({
  page,
}) => {
  await page.addInitScript(() =>
    Object.defineProperty(navigator, "languages", { value: ["ja-JP"] }),
  );
  await page.goto("/");
  await expect(page).toHaveURL(/\/ja\/$/);
  await page.evaluate(() => localStorage.setItem("variora-theme", "dark"));
  const response = await page.goto("/missing-page/");
  expect(response?.status()).toBe(404);
  await expect(page).toHaveTitle("Page not found - Variora");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await expect(page.locator(".entry-page h1")).toHaveText("Variora");
  await expect(page.locator(".entry-message")).toHaveText(
    "404 - Page not found.",
  );
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.evaluate(() => localStorage.setItem("variora-locale", "zh"));
  await page.getByRole("link", { name: "Explore Variora" }).click();
  await expect(page).toHaveURL(/\/zh\/$/);
});
