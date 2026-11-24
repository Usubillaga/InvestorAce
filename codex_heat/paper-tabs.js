(() => {
  const panel=document.getElementById('panic-paper');
  if (!panel) return;
  const content=panel.querySelector('[data-paper-content]');
  const primary=document.getElementById('ia-primary');
  const tabs=[...document.querySelectorAll('.ia-paper-tabs [role="tab"]')];
  const lang=panel.dataset.language;
  const data=JSON.parse(document.getElementById('ia-paper-data').textContent);
  const remote='https://raw.githubusercontent.com/Usubillaga/InvestorAce-Tradingdesk/main/dist/';
  let checked=0;
  let refreshing=false;

  function activate(key, focus=false) {
    const paper=key==='panic-paper';
    primary.hidden=paper;
    panel.hidden=!paper;
    for(const tab of tabs) {
      const current=tab.getAttribute('aria-controls')===key;
      tab.setAttribute('aria-selected',String(current));
      tab.tabIndex=current?0:-1;
      if(focus && current) tab.focus();
    }
    if(paper) refresh();
  }
  function followHash() {
    const id=location.hash.slice(1);
    const isPaper=id==='panic-paper'||id.startsWith('panic-paper-');
    activate(isPaper?'panic-paper':'ia-primary');
    const target=isPaper && document.getElementById(id);
    if(target && target.tagName==='DETAILS') {
      target.open=true;
      target.scrollIntoView({block:'start'});
    }
  }
  function switchTab(tab,focus=false) {
    const id=tab.getAttribute('aria-controls');
    const hash=id==='panic-paper'?'#panic-paper':'';
    if(location.hash!==hash) history.pushState(null,'',location.pathname+location.search+hash);
    activate(id,focus);
  }
  tabs.forEach((tab,i)=>{
    tab.addEventListener('click',()=>switchTab(tab));
    tab.addEventListener('keydown',e=>{
      if(!['ArrowRight','ArrowLeft','Home','End'].includes(e.key)) return;
      e.preventDefault();
      switchTab(tabs[e.key==='Home'?0:e.key==='End'?tabs.length-1:1-i],true);
    });
  });
  async function load(name,check,previous) {
    try {
      const r=await fetch(remote+name,{cache:'no-store',signal:AbortSignal.timeout(6000)});
      if(!r.ok) return previous;
      const next=await r.json();
      return next.schema===1 && next.as_of>=previous.as_of && check(next) ? next : previous;
    } catch {return previous;}
  }
  async function refresh() {
    if(refreshing || Date.now()-checked<60000) return;
    refreshing=true;checked=Date.now();
    try {
      const [original,overlap]=await Promise.all([
        load('heat-account.json', s=>Number.isFinite(s.equity)&&Array.isArray(s.history),data.original),
        load('heat-overlap.json', s=>s.books?.[5]&&s.books?.[6],data.overlap)
      ]);
      if(JSON.stringify(original)===JSON.stringify(data.original) && JSON.stringify(overlap)===JSON.stringify(data.overlap)) return;
      const updated=paperPanel(lang,{...data,original,overlap},paperWords,PaperModel);
      const open=[...content.querySelectorAll('details[open]')].map(d=>d.id);
      const focused=document.activeElement?.closest('details')?.id;
      content.innerHTML=updated;
      data.original=original;data.overlap=overlap;
      for(const id of open) {const d=document.getElementById(id);if(d) d.open=true;}
      if(focused) document.getElementById(focused)?.querySelector('summary')?.focus({preventScroll:true});
    } catch { /* Keep the complete, dated published snapshot. */ }
    finally {refreshing=false;}
  }
  window.addEventListener('popstate',followHash);
  window.addEventListener('hashchange',followHash);
  document.addEventListener('visibilitychange',()=>{if(!document.hidden&&!panel.hidden) refresh();});
  panel.addEventListener('click',e=>{
    const a=e.target.closest('a[href^="#panic-paper-"]');
    if(a && a.hash===location.hash) followHash();
  });
  followHash();
})();
