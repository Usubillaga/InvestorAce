"""Index ETF timing rules, tested before either AI trades them (asked for on 22 Nov 2026). Research only.

Codex started a daily long/short paper account on five index ETFs (SPY, QQQ, DAX, DIA, IWM): long when the close
is above its 20-day average and above the close five sessions earlier, short when below both, flat otherwise.
It was started without a backtest. This study runs that rule and its alternatives on the same ETFs:

* codex_20d_5d_long_short: the rule above.
* codex_20d_5d_long_only: the same signal, flat instead of short.
* trend_200d: long above the 200-day average, flat below (Faber 2007, "A Quantitative Approach to Tactical Asset
  Allocation").
* buy_and_hold: the benchmark every rule is judged against.

Equal capital per ETF (one fifth each). The position decided at a close is held from the next close (the same one-
session delay as backtest.py; Codex fills at the next open, so this is slightly different). Costs 0.1% of each
change in position; shorts pay 2% a year borrow; cash earns nothing (a conservative assumption for the flat rules).
Stops are not modelled. Each rule is compared with buy and hold from 20 start dates, 5 sessions apart, in each of
the three periods, as in start_offsets.py; a rule passes only if its median difference in CAGR and Sharpe is
positive in every period.
"""
import math
import statistics

import numpy as np
import pandas as pd

ETFS = ('SPY', 'QQQ', 'DAX', 'DIA', 'IWM')
COST, BORROW = 0.001, 0.02
STARTS, STEP = 20, 5


def signals(close, rule):
    """Target position (-1, 0, 1) per date and ETF, known at that close."""
    sma20, sma200, back5 = close.rolling(20).mean(), close.rolling(200).mean(), close.shift(5)
    up = (close > sma20) & (close > back5)
    down = (close < sma20) & (close < back5)
    if rule == 'codex_20d_5d_long_short':
        pos = up.astype(float) - down.astype(float)
    elif rule == 'codex_20d_5d_long_only':
        pos = up.astype(float)
    elif rule == 'trend_200d':
        pos = (close > sma200).astype(float)
    elif rule == 'buy_and_hold':
        pos = pd.DataFrame(1., index=close.index, columns=close.columns)
    else:
        raise ValueError(rule)
    ready = sma200.notna() if rule == 'trend_200d' else sma20.notna() & back5.notna()
    return pos.where(ready)


def equity(close, rule, start, end=None):
    """Daily equity of the equal-weight book from start (inclusive) to end (exclusive), starting at 1."""
    rets = close.pct_change()
    held = signals(close, rule).shift(1)          # decided at close t, held over t+1
    mask = (close.index >= start) & ((close.index < end) if end is not None else True)
    rets, held = rets[mask], held[mask]
    live = held.notna() & rets.notna()
    held = held.where(live, 0.)
    turnover = held.diff().abs()
    turnover.iloc[0] = held.iloc[0].abs()
    daily = held * rets.fillna(0.) - turnover * COST - held.clip(upper=0).abs() * BORROW / 252
    weights = live.astype(float)
    n = weights.sum(axis=1).replace(0, np.nan)
    book = (daily * weights).sum(axis=1) / n
    return (1 + book.fillna(0.)).cumprod()


def metrics(curve):
    rets = curve.pct_change().dropna()
    years = max((curve.index[-1] - curve.index[0]).days / 365.25, 1e-9)
    return dict(cagr=100 * (curve.iloc[-1] ** (1 / years) - 1),
                sharpe=float(rets.mean() / rets.std() * math.sqrt(252)) if rets.std() > 0 else None,
                max_drawdown=100 * float((curve / curve.cummax() - 1).min()))


def study(close, windows, starts=STARTS, step=STEP):
    rules = ('codex_20d_5d_long_short', 'codex_20d_5d_long_only', 'trend_200d')
    out = {}
    for lo, hi in windows:
        start, end = pd.Timestamp(lo), (pd.Timestamp(hi) if hi else None)
        days = close.index[(close.index >= start) & ((close.index < end) if end is not None else True)]
        if len(days) < 250 + (starts - 1) * step:
            continue
        label = f'{days[0].date()} → {days[-1].date()}'
        rows = {}
        for rule in rules:
            diffs = {m: [] for m in ('cagr', 'sharpe', 'max_drawdown')}
            wins = 0
            absolute = []
            for k in range(starts):
                first = days[k * step]
                base, var = metrics(equity(close, 'buy_and_hold', first, end)), metrics(equity(close, rule, first, end))
                absolute.append(var)
                wins += var['cagr'] > base['cagr']
                for m in diffs:
                    if None not in (var[m], base[m]):
                        diffs[m].append(var[m] - base[m])
            rows[rule] = dict(wins=wins, starts=starts,
                              cagr=statistics.median(a['cagr'] for a in absolute),
                              **{f'd_{m}': dict(median=statistics.median(v), min=min(v), max=max(v))
                                 for m, v in diffs.items() if v})
        rows['buy_and_hold'] = dict(cagr=metrics(equity(close, 'buy_and_hold', days[0], end))['cagr'])
        out[label] = rows
    for rule in ('codex_20d_5d_long_short', 'codex_20d_5d_long_only', 'trend_200d'):
        cells = [r[rule] for r in out.values() if rule in r]
        out.setdefault('_passes', {})[rule] = bool(cells) and len(cells) == len(windows) and all(
            c['d_cagr']['median'] > 0 and c['d_sharpe']['median'] > 0 for c in cells)
    return out


def report(result):
    lines = ['', '## Index ETF timing (SPY, QQQ, DAX, DIA, IWM; equal weight)', '',
             'Rules against buy and hold from 20 paired starts per period. Costs 0.1% per position change, 2% a year '
             'borrow on shorts, cash earns nothing, no stops. Passes only with a positive median ΔCAGR and ΔSharpe in '
             'every period.', '',
             '| Period | Rule | Beats buy & hold | Median CAGR | ΔCAGR median [min, max] | ΔSharpe median | ΔMax DD median |',
             '|---|---|---|---:|---|---:|---:|']
    for period, rows in result.items():
        if period.startswith('_'):
            continue
        lines.append(f"| {period} | buy_and_hold | — | {rows['buy_and_hold']['cagr']:.2f}% | — | — | — |")
        for rule, r in rows.items():
            if rule == 'buy_and_hold':
                continue
            d = r['d_cagr']
            lines.append(f"| {period} | {rule} | {r['wins']}/{r['starts']} | {r['cagr']:.2f}% | "
                         f"{d['median']:+.2f} [{d['min']:+.2f}, {d['max']:+.2f}] | {r['d_sharpe']['median']:+.2f} | "
                         f"{r['d_max_drawdown']['median']:+.2f} |")
    lines += ['', 'Passes: ' + ', '.join(f"{k} {'yes' if v else 'no'}" for k, v in result.get('_passes', {}).items()), '']
    return '\n'.join(lines) + '\n'


def download(period='14y'):
    import yfinance as yf
    raw = yf.download(list(ETFS), period=period, auto_adjust=True, progress=False, threads=False, group_by='column')
    close = raw['Close'][list(ETFS)].round(4)
    close.index = close.index.tz_localize(None) if close.index.tz is not None else close.index
    return close
