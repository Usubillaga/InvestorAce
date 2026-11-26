/* One public feed for both market screens. Only the GitHub workflow publishes alerts. */
(() => {
  const feed = 'https://raw.githubusercontent.com/Usubillaga/InvestorAce/panic-feed/panic-status.json';
  const thread = 'https://github.com/Usubillaga/InvestorAce/issues/241';
  const words = {
    de: ['Panikindikator · Alarm unter 20', 'Erste Handelsmessung steht aus', 'Daten veraltet',
      'Panik', 'Über der Schwelle oder bei 20', 'Datenquelle', 'GitHub-Meldungen', 'Indexgewichte',
      'Titel', 'Gewicht', 'Datenstand', 'nicht verifiziert', 'Abruf fehlgeschlagen', 'Schlussstand', 'Formel'],
    en: ['Panic indicator · Alert below 20', 'Awaiting the first market reading', 'Stale data',
      'Panic', 'At or above 20', 'Data source', 'GitHub alerts', 'Index weights',
      'Holding', 'Weight', 'As of', 'unverified', 'Fetch failed', 'Closing weights', 'Formula'],
    es: ['Indicador de pánico · Alerta bajo 20', 'Pendiente de la primera lectura de mercado', 'Datos desactualizados',
      'Pánico', 'En 20 o por encima', 'Fuente de datos', 'Alertas de GitHub', 'Pesos del índice',
      'Título', 'Peso', 'Fecha', 'sin verificar', 'Error de consulta', 'Pesos al cierre', 'Fórmula']
  };
  let saved, checked = 0, pending, failure = false;
  function node(tag, value) {
    const el = document.createElement(tag);
    if (value != null) el.textContent = value;
    return el;
  }
  function link(label, target) {
    const a = node('a', label);
    if (target && new URL(target).protocol === 'https:') a.href = target;
    return a;
  }
  function clock(stamp, lang, zone) {
    return new Intl.DateTimeFormat(lang, {timeZone:zone, month:'short', day:'numeric',
      hour:'2-digit', minute:'2-digit', timeZoneName:'short'}).format(new Date(stamp));
  }
  class PanicAlert extends HTMLElement {
    connectedCallback() {
      this.draw();
      refresh();
    }
    draw() {
      const lang = this.getAttribute('lang') || document.documentElement.lang;
      const t = words[lang] || words.en;
      const r = saved?.reading;
      const labels = {
        de: ['InvestorAce-Marktthermometer', 'Index-Leader-Strategie', 'Komponenten', 'Kursdaten ggf. verzögert. Feed-Latenz unbekannt.'],
        en: ['InvestorAce market thermometer', 'Index-leader strategy', 'components', 'Quotes may be delayed. Feed latency is unknown.'],
        es: ['Termómetro de mercado InvestorAce', 'Estrategia de líderes', 'componentes', 'Posible retraso de cotizaciones. Latencia desconocida.']
      }[lang] || ['InvestorAce thermometer', 'Index-leader strategy', 'components', 'Feed latency unknown.'];
      const head = node('h2', t[0]);
      const readings = node('div');
      for (const [title, slot] of [[labels[0], saved?.dashboard], [labels[1], saved]]) {
        const sample = slot?.reading;
        const stale = failure || slot?.status === 'unavailable' || (sample &&
          (Date.now() - Date.parse(sample.as_of) > 25 * 60000 || Date.now() >= Date.parse(sample.close)));
        const value = node('p');
        value.append(node('strong', title), ' · ');
        if (sample && Number.isFinite(sample.heat)) {
          value.append(node('strong', sample.heat.toLocaleString(lang, {maximumFractionDigits:3}) + ' / 100'),
            ' · ' + (stale ? t[2] : sample.heat < 20 ? t[3] : t[4]) + ' · ',
            clock(sample.as_of, lang, 'America/New_York')+' / '+clock(sample.as_of, lang, 'Europe/Berlin') +
            ' · '+sample.components+' '+labels[2]+' · ', link(t[14], sample.method), ' · ', link(t[5], sample.source));
        } else {
          value.append(stale ? t[12]+' · '+t[11] : t[1]);
        }
        readings.append(value);
      }
      const sources = node('p');
      sources.append(link(t[6], thread), ' · '+labels[3]);
      const details = node('details');
      details.open = this.querySelector('details')?.open || false;
      details.append(node('summary', t[7]));
      const today = new Intl.DateTimeFormat('sv-SE', {timeZone:'America/New_York'}).format(new Date());
      for (const [key, name] of [['SPX','S&P 500'], ['NDX','Nasdaq-100']]) {
        const w = saved?.weights?.[key];
        const stamp = w?.as_of;
        const previous = r?.session === today ? r.previous_session : saved?.weights_previous_session;
        const label = !stamp ? t[11] : stamp === today ? '' : stamp === previous && saved?.weights_checked === today ? t[13] : t[2];
        const title = node('h3', name);
        const date = node('p');
        date.append(w?.source ? link(t[10], w.source) : t[10], ' · '+(stamp || '—') + (label?' · '+label:'') + (w?.fetch_error?' · '+t[12]:''));
        details.append(title, date);
        if (!w?.rows?.length) continue;
        const table = node('table');
        const header = table.createTHead().insertRow();
        for (const text of ['#', t[8], t[9]]) header.append(node('th', text));
        const body = table.createTBody();
        w.rows.forEach((row, i) => {
          const tr = body.insertRow();
          tr.insertCell().textContent = i+1;
          tr.insertCell().textContent = row.name+(row.ticker?' ('+row.ticker+')':'');
          tr.insertCell().textContent = row.pct.toLocaleString(lang,{minimumFractionDigits:2})+' %';
        });
        details.append(table);
      }
      this.replaceChildren(head, readings, sources, details);
    }
  }
  function draw() { document.querySelectorAll('ia-panic-alert').forEach(el => el.draw()); }
  async function refresh() {
    if (pending || Date.now()-checked < 55000 || !document.querySelector('ia-panic-alert')) return;
    pending = true;
    checked = Date.now();
    try {
      const res = await fetch(feed, {cache:'no-store', signal:AbortSignal.timeout(8000)});
      if (!res.ok) throw Error(res.status);
      const data = await res.json();
      if (data.schema !== 1) throw Error('schema');
      saved = data;
      failure = false;
    } catch { failure = true; }
    finally { pending = false; draw(); }
  }
  customElements.define('ia-panic-alert', PanicAlert);
  setInterval(() => { if (!document.hidden) { draw(); refresh(); } }, 60000);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) { draw(); refresh(); } });
})();
