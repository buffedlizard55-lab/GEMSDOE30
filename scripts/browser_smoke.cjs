#!/usr/bin/env node
// Optional headless UI test. From the repository root:
// npm install --prefix outputs/browser --package-lock=false playwright-core@1.64.1 @sparticuz/chromium@153.0.0
// .venv/bin/python scripts/serve_research_site.py --port 8000  # use a process manager
// node scripts/browser_smoke.cjs
// Browser packages, screenshots and downloaded copies stay in ignored outputs/.
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
  const executablePath = await chromium.executablePath();
  const browser = await playwright.launch({args:chromium.args, executablePath, headless:true});
  const pointer=JSON.parse(fs.readFileSync('docs/current-run.json'));
  const card=JSON.parse(fs.readFileSync(pointer.run_card));
  const latest=JSON.parse(fs.readFileSync(pointer.latest_attempt));
  const result={engine:'headless Chromium / playwright-core', chromium_version:browser.version(),playwright_version:browserRequire('playwright-core/package.json').version, viewports:[], errors:[], downloaded_tiff_sha256:null};
  const context=await browser.newContext({acceptDownloads:true});
  const page=await context.newPage();
  page.on('pageerror', e=>result.errors.push(e.message));
  page.on('requestfailed', r=>result.errors.push(r.url()+': '+r.failure()?.errorText));
  for (const viewport of [{width:1440,height:1100},{width:390,height:844}]) {
    await page.setViewportSize(viewport);
    await page.goto('http://127.0.0.1:8000/',{waitUntil:'networkidle'});
    if (!(await page.getByRole('heading',{level:1}).textContent()).includes('No new submission.')) throw new Error('Missing overview heading');
    if (await page.getByText('NOT APPROVED FOR SUBMISSION',{exact:true}).count() !== 1) throw new Error('Ambiguous approval status');
    const overflow=await page.evaluate(()=>({page:document.documentElement.scrollWidth,screen:innerWidth}));
    if (overflow.page>overflow.screen) throw new Error('Horizontal overflow: '+JSON.stringify(overflow));
    const downloadPromise=page.waitForEvent('download');
    await page.getByRole('link',{name:/Download archived research TIFF/}).click();
    const download=await downloadPromise;
    const path='outputs/browser/download-'+viewport.width+'.tif';
    await download.saveAs(path);
    const hash=crypto.createHash('sha256').update(fs.readFileSync(path)).digest('hex');
    if (hash!==card.raster_sha256) throw new Error('Downloaded TIFF hash mismatch');
    result.downloaded_tiff_sha256=hash;
    await page.screenshot({path:`outputs/browser/overview-${viewport.width}.png`,fullPage:true});
    await page.getByRole('link',{name:'Submission guide',exact:true}).click();
    await page.waitForLoadState('networkidle');
    if (await page.locator('#submission-note').inputValue() !== card.note) throw new Error('Wrong submission note');
    await page.getByRole('button',{name:'Copy note',exact:true}).click();
    await page.waitForFunction(()=>document.querySelector('#copy-status').textContent.length>0);
    const copyMessage=await page.locator('#copy-status').textContent();
    if (!copyMessage.includes('NOT approved')) throw new Error('Clipboard message lost warning');
    await page.screenshot({path:`outputs/browser/guide-${viewport.width}.png`,fullPage:true});
    const guideOverflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);
    if(guideOverflow) throw new Error('Guide horizontal overflow');
    result.viewports.push({...viewport,overview:true,guide:true,download_verified:true,copy_warning:true,no_overflow:true});
  }
  await page.getByRole('link',{name:'Research',exact:true}).click();
  await page.waitForLoadState('networkidle');
  if (!(await page.getByRole('heading',{level:1}).textContent()).includes('Falsification is')) throw new Error('Missing falsification report');
  if(await page.locator('a[download]').count()) throw new Error('Stopped result must not offer a TIFF download');
  const privateResponse=await fetch('http://127.0.0.1:8000/'+latest.artifact_path);
  result.quarantined_tiff_http_status=privateResponse.status;
  if(privateResponse.status!==403) throw new Error('Quarantined TIFF must not be served');
  const response=await fetch('http://127.0.0.1:8000/.git/config');
  result.private_git_request_status=response.status;
  if(response.status!==403) throw new Error('Private .git must not be exposed');
  if(result.errors.length) throw new Error(JSON.stringify(result.errors));
  fs.writeFileSync('docs/research/texture-controls/browser-check.json',JSON.stringify(result,null,2)+'\n');
  console.log(JSON.stringify(result,null,2));
  await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
