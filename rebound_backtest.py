"""Buy the oversold dip to sell the rebound (asked for on 23 Nov 2026, after NVDA's +28% on the CEO news).

The user's rule: after three red closes in a row with the stock stretched far below its 21-day EMA, buy to sell
the bounce. NVDA on 20 Nov 2026 closed at 125.53, 4.7 ATR under its EMA21 and 38% under its SMA200, after the same
signal had already fired on 18 Nov (-3.4 ATR) and 19 Nov (-3.5 ATR).

Rule tested (one open trade per stock; a new signal only after the previous trade closed):
* Signal at close t: close[t] < close[t-1] < close[t-2] < close[t-3] (three red closes) and
  (close - EMA21) / ATR14 <= -OVERSOLD.
* Entry: at the signal close (a market-on-close order placed minutes before the close; slightly optimistic).
* Exit, "sell the rebound": the first close above the 10-day EMA, or after MAX_HOLD sessions.
* Stop: a close 8% under the entry (the swing rules' stop), or none in the *_no_stop variants.
* Costs: 0.1% per side.

Variants split the signal by trend: all, above SMA200 (Connors' short-term mean reversion only buys above it) and
below SMA200 (NVDA's case). Each trade is compared with the S&P 500 over the same sessions. A variant passes only
with at least MIN_TRADES trades and a positive mean and median excess return in every period. Universe and
survivorship caveats as in backtest.py: today's members, so the absolute returns are flattered; the excess over
the S&P 500 and the comparison between variants are what count. Research only; no rule changes.
"""
import math
import statistics

import numpy as np

OVERSOLD = 3.0
MAX_HOLD = 10
STOP = 0.08
COST = 0.001
MIN_TRADES = 30
VARIANTS = {
    'all': dict(trend=None, stop=True),
    'above_sma200': dict(trend='above', stop=True),
    'below_sma200': dict(trend='below', stop=True),
    'all_no_stop': dict(trend=None, stop=False),
    'below_sma200_no_stop': dict(trend='below', stop=False),
}


def trades(frame, spx, start, end=None, trend=None, stop=True, oversold=OVERSOLD, max_hold=MAX_HOLD):
    """Trades of one stock. frame has close, ema10, sma200, ext_atr (backtest.indicators); spx is aligned."""
    close = frame['close'].to_numpy(float)
    ema10 = frame['ema10'].to_numpy(float)
    sma200 = frame['sma200'].to_numpy(float)
    ext = frame['ext_atr'].to_numpy(float)
    index = frame.index
    bench = spx.reindex(index).ffill().to_numpy(float)
    live = (index >= start) & ((index < end) if end is not None else True)
    out, i, n = [], 3, len(close)
    while i < n:
        if not live[i] or np.isnan(ext[i]) or np.isnan(close[i - 3]):
            i += 1
            continue
        red = close[i] < close[i - 1] < close[i - 2] < close[i - 3]
        below = not np.isnan(sma200[i]) and close[i] < sma200[i]
        above = not np.isnan(sma200[i]) and close[i] > sma200[i]
        wanted = trend is None or (trend == 'below' and below) or (trend == 'above' and above)
        if not (red and ext[i] <= -oversold and wanted):
            i += 1
            continue
        entry, exit_at, reason = close[i], None, 'time'
        last = min(i + max_hold, n - 1)
        if last == i:
            break                                         # no session left to exit
        for j in range(i + 1, last + 1):
            if np.isnan(close[j]):
                continue
            if stop and close[j] <= entry * (1 - STOP):
                exit_at, reason = j, 'stop'
                break
            if not np.isnan(ema10[j]) and close[j] > ema10[j]:
                exit_at, reason = j, 'rebound'
                break
        if exit_at is None:
            exit_at, reason = last, ('time' if last == i + max_hold else 'open')
        ret = close[exit_at] / entry * (1 - COST) / (1 + COST) - 1
        spx_ret = bench[exit_at] / bench[i] - 1 if bench[i] and not np.isnan(bench[exit_at]) else 0.
        out.append(dict(date=str(index[i].date()), entry=float(entry), exit=str(index[exit_at].date()),
                        sessions=int(exit_at - i), ret=float(ret), excess=float(ret - spx_ret), reason=reason,
                        ext_atr=float(ext[i]), below_sma200=bool(below)))
        i = exit_at + 1
    return out


def summary(rows):
    rows = [r for r in rows if r['reason'] != 'open']     # trades still open at the end of the data
    if not rows:
        return dict(trades=0)
    rets = [r['ret'] for r in rows]
    exc = [r['excess'] for r in rows]
    srt = sorted(rets)
    return dict(trades=len(rows), win_rate=sum(r > 0 for r in rets) / len(rets),
                mean=statistics.fmean(rets), median=statistics.median(rets),
                mean_excess=statistics.fmean(exc), median_excess=statistics.median(exc),
                worst=srt[0], p05=srt[max(0, math.ceil(0.05 * len(srt)) - 1)], best=srt[-1],
                sessions=statistics.fmean(r['sessions'] for r in rows),
                stops=sum(r['reason'] == 'stop' for r in rows) / len(rows))


def study(frames, spx, windows):
    import pandas as pd
    out = {}
    for lo, hi in windows:
        start, end = pd.Timestamp(lo), (pd.Timestamp(hi) if hi else None)
        days = spx.index[(spx.index >= start) & ((spx.index < end) if end is not None else True)]
        if len(days) < 250:
            continue
        label = f'{days[0].date()} → {days[-1].date()}'
        out[label] = {name: summary([t for f in frames.values() for t in trades(f, spx, start, end, **kw)])
                      for name, kw in VARIANTS.items()}
    periods = [v for k, v in out.items() if not k.startswith('_')]
    out['_passes'] = {name: len(periods) == len(windows) and all(
        p[name]['trades'] >= MIN_TRADES and p[name]['mean_excess'] > 0 and p[name]['median_excess'] > 0
        for p in periods) for name in VARIANTS}
    if 'NVDA' in frames:
        recent = pd.Timestamp('2026-11-01')
        out['_nvda_nov_2026'] = [t for t in trades(frames['NVDA'], spx, recent, None, stop=True)]
    return out


def _pct(x):
    return '—' if x is None else f'{100 * x:+.2f}%'


def report(result):
    lines = ['', '## Buy the oversold dip, sell the rebound', '',
             f'Signal: three red closes and at least {OVERSOLD:g} ATR under the 21-day EMA. Entry at the signal close, '
             f'exit at the first close above the 10-day EMA or after {MAX_HOLD} sessions; stop 8% (close) unless '
             f'"no_stop"; 0.1% cost per side. Passes only with at least {MIN_TRADES} trades and a positive mean and '
             'median excess over the S&P 500 in every period.', '',
             '| Period | Variant | Trades | Win rate | Mean | Median | Mean vs S&P | Median vs S&P | Worst | 5th pct | Stops |',
             '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for period, rows in result.items():
        if period.startswith('_'):
            continue
        for name, s in rows.items():
            if not s.get('trades'):
                lines.append(f'| {period} | {name} | 0 | — | — | — | — | — | — | — | — |')
                continue
            lines.append(f"| {period} | {name} | {s['trades']} | {100 * s['win_rate']:.0f}% | {_pct(s['mean'])} | "
                         f"{_pct(s['median'])} | {_pct(s['mean_excess'])} | {_pct(s['median_excess'])} | "
                         f"{_pct(s['worst'])} | {_pct(s['p05'])} | {100 * s['stops']:.0f}% |")
    lines += ['', 'Passes: ' + ', '.join(f"{k} {'yes' if v else 'no'}" for k, v in result.get('_passes', {}).items())]
    nvda = result.get('_nvda_nov_2026')
    if nvda is not None:
        lines += ['', 'NVDA in November 2026 under this rule (with the 8% stop): ' + (
            '; '.join(f"signal {t['date']} at {t['entry']:.2f} ({t['ext_atr']:+.1f} ATR) → {t['reason']} on "
                      f"{t['exit']}, {_pct(t['ret'])}" for t in nvda) or 'no signal')]
    return '\n'.join(lines) + '\n'
