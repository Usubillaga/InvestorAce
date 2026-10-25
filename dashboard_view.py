"""Organize existing report fragments without changing their financial content."""
from html import escape


CSS = """
body{max-width:1480px;margin:auto}
body a{color:var(--cyan)}
#investorace-language-nav,#investorace-research-nav{background:transparent!important;border:0!important;padding:4px 0!important;margin:0 0 10px!important;font-size:12px;gap:10px 18px!important}
.dashboard-hero{padding:20px 0 8px}.dashboard-hero .lede{max-width:86ch}
.dashboard-stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:12px 0 18px}
.dashboard-stat{padding:14px 16px;border:1px solid var(--line);border-radius:10px;background:var(--panel)}
.dashboard-stat small{display:block;color:var(--mu);font-size:12px}.dashboard-stat strong{display:block;font-size:23px;font-variant-numeric:tabular-nums;margin-top:4px}
.dashboard-nav{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 22px}
.dashboard-nav a{padding:7px 12px;border:1px solid var(--line);border-radius:7px;font-size:13px;text-decoration:none}
.dashboard-nav a:hover,.dashboard-nav a:focus-visible{border-color:var(--cyan);background:#13202e}
#universe{scroll-margin-top:14px;margin-bottom:24px}
.dashboard-heading{display:flex;align-items:baseline;justify-content:space-between;gap:12px;flex-wrap:wrap}
.dashboard-heading p{color:var(--mu);font-size:12px;margin:0 0 10px}
.dashboard-controls:not([hidden]){display:flex;align-items:end;flex-wrap:wrap;gap:12px;padding:12px;margin:10px 0;border:1px solid var(--line);border-radius:10px;background:var(--panel)}
.dashboard-controls label{color:var(--mu);font-size:12px}.dashboard-search{flex:1 1 240px}.dashboard-search input{display:block;width:100%;margin-top:5px}
.dashboard-controls .dashboard-held{align-self:center;display:flex;align-items:center;gap:7px;min-height:44px}
.dashboard-controls button{font-size:12px;min-height:44px;padding:8px 12px}.dashboard-controls button[aria-pressed="true"]{outline:1px solid var(--cyan)}
#universe>.tw{max-height:580px;overflow:auto;overscroll-behavior:contain}
#master-table{min-width:920px}#master-table td{padding-top:12px;padding-bottom:12px}
#master-table[data-compact="true"] tr>:is(:nth-child(5),:nth-child(9),:nth-child(10),:nth-child(11),:nth-child(12),:nth-child(13),:nth-child(14),:nth-child(16),:nth-child(17),:nth-child(18),:nth-child(20),:nth-child(21)){display:none}
.dashboard-section{border:1px solid var(--line);border-radius:12px;background:var(--panel);margin:12px 0;scroll-margin-top:14px}
.dashboard-section>summary{padding:18px;font-weight:650;font-size:17px;list-style-position:inside}
.dashboard-section>summary span{display:block;font-size:12px;font-weight:400;color:var(--mu);margin:4px 0 0 20px}
.dashboard-section[open]>summary{border-bottom:1px solid var(--line);margin-bottom:0}
.dashboard-section-content{padding:16px;min-width:0;overflow-wrap:anywhere}.dashboard-section-content>.box:last-child{margin-bottom:0}
.dashboard-section-content .box>.mono{white-space:normal;overflow-wrap:anywhere}
.dashboard-section-content .lede .mono{white-space:normal;overflow-wrap:anywhere}
.dashboard-empty{padding:14px;color:var(--amber)}
@media(max-width:640px){.dashboard-stats{grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.dashboard-stat{padding:12px}.dashboard-stat strong{font-size:19px}.dashboard-hero{padding-top:12px}.dashboard-section>summary{font-size:15px;padding:14px}.dashboard-section-content{padding:10px}.dashboard-nav a{flex:1 1 auto;text-align:center}.dashboard-controls button{flex:1}.dashboard-controls .dashboard-held{flex:1 1 100%}#universe>.tw{max-height:62vh}}
"""

JS = r"""
(() => {
  const table=document.getElementById('master-table');
  if(!table) return;
  const rows=[...table.tBodies[0].rows], query=document.getElementById('dashboard-query');
  const held=document.getElementById('dashboard-held'), columns=document.getElementById('dashboard-columns');
  const count=document.getElementById('dashboard-count'), empty=document.getElementById('dashboard-empty');
  document.getElementById('dashboard-controls').hidden=false;
  table.dataset.compact='true';
  const normalize=value=>value.normalize('NFKD').replace(/\p{M}/gu,'').toLocaleLowerCase();
  function filter(){
    const term=normalize(query.value.trim());
    let visible=0;
    rows.forEach(row=>{
      row.hidden=!(normalize(row.dataset.dashboardSearch+' '+row.cells[2].textContent).includes(term)
        && (!held.checked || row.dataset.dashboardHeld==='1'));
      if(!row.hidden) visible++;
    });
    count.textContent=visible+' / '+rows.length;
    empty.hidden=visible!==0;
  }
  query.addEventListener('input',filter);held.addEventListener('change',filter);
  document.getElementById('dashboard-reset').addEventListener('click',()=>{
    query.value='';held.checked=false;filter();query.focus();
  });
  columns.addEventListener('click',()=>{
    const full=columns.getAttribute('aria-pressed')!=='true';
    columns.setAttribute('aria-pressed',String(full));table.dataset.compact=String(!full);
  });
  function openSection(hash){
    let id;try{id=decodeURIComponent(hash.slice(1));}catch(_){return;}
    const portfolio=id.toLowerCase()==='ziel';
    const target=document.getElementById(portfolio?'portfolio-section':id);
    if(!target) return;
    for(let node=target;node;node=node.parentElement){if(node.tagName==='DETAILS') node.open=true;}
    if(portfolio && typeof window.revealZiel==='function') window.revealZiel();
    requestAnimationFrame(()=>target.scrollIntoView({block:'start'}));
  }
  document.querySelector('[data-dashboard-nav]').addEventListener('click',event=>{
    const link=event.target.closest('a');if(link) openSection(link.hash);
  });
  window.addEventListener('hashchange',()=>openSection(location.hash));
  document.addEventListener('toggle',event=>{
    if(event.target.tagName==='DETAILS' && event.target.open){
      requestAnimationFrame(()=>{
        window.dispatchEvent(new Event('resize'));
        if(window.drawPortfolioCharts) window.drawPortfolioCharts();
      });
    }
  },true);
  if(location.hash) openSection(location.hash);
  filter();
})();
"""


def render(header, table, *, stats, sections):
    """Wrap trusted engine HTML; escape all newly supplied labels and counts."""
    cards = ''.join('<div class="dashboard-stat"><small>' + escape(label)
                    + '</small><strong>' + escape(str(value)) + '</strong></div>'
                    for label, value in stats)
    nav = '<a href="#universe">My universe</a>' + ''.join(
        '<a href="#' + escape(key, quote=True) + '">' + escape(title) + '</a>'
        for key, title, _, _ in sections)
    groups = ''.join('<details class="dashboard-section" id="' + escape(key, quote=True)
                     + '"><summary>' + escape(title) + '<span>' + escape(description)
                     + '</span></summary><div class="dashboard-section-content">' + content
                     + '</div></details>' for key, title, description, content in sections)
    return ('<main id="investorace-dashboard"><header class="dashboard-hero">' + header
            + '</header><div class="dashboard-stats">' + cards
            + '</div><nav class="dashboard-nav" data-dashboard-nav aria-label="Report sections">'
            + nav + '</nav><section id="universe" aria-labelledby="universe-title">'
            '<div class="dashboard-heading"><h2 id="universe-title">My universe</h2>'
            '<p>Model scores and reviewed ratings remain separate.</p></div>'
            '<div class="dashboard-controls" id="dashboard-controls" hidden>'
            '<label class="dashboard-search">Find a company<input id="dashboard-query" '
            'type="search" placeholder="Ticker, company or sector" aria-controls="master-table"></label>'
            '<label class="dashboard-held"><input type="checkbox" id="dashboard-held" '
            'aria-controls="master-table">My holdings only</label>'
            '<button type="button" id="dashboard-columns" aria-pressed="false" '
            'aria-controls="master-table">All columns</button>'
            '<button type="button" id="dashboard-reset">Reset filters</button>'
            '<output id="dashboard-count" aria-live="polite"></output></div>' + table
            + '<p id="dashboard-empty" class="dashboard-empty" hidden>No matching companies. Reset filters to show the full universe.</p>'
            '</section>' + groups + '</main>')
