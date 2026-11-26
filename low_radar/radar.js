/* One renderer for the InvestorAce scoreboard and Tradingdesk. */
const LowRadar = (() => {
  const words = {
    en: {
      nav:'52-week radar', title:'Nearest to a 52-week low', coverage:'eligible listings', universe:'InvestorAce universe', updated:'Snapshot',
      company:'Company / ticker', distance:'Above low', change:'Day change', price:'Price', low:'52-week low', cap:'Market cap · bn', pe:'P/E', time:'Quote · UTC',
      details:'Data and calculation', method:'Ranked by 100 × (price ÷ 52-week low − 1), using unrounded values. Up to 30 equities with matching Yahoo Finance quotes from the preceding five days qualify for display. Daily change uses the previous regular-session close.',
      source:'Prices and lows use the listing currency. Market cap and reported P/E come from the same-day InvestorAce valuation. Cap is in billions of the currency shown. A dash indicates an unavailable figure.',
      stale:'Archived snapshot', empty:'No eligible quotes in this snapshot.', saved:'Saved snapshot', lang:'Language'
    },
    es: {
      nav:'Radar de 52 semanas', title:'Más cerca de su mínimo de 52 semanas', coverage:'cotizaciones válidas', universe:'Universo InvestorAce', updated:'Captura',
      company:'Empresa / ticker', distance:'Sobre el mínimo', change:'Variación diaria', price:'Cotización', low:'Mín. 52 sem.', cap:'Capitalización · mil M', pe:'PER', time:'Cotización · UTC',
      details:'Datos y cálculo', method:'Orden según 100 × (cotización ÷ mínimo de 52 semanas − 1), antes de redondear. Se muestran hasta 30 acciones con cotizaciones válidas de Yahoo Finance de los últimos cinco días. La variación diaria se calcula frente al cierre de la sesión anterior.',
      source:'La cotización y el mínimo figuran en la divisa del mercado. La capitalización y el PER sobre beneficios declarados proceden de la valoración de InvestorAce del mismo día. La capitalización se expresa en miles de millones de la divisa indicada. Un guion indica un dato no disponible.',
      stale:'Captura histórica', empty:'Esta captura no contiene cotizaciones válidas.', saved:'Captura guardada', lang:'Idioma'
    },
    de: {
      nav:'52-Wochen-Radar', title:'Am nächsten am 52-Wochen-Tief', coverage:'gültige Kurse', universe:'InvestorAce-Universum', updated:'Datenstand',
      company:'Unternehmen / Ticker', distance:'Über dem Tief', change:'Tagesänderung', price:'Kurs', low:'52-Wochen-Tief', cap:'Börsenwert · Mrd.', pe:'KGV', time:'Kurszeit · UTC',
      details:'Daten und Berechnung', method:'Sortiert nach 100 × (Kurs ÷ 52-Wochen-Tief − 1), vor dem Runden. Angezeigt werden bis zu 30 Aktien mit passenden Yahoo-Finance-Kursen der letzten fünf Tage. Die Tagesänderung bezieht sich auf den vorherigen regulären Schlusskurs.',
      source:'Kurs und Tief stehen in der Handelswährung. Börsenwert und KGV auf Basis des ausgewiesenen Gewinns stammen aus der InvestorAce-Bewertung desselben Tages. Der Börsenwert steht in Milliarden der angegebenen Währung. Ein Strich kennzeichnet fehlende Angaben.',
      stale:'Archivierter Datenstand', empty:'Dieser Datenstand enthält keine gültigen Kurse.', saved:'Gespeicherter Datenstand', lang:'Sprache'
    }
  };
  const names = {en:'English', es:'Español', de:'Deutsch'};
  const home = {en:'index.html', es:'index.es.html', de:'index.de.html'};
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  function draw(data, lang, desk=false, saved=false) {
    const w=words[lang];
    const format=new Intl.NumberFormat(lang,{minimumFractionDigits:2,maximumFractionDigits:2});
    const number=v=>Number.isFinite(v)?format.format(v):'—';
    const date=v=>new Intl.DateTimeFormat(lang,{day:'2-digit',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit',timeZone:'UTC',hourCycle:'h23'}).format(new Date(v));
    const links=Object.entries(names).map(([code,name])=>{
      const target=desk?'?lang='+code:home[code];
      return `<a href="${target}#low-radar" lang="${code}" hreflang="${code}" ${code===lang?'aria-current="true"':''}>${name}</a>`;
    }).join('');
    const max=data.rows.at(-1)?.distance || 1;
    const rows=data.rows.map((r,i)=>{
      const scale=Math.min(1,Math.max(0,r.distance/max));
      const change=Number.isFinite(r.change)?(r.change>0?'+':'')+number(r.change)+'%':'—';
      return `<tr><td class="lr-rank">${i+1}</td><th scope="row"><a href="https://finance.yahoo.com/quote/${encodeURIComponent(r.symbol)}/">${esc(r.name)}</a><small>${esc(r.exchange)} · ${esc(r.symbol)}</small></th>
        <td class="lr-distance"><strong>${number(r.distance)}%</strong><span class="lr-track" aria-hidden="true"><i style="width:${scale*100}%;background:hsl(${150-145*scale} 65% 42%)"></i></span></td>
        <td class="${r.change>0?'lr-up':r.change<0?'lr-down':''}">${change}</td><td>${number(r.price)} ${esc(r.currency)}</td><td>${number(r.low)} ${esc(r.currency)}</td>
        <td>${r.market_cap==null?'—':number(r.market_cap/1e9)+' '+esc(r.cap_currency)}</td><td>${number(r.pe)}</td><td><time datetime="${esc(r.observed)}">${esc(date(r.observed))}</time></td></tr>`;
    }).join('');
    const old=Date.now()-Date.parse(data.captured)>5*86400000;
    return `<div class="lr" lang="${lang}"><header><div><p>${w.universe}</p><h2>${w.title}</h2></div><nav aria-label="${w.lang}">${links}</nav></header>
      <div class="lr-meta"><span><b>Top ${data.rows.length}</b> · ${data.eligible} / ${data.universe} ${w.coverage}</span>
      <span>${old?w.stale:saved?w.saved:w.updated} · ${esc(date(data.captured))} UTC</span></div>
      ${rows?`<div class="lr-scroll" role="region" aria-label="${w.title}" tabindex="0"><table><thead><tr>${['#',w.company,w.distance,w.change,w.price,w.low,w.cap,w.pe,w.time].map(s=>'<th scope="col">'+s+'</th>').join('')}</tr></thead><tbody>${rows}</tbody></table></div>`:`<p>${w.empty}</p>`}
      <details><summary>${w.details}</summary><p>${w.method}</p><p>${w.source}</p></details></div>`;
  }
  return {draw,words};
})();
if (typeof module!=='undefined' && require.main===module) {
  const data=JSON.parse(require('node:fs').readFileSync(0,'utf8'));
  process.stdout.write(JSON.stringify(Object.fromEntries(Object.keys(LowRadar.words).map(lang=>[lang,LowRadar.draw(data,lang)]))));
}
