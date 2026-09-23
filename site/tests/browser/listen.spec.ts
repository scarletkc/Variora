import type { Page } from "@playwright/test";
import { test, expect } from "./fixtures/giscus";
import catalog from "../../.generated/catalog.json";

const listen = (model: string, locale = "en") =>
  `/${locale}/listen/?project=e2e-music&model=${model}`;
const paused = (page: Page) =>
  page.locator("audio").evaluate((audio: HTMLAudioElement) => audio.paused);
const loaded = (page: Page) =>
  expect(page.locator(".player-seek input")).toBeEnabled();

test("music outputs are listed in their category with output types", async ({
  page,
}) => {
  await page.goto("/en/");
  await page.getByRole("button", { name: "Music", exact: true }).click();
  await expect(page.locator(".project-card")).toHaveCount(
    catalog.filter((project) => project.category === "music").length,
  );
  await page.getByRole("link", { name: "Music fixture", exact: true }).click();
  await expect(page.locator(".project-intro .eyebrow")).toHaveText("Music");
  const card = page.locator(".model-card").filter({ hasText: "Tone A" });
  await expect(card.locator("dd").first()).toHaveText(
    "Audio (WAV) · MIDI · Source code",
  );
  await expect(
    page
      .locator(".model-card")
      .filter({ hasText: "MIDI only" })
      .locator("dd")
      .first(),
  ).toHaveText("MIDI");
  await card.getByRole("link", { name: "Listen", exact: true }).click();
  await expect(page).toHaveTitle("Tone A - Music fixture - Variora");
  await expect(page.locator("h1")).toHaveText("Tone A");
});

test("playback waits for the visitor, switches without overlap, and stops on leave", async ({
  page,
}) => {
  await page.goto(listen("tone-a"));
  await loaded(page);
  await page.waitForTimeout(300);
  expect(await paused(page)).toBe(true);
  await page.getByRole("button", { name: "Play", exact: true }).click();
  await expect.poll(() => paused(page)).toBe(false);
  await expect(page.getByRole("button", { name: "Pause" })).toBeVisible();
  const first = await page.locator("audio").elementHandle();

  const switcher = page.getByRole("navigation", {
    name: "Outputs for this prompt",
  });
  await expect(switcher.getByRole("link")).toHaveCount(4);
  await expect(
    switcher.locator('[aria-current="page"] .switcher-name'),
  ).toHaveText("Tone A");
  await switcher.getByRole("link", { name: /Tone B/ }).click();
  await expect(page).toHaveURL(/model=tone-b/);
  await expect(page.locator("h1")).toHaveText("Tone B");
  expect(await first!.evaluate((audio: HTMLAudioElement) => audio.paused)).toBe(
    true,
  );
  await expect(page.locator("audio")).toHaveCount(1);
  await expect(page.locator("audio")).toHaveAttribute(
    "src",
    /\/render\/tone-b\.wav$/,
  );
  await expect.poll(() => paused(page)).toBe(false);
  const second = await page.locator("audio").elementHandle();

  await page.getByRole("button", { name: "Pause" }).click();
  await expect.poll(() => paused(page)).toBe(true);
  await switcher.getByRole("link", { name: /Tone A/ }).click();
  await expect(page.locator("h1")).toHaveText("Tone A");
  await page.waitForTimeout(300);
  expect(await paused(page)).toBe(true);

  await page.getByRole("button", { name: "Play", exact: true }).click();
  await expect.poll(() => paused(page)).toBe(false);
  const third = await page.locator("audio").elementHandle();
  await page.getByRole("link", { name: "Back to project" }).click();
  await expect(page.locator("h1")).toHaveText("Music fixture");
  await expect(page.locator("audio")).toHaveCount(0);
  for (const audio of [second, third])
    expect(await audio!.evaluate((item: HTMLAudioElement) => item.paused)).toBe(
      true,
    );
});

test("seeking, restart, volume, and keyboard controls drive the audio", async ({
  page,
}) => {
  await page.goto(listen("tone-a"));
  await loaded(page);
  const seek = page.getByRole("slider", { name: "Playback position" });
  const time = () =>
    page
      .locator("audio")
      .evaluate((audio: HTMLAudioElement) => audio.currentTime);
  await expect(page.locator(".player-time").last()).toHaveText("0:12");
  await seek.focus();
  await page.keyboard.press("ArrowRight");
  await page.keyboard.press("ArrowRight");
  await expect.poll(time).toBeCloseTo(10, 0);
  await expect(seek).toHaveAttribute("aria-valuetext", "0:10 of 0:12");
  await page.keyboard.press("Home");
  await expect.poll(time).toBe(0);
  await page.keyboard.press("PageUp");
  await expect.poll(time).toBeCloseTo(12, 0);
  await page.keyboard.press("Home");
  await page.keyboard.press("k");
  await expect.poll(() => paused(page)).toBe(false);
  await page.keyboard.press(" ");
  await expect.poll(() => paused(page)).toBe(true);
  await seek.fill("6");
  await expect.poll(time).toBeCloseTo(6, 0);

  await page.getByRole("button", { name: "Restart" }).click();
  await expect.poll(() => paused(page)).toBe(false);
  expect(await time()).toBeLessThan(3);
  await page.getByRole("button", { name: "Pause" }).click();

  const volume = page.getByRole("slider", { name: "Volume" });
  await volume.fill("0.4");
  await expect
    .poll(() =>
      page.locator("audio").evaluate((audio: HTMLAudioElement) => audio.volume),
    )
    .toBeCloseTo(0.4);
  await expect(volume).toHaveAttribute("aria-valuetext", "40%");
  await page.getByRole("button", { name: "Mute" }).click();
  await expect(page.getByRole("button", { name: "Unmute" })).toBeVisible();
  expect(
    await page
      .locator("audio")
      .evaluate((audio: HTMLAudioElement) => audio.muted),
  ).toBe(true);
  await page
    .getByRole("navigation", { name: "Outputs for this prompt" })
    .getByRole("link", { name: /Tone B/ })
    .click();
  await expect(page.locator("h1")).toHaveText("Tone B");
  expect(
    await page
      .locator("audio")
      .evaluate((audio: HTMLAudioElement) => [audio.muted, audio.volume]),
  ).toEqual([true, 0.4]);
});

test("files, provenance, rendering, and MIDI details stay connected", async ({
  page,
}) => {
  await page.goto(listen("tone-a"));
  await expect(
    page.getByRole("link", { name: "Shared prompt" }),
  ).toHaveAttribute("href", /\/projects\/e2e-music\/PROMPT\.md$/);
  await expect(
    page.getByRole("link", { name: "Model record" }),
  ).toHaveAttribute("href", /\/projects\/e2e-music\/models\/tone-a$/);
  const files = page.locator(".file-list li");
  await expect(files).toHaveCount(3);
  await expect(files.nth(0)).toContainText("Audio · WAV");
  await expect(files.nth(0)).toContainText("From the model run");
  const audio = files.nth(0).getByRole("link", { name: "Download" });
  await expect(audio).toHaveAttribute("download", "tone-a.wav");
  const midi = files.nth(1).getByRole("link", { name: "Download" });
  await expect(midi).toHaveAttribute("download", "tone-a.mid");
  for (const link of [audio, midi]) {
    const response = await page.request.get((await link.getAttribute("href"))!);
    expect(response.status()).toBe(200);
  }
  await expect(files.nth(2).getByRole("link")).toHaveAttribute(
    "href",
    "https://github.com/scarletkc/variora/blob/main/projects/e2e-music/models/tone-a/app/compose.py",
  );
  await expect(page.locator(".listen-rendering")).toHaveText(
    "Rendered by a test sine generator.",
  );
  const facts = page.locator(".midi-facts");
  await expect(facts).toContainText("Length0:02");
  await expect(facts).toContainText("Tempo120 BPM");
  await expect(facts).toContainText("Notes4");
  await expect(facts).toContainText("InstrumentsAcoustic Grand Piano");
  await expect(
    page.getByRole("img", { name: "Piano roll from the MIDI file" }),
  ).toBeVisible();

  await page.goto(listen("tone-b"));
  await expect(page.locator(".file-list li").first()).toContainText(
    "Processed after the run",
  );
  await expect(page.locator(".listen-note")).toHaveText(
    "No generating source code was supplied. See the model record for details.",
  );
});

test("missing, broken, and unknown outputs explain what is available", async ({
  page,
}) => {
  await page.goto(listen("midi-only"));
  await expect(page.locator(".player-empty")).toContainText(
    "No playable audio was supplied for this output.",
  );
  await expect(page.locator(".player-empty")).toHaveAttribute("role", "status");
  await expect(page.locator("audio")).toHaveCount(0);
  await expect(
    page.locator(".file-list").getByRole("link", { name: "Download" }),
  ).toHaveAttribute("download", "theme.mid");

  await page.goto(listen("broken-audio"));
  await expect(page.locator(".player-message")).toHaveText(
    "This audio could not be loaded. Download the file or check the model record.",
  );
  await expect(page.locator(".player-message")).toHaveAttribute(
    "role",
    "alert",
  );
  await expect(page.getByRole("button", { name: "Play" })).toBeDisabled();
  await expect(page.locator(".file-list li")).toHaveCount(1);

  for (const url of [
    "/en/listen/?project=missing&model=missing",
    "/en/listen/?project=rainy-ramen&model=e2e-fixture",
  ]) {
    await page.goto(url);
    await expect(page).toHaveTitle("Listening - Variora");
    await expect(
      page.getByRole("heading", { name: "This output is unavailable." }),
    ).toBeVisible();
  }
});

for (const locale of ["en", "ja"]) {
  test(`${locale} listening view fits the viewport`, async ({ page }) => {
    await page.goto(listen("tone-a", locale));
    await loaded(page);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    if (locale === "ja")
      await expect(
        page.getByRole("button", { name: "再生", exact: true }),
      ).toBeVisible();
  });
}
