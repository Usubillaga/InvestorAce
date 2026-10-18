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
  const status = row => row.review_status === 'UNRESOLVED' ? 'Einwände offen' : 'Ungeprüft';
  const regimeName = {GOLDILOCKS:'Goldilocks', REFLATION:'Reflation', INFLATION:'Inflation', STAGFLATION:'Stagflation', RECESSION:'Rezession'};
  const regimes = data.regimes || Object.keys(regimeName);
  const currentRegime = data.current_regime;
  const candidates = market.candidates || [];
  const universeControls = ['query','band','sector','currency','holdings','minimum','review','regime'];
  const marketControls = ['m-query','m-band','m-sector','m-holdings','m-cap','m-minimum','m-regime'];
  let view = candidates.length ? 'market' : 'universe';
  let selected = [];

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
  } else {
    $('funnel').hidden = true;
  }
  $('audit-meta').innerHTML = `<p>Scanner erstellt: ${esc(date(data.generated_at))}<br>Modellaufnahme: ${esc(date(data.captured_at))}<br>Run: <code>${esc(data.run_id || 'nicht hinterlegt')}</code><br>Modell-Hash: <code>${esc(data.model_source_sha256)}</code></p>`
    + `<p>Marktscan: ${esc(market.generated_at ? date(market.generated_at) : 'nicht vorhanden')} · Status ${esc(market.status)}${market.note ? ' · ' + esc(market.note) : ''}<br>Quellen: SEC EDGAR (Tickerliste, XBRL-Frames, Companyfacts, Submissions), Yahoo-Tagesschlusskurse.</p>`
    + `<p>Kursprüfung Universum: ${esc(data.quote_policy.note)}</p>`;

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
    $('detail').hidden = true;
    const regime = regimeName[currentRegime] || 'nicht gespeichert';
    if (view === 'market') {
      setStats([['Geprüfte US-Unternehmen', num(market.funnel?.[0]?.count ?? null, 0)],
                ['Nach Qualitätsfiltern', num(market.funnel?.[1]?.count ?? null, 0)],
                ['Neue Ideen mit Score ≥ 7', candidates.filter(c => !c.in_universe && c.score >= 7).length],
                ['Kandidaten gespeichert', candidates.length]]);
      $('notice').innerHTML = (market.note ? `<b>${esc(market.note)}</b> ` : '') + '<b>Vorscore, keine Kaufempfehlung:</b> Der Screening-Score rechnet mechanisch aus SEC-Daten und einem Schlusskurs. Eine Bewertung entsteht erst, wenn ein Kandidat per add-ticker ins Modell kommt und gegengeprüft wird.';
      $('list-eyebrow').textContent = 'VOM MARKT ZUR AUSWAHL';
      $('list-title').textContent = 'Neue Aktienideen';
      $('table-note').textContent = `Reihenfolge nach ungerundetem Screening-Score. Regime-Fit bleibt separat und ändert die Reihenfolge nicht. Aktuelles Regime laut Engine: ${regime}. Sektor aus dem SEC-SIC-Code abgeleitet.`;
      $('scanner-head').innerHTML = '<tr><th scope="col">Unternehmen</th><th scope="col">Screening-Score</th><th scope="col">Kurs &amp; Marktwert</th><th scope="col">Kennzahlen (TTM)</th><th scope="col">Regime-Fit</th><th scope="col">Analyse</th></tr>';
    } else {
      setStats([['Aktien im Universum', data.universe_count],
                ['Buy / Strong Buy im Modell', data.rows.filter(r => r.model_score !== null && r.model_score >= 7).length],
                ['Mit offenen Einwänden', data.rows.filter(r => r.review_status === 'UNRESOLVED').length],
                ['Quellenprüfung hinterlegt', data.rows.filter(r => r.source_status === 'SOURCE_CHECKED').length]]);
      $('notice').innerHTML = '<b>Forschungsliste:</b> Ein Modellband ist eine vorläufige Einordnung. Offene wesentliche Einwände verhindern eine belastbare aktuelle Einstufung.';
      $('list-eyebrow').textContent = 'VOM UNIVERSUM ZUR AUSWAHL';
      $('list-title').textContent = 'Mein Universum';
      $('table-note').textContent = `Reihenfolge nach ungerundetem Modellscore. Regime-Fit bleibt separat. Aktuelles Regime laut Engine: ${regime}. „Neue Ideen“ blendet nur die im gespeicherten Datensatz gehaltenen Positionen aus.`;
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
      <td><span class="score">${num(c.score)}</span> / 10<br>${badge(c.band)}<span class="subline">Vorscore · ungeprüft</span></td>
      <td>${num(c.price)} USD<span class="subline">Schluss ${esc(day(c.price_date))}</span><span class="subline">Marktwert ${esc(money(c.metrics.market_cap))}</span></td>
      <td><span class="kv">Umsatz ${esc(signed(c.metrics.growth_pct))}</span><span class="kv">Op.-Marge ${esc(pct(c.metrics.operating_margin_pct))}</span><span class="kv">FCF-Rendite ${esc(pct(c.metrics.fcf_yield_pct))}</span><span class="kv">NGV-Deckung ${esc(pct(c.metrics.cover_pct, 0))}</span></td>
      <td><span class="fit">${num(c.regime_fit?.[regime], 1)}</span><span class="subline">/ 100 · ${esc(regimeName[regime])}<br>ohne Scoregewicht</span></td>
      <td><button class="open-detail" data-ticker="${esc(c.ticker)}" aria-label="Analyse zu ${esc(c.ticker)} öffnen">Prüfen ↗</button></td></tr>`;
  }
  const inputText = x => ({
    g: () => 'Umsatzwachstum ' + signed(x.input),
    p: () => 'operative Marge ' + pct(x.input),
    c: () => 'FCF-Marge ' + pct(x.input),
    b: () => x.input === null ? 'Nettoverschuldung/EBITDA nicht berechenbar' : 'Nettoverschuldung/EBITDA ' + num(x.input, 1) + '×',
    v: () => 'FCF-Rendite ' + pct(x.input),
    pr: () => 'NGV-Deckung ' + pct(x.input, 0),
    r: () => 'Dividenden- plus Rückkaufrendite ' + pct(x.input),
    d: () => x.input === null ? 'Aktienzahl ohne Vorjahreswert' : 'Aktienzahl ' + signed(x.input) + ' gg. Vorjahr',
  }[x.key] || (() => ''))();
  function marketDetail(c) {
    const m = c.metrics;
    const strong = c.components.filter(x => x.value >= 8).sort((a, b) => b.value - a.value).slice(0, 3);
    const weak = c.components.filter(x => x.value < 5.5).sort((a, b) => a.value - b.value).slice(0, 3);
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
      ['Operativer Cashflow', money(m.operating_cash_flow)], ['Investitionen (Capex)', money(m.capex)], ['Free Cashflow', money(m.fcf)], ['FCF-Marge', pct(m.fcf_margin_pct)],
      ['Abschreibungen', money(m.depreciation)], ['EBITDA (op. Ergebnis + Abschreibungen)', money(m.ebitda)],
      ['Finanzschulden', money(m.debt)], ['Liquidität', money(m.cash)], ['Nettoverschuldung (ohne Leasing)', money(m.net_debt)],
      ['Nettoverschuldung / EBITDA', m.nd_ebitda === null ? '—' : num(m.nd_ebitda, 2) + '×'], ['Bilanzstichtag', day(c.balance_date)],
      ['Aktien', num(m.shares === null ? null : m.shares / 1e6, 1) + ' Mio. · ' + shares], ['Aktienzahl gg. Vorjahr', signed(m.share_change_pct)],
      ['Marktwert', money(m.market_cap)], ['FCF-Rendite', pct(m.fcf_yield_pct)], ['Dividendenrendite', pct(m.dividend_yield_pct)], ['Rückkaufrendite (Aktienrückgang)', pct(m.buyback_yield_pct)],
      ['NGV je Aktie (FCF ÷ 8 %)', num(m.ngv_per_share) + ' USD'], ['NGV-Deckung des Kurses', pct(m.cover_pct, 0)],
    ];
    return `<div class="detail-head"><div><p class="eyebrow">MARKTSCAN · VORSCORE</p><h2 id="detail-title">${esc(c.name)} <span class="small">${esc(c.ticker)} · ${esc(c.exchange)}</span></h2>${badge(c.band)} <span class="small">Screening-Score ${num(c.score)} · mechanisch, ungeprüft</span></div><button id="close-detail" aria-label="Analyse schließen">Schließen ×</button></div>
      <div class="detail-grid"><div><h3>Warum auf der Liste?</h3>${strong.length ? '<ul>' + strong.map(line).join('') + '</ul>' : '<p>Keine Kategorie erreicht 8 Punkte; der Rang kommt aus einem breiten Mittelfeld.</p>'}
      <h3>Größte Schwächen</h3>${weak.length ? '<ul>' + weak.map(line).join('') + '</ul>' : '<p>Keine Kategorie unter 5,5 Punkten.</p>'}
      <h3>Datenbasis</h3><p>${esc(basis)}. Bilanz zum ${esc(day(c.balance_date))}. Schlusskurs vom ${esc(day(c.price_date))}. Sektor aus SIC ${esc(c.sic ?? '—')} (${esc(c.sic_description || 'ohne Beschreibung')}).</p>
      ${c.flags.length ? '<h3>Hinweise zur Datenqualität</h3><ul>' + c.flags.map(f => `<li><span class="issue-code">${esc(f)}</span><br>${esc(c.flag_text?.[f] || f)}</li>`).join('') + '</ul>' : ''}</div>
      <div><h3>Nächster Schritt</h3>${next}
      <h3>Kennzahlen</h3><table class="score-table"><tbody>${rows.map(([k, v]) => `<tr><td>${esc(k)}</td><td>${esc(v)}</td></tr>`).join('')}</tbody></table></div></div>
      <details open><summary>Scorebeiträge der acht Kategorien</summary><table class="score-table"><thead><tr><th>Kategorie</th><th>Kennzahl</th><th>Wert</th><th>Gewicht</th><th>Beitrag</th></tr></thead><tbody>${c.components.map(x => `<tr><td>${esc(x.label)}</td><td>${esc(inputText(x))}</td><td>${num(x.value,1)}</td><td>${num(x.weight*100,0)} %</td><td>${num(x.contribution,3)}</td></tr>`).join('')}</tbody></table></details>
      <h3>Quellen & Herkunft</h3><ul class="sources">${c.sources.map(s => `<li><a href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">${esc(s.title)}</a></li>`).join('')}</ul>`;
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
    return `<tr>
      <td><span class="ticker">${esc(r.ticker)}</span><span class="subline">${esc(r.issuer)}</span><span class="subline">${esc(r.listing)} · ${esc(r.sector)}${r.held_in_snapshot ? ' · Bestand im Datensatz' : ''}</span></td>
      <td><span class="score">${num(r.model_score)}</span> / 10<br>${badge(r.model_band)}<span class="subline">${r.score_basis === 'PUBLISHED_TOTAL' ? 'Fester Gesamtscore' : 'Modell · ungeprüft'}</span></td>
      <td>${num(r.price)} ${esc(r.currency)}<span class="subline">${r.quote_status === 'DATED' ? esc(date(r.quote_observed_at)) : 'Kursdatum: ' + esc({TIME_UNKNOWN:'unbekannt',STALE:'veraltet',MISSING:'fehlend',FUTURE:'ungültig'}[r.quote_status])}</span></td>
      <td><span class="pending">${status(r)}</span><span class="subline">${r.issues.length} offene Prüfpunkte</span><span class="subline">Quelle: ${r.source_status === 'SOURCE_CHECKED' ? 'geprüft, Bewertung offen' : 'Prüfung unvollständig'}</span></td>
      <td><span class="fit">${num(r.regime_fit[$('regime').value],1)}</span><span class="subline">/ 100 · ${esc(regimeName[$('regime').value])}<br>ohne Scoregewicht</span></td>
      <td><button class="open-detail" data-ticker="${esc(r.ticker)}" aria-label="Analyse zu ${esc(r.ticker)} öffnen">Prüfen ↗</button></td></tr>`;
  }
  function universeDetail(r) {
    const objections = r.objections.filter(x => !['verified','rejected'].includes(x.status));
    return `<div class="detail-head"><div><p class="eyebrow">ANALYSE & GEGENPRÜFUNG</p><h2 id="detail-title">${esc(r.issuer)} <span class="small">${esc(r.listing)}</span></h2>${badge(r.model_band)} <span class="small">Modellscore ${num(r.model_score)} · ${status(r)}</span></div><button id="close-detail" aria-label="Analyse schließen">Schließen ×</button></div>
      <div class="detail-grid"><div><h3>Warum auf die Prüfliste?</h3><p>${esc(r.thesis || 'Der gespeicherte Modellscore setzt diesen Titel auf die Prüfliste. Eine aktuelle, belegte Investmentthese wurde für den Scanner noch nicht erstellt.')}</p><h3>Stärkstes Gegenargument</h3><p>${esc(r.counterargument || 'Noch keine dokumentierte Gegenprüfung. Ein hoher Modellscore belegt weder einen Burggraben noch einen attraktiven Kaufpreis.')}</p><h3>Nächster Nachweis</h3><p>${esc(r.next_check)}</p>${r.notes_as_of ? `<p class="small">Research-Notiz vom ${esc(r.notes_as_of)}</p>` : ''}</div>
      <div><h3>Ungelöste Analysteneinwände</h3>${objections.length ? '<ul>' + objections.map(x => `<li><b>${esc(x.id)} · ${esc(x.severity)} · ${esc(x.status)}</b><br>${esc(x.message)}${x.response ? '<br><b>Antwort:</b> ' + esc(x.response) : ''}${x.resolution_required ? '<br><b>Zur Klärung:</b> ' + esc(x.resolution_required) : ''}</li>`).join('') + '</ul>' : '<p>Keine separaten Analysteneinwände hinterlegt. Das bestätigt keine abgeschlossene Gegenprüfung.</p>'}<h3>Offene Daten- und Bewertungsprüfung</h3><ul>${r.issues.map(x => `<li><span class="issue-code">${esc(x.code)} · ${esc(x.status)}</span><br>${esc(x.message)}</li>`).join('')}</ul></div></div>
      <h3>Quellen & Herkunft</h3><p>${esc(r.source_reason || 'Keine vollständige Quellenprüfung hinterlegt.')}</p><ul class="sources">${r.sources.map(s => `<li><a href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">${esc(s.title)}</a>${s.published_at ? ' · ' + esc(s.published_at) : ''}</li>`).join('') || '<li>Quellen müssen noch ergänzt werden.</li>'}</ul>
      <details><summary>Archivierte Bewertungsannahmen ansehen — ungeprüft</summary><p class="small">Herkunftsnachweis zum gespeicherten Modell. Wegen offener Prüfung keine aktuelle bestätigte Bewertung; NGV ist ein No-Growth-Wert und kein Kursziel.</p><table><tbody><tr><td>NGV im Modell</td><td>${num(r.archived_valuation.ngv)} ${esc(r.currency)}</td></tr><tr><td>NGV / Kurs im Modell</td><td>${r.archived_valuation.cover === null ? '—' : num(r.archived_valuation.cover*100,1) + ' %'}</td></tr><tr><td>EPV im Modell</td><td>${num(r.archived_valuation.epv)} ${esc(r.currency)}</td></tr><tr><td>Cashflow-Cushion</td><td>${r.archived_valuation.cushion === null ? 'nicht vergleichbar / nicht verfügbar' : num(r.archived_valuation.cushion,1) + ' pp'}</td></tr><tr><td>Kurszeitpunkt / Abrufzeit</td><td>${esc(r.quote_observed_at || 'unbekannt')} / ${esc(r.retrieved_at || 'unbekannt')}</td></tr></tbody></table><p>${esc(r.model_note)}</p></details>
      <details><summary>Scorebeiträge aus dem Modell</summary>${r.score_components.length ? '<table class="score-table"><thead><tr><th>Kategorie</th><th>Wert</th><th>Gewicht</th><th>Beitrag</th></tr></thead><tbody>' + r.score_components.map(c => `<tr><td>${esc(c.label)}</td><td>${num(c.value,1)}</td><td>${num(c.effective_weight*100,1)} %</td><td>${num(c.contribution,3)}</td></tr>`).join('') + '</tbody></table>' : '<p>Nur ein fester Gesamtscore verfügbar. Keine Kategorien erfunden.</p>'}</details>`;
  }

  // ---------- shared rendering
  function render() {
    selected = view === 'market' ? marketSelection() : universeSelection();
    const total = view === 'market' ? candidates.length : data.universe_count;
    $('result-count').textContent = `${selected.length} von ${total} ${view === 'market' ? 'Kandidaten' : 'Aktien'}`;
    $('empty').hidden = selected.length !== 0;
    $('empty').textContent = view === 'market' && !candidates.length
      ? (market.note || 'Noch kein Marktscan gespeichert.') + ' Der wöchentliche Lauf (market-scan) füllt diese Liste.'
      : 'Keine Treffer für diese Filter. Öffne „Alle Bänder“ oder setze die Filter zurück.';
    $('scanner-rows').innerHTML = selected.map(view === 'market' ? marketRow : universeRow).join('');
  }
  function detail(ticker) {
    const html = view === 'market'
      ? (c => c && marketDetail(c))(candidates.find(c => c.ticker === ticker))
      : (r => r && universeDetail(r))(data.rows.find(r => r.ticker === ticker));
    if (!html) return;
    $('detail').innerHTML = html;
    $('detail').hidden = false; $('detail').focus();
    $('close-detail').onclick = () => { $('detail').hidden = true; $('list-title').scrollIntoView({block:'start'}); };
    const jump = $('open-in-universe');
    if (jump) jump.onclick = () => {
      setView('universe'); $('band').value = 'all'; $('holdings').value = 'all'; $('query').value = jump.dataset.ticker; render(); detail(jump.dataset.ticker);
    };
    $('detail').scrollIntoView({behavior:'smooth',block:'start'});
  }
  $('scanner-rows').addEventListener('click', e => { const button = e.target.closest('button[data-ticker]'); if (button) detail(button.dataset.ticker); });
  for (const id of universeControls.concat(marketControls)) $(id).addEventListener(['query','minimum','m-query','m-minimum'].includes(id) ? 'input' : 'change', render);
  $('tab-market').onclick = () => setView('market');
  $('tab-universe').onclick = () => setView('universe');
  for (const [button, form, select] of [['reset-filters','filters','regime'], ['m-reset','market-filters','m-regime']]) {
    $(button).onclick = () => { $(form).reset(); $(select).value = $(select).dataset.default; $('detail').hidden = true; render(); };
  }
  const csv = value => '"' + String(value ?? '').replace(/^[=+@\-\t\r]/, "'" + '$&').replace(/"/g,'""') + '"';
  const download = (text, name, type) => {
    const url = URL.createObjectURL(new Blob([text], {type})); const a = document.createElement('a');
    a.href = url; a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  $('export').onclick = () => {
    let header, rows, name;
    if (view === 'market') {
      header = ['Ticker','Unternehmen','Sektor','Börse','Screening-Score','Band (ungeprüft)','Kurs USD','Kursdatum','Marktwert USD','Umsatzwachstum %','Op.-Marge %','FCF-Marge %','FCF-Rendite %','NGV-Deckung %','Nettoverschuldung/EBITDA','Im Universum','Basis','Periodenende','Scan'];
      rows = selected.map(c => [c.ticker,c.name,c.sector,c.exchange,c.score,c.band,c.price,c.price_date,c.metrics.market_cap,c.metrics.growth_pct,c.metrics.operating_margin_pct,c.metrics.fcf_margin_pct,c.metrics.fcf_yield_pct,c.metrics.cover_pct,c.metrics.nd_ebitda,c.in_universe ? 'ja' : 'nein',c.basis,c.period_end,market.as_of]);
      name = 'InvestorAce_Marktscan.csv';
    } else {
      header = ['Ticker','Listing','Unternehmen','Modellscore','Modellband ungeprüft','Aktuelle Einstufung','Währung','Sektor','Prüfstatus','Offene Prüfpunkte','Datenaufnahme'];
      rows = selected.map(r => [r.ticker,r.listing,r.issuer,r.model_score,r.model_band,'ungeprüft',r.currency,r.sector,r.review_status,r.issues.map(x => x.message).join(' | '),data.captured_at]);
      name = 'InvestorAce_Aktienideen.csv';
    }
    download('﻿' + [header,...rows].map(row => row.map(csv).join(';')).join('\r\n'), name, 'text/csv;charset=utf-8;');
  };
  $('download-json').onclick = e => { e.preventDefault(); download(JSON.stringify(data,null,2), 'InvestorAce_Scanner.json', 'application/json'); };
  setView(view);
})();
