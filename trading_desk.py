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
            '20 sessions. ✓ marks an InvestorAce universe member; others can be added with add-ticker, and only then '
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


def claude_account(root, series, today):
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
                note='Long and short orders possible; the rules open longs only until a short rule passes the backtest.')


def _rules_version():
    try:
        import active_rules
        return active_rules.VERSION.replace('claude-rules-', '')
    except Exception:            # the page must render even if the rules module cannot load
        return ''


def codex_long_short(root):
    path = Path(root) / 'history' / 'long_short_lab.json'
    if not path.exists():
        return None
    doc = json.loads(path.read_text(encoding='utf-8'))
    paper, params = doc.get('paper') or {}, doc.get('parameters') or {}
    capital = params.get('capital_usd') or 10000.
    positions = paper.get('positions') or {}
    gross = sum(abs(p.get('marked_notional') or 0) for p in positions.values())
    equity = paper.get('final_equity') or capital
    curve = [v for _, v in paper.get('daily_equity') or [] if isinstance(v, (int, float))]
    return dict(name='Codex · long/short lab', currency='USD', start=capital, value=equity,
                ret=paper.get('return_pct') or 0., dd=paper.get('drawdown_pct') if curve else 0.,
                longs=sum(p.get('side') == 'LONG' for p in positions.values()),
                shorts=sum(p.get('side') == 'SHORT' for p in positions.values()),
                exposure=100 * gross / equity if equity else None, sessions=paper.get('sessions') or 0,
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
                note='Long only.')


def benchmark(series, today):
    rows = [(d, c) for d, c in series.get('^GSPC') or [] if COMPARE_FROM <= d <= today]
    return 100 * (rows[-1][1] / rows[0][1] - 1) if len(rows) > 1 else 0.


def render_compare(accounts, spx, *, today):
    from war_scenario import shell
    rows = ''.join(
        f'<tr><td class="l"><b>{escape(a["name"])}</b></td><td>{a["sessions"]}</td>'
        f'<td>{a["value"]:,.0f} {a["currency"]}</td><td class="{"down" if a["ret"] < 0 else "up"}">{_num(a["ret"], "+.2f")}</td>'
        f'<td>{_num(a["ret"] - spx, "+.2f", " pts")}</td><td>{_num(a["dd"], "+.2f")}</td><td>{a["longs"]}</td>'
        f'<td>{a["shorts"]}</td><td>{_num(a["exposure"], ".0f")}</td>'
        f'<td>{_num(a["ret"] / a["exposure"] * 100 if a["exposure"] else None, "+.1f")}</td>'
        f'<td class="l">{escape(a["note"])}</td></tr>' for a in accounts)
    body = ('<h1>Trading comparison</h1><p class="lead">Claude and Codex paper accounts from the close of '
            f'{COMPARE_FROM} to {escape(today)}. S&amp;P 500 over the same dates: <b>{_num(spx, "+.2f")}</b>.</p>'
            '<div class="note">Each account is read from its own committed ledger. Returns are in each account\'s '
            'currency (EUR or USD), so currency moves are part of the difference. "Return per 100% invested" divides '
            'the return by today\'s gross exposure (longs plus shorts): an account that holds mostly cash looks safe '
            'in a falling market without showing skill. A few weeks measure noise, not the rules.</div>'
            '<div class="tw"><table><thead><tr><th class="l">Account</th><th>Sessions</th><th>Value</th>'
            '<th>Return</th><th>vs S&amp;P 500</th><th>Max drawdown</th><th>Longs</th><th>Shorts</th>'
            '<th>Gross exposure</th><th>Return per 100% invested</th><th class="l">Note</th></tr></thead><tbody>'
            + (rows or '<tr><td colspan="11" class="muted">No account has a session since the start date yet.</td></tr>')
            + '</tbody></table></div>')
    return shell('Trading comparison', body)


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
    pages = [(Path(SCAN_PAGE), render_scan(scan(record), market=market if isinstance(market, str) else None,
                                           captured=str(meta.get('captured_at') or ''), market_section=section))]
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
    for load in (lambda: claude_account(root, series, last), lambda: codex_active(root), lambda: codex_long_short(root)):
        try:
            account = load()
        except (ValueError, KeyError, TypeError, OSError):    # an unreadable ledger must not block the site
            account = None
        if account:
            accounts.append(account)
    pages.append((Path(COMPARE_PAGE), render_compare(accounts, benchmark(series, last), today=last)))
    return pages


if __name__ == '__main__':
    from evidence import current_build
    for name, html in site_pages('.', current_build(Path('history'))):
        Path('/tmp').joinpath(name.name).write_text(html, encoding='utf-8')
        print('wrote', name)
