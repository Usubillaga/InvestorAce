"""Paper portfolios that test the automatic InvestorAce labels out of sample.

A portfolio file in paper_trades/ freezes its holdings, weights, entry and
exit dates before the entry date. The nightly build records the recent
closes of every tracked symbol (macro.pulse.tracked), so the evaluation
reads entry and exit closes from committed snapshots and never from
hindsight. Nothing here changes a score, a label or the real portfolio.
"""
import json
from datetime import date, timedelta
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


def merge_series(snapshots):
    """{symbol: {date: close}} merged over several snapshots' pulse.tracked."""
    merged = {}
    for snapshot in snapshots:
        tracked = ((((snapshot or {}).get('_evidence') or {}).get('macro') or {}).get('pulse') or {}).get('tracked') or {}
        for symbol, rows in tracked.items():
            target = merged.setdefault(symbol, {})
            for when, value in rows:
                target[when] = value
    return {s: sorted(v.items()) for s, v in merged.items()}


def _leg(holdings, series, entry, exit_):
    rows, weight_used, total = [], 0., 0.
    for h in holdings:
        start = _close_on_or_before(series.get(h['yahoo']), entry)
        end = _close_on_or_before(series.get(h['yahoo']), exit_)
        stale = lambda close, day: close[0] < (date.fromisoformat(day) - timedelta(days=4)).isoformat()
        if not start or not end or stale(start, entry) or stale(end, exit_):
            rows.append(dict(h, status='NO_PRICE'))   # missing or stale close: never 0% by default
            continue
        change = 100 * (end[1] / start[1] - 1)
        rows.append(dict(h, entry_close=start[1], entry_close_date=start[0], exit_close=end[1],
                         exit_close_date=end[0], return_pct=change, status='PRICED'))
        weight_used += h['weight_pct']
        total += h['weight_pct'] * change
    return rows, (total / weight_used if weight_used else None), weight_used


def evaluate(doc, series, as_of=None):
    """Weighted returns of the holdings, the control basket and the benchmark."""
    exit_ = min(doc['exit_date'], (as_of or date.fromisoformat(doc['exit_date'])).isoformat())
    entry = doc['entry_date']
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
    return dict(name=doc['name'], entry_date=entry, valued_to=exit_, final=exit_ == doc['exit_date'],
                discretionary_name=pick.get('name'), discretionary=pick_rows,
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
    lines += ['', '| Ticker | Label | Weight | Entry | Exit | Return |', '|---|---|---|---|---|---|']
    ranked = lambda h: -h['return_pct'] if h.get('return_pct') is not None else float('inf')
    for h in sorted(result['holdings'], key=ranked):
        lines.append(f"| {h['ticker']} | {h['label']} {h['score']:.2f} | {h['weight_pct']:.1f}% | "
                     f"{h.get('entry_close', '—')} | {h.get('exit_close', '—')} | {pct(h.get('return_pct'))} |")
    missing = [h['ticker'] for h in result['holdings'] + result['control'] + result.get('discretionary', [])
               if h['status'] != 'PRICED']
    if missing:
        lines.append('\nNot priced: ' + ', '.join(missing))
    return '\n'.join(lines)


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
