#!/usr/bin/env node
// Optional real-browser checks; packages / screenshots / downloads remain ignored.
// npm install --prefix outputs/browser --package-lock=false playwright-core@1.64.1 @sparticuz/chromium@153.0.0
// Start scripts/serve_research_site.py with a process manager, then run this file.
const pathModule = require('path');
const {createRequire} = require('module');
process.chdir(pathModule.resolve(__dirname, '..'));
const browserRequire = createRequire(pathModule.resolve('outputs/browser/package.json'));
const {chromium: playwright} = browserRequire('playwright-core');
const chromiumModule = browserRequire('@sparticuz/chromium');
const chromium = chromiumModule.default || chromiumModule;
const fs = require('fs');
const crypto = require('crypto');
(async()=>{
  await chromiumModule.inflate(pathModule.resolve(pathModule.dirname(browserRequire.resolve('@sparticuz/chromium')), '../bin/al2023.tar.br'));
  chromiumModule.setupLambdaEnvironment('/tmp/al2023/lib');
  const browser = await playwright.launch({args:chromium.args, executablePath:await chromium.executablePath(), headless:true});
  const pointer=JSON.parse(fs.readFileSync('docs/current-run.json'));
  const card=JSON.parse(fs.readFileSync(pointer.latest_review.run_card));
  const stopped=JSON.parse(fs.readFileSync(pointer.latest_attempt));
  const result={engine:'headless Chromium / playwright-core', chromium_version:browser.version(),
    playwright_version:browserRequire('playwright-core/package.json').version, viewports:[], errors:[],
    downloaded_tiff_sha256:null, checked_priority_pages:[]};
  const context=await browser.newContext({acceptDownloads:true});
  const page=await context.newPage();
  page.on('pageerror', e=>result.errors.push(e.message));
  page.on('requestfailed', r=>result.errors.push(r.url()+': '+r.failure()?.errorText));
  for (const viewport of [{width:1440,height:1100},{width:390,height:844}]) {
    await page.setViewportSize(viewport);
    await page.goto('http://127.0.0.1:8000/',{waitUntil:'networkidle'});
    if (!(await page.getByRole('heading',{level:1}).textContent()).includes('No new submission.')) throw new Error('Missing current decision heading');
    if (await page.getByText('NOT APPROVED FOR SUBMISSION',{exact:true}).count() !== 1) throw new Error('Ambiguous approval status');
    if (await page.locator('a[download]').count() !== 1) throw new Error('Expected exactly one current research TIFF');
    if (await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)) throw new Error('Overview horizontal overflow');
    const downloadPromise=page.waitForEvent('download');
    await page.getByRole('link',{name:/Download GDX-1 research TIFF/}).click();
    const download=await downloadPromise;
    const path='outputs/browser/download-'+viewport.width+'.tif';
    await download.saveAs(path);
    const hash=crypto.createHash('sha256').update(fs.readFileSync(path)).digest('hex');
    if (hash!==card.raster_sha256 || download.suggestedFilename()!==pathModule.basename(card.published_tiff)) throw new Error('Downloaded TIFF identity mismatch');
    result.downloaded_tiff_sha256=hash;
    await page.screenshot({path:`outputs/browser/overview-${viewport.width}.png`,fullPage:true});
    await page.getByRole('link',{name:'Submission guide',exact:true}).click();
    await page.waitForLoadState('networkidle');
    if (await page.locator('#submission-note').inputValue() !== card.note) throw new Error('Wrong research note');
    if (await page.locator('#submission-name').inputValue() !== card.submission_name) throw new Error('Wrong run name');
    await page.getByRole('button',{name:'Copy note',exact:true}).click();
    await page.waitForFunction(()=>document.querySelector('#copy-status').textContent.length>0);
    if (!(await page.locator('#copy-status').textContent()).includes('NOT approved')) throw new Error('Clipboard message lost warning');
    await page.screenshot({path:`outputs/browser/guide-${viewport.width}.png`,fullPage:true});
    if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)) throw new Error('Guide horizontal overflow');
    result.viewports.push({...viewport,overview:true,guide:true,download_verified:true,copy_warning:true,no_overflow:true});
  }
  await page.getByRole('link',{name:'GDX-1 science',exact:true}).click();
  await page.waitForLoadState('networkidle');
  if(!(await page.locator('#novelty').textContent()).includes('UNKNOWN')) throw new Error('Missing global novelty blocker');
  if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)) throw new Error('Science horizontal overflow');
  for(const site of [24,25,27,28,30,31,32,33,36]) {
    await page.goto(`http://127.0.0.1:8000/priority-GEMSDOE${site}.html`,{waitUntil:'networkidle'});
    if(!(await page.getByRole('heading',{level:1}).textContent()).includes(`GEMSDOE${site}`)) throw new Error('Wrong priority executive page');
    if(await page.getByText('DO NOT RESUBMIT HISTORICAL BYTES',{exact:true}).count()!==1) throw new Error('Missing historical-byte warning');
    if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)) throw new Error('Priority page overflow '+site);
    result.checked_priority_pages.push(`GEMSDOE${site}`);
  }
  const privateResponse=await fetch('http://127.0.0.1:8000/'+stopped.artifact_path);
  result.quarantined_tiff_http_status=privateResponse.status;
  if(privateResponse.status!==403) throw new Error('Quarantined TIFF must not be served');
  const response=await fetch('http://127.0.0.1:8000/.git/config');
  result.private_git_request_status=response.status;
  if(response.status!==403) throw new Error('Private .git must not be exposed');
  if(result.errors.length) throw new Error(JSON.stringify(result.errors));
  fs.writeFileSync('docs/research/2026-10-26-gdx/browser-check.json',JSON.stringify(result,null,2)+'\n');
  console.log(JSON.stringify(result,null,2));
  await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
