"""Two information pages: a technical-only trend scan of the universe and the Claude vs Codex trading comparison.

Asked for on 21 Nov 2026. Neither page places an order or changes a score, label or rule.

* technical-scan.html: every universe member with daily trend data, grouped by its position against the
  36/50/200-day averages. In a correction the uptrend list is a watch list for the next uptrend; the active
  rules still buy only Buy labels while the S&P 500 is above its 200-day average.
* trading-compare.html: Claude's active account against Codex's accounts from the same start date. Each account
  is read from its own committed ledger; nothing is recomputed differently for one side.
"""
import json
from datetime import datetime, timezone
from html import escape
from pathlib import Path

SCAN_PAGE, COMPARE_PAGE = 'technical-scan.html', 'trading-compare.html'
COMPARE_FROM = '2026-11-20'      # Codex long/short forward start, declared before its first session
GROUPS = (('UPTREND', 'Uptrend: above the 36, 50 and 200-day averages, 50-day above the 200-day'),
          ('RECOVERING', 'Above the 50-day, still below the 200-day average'),
          ('PULLBACK', 'Above the 200-day average, below the 36 or 50-day'),
          ('DOWNTREND', 'Downtrend: below the 36, 50 and 200-day averages (short side)'))


def trend_group(t):
    c, s36, s50, s200 = (t.get(k) for k in ('close', 'sma36', 'sma50', 'sma200'))
    if not all(isinstance(x, (int, float)) and x > 0 for x in (c, s36, s50, s200)):
        return None
    if c > s36 and c > s50 and c > s200 and s50 > s200:
        return 'UPTREND'
    if c < s36 and c < s50 and c < s200:
        return 'DOWNTREND'
    if c > s200:
        return 'PULLBACK'
    return 'RECOVERING' if c > s50 else None


def scan(record):
    inputs = (record.get('_evidence') or {}).get('inputs') or {}
    rows, measured = [], 0
    for ticker, row in sorted(inputs.items()):
        timing = (row or {}).get('timing') or {} if isinstance(row, dict) else {}
        if timing.get('status') != 'AVAILABLE':
            continue
        group = trend_group(timing)
        if timing.get('sma200'):
            measured += 1
        if group is None:
            continue
        opp = (record.get(ticker) or {}).get('opportunity') or {}
        rows.append(dict(ticker=ticker, sector=row.get('sector'), group=group, close=timing['close'],
                         vs200=100 * (timing['close'] / timing['sma200'] - 1),
                         vs50=100 * (timing['close'] / timing['sma50'] - 1),
                         ext_atr=timing.get('extension_atr'), label=opp.get('label'), score=opp.get('score'),
                         from_high=(record.get(ticker) or {}).get('from_high')))
    above = sum(r['vs200'] > 0 for r in rows)
    return dict(rows=rows, measured=measured, breadth=100 * above / measured if measured else None)


def _num(x, fmt='+.1f', suffix='%'):
    return '—' if not isinstance(x, (int, float)) else format(x, fmt) + suffix


def render_scan(result, *, market=None, captured='', market_section=''):
    from war_scenario import label, shell
    parts = ['<h1>Technical trend scan</h1><p class="lead">Price trend only, no fundamentals. Universe members with '
             'daily data, from the build of ' + escape(captured[:10] or '—') + '. '
             + (f'Market: <b>{escape(market)}</b>. ' if market else '')
             + f'Breadth: <b>{_num(result["breadth"], ".0f")}</b> of {result["measured"]} members are above their '
             '200-day average.</p><div class="note">In a correction (S&amp;P 500 below its 200-day average) the '
             'active rules buy nothing; this list is the watch list for the next uptrend. Stocks that hold their '
             'trend in a correction are often defensive, not the next leaders. The downtrend list shows the '
             'candidates a short rule would use; Claude\'s rules open no shorts until a backtest supports it.</div>']
    for key, title in GROUPS:
        rows = sorted((r for r in result['rows'] if r['group'] == key),
                      key=lambda r: -r['vs200'] if key != 'DOWNTREND' else r['vs200'])
        body = ''.join(
            f'<tr><td><b>{escape(r["ticker"])}</b></td><td class="l">{escape(r["sector"] or "")}</td>'
            f'<td>{_num(r["vs200"])}</td><td>{_num(r["vs50"])}</td><td>{_num(r["ext_atr"], "+.1f", "")}</td>'
            f'<td>{_num(r["from_high"])}</td><td>{label(r["label"], r["score"])}</td></tr>' for r in rows)
        parts.append(f'<h2>{escape(title)} ({len(rows)})</h2><div class="tw"><table><thead><tr><th>Ticker</th>'
                     '<th class="l">Sector</th><th>vs 200-day</th><th>vs 50-day</th><th>ATR above 21-day EMA</th>'
                     '<th>From high</th><th>Label</th></tr></thead><tbody>'
                     + (body or '<tr><td colspan="7" class="muted">None.</td></tr>') + '</tbody></table></div>')
    return shell('Technical trend scan', ''.join(parts[:1]) + market_section
                 + '<h2>InvestorAce universe</h2>' + ''.join(parts[1:]))


def _sparkline(values, width=420, height=60):
    pts = [v for v in values if isinstance(v, (int, float))]
    if len(pts) < 2:
        return ''
    lo, hi = min(pts + [0.]), max(pts + [100.])
    step = width / (len(pts) - 1)
    path = ' '.join(f'{i * step:.1f},{height - (v - lo) / (hi - lo) * height:.1f}' for i, v in enumerate(pts))
    mid = height - (50 - lo) / (hi - lo) * height
    return (f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img" '
            f'aria-label="Share above the 200-day average"><line x1="0" x2="{width}" y1="{mid:.1f}" y2="{mid:.1f}" '
            'stroke="#555" stroke-dasharray="3 3"/><polyline fill="none" stroke="#c1d98b" stroke-width="2" '
            f'points="{path}"/></svg>')


def opportunity_candidates(scan, trend):
    """Match the same listing and close across both published screens."""
    import math
    import re
    if scan.get('schema') != 'market-scan-v1' or trend.get('schema') != 'market-trend-v1':
        return []
    day = trend.get('as_of')
    if not isinstance(day, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', day):
        return []
    trends = trend.get('opportunity_trends')
    if trends is None:
        trends = trend.get('leaders', []) + trend.get('new_uptrends', [])
    technical = {r['ticker']: r for r in trends if isinstance(r, dict) and r.get('ticker') and not r.get('event_jump')}
    found = {}
    for c in scan.get('candidates', []):
        if not isinstance(c, dict):
            continue
        symbol = c.get('yahoo')
        row = technical.get(symbol)
        if (not row or c.get('rank_eligible', c.get('status') == 'COMPLETE') is not True or c.get('price_date') != day
                or c.get('band') not in ('Buy', 'Strong Buy') or not isinstance(c.get('score'), (float, int))
                or not math.isfinite(c['score'])):
            continue
        found[symbol] = dict(ticker=symbol, name=c.get('name') or symbol, band=c['band'], score=c['score'],
                             new_trend=bool(row.get('new_uptrend')), rs3=row.get('rs3'))
    return sorted(found.values(), key=lambda r: (-r['score'], r['ticker']))


def opportunity_section(doc):
    from urllib.parse import urlencode
    body = []
    for r in doc['rows']:
        symbol = r['ticker']
        target = 'https://github.com/Usubillaga/InvestorAce/issues/new?' + urlencode({'title': 'add-ticker: ' + symbol})
        action = ('Check scorecard, quality and SMA36 entry' if r['covered'] else
                  f'<a href="{escape(target, quote=True)}">Review for universe admission</a>')
        body.append(f'<tr><td>{escape(symbol)}</td><td>{escape(r["band"])} · {r["score"]:.2f}</td>'
                    f'<td>{"New uptrend" if r["new_trend"] else "Uptrend"}</td><td>{action}</td></tr>')
    return ('<section id="opportunities"><h2>New long opportunities for review</h2>'
            f'<p>Trend close {escape(doc["as_of"] or "unavailable")}. '
            'The fundamental scanner and technical trend must agree on the same listing and price date. '
            'Swing entries still require the strategy’s fundamental and quality thresholds and a fresh SMA36 trigger.</p>'
            '<div class="tw"><table><thead><tr><th>Ticker</th><th>Scanner score</th><th>Trend</th><th>Next check</th>'
            '</tr></thead><tbody>' + (''.join(body) or '<tr><td colspan="4">No verified matches available.</td></tr>')
            + '</tbody></table></div></section>')


def render_market(trend, universe):
    """Market-wide section from market-scan/trend.json (built in GitHub Actions)."""
    if not trend or trend.get('schema') != 'market-trend-v1' or not trend.get('breadth'):
        return ('<h2>Whole market</h2><p class="muted">The market-wide trend file is not available yet; it is '
                'written by the market-scan workflow after each US close.</p>')
    b = trend['breadth']
    weekly = b[::-5][::-1][-12:] if len(b) > 5 else b
    hist = ''.join(f'<tr><td>{escape(r["date"])}</td><td>{_num(r["pct50"], ".0f")}</td><td>{_num(r["pct200"], ".0f")}</td>'
                   f'<td>{_num(r["uptrend"], ".0f")}</td><td>{int(r["highs"])}</td><td>{int(r["lows"])}</td></tr>'
                   for r in weekly)
    first, last = b[0], b[-1]
    direction = ('improving' if last['pct200'] - first['pct200'] >= 5 else
                 'deteriorating' if first['pct200'] - last['pct200'] >= 5 else 'flat')
    known = {k.upper() for k in universe} | {str((r or {}).get('yf') or '').upper() for r in universe.values()
                                             if isinstance(r, dict)}

    def table(rows):
        body = ''.join(
            f'<tr><td><b>{escape(r["ticker"])}</b>{" ✓" if r["ticker"].upper() in known else ""}</td>'
            f'<td class="l">{escape((r.get("name") or "")[:32])}</td><td>{_num(r["vs50"])}</td><td>{_num(r["vs200"])}</td>'
            f'<td>{_num(r["rs3"], "+.1f", " pts")}</td><td>{_num(r["rs6"], "+.1f", " pts")}</td>'
            f'<td>{_num(r["from_high"])}</td><td>{_num(r["value_musd"], ".0f", "m")}</td></tr>' for r in rows)
        return ('<div class="tw"><table><thead><tr><th>Ticker</th><th class="l">Company</th><th>vs 50-day</th>'
                '<th>vs 200-day</th><th>vs S&amp;P 3 months</th><th>vs S&amp;P 6 months</th><th>From high</th>'
                '<th>Traded per day (USD)</th></tr></thead><tbody>'
                + (body or '<tr><td colspan="8" class="muted">None.</td></tr>') + '</tbody></table></div>')
    return (f'<h2>Whole market: {int(trend["population"])} liquid NYSE/Nasdaq stocks</h2>'
            f'<p class="lead">As of {escape(trend["as_of"])}: <b>{_num(last["pct200"], ".0f")}</b> above their 200-day '
            f'average, <b>{_num(last["pct50"], ".0f")}</b> above their 50-day, <b>{int(trend["uptrend_count"])}</b> in an '
            f'uptrend, <b>{int(trend["new_uptrend_count"])}</b> of them new in the last 20 sessions; '
            f'{int(last["highs"])} new 52-week highs against {int(last["lows"])} lows. Over {len(b)} sessions breadth is '
            f'<b>{direction}</b> ({_num(first["pct200"], ".0f")} → {_num(last["pct200"], ".0f")} above the 200-day).</p>'
            + _sparkline([r['pct200'] for r in b])
            + '<div class="tw"><table><thead><tr><th>Date</th><th>Above 50-day</th><th>Above 200-day</th>'
            '<th>In uptrend</th><th>New highs</th><th>New lows</th></tr></thead><tbody>' + hist + '</tbody></table></div>'
            '<div class="note">Uptrend: close above the 50-day average, 50-day above the 200-day, 200-day rising over '
            '20 sessions. Stocks with a one-day move above 35% in the last 6 months (trial results, bids) are left out of '
            f'the lists ({int(trend.get("event_jumps") or 0)} today). ✓ marks an InvestorAce universe member; others can be added with add-ticker, and only then '
            'get a model label. Stocks only, at least 5 USD and 10m USD traded a day.</div>'
            f'<h3>Turning up: new uptrends, strongest against the S&amp;P 500 over 3 months ({len(trend["new_uptrends"])})</h3>'
            + table(trend['new_uptrends'])
            + f'<h3>Leaders: uptrends strongest against the S&amp;P 500 over 6 months ({len(trend["leaders"])})</h3>'
            + table(trend['leaders']))


def _drawdown(values):
    peak, worst = None, 0.
    for v in values:
        peak = v if peak is None else max(peak, v)
        worst = min(worst, v / peak - 1)
    return 100 * worst


def _money(amount, unit):
    return f'{amount:,.2f} {unit}' if isinstance(amount, (int, float)) else '—'


def claude_trades(doc, state, series, day, regime):
    import active_rules as rules
    filled = [o for o in state['orders'] if o['status'] == 'FILLED']
    stops = {}
    for p in state['positions']:
        if p['shares'] <= 0 or p['last_close'] is None:
            continue
        rate = 1 if p['currency'] == doc['account_currency'] else doc['fx'][p['currency']]
        entry = p['cost'] / (p['shares'] * rate)
        fraction = rules.STOP_CORRECTION if regime == 'CORRECTION' else rules.STOP
        opening, _, _, _, _, floor = rules.long_risk(p['ticker'], p, filled, series, day, p['last_close'], entry, fraction)
        if opening and regime:
            stops[p['ticker']] = (opening['fill_date'], opening['id'], floor)
    rows = []
    for o in reversed(state['orders']):
        filled_now = o['status'] == 'FILLED'
        stop = stops.get(o['ticker'])
        level = '—'
        if stop and filled_now and o['side'] == 'BUY' and (o['fill_date'], o['id']) >= stop[:2]:
            level = 'Close ≤ ' + _money(stop[2], o['currency'])
        rows.append([o['ticker'], o['side'], o['status'], o['submitted_at'], o.get('fill_date') if filled_now else None,
                     o['shares'], _money(o.get('amount'), doc['account_currency']), _money(o.get('fill_price') if filled_now else None, o['currency']), level])
    return rows


def lab_trades(paper, params, inputs):
    rows = []
    for o in reversed([*paper.get('orders', []), *paper['pending']]):
        filled = o['status'] == 'FILLED'
        pending = o['status'] == 'PENDING'
        opened = (paper['positions'].get(o['ticker']) or {}).get('opened_on')
        stop = '—'
        if o['action'] == 'OPEN' and (pending or (filled and opened == o.get('execution_session'))):
            t = (inputs.get(o['ticker']) or {}).get('timing') or {}
            sma = t.get('sma36') if t.get('status') == 'AVAILABLE' else None
            direction = '>' if o['side'] == 'SHORT' else '<'
            stop = f'Close {direction} SMA36'
            if sma is not None:
                stop += ' (' + _money(sma, 'USD') + ')'
            elif pending and o.get('sma36') is not None:
                stop += ' (signal: ' + _money(o['sma36'], 'USD') + ')'
        amount = o.get('turnover') if filled else params.get('position_usd') if pending and o['action'] == 'OPEN' else None
        rows.append([o['ticker'], o['action'] + ' ' + o['side'], o['status'], o.get('submitted_at'),
                     o.get('execution_session') if filled else None, None,
                     ('Planned ' if pending and amount is not None else '') + _money(amount, 'USD'),
                     _money(o.get('execution_close') if filled else None, 'USD'), stop])
    return rows


TRADE_COLUMNS = ['Ticker', 'Action', 'Order status', 'Submitted (offset shown)', 'Fill session',
                 'Shares ordered', 'Notional before fees', 'Fill price per share', 'Current closing exit level']


def trade_tables(accounts):
    out = ['<h2 id="trades">Paper trades and exit levels</h2><p>Daily fills use the session close. '
           'Stops are evaluated on a completed close. A moving average can change before the next decision. '
           'Orders before 20 November are shown to explain opening holdings.</p>']
    for a in accounts:
        out.append(f'<h3>{escape(a["name"])}</h3>')
        rows = a.get('trades') or []
        if not rows:
            out.append('<p>No recorded orders.</p>')
            continue
        out.append('<div class="tw"><table><thead><tr>' + ''.join(f'<th>{c}</th>' for c in TRADE_COLUMNS)
                   + '</tr></thead><tbody>')
        for row in rows:
            out.append('<tr>' + ''.join('<td>' + escape(str(v) if v is not None else '—') + '</td>' for v in row) + '</tr>')
        out.append('</tbody></table></div>')
    return ''.join(out)


def claude_account(root, series, today, regime=None):
    import active_trading as at
    path = Path(root) / 'paper_trades' / 'active-account.json'
    if not path.exists():
        return None
    doc = at.load(path)
    days = sorted(d for d, _ in series.get(at.BENCHMARK) or [] if COMPARE_FROM <= d <= today)
    curve = [(d, at.replay(doc, series, d)['value']) for d in days]
    curve = [(d, v) for d, v in curve if v is not None]
    if not curve:
        return None
    now = at.replay(doc, series, today)
    longs = sum(p['value'] for p in now['positions'] if p['shares'] > 0 and p['value'])
    shorts = -sum(p['value'] for p in now['positions'] if p['shares'] < 0 and p['value'])
    return dict(name='Claude · active rules ' + _rules_version(), currency='EUR', start=curve[0][1],
                value=curve[-1][1], ret=100 * (curve[-1][1] / curve[0][1] - 1), dd=_drawdown([v for _, v in curve]),
                longs=sum(p['shares'] > 0 for p in now['positions']), shorts=sum(p['shares'] < 0 for p in now['positions']),
                exposure=100 * (longs + shorts) / curve[-1][1], sessions=len(curve) - 1,
                trades=claude_trades(doc, now, series, today, regime),
                note='Long and short orders possible; the rules open longs only until a short rule passes the backtest.')


def _rules_version():
    try:
        import active_rules
        return active_rules.VERSION.replace('claude-rules-', '')
    except Exception:            # the page must render even if the rules module cannot load
        return ''


def codex_long_short(root, build_id=None, inputs=None):
    path = Path(root) / 'history' / 'long_short_lab.json'
    if not path.exists():
        return None
    doc = json.loads(path.read_text(encoding='utf-8'))
    if doc.get('schema') != 'codex-long-short-v1' or (build_id and doc.get('archive_build') != build_id):
        return None
    paper, params = doc.get('paper') or {}, doc.get('parameters') or {}
    capital = params.get('capital_usd') or 10000.
    positions = paper.get('positions') or {}
    gross = sum(abs(p.get('marked_notional') or 0) for p in positions.values())
    equity = paper['final_equity']
    return dict(name='Codex · long/short lab', currency='USD', start=capital, value=equity,
                ret=paper['return_pct'], dd=paper['drawdown_pct'],
                longs=sum(p.get('side') == 'LONG' for p in positions.values()),
                shorts=sum(p.get('side') == 'SHORT' for p in positions.values()),
                exposure=100 * gross / equity if equity else None, sessions=paper['sessions'], last=paper.get('last'),
                trades=lab_trades(paper, params, inputs or {}),
                note=f'{len(paper.get("pending") or [])} pending order(s); positions of '
                     f'{params.get("position_usd", "—")} USD, {params.get("slots_per_side", "—")} per side.')


def codex_active(root):
    path = Path(root) / 'history' / 'codex_trading.json'
    if not path.exists():
        return None
    doc = json.loads(path.read_text(encoding='utf-8'))
    decisions = [d for d in doc.get('decisions') or [] if d.get('session', '') >= COMPARE_FROM]
    curve = [d['outcomes']['timing']['equity'] for d in decisions
             if isinstance(((d.get('outcomes') or {}).get('timing') or {}).get('equity'), (int, float))]
    if not curve:
        return None
    account = (doc.get('accounts') or {}).get('timing') or {}
    holdings = account.get('holdings') or {}
    return dict(name='Codex · active (opportunity + timing)', currency='EUR', start=curve[0], value=curve[-1],
                ret=100 * (curve[-1] / curve[0] - 1), dd=_drawdown(curve), longs=len(holdings), shorts=0,
                exposure=100 * (curve[-1] - account.get('cash', curve[-1])) / curve[-1], sessions=len(curve) - 1,
                trades=[[o['ticker'], o['side'], o['status'], o.get('submitted'),
                         o.get('day') if o['status'] == 'Filled' else None, None,
                         ('Planned ' if o['status'] == 'Pending' else '') + _money(o.get('euros') if o['status'] in ('Pending', 'Filled') else None, 'EUR'),
                         _money(o.get('close'), o['currency']), 'Score < 6.5 or close below SMA200' if o['side'] == 'Buy' and o['ticker'] in holdings else '—']
                        for o in reversed(account.get('orders', []))],
                note='Long only.')


def benchmark(series, today):
    rows = [(d, c) for d, c in series.get('^GSPC') or [] if COMPARE_FROM <= d <= today]
    return 100 * (rows[-1][1] / rows[0][1] - 1) if rows and rows[0][0] == COMPARE_FROM else None


DESK_RAW = 'https://raw.githubusercontent.com/Usubillaga/InvestorAce-Tradingdesk/main/dist/'


def _fetch_json(url):
    from urllib.request import Request, urlopen
    with urlopen(Request(url, headers={'User-Agent': 'InvestorAce site build'}), timeout=15) as response:
        return json.load(response)


def index_section(fetch=_fetch_json):
    """The two index ETF accounts that run in the Trading Desk, read from its committed journals."""
    rows = []
    try:
        codex = fetch(DESK_RAW + 'index-paper.json')
        trades = codex.get('trades') or []
        rows.append(('Codex · index long/short day trades', codex.get('model'), codex.get('as_of'), codex.get('equity'),
                     len(trades), 'Not passed: loses to buy and hold in 60 of 60 backtest starts (−24% to −28% a year, '
                     'mostly costs). Kept running as a forward check of that backtest.'))
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        pass
    try:
        hold = fetch(DESK_RAW + 'index-hold.json')
        rows.append(('Claude · index buy and hold', hold.get('model'), hold.get('as_of'),
                     hold.get('equity') if hold.get('bought') else hold.get('capital'),
                     len(hold.get('holdings') or {}), 'Benchmark: no index timing rule beat it in the backtest. '
                     'Bought once at the open of ' + str(hold.get('start')) + '.'))
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        pass
    if not rows:
        return ('<h2>Index ETF accounts</h2><p class="muted">The Trading Desk journals could not be read at build '
                'time.</p>')
    body = ''.join(
        f'<tr><td class="l"><b>{escape(name)}</b></td><td>{escape(str(model or "—"))}</td><td>{escape(str(asof or "—"))}</td>'
        f'<td>{_num(value, ",.0f", " USD")}</td><td class="{"down" if isinstance(value, (int, float)) and value < 10000 else "up"}">'
        f'{_num(100 * (value / 10000 - 1) if isinstance(value, (int, float)) else None, "+.2f")}</td><td>{n}</td>'
        f'<td class="l">{escape(note)}</td></tr>' for name, model, asof, value, n, note in rows)
    return ('<h2>Index ETF accounts (SPY, QQQ, DAX, DIA, IWM)</h2><p class="lead">Both run automatically in the '
            '<a href="https://usubillaga.github.io/InvestorAce-Tradingdesk/index-paper.html">Trading Desk</a> from '
            '10,000 USD each; the backtest is in backtest.html (index ETF timing).</p><div class="tw"><table><thead><tr>'
            '<th class="l">Account</th><th>Model</th><th>As of</th><th>Value</th><th>Return</th><th>Trades / holdings</th>'
            '<th class="l">Status</th></tr></thead><tbody>' + body + '</tbody></table></div>')


def render_compare(accounts, spx, *, today, index_html=''):
    from war_scenario import shell
    rows = ''.join(
        f'<tr><td class="l"><b>{escape(a["name"])}</b></td><td>{a["sessions"]}</td>'
        f'<td>{_num(a["value"], ",.0f", "")} {a["currency"]}</td><td class="{"down" if (a["ret"] or 0) < 0 else "up"}">{_num(a["ret"], "+.2f")}</td>'
        f'<td>{_num(a["ret"] - spx if a["ret"] is not None and spx is not None and a["currency"] == "USD" and a.get("last") == today else None, "+.2f", " pts")}</td><td>{_num(a["dd"], "+.2f")}</td><td>{a["longs"]}</td>'
        f'<td>{a["shorts"]}</td><td>{_num(a["exposure"], ".0f")}</td>'
        f'<td class="l">{escape(a["note"])}</td></tr>' for a in accounts)
    body = ('<h1>Trading comparison</h1><p class="lead">Claude and Codex paper accounts from the close of '
            f'{COMPARE_FROM} to {escape(today)}. S&amp;P 500 over the same dates: <b>{_num(spx, "+.2f")}</b>.</p>'
            '<div class="note">Each account is read from its own committed ledger. Returns are in each account\'s '
            'currency (EUR or USD). The benchmark is a USD price index. The difference is shown for a USD account '
            'marked through the same close. A dash means no comparable observation.</div>'
            '<div class="tw"><table><thead><tr><th class="l">Account</th><th>Sessions</th><th>Value</th>'
            '<th>Return</th><th>vs S&amp;P 500</th><th>Max drawdown</th><th>Longs</th><th>Shorts</th>'
            '<th>Gross exposure</th><th class="l">Note</th></tr></thead><tbody>'
            + (rows or '<tr><td colspan="10" class="muted">No account has a session since the start date yet.</td></tr>')
            + '</tbody></table></div>')
    return shell('Trading comparison', body + index_html + trade_tables(accounts))


def site_pages(root, committed_build, *, now=None):
    import paper_portfolio as pp
    record = committed_build['record']
    today = (now or datetime.now(timezone.utc)).date()
    meta = record.get('_evidence') or {}
    market = None
    try:
        import active_rules
        market = active_rules.market(record)
    except Exception:
        market = None
    try:
        trend = json.loads((Path(root) / 'market-scan' / 'trend.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        trend = None
    try:
        section = render_market(trend, meta.get('inputs') or {})
    except (KeyError, TypeError, ValueError):       # a malformed trend file must not block the site
        section = render_market(None, {})
    try:
        scanner_data = json.loads((Path(root) / 'market-scan/latest.json').read_text(encoding='utf-8'))
        matches = opportunity_candidates(scanner_data, trend or {})
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        matches = []
    symbols = {r.get('yf') or k for k, r in (meta.get('inputs') or {}).items() if isinstance(r, dict)}
    ideas = dict(as_of=(trend or {}).get('as_of') if isinstance(trend, dict) else None,
                 rows=[dict(r, covered=r['ticker'] in symbols) for r in matches])
    section = '<p><a href="markov-experiments.html">Markov experiments · macro and pullbacks</a></p>' + opportunity_section(ideas) + section
    pages = [(Path(SCAN_PAGE), render_scan(scan(record), market=market if isinstance(market, str) else None,
                                           captured=str(meta.get('captured_at') or ''), market_section=section))]
    pages.append((Path("scanner-opportunities.json"), json.dumps(ideas, ensure_ascii=False)))
    snapshots = []
    for path in sorted((Path(root) / 'history' / 'runs').glob('*.json')):
        try:
            stamp = datetime.strptime(path.name[:8], '%Y%m%d').date()
        except ValueError:
            continue
        if (today - stamp).days <= 60:
            snapshots.append(json.loads(path.read_text(encoding='utf-8')))
    series = pp.merge_series(snapshots + [record])
    last = max((d for d, _ in series.get('^GSPC') or []), default=today.isoformat())
    accounts = []
    for load in (lambda: claude_account(root, series, last, market), lambda: codex_active(root), lambda: codex_long_short(root, committed_build['manifest']['run_id'], meta.get('inputs') or {})):
        try:
            account = load()
        except (ValueError, KeyError, TypeError, OSError):    # an unreadable ledger must not block the site
            account = None
        if account:
            accounts.append(account)
    pages.append((Path(COMPARE_PAGE), render_compare(accounts, benchmark(series, last), today=last,
                                                     index_html=index_section())))
    tape = dict(as_of=last, build=committed_build.get('manifest', {}).get('run_id'), columns=TRADE_COLUMNS,
                accounts=[dict(name=a['name'], trades=a['trades']) for a in accounts])
    pages.append((Path('competition-trades.json'), json.dumps(tape, ensure_ascii=False, allow_nan=False)))
    return pages


if __name__ == '__main__':
    from evidence import current_build
    for name, html in site_pages('.', current_build(Path('history'))):
        Path('/tmp').joinpath(name.name).write_text(html, encoding='utf-8')
        print('wrote', name)
