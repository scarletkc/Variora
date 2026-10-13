// Optional browser acceptance: NODE_PATH must expose Playwright.
const { chromium } = require('playwright');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  page.setDefaultTimeout(15000);
  const problems = [];
  const abortedMediaRequests = [];
  page.on('pageerror', error => problems.push(error.message));
  page.on('requestfailed', request => {
    const detail = `${request.url()}: ${request.failure()?.errorText}`;
    if (request.url().endsWith('/sea_breeze.mp3') && request.failure()?.errorText === 'net::ERR_ABORTED') abortedMediaRequests.push(detail);
    else problems.push(detail);
  });
  await page.goto('http://127.0.0.1:8768/', { waitUntil: 'networkidle' });
  await page.waitForFunction(() => document.querySelector('audio').readyState >= 1);
  const before = await page.$eval('audio', element => ({ paused: element.paused, time: element.currentTime, duration: element.duration, src: element.currentSrc }));
  assert.equal(before.paused, true);
  assert.equal(before.time, 0);
  assert(before.duration > 170 && before.duration < 174);
  await page.$eval('audio', element => { element.muted = true; return element.play(); });
  await page.waitForFunction(() => document.querySelector('audio').currentTime > 1);
  const playing = await page.$eval('audio', element => ({ paused: element.paused, time: element.currentTime }));
  assert.equal(playing.paused, false);
  console.log('Metadata and playback passed.');
  await page.$eval('audio', element => { element.pause(); element.currentTime = 85; });
  await page.waitForFunction(() => Math.abs(document.querySelector('audio').currentTime - 85) < .1 && !document.querySelector('audio').seeking);
  await page.$eval('audio', element => element.play());
  await page.waitForFunction(() => document.querySelector('audio').currentTime > 86);
  console.log('Seek passed.');
  await page.$eval('audio', element => { element.pause(); element.currentTime = 0; element.muted = false; });
  const screenshotDir = path.join(__dirname, 'screenshots');
  fs.mkdirSync(screenshotDir, { recursive: true });
  await page.screenshot({ path: path.join(screenshotDir, 'desktop.png'), fullPage: true });
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: path.join(screenshotDir, 'mobile.png'), fullPage: true });
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
  // The published preview's opaque origin is materially different from a plain page.
  await page.goto('http://127.0.0.1:8768/', { waitUntil: 'domcontentloaded' });
  await page.setContent('<iframe title="preview" sandbox="allow-scripts" src="http://127.0.0.1:8768/"></iframe>');
  const frame = await page.waitForSelector('iframe');
  const content = await frame.contentFrame();
  await content.waitForFunction(() => document.querySelector('audio')?.readyState >= 1);
  const sandboxDuration = await content.$eval('audio', element => element.duration);
  assert(sandboxDuration > 170);
  await content.$eval('audio', element => { element.muted = true; return element.play(); });
  await content.waitForFunction(() => document.querySelector('audio').currentTime > .5);
  assert(await content.$eval('audio', element => element.error === null));
  assert.deepEqual(problems, []);
  fs.writeFileSync(path.join(__dirname, 'browser-verification.json'), JSON.stringify({ checks: 'passed', browser: `Chromium ${browser.version()}`, before, playing, seek: '85s -> playback advanced beyond 86s', screenshots: ['screenshots/desktop.png', 'screenshots/mobile.png'], layouts: ['1440x1000', '390x844'], horizontalOverflow: false, sandboxedPreview: 'audio metadata loaded and playback advanced with allow-scripts; no allow-same-origin', errors: problems, expectedAbortedMediaRequests: abortedMediaRequests, mediaAbortExplanation: 'Chromium cancels metadata/preload requests when starting playback, seeking, or navigating. The completed playback assertions and audio.error === null distinguish these from failed audio loads.', audibleListening: 'not assessed; automated playback was muted' }, null, 2) + '\n');
  await browser.close();
  console.log('Browser playback, seeking, desktop/mobile layouts and sandbox preview passed.');
})().catch(error => { console.error(error); process.exit(1); });
