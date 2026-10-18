// Optional end-to-end check after generating the standalone scanner.
// npm install --no-save playwright
// node tests/scanner_browser.cjs
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const {chromium} = require('playwright');

(async () => {
  const browser = await chromium.launch({headless:true,
    ...(process.env.SCANNER_BROWSER_EXECUTABLE ? {executablePath:process.env.SCANNER_BROWSER_EXECUTABLE} : {}),
    args:['--no-sandbox','--disable-gpu','--disable-software-rasterizer','--use-gl=disabled','--disable-webgl']});
  try {
    const page = await browser.newPage({viewport:{width:1440,height:1080},acceptDownloads:true});
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    const file = path.resolve(process.env.SCANNER_PAGE || 'research-output/scanner/scanner.html');
    await page.goto(pathToFileURL(file).href);
    const data = await page.locator('#scanner-data').textContent().then(JSON.parse);
    const market = data.market || {candidates: []};
    if (data.current_regime) assert.equal(await page.locator('#regime').inputValue(), data.current_regime);
    if (market.candidates.length) {
      // The market tab is the default view and shows only new Buy/Strong Buy ideas.
      const fresh = market.candidates.filter(c => c.score >= 7 && !c.in_universe).length;
      assert.equal(await page.locator('#scanner-rows tr').count(), fresh);
      if (data.current_regime) assert.equal(await page.locator('#m-regime').inputValue(), data.current_regime);
      await page.selectOption('#m-band', 'all');
      await page.selectOption('#m-holdings', 'all');
      assert.equal(await page.locator('#scanner-rows tr').count(), market.candidates.length);
      const first = market.candidates[0];
      await page.click(`button[data-ticker="${first.ticker}"]`);
      const detail = await page.locator('#detail').innerText();
      assert.ok(detail.includes('Scorebeiträge') && detail.includes('Quellen') && detail.includes(first.ticker));
      await page.click('#close-detail');
      const marketCsv = page.waitForEvent('download');
      await page.click('#export');
      const marketText = await fs.readFile(await (await marketCsv).path(), 'utf8');
      assert.equal(marketText.trim().split('\r\n').length, market.candidates.length + 1);
      await page.click('#m-reset');
      assert.equal(await page.locator('#scanner-rows tr').count(), fresh);
    }
    await page.click('#tab-universe');
    const expected = data.rows.filter(r => r.model_score >= 7 && !r.held_in_snapshot).length;
    assert.equal(await page.locator('#scanner-rows tr').count(), expected);
    const order = await page.locator('#scanner-rows .ticker').allTextContents();
    await page.selectOption('#regime','GOLDILOCKS');
    assert.deepEqual(await page.locator('#scanner-rows .ticker').allTextContents(),order);
    await page.selectOption('#band','all');
    await page.selectOption('#holdings','all');
    assert.equal(await page.locator('#scanner-rows tr').count(),data.universe_count);
    await page.selectOption('#band','Strong Buy');
    assert.equal(await page.locator('#scanner-rows tr').count(),data.rows.filter(r=>r.model_band==='Strong Buy').length);
    await page.selectOption('#band','all');
    await page.fill('#query','Sanofi');
    assert.equal(await page.locator('#scanner-rows tr').count(),1);
    const csvPending = page.waitForEvent('download');
    await page.click('#export');
    const csv = await csvPending;
    const text = await fs.readFile(await csv.path(),'utf8');
    assert.equal(text.trim().split('\r\n').length,2);
    assert.ok(text.includes('SAN.PA') && text.includes('ungeprüft'));
    for (const ticker of ['WKL','DIS']) {
      await page.fill('#query',ticker);
      await page.click(`button[data-ticker="${ticker}"]`);
      const detail = await page.locator('#detail').innerText();
      assert.ok(detail.includes('NORM-'+ticker) && detail.includes('Antwort:') && detail.includes('Zur Klärung:'));
      await page.click('#close-detail');
    }
    await page.locator('details.audit summary').click();
    const jsonPending = page.waitForEvent('download');
    await page.click('#download-json');
    const jsonFile = await jsonPending;
    const exported = JSON.parse(await fs.readFile(await jsonFile.path(),'utf8'));
    assert.equal(exported.rows.length,data.universe_count);
    assert.ok(exported.rows.every(row=>row.rating===null));
    // A control named 'reset' used to shadow the form's native reset method.
    await page.click('#reset-filters');
    assert.equal(await page.locator('#query').inputValue(),'');
    assert.equal(await page.locator('#scanner-rows tr').count(),expected);
    await page.setViewportSize({width:390,height:844});
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
    assert.deepEqual(errors,[]);
    console.log('Scanner browser checks passed.');
  } finally {
    await browser.close();
  }
})().catch(error=>{console.error(error);process.exitCode=1;});
