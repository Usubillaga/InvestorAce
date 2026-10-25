// Serve the built site and set PDF_SITE_URL, then run with optional PDF_BROWSER_EXECUTABLE.
const assert=require('node:assert/strict');
const fs=require('node:fs/promises');
const {chromium}=require('playwright');

(async()=>{
  const executablePath=process.env.PDF_BROWSER_EXECUTABLE;
  const browser=await chromium.launch({headless:true,...(executablePath?{executablePath}:{}),
    args:['--no-sandbox','--disable-gpu','--disable-software-rasterizer','--use-gl=disabled','--disable-webgl']});
  try{
    const base=process.env.PDF_SITE_URL||'http://127.0.0.1:8765';
    const page=await browser.newPage({acceptDownloads:true});
    await page.route('https://**/*',r=>r.abort());
    const errors=[];page.on('pageerror',e=>errors.push(e.message));
    async function download(selector,filename){
      const pending=page.waitForEvent('download');await page.click(selector);
      const result=await pending;
      assert.equal(result.suggestedFilename(),filename);
      const bytes=await fs.readFile(await result.path());
      assert.equal(bytes.subarray(0,5).toString(),'%PDF-');
      return bytes;
    }
    await page.goto(base+'/index.es.html');
    await page.fill('#dashboard-query','ZTS');
    const main=await download('[data-company-pdf="ZTS"]','ZTS.es.pdf');
    await page.goto(base+'/scanner.html?view=universe&ticker=ZTS');
    const universe=await download('.pdf-downloads a[lang="es"]','ZTS.es.pdf');
    assert.ok(main.equals(universe),'Main and scanner must download the same universe analysis');
    const data=JSON.parse(await page.locator('#scanner-data').textContent());
    const candidate=data.market.candidates[0];
    await page.goto(base+'/scanner.html?view=market&ticker='+encodeURIComponent(candidate.ticker));
    await download('.pdf-downloads a[lang="es"]',candidate.ticker+'.es.pdf');
    const url=await page.locator('.pdf-downloads a[lang="es"]').getAttribute('href');
    assert.ok(url.startsWith('analysis-pdfs/market/'),'Market method must use its own PDF');
    const allUrls=new Set(data.rows.flatMap(row=>Object.values(row.pdf_urls))
      .concat(data.market.candidates.flatMap(row=>Object.values(row.pdf_urls))));
    for(const url of allUrls){
      const response=await page.request.head(base+'/'+url);
      assert.equal(response.status(),200,'Missing linked PDF: '+url);
      assert.match(response.headers()['content-type'],/application\/pdf/);
    }
    assert.deepEqual(errors,[]);
    console.log('Real main/scanner PDF downloads passed; '+allUrls.size+' linked language/scope PDFs return HTTP200/application-pdf.');
  }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
