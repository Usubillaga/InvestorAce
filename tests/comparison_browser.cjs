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
    assert.equal(await page.locator('[data-duel-round]').count(),5);
    const originalPoints=await page.locator('[data-duel-points]').allTextContents();
    const originalVerdict=await page.locator('#duel-verdict').innerText();
    assert.ok((await page.locator('.duel-why').innerText()).includes('Why'));
    assert.ok((await page.locator('.duel-counter').innerText()).length>50);
    await page.click('#swap');
    assert.equal(await page.locator('#left').inputValue(),'DIS');
    assert.equal(await page.locator('#right').inputValue(),'WKL');
    assert.deepEqual(await page.locator('[data-duel-points]').allTextContents(),originalPoints.toReversed());
    assert.equal(await page.locator('#duel-verdict').innerText(),originalVerdict);
    await page.selectOption('#period','1');
    assert.equal(new URL(page.url()).searchParams.get('year'),'1');
    for (const [language,heading] of [['de','Aktien vergleichen'],['es','Comparar acciones'],['en','Compare stocks']]) {
      await page.selectOption('#language',language);
      assert.equal(await page.locator('h1').innerText(),heading);
      assert.equal(await page.locator('html').getAttribute('lang'),language);
      assert.equal(await page.locator('#period').inputValue(),'1');
      assert.ok(!(await page.locator('#duel').innerText()).includes('roundGrowth'));
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
      assert.ok(csv.includes('duel_round_wins') && csv.includes('finance-duel-v1'));
    }
    await page.selectOption('#left','WKL');
    await page.selectOption('#right','WKL');
    assert.equal(await page.locator('#duel').getAttribute('data-status'),'SAME_STOCK');
    assert.equal(await page.locator('#duel').getAttribute('data-winner'),'');
    const noData=data.rows.find(r=>!r.annual?.length);
    if (noData) {
      await page.selectOption('#right',noData.ticker);
      assert.equal(await page.locator('#duel').getAttribute('data-status'),'OPEN');
      assert.equal(await page.locator('#duel').getAttribute('data-winner'),'');
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
    for (const language of ['de','es']) {
      await page.selectOption('#language',language);
      for (const width of [390,320]) {
        await page.setViewportSize({width,height:844});
        assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'No '+language+' overflow at '+width);
      }
    }
    await page.selectOption('#language','de');
    await page.setViewportSize({width:390,height:844});
    await page.locator('#duel').screenshot({path:'/workspace/scratch/d4c3218166d4/duel-mobile-de.png'});
    await page.setViewportSize({width:1440,height:1100});
    await page.locator('#duel').screenshot({path:'/workspace/scratch/d4c3218166d4/duel-desktop-de.png'});

    // Exercise uncertain results and escaped issuer names through the complete UI.
    const html=await fs.readFile(path.resolve(process.env.COMPARE_PAGE || 'research-output/comparison/compare.html'),'utf8');
    const fixture=structuredClone(data);
    fixture.rows=data.rows.filter(r=>['WKL','DIS'].includes(r.ticker)).map(r=>structuredClone(r));
    fixture.universe_count=2;
    const viewedAt=Date.now();
    fixture.generated_at=new Date(viewedAt).toISOString();
    const fiscalEnd=new Date(viewedAt-365*86400000).toISOString().slice(0,10);
    for (const r of fixture.rows) {
      r.status='OK';r.warnings=[];r.retrieved_at=fixture.generated_at;
      r.annual=[{period_end:fiscalEnd,revenue_growth:10,operating_margin:20,
        fcf_margin:15,net_debt_ebitda:2,dilution:1,ebitda:100}];
    }
    const wkl=fixture.rows.find(r=>r.ticker==='WKL');
    wkl.name='<img src=x onerror="window.issuerInjected=true">';
    wkl.annual[0].revenue_growth=20;
    const synthetic=await browser.newPage();
    synthetic.on('pageerror',error=>errors.push(error.message));
    const renderFixture=async()=>synthetic.setContent(html.replace(
      /(<script id="comparison-data" type="application\/json">)[\s\S]*?(<\/script>)/,
      (_,start,end)=>start+JSON.stringify(fixture).replace(/</g,'\\u003c')+end));
    await renderFixture();
    assert.equal(await synthetic.locator('#duel').getAttribute('data-status'),'WINNER');
    assert.equal(await synthetic.locator('#duel').getAttribute('data-winner'),'WKL');
    assert.equal(await synthetic.locator('#duel img').count(),0);
    assert.equal(await synthetic.evaluate(()=>window.issuerInjected),undefined);
    // A previously published page must age with the viewing clock, including its CSV.
    fixture.generated_at=new Date(viewedAt-20*86400000).toISOString();
    for (const r of fixture.rows) r.retrieved_at=fixture.generated_at;
    await renderFixture();
    assert.equal(await synthetic.locator('#duel').getAttribute('data-status'),'PROVISIONAL',
      'Old build timestamps must not freeze freshness checks');
    assert.equal(await synthetic.locator('#duel').getAttribute('data-winner'),'');
    const agedDownload=synthetic.waitForEvent('download');
    await synthetic.click('#export');
    const agedCsv=await fs.readFile(await (await agedDownload).path(),'utf8');
    assert.ok(agedCsv.includes('"duel_status","finance-duel-v1","PROVISIONAL"'),
      'CSV must use the same current freshness rules');
    fixture.generated_at=new Date(viewedAt).toISOString();
    for (const r of fixture.rows) r.retrieved_at=fixture.generated_at;
    wkl.status='CACHED';
    await renderFixture();
    assert.equal(await synthetic.locator('#duel').getAttribute('data-status'),'PROVISIONAL');
    assert.equal(await synthetic.locator('#duel').getAttribute('data-winner'),'');
    assert.ok((await synthetic.locator('#duel-verdict').innerText()).includes('Provisional'));
    await synthetic.close();
    assert.deepEqual(errors,[]);
    console.log('Comparison browser checks passed: duel verdicts, round explanations, swap symmetry, incomplete data, injection safety, selectors, languages, CSV and mobile layout.');
  } finally { await browser.close(); }
})().catch(error=>{console.error(error);process.exitCode=1;});
