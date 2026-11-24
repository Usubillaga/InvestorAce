/* The publisher and browser use this same read-only HTML renderer. */
function paperPanel(language, data, words, model) {
  const t = words[language];
  const esc = x => String(x ?? '—').replace(/[&<>"']/g, c =>
    ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const money = (x, currency='USD') => Number.isFinite(x)
    ? x.toLocaleString(language,{style:'currency',currency,currencyDisplay:'code'}) : '—';
  const pct = x => Number.isFinite(x) ? x.toLocaleString(language,{style:'percent',maximumFractionDigits:2}) : '—';
  const number = x => Number.isFinite(x) ? x.toLocaleString(language,{maximumFractionDigits:3}) : '—';
  const time = stamp => new Intl.DateTimeFormat(language,{dateStyle:'medium',timeStyle:'short',timeZone:'America/New_York'}).format(new Date(stamp))+' NY';
  const url = (label, href) => typeof href==='string' && href.startsWith('https://')
    ? '<a href="'+esc(href)+'">'+esc(label)+'</a>' : esc(label);
  const study = 'heat-comparison'+({es:'',en:'.en',de:'.de'}[language])+'.html';
  function table(head, rows) {
    return '<div class="pp-scroll" tabindex="0"><table><thead><tr>'+head.map(h=>'<th scope="col">'+esc(h)+'</th>').join('')+
      '</tr></thead><tbody>'+rows.map(r=>'<tr>'+r.map(v=>'<td>'+esc(v)+'</td>').join('')+'</tr>').join('')+'</tbody></table></div>';
  }
  function metrics(rows) {
    return '<dl>'+rows.map(([k,v])=>'<dt>'+esc(k)+'</dt><dd>'+esc(v)+'</dd>').join('')+'</dl>';
  }
  const selection=data.overlap.selection;
  const books=[model.original(data.original),model.concentrated(data.overlap,5),model.concentrated(data.overlap,6)];
  const labels={original:t.original,5:t.five,6:t.six};
  function next(b) {
    if (b.pending) return t[b.pending.side]+' · '+t.target+' '+b.pending.target;
    if (b.entry) return b.eligible && b.asOf<b.eligible ? t.locked+' '+b.eligible : t.sellRule;
    return b.size && selection && selection.candidates.length<b.size ? t.blocked : t.wait;
  }
  function card(b) {
    const start=b.start && new Intl.DateTimeFormat('sv-SE',{timeZone:'America/New_York'}).format(new Date(b.start));
    const mark=start && start>b.asOf ? [t.openingBalance,start] : [t.asOf,b.asOf];
    const state=b.pending?t.pending:b.entry?t.invested:t.cashState;
    return '<article data-book="'+b.key+'"><h3>'+esc(labels[b.key])+'</h3><span class="pp-state">'+esc(state)+'</span>'+
      '<strong class="pp-value">'+esc(money(b.nav))+'</strong><p>'+esc(t.result)+' '+esc(pct(b.nav/b.initial-1))+'</p>'+
      metrics([[t.cash,money(b.cash)],[t.holdings,b.holdings.length],mark])+
      '<p><b>'+esc(t.next)+'</b> · '+esc(next(b))+'</p><a href="#panic-paper-'+b.key+'">'+esc(t.show)+'</a></article>';
  }
  function bookDetails(b) {
    const orders=[...b.events].reverse();
    if(b.pending) orders.unshift({day:b.pending.target,status:b.pending.side,order:b.pending});
    const rows=b.holdings.map(h=>[h.symbol,pct(h.value/b.nav),money(h.value),money(h.cost),money(h.value-h.cost),money(h.price),number(h.units)]);
    const journal=orders.map(event=>{
      const a=model.audit(event);
      return '<li><b>'+esc(t[a.status])+' · '+esc(a.day)+'</b> '+esc(a.symbols.join(' / '))+
        '<br>'+esc(t.signal)+' '+esc(a.signalTime?time(a.signalTime):a.dayOfSignal)+' · '+esc(number(a.heat))+
        '/100 · '+esc(t.posted)+' '+esc(time(a.submitted))+(a.source?' · '+url(t.readingLink,a.source):'')+'</li>';
    }).join('');
    const warnings=b.warnings.map(x=>esc(x==='NO_NEW_READING'?t.noNew:x));
    if(b.missed.length) warnings.push(esc(t.missed)+' · '+esc(b.missed.join(', ')));
    return '<details id="panic-paper-'+b.key+'"><summary>'+esc(labels[b.key])+' · '+esc(t.show)+'</summary>'+
      '<p>'+esc(b.size?t.overlapRule:t.originalRule)+'</p>'+
      metrics([[t.initial,money(b.initial)],[t.fee,pct(.001)],...(b.start?[[t.started,time(b.start)]]:[]),
        ...(b.entry?[[t.open,b.entry]]:[]),...(b.eligible?[[t.locked,b.eligible]]:[])])+
      '<h4>'+esc(t.holdings)+'</h4>'+(rows.length?table([t.security,t.weight,t.position,t.basis,t.pnl,t.price,t.units],rows):'<p>'+esc(t.empty)+'</p>')+
      '<h4>'+esc(t.bench)+'</h4>'+metrics(Object.entries(b.controls).map(([k,v])=>[k,money(v)+' · '+pct(v/b.initial-1)]))+
      '<h4>'+esc(t.history)+'</h4>'+(journal?'<ol>'+journal+'</ol>':'<p>'+esc(t.waiting)+'</p>')+
      (warnings.length?'<p>'+esc(t.checks)+' · '+warnings.join(' · ')+'</p>':'')+
      '<p>'+url(t.ledger,'https://github.com/Usubillaga/InvestorAce-Tradingdesk/blob/main/dist/'+(b.size?'heat-overlap.json':'heat-account.json'))+'</p></details>';
  }
  const reading=model.latestReading(data.original,data.overlap);
  let indicator=t.noReading;
  if(reading) {
    const gap=reading.heat-20;
    indicator='<strong>'+esc(number(reading.heat))+' / 100</strong> · '+url((reading.intraday?t.intraday:t.close)+' · '+time(reading.as_of),reading.url)+
      '<br>'+esc(gap>0?number(gap)+' '+t.distance:gap===0?t.boundary:t.zone);
  }
  let ranks='<p>'+esc(t.noWeights)+'</p>';
  if(selection) {
    const n=selection.candidates.length;
    ranks=table(['#',t.security,'SPY','QQQ',t.five,t.six],selection.candidates.map((c,i)=>
      [i+1,c.name+' · '+c.classes.join(' / '),pct(c.weights.SPY),pct(c.weights.QQQ),n>=5&&i<5?pct(1/5):'—',n>=6&&i<6?pct(1/6):'—']))+
      '<p>'+esc(t.selection)+' · '+esc(time(selection.checked))+' · '+Object.entries(selection.sources).map(([f,v])=>url(f+' '+v.date,v.url)).join(' · ')+'</p>';
  }
  const refs=(data.claude||[]).map((a,i)=>{
    const m=a.marks.at(-1), cur=a.currency||'USD';
    return [i===2?t.special:t.mix,t.below+' '+a.level,(a.basket_spec||[]).map(([k,w])=>pct(w)+' '+(k==='top10'?'Top 10':k)).join(' + '),
      money(a.capital,cur),money(m?.equity,cur),money(a.cash,cur),m?.date||'—'];
  });
  return '<h2>'+esc(t.title)+'</h2><p>'+esc(t.intro)+'</p><section class="pp-signal"><h3>'+esc(t.thermo)+'</h3><p>'+indicator+'</p></section>'+
    '<div class="pp-books">'+books.map(card).join('')+'</div><h3>'+esc(t.detail)+'</h3>'+books.map(bookDetails).join('')+
    '<details id="panic-paper-candidates"><summary>'+esc(t.candidates)+'</summary><p>'+esc(t.method)+'</p>'+ranks+'</details>'+
    (refs.length?'<details id="panic-paper-claude"><summary>'+esc(t.external)+'</summary><p>'+esc(t.externalNote)+'</p>'+
      table([t.strategy,t.rule,t.allocation,t.initial,t.value,t.cash,t.dated],refs)+'<p><a href="index-leaders.html">'+esc(t.claudeLink)+'</a></p></details>':'')+
    '<p class="pp-studies"><a href="'+study+'">'+esc(t.study)+'</a> · <a href="heat-archive'+(language==='en'?'.en':'')+'.html#historia">Backtest · SPY / QQQ / DIA</a></p>';
}

if (typeof module!=='undefined' && require.main===module) {
  const fs=require('node:fs'), data=JSON.parse(fs.readFileSync(0,'utf8'));
  const words=require('./heat-paper-i18n.js'), model=require('./heat-paper-model.js');
  const pages=Object.fromEntries(['es','de','en'].map(lang=>[lang,paperPanel(lang,data,words,model)]));
  process.stdout.write(JSON.stringify(pages));
}
