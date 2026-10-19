// Run after: python weekly_research.py --output research-output/comparison
// NODE_PATH can point at an existing Playwright installation.
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const {chromium} = require('playwright');

(async () => {
  const options = {headless:true,args:['--no-sandbox','--disable-dev-shm-usage']};
  if (process.env.COMPARE_BROWSER_EXECUTABLE) options.executablePath=process.env.COMPARE_BROWSER_EXECUTABLE;
  const browser = await chromium.launch(options);
  try {
    const page=await browser.newPage({viewport:{width:1440,height:1100},acceptDownloads:true});
    const errors=[];
    page.on('pageerror',error=>errors.push(error.message));
    const url=pathToFileURL(path.resolve(process.env.COMPARE_PAGE || 'research-output/comparison/compare.html'));
    await page.goto(url.href);
    const data=JSON.parse(await page.locator('#comparison-data').textContent());
    assert.equal(await page.locator('#left option').count(),data.universe_count);
    assert.equal(await page.locator('#right option').count(),data.universe_count);
    assert.equal(await page.locator('#left').inputValue(),'WKL');
    assert.equal(await page.locator('#right').inputValue(),'DIS');
    assert.equal(await page.locator('#metric-rows tr[data-metric]').count(),29);
    await page.click('#swap');
    assert.equal(await page.locator('#left').inputValue(),'DIS');
    assert.equal(await page.locator('#right').inputValue(),'WKL');
    await page.selectOption('#period','1');
    assert.equal(new URL(page.url()).searchParams.get('year'),'1');
    for (const [language,heading] of [['de','Aktien vergleichen'],['es','Comparar acciones'],['en','Compare stocks']]) {
      await page.selectOption('#language',language);
      assert.equal(await page.locator('h1').innerText(),heading);
      assert.equal(await page.locator('html').getAttribute('lang'),language);
      assert.equal(await page.locator('#period').inputValue(),'1');
    }
    await page.click('[data-group="shares"]');
    assert.equal(await page.locator('#metric-rows tr[data-metric]').count(),6);
    assert.ok((await page.locator('[data-metric="float_shares"]').innerText()).includes('Retrieved'));
    await page.click('[data-group="all"]');
    const bad=new URL(url.href);bad.searchParams.set('a','OUTSIDE');bad.searchParams.set('b','DIS');
    await page.goto(bad.href);
    assert.ok((await page.locator('#warnings').innerText()).includes('outside your universe'));
    assert.equal(await page.locator('#left option[value="OUTSIDE"]').count(),0);
    assert.equal(await page.locator('#left').inputValue(),'WKL');
    await page.selectOption('#left','BABA');
    await page.selectOption('#right','AAPL');
    const baba=data.rows.find(r=>r.ticker==='BABA');
    if (baba.financial_currency==='CNY') {
      assert.ok((await page.locator('#warnings').innerText()).includes('Different reporting currencies'));
      assert.ok((await page.locator('#metric-head').innerText()).includes('CNY'));
    }
    const negative=data.rows.find(r=>r.annual?.[0]?.net_income<0);
    if (negative) {
      await page.selectOption('#left',negative.ticker);
      const pending=page.waitForEvent('download');
      await page.click('#export');
      const csv=await fs.readFile(await (await pending).path(),'utf8');
      assert.ok(csv.includes('"'+String(negative.annual[0].net_income)+'"'),'CSV must preserve negative numeric values as numbers');
      assert.ok(csv.includes('financial_currency'));
    }
    await page.selectOption('#left','WKL');
    await page.selectOption('#right','DIS');
    await page.screenshot({path:process.env.COMPARE_SCREENSHOT || '/workspace/scratch/d4c3218166d4/comparison-desktop.png',fullPage:true});
    for (const width of [390,360,320]) {
      await page.setViewportSize({width,height:844});
      assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'No page overflow at '+width);
    }
    await page.setViewportSize({width:390,height:844});
    await page.screenshot({path:'/workspace/scratch/d4c3218166d4/comparison-mobile.png',fullPage:true});
    assert.deepEqual(errors,[]);
    console.log('Comparison browser checks passed: selectors, membership, languages, periods, currencies, CSV, and mobile layout.');
  } finally { await browser.close(); }
})().catch(error=>{console.error(error);process.exitCode=1;});
