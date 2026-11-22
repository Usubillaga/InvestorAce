"""Start-date sensitivity of the backtest variants (asked for on 22 Nov 2026).

One different trade can move a four-year result by several points of CAGR: the 1% SMA200 buffer skipped a single
Barrick entry in October 2018 and the two books never met again (+66 total-return points by 2021, 63% of it from
two later positions). A variant is therefore also run from 20 staggered start dates per main period, five trading
sessions apart, each paired with v1.6 started on the same date with the same capital and ending on the same day.
Start 0 is the original start.

Reported per variant and period: wins, ties (identical ending equity) and losses against v1.6, and the median,
minimum and maximum of the paired differences in CAGR, maximum drawdown and Sharpe. The 20 runs overlap almost
entirely, so a win count describes start-date sensitivity; it is not a probability of future outperformance.
"""
import statistics

STARTS, STEP = 20, 5
METRICS = ('cagr', 'max_drawdown', 'sharpe')


def _diff(a, b):
    return None if a is None or b is None else a - b


def summarise(pairs):
    """pairs: [(base result, variant result)] for one variant and period."""
    wins = ties = losses = 0
    diffs = {m: [] for m in METRICS}
    for base, var in pairs:
        gap = var['final'] - base['final']
        if gap == 0:
            ties += 1
        elif gap > 0:
            wins += 1
        else:
            losses += 1
        for m in METRICS:
            d = _diff(var.get(m), base.get(m))
            if d is not None:
                diffs[m].append(d)
    out = dict(starts=len(pairs), wins=wins, ties=ties, losses=losses,
               original=dict((m, _diff(pairs[0][1].get(m), pairs[0][0].get(m))) for m in METRICS) if pairs else None)
    for m, values in diffs.items():
        out[m] = (dict(median=round(statistics.median(values), 2), min=round(min(values), 2), max=round(max(values), 2))
                  if values else None)
    return out


def study(simulate, frames, spx, sectors, prepared, windows, variants, base, starts=STARTS, step=STEP):
    """{period: {variant: summary}} with v1.6 and each variant paired on the same start and end dates."""
    import pandas as pd
    if starts < 1 or step < 1:
        raise ValueError('starts and step must be positive')
    out = {}
    for lo, hi in windows:
        start = pd.Timestamp(lo)
        end = pd.Timestamp(hi) if hi else None
        days = spx.index[(spx.index >= start) & ((spx.index < end) if end is not None else True)]
        if len(days) < 250 + (starts - 1) * step:
            continue
        label = f'{days[0].date()} → {days[-1].date()}'
        runs = {}
        for k in range(starts):
            first = days[k * step]
            runs[k] = {name: simulate(frames, spx, sectors, first, end, prepared, precise=True, **rule)
                       for name, rule in variants.items()}
        out[label] = {name: summarise([(runs[k][base], runs[k][name]) for k in range(starts)])
                      for name in variants if name != base}
        for name, row in out[label].items():
            row['observations'] = [
                dict(start=str(days[k * step].date()), end=str(days[-1].date()),
                     equity_delta=runs[k][name]['final'] - runs[k][base]['final'],
                     **{m: _diff(runs[k][name][m], runs[k][base][m]) for m in METRICS})
                for k in range(starts)]
    return out


def report(result):
    lines = ['', '## Start-date sensitivity (paired with v1.6)', '',
             'Each row compares a variant with v1.6 started on the same day with the same capital. Wins / ties / losses '
             'count ending equity; Δ columns show median [min, max] of the paired differences. The starts overlap, so the '
             'counts describe sensitivity to the start date, not a probability of future outperformance.', '']
    for period, rows in result.items():
        first = next(iter(rows.values()), {})
        precision = ('Counts use unrounded ending equity.' if 'observations' in first else
                     'Archived run: wins and ties use ending equity rounded to whole currency units.')
        lines += [f'### {period}', '', f"{first.get('starts', 0)} paired starts. {precision}", '',  '| Variant | W / T / L | Original start ΔCAGR | ΔCAGR | ΔMax DD | ΔSharpe |',
                  '|---|---|---:|---|---|---|']
        for name, r in rows.items():
            def cell(m):
                v = r.get(m)
                return '—' if not v else f"{v['median']:+.2f} [{v['min']:+.2f}, {v['max']:+.2f}]"
            orig = (r.get('original') or {}).get('cagr')
            lines.append(f"| {name} | {r['wins']} / {r['ties']} / {r['losses']} | "
                         f"{'—' if orig is None else format(orig, '+.2f')} | {cell('cagr')} | {cell('max_drawdown')} | "
                         f"{cell('sharpe')} |")
        lines.append('')
    return '\n'.join(lines) + '\n'
