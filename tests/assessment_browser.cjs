// python tests/assessment_pages.py research-output/assessment
// NODE_PATH=<Playwright modules> node tests/assessment_browser.cjs
const assert=require('node:assert/strict');
const path=require('node:path');
const {pathToFileURL}=require('node:url');
const {chromium}=require('playwright');
(async()=>{
  const options={headless:true,args:['--no-sandbox','--disable-dev-shm-usage']};
  if(process.env.ASSESSMENT_BROWSER_EXECUTABLE) options.executablePath=process.env.ASSESSMENT_BROWSER_EXECUTABLE;
  const browser=await chromium.launch(options);
  try{
    const directory=path.resolve(process.env.ASSESSMENT_PAGES||'research-output/assessment');
    for(const file of ['index.en.html','index.de.html','index.es.html','scanner.html','compare.html'].filter(file=>!process.env.ASSESSMENT_ONLY_PAGE||file===process.env.ASSESSMENT_ONLY_PAGE)){
      const page=await browser.newPage();
      const errors=[];page.on('pageerror',error=>errors.push(error.message));
      await page.route('https://**/*',route=>route.abort());
      await page.clock.install({time:new Date('2026-10-20T17:00:00Z')});
      async function crossExpiry(when){
        await page.clock.setSystemTime(new Date(Date.parse(when)-10));
        await page.evaluate(()=>document.dispatchEvent(new Event('visibilitychange')));
        await page.clock.runFor(20);
      }
      await page.goto(pathToFileURL(path.join(directory,file)).href);
      if(file.startsWith('index')){
        await page.evaluate(()=>revealZiel());
        await page.locator('details').evaluateAll(nodes=>nodes.forEach(node=>node.open=true));
        const originalScore=await page.locator('[data-assessment-field="model_score"]').first().innerText();
        assert.equal(await page.locator('[data-assessment-field="rating"]').first().innerText(),'BUY');
        assert.equal(await page.locator('[data-entry-current="true"]').count(),2);
        assert.equal(await page.locator('[data-portfolio-reviewed]').isVisible(),true);
        await page.clock.runFor(100);
        await crossExpiry('2026-10-21T16:00:00Z');
        assert.notEqual(await page.locator('[data-assessment-field="rating"]').first().innerText(),'BUY');
        assert.equal(await page.locator('[data-entry-current="true"]').count(),0);
        assert.equal(await page.locator('[data-portfolio-reviewed]').isVisible(),false);
        assert.equal(await page.locator('[data-portfolio-review-status]').isVisible(),true);
        assert.equal(await page.locator('[data-entry-action="limit"]').first().innerText(),'—');
        assert.equal(await page.locator('[data-proposal-current="capacity"]').innerText(),'100.0%');
        assert.equal(await page.locator('[data-assessment-field="model_score"]').first().innerText(),originalScore);
        await crossExpiry('2026-10-24T15:40:00Z');
        assert.equal(await page.locator('[data-assessment-field="model_score"]').first().innerText(),'—');
        assert.equal(await page.locator('[data-assessment-field="coverage"]').first().innerText(),'85%');
      }else if(file==='scanner.html'){
        await page.selectOption('#band','all');await page.selectOption('#holdings','all');
        assert.ok((await page.locator('#scanner-rows').innerText()).includes('Geprüft'));
        assert.equal(await page.locator('#stat-3').innerText(),'1');
        assert.ok((await page.locator('#scanner-rows').innerText()).includes('Einwände offen'));
        await crossExpiry('2026-10-21T16:00:00Z');
        assert.ok((await page.locator('#scanner-rows').innerText()).includes('Ungeprüft'));
        await crossExpiry('2026-10-24T15:40:00Z');
        assert.deepEqual(await page.locator('#scanner-rows .score').allTextContents(),['—','—']);
      }else{
        assert.ok(!(await page.locator('.duel-model').innerText()).includes('review pending'));
        await crossExpiry('2026-10-21T16:00:00Z');
        assert.match(await page.locator('.duel-model').innerText(),/review pending/i);
        await crossExpiry('2026-10-24T15:40:00Z');
        assert.ok(!/8[.,]2\d\/10/.test(await page.locator('.duel-model').innerText()));
      }
      assert.deepEqual(errors,[],file+' JavaScript errors');
      console.log(file+': approval and quote expiry passed');await page.close();
    }
  }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
