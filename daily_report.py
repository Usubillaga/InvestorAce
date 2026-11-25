"""Automatic daily report (Spanish) and data-status page, built with every site build. No Claude needed.

Asked for on 21 Nov 2026 to automate what the chat did by hand:

* informe-diario.html replaces the chat task "Cartera diaria": model account and each paper test against the
  S&P 500, every model position sorted by return, the active account with its positions, stops and recent
  orders (Claude vs Codex on trading-compare.html), and the flags of the user's rules (loss above 250 EUR,
  +20% within three weeks of entry, label no longer Buy).
* estado.html replaces the data part of the chat task "Control + Escáner": age of the build, the market scan,
  the trend scan and the backtest; label changes against the build about 15 days earlier; the scanner's top
  ten; and the size of the history folder.

Judgement (why a position fell, what to do) stays out: the pages only show what the committed data says.
"""
import json
from datetime import date, datetime, timedelta, timezone
from html import escape
from pathlib import Path

REPORT_PAGE, STATUS_PAGE = 'informe-diario.html', 'estado.html'
LOSS_FLAG_EUR, FAST_GAIN, FAST_DAYS = 250., 20., 21
STALE_DAYS = 4                     # calendar days; covers a weekend plus one missing build


def _eur(x):
    return '—' if x is None else ('−' if x < 0 else '+') + format(abs(x), ',.0f').replace(',', '.') + ' €'


def _num(x):
    return '—' if x is None else format(x, ',.0f').replace(',', '.')


def _pct(x):
    return '—' if x is None else ('−' if x < 0 else '+') + format(abs(x), '.2f').replace('.', ',') + ' %'


def _cls(x):
    return 'down' if (x or 0) < 0 else 'up'


def _snapshots(root, since):
    out = []
    for path in sorted((Path(root) / 'history' / 'runs').glob('*.json')):
        try:
            stamp = datetime.strptime(path.name[:8], '%Y%m%d').date()
        except ValueError:
            continue
        if stamp >= since:
            out.append(json.loads(path.read_text(encoding='utf-8')))
    return out


def _label(record, ticker):
    return ((record.get(ticker) or {}).get('opportunity') or {}).get('label')


def model_section(docs, results, record, today):
    capital = sum(r.get('capital') or 0 for r in results)
    value = sum(r.get('value_now') or 0 for r in results)
    lines, positions, flags = [], [], []
    for doc, r in zip(docs, results):
        lines.append(f'<tr><td class="l">{escape(doc.get("short_name") or doc["name"])}</td>'
                     f'<td class="{_cls(r.get("portfolio_return_pct"))}">{_pct(r.get("portfolio_return_pct"))}</td>'
                     f'<td>{_pct(r.get("benchmark_return_pct"))}</td><td>{_pct(r.get("control_return_pct"))}</td>'
                     f'<td>{escape(str(r.get("discretionary_name") or "—"))} {_pct(r.get("discretionary_return_pct"))}</td>'
                     f'<td>{_eur(r.get("pnl"))}</td></tr>')
        for h in r['holdings'] + (r.get('discretionary') or []):
            if h.get('value_now') is None or not h.get('cost'):
                continue
            pnl = h['value_now'] - h['cost']
            ret = h.get('return_pct')
            positions.append((ret if ret is not None else -1e9, h['ticker'], h.get('shares'), ret, pnl))
            entry = date.fromisoformat(h.get('entry_close_date') or r['entry_date'])
            label = _label(record, h['ticker'])
            if pnl <= -LOSS_FLAG_EUR:
                flags.append(f'{h["ticker"]}: pérdida de {_eur(pnl)} (regla de pérdida en la próxima ronda)')
            if ret is not None and ret >= FAST_GAIN and (today - entry).days <= FAST_DAYS:
                flags.append(f'{h["ticker"]}: {_pct(ret)} en menos de 3 semanas (regla O\'Neil: mantener 8 semanas)')
            if label not in ('Buy', 'Strong Buy'):
                flags.append(f'{h["ticker"]}: la etiqueta automática ya no es Buy ({escape(str(label or "sin etiqueta"))})')
    bench = [r.get('benchmark_return_pct') for r in results if r.get('benchmark_return_pct') is not None]
    head = (f'<h2>Cuenta modelo</h2><p class="lead">Valor <b>{_num(value)} €</b> de {_num(capital)} € · '
            f'<span class="{_cls(value - capital)}">{_eur(value - capital)} ({_pct(100 * (value / capital - 1) if capital else None)})</span>'
            + (f' · S&amp;P 500 {_pct(sum(bench) / len(bench))} en las mismas fechas' if bench else '') + '</p>')
    tests = ('<div class="tw"><table><thead><tr><th class="l">Test</th><th>Modelo</th><th>S&amp;P 500</th>'
             '<th>Control</th><th>Selección del usuario</th><th>Resultado</th></tr></thead><tbody>'
             + ''.join(lines) + '</tbody></table></div>')
    rows = ''.join(f'<tr><td><b>{escape(t)}</b></td><td>{n}</td><td class="{_cls(r)}">{_pct(r)}</td>'
                   f'<td class="{_cls(p)}">{_eur(p)}</td></tr>'
                   for _, t, n, r, p in sorted(positions, reverse=True))
    table = ('<h3>Posiciones del modelo, de mejor a peor</h3><div class="tw"><table><thead><tr><th>Ticker</th>'
             '<th>Acciones</th><th>%</th><th>€</th></tr></thead><tbody>' + rows + '</tbody></table></div>')
    return head + tests + table, flags


def active_section(root, record, series, today):
    import active_rules
    import active_trading as at
    path = Path(root) / 'paper_trades' / 'active-account.json'
    if not path.exists():
        return '', []
    doc = at.load(path)
    state = at.replay(doc, series, today.isoformat())
    plan = active_rules.plan(doc, record, series, today)
    recent = [o for o in state['orders'] if o.get('status') in ('FILLED', 'REJECTED', 'PENDING', 'CANCELLED')][-6:]
    pos = ''.join(f'<tr><td><b>{escape(p["ticker"])}</b></td><td>{p["shares"]}</td>'
                  f'<td class="{_cls(p.get("pnl_pct"))}">{_pct(p.get("pnl_pct"))}</td><td>{_eur(p.get("pnl"))}</td></tr>'
                  for p in state['positions'])
    orders = ''.join(f'<tr><td>#{o["id"]}</td><td class="l">{escape(o["side"])} {o["shares"]} {escape(o["ticker"])}</td>'
                     f'<td>{escape(str(o.get("fill_date") or "—"))}</td><td class="l">{escape(o["status"])}'
                     f'{(" · " + escape(o["reason"])) if o.get("reason") else ""}</td></tr>' for o in reversed(recent))
    notes = ''.join(f'<li>{escape(n)}</li>' for n in plan['notes'])
    html = (f'<h2>Cuenta activa (reglas {escape(active_rules.VERSION)})</h2><p class="lead">Valor '
            f'<b>{_num(state["value"])} €</b> · <span class="{_cls(state["pnl"])}">{_eur(state["pnl"])} '
            f'({_pct(state["return_pct"])})</span> · S&amp;P 500 desde la apertura {_pct(state["benchmark_pct"])} · '
            f'liquidez {_num(state["cash"])} €. Mercado: <b>{escape(plan["market"])}</b>. '
            '<a href="trading-compare.html">Comparación con Codex</a>.</p>'
            '<div class="tw"><table><thead><tr><th>Ticker</th><th>Acciones</th><th>%</th><th>€</th></tr></thead><tbody>'
            + (pos or '<tr><td colspan="4" class="muted">Sin posiciones.</td></tr>') + '</tbody></table></div>'
            f'<h3>Decisión de las reglas para la próxima ronda</h3><ul>{notes}</ul>'
            '<h3>Últimas órdenes</h3><div class="tw"><table><thead><tr><th>#</th><th class="l">Orden</th><th>Ejecución</th>'
            '<th class="l">Estado</th></tr></thead><tbody>'
            + (orders or '<tr><td colspan="4" class="muted">Ninguna.</td></tr>') + '</tbody></table></div>')
    return html, plan


def report_page(root, build, *, now=None):
    import paper_portfolio as pp
    from war_scenario import shell
    record = build['record']
    now = now or datetime.now(timezone.utc)
    captured = str((record.get('_evidence') or {}).get('captured_at') or '')
    built = datetime.fromisoformat(captured).date() if captured else None
    docs = pp.load(Path(root) / 'paper_trades')
    start = min([date.fromisoformat(d['entry_date']) for d in docs] + [now.date()]) - timedelta(days=60)
    series = pp.merge_series(_snapshots(root, start) + [record])
    last = max((d for d, _ in series.get('^GSPC') or []), default=None)
    today = date.fromisoformat(last) if last else now.date()
    parts = [f'<h1>Informe diario</h1><p class="lead">Generado automáticamente con cada actualización del sitio, '
             f'sin intervención de Claude. Cierre usado: <b>{escape(str(last or "—"))}</b> · build del '
             f'{escape(captured[:16].replace("T", " "))} UTC.</p>']
    if built is None or (now.date() - built).days > STALE_DAYS:
        parts.append('<div class="note"><b>Datos viejos:</b> el último build tiene más de '
                     f'{STALE_DAYS} días; las cifras pueden no reflejar el mercado actual.</div>')
    flags = []
    if any(d.get('comparison_group') == pp.ROUND2 for d in docs):
        parts.append('<p><a href="index.es.html#paper-round2">Ronda 2 · reglas frente a puntuación</a></p>')
        docs = [d for d in docs if d.get('comparison_group') != pp.ROUND2]
    if docs:
        results = [pp.evaluate(d, series, today) for d in docs]
        html, flags = model_section(docs, results, record, today)
        parts.append(html)
    active_html, _ = active_section(root, record, series, today)
    parts.append(active_html)
    parts.append('<h2>Alertas de tus reglas</h2>' + ('<ul>' + ''.join(f'<li>{escape(f)}</li>' for f in flags) + '</ul>'
                                                     if flags else '<p class="muted">Ninguna.</p>'))
    parts.append('<div class="note">Pocos días miden ruido, no el modelo. Páginas relacionadas: '
                 '<a href="paper-test.html">tests de papel</a>, <a href="trade.html">cuenta activa</a>, '
                 '<a href="technical-scan.html">tendencia del mercado</a>, <a href="estado.html">estado de los datos</a>.</div>')
    return shell('Informe diario', ''.join(parts)).replace('lang="en"', 'lang="es"', 1)


def _age(stamp, now):
    if not stamp:
        return None
    try:
        when = datetime.fromisoformat(str(stamp).replace('Z', '+00:00'))
    except ValueError:
        when = datetime.combine(date.fromisoformat(str(stamp)[:10]), datetime.min.time(), timezone.utc)
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return (now - when).total_seconds() / 86400


def status_page(root, build, *, now=None):
    from war_scenario import shell
    root, now = Path(root), now or datetime.now(timezone.utc)
    record = build['record']

    def read(path):
        try:
            return json.loads((root / path).read_text(encoding='utf-8'))
        except (OSError, ValueError):
            return {}
    scan, trend, backtest = read('market-scan/latest.json'), read('market-scan/trend.json'), read('backtests/latest.json')
    rows = [('Build del modelo', (record.get('_evidence') or {}).get('captured_at'), 2),
            ('Escáner de mercado', (scan.get('quote_refresh') or {}).get('attempted_at') or scan.get('generated_at'), 4),
            ('Tendencia del mercado', trend.get('generated_at'), 4),
            ('Backtest', backtest.get('generated_at'), 40)]
    health = ''.join(
        f'<tr><td class="l">{escape(name)}</td><td>{escape(str(stamp or "—")[:16].replace("T", " "))}</td>'
        f'<td class="{"down" if age is None or age > limit else "up"}">'
        f'{"falta" if age is None else ("viejo" if age > limit else "al día")}</td></tr>'
        for name, stamp, limit in rows for age in [_age(stamp, now)])
    labels = {t: (v.get('opportunity') or {}).get('label') for t, v in record.items()
              if isinstance(v, dict) and isinstance(v.get('opportunity'), dict)}
    counts = {}
    for label in labels.values():
        counts[label or 'sin etiqueta'] = counts.get(label or 'sin etiqueta', 0) + 1
    older = None
    for path in sorted((root / 'history' / 'runs').glob('*.json')):
        try:
            stamp = datetime.strptime(path.name[:8], '%Y%m%d').date()
        except ValueError:
            continue
        if stamp <= now.date() - timedelta(days=15):
            older = path
    changes, added = [], []
    if older is not None:
        previous = json.loads(older.read_text(encoding='utf-8'))
        for t, label in sorted(labels.items()):
            if not isinstance(previous.get(t), dict):
                added.append(t)                    # joined the universe since then: not a label change
                continue
            before = (previous[t].get('opportunity') or {}).get('label')
            if before != label:
                changes.append(f'<tr><td><b>{escape(t)}</b></td><td>{escape(str(before or "—"))}</td>'
                               f'<td>{escape(str(label or "—"))}</td></tr>')
    top = sorted(scan.get('candidates') or [], key=lambda c: -(c.get('score') or 0))[:10]
    ideas = ''.join(f'<tr><td><b>{escape(c["ticker"])}</b>{" ✓" if c.get("in_universe") else ""}</td>'
                    f'<td class="l">{escape(str(c.get("name") or "")[:30])}</td><td>{(c.get("score") or 0):.2f}</td>'
                    f'<td>{escape(", ".join(c.get("flags") or []) or "—")}</td></tr>' for c in top)
    size = sum(p.stat().st_size for p in (root / 'history').rglob('*') if p.is_file()) / 1e6
    body = ('<h1>Estado de los datos</h1><p class="lead">Generado automáticamente con cada actualización del sitio.</p>'
            '<h2>Actualizaciones</h2><div class="tw"><table><thead><tr><th class="l">Fuente</th><th>Última</th>'
            '<th>Estado</th></tr></thead><tbody>' + health + '</tbody></table></div>'
            '<h2>Etiquetas del universo</h2><p class="lead">' + ' · '.join(
                f'{escape(k)} {v}' for k, v in sorted(counts.items(), key=lambda kv: -kv[1])) + '</p>'
            f'<h3>Cambios frente al build de hace unos 15 días ({escape(older.name[:8] if older else "—")})</h3>'
            '<div class="tw"><table><thead><tr><th>Ticker</th><th>Antes</th><th>Ahora</th></tr></thead><tbody>'
            + (''.join(changes) or '<tr><td colspan="3" class="muted">Sin cambios.</td></tr>') + '</tbody></table></div>'
            + (f'<p class="lead">Nuevos en el universo desde entonces ({len(added)}): {escape(", ".join(added))}.</p>'
               if added else '')
            + '<h2>Escáner: las 10 mejores ideas</h2><div class="tw"><table><thead><tr><th>Ticker</th><th class="l">Empresa</th>'
            '<th>Score</th><th>Avisos</th></tr></thead><tbody>' + ideas + '</tbody></table></div>'
            f'<p class="lead">Carpeta history sin comprimir: <b>{_num(size)} MB</b>. Git la guarda comprimida '
            '(son archivos JSON muy repetitivos); el límite que GitHub recomienda, 1 GB, se refiere al tamaño '
            'comprimido del repositorio.</p>')
    return shell('Estado de los datos', body).replace('lang="en"', 'lang="es"', 1)


def site_pages(root, build, *, now=None):
    pages = []
    for name, make in ((REPORT_PAGE, report_page), (STATUS_PAGE, status_page)):
        try:
            pages.append((Path(name), make(root, build, now=now)))
        except (OSError, ValueError, KeyError, TypeError) as exc:     # one broken page must not block the site
            import logging
            logging.warning('%s unavailable: %s', name, exc)
    return pages


if __name__ == '__main__':
    from evidence import current_build
    for name, html in site_pages('.', current_build(Path('history'))):
        Path('/tmp', name.name).write_text(html, encoding='utf-8')
        print('wrote /tmp/' + name.name)
