/* Both Pages sites display the same InvestorAce report. All amounts are in EUR. */
const RoundTwo = (() => {
  const words = {
    de: {
      title:'Paper-Runde 2', subtitle:'Regelportfolio und Scoremodell', rules:'Regelportfolio', score:'Scoremodell',
      start:'Einstieg', end:'Geplanter Schluss', mark:'Bewerteter Handelstag', open:'Offen', before:'Vor Handelskosten',
      capital:'Startvermögen', invested:'Investiert am Einstieg', cash:'Cash am Einstieg', cashPct:'Cashquote am Einstieg',
      nav:'Kontowert', pnl:'Gewinn / Verlust', ret:'Kontorendite', stocks:'Rendite des Aktienanteils', gap:'Regeln minus Score',
      index:'S&P 500 · Preisrendite', excess:'Abstand zum S&P 500', risk:'Max. Drawdown seit Einstieg', dates:'Hoch / Tief',
      values:'Kontovergleich', costs:'Umsatz und Handelskosten', volume:'Umsatz beim Einstieg', trades:'Geänderte Positionen',
      sim:'Kosten bei 0,05 % Umsatz (Modell)', final:'Abschluss', finalNav:'Schlussvermögen vor Kosten', finalRet:'Schlussrendite vor Kosten',
      fees:'Belegte Handelskosten', income:'Dividenden / Cashzinsen', net:'Schlussvermögen nach Kosten', netRet:'Nettorendite', netGap:'Nettoabstand',
      holdings:'Positionen', ticker:'Titel', unit:'Stück', px:'Einstiegskurs', close:'Letzter Kurs', series:'Tägliche Kontowerte', day:'Handelstag',
      basis:'Die Kontorendite bezieht sich auf das volle Startvermögen einschließlich Cash. Ganze Stückzahlen und EUR/USD-Modellkurs bleiben fix. Der Drawdown verwendet die vollständige Reihe der Tagesschlusswerte.',
      costNote:'Beide Varianten starten für die Kostenrechnung aus demselben Vorbestand. Das Szenario kostet 5 Basispunkte je gehandeltem Euro. Der Schlusskurs löst keinen Verkauf aus. Nettowerte erfordern belegte Kosten, Dividenden und Zinsen.',
      missing:'Fehlende Kurse', sources:'Quellen', proof:'Abschlussbelege eintragen', inputs:'Eingefrorene Portfolios', archive:'Kursarchiv',
      error:'Vergleichsdaten konnten nicht geladen werden.', cache:'Lokaler Datenstand · Aktualisierung nicht verfügbar',
      holiday:'Am 26.11. gelten für US-Werte die Schlusskurse des 25.11. WKL wird zum Amsterdamer Tagesschluss bewertet.'
    },
    en: {
      title:'Paper round 2', subtitle:'Rules portfolio and score-only model', rules:'Rules portfolio', score:'Score model',
      start:'Entry',end:'Scheduled close',mark:'Valuation date',open:'Pending',before:'Before trading costs',
      capital:'Opening NAV',invested:'Invested at entry',cash:'Cash at entry',cashPct:'Opening cash allocation',
      nav:'Account value',pnl:'Profit / loss',ret:'Account return',stocks:'Equity sleeve return',gap:'Rules minus score',
      index:'S&P 500 price return',excess:'Excess vs S&P 500',risk:'Max drawdown since entry',dates:'Peak / trough',
      values:'Account comparison',costs:'Turnover and trading costs',volume:'Opening traded value',trades:'Positions traded',
      sim:'Cost at 0.05% of turnover (model)',final:'Settlement',finalNav:'Closing NAV before costs',finalRet:'Closing return before costs',
      fees:'Verified trading costs',income:'Dividends / cash interest',net:'Closing NAV after costs',netRet:'Net return',netGap:'Net return spread',
      holdings:'Holdings',ticker:'Listing',unit:'Shares',px:'Entry close',close:'Latest close',series:'Daily account values',day:'Session',
      basis:'Account returns use the full opening NAV including cash. Whole-share positions and the EUR/USD conversion are fixed. Drawdown uses the complete daily closing series.',
      costNote:'Both variants rebalance from the same prior holdings. The scenario charges 5 basis points on value traded. The end mark does not trigger a sale. Net figures require verified trading costs, dividends and cash interest.',
      missing:'Missing closes',sources:'Sources',proof:'Enter settlement evidence',inputs:'Frozen portfolios',archive:'Price archive',
      error:'Comparison data could not be loaded.',cache:'Local snapshot · update unavailable',
      holiday:'On 26 Nov, US listings carry the 25 Nov close. WKL uses its Amsterdam closing price.'
    },
    es: {
      title:'Ronda de papel 2',subtitle:'Cartera con reglas y modelo por puntuación',rules:'Cartera con reglas',score:'Modelo por puntuación',
      start:'Entrada',end:'Cierre previsto',mark:'Fecha de valoración',open:'Pendiente',before:'Antes de costes',
      capital:'Patrimonio inicial',invested:'Invertido al entrar',cash:'Efectivo al entrar',cashPct:'Efectivo inicial (%)',
      nav:'Valor de la cuenta',pnl:'Ganancia / pérdida',ret:'Rentabilidad de la cuenta',stocks:'Rentabilidad de las acciones',gap:'Reglas menos puntuación',
      index:'S&P 500 · variación de precio',excess:'Diferencia frente al S&P 500',risk:'Caída máxima desde la entrada',dates:'Máximo / mínimo',
      values:'Comparación de cuentas',costs:'Volumen y costes',volume:'Volumen negociado al entrar',trades:'Posiciones modificadas',
      sim:'Coste del 0,05 % del volumen (modelo)',final:'Cierre de la ronda',finalNav:'Patrimonio final antes de costes',finalRet:'Rentabilidad final antes de costes',
      fees:'Costes de negociación verificados',income:'Dividendos / intereses',net:'Patrimonio final tras costes',netRet:'Rentabilidad neta',netGap:'Diferencia neta',
      holdings:'Posiciones',ticker:'Valor',unit:'Acciones',px:'Precio de entrada',close:'Último cierre',series:'Valor diario de las cuentas',day:'Sesión',
      basis:'La rentabilidad usa todo el patrimonio inicial, incluido el efectivo. Se mantienen los títulos enteros y el cambio fijo EUR/USD. La caída máxima exige la serie completa de cierres diarios.',
      costNote:'Ambas variantes parten de las mismas posiciones previas para medir los costes. El escenario aplica 5 puntos básicos al volumen negociado. La valoración final no genera una venta. El cálculo neto exige costes, dividendos e intereses documentados.',
      missing:'Cierres pendientes',sources:'Fuentes',proof:'Registrar comprobantes del cierre',inputs:'Carteras originales',archive:'Archivo de cotizaciones',
      error:'No se han podido cargar los datos.',cache:'Copia local · actualización no disponible',
      holiday:'El 26/11 los valores de EE. UU. conservan el cierre del 25/11. WKL usa el cierre de Ámsterdam.'
    }
  };
  const safe = value => String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const valid = Number.isFinite;
  const ratio = (value,base) => valid(value) && base > 0 ? 100*(value-base)/base : null;
  const diff = (a,b) => valid(a) && valid(b) ? a-b : null;
  const root = 'https://github.com/Usubillaga/InvestorAce/';
  function draw(d, lang, cached=false) {
    const w=words[lang] || words.en;
    const fmt=new Intl.NumberFormat(lang,{minimumFractionDigits:2,maximumFractionDigits:2});
    const number=(x,suffix='')=>valid(x)?fmt.format(x)+suffix:w.open;
    const eur=x=>number(x,' €'), pct=x=>number(x,' %'), pp=x=>number(x,' pp');
    const [a,b]=[d.accounts.rules,d.accounts.score];
    const nav=x=>x.days.at(-1)?.nav;
    const ret=x=>ratio(nav(x),x.capital), net=x=>ratio(x.net_nav,x.capital);
    const bm=ratio(d.benchmark[d.mark],d.benchmark[d.entry]);
    const table=(headers,rows)=>'<div class="r2-scroll"><table><thead><tr>'+headers.map(t=>'<th scope="col">'+safe(t)+'</th>').join('')+
      '</tr></thead><tbody>'+rows.map(row=>'<tr>'+row.map((v,i)=>i?'<td>'+safe(v)+'</td>':'<th scope="row">'+safe(v)+'</th>').join('')+'</tr>').join('')+'</tbody></table></div>';
    const accounts=rows=>table(['',w.rules,w.score],rows.map(([label,fn])=>[label,fn(a),fn(b)]));
    const section=(title,body)=>'<h3>'+safe(title)+'</h3>'+body;
    const symbols=[...new Set([...a.positions,...b.positions].map(p=>p.symbol))].sort();
    const holdings=symbols.map(symbol=>{
      const first=a.positions.find(p=>p.symbol===symbol), second=b.positions.find(p=>p.symbol===symbol);
      const p=first||second;
      return [symbol,number(p.entry,' '+p.currency),number(p.close,' '+p.currency),first?.shares??(a.positions.length?0:w.open),second?.shares??(b.positions.length?0:w.open)];
    });
    const dates=x=>x.peak_day && x.trough_day ? x.peak_day+' / '+x.trough_day : w.open;
    const normalizedNote=lang==='de'?'Fixkurs':lang==='es'?'Cambio fijo':'Fixed FX';
    const allocation=[a,b].map((x,i)=>{
      if(!valid(x.invested) || !valid(x.cash) || !(x.capital>0)) return '';
      const invested=100*x.invested/x.capital;
      return '<div class="r2-allocation"><b>'+[w.rules,w.score][i]+'</b><span>'+w.invested+' '+pct(invested)+'</span>'+
        '<div class="r2-track" aria-hidden="true"><i style="width:'+Math.min(100,Math.max(0,invested))+'%"></i></div>'+
        '<span>'+w.cash+' '+pct(100*x.cash/x.capital)+'</span></div>';
    }).join('');
    return '<div class="r2" lang="'+safe(lang)+'"><h2>'+w.title+'</h2><p>'+w.subtitle+'</p><p>'+w.start+' <b>'+safe(d.entry)+'</b> · '+w.end+' <b>'+safe(d.end)+'</b> · '+w.mark+' <b>'+safe(d.mark||w.open)+'</b></p>'+
      (cached?'<p role="status">'+w.cache+'</p>':'')+
      '<div class="r2-allocation-grid">'+allocation+'</div>'+section(w.values,accounts([[w.capital,x=>eur(x.capital)],[w.invested,x=>eur(x.invested)],[w.cash,x=>eur(x.cash)],[w.cashPct,x=>pct(valid(x.cash)?100*x.cash/x.capital:null)],
        [w.nav,x=>eur(nav(x))],[w.pnl,x=>eur(diff(nav(x),x.capital))],[w.ret,x=>pct(ret(x))],[w.stocks,x=>pct(ratio(diff(nav(x),x.cash),x.invested))],
        [w.index,()=>pct(bm)],[w.excess,x=>pp(diff(ret(x),bm))],[w.risk,x=>pct(x.drawdown)],[w.dates,dates]]))+
      '<p><strong>'+w.gap+' · '+pp(diff(ret(a),ret(b)))+'</strong> ('+w.before+')</p><p>'+w.basis+' '+normalizedNote+' '+safe(d.fx)+' €/USD.</p>'+
      section(w.costs,accounts([[w.volume,x=>eur(x.volume)],[w.trades,x=>x.orders??w.open],[w.sim,x=>eur(valid(x.volume)?x.volume*.0005:null)]]))+'<p>'+w.costNote+'</p>'+
      section(w.final,accounts([[w.finalNav,x=>eur(x.final_nav)],[w.finalRet,x=>pct(ratio(x.final_nav,x.capital))],[w.fees,x=>eur(x.settlement?.costs_eur)],
        [w.income,x=>eur(x.settlement?.dividends_eur)+' / '+eur(x.settlement?.interest_eur)],[w.net,x=>eur(x.net_nav)],[w.netRet,x=>pct(net(x))]]))+
      '<p>'+w.netGap+' · '+pp(diff(net(a),net(b)))+'</p>'+
      '<details><summary>'+w.holdings+'</summary>'+table([w.ticker,w.px,w.close,w.unit+' · '+w.rules,w.unit+' · '+w.score],holdings)+'</details>'+
      '<details><summary>'+w.series+'</summary>'+table([w.day,w.rules,w.score,w.missing],a.days.map((row,i)=>[row.day,eur(row.nav),eur(b.days[i]?.nav),
        [...new Set(row.missing.concat(b.days[i]?.missing||[]))].join(', ')||'—']))+'<p>'+w.holiday+'</p></details>'+
      '<p>'+w.sources+' · <a href="'+root+'tree/4899370769e97b673930f8d65c5b9361a550804f/paper_trades">'+w.inputs+'</a> · <a href="'+root+'tree/main/history/runs">'+w.archive+'</a> · <a href="'+root+'blob/main/paper_trades/round2-settlement.json">'+w.proof+'</a></p></div>';
  }
  async function get(url) {
    const response=await fetch(url,{cache:'no-store',signal:AbortSignal.timeout(7000)});
    if(!response.ok) throw Error(response.status);
    const d=await response.json();
    if(d.schema!==1 || d.round!=='v18-2026-11-24' || !d.accounts?.rules || !d.accounts.score) throw Error('schema');
    return d;
  }
  return {draw,get,words};
})();
if (typeof module !== 'undefined' && require.main===module) {
  const snapshot=JSON.parse(require('node:fs').readFileSync(0,'utf8'));
  process.stdout.write(JSON.stringify(Object.fromEntries(Object.keys(RoundTwo.words).map(lang=>[lang,RoundTwo.draw(snapshot,lang)]))));
}
