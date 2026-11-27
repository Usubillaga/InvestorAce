"""McClellan Oscillator breadth thrust, rebuilt from S&P 500 members (asked for on 27 Nov 2026).

NYSE advance/decline history is not in our data, so breadth is rebuilt from the stocks that were in the S&P 500
on each day (point-in-time members, as in panic_history.py): advancers minus decliners over members with a price
on both days, ratio-adjusted x1000 (RANA). Oscillator = EMA19 - EMA39. Signals, one per 63 sessions:
* thrust: the oscillator crosses above 0 within 20 sessions of a reading under OVERSOLD;
* oversold: the first close under OVERSOLD.
Each is bought at the signal close in the S&P 500 and compared with the S&P 500's average forward return over all
days of the same period. A signal passes only with a positive mean and median edge at 126 sessions in all three
periods. Research only; members without Yahoo prices are left out (survivorship).
"""
import json
import statistics
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
OUT_JSON = ROOT / 'backtests' / 'mcclellan.json'
OUT_MD = ROOT / 'backtests' / 'mcclellan.md'
OVERSOLD, LOOKBACK, GAP = -150., 20, 63
HORIZONS = (21, 63, 126, 252)
PERIODS = (('2000-01-01', '2009-12-31'), ('2010-01-01', '2019-12-31'), ('2020-01-01', None))


def oscillator(close, members):
    """RANA McClellan oscillator from member closes (dates x tickers) and membership (same shape, bool)."""
    change = close.diff()
    valid = members & close.notna() & close.shift().notna()
    adv = ((change > 0) & valid).sum(axis=1)
    dec = ((change < 0) & valid).sum(axis=1)
    net = 1000 * (adv - dec) / (adv + dec).where(adv + dec >= 50)
    net = net.dropna()
    return (net.ewm(span=19, adjust=False).mean() - net.ewm(span=39, adjust=False).mean()).iloc[39:]


def signals(osc, oversold=OVERSOLD, lookback=LOOKBACK, gap=GAP):
    low = osc.rolling(lookback).min()
    thrust = (osc > 0) & (osc.shift() <= 0) & (low.shift() < oversold)
    under = (osc < oversold) & (osc.shift() >= oversold)
    out = {}
    for name, flags in (('thrust', thrust), ('oversold', under)):
        days, last = [], None
        for i, (day, f) in enumerate(flags.items()):
            if f and (last is None or i - last > gap):
                days.append(day)
                last = i
        out[name] = days
    return out


def forward(spx, days, h):
    idx = spx.index
    out = {}
    for d in days:
        i = idx.get_loc(d)
        if i + h < len(idx):
            out[d] = float(spx.iloc[i + h] / spx.iloc[i] - 1)
    return out


def study(spx, osc, sig):
    result = dict(schema='mcclellan-v1', start=str(osc.index[0].date()), end=str(osc.index[-1].date()),
                  last=dict(date=str(osc.index[-1].date()), value=round(float(osc.iloc[-1]), 1)), signals={}, passes={})
    for name, days in sig.items():
        block = {}
        for lo, hi in PERIODS:
            key = f'{lo[:4]}-{(hi or "now")[:4]}'
            sel = [d for d in days if d >= pd.Timestamp(lo) and (hi is None or d <= pd.Timestamp(hi))]
            span = spx[(spx.index >= pd.Timestamp(lo)) & ((spx.index <= pd.Timestamp(hi)) if hi else True)]
            cells = {}
            for h in HORIZONS:
                f = forward(spx, sel, h)
                base = list(forward(spx, list(span.index), h).values())
                if f and base:
                    edge = [x - statistics.fmean(base) for x in f.values()]
                    cells[str(h)] = dict(n=len(f), mean=statistics.fmean(f.values()), base=statistics.fmean(base),
                                         mean_edge=statistics.fmean(edge), median_edge=statistics.median(edge),
                                         positive=sum(x > 0 for x in f.values()) / len(f))
            block[key] = cells
        result['signals'][name] = dict(dates=[str(d.date()) for d in days], periods=block)
        result['passes'][name] = all(c.get('126') and c['126']['mean_edge'] > 0 and c['126']['median_edge'] > 0
                                     for c in block.values())
    return result


def _pct(x):
    return f'{100 * x:+.1f}%'


def report(r):
    lines = ['# McClellan Oscillator from S&P 500 members', '',
             f"Rebuilt breadth (RANA) {r['start']} → {r['end']}; last {r['last']['value']:+.1f} on {r['last']['date']}. "
             f'Thrust: crosses above 0 within {LOOKBACK} sessions of a reading under {OVERSOLD:g}. Oversold: first close '
             f'under {OVERSOLD:g}. One signal per {GAP} sessions; S&P 500 forward returns against the average of all '
             'days in the same period. Passes only with a positive mean and median 6-month edge in all periods.', '',
             '| Signal | Period | Horizon | n | Mean | All days | Mean edge | Median edge | Positive |',
             '|---|---|---|---:|---:|---:|---:|---:|---:|']
    for name, s in r['signals'].items():
        for period, cells in s['periods'].items():
            for h, c in cells.items():
                lines.append(f"| {name} | {period} | {h} | {c['n']} | {_pct(c['mean'])} | {_pct(c['base'])} | "
                             f"{_pct(c['mean_edge'])} | {_pct(c['median_edge'])} | {100 * c['positive']:.0f}% |")
    lines += [''] + [f"Passes {k}: {'yes' if v else 'no'}" for k, v in r['passes'].items()]
    lines += [''] + [f"{k} dates: " + ', '.join(s['dates']) for k, s in r['signals'].items()]
    return '\n'.join(lines) + '\n'


def main():
    import panic_backtest as pb
    import panic_history as ph
    rows = pb.fetch_members()
    tickers = sorted({pb.yahoo(t) for d, m in rows if d >= pd.Timestamp('1998-01-01') for t in m})
    spx, _ = ph.index_series()
    data = ph.download(tickers)
    close = data['adj'].reindex(spx.index)
    members = ph.membership(rows, close.index, close.columns)
    osc = oscillator(close, members)
    result = study(spx, osc, signals(osc))
    OUT_JSON.parent.mkdir(exist_ok=True)
    OUT_JSON.write_text(json.dumps(result, indent=1, allow_nan=False) + '\n', encoding='utf-8')
    OUT_MD.write_text(report(result), encoding='utf-8')
    print(report(result))


if __name__ == '__main__':
    main()
