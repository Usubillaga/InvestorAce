// Compare reports rendered from the same dated input record before/after the change.
// DASHBOARD_BEFORE=<directory> DASHBOARD_AFTER=<directory> node tests/dashboard_browser.cjs
const assert=require('node:assert/strict');
const path=require('node:path');
const {pathToFileURL}=require('node:url');
const fs=require('node:fs/promises');
const {chromium}=require('playwright');

async function inventory(page){
  return page.evaluate(()=>{
    const normalize=s=>s.replace(/\d{4}-\d\d-\d\d \d\d:\d\d UTC/g,'SNAPSHOT').replace(/\s+/g,' ').trim();
    const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
    const text=[];
    while(walker.nextNode()){
      if(['SCRIPT','STYLE'].includes(walker.currentNode.parentElement.tagName))continue;
      const value=normalize(walker.currentNode.textContent);if(value)text.push(value);
    }
    const table=[...document.querySelectorAll('table')].find(t=>t.tHead?.rows[0]?.cells.length===21);
    const scripts=[...document.scripts].map(s=>s.textContent).join('\n');
    return {text,rows:[...table.tBodies[0].rows].map(r=>[...r.cells].map(c=>{
      const clone=c.cloneNode(true);clone.querySelectorAll('[data-company-pdf]').forEach(a=>a.remove());
      return normalize(clone.textContent);
    })),
      assessment:JSON.parse(document.getElementById('assessment-data').textContent),
      portfolio:scripts.match(/const ZP = "([^"]+)"/)[1],
      links:[...document.querySelectorAll('a')].map(a=>a.getAttribute('href'))};
  });
}
function containsAll(before,after,label){
  const counts=new Map();for(const item of after)counts.set(item,(counts.get(item)||0)+1);
  for(const item of before){assert.ok(counts.get(item)>0,label+': '+item);counts.set(item,counts.get(item)-1);}
}
(async()=>{
  const executablePath=process.env.DASHBOARD_BROWSER_EXECUTABLE;
  const browser=await chromium.launch({headless:true,...(executablePath?{executablePath}:{}),
    args:['--no-sandbox','--disable-gpu','--disable-software-rasterizer','--use-gl=disabled','--disable-webgl']});
  try{
    const before=path.resolve(process.env.DASHBOARD_BEFORE||'research-output/dashboard-before');
    const after=path.resolve(process.env.DASHBOARD_AFTER||'research-output/dashboard-after');
    for(const language of (process.env.DASHBOARD_LANGUAGES||'en,de,es').split(',')){
      const page=await browser.newPage({viewport:{width:1440,height:1000}});
      await page.route('https://**/*',r=>r.abort());
      if(process.env.DASHBOARD_CHART_JS){
        const chartSource=await fs.readFile(process.env.DASHBOARD_CHART_JS,'utf8');
        await page.route('https://cdn.jsdelivr.net/npm/chart.js@4',r=>r.fulfill({contentType:'text/javascript',body:chartSource}));
      }
      await page.clock.install({time:new Date('2026-10-25T20:00:00Z')});
      const errors=[];page.on('pageerror',e=>errors.push(e.message));
      await page.goto(pathToFileURL(path.join(before,`index.${language}.html`)).href);
      const original=await inventory(page);
      const url=pathToFileURL(path.join(after,`index.${language}.html`)).href;
      await page.goto(url);
      const current=await inventory(page);
      containsAll(original.text,current.text,'Original text missing');
      containsAll(original.links,current.links,'Original link missing');
      assert.deepEqual(current.rows,original.rows,'All 21 cells of every company must survive unchanged');
      assert.deepEqual(current.assessment,original.assessment,'Review/expiry inputs must survive unchanged');
      assert.equal(current.portfolio,original.portfolio,'Private portfolio payload must survive unchanged');
      assert.equal(await page.locator('#zielBox').getAttribute('data-open'),'0');
      assert.equal(await page.locator('.dashboard-section[open]').count(),0);
      assert.ok(await page.locator('#universe').evaluate(el=>el.getBoundingClientRect().top)<650);
      assert.equal(await page.locator('#master-table th:visible').count(),9);
      assert.equal(await page.locator('#master-table th').count(),21);
      const pdfs=await page.locator('#master-table [data-company-pdf]').evaluateAll(links=>links.map(a=>a.getAttribute('href')));
      assert.equal(pdfs.length,original.rows.length);
      assert.ok(pdfs.every(href=>href.endsWith('.'+language+'.pdf')),'Each edition must link to its own PDF language');
      await page.click('#dashboard-columns');
      assert.equal(await page.locator('#dashboard-columns').getAttribute('aria-pressed'),'true');
      assert.equal(await page.locator('#master-table th:visible').count(),21);
      await page.click('#dashboard-columns');
      await page.fill('#dashboard-query','zts');
      assert.deepEqual(await page.locator('#master-table tbody tr:visible').getAttribute('data-assessment'),'ZTS');
      await page.fill('#dashboard-query','Zoetis');
      assert.equal(await page.locator('#master-table tbody tr:visible').getAttribute('data-assessment'),'ZTS');
      await page.fill('#dashboard-query','__NO_MATCH__');
      assert.equal(await page.locator('#master-table tbody tr:visible').count(),0);
      assert.equal(await page.locator('#dashboard-empty').isVisible(),true);
      await page.click('#dashboard-reset');
      assert.equal(await page.locator('#master-table tbody tr:not([hidden])').count(),original.rows.length);
      const translatedSector=await page.locator('#master-table tbody tr').evaluateAll(rows=>
        rows.find(r=>r.dataset.dashboardSearch.includes(' Technology ')).cells[2].textContent.trim());
      await page.fill('#dashboard-query',translatedSector);
      assert.ok(await page.locator('#master-table tbody tr:visible').count()>0,'Search must match the displayed sector language');
      await page.fill('#dashboard-query',translatedSector.normalize('NFKD').replace(/\p{M}/gu,''));
      assert.ok(await page.locator('#master-table tbody tr:visible').count()>0,'Mobile searches may omit diacritics');
      await page.click('#dashboard-reset');
      const holdings=await page.locator('#master-table tr[data-dashboard-held="1"]').count();
      await page.check('#dashboard-held');
      assert.equal(await page.locator('#master-table tbody tr:visible').count(),holdings);
      await page.click('#dashboard-reset');
      await page.click('.dashboard-nav a[href="#market-context"]');
      assert.equal(await page.locator('#market-context').getAttribute('open'),'');
      if(process.env.DASHBOARD_CHART_JS){
        await page.waitForFunction(()=>[...document.querySelectorAll('#market-context canvas')].every(canvas=>{
          const chart=window.Chart.getChart(canvas);return chart && chart.width>100 && chart.height>100;
        }));
      }
      await page.locator('#market-context>summary').click();
      await page.click('.dashboard-nav a[href="#market-context"]');
      assert.equal(await page.locator('#market-context').getAttribute('open'),'','Same-hash navigation must reopen a closed group');
      await page.goto(url+'#decision-observations');
      assert.equal(await page.locator('#company-research').getAttribute('open'),'');
      await page.goto(url+'#ziel');
      assert.equal(await page.locator('#portfolio-section').getAttribute('open'),'');
      assert.equal(await page.locator('#zielBox').getAttribute('data-open'),'1');
      await page.goto(url+'?test=keyboard');
      await page.keyboard.type('ziel');
      assert.equal(await page.locator('#portfolio-section').getAttribute('open'),'','Existing keyboard shortcut must reveal the group');
      await page.locator('#portfolio-section>summary').click();
      await page.keyboard.type('ziel');
      assert.equal(await page.locator('#portfolio-section').getAttribute('open'),'','Shortcut must reopen an already decoded portfolio');
      await page.goto(url+'?test=uppercase#ZIEL');
      assert.equal(await page.locator('#portfolio-section').getAttribute('open'),'','Legacy case-insensitive hash must remain usable');
      await page.setViewportSize({width:390,height:844});
      await page.locator('.dashboard-section').evaluateAll(nodes=>nodes.forEach(n=>n.open=true));
      // Responsive charts resize asynchronously after a viewport/section change.
      await page.waitForFunction(()=>document.documentElement.scrollWidth<=innerWidth+1,
        undefined,{timeout:5000});
      assert.deepEqual(errors,[],language+' JavaScript errors');
      await page.goto(url);
      if(process.env.DASHBOARD_SCREENSHOTS){
        await page.screenshot({path:path.join(process.env.DASHBOARD_SCREENSHOTS,`dashboard-${language}-mobile.png`),fullPage:true});
        await page.setViewportSize({width:1440,height:1000});
        await page.screenshot({path:path.join(process.env.DASHBOARD_SCREENSHOTS,`dashboard-${language}-desktop.png`),fullPage:true});
      }
      await page.close();
      console.log(language+': all content, 21-column rows, source links, review JSON, portfolio payload and controls preserved');
    }
    const page=await browser.newPage({javaScriptEnabled:false});
    await page.route('https://**/*',r=>r.abort());
    await page.goto(pathToFileURL(path.join(after,'index.es.html')).href);
    assert.equal(await page.locator('#master-table th:visible').count(),21);
    assert.equal(await page.locator('#dashboard-controls').isVisible(),false);
    await page.locator('#model-controls>summary').click();
    assert.equal(await page.locator('#model-controls').getAttribute('open'),'');
    console.log('No-JavaScript full-table and native-section fallback passed');
  }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
