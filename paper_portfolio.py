"""Paper portfolios that test the automatic InvestorAce labels out of sample.

A portfolio file in paper_trades/ freezes its holdings, weights, entry and
exit dates before the entry date. The nightly build records the recent
closes of every tracked symbol (macro.pulse.tracked), so the evaluation
reads entry and exit closes from committed snapshots and never from
hindsight. Nothing here changes a score, a label or the real portfolio.
"""
import json
import math
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FOLDER = ROOT / 'paper_trades'
TRACK_DAYS_AFTER_EXIT = 5


def load(folder=FOLDER):
    out = []
    for path in sorted(Path(folder).glob('*.json')):
        doc = json.loads(path.read_text(encoding='utf-8'))
        if doc.get('schema') == 'paper-portfolio-v1':
            out.append(dict(doc, _file=path.name))
    return out


def _symbols(doc):
    symbols = [h['yahoo'] for h in doc.get('holdings', [])]
    symbols += [h['yahoo'] for h in (doc.get('control_basket') or {}).get('holdings', [])]
    symbols += [h['yahoo'] for h in (doc.get('discretionary') or {}).get('holdings', [])]
    if doc.get('benchmark', {}).get('yahoo'):
        symbols.append(doc['benchmark']['yahoo'])
    return symbols


def tracked_symbols(today, folder=FOLDER):
    """Symbols of portfolios whose window is open (entry - 3 days to exit + 5 days)."""
    out = set()
    for doc in load(folder):
        start = date.fromisoformat(doc['entry_date']) - timedelta(days=3)
        end = date.fromisoformat(doc['exit_date']) + timedelta(days=TRACK_DAYS_AFTER_EXIT)
        if start <= today <= end:
            out.update(_symbols(doc))
    return sorted(out)


def _close_on_or_before(series, day):
    """Last close on or before `day` from [(date, close)], with its date."""
    best = None
    for when, value in series or []:
        if when <= day and value:
            best = (when, value)
    return best


def _close_on_or_after(series, day):
    """First close on or after `day`: the first price executable after the decision."""
    for when, value in sorted(series or []):
        if when >= day and value:
            return (when, value)
    return None


def _days(day, n):
    return (date.fromisoformat(day) + timedelta(days=n)).isoformat()


US_CLOSE_UTC = '21:05'      # NYSE closes at 21:00 UTC in winter; summer is earlier, so this is conservative


def merge_series(snapshots):
    """{symbol: [(date, close)]} merged over several snapshots' pulse.tracked.

    A build that ran during the trading day records that day's partial bar. It is not a close, so a row dated
    on the capture day counts only when the build ran after the US close; later snapshots overwrite earlier."""
    merged = {}
    for snapshot in snapshots:
        evidence = (snapshot or {}).get('_evidence') or {}
        tracked = (((evidence.get('macro') or {}).get('pulse') or {}).get('tracked')) or {}
        captured = str(evidence.get('captured_at') or '')
        day, clock = captured[:10], captured[11:16]
        partial_day = day if captured and clock < US_CLOSE_UTC else None
        for symbol, rows in tracked.items():
            target = merged.setdefault(symbol, {})
            for when, value in rows:
                if when != partial_day:
                    target[when] = value
    return {s: sorted(v.items()) for s, v in merged.items()}


def _leg(holdings, series, entry, exit_):
    rows, weight_used, total = [], 0., 0.
    for h in holdings:
        start = _close_on_or_after(series.get(h['yahoo']), entry)
        if start and (start[0] > _days(entry, 4) or start[0] > exit_):
            start = None                       # no entry close yet, or only a late one
        end = _close_on_or_before(series.get(h['yahoo']), exit_)
        if not start or not end or end[0] < start[0] or end[0] < _days(exit_, -4):
            rows.append(dict(h, status='NO_PRICE'))   # missing or stale close: never 0% by default
            continue
        change = 100 * (end[1] / start[1] - 1)
        rows.append(dict(h, entry_close=start[1], entry_close_date=start[0], exit_close=end[1],
                         exit_close_date=end[0], return_pct=change, status='PRICED'))
        weight_used += h['weight_pct']
        total += h['weight_pct'] * change
    return rows, (total / weight_used if weight_used else None), weight_used


def _size(rows, amount, fx):
    """Whole shares per position. Sizing uses the entry close once known, else the signal price.

    `fx` converts a listing currency to USD at a rate fixed in the portfolio file; it only sizes the
    positions and values them in dollars, returns stay in each listing currency."""
    cost = value = 0.
    for h in rows:
        rate = (fx or {}).get(h.get('currency') or 'USD', 1.)
        price = h.get('entry_close') or h.get('signal_price')
        if not price or not rate:
            continue
        shares = math.floor(amount * h['weight_pct'] / 100 / (price * rate))
        spent = shares * price * rate
        latest = h.get('exit_close')
        h.update(shares=shares, cost_usd=spent, sizing_price=price,
                 sizing='ENTRY_CLOSE' if h.get('entry_close') else 'SIGNAL_PRICE',
                 value_usd=shares * latest * rate if latest and h.get('entry_close') else spent)
        cost += spent
        value += h['value_usd']
    return cost, value


def _capital(doc, result):
    """Dollar sizing of the model sleeve and the pick sleeve; the portfolio file fixes capital and FX."""
    capital = doc.get('capital_usd')
    if not capital:
        return
    sleeve = float(result.get('discretionary_sleeve_pct') or 0.)
    fx = doc.get('fx_usd') or {}
    cost = value = 0.
    for rows, amount in ((result['holdings'], capital * (100 - sleeve) / 100),
                         (result.get('discretionary') or [], capital * sleeve / 100)):
        c, v = _size(rows, amount, fx)
        cost, value = cost + c, value + v
    result.update(capital_usd=float(capital), invested_usd=cost, cash_usd=capital - cost, value_usd=value + (capital - cost),
                  pnl_usd=value - cost, fx_usd=fx)


def evaluate(doc, series, as_of=None):
    result = _evaluate(doc, series, as_of)
    _capital(doc, result)
    return result


def _evaluate(doc, series, as_of=None):
    """Weighted returns of the holdings, the control basket and the benchmark."""
    exit_ = min(doc['exit_date'], (as_of or date.fromisoformat(doc['exit_date'])).isoformat())
    entry = doc['entry_date']
    if exit_ < entry:
        # Before the entry date nothing is held; no return is computed.
        pending = lambda hs: [dict(h, status='PENDING') for h in hs]
        pick = doc.get('discretionary') or {}
        return dict(name=doc['name'], entry_date=entry, valued_to=None, final=False, status='PENDING',
                    portfolio_return_pct=None, priced_weight_pct=0., holdings=pending(doc['holdings']),
                    control_return_pct=None, control_priced_weight_pct=0.,
                    control=pending((doc.get('control_basket') or {}).get('holdings', [])),
                    benchmark_return_pct=None, excess_vs_benchmark_pct=None, excess_vs_control_pct=None,
                    discretionary_name=pick.get('name'), discretionary=pending(pick.get('holdings', [])),
                    discretionary_return_pct=None,
                    discretionary_sleeve_pct=float(pick.get('sleeve_weight_pct') or 0.),
                    combined_return_pct=None, excess_combined_vs_benchmark_pct=None)
    holdings, portfolio, used = _leg(doc['holdings'], series, entry, exit_)
    control_rows, control, control_used = _leg((doc.get('control_basket') or {}).get('holdings', []),
                                               series, entry, exit_)
    bench = None
    if doc.get('benchmark'):
        rows, bench, _ = _leg([dict(doc['benchmark'], weight_pct=100.)], series, entry, exit_)
    # The user's own pick is a separate sleeve: the model result stays clean.
    pick = doc.get('discretionary') or {}
    pick_rows, pick_return, _ = _leg(pick.get('holdings', []), series, entry, exit_)
    sleeve = float(pick.get('sleeve_weight_pct') or 0.) if pick_rows else 0.
    combined = ((100 - sleeve) * portfolio + sleeve * pick_return) / 100 \
        if None not in (portfolio, pick_return) and sleeve else None
    final = exit_ == doc['exit_date']
    return dict(name=doc['name'], entry_date=entry, valued_to=exit_, final=final,
                status='FINAL' if final else 'RUNNING', discretionary_name=pick.get('name'), discretionary=pick_rows,
                discretionary_return_pct=pick_return, discretionary_sleeve_pct=sleeve,
                combined_return_pct=combined,
                excess_combined_vs_benchmark_pct=combined - bench if None not in (combined, bench) else None,
                portfolio_return_pct=portfolio, priced_weight_pct=used, holdings=holdings,
                control_return_pct=control, control_priced_weight_pct=control_used, control=control_rows,
                benchmark_return_pct=bench,
                excess_vs_benchmark_pct=portfolio - bench if None not in (portfolio, bench) else None,
                excess_vs_control_pct=portfolio - control if None not in (portfolio, control) else None)


def report(result):
    """Short markdown summary for the user."""
    pct = lambda v: '—' if v is None else ('%+.2f%%' % v)
    if result.get('status') == 'PENDING':
        return f"**{result['name']}** · starts with the close of {result['entry_date']}; nothing held yet."
    lines = [f"**{result['name']}** · {result['entry_date']} → {result['valued_to']}"
             + ('' if result['final'] else ' (interim)'),
             f"InvestorAce Buy portfolio {pct(result['portfolio_return_pct'])} · "
             f"S&P 500 {pct(result['benchmark_return_pct'])} · "
             f"earnings-IV basket {pct(result['control_return_pct'])}",
             f"Excess vs S&P 500 {pct(result['excess_vs_benchmark_pct'])} · "
             f"vs IV basket {pct(result['excess_vs_control_pct'])}"]
    if result.get('discretionary'):
        picks = ', '.join(f"{h['ticker']} {pct(h.get('return_pct'))}" for h in result['discretionary'])
        sleeve = result['discretionary_sleeve_pct']
        lines += [f"{result['discretionary_name']}: {picks} · "
                  f"combined ({100 - sleeve:.0f}% model + {sleeve:.0f}% pick) {pct(result['combined_return_pct'])}"
                  f" · vs S&P 500 {pct(result['excess_combined_vs_benchmark_pct'])}"]
    if result.get('capital_usd'):
        lines.append(f"Capital ${result['capital_usd']:,.0f}: invested ${result['invested_usd']:,.0f}, cash "
                     f"${result['cash_usd']:,.0f}, value ${result['value_usd']:,.0f}, gain/loss ${result['pnl_usd']:+,.0f}")
    lines += ['', '| Ticker | Label | Weight | Shares | Entry | Exit | Return |', '|---|---|---|---|---|---|---|']
    ranked = lambda h: -h['return_pct'] if h.get('return_pct') is not None else float('inf')
    for h in sorted(result['holdings'], key=ranked):
        lines.append(f"| {h['ticker']} | {h['label']} {h['score']:.2f} | {h['weight_pct']:.1f}% | "
                     f"{h.get('shares', '—')} | {h.get('entry_close', '—')} | {h.get('exit_close', '—')} | "
                     f"{pct(h.get('return_pct'))} |")
    missing = [h['ticker'] for h in result['holdings'] + result['control'] + result.get('discretionary', [])
               if h['status'] != 'PRICED']
    if missing:
        lines.append('\nNot priced: ' + ', '.join(missing))
    return '\n'.join(lines)


PAGE = 'paper-test.html'


def _pct(value, css=True):
    from html import escape
    if value is None:
        return '<span class="muted">—</span>'
    text = escape('%+.2f%%' % value)
    return f'<span class="{"up" if value > 0 else "down" if value < 0 else ""}">{text}</span>' if css else text


def _price(h, key):
    value = h.get(key)
    return '<span class="muted">—</span>' if value is None else format(value, ',.2f')


def render(results, docs, *, now):
    """One page with every paper portfolio: rules, live result, holdings."""
    from html import escape
    from war_scenario import shell, label
    body = ['<h1>Paper test</h1><p class="lead">A fictitious portfolio that checks whether the automatic '
            'InvestorAce Buy labels beat the market out of sample. Holdings, weights and dates were frozen '
            'before the entry date; prices come only from the nightly builds, never from hindsight. '
            f'Updated {escape(now.strftime("%Y-%m-%d %H:%M"))} UTC.</p>']
    for result, doc in zip(results, docs):
        status = result['status']
        state = {'PENDING': f"Not started: entry at the close of {result['entry_date']}",
                 'RUNNING': f"Running: valued to {result['valued_to']} (interim)",
                 'FINAL': f"Final: {result['entry_date']} → {result['valued_to']}"}[status]
        sleeve = result.get('discretionary_sleeve_pct') or 0.
        tiles = [('InvestorAce Buy portfolio', result['portfolio_return_pct']),
                 ('S&P 500', result['benchmark_return_pct']),
                 ('Excess vs S&P 500', result['excess_vs_benchmark_pct']),
                 ('Earnings-IV basket (control)', result['control_return_pct'])]
        if result.get('discretionary'):
            tiles += [('Your pick: ' + ', '.join(h['ticker'] for h in result['discretionary']),
                       result['discretionary_return_pct']),
                      (f'Combined {100 - sleeve:.0f}% model + {sleeve:.0f}% pick', result['combined_return_pct'])]
        if not result['control']:
            tiles = [t for t in tiles if not t[0].startswith('Earnings-IV')]
        money = lambda v: format(v, ',.0f')
        dollars = ''
        if result.get('capital_usd'):
            pnl = result.get('pnl_usd') or 0.
            dollars = ('<div class="tiles">'
                       f'<div class="tile"><span>Capital</span><b>${money(result["capital_usd"])}</b></div>'
                       f'<div class="tile"><span>Invested (whole shares)</span><b>${money(result["invested_usd"])}</b></div>'
                       f'<div class="tile"><span>Cash left</span><b>${money(result["cash_usd"])}</b></div>'
                       f'<div class="tile"><span>Value now</span><b>${money(result["value_usd"])}</b></div>'
                       f'<div class="tile"><span>Gain / loss</span><b class="{"up" if pnl > 0 else "down" if pnl < 0 else ""}">'
                       f'{"+" if pnl >= 0 else "−"}${money(abs(pnl))}</b></div></div>')
        body.append(f'<h2>{escape(doc["name"])}</h2><p><b>{escape(state)}</b> · exit at the close of '
                    f'{escape(doc["exit_date"])}</p><div class="tiles">'
                    + ''.join(f'<div class="tile"><span>{escape(name)}</span><b>{_pct(value)}</b></div>'
                              for name, value in tiles) + '</div>' + dollars)
        rule = str(doc.get('weight_rule') or '').strip().rstrip('.')
        rule = rule[len('Weight '):] if rule.lower().startswith('weight ') else rule
        selection = doc.get('selection_note') or ('every Buy label in the '
                    f'{str(doc.get("signal_snapshot_captured", ""))[:10]} snapshot')
        sizing = ''
        if doc.get('capital_usd'):
            fx = ', '.join(f'1 {k} = {v} USD' for k, v in (doc.get('fx_usd') or {}).items())
            sizing = (f' Sizing: ${money(doc["capital_usd"])} split by weight, whole shares at the entry close'
                      + (f' (fixed rate {escape(fx)} for sizing and dollar values only)' if fx else '')
                      + '; the rest stays cash.')
        body.append('<div class="note"><b>Rules.</b> Holdings: ' + escape(selection) + ' '
                    f'(model {escape(str(doc.get("model", "")))}, regime {escape(str(doc.get("regime", "")))}). '
                    f'Weights: {escape(rule)}. Entry: first close on or after {escape(doc["entry_date"])}; '
                    f'exit: last close on or before {escape(doc["exit_date"])}, each in its listing currency. '
                    'A missing or stale close is shown as not priced, never as 0%. '
                    + ('Control: the earnings-week implied-volatility list, equal weight. ' if result['control'] else '')
                    + 'Benchmark: S&P 500 price index.' + escape(sizing) + '</div>')
        rows = []
        for h in sorted(result['holdings'], key=lambda h: -h['weight_pct']):
            contribution = h['weight_pct'] * h['return_pct'] / 100 if h.get('return_pct') is not None else None
            have = h.get('shares') is not None
            rows.append(f'<tr><td><b>{escape(h["ticker"])}</b></td><td class="l">{label(h.get("label"), h.get("score"))}</td>'
                        f'<td>{h["weight_pct"]:.1f}%</td>'
                        + (f'<td><b>{h["shares"]:,}</b></td><td>${money(h["cost_usd"])}</td>' if have else '')
                        + f'<td>{_price(h, "signal_price")} {escape(h.get("currency", ""))}</td>'
                        f'<td>{_price(h, "entry_close")}</td><td>{_price(h, "exit_close")}</td>'
                        f'<td>{_pct(h.get("return_pct"))}</td><td>{_pct(contribution)}</td></tr>')
        sized = result.get('capital_usd') is not None
        body.append('<h2>Model holdings</h2><div class="tw"><table><thead><tr><th>Ticker</th><th class="l">Label</th>'
                    '<th>Weight</th>' + ('<th>Shares</th><th>Invested</th>' if sized else '')
                    + '<th>Signal price</th><th>Entry close</th><th>Latest close</th><th>Return</th>'
                    '<th>Contribution</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div>')
        if result.get('discretionary'):
            pick = doc.get('discretionary') or {}
            rows = ''.join(f'<tr><td><b>{escape(h["ticker"])}</b></td><td class="l">{label(h.get("label"), h.get("score"))}</td>'
                           + (f'<td><b>{h["shares"]:,}</b></td><td>${money(h["cost_usd"])}</td>' if h.get('shares') is not None else '')
                           + f'<td>{_price(h, "signal_price")}</td><td>{_price(h, "entry_close")}</td>'
                           f'<td>{_price(h, "exit_close")}</td><td>{_pct(h.get("return_pct"))}</td></tr>'
                           for h in result['discretionary'])
            body.append(f'<h2>{escape(result.get("discretionary_name") or "Your pick")} · {sleeve:.0f}% sleeve</h2>'
                        f'<p class="lead">{escape(pick.get("rationale", ""))}</p><div class="tw"><table><thead><tr>'
                        '<th>Ticker</th><th class="l">Model label</th>' + ('<th>Shares</th><th>Invested</th>' if sized else '')
                        + '<th>Signal price</th><th>Entry close</th>'
                        '<th>Latest close</th><th>Return</th></tr></thead><tbody>' + rows + '</tbody></table></div>')
        rows = ''.join(f'<tr><td><b>{escape(h["ticker"])}</b></td><td>{_pct(h.get("implied_move_pct"), css=False).replace("+", "±")}</td>'
                       f'<td class="l">{label(h.get("investorace_label"))}</td><td>{_price(h, "entry_close")}</td>'
                       f'<td>{_price(h, "exit_close")}</td><td>{_pct(h.get("return_pct"))}</td></tr>'
                       for h in sorted(result['control'], key=lambda h: h['ticker']))
        if result['control']:
            body.append('<h2>Control basket</h2><div class="tw"><table><thead><tr><th>Ticker</th><th>Implied move</th>'
                        '<th class="l">InvestorAce label</th><th>Entry close</th><th>Latest close</th><th>Return</th>'
                        '</tr></thead><tbody>' + rows + '</tbody></table></div>')
        missing = [h['ticker'] for h in result['holdings'] + result['control'] + result.get('discretionary', [])
                   if h['status'] == 'NO_PRICE']
        if missing:
            body.append('<div class="note">Not priced yet: ' + escape(', '.join(missing)) + '</div>')
    body.append('<div class="note">Paper money only. Research, not an approved purchase recommendation.</div>')
    return shell('Paper test', ''.join(body))


def site_pages(root, build, *, now=None):
    """paper-test.html from committed snapshots; empty when no portfolio exists."""
    now = now or datetime.now(timezone.utc)
    docs = load(Path(root) / 'paper_trades')
    if not docs:
        return []
    start = min(date.fromisoformat(d['entry_date']) for d in docs) - timedelta(days=7)
    snapshots = []
    for path in sorted((Path(root) / 'history' / 'runs').glob('*.json')):
        try:
            stamp = datetime.strptime(path.name[:8], '%Y%m%d').date()
        except ValueError:
            continue
        if stamp >= start:
            snapshots.append(json.loads(path.read_text(encoding='utf-8')))
    snapshots.append(build['record'])
    series = merge_series(snapshots)
    results = [evaluate(doc, series, now.date()) for doc in docs]
    return [(Path(PAGE), render(results, docs, now=now))]


def main(argv=None):
    import argparse
    import glob
    parser = argparse.ArgumentParser(description='Evaluate paper portfolios from committed snapshots.')
    parser.add_argument('--as-of', help='valuation date (YYYY-MM-DD); default: each exit date')
    args = parser.parse_args(argv)
    snapshots = [json.loads(Path(p).read_text(encoding='utf-8')) for p in sorted(glob.glob(str(ROOT / 'history/runs/*.json')))]
    series = merge_series(snapshots)
    for doc in load():
        as_of = date.fromisoformat(args.as_of) if args.as_of else None
        print(report(evaluate(doc, series, as_of)))
        print()


if __name__ == '__main__':
    main()
