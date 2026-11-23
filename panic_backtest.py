"""The market thermometer's "Panic · buy" signal, and buying the leaders when it fires (asked for on 23 Nov 2026).

On Friday 20 Nov 2026 the thermometer (market_pulse.py) read 15.4: VIX 35.89 (score 13.7), S&P 500 5.96% under
its 200-day average (20.2) and 9.37% under its 50-day (0.0), 27.6% of the universe above its own 200-day (27.6).
Under 20 the band is Panic, which the page labels "buy". CNN's Fear & Greed was not available that day, so the
thermometer is the mean of those four scores, each rebuilt here exactly as market_pulse.summarize scores it.

Signals:
* panic_entry: the first close under 20 after at least GAP sessions without one (one signal per panic episode).
* panic_exit: the first close back at or above 20 after such an episode (waits for confirmation).

At each signal, bought at the next close and held 21/63/126/252 sessions:
* leader: the universe stock with the highest 21-day / 200-day average ratio (v1.6's ranking) on the signal day.
* top5: the five highest, equal weight.
* universe: every stock with a price, equal weight.
* spx: the S&P 500.
Costs 0.1% per side. Caveats: today's universe (survivorship flatters every stock basket, the leader most of all,
since a leader that later collapsed may be gone); signals overlap in time across horizons; few episodes. The test
compares the leader with the S&P 500 and the universe on the same dates. Research only; nothing is traded.
"""
import statistics

import numpy as np
import pandas as pd

PANIC = 20.
GAP = 63
HORIZONS = (21, 63, 126, 252)
COST = 0.001


def _clip(x):
    return x.clip(lower=0, upper=100)


def heat(spx, vix, close):
    """Daily thermometer from closes: the mean of the four market_pulse scores (no Fear & Greed)."""
    ma200, ma50 = spx.rolling(200).mean(), spx.rolling(50).mean()
    s200 = _clip(50 + 5 * 100 * (spx / ma200 - 1))
    s50 = _clip(50 + 10 * 100 * (spx / ma50 - 1))
    svix = _clip((40 - vix.reindex(spx.index).ffill()) / 30 * 100)
    sma = close.rolling(200).mean()
    valid = sma.notna() & close.notna()
    share = 100 * ((close > sma) & valid).sum(axis=1) / valid.sum(axis=1).where(valid.sum(axis=1) >= 20)
    frame = pd.concat([s200, s50, svix, share.reindex(spx.index)], axis=1)
    return frame.mean(axis=1).where(frame.notna().sum(axis=1) >= 3)   # as live: a mean of at least 3 scores


def signals(h, panic=PANIC, gap=GAP):
    """(entries, exits): dates of the first panic close per episode and of the first close back above."""
    entries, exits, last_panic, open_episode = [], [], None, False
    for i, (day, v) in enumerate(h.items()):
        if np.isnan(v):
            continue
        if v < panic:
            if last_panic is None or i - last_panic > gap:
                entries.append(day)
                open_episode = True
            last_panic = i
        elif open_episode:
            exits.append(day)
            open_episode = False
    return entries, exits


def _ret(series, i, h):
    if i + h >= len(series):
        return None
    a, b = series.iloc[i], series.iloc[i + h]
    if not (np.isfinite(a) and np.isfinite(b)) or a <= 0:
        return None
    return float(b / a * (1 - COST) / (1 + COST) - 1)


def outcomes(day, close, mad, spx, horizons=HORIZONS):
    """Returns after buying at the close after `day`."""
    pos = close.index.get_loc(day)
    if pos + 1 >= len(close.index):
        return None
    ranked = mad.loc[day].dropna().sort_values(ascending=False)
    if ranked.empty:
        return None
    leader, top5 = ranked.index[0], list(ranked.index[:5])
    out = dict(date=str(day.date()), leader=leader, top5=top5, returns={})
    i = pos + 1
    spx_i = spx.index.get_loc(close.index[i])
    for h in horizons:
        r = dict(leader=_ret(close[leader], i, h),
                 top5=_mean([_ret(close[s], i, h) for s in top5]),
                 universe=_mean([_ret(close[s], i, h) for s in close.columns]),
                 spx=_ret(spx, spx_i, h))
        out['returns'][str(h)] = r
    return out


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return float(np.mean(xs)) if xs else None


def summary(events, horizons=HORIZONS):
    out = {}
    for h in horizons:
        rows = [e['returns'][str(h)] for e in events if e and all(e['returns'][str(h)][k] is not None
                                                                   for k in ('leader', 'top5', 'universe', 'spx'))]
        if not rows:
            out[str(h)] = dict(n=0)
            continue
        cell = dict(n=len(rows))
        for k in ('leader', 'top5', 'universe', 'spx'):
            xs = [r[k] for r in rows]
            cell[k] = dict(mean=statistics.fmean(xs), median=statistics.median(xs),
                           positive=sum(x > 0 for x in xs), worst=min(xs))
        cell['leader_beats_spx'] = sum(r['leader'] > r['spx'] for r in rows)
        cell['top5_beats_spx'] = sum(r['top5'] > r['spx'] for r in rows)
        out[str(h)] = cell
    return out


def study(frames, spx, vix):
    close = pd.DataFrame({s: f['close'] for s, f in frames.items()}).reindex(spx.index)
    mad = pd.DataFrame({s: f['mad'] for s, f in frames.items()}).reindex(spx.index)
    h = heat(spx, vix, close)
    entries, exits = signals(h)
    result = dict(last_heat=dict(date=str(h.dropna().index[-1].date()), value=round(float(h.dropna().iloc[-1]), 1))
                  if h.notna().any() else None)
    for name, days in (('panic_entry', entries), ('panic_exit', exits)):
        events = [e for e in (outcomes(d, close, mad, spx) for d in days) if e]
        for e in events:
            e['heat'] = round(float(h.loc[pd.Timestamp(e['date'])]), 1)
        result[name] = dict(events=events, summary=summary(events))
    return result


def _pct(x):
    return '—' if x is None else f'{100 * x:+.1f}%'


def report(result):
    lines = ['', '## Thermometer "Panic · buy": buy the leader', '',
             f'Signal: the thermometer (market_pulse.py, rebuilt without Fear & Greed) closes under {PANIC:g}; one '
             f'signal per episode ({GAP} sessions apart). Bought at the next close; 0.1% per side. Leader: highest '
             '21/200-day average ratio in the universe on the signal day; top5: the five highest. Today\'s universe, '
             'so stock baskets are flattered by survivorship.', '']
    if result.get('last_heat'):
        lines.append(f"Rebuilt thermometer on {result['last_heat']['date']}: {result['last_heat']['value']}.")
    for name, title in (('panic_entry', 'First panic close'), ('panic_exit', 'First close back above 20')):
        block = result.get(name) or {}
        lines += ['', f'### {title}', '',
                  '| Sessions | Signals | Leader mean / median | Top 5 mean / median | Universe mean | S&P 500 mean / median | '
                  'Leader beats S&P | Leader worst |', '|---:|---:|---|---|---:|---|---:|---:|']
        for h, c in (block.get('summary') or {}).items():
            if not c.get('n'):
                lines.append(f'| {h} | 0 | — | — | — | — | — | — |')
                continue
            lines.append(f"| {h} | {c['n']} | {_pct(c['leader']['mean'])} / {_pct(c['leader']['median'])} | "
                         f"{_pct(c['top5']['mean'])} / {_pct(c['top5']['median'])} | {_pct(c['universe']['mean'])} | "
                         f"{_pct(c['spx']['mean'])} / {_pct(c['spx']['median'])} | {c['leader_beats_spx']}/{c['n']} | "
                         f"{_pct(c['leader']['worst'])} |")
        lines += ['', 'Signals: ' + '; '.join(
            f"{e['date']} (heat {e['heat']}, leader {e['leader']}: 63 sessions {_pct(e['returns']['63']['leader'])}, "
            f"S&P {_pct(e['returns']['63']['spx'])})" for e in block.get('events', []))]
    return '\n'.join(lines) + '\n'


def download_vix(period):
    import yfinance as yf
    raw = yf.download(['^VIX'], period=period, auto_adjust=False, progress=False, threads=False, group_by='column')
    s = raw['Close']['^VIX'].dropna().round(4)
    s.index = s.index.tz_localize(None) if s.index.tz is not None else s.index
    return s
