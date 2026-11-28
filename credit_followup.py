"""Credit stress follow-up to the panic study (asked for on 28 Nov 2026).

The panic study found only two buys with wide credit spreads (both 2008), too few to judge two ideas:
  1. "hold longer": with wide spreads a panic buy needs more time; test how returns and the time to recover the
     entry price change with the holding period, by credit group;
  2. "buy in tranches": with wide spreads, buy in thirds instead of all at once.

To get more episodes this uses the S&P 500 index alone (price index, no dividends) since 1989 and every first
close at a drawdown of 15% or 20% from the 252-session high (a new episode only after the index recovered to within
5% of its high), grouped by the Moody's Baa minus 10-year spread (FRED BAA10Y) against its 3-year mean on that day,
with the panic study's bands. Plans, each a whole account (cash earns nothing):
  lump       all at the signal close;
  time3      thirds at the signal close and 21 and 42 sessions later;
  dip3       thirds at the signal close, at the first close 10% and 20% below it; a third still unbought after
             126 sessions is bought then;
  dip3_cash  as dip3, but an unbought third stays in cash.
Research only; it does not change any rule (the user's rule needs three periods and the 20-start test).
"""
import json
import statistics
from pathlib import Path

import pandas as pd

import panic_history as ph

ROOT = Path(__file__).resolve().parent
OUT_JSON = ROOT / 'backtests' / 'credit_followup.json'
OUT_MD = ROOT / 'backtests' / 'credit_followup.md'
DEPTHS = (0.15, 0.20)
RESET = 0.05
HORIZONS = (252, 504, 882)
PLANS = ('lump', 'time3', 'dip3', 'dip3_cash')
FALLBACK = 126
START = '1989-01-01'


def drawdown(spx):
    return spx / spx.rolling(252, min_periods=1).max() - 1


def episodes(spx, depth, start=START, reset=RESET):
    """First close of each episode at or below -depth from the 252-session high."""
    dd = drawdown(spx)
    out, armed = [], True
    for day, x in dd.items():
        if x > -reset:
            armed = True
        elif armed and x <= -depth and day >= pd.Timestamp(start):
            out.append(day)
            armed = False
    return out


def buy_days(spx, i, plan):
    """Session positions of the three thirds (None: stays in cash)."""
    if plan == 'lump':
        return [i, i, i]
    if plan == 'time3':
        return [i, min(i + 21, len(spx) - 1), min(i + 42, len(spx) - 1)]
    entry, days = spx.iloc[i], [i]
    for cut in (0.10, 0.20):
        hit = next((j for j in range(i + 1, min(i + FALLBACK, len(spx) - 1) + 1) if spx.iloc[j] <= entry * (1 - cut)), None)
        if hit is None:
            hit = None if plan == 'dip3_cash' else min(i + FALLBACK, len(spx) - 1)
        days.append(hit)
    return days


def account(spx, i, plan, h):
    """(return, max drawdown) of a one-unit account over h sessions from the signal, or None past the data."""
    if i + h >= len(spx):
        return None
    days = buy_days(spx, i, plan)
    path = []
    for k in range(i, i + h + 1):
        value = sum((spx.iloc[k] / spx.iloc[d] if d is not None and d <= k else 1.) for d in days) / 3
        path.append(value)
    peak, worst = path[0], 0.
    for v in path:
        peak = max(peak, v)
        worst = min(worst, v / peak - 1)
    return dict(ret=path[-1] - 1, drawdown=worst)


def recovery(spx, i, cap=1260):
    """Sessions until the index closes at or above the signal close again (None: not within cap or the data)."""
    entry = spx.iloc[i]
    for k in range(i + 1, min(i + cap, len(spx) - 1) + 1):
        if spx.iloc[k] >= entry:
            return k - i
    return None


def band(x):
    return next((name for name, test in ph.CREDIT_BANDS if test(x)), None) if x == x else None


def study(spx, credit):
    spx = spx.dropna()
    ex = ph.excess(credit, spx.index)
    result = {}
    for depth in DEPTHS:
        rows = []
        for day in episodes(spx, depth):
            i = spx.index.get_loc(day)
            c = ex.get(day)
            row = dict(date=str(day.date()), spread_excess=None if c is None or c != c else round(float(c), 2),
                       band=band(c) if c is not None else None, recovery=recovery(spx, i),
                       plans={p: {str(h): account(spx, i, p, h) for h in HORIZONS} for p in PLANS})
            rows.append(row)
        groups = {}
        for name, _ in ph.CREDIT_BANDS:
            sel = [r for r in rows if r['band'] == name]
            groups[name] = dict(n=len(sel), dates=[r['date'] for r in sel], plans={
                p: {str(h): summarize([r['plans'][p][str(h)] for r in sel]) for h in HORIZONS} for p in PLANS},
                recovery=[r['recovery'] for r in sel])
        result[f'{int(depth * 100)}'] = dict(rows=rows, groups=groups)
    days = all_days(spx, ex)
    return dict(schema='credit-followup-v1', start=START, end=str(spx.index[-1].date()), depths=result, all_days=days)


def summarize(xs):
    xs = [x for x in xs if x]
    if not xs:
        return dict(n=0)
    r = [x['ret'] for x in xs]
    return dict(n=len(xs), mean=statistics.fmean(r), median=statistics.median(r), worst=min(r),
                positive=sum(v > 0 for v in r), drawdown=statistics.fmean(x['drawdown'] for x in xs),
                worst_drawdown=min(x['drawdown'] for x in xs))


def all_days(spx, ex):
    """Every session since START: forward S&P returns by credit band, with the number of separate wide episodes."""
    out = {}
    idx = spx.index
    for h in HORIZONS:
        fwd = spx.shift(-h) / spx - 1
        cells = {}
        for name, test in ph.CREDIT_BANDS:
            mask = ex.apply(lambda v: v == v and test(v)) & (idx >= pd.Timestamp(START)) & fwd.notna()
            vals = fwd[mask]
            cells[name] = dict(days=int(mask.sum()), mean=float(vals.mean()) if len(vals) else None,
                               positive=float((vals > 0).mean()) if len(vals) else None)
        out[str(h)] = cells
    wide = ex.apply(lambda v: v == v and v > 1.0) & (idx >= pd.Timestamp(START))
    runs, last = [], None
    for k, (day, w) in enumerate(wide.items()):
        if w:
            if last is None or k - last > 63:
                runs.append([str(day.date()), str(day.date())])
            runs[-1][1] = str(day.date())
            last = k
    out['wide_episodes'] = runs
    return out


def now_and_analogs(spx, vix, credit, move=None):
    """Today's reading and the past sessions that looked like it: S&P drawdown within 5 pp and credit spread excess
    within 0.5 pp of today's, with forward S&P returns and the separate episodes (gaps over 63 sessions)."""
    spx = spx.dropna()
    ex, dd = ph.excess(credit, spx.index), drawdown(spx)
    day = spx.index[-1]
    lvl = credit.reindex(spx.index).ffill()
    now = dict(date=str(day.date()), spx=round(float(spx.iloc[-1]), 2), drawdown=round(float(dd.iloc[-1]), 4),
               vix=None if vix is None or not len(vix) else round(float(vix.dropna().iloc[-1]), 2),
               credit=round(float(lvl.iloc[-1]), 2), credit_excess=round(float(ex.iloc[-1]), 2), band=band(ex.iloc[-1]),
               credit_mean_3y=round(float(lvl.iloc[-1] - ex.iloc[-1]), 2))
    if move is not None and len(move):
        mx = ph.excess(move, spx.index)
        now['move'] = round(float(move.dropna().iloc[-1]), 1)
        now['move_excess'] = round(float(mx.iloc[-1]), 1)
    like = (dd - dd.iloc[-1]).abs().le(0.05) & (ex - ex.iloc[-1]).abs().le(0.5) & (spx.index >= pd.Timestamp(START))
    like.iloc[-63:] = False
    out = {}
    for h in HORIZONS:
        fwd = (spx.shift(-h) / spx - 1)[like].dropna()
        out[str(h)] = dict(days=len(fwd), mean=float(fwd.mean()) if len(fwd) else None,
                           positive=float((fwd > 0).mean()) if len(fwd) else None,
                           worst=float(fwd.min()) if len(fwd) else None)
    runs, last = [], None
    for k, (d, w) in enumerate(like.items()):
        if w:
            if last is None or k - last > 63:
                runs.append([str(d.date()), str(d.date())])
            runs[-1][1] = str(d.date())
            last = k
    return dict(now=now, analogs=out, analog_episodes=runs)


def _p(x):
    return '—' if x is None else f'{100 * x:+.1f}%'


def _share(x):
    return '—' if x is None else f'{100 * x:.0f}%'


def report(r):
    lines = ['# Credit stress follow-up: hold longer, buy in tranches', '',
             f"S&P 500 price index {r['start'][:4]}–{r['end']}; Moody's Baa minus 10-year (FRED BAA10Y) against its 3-year "
             'mean on the signal day. Signals: first close at -15% / -20% from the 252-session high (new episode after '
             'recovering to -5%). Plans: lump (all at once); time3 (thirds at 0, +21, +42 sessions); dip3 (thirds at '
             '0, -10%, -20% below the first buy, the rest after 126 sessions); dip3_cash (the rest stays in cash). '
             'No dividends, no costs. Research only.', '']
    for depth, block in r['depths'].items():
        lines += [f'## Drawdown of {depth}%', '',
                  '| Credit | n | Plan | 12 m mean / worst | 24 m mean / worst | 42 m mean / worst / positive | '
                  'Avg max drawdown (42 m) |', '|---|---:|---|---|---|---|---:|']
        for name, g in block['groups'].items():
            for p in PLANS:
                c = g['plans'][p]
                a, b, l = c['252'], c['504'], c['882']
                if not a.get('n'):
                    continue
                lines.append(f"| {name} | {g['n']} | {p} | {_p(a['mean'])} / {_p(a['worst'])} | "
                             f"{_p(b.get('mean'))} / {_p(b.get('worst'))} | {_p(l.get('mean'))} / {_p(l.get('worst'))} / "
                             f"{l.get('positive', '—')}/{l.get('n', 0)} | {_p(l.get('drawdown'))} |")
        lines += ['', 'Signals (spread vs 3-year mean, sessions to recover the signal close):', '']
        lines += ['; '.join(f"{x['date']} {x['spread_excess'] if x['spread_excess'] is not None else '—'} pp, "
                            f"{x['recovery'] if x['recovery'] is not None else '>1260/open'}" for x in block['rows']), '']
    a = r['all_days']
    lines += ['## Every session: forward S&P return by credit band', '',
              '| Credit | Days | 12 m mean / positive | 24 m mean / positive | 42 m mean / positive |',
              '|---|---:|---|---|---|']
    for name, _ in ph.CREDIT_BANDS:
        c = [a[str(h)][name] for h in HORIZONS]
        lines.append(f"| {name} | {c[0]['days']} | " + ' | '.join(
            f"{_p(x['mean'])} / {_share(x['positive'])}" for x in c) + ' |')
    lines += ['', 'Separate wide-spread episodes (> +1.0 pp): ' + '; '.join(f'{s} to {e}' for s, e in a['wide_episodes'])]
    if r.get('today'):
        t, n = r['today'], r['today']['now']
        lines += ['', f"## Today ({n['date']}) and the past sessions that looked like it", '',
                  f"S&P 500 {n['spx']} ({_p(n['drawdown'])} from its 252-session high); VIX {n['vix']}; "
                  f"Baa minus 10-year {n['credit']} pp vs 3-year mean {n['credit_mean_3y']} ({n['credit_excess']:+.2f} pp, "
                  f"{n['band']})" + (f"; MOVE {n['move']} ({n['move_excess']:+.1f} vs 3-year mean)" if 'move' in n else '') + '.',
                  '', 'Sessions since 1989 with the drawdown within 5 pp and the spread excess within 0.5 pp of today:', '',
                  '| Horizon | Sessions | Mean | Positive | Worst |', '|---|---:|---:|---:|---:|']
        for h in HORIZONS:
            c = t['analogs'][str(h)]
            lines.append(f"| {h} | {c['days']} | {_p(c['mean'])} | {_share(c['positive'])} | {_p(c['worst'])} |")
        lines += ['', 'Episodes: ' + '; '.join(f'{s} to {e}' for s, e in t['analog_episodes'])]
    return '\n'.join(lines) + '\n'


def main():
    spx, vix = ph.index_series()
    credit = ph.credit_series()
    if credit is None:
        raise SystemExit('credit spreads unavailable: ' + '; '.join(ph.CREDIT_LOG))
    result = study(spx, credit[1])
    result['credit_series'] = credit[0]
    try:
        move = ph.move_series()
    except Exception:
        move = None
    result['today'] = now_and_analogs(spx, vix, credit[1], move)
    OUT_JSON.parent.mkdir(exist_ok=True)
    OUT_JSON.write_text(json.dumps(result, indent=1, allow_nan=False) + '\n', encoding='utf-8')
    OUT_MD.write_text(report(result), encoding='utf-8')
    print(report(result))


if __name__ == '__main__':
    main()
