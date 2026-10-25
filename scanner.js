'use strict';
(() => {
  const data = JSON.parse(document.getElementById('scanner-data').textContent);
  const market = data.market || {status: 'MISSING', candidates: [], funnel: []};
  const $ = id => document.getElementById(id);
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const num = (value, digits=2) => value === null || value === undefined ? '—' : Number(value).toLocaleString('de-DE', {minimumFractionDigits:digits, maximumFractionDigits:digits});
  const pct = (value, digits=1) => value === null || value === undefined ? '—' : num(value, digits) + ' %';
  const signed = (value, digits=1) => value === null || value === undefined ? '—' : (value > 0 ? '+' : '') + num(value, digits) + ' %';
  const money = value => {
    if (value === null || value === undefined) return '—';
    const a = Math.abs(value);
    return a >= 1e12 ? num(value/1e12, 2) + ' Bio. USD' : a >= 1e9 ? num(value/1e9, 1) + ' Mrd. USD' : a >= 1e6 ? num(value/1e6, 0) + ' Mio. USD' : num(value, 0) + ' USD';
  };
  const date = value => value ? new Date(value).toLocaleString('de-DE', {timeZone:'UTC',dateStyle:'medium',timeStyle:'short'}) + ' UTC' : 'nicht belegt';
  const day = value => value ? new Date(String(value).slice(0, 10) + 'T00:00:00Z').toLocaleDateString('de-DE', {timeZone:'UTC',dateStyle:'medium'}) : 'nicht belegt';
  const badge = band => `<span class="badge ${band?.includes('Buy') ? 'buy' : band === 'Sell' ? 'sell' : 'hold'}">${esc(band || 'Ohne Score')}</span>`;
  const status = row => InvestorAceAssessment.statusLabel(row,'de');
  const frozenAssessments = new Map(data.rows.map(r => [r.ticker,r.assessment]));
  const frozenIssues = new Map(data.rows.map(r => [r.ticker,r.issues]));
  function refreshAssessments() {
    for (const r of data.rows) {
      const current=InvestorAceAssessment.project(frozenAssessments.get(r.ticker),{objections:r.objections});
      const bands={'SELL':'Sell','HOLD NEG':'Hold negativ','HOLD POS':'Hold positiv','BUY':'Buy','STRONG BUY':'Strong Buy'};
      Object.assign(r,{assessment:current,model_score:current.model_score,model_band:bands[current.model_band]||null,
        rating:current.rating,review_status:current.review_status,quote_status:current.quote_status,
        score_components:current.components});
      r.issues=[...new Map([...(frozenIssues.get(r.ticker)||[]),...(current.issues||[])].map(x=>[x.code,x])).values()];
    }
    data.rated_count=data.rows.filter(r=>r.rating!==null).length;
    $('scanner-health').textContent = `${market.candidates.length} gespeicherte Marktkandidaten · ${market.candidates.filter(c=>!c.in_universe).length} außerhalb des Universums · ${data.universe_count} Aktien im Universum · ${data.rated_count} freigegebene Einstufungen im Universum. Stand der Seite: ${date(data.generated_at)}.`;
  }
  const regimeName = {GOLDILOCKS:'Goldilocks', REFLATION:'Reflation', INFLATION:'Inflation', STAGFLATION:'Stagflation', RECESSION:'Rezession'};
  const regimes = data.regimes || Object.keys(regimeName);
  const currentRegime = data.current_regime;
  const candidates = market.candidates || [];
  const universeControls = ['query','band','sector','currency','holdings','minimum','review','regime'];
  const marketControls = ['m-query','m-band','m-sector','m-quality','m-holdings','m-cap','m-minimum','m-regime'];
  let view = candidates.length ? 'market' : 'universe';
  let selected = [];
  let activeDetail = null;

  // ---------- static setup
  for (const id of ['regime', 'm-regime']) {
    for (const key of regimes) {
      const option = document.createElement('option');
      option.value = key;
      option.textContent = regimeName[key] + (key === currentRegime ? ' (aktuell)' : '');
      $(id).append(option);
    }
    $(id).value = currentRegime || regimes[0];
    $(id).dataset.default = $(id).value;
  }
  for (const [control, field] of [['sector','sector'],['currency','currency']]) {
    for (const value of [...new Set(data.rows.map(r => r[field]))].sort()) {
      const option = document.createElement('option'); option.value = value; option.textContent = value; $(control).append(option);
    }
  }
  for (const value of [...new Set(candidates.map(c => c.sector))].sort()) {
    const option = document.createElement('option'); option.value = value; option.textContent = value; $('m-sector').append(option);
  }
  $('captured').textContent = date(data.captured_at);
  $('universe').textContent = data.coverage;
  const priceDates = candidates.map(c => c.price_date).filter(Boolean).sort();
  $('market-date').textContent = ['OK','STALE'].includes(market.status)
    ? `Marktscan ${day(market.as_of)}` : 'Marktscan noch nicht verfügbar';
  $('market-coverage').textContent = (market.coverage || market.note || '') +
    (priceDates.length ? ` Schlusskurse bis ${day(priceDates[priceDates.length - 1])}.` : '');
  $('tab-market-count').textContent = candidates.length ? `(${candidates.filter(c => !c.in_universe).length} neu)` : '(—)';
  $('tab-universe-count').textContent = `(${data.universe_count})`;
  if (market.funnel?.length) {
    $('funnel-steps').innerHTML = market.funnel.map(s => `<li><strong>${num(s.count, 0)}</strong><span>${esc(s.stage)}</span></li>`).join('');
    $('funnel-note').textContent = market.method?.note || '';
    const aside = market.implausible || [];
    $('funnel-aside').innerHTML = aside.length
      ? `<b>Beiseitegelegt, weil die Zahlen nicht zu einem operativen Unternehmen passen:</b> ` + aside.map(x =>
          `<a href="${esc(x.source_url)}" target="_blank" rel="noopener noreferrer">${esc(x.ticker)}</a> (${esc((x.reasons || []).join('; '))})`).join(' · ')
      : '';
  } else {
    $('funnel').hidden = true;
  }
  $('audit-meta').innerHTML = `<p>Scanner erstellt: ${esc(date(data.generated_at))}<br>Modellaufnahme: ${esc(date(data.captured_at))}<br>Run: <code>${esc(data.run_id || 'nicht hinterlegt')}</code><br>Modell-Hash: <code>${esc(data.model_source_sha256)}</code></p>`
    + `<p>Marktscan: ${esc(market.generated_at ? date(market.generated_at) : 'nicht vorhanden')} · Status ${esc(market.status)}${market.note ? ' · ' + esc(market.note) : ''}<br>Quellen: SEC EDGAR (Tickerliste, XBRL-Frames, Companyfacts, Submissions), Yahoo-Tagesschlusskurse.</p>`
    + `<p>Kursprüfung Universum: ${esc(data.quote_policy.note)}<br>Marktscan: ${esc(market.quote_policy?.note || '')}</p>`
    + `<p>Letzter Kursabruf: ${esc(market.quote_refresh?.attempted_at ? date(market.quote_refresh.attempted_at) : 'im vollständigen Marktscan')} · Ausfälle: ${esc((market.quote_refresh?.failures || []).join(', ') || 'keine gemeldet')}. Finanzprüfung behält ihr ursprüngliches Datum.</p>`;

  // ---------- views
  function setStats(items) {
    items.forEach(([label, value], i) => { $(`stat-${i+1}-label`).textContent = label; $(`stat-${i+1}`).textContent = value; });
  }
  function setView(next) {
    view = next;
    $('tab-market').setAttribute('aria-selected', String(view === 'market'));
    $('tab-universe').setAttribute('aria-selected', String(view === 'universe'));
    $('market-filters').hidden = view !== 'market';
    $('filters').hidden = view !== 'universe';
    const regime = regimeName[currentRegime] || 'nicht gespeichert';
    if (view === 'market') {
      setStats([['Geprüfte US-Unternehmen', num(market.funnel?.[0]?.count ?? null, 0)],
                ['Nach Qualitätsfiltern', num(market.funnel?.[1]?.count ?? null, 0)],
                ['Neue Ideen mit Score ≥ 7', candidates.filter(c => !c.in_universe && c.score >= 7).length],
                ['Score wegen Datenlücken ausgesetzt', candidates.filter(c=>!c.rank_eligible).length]]);
      const cal = market.calibration;
      const pts = v => (v > 0 ? '+' : '') + num(v, 1);
      const calText = cal && cal.n >= 3
        ? ` <b>Abgleich:</b> Bei ${cal.n} Titeln, die auch in deinem Universum stehen, liegt der Vorscore im Mittel ${num(Math.abs(cal.mean_diff), 1)} Punkte ${cal.mean_diff >= 0 ? 'über' : 'unter'} deinem Modellscore (Spanne ${pts(cal.min_diff)} bis ${pts(cal.max_diff)}). Ein Vorscore-„Buy“ ist also kein Modell-Buy.`
        : '';
      $('notice').innerHTML = (market.note ? `<b>${esc(market.note)}</b> ` : '') + '<b>Vorscore mit Datenprüfung:</b> Fehlende Kennzahlen erhalten keine neutralen Punkte. Nur acht berechenbare Kategorien ergeben ein Band; offene Datenlücken findest du unter „Datenprüfung“. Die Gewichte bleiben unverändert. Vollständige Rechenbarkeit ersetzt keine Gegenprüfung.' + calText;
      $('list-eyebrow').textContent = 'VOM MARKT ZUR AUSWAHL';
      $('list-title').textContent = 'Neue Aktienideen';
      $('table-note').textContent = `Reihenfolge nach ungerundetem Screening-Score. Regime-Fit bleibt separat und ändert die Reihenfolge nicht. Aktuelles Regime laut Engine: ${regime}. Sektor aus dem SEC-SIC-Code abgeleitet.`;
      $('scanner-head').innerHTML = '<tr><th scope="col">Unternehmen</th><th scope="col">Screening-Score / Datenprüfung</th><th scope="col">Kurs &amp; Marktwert</th><th scope="col">Berichtete Kennzahlen</th><th scope="col">Regime-Fit</th><th scope="col">Analyse</th></tr>';
    } else {
      setStats([['Aktien im Universum', data.universe_count],
                ['Buy / Strong Buy im Modell', data.rows.filter(r => r.model_score !== null && r.model_score >= 7).length],
                ['Mit offenen Einwänden', data.rows.filter(r => InvestorAceAssessment.materialObjections(r.objections).length).length],
                ['Quellenprüfung hinterlegt', data.rows.filter(r => r.source_status === 'SOURCE_CHECKED').length]]);
      $('notice').innerHTML = '<b>Forschungsliste:</b> Ein Modellband ist eine vorläufige Einordnung. Offene wesentliche Einwände verhindern eine belastbare aktuelle Einstufung.';
      $('list-eyebrow').textContent = 'VOM UNIVERSUM ZUR AUSWAHL';
      $('list-title').textContent = 'Mein Universum';
      $('table-note').textContent = `Reihenfolge nach ungerundetem Modellscore. Regime-Fit bleibt separat. Aktuelles Regime laut Engine: ${regime}. „Nicht im Bestand“ blendet nur die im gespeicherten Datensatz gehaltenen Positionen aus; neue Aktien findet der Tab „Gesamtmarkt USA“.`;
      $('scanner-head').innerHTML = '<tr><th scope="col">Unternehmen</th><th scope="col">Modellscore / Band</th><th scope="col">Kurs im Datensatz</th><th scope="col">Prüfung / Einwände</th><th scope="col">Regime-Fit</th><th scope="col">Analyse</th></tr>';
    }
    render();
  }

  // ---------- market list
  function marketSelection() {
    const query = $('m-query').value.trim().toLocaleLowerCase('de-DE');
    const band = $('m-band').value, sector = $('m-sector').value, holdings = $('m-holdings').value;
    const cap = Number($('m-cap').value), minimum = Number($('m-minimum').value);
    return candidates.filter(c => {
      if (query && !`${c.ticker} ${c.name} ${c.sector} ${c.sic_description}`.toLocaleLowerCase('de-DE').includes(query)) return false;
      if (band === 'positive' && !(c.score !== null && c.score >= 7)) return false;
      if (!['all','positive'].includes(band) && c.band !== band) return false;
      if (sector !== 'all' && c.sector !== sector) return false;
      if (holdings === 'new' && c.in_universe) return false;
      if (holdings === 'held' && !c.in_universe) return false;
      const quality = $('m-quality').value;
      if (quality === 'complete' && !c.rank_eligible) return false;
      if (quality === 'blocked' && c.rank_eligible) return false;
      if (quality === 'commodity' && !c.flags.includes('COMMODITY_MIDCYCLE_REQUIRED')) return false;
      if (cap > 0 && !(c.metrics.market_cap >= cap)) return false;
      if (minimum > 0 && (c.score === null || c.score < minimum)) return false;
      return true;
    });
  }
  function marketRow(c) {
    const regime = $('m-regime').value;
    const held = c.in_universe ? ` · im Universum${c.universe_score !== null && c.universe_score !== undefined ? ' (Modell ' + num(c.universe_score) + ')' : ''}` : '';
    return `<tr>
      <td><span class="ticker">${esc(c.ticker)}</span><span class="subline">${esc(c.name)}</span><span class="subline">${esc(c.sector)} · ${esc(c.exchange)}${esc(held)}</span></td>
      <td><span class="score">${num(c.score)}</span> / 10<br>${badge(c.band)}<span class="subline">${c.rank_eligible ? 'Vorscore · Gegenprüfung offen' : 'Score ausgesetzt · Daten prüfen'}</span><span class="subline">${num(c.coverage_weight*100,0)} % Scoregewicht berechenbar</span></td>
      <td>${num(c.price)} USD<span class="subline">${c.quote_status === 'DATED' ? 'Schluss ' + esc(day(c.price_date)) : esc({STALE:'Kurs veraltet',FUTURE:'Zukünftiges Kursdatum',TIME_UNKNOWN:'Kursdatum fehlt',MISSING:'Kurs fehlt'}[c.quote_status] || c.quote_status)}</span><span class="subline">Marktwert ${esc(money(c.metrics.market_cap))}</span></td>
      <td><span class="kv">Umsatz ${esc(signed(c.metrics.growth_pct))}</span><span class="kv">Op.-Marge ${esc(pct(c.metrics.operating_margin_pct))}</span><span class="kv">FCF-Rendite ${esc(pct(c.metrics.fcf_yield_pct))}</span><span class="kv">8%-Szenario/Kurs ${esc(pct(c.metrics.cover_pct, 0))}</span><span class="subline">${esc(c.basis)} bis ${esc(day(c.period_end))}</span></td>
      <td><span class="fit">${num(c.regime_fit?.[regime], 1)}</span><span class="subline">/ 100 · ${esc(regimeName[regime])}<br>ohne Scoregewicht</span></td>
      <td><button class="open-detail" data-ticker="${esc(c.ticker)}" aria-label="Analyse zu ${esc(c.ticker)} öffnen">Prüfen ↗</button></td></tr>`;
  }
  const inputText = x => ({
    g: () => 'Umsatzwachstum ' + signed(x.input),
    p: () => 'operative Marge ' + pct(x.input),
    c: () => 'FCF-Marge ' + pct(x.input),
    b: () => x.input === null ? 'Nettoverschuldung/EBITDA nicht berechenbar' : 'Nettoverschuldung/EBITDA ' + num(x.input, 1) + '×',
    v: () => 'FCF-Rendite ' + pct(x.input),
    pr: () => '8%-FCF-Szenario/Kurs ' + pct(x.input, 0),
    r: () => (x.input_basis === 'SATURATED_LOWER_BOUND' ? 'Bekannte Untergrenze (Kurve bereits bei 9 Punkten): ' : 'Dividenden- plus Aktienrückgangs-Proxy ') + pct(x.input),
    d: () => x.input === null ? 'Aktienzahl ohne Vorjahreswert' : 'Aktienzahl ' + signed(x.input) + ' gg. Vorjahr',
  }[x.key] || (() => ''))();
  function marketDetail(c) {
    const m = c.metrics;
    const strong = c.components.filter(x => x.value !== null && x.value >= 8).sort((a, b) => b.value - a.value).slice(0, 3);
    const weak = c.components.filter(x => x.value !== null && x.value < 5.5).sort((a, b) => a.value - b.value).slice(0, 3);
    const line = x => `<li><b>${esc(x.label)} ${num(x.value, 1)}</b> · ${esc(inputText(x))}</li>`;
    const basis = c.basis === 'TTM' ? `Letzte zwölf Monate bis ${day(c.period_end)} (letztes Geschäftsjahr + laufendes YTD − Vorjahres-YTD)` : `Geschäftsjahr bis ${day(c.period_end)}`;
    const growthBasis = {TTM:'TTM gegen Vorjahres-TTM', YTD:'laufendes YTD gegen Vorjahres-YTD', FY:'Geschäftsjahr gegen Vorjahr'}[c.growth_basis] || 'kein Vorjahreswert';
    const shares = {COVER_PAGE:'Aktien laut Deckblatt der letzten Einreichung', DILUTED_AVG:'verwässerter Quartalsdurchschnitt', DILUTED_AVG_FY:'verwässerter Jahresdurchschnitt (SEC-Frames)'}[c.shares_basis] || 'nicht belegt';
    const next = c.in_universe
      ? `<p>Schon im Universum${c.universe_score !== null && c.universe_score !== undefined ? ' mit Modellscore ' + num(c.universe_score) : ''}. Der Vergleich Vorscore gegen Modellscore zeigt, wie weit die mechanische Rechnung von der gepflegten abweicht.</p><button type="button" id="open-in-universe" data-ticker="${esc(c.universe_key || c.ticker)}">Im Universum öffnen ↗</button>`
      : `<p>Für eine echte Bewertung muss die Aktie ins Modell. Das Formular startet den bestehenden add-ticker-Ablauf: Er legt einen Entwurf auf einem eigenen Branch an; WACC, Normalisierung, deliver und clock bleiben Handarbeit.</p><a class="cta" href="${esc(c.add_url)}" target="_blank" rel="noopener noreferrer">Zu InvestorAce hinzufügen ↗</a>`;
    const rows = [
      ['Umsatz', money(m.revenue)], ['Umsatz Vorjahreszeitraum', money(m.revenue_prior)], ['Umsatzwachstum', signed(m.growth_pct) + ' · ' + growthBasis],
      ['Operatives Ergebnis', money(m.operating_income)], ['Operative Marge', pct(m.operating_margin_pct)],
      ['Operativer Cashflow', money(m.operating_cash_flow)], [c.flags.includes('CAPEX_NOT_TAGGED') ? 'Capex-Proxy: Abschreibungen, keine belegten Investitionen' : 'Investitionen (Capex)', money(m.capex)], ['FCF-Rechnung (Cashflow minus Capex)', money(m.fcf)], ['FCF-Marge', pct(m.fcf_margin_pct)],
      ['Abschreibungen', money(m.depreciation)], ['EBITDA (op. Ergebnis + Abschreibungen)', money(m.ebitda)],
      ['Finanzschulden', money(m.debt)], ['Liquidität', money(m.cash)], ['Nettoverschuldung (ohne Leasing)', money(m.net_debt)],
      ['Nettoverschuldung / EBITDA', m.nd_ebitda === null ? '—' : num(m.nd_ebitda, 2) + '×'], ['Bilanzstichtag', day(c.balance_date)],
      ['Aktien', num(m.shares === null ? null : m.shares / 1e6, 1) + ' Mio. · ' + shares], ['Aktienzahl gg. Vorjahr', signed(m.share_change_pct)],
      ['Marktwert', money(m.market_cap)], ['FCF-Rendite', pct(m.fcf_yield_pct)], ['Dividendenrendite', pct(m.dividend_yield_pct)], ['Aktienrückgang (Proxy, keine Cash-Rückkaufrendite)', pct(m.buyback_yield_pct)],
      ['FCF-Rechenszenario je Aktie (÷ 8 %, keine bestätigte NGV)', num(m.ngv_per_share) + ' USD'], ['Szenario / Kurs', pct(m.cover_pct, 0)],
    ];
    return `<div class="detail-head"><div><p class="eyebrow">MARKTSCAN · VORSCORE</p><h2 id="detail-title">${esc(c.name)} <span class="small">${esc(c.ticker)} · ${esc(c.exchange)}</span></h2>${badge(c.band)} <span class="small">Screening-Score ${num(c.score)} · mechanisch, ungeprüft</span></div><button id="close-detail" aria-label="Analyse schließen">Schließen ×</button></div>
      <div class="detail-grid"><div><h3>Warum auf der Liste?</h3>${strong.length ? '<ul>' + strong.map(line).join('') + '</ul>' : '<p>Keine Kategorie erreicht 8 Punkte; der Rang kommt aus einem breiten Mittelfeld.</p>'}
      <h3>Größte Schwächen</h3>${weak.length ? '<ul>' + weak.map(line).join('') + '</ul>' : '<p>Keine Kategorie unter 5,5 Punkten.</p>'}
      <h3>Datenbasis</h3><p>${esc(basis)}. Bilanz zum ${esc(day(c.balance_date))}. Schlusskurs vom ${esc(day(c.price_date))}. Sektor aus SIC ${esc(c.sic ?? '—')} (${esc(c.sic_description || 'ohne Beschreibung')}).</p>
      ${c.flags.length ? '<h3>Hinweise zur Datenqualität</h3><ul>' + c.flags.map(f => `<li><span class="issue-code">${esc(f)}</span><br>${esc(c.flag_text?.[f] || f)}</li>`).join('') + '</ul>' : ''}</div>
      <div><h3>Nächster Schritt</h3>${next}
      <h3>Kennzahlen</h3><table class="score-table"><tbody>${rows.map(([k, v]) => `<tr><td>${esc(k)}</td><td>${esc(v)}</td></tr>`).join('')}</tbody></table></div></div>
      <details open><summary>Scorebeiträge der acht Kategorien</summary><p>${c.rank_eligible ? 'Summe aller acht Beiträge: ' + num(c.score,3) : 'Kein Gesamtscore: fehlende Beiträge bleiben leer; Gewichte werden nicht umverteilt.'} · ${num(c.coverage_weight*100,0)} % berechenbar.</p><div class="table-scroll"><table class="score-table"><thead><tr><th>Kategorie</th><th>Kennzahl</th><th>Wert</th><th>Gewicht</th><th>Beitrag</th></tr></thead><tbody>${c.components.map(x => `<tr><td>${esc(x.label)}${x.reason ? '<span class="subline">' + esc(x.reason) + '</span>' : ''}</td><td>${esc(inputText(x))}</td><td>${num(x.value,1)}</td><td>${num(x.weight*100,0)} %</td><td>${num(x.contribution,3)}</td></tr>`).join('')}</tbody></table></div></details>
      <details><summary>Archivierter Vorscore vor der Gegenprüfung</summary><p>Historischer Rechenstand ${num(c.archived_screen?.score)} / 10 · ${esc(c.archived_screen?.band || 'ohne Band')}. Wegen möglicher Datenfehler keine aktuelle Einstufung.</p></details>
      <h3>Quellen & Herkunft</h3><p class="small">${esc(c.source_limit)}</p><ul class="sources">${c.sources.map(s => `<li><a href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">${esc(s.title)}</a></li>`).join('')}</ul>`;
  }

  // ---------- universe list (unchanged logic)
  function universeSelection() {
    const query = $('query').value.trim().toLocaleLowerCase('de-DE');
    return data.rows.filter(r => {
      if (query && !`${r.ticker} ${r.listing} ${r.issuer}`.toLocaleLowerCase('de-DE').includes(query)) return false;
      const band = $('band').value;
      if (band === 'positive' && !(r.model_score !== null && r.model_score >= 7)) return false;
      if (!['all','positive'].includes(band) && r.model_band !== band) return false;
      if ($('sector').value !== 'all' && r.sector !== $('sector').value) return false;
      if ($('currency').value !== 'all' && r.currency !== $('currency').value) return false;
      if ($('holdings').value === 'new' && r.held_in_snapshot) return false;
      if ($('holdings').value === 'held' && !r.held_in_snapshot) return false;
      if (Number($('minimum').value) > 0 && (r.model_score === null || r.model_score < Number($('minimum').value))) return false;
      if ($('review').value === 'issues' && !r.issues.length) return false;
      if ($('review').value === 'notes' && !r.thesis) return false;
      return true;
    });
  }
  function universeRow(r) {
    const fresh = candidates.find(c => c.universe_key === r.ticker);
    return `<tr>
      <td><span class="ticker">${esc(r.ticker)}</span><span class="subline">${esc(r.issuer)}</span><span class="subline">${esc(r.listing)} · ${esc(r.sector)}${r.held_in_snapshot ? ' · Bestand im Datensatz' : ''}</span></td>
      <td><span class="score">${num(r.model_score)}</span> / 10<br>${badge(r.model_band)}<span class="subline">${r.rating ? 'Prüfstatus separat beachten' : 'Modell · ungeprüft'}</span>${r.raw_score !== null && r.raw_score !== undefined ? '<span class="subline">Archivierter Rechenwert: ' + num(r.raw_score) + '</span>' : ''}${fresh ? '<span class="subline">Neuer Marktscreen: ' + (fresh.score === null ? 'Datenprüfung offen' : num(fresh.score) + ' · andere Methode') + '</span>' : ''}</td>
      <td>${num(r.price)} ${esc(r.currency)}<span class="subline">${r.quote_status === 'DATED' ? esc(date(r.quote_observed_at)) : 'Kursdatum: ' + esc({TIME_UNKNOWN:'unbekannt',STALE:'veraltet',MISSING:'fehlend',FUTURE:'ungültig'}[r.quote_status])}</span></td>
      <td><span class="pending">${status(r)}</span><span class="subline">${r.issues.length} offene Prüfpunkte</span><span class="subline">Quelle: ${r.source_status === 'SOURCE_CHECKED' ? 'geprüft, Bewertung offen' : 'Prüfung unvollständig'}</span></td>
      <td><span class="fit">${num(r.regime_fit[$('regime').value],1)}</span><span class="subline">/ 100 · ${esc(regimeName[$('regime').value])}<br>ohne Scoregewicht</span></td>
      <td><button class="open-detail" data-ticker="${esc(r.ticker)}" aria-label="Analyse zu ${esc(r.ticker)} öffnen">Prüfen ↗</button></td></tr>`;
  }
  function dynamicAnalysis(analysis) {
    if (!analysis) return '';
    const inputs = analysis.inputs || {}, parameters = analysis.parameters || {}, valuation = analysis.valuation || {};
    const currency = analysis.currency || '—';
    const financialCurrency = analysis.financial_currency || '—';
    const amount = value => value === null || value === undefined ? '—'
      : money(value).replace(/ USD$/, ' ' + financialCurrency);
    const perShare = value => value === null || value === undefined ? '—' : num(value) + ' ' + currency;
    const at = value => value && Number.isFinite(Date.parse(value)) ? date(value) : '—';
    const rows = [
      ['Kurs im Eingabestand', perShare(inputs.quote_price)], ['Umsatz', amount(inputs.revenue)],
      ['Operatives Ergebnis', amount(inputs.operating_income)], ['Jahresüberschuss', amount(inputs.net_income)],
      ['Operativer Cashflow', amount(inputs.operating_cash_flow)], ['Investitionen (Capex)', amount(inputs.capex)],
      ['Gemeldeter freier Cashflow', amount(inputs.fcf)], ['Cashflow im Bewertungsszenario', amount(inputs.valuation_fcf)],
      ['Finanzschulden', amount(inputs.debt)], ['Liquidität', amount(inputs.cash)],
      ['Aktienzahl', num(inputs.shares, 0)], ['Eigenkapitalkosten', pct(parameters.discount_rate_pct)],
      ['Risikofreier Zins (USD)', pct(parameters.risk_free_pct)], ['Beta', num(parameters.beta)],
      ['Marktrisikoprämie', pct(parameters.market_premium_pct)],
      ['Wachstumsannahme', pct(parameters.growth_rate_pct)], ['Terminalwachstum', pct(parameters.terminal_growth_pct)],
      ['Prognosejahre', num(parameters.horizon_years, 0)], ['NGV je Aktie', perShare(valuation.ngv_per_share)],
      ['DCF-Szenario je Aktie', perShare(valuation.dcf_per_share)],
      ['Vom Kurs impliziertes Wachstum (Reverse DCF)', pct(valuation.reverse_dcf_growth_pct)],
    ];
    const scenarios = Array.isArray(valuation.scenarios) ? valuation.scenarios : [];
    const warnings = Array.isArray(analysis.warnings) ? analysis.warnings : [];
    const warningLabels = {
      'Reported leveraged FCF proxy; sustainable cash flow has not been normalized.': 'Gemeldeter Cashflow nach Fremdkapitalkosten als Näherungswert; nachhaltiger Cashflow ist noch nicht normalisiert.',
      'OCF/capex bridge unavailable; cash flow uses Yahoo reported Free Cash Flow.': 'Die Überleitung aus operativem Cashflow und Investitionen fehlt; verwendet wird der von Yahoo gemeldete Free Cashflow.',
      'Five-year growth and terminal growth are scenario assumptions, not forecasts.': 'Wachstum über fünf Jahre und Terminalwachstum sind Szenarioannahmen, keine Prognosen.',
      'Quote and financial currencies are missing or incompatible; valuation suspended.': 'Kurs- und Berichtswährung fehlen oder sind nicht vereinbar; Bewertung ausgesetzt.',
      'USD risk-free curve is a shared model assumption for this non-USD cash flow.': 'Für diesen Cashflow in einer anderen Währung verwendet das Modell den USD-Zins als gemeinsame Annahme.',
      'No sufficiently recent dated quote; price-dependent outputs suspended.': 'Kein ausreichend aktueller datierter Kurs; kursabhängige Ergebnisse ausgesetzt.',
      'Valid cost-of-equity inputs unavailable; valuation suspended.': 'Keine gültigen Eingaben für Eigenkapitalkosten; Bewertung ausgesetzt.',
      'Commodity value uses a multi-year reported cash-flow mean; acquisitions and normalization still require review.': 'Rohstoffbewertung verwendet den Mittelwert mehrerer gemeldeter Jahrescashflows; Übernahmen und Normalisierung bleiben zu prüfen.',
      'No comparable positive annual FCF growth; base growth assumes zero.': 'Kein vergleichbares jährliches Cashflow-Wachstum mit positiver Ausgangsbasis; Basisszenario nimmt null Wachstum an.',
      'Financial refresh failed; dated last-good inputs retained and repriced.': 'Finanzdatenabruf fehlgeschlagen; der letzte gültige datierte Eingabestand bleibt erhalten und wird neu bewertet.',
      'Commodity economics still require mid-cycle normalization; reported cash scenario only.': 'Rohstoffgeschäft benötigt weiterhin eine Zyklusnormalisierung; gezeigt wird ein Szenario auf Basis gemeldeter Cashflows.',
    };
    const scenarioLabels = {bear:'Bär', base:'Basis', bull:'Bulle'};
    const periods = analysis.metric_periods || {};
    const periodPair = key => (periods[key] || []).map(value => esc(value)).join(' / ') || '—';
    const sources = Array.isArray(analysis.source_urls) ? analysis.source_urls.filter(url =>
      typeof url === 'string' && /^https:\/\/finance\.yahoo\.com\/quote\//.test(url)) : [];
    return `<section id="dynamic-analysis" aria-labelledby="dynamic-analysis-title"><h3 id="dynamic-analysis-title">Aktuelles yfinance-Modellszenario · Prüfung erforderlich</h3>
      <p class="small">Beim Erstellen der Seite aus yfinance-Eingaben berechnet. Berechnung: ${esc(at(analysis.as_of))} · Eingaben abgerufen: ${esc(at(analysis.fetched_at))} · Kurs vom ${esc(at(analysis.quote_observed_at))}. Finanzperiode: ${esc(analysis.financial_period ?? '—')} · Basis: ${esc(analysis.basis ?? '—')} · Kurswährung: ${esc(currency)} · Berichtswährung: ${esc(financialCurrency)} · Status: ${esc(analysis.status ?? '—')} · Datenabruf: ${esc(analysis.data_status ?? '—')}.</p>
      <p>Die Szenarien hängen von den angegebenen Annahmen ab und benötigen eine Gegenprüfung.</p>
      <p class="small">Jahresvergleich Umsatz: ${periodPair('revenue_growth')} · Cashflow: ${periodPair('fcf_growth')} · Aktienzahl: ${periodPair('share_change')}.</p>
      <div class="table-scroll"><table class="score-table"><tbody>${rows.map(([key,value]) => `<tr><td>${esc(key)}</td><td>${esc(value)}</td></tr>`).join('')}</tbody></table></div>
      ${scenarios.length ? '<h3>Bewertungsszenarien</h3><div class="table-scroll"><table class="score-table"><thead><tr><th>Szenario</th><th>Wachstum</th><th>Wert je Aktie</th></tr></thead><tbody>' + scenarios.map(s => `<tr><td>${esc(scenarioLabels[s.name] ?? s.name ?? '—')}</td><td>${esc(pct(s.growth_pct))}</td><td>${esc(perShare(s.value_per_share))}</td></tr>`).join('') + '</tbody></table></div>' : ''}
      ${warnings.length ? '<h3>Offene Hinweise zum Modellszenario</h3><ul>' + warnings.map(w => `<li>${esc(warningLabels[w] ?? w)}</li>`).join('') + '</ul>' : ''}
      ${sources.length ? '<h3>Finanzdatenquellen</h3><ul class="sources">' + sources.map(url => `<li><a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(url)}</a></li>`).join('') + '</ul>' : ''}</section>`;
  }
  function universeDetail(r) {
    const objections = r.objections.filter(x => !['verified','rejected'].includes(x.status));
    return `<div class="detail-head"><div><p class="eyebrow">ANALYSE & GEGENPRÜFUNG</p><h2 id="detail-title">${esc(r.issuer)} <span class="small">${esc(r.listing)}</span></h2>${badge(r.model_band)} <span class="small">Modellscore ${num(r.model_score)} · ${status(r)}</span></div><button id="close-detail" aria-label="Analyse schließen">Schließen ×</button></div>
      ${dynamicAnalysis(r.dynamic_analysis)}
      <div class="detail-grid"><div><h3>Warum auf die Prüfliste?</h3><p>${esc(r.thesis || 'Der gespeicherte Modellscore setzt diesen Titel auf die Prüfliste. Eine aktuelle, belegte Investmentthese wurde für den Scanner noch nicht erstellt.')}</p><h3>Stärkstes Gegenargument</h3><p>${esc(r.counterargument || 'Noch keine dokumentierte Gegenprüfung. Ein hoher Modellscore belegt weder einen Burggraben noch einen attraktiven Kaufpreis.')}</p><h3>Nächster Nachweis</h3><p>${esc(r.next_check)}</p>${r.notes_as_of ? `<p class="small">Research-Notiz vom ${esc(r.notes_as_of)}</p>` : ''}</div>
      <div><h3>Ungelöste Analysteneinwände</h3>${objections.length ? '<ul>' + objections.map(x => `<li><b>${esc(x.id)} · ${esc(x.severity)} · ${esc(x.status)}</b><br>${esc(x.message)}${x.response ? '<br><b>Antwort:</b> ' + esc(x.response) : ''}${x.resolution_required ? '<br><b>Zur Klärung:</b> ' + esc(x.resolution_required) : ''}</li>`).join('') + '</ul>' : '<p>Keine separaten Analysteneinwände hinterlegt. Das bestätigt keine abgeschlossene Gegenprüfung.</p>'}<h3>Offene Daten- und Bewertungsprüfung</h3><ul>${r.issues.map(x => `<li><span class="issue-code">${esc(x.code)} · ${esc(x.status)}</span><br>${esc(x.message)}</li>`).join('')}</ul></div></div>
      <h3>Quellen & Herkunft</h3><p>${esc(r.source_reason || 'Keine vollständige Quellenprüfung hinterlegt.')}</p><ul class="sources">${r.sources.map(s => `<li><a href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">${esc(s.title)}</a>${s.published_at ? ' · ' + esc(s.published_at) : ''}</li>`).join('') || '<li>Quellen müssen noch ergänzt werden.</li>'}</ul>
      <details><summary>Archivierte Bewertungsannahmen ansehen — ungeprüft</summary><p class="small">Herkunftsnachweis zum gespeicherten Modell. Wegen offener Prüfung keine aktuelle bestätigte Bewertung; NGV ist ein No-Growth-Wert und kein Kursziel.</p><table><tbody><tr><td>NGV im Modell</td><td>${num(r.archived_valuation.ngv)} ${esc(r.currency)}</td></tr><tr><td>NGV / Kurs im Modell</td><td>${r.archived_valuation.cover === null ? '—' : num(r.archived_valuation.cover*100,1) + ' %'}</td></tr><tr><td>EPV im Modell</td><td>${num(r.archived_valuation.epv)} ${esc(r.currency)}</td></tr><tr><td>Cashflow-Cushion</td><td>${r.archived_valuation.cushion === null ? 'nicht vergleichbar / nicht verfügbar' : num(r.archived_valuation.cushion,1) + ' pp'}</td></tr><tr><td>Kurszeitpunkt / Abrufzeit</td><td>${esc(r.quote_observed_at || 'unbekannt')} / ${esc(r.retrieved_at || 'unbekannt')}</td></tr></tbody></table><p>${esc(r.model_note)}</p></details>
      <details><summary>Scorebeiträge aus dem Modell</summary>${r.score_components.length ? '<table class="score-table"><thead><tr><th>Kategorie</th><th>Wert</th><th>Gewicht</th><th>Beitrag</th></tr></thead><tbody>' + r.score_components.map(c => `<tr><td>${esc(c.label)}</td><td>${num(c.value,1)}</td><td>${num(c.effective_weight*100,1)} %</td><td>${num(c.contribution,3)}</td></tr>`).join('') + '</tbody></table>' : '<p>Nur ein fester Gesamtscore verfügbar. Keine Kategorien erfunden.</p>'}</details>`;
  }

  // ---------- shared rendering
  function render() {
    refreshAssessments();
    selected = view === 'market' ? marketSelection() : universeSelection();
    const total = view === 'market' ? candidates.length : data.universe_count;
    $('result-count').textContent = `${selected.length} von ${total} ${view === 'market' ? 'Kandidaten' : 'Aktien'}`;
    $('empty').hidden = selected.length !== 0;
    $('empty').textContent = view === 'market' && !candidates.length
      ? (market.note || 'Noch kein Marktscan gespeichert.') + ' Der wöchentliche Lauf (market-scan) füllt diese Liste.'
      : view === 'universe' && !selected.length && data.universe_count
      ? `Der Scanner enthält ${data.universe_count} Aktien; ${data.rated_count} Einstufungen sind freigegeben. Diese Filter zeigen keine Treffer. „Alle Bänder“ zeigt auch Aktien mit offener Prüfung.`
      : 'Keine Treffer für diese Filter. Öffne „Alle Bänder“ oder setze die Filter zurück.';
    $('scanner-rows').innerHTML = selected.map(view === 'market' ? marketRow : universeRow).join('');
  }
  function updateLocation(scope, ticker) {
    const url = new URL(location.href);
    url.searchParams.set('view', scope);
    if (ticker) url.searchParams.set('ticker', ticker);
    else url.searchParams.delete('ticker');
    // An embedded preview may restrict history access; local files and the
    // standalone page still support the same deep-link behavior.
    try { history.replaceState(null, '', url); } catch (_) { /* keep selection usable */ }
  }
  function closeDetail() {
    activeDetail = null;
    $('detail').hidden = true;
    $('detail').removeAttribute('data-scope');
    $('detail').removeAttribute('data-ticker');
    $('selected-review-packet').hidden = true;
    $('selected-review-packet').onclick = null;
  }
  function clearFilters(scope) {
    const controls = scope === 'market' ? marketControls : universeControls;
    for (const id of controls) {
      if (id === 'regime' || id === 'm-regime') continue;
      const control = $(id);
      control.value = control.tagName === 'SELECT'
        ? (id === 'm-cap' ? '0' : 'all') : control.type === 'number' ? '0' : '';
    }
  }
  function openLinkedDetail(scope, ticker) {
    clearFilters(scope);
    $(scope === 'market' ? 'm-query' : 'query').value = ticker;
    setView(scope);
    detail(ticker, false, scope);
  }
  function detail(ticker, refresh=false, scope=view) {
    const html = scope === 'market'
      ? (c => c && marketDetail(c))(candidates.find(c => c.ticker === ticker))
      : (r => r && universeDetail(r))(data.rows.find(r => r.ticker === ticker));
    if (!html) return;
    activeDetail = {scope, ticker};
    $('selection-status').hidden = true;
    const storedPacket = data.review_packets?.[scope]?.[ticker];
    const packetText = typeof storedPacket === 'string' ? storedPacket : null;
    const packetLabel = `Prüfpaket ${ticker} · ${scope === 'market' ? 'Marktscan' : 'Universum'} ↓`;
    $('detail').innerHTML = html;
    $('detail').dataset.scope = scope;
    $('detail').dataset.ticker = ticker;
    if (packetText) $('detail').querySelector('.detail-head').insertAdjacentHTML('afterend',
      `<section aria-label="Gemeinsame Gegenprüfung"><button type="button" id="download-review-packet" class="cta">${esc(packetLabel)}</button><p class="small">Daten, Bewertungsannahmen, Quellen und offene Einwände mit drei getrennten Prüfaufträgen als JSON. Das Paket kannst du hier im Chat zur Gegenprüfung hochladen. Der ursprüngliche Datenstand bleibt erhalten; die Gegenprüfung steht noch aus.</p></section>`);
    $('detail').hidden = false; if(!refresh) $('detail').focus();
    const downloadPacket = () => download(packetText,
      `InvestorAce_Pruefpaket_${scope}_${ticker.replace(/[^a-zA-Z0-9._-]/g,'_')}.json`, 'application/json');
    const topButton = $('selected-review-packet');
    topButton.hidden = !packetText;
    topButton.textContent = packetLabel;
    topButton.onclick = packetText ? downloadPacket : null;
    if ($('download-review-packet')) $('download-review-packet').onclick = downloadPacket;
    $('close-detail').onclick = () => {
      closeDetail(); updateLocation(view);
      $('list-title').scrollIntoView({block:'start'});
    };
    const jump = $('open-in-universe');
    if (jump) jump.onclick = () => openLinkedDetail('universe', jump.dataset.ticker);
    if(!refresh) {
      updateLocation(scope, ticker);
      $('detail').scrollIntoView({behavior:'smooth',block:'start'});
    }
  }
  function openLocation() {
    const params = new URLSearchParams(location.search);
    const requestedView = params.get('view');
    const rawTicker = params.get('ticker');
    const normalized = (rawTicker || '').trim().toUpperCase();
    const validTicker = params.getAll('ticker').length === 1 && /^[A-Z0-9][A-Z0-9._-]{0,31}$/.test(normalized);
    const findTicker = scope => validTicker && (scope === 'market' ? candidates : data.rows)
      .find(row => row.ticker.toUpperCase() === normalized)?.ticker;
    const scope = ['market','universe'].includes(requestedView) ? requestedView
      : findTicker('universe') ? 'universe' : findTicker('market') ? 'market' : view;
    closeDetail();
    $('selection-status').hidden = true;
    if (rawTicker === null) { setView(scope); return; }
    const ticker = findTicker(scope);
    if (ticker) { openLinkedDetail(scope, ticker); return; }
    clearFilters(scope);
    setView(scope);
    $('selection-status').textContent = `Der Ticker im Link ist ungültig oder in dieser Liste nicht vorhanden. Alle ${scope === 'market' ? 'Marktkandidaten' : 'Aktien im Universum'} werden angezeigt. Wähle eine Aktie, um ihr Prüfpaket zu laden.`;
    $('selection-status').hidden = false;
  }
  $('scanner-rows').addEventListener('click', e => { const button = e.target.closest('button[data-ticker]'); if (button) detail(button.dataset.ticker); });
  for (const id of universeControls.concat(marketControls)) $(id).addEventListener(['query','minimum','m-query','m-minimum'].includes(id) ? 'input' : 'change', () => {
    if (id === 'm-quality' && ['blocked','commodity'].includes($(id).value)) {
      $('m-band').value = 'all'; $('m-minimum').value = 0;
    }
    render();
  });
  for (const scope of ['market','universe']) $(`tab-${scope}`).onclick = () => {
    setView(scope);
    if (!activeDetail) updateLocation(scope);
  };
  for (const [button, form, select] of [['reset-filters','filters','regime'], ['m-reset','market-filters','m-regime']]) {
    $(button).onclick = () => { $(form).reset(); $(select).value = $(select).dataset.default; render(); };
  }
  const csv = value => '"' + String(value ?? '').replace(/^[=+@\-\t\r]/, "'" + '$&').replace(/"/g,'""') + '"';
  const download = (text, name, type) => {
    const url = URL.createObjectURL(new Blob([text], {type})); const a = document.createElement('a');
    a.href = url; a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  $('export').onclick = () => {
    render();
    let header, rows, name;
    if (view === 'market') {
      header = ['Ticker','Unternehmen','Sektor','Börse','Screening-Score','Band (ungeprüft)','Kurs USD','Kursdatum','Marktwert USD','Umsatzwachstum %','Op.-Marge %','FCF-Marge %','FCF-Rendite %','8%-Szenario/Kurs %','Nettoverschuldung/EBITDA','Im Universum','Basis','Periodenende','Scan','Prüfstatus','Abdeckung Gewicht','Kursstatus','Offene Prüfpunkte'];
      rows = selected.map(c => [c.ticker,c.name,c.sector,c.exchange,c.score,c.band,c.price,c.price_date,c.metrics.market_cap,c.metrics.growth_pct,c.metrics.operating_margin_pct,c.metrics.fcf_margin_pct,c.metrics.fcf_yield_pct,c.metrics.cover_pct,c.metrics.nd_ebitda,c.in_universe ? 'ja' : 'nein',c.basis,c.period_end,market.as_of,c.review_status,c.coverage_weight,c.quote_status,c.flags.join(' | ')]);
      name = 'InvestorAce_Marktscan.csv';
    } else {
      header = ['Ticker','Listing','Unternehmen','Modellscore','Modellband ungeprüft','Aktuelle Einstufung','Währung','Sektor','Prüfstatus','Offene Prüfpunkte','Datenaufnahme'];
      rows = selected.map(r => [r.ticker,r.listing,r.issuer,r.model_score,r.model_band,r.rating||'ungeprüft',r.currency,r.sector,r.review_status,r.issues.map(x => x.message).join(' | '),data.captured_at]);
      name = 'InvestorAce_Aktienideen.csv';
    }
    download('﻿' + [header,...rows].map(row => row.map(csv).join(';')).join('\r\n'), name, 'text/csv;charset=utf-8;');
  };
  $('download-json').onclick = e => { e.preventDefault(); refreshAssessments(); download(JSON.stringify(data,null,2), 'InvestorAce_Scanner.json', 'application/json'); };
  InvestorAceAssessment.watch(()=>{
    refreshAssessments();setView(view);
    if(activeDetail) detail(activeDetail.ticker, true, activeDetail.scope);
  },[...frozenAssessments.values()]);
  openLocation();
  window.addEventListener('popstate', openLocation);
})();
