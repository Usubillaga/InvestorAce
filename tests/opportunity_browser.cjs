// OPPORTUNITY_PAGE_DIR=<replay directory> OPPORTUNITY_BROWSER_EXECUTABLE=<Chrome> node tests/opportunity_browser.cjs
const assert=require('node:assert/strict');
const path=require('node:path');
const fs=require('node:fs/promises');
const {pathToFileURL}=require('node:url');
const {chromium}=require('playwright');

(async()=>{
  const root=path.resolve(process.env.OPPORTUNITY_PAGE_DIR||'research-output/opportunity');
  const browser=await chromium.launch({executablePath:process.env.OPPORTUNITY_BROWSER_EXECUTABLE,
    headless:true,args:['--no-sandbox','--disable-gpu','--disable-software-rasterizer']});
  try{
    for(const width of [1440,390]){
      const page=await browser.newPage({viewport:{width,height:950}});
      const errors=[];page.on('pageerror',e=>errors.push(e.message));
      await page.clock.install({time:new Date()});
      await page.route('https://**/*',route=>route.abort());
      await page.goto(pathToFileURL(path.join(root,'index.es.html')).href);
      const packet=await page.locator('#assessment-data').evaluate(x=>JSON.parse(x.textContent));
      assert.equal(await page.locator('#master-table tbody tr').count(),Object.keys(packet.assessments).length);
      assert.ok(Object.keys(packet.assessments).length>=75);
      for(const ticker of ['ZTS','WKL','AR']){
        await page.fill('#dashboard-query',ticker);
        const row=page.locator('#master-table tbody tr[data-assessment="'+ticker+'"]');
        assert.ok(await row.isVisible());
        assert.equal(await row.locator('[data-opportunity-field="label"]').innerText(),'Buy');
        assert.match(await row.locator('[data-opportunity-field="metrics"]').innerText(),/PER/);
      }
      await page.fill('#dashboard-query','defensiva');
      assert.ok(await page.locator('#master-table tbody tr:visible').count()>0);
      await page.click('#dashboard-reset');
      assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
      await page.screenshot({path:path.join(root,`dashboard-${width}.png`),fullPage:false});
      await page.clock.fastForward(5*24*3600000);
      const zts=page.locator('#master-table tr[data-assessment="ZTS"]');
      assert.equal(await zts.locator('[data-opportunity-field="label"]').innerText(),'Datos incompletos');
      assert.equal(await zts.locator('[data-opportunity-field="score"]').innerText(),'—');
      assert.equal(await zts.locator('[data-opportunity-field="entry"]').first().innerText(),'Precio de compra no disponible');
      assert.equal(errors.length,0,errors.join('\n'));
      await page.close();
    }
    const page=await browser.newPage({viewport:{width:1440,height:1000}});
    const scan=JSON.parse(await fs.readFile(path.join(root,'scanner.json'),'utf8'));
    await page.clock.install({time:new Date(scan.generated_at)});
    await page.goto(pathToFileURL(path.join(root,'scanner.html')).href+'?view=universe&ticker=ZTS');
    await page.waitForSelector('#detail:not([hidden])');
    assert.equal(await page.locator('#scanner-rows [data-opportunity-field="label"]').innerText(),'Buy');
    assert.equal(await page.locator('#opportunity-ZTS [data-opportunity-field="regimes"] tr').count(),5);
    await page.clock.fastForward(5*24*3600000);
    assert.equal(await page.locator('#detail [data-opportunity-field="label"]').innerText(),'Daten unvollständig');
    assert.equal(await page.locator('#detail [data-opportunity-field="components"]').textContent(),'Daten unvollständig');
    console.log('Opportunity UI: desktop/mobile, profiles, automatic labels, five regimes and quote expiry passed');
  }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1});
