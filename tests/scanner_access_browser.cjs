// Focused regression checks for stock deep links and original review packets.
// Generate scanner.html first, then pass SCANNER_PAGE and optionally
// SCANNER_BROWSER_EXECUTABLE as for scanner_browser.cjs.
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
    const base = pathToFileURL(file).href;
    await page.goto(base);
    const original = await page.locator('#scanner-data').textContent().then(JSON.parse);
    assert.ok(original.rows.some(r=>r.ticker==='ZTS'),'ZTS must be available for its public deep link');
    const go = query => page.goto(base + query);
    async function active(scope,ticker) {
      assert.equal(await page.locator(`#tab-${scope}`).getAttribute('aria-selected'),'true');
      assert.equal(await page.locator('#detail').isVisible(),true);
      assert.equal(await page.locator('#detail').getAttribute('data-scope'),scope);
      assert.equal(await page.locator('#detail').getAttribute('data-ticker'),ticker);
      assert.equal(await page.locator('#selected-review-packet').isVisible(),true);
      assert.ok((await page.locator('#selected-review-packet').innerText()).includes(ticker));
    }
    async function packet(id,scope,ticker) {
      const pending = page.waitForEvent('download');
      await page.click(id);
      const download = await pending;
      assert.equal(download.suggestedFilename(),`InvestorAce_Pruefpaket_${scope}_${ticker}.json`);
      const raw = await fs.readFile(await download.path(),'utf8');
      // Compare bytes rather than reserialized JSON: Python floats and the hash
      // of the archived snapshot must survive each download without changes.
      assert.equal(raw,original.review_packets[scope][ticker]);
      const parsed = JSON.parse(raw);
      assert.equal(parsed.snapshot.scope,scope);
      assert.equal(parsed.snapshot.ticker,ticker);
      assert.equal(parsed.can_approve,false);
      return raw;
    }
    async function unrestricted(scope,ticker) {
      const prefix = scope==='market'?'m-':'';
      for (const key of scope==='market'
        ? ['band','sector','quality','holdings'] : ['band','sector','currency','holdings','review']) {
        assert.equal(await page.locator(`#${prefix}${key}`).inputValue(),'all',key);
      }
      assert.equal(await page.locator(`#${prefix}minimum`).inputValue(),'0');
      if (scope==='market') assert.equal(await page.locator('#m-cap').inputValue(),'0');
      assert.equal(await page.locator(`#${prefix}query`).inputValue(),ticker);
      assert.ok((await page.locator('#scanner-rows .ticker').allTextContents()).includes(ticker));
    }

    await go('?view=universe&ticker=ZTS');
    await active('universe','ZTS');
    await unrestricted('universe','ZTS');
    await packet('#selected-review-packet','universe','ZTS');
    // The per-detail action must be immediately below its heading.
    assert.equal(await page.locator('#detail .detail-head + section #download-review-packet').count(),1);
    await page.fill('#query','__NO_MATCH__');
    await page.selectOption('#band','Sell');
    await page.selectOption('#holdings','held');
    await page.fill('#minimum','10');
    assert.equal(await page.locator('#scanner-rows tr').count(),0);
    await packet('#selected-review-packet','universe','ZTS');
    await page.click('#tab-market');
    assert.equal(await page.locator('#tab-market').getAttribute('aria-selected'),'true');
    assert.equal(await page.locator('#detail').getAttribute('data-scope'),'universe');
    await packet('#download-review-packet','universe','ZTS');
    // Periodic/visibility assessment projections previously hid the detail.
    await page.evaluate(()=>document.dispatchEvent(new Event('visibilitychange')));
    assert.equal(await page.locator('#detail').isVisible(),true);
    await packet('#selected-review-packet','universe','ZTS');
    await page.click('#m-reset');
    await packet('#selected-review-packet','universe','ZTS');
    assert.equal(new URL(page.url()).searchParams.get('view'),'universe');
    assert.equal(new URL(page.url()).searchParams.get('ticker'),'ZTS');
    await page.setViewportSize({width:390,height:844});
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
    await page.setViewportSize({width:1440,height:1080});
    await page.click('#close-detail');
    assert.equal(await page.locator('#detail').isVisible(),false);
    assert.equal(await page.locator('#selected-review-packet').isVisible(),false);

    const common = original.market?.candidates.find(c=>original.rows.some(r=>r.ticker===(c.universe_key||c.ticker)));
    const candidate = common || original.market?.candidates[0];
    if (candidate) {
      await go(`?view=market&ticker=${encodeURIComponent(candidate.ticker)}`);
      await active('market',candidate.ticker);
      await unrestricted('market',candidate.ticker);
      await packet('#selected-review-packet','market',candidate.ticker);
      if (common) {
        // Jumping out of a market detail must clear *all* universe restrictions.
        await page.evaluate(()=>{
          document.getElementById('query').value='__NO_MATCH__';
          for (const id of ['sector','currency']) {
            const control=document.getElementById(id); control.selectedIndex=control.options.length-1;
          }
          document.getElementById('minimum').value='10';
          document.getElementById('review').value='notes';
        });
        await page.click('#open-in-universe');
        const ticker=common.universe_key||common.ticker;
        await active('universe',ticker);
        await unrestricted('universe',ticker);
        await packet('#selected-review-packet','universe',ticker);
      }
    }
    for (const query of ['?view=universe&ticker=%20zts%20','?ticker=zts','?view=unknown&ticker=ZTS']) {
      await go(query);
      await active('universe','ZTS');
    }
    for (const scope of ['universe','market']) {
      for (const ticker of ['UNKNOWN_STOCK','%E0%A4%A','%3Cimg%20src=x%20onerror=window.packetScriptRan=1%3E','__proto__','constructor','ZTS&ticker=KO','']) {
        await go(`?view=${scope}&ticker=${ticker}`);
        assert.equal(await page.locator(`#tab-${scope}`).getAttribute('aria-selected'),'true');
        assert.equal(await page.locator('#detail').isVisible(),false);
        assert.equal(await page.locator('#selected-review-packet').isVisible(),false);
        assert.equal(await page.locator('#selection-status').isVisible(),true);
        assert.equal(await page.evaluate(()=>window.packetScriptRan),undefined);
        const expected=scope==='universe'?original.rows.length:(original.market?.candidates.length||0);
        assert.equal(await page.locator('#scanner-rows tr').count(),expected);
      }
    }
    await go('?view=universe');
    assert.equal(await page.locator('#tab-universe').getAttribute('aria-selected'),'true');
    assert.equal(await page.locator('#detail').isVisible(),false);

    // Optional build-time yfinance data augments the saved research without
    // requiring any network requests or inventing missing valuation inputs.
    const fixture=JSON.parse(JSON.stringify(original));
    fixture.rows.find(r=>r.ticker==='ZTS').dynamic_analysis={status:'MODEL_SCENARIO',
      as_of:'2026-10-25T10:30:00Z',fetched_at:'2026-10-25T10:00:00Z',financial_period:'2026-06-30',basis:'TTM',currency:'USD',
      inputs:{revenue:9000000000,operating_income:3000000000,net_income:2000000000,operating_cash_flow:2500000000,
        capex:500000000,fcf:2000000000,debt:6000000000,cash:1500000000,shares:450000000,quote_price:122.5},
      parameters:{discount_rate_pct:9,growth_rate_pct:5,terminal_growth_pct:2,horizon_years:10},
      valuation:{ngv_per_share:95.2,dcf_per_share:125.4,reverse_dcf_growth_pct:null,
        scenarios:[{name:'Basisszenario',growth_pct:5,value_per_share:125.4}]},
      warnings:['Prüfhinweis <img src=x onerror=window.packetScriptRan=1>']};
    delete fixture.review_packets.universe.ZTS;
    const html=(await fs.readFile(file,'utf8')).replace(
      /(<script type="application\/json" id="scanner-data">)[\s\S]*?(<\/script>)/,
      (_,start,end)=>start+JSON.stringify(fixture).replace(/</g,'\\u003c')+end);
    await page.route('https://scanner.test/**',route=>route.fulfill({contentType:'text/html',body:html}));
    await page.goto('https://scanner.test/scanner.html?view=universe&ticker=ZTS');
    assert.equal(await page.locator('#detail').isVisible(),true);
    assert.equal(await page.locator('#selected-review-packet').isVisible(),false);
    const model=await page.locator('#dynamic-analysis').innerText();
    for (const text of ['yfinance','Prüfung erforderlich','2026-06-30','TTM','95,20 USD','125,40 USD','9,0 %','Basisszenario','—']) {
      assert.ok(model.includes(text),text);
    }
    assert.equal(await page.locator('#dynamic-analysis tr').filter({hasText:'Vom Kurs impliziertes Wachstum'}).locator('td').nth(1).innerText(),'—');
    assert.equal(await page.locator('#dynamic-analysis img').count(),0);
    assert.equal(await page.evaluate(()=>window.packetScriptRan),undefined);
    const row=fixture.rows.find(r=>r.ticker==='ZTS');
    if (row.thesis) assert.ok((await page.locator('#detail').innerText()).includes(row.thesis));
    if (row.counterargument) assert.ok((await page.locator('#detail').innerText()).includes(row.counterargument));
    await page.setViewportSize({width:390,height:844});
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
    assert.deepEqual(errors,[]);
    console.log('Scanner deep-link, packet identity, and optional dynamic-model checks passed.');
  } finally {
    await browser.close();
  }
})().catch(error=>{console.error(error);process.exitCode=1;});
