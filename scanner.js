'use strict';
(() => {
  const data = JSON.parse(document.getElementById('scanner-data').textContent);
  const $ = id => document.getElementById(id);
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const num = (value, digits=2) => value === null || value === undefined ? '—' : Number(value).toLocaleString('de-DE', {minimumFractionDigits:digits, maximumFractionDigits:digits});
  const date = value => value ? new Date(value).toLocaleString('de-DE', {timeZone:'UTC',dateStyle:'medium',timeStyle:'short'}) + ' UTC' : 'nicht belegt';
  const badge = band => `<span class="badge ${band?.includes('Buy') ? 'buy' : band === 'Sell' ? 'sell' : 'hold'}">${esc(band || 'Ohne Score')}</span>`;
  const status = row => row.review_status === 'UNRESOLVED' ? 'Einwände offen' : 'Ungeprüft';
  const controls = ['query','band','sector','currency','holdings','minimum','review','regime'];
  let selected = [];
  $('captured').textContent = date(data.captured_at);
  $('universe').textContent = data.coverage;
  $('count-total').textContent = data.universe_count;
  $('count-buy').textContent = data.rows.filter(r => r.model_score !== null && r.model_score >= 7).length;
  $('count-rated').textContent = data.rated_count;
  $('count-sourced').textContent = data.rows.filter(r => r.source_status === 'SOURCE_CHECKED').length;
  for (const [control, field] of [['sector','sector'],['currency','currency']]) {
    for (const value of [...new Set(data.rows.map(r => r[field]))].sort()) {
      const option = document.createElement('option'); option.value = value; option.textContent = value; $(control).append(option);
    }
  }
  $('audit-meta').innerHTML = `<p>Scanner erstellt: ${esc(date(data.generated_at))}<br>Modellaufnahme: ${esc(date(data.captured_at))}<br>Run: <code>${esc(data.run_id || 'nicht hinterlegt')}</code><br>Modell-Hash: <code>${esc(data.model_source_sha256)}</code></p><p>Kursprüfung: ${esc(data.quote_policy.note)}</p>`;
  function render() {
    const query = $('query').value.trim().toLocaleLowerCase('de-DE');
    selected = data.rows.filter(r => {
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
    $('result-count').textContent = `${selected.length} von ${data.universe_count} Aktien`;
    $('empty').hidden = selected.length !== 0;
    $('scanner-rows').innerHTML = selected.map(r => `<tr>
      <td><span class="ticker">${esc(r.ticker)}</span><span class="subline">${esc(r.issuer)}</span><span class="subline">${esc(r.listing)} · ${esc(r.sector)}${r.held_in_snapshot ? ' · Bestand im Datensatz' : ''}</span></td>
      <td><span class="score">${num(r.model_score)}</span> / 10<br>${badge(r.model_band)}<span class="subline">${r.score_basis === 'PUBLISHED_TOTAL' ? 'Fester Gesamtscore' : 'Modell · ungeprüft'}</span></td>
      <td>${num(r.price)} ${esc(r.currency)}<span class="subline">${r.quote_status === 'DATED' ? esc(date(r.quote_observed_at)) : 'Kursdatum: ' + esc({TIME_UNKNOWN:'unbekannt',STALE:'veraltet',MISSING:'fehlend',FUTURE:'ungültig'}[r.quote_status])}</span></td>
      <td><span class="pending">${status(r)}</span><span class="subline">${r.issues.length} offene Prüfpunkte</span><span class="subline">Quelle: ${r.source_status === 'SOURCE_CHECKED' ? 'geprüft, Bewertung offen' : 'Prüfung unvollständig'}</span></td>
      <td><span class="fit">${num(r.regime_fit[$('regime').value],1)}</span><span class="subline">Modell / 100<br>ohne Scoregewicht</span></td>
      <td><button class="open-detail" data-ticker="${esc(r.ticker)}" aria-label="Analyse zu ${esc(r.ticker)} öffnen">Prüfen ↗</button></td></tr>`).join('');
  }
  function detail(ticker) {
    const r = data.rows.find(row => row.ticker === ticker); if (!r) return;
    const objections = r.objections.filter(x => !['verified','rejected'].includes(x.status));
    $('detail').innerHTML = `<div class="detail-head"><div><p class="eyebrow">ANALYSE & GEGENPRÜFUNG</p><h2 id="detail-title">${esc(r.issuer)} <span class="small">${esc(r.listing)}</span></h2>${badge(r.model_band)} <span class="small">Modellscore ${num(r.model_score)} · ${status(r)}</span></div><button id="close-detail" aria-label="Analyse schließen">Schließen ×</button></div>
      <div class="detail-grid"><div><h3>Warum auf die Prüfliste?</h3><p>${esc(r.thesis || 'Der gespeicherte Modellscore setzt diesen Titel auf die Prüfliste. Eine aktuelle, belegte Investmentthese wurde für den Scanner noch nicht erstellt.')}</p><h3>Stärkstes Gegenargument</h3><p>${esc(r.counterargument || 'Noch keine dokumentierte Gegenprüfung. Ein hoher Modellscore belegt weder einen Burggraben noch einen attraktiven Kaufpreis.')}</p><h3>Nächster Nachweis</h3><p>${esc(r.next_check)}</p>${r.notes_as_of ? `<p class="small">Research-Notiz vom ${esc(r.notes_as_of)}</p>` : ''}</div>
      <div><h3>Ungelöste Analysteneinwände</h3>${objections.length ? '<ul>' + objections.map(x => `<li><b>${esc(x.id)} · ${esc(x.severity)} · ${esc(x.status)}</b><br>${esc(x.message)}${x.response ? '<br><b>Antwort:</b> ' + esc(x.response) : ''}${x.resolution_required ? '<br><b>Zur Klärung:</b> ' + esc(x.resolution_required) : ''}</li>`).join('') + '</ul>' : '<p>Keine separaten Analysteneinwände hinterlegt. Das bestätigt keine abgeschlossene Gegenprüfung.</p>'}<h3>Offene Daten- und Bewertungsprüfung</h3><ul>${r.issues.map(x => `<li><span class="issue-code">${esc(x.code)} · ${esc(x.status)}</span><br>${esc(x.message)}</li>`).join('')}</ul></div></div>
      <h3>Quellen & Herkunft</h3><p>${esc(r.source_reason || 'Keine vollständige Quellenprüfung hinterlegt.')}</p><ul class="sources">${r.sources.map(s => `<li><a href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">${esc(s.title)}</a>${s.published_at ? ' · ' + esc(s.published_at) : ''}</li>`).join('') || '<li>Quellen müssen noch ergänzt werden.</li>'}</ul>
      <details><summary>Archivierte Bewertungsannahmen ansehen — ungeprüft</summary><p class="small">Herkunftsnachweis zum gespeicherten Modell. Wegen offener Prüfung keine aktuelle bestätigte Bewertung; NGV ist ein No-Growth-Wert und kein Kursziel.</p><table><tbody><tr><td>NGV im Modell</td><td>${num(r.archived_valuation.ngv)} ${esc(r.currency)}</td></tr><tr><td>NGV / Kurs im Modell</td><td>${r.archived_valuation.cover === null ? '—' : num(r.archived_valuation.cover*100,1) + ' %'}</td></tr><tr><td>EPV im Modell</td><td>${num(r.archived_valuation.epv)} ${esc(r.currency)}</td></tr><tr><td>Cashflow-Cushion</td><td>${r.archived_valuation.cushion === null ? 'nicht vergleichbar / nicht verfügbar' : num(r.archived_valuation.cushion,1) + ' pp'}</td></tr><tr><td>Kurszeitpunkt / Abrufzeit</td><td>${esc(r.quote_observed_at || 'unbekannt')} / ${esc(r.retrieved_at || 'unbekannt')}</td></tr></tbody></table><p>${esc(r.model_note)}</p></details>
      <details><summary>Scorebeiträge aus dem Modell</summary>${r.score_components.length ? '<table class="score-table"><thead><tr><th>Kategorie</th><th>Wert</th><th>Gewicht</th><th>Beitrag</th></tr></thead><tbody>' + r.score_components.map(c => `<tr><td>${esc(c.label)}</td><td>${num(c.value,1)}</td><td>${num(c.effective_weight*100,1)} %</td><td>${num(c.contribution,3)}</td></tr>`).join('') + '</tbody></table>' : '<p>Nur ein fester Gesamtscore verfügbar. Keine Kategorien erfunden.</p>'}</details>`;
    $('detail').hidden = false; $('detail').focus();
    $('close-detail').onclick = () => { $('detail').hidden = true; $('list-title').scrollIntoView({block:'start'}); };
    $('detail').scrollIntoView({behavior:'smooth',block:'start'});
  }
  $('scanner-rows').addEventListener('click', e => { const button = e.target.closest('button[data-ticker]'); if (button) detail(button.dataset.ticker); });
  for (const id of controls) $(id).addEventListener(id === 'query' || id === 'minimum' ? 'input' : 'change', render);
  $('reset-filters').onclick = () => { $('filters').reset(); $('detail').hidden = true; render(); };
  const csv = value => '"' + String(value ?? '').replace(/^[=+@\-\t\r]/, "'" + '$&').replace(/"/g,'""') + '"';
  $('export').onclick = () => {
    const header = ['Ticker','Listing','Unternehmen','Modellscore','Modellband ungeprüft','Aktuelle Einstufung','Währung','Sektor','Prüfstatus','Offene Prüfpunkte','Datenaufnahme'];
    const rows = selected.map(r => [r.ticker,r.listing,r.issuer,r.model_score,r.model_band,'ungeprüft',r.currency,r.sector,r.review_status,r.issues.map(x => x.message).join(' | '),data.captured_at]);
    const blob = new Blob(['\ufeff' + [header,...rows].map(row => row.map(csv).join(';')).join('\r\n')],{type:'text/csv;charset=utf-8;'});
    const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href=url; a.download='InvestorAce_Aktienideen.csv'; a.click(); setTimeout(() => URL.revokeObjectURL(url),1000);
  };
  $('download-json').onclick = e => {
    e.preventDefault(); const url = URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));
    const a = document.createElement('a'); a.href=url; a.download='InvestorAce_Scanner.json'; a.click(); setTimeout(() => URL.revokeObjectURL(url),1000);
  };
  render();
})();
