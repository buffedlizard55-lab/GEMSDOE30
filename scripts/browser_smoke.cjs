#!/usr/bin/env node
// Optional current-site browser checks; never downloads or uploads a prediction.
// npm install --prefix outputs/browser --package-lock=false playwright-core@1.64.1 @sparticuz/chromium@153.0.0
// Start scripts/serve_research_site.py, then run this file. Artifacts stay ignored.
const path = require('path');
const fs = require('fs');
const {createRequire} = require('module');
process.chdir(path.resolve(__dirname, '..'));
const browserRequire = createRequire(path.resolve('outputs/browser/package.json'));
const {chromium: playwright} = browserRequire('playwright-core');
const chromiumModule = browserRequire('@sparticuz/chromium');
const chromium = chromiumModule.default || chromiumModule;

(async () => {
  await chromiumModule.inflate(path.resolve(path.dirname(browserRequire.resolve('@sparticuz/chromium')), '../bin/al2023.tar.br'));
  chromiumModule.setupLambdaEnvironment('/tmp/al2023/lib');
  const browser = await playwright.launch({args: chromium.args, executablePath: await chromium.executablePath(), headless: true});
  try {
    const base = process.env.PREVIEW_URL || 'http://127.0.0.1:8000';
    const receipt = JSON.parse(fs.readFileSync('docs/research/2026-10-28-priority-audit.json'));
    const result = {engine: 'headless Chromium / playwright-core', chromium_version: browser.version(),
      playwright_version: browserRequire('playwright-core/package.json').version,
      viewports: [], checked_priority_pages: [], errors: [], prediction_downloaded: false};
    const page = await browser.newPage();
    page.on('pageerror', e => result.errors.push(e.message));
    page.on('requestfailed', r => result.errors.push(r.url() + ': ' + r.failure()?.errorText));
    for (const viewport of [{width: 1440, height: 1100}, {width: 390, height: 844}]) {
      await page.setViewportSize(viewport);
      await page.goto(base + '/', {waitUntil: 'networkidle'});
      if (!(await page.locator('aside[aria-label="Latest byte audit"]').textContent()).includes('no approved submission download')) throw new Error('Missing current decision');
      await page.getByRole('link', {name: '28 Oct byte audit', exact: true}).click();
      await page.waitForLoadState('networkidle');
      if ((await page.getByRole('heading', {level: 1}).textContent()) !== 'No approved submission download.') throw new Error('Wrong audit heading');
      if (await page.locator('tbody tr').count() !== 9) throw new Error('Missing site rows');
      if (await page.getByText('NO — duplicate-stop', {exact: true}).count() !== 9) throw new Error('Ambiguous stop status');
      if (await page.locator('a[download]').count() !== 0) throw new Error('Stopped references must not be download controls');
      if (await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)) throw new Error('Audit viewport overflow');
      for (const row of receipt.rows) {
        if (await page.getByRole('link', {name: row.historical_file, exact: true}).getAttribute('href') !== row.source_url) throw new Error('Wrong immutable source link');
      }
      await page.screenshot({path: `outputs/browser/priority-audit-${viewport.width}.png`, fullPage: true});
      await page.getByRole('link', {name: 'Submission guide', exact: true}).click();
      await page.waitForLoadState('networkidle');
      if (!(await page.getByRole('heading', {name: 'There is no approved file to submit.', exact: true}).count())) throw new Error('Guide lost approval warning');
      if (await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)) throw new Error('Guide viewport overflow');
      result.viewports.push({...viewport, audit: true, guide: true, no_download_controls_on_audit: true, no_overflow: true});
    }
    for (const row of receipt.rows) {
      await page.goto(`${base}/priority-${row.site}.html`, {waitUntil: 'networkidle'});
      if ((await page.getByRole('heading', {level: 1}).textContent()) !== row.site) throw new Error('Wrong per-site heading');
      if (!(await page.locator('aside[aria-label="Latest byte audit"]').textContent()).includes('no approved submission download')) throw new Error('Missing per-site stop');
      result.checked_priority_pages.push(row.site);
    }
    const privateStatuses = {};
    for (const target of ['/.git/config', '/data/raw/sample_submission.tif', '/outputs/browser/']) {
      const response = await fetch(base + target);
      privateStatuses[target] = response.status;
      if (response.status !== 403) throw new Error('Private path exposed: ' + target);
    }
    result.private_path_statuses = privateStatuses;
    if (result.errors.length) throw new Error(JSON.stringify(result.errors));
    // Never overwrite an archived historical browser receipt under docs/research.
    fs.writeFileSync('outputs/browser/current-check.json', JSON.stringify(result, null, 2) + '\n');
    console.log(JSON.stringify(result, null, 2));
  } finally {
    await browser.close();
  }
})().catch(e => {console.error(e); process.exit(1);});
