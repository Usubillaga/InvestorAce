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
QUANTILE, WARMUP = 0.025, 500          # calibrated oversold: the lowest 2.5% of readings so far
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


def calibrated(osc, q=QUANTILE, warmup=WARMUP):
    """Oversold level from the oscillator's own history (known on the day): the fixed NYSE level of -150 does not
    fit breadth rebuilt from 500 large stocks, which reached it only four times since 2000 and not in 2008."""
    return osc.expanding(warmup).quantile(q).shift()


def signals(osc, oversold=OVERSOLD, lookback=LOOKBACK, gap=GAP):
    """oversold: a fixed level or a series of levels (one per day)."""
    level = oversold if isinstance(oversold, pd.Series) else pd.Series(oversold, index=osc.index)
    low = osc.rolling(lookback).min()
    thrust = (osc > 0) & (osc.shift() <= 0) & (low.shift() < level.shift())
    under = (osc < level) & (osc.shift() >= level.shift())
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


def strategy(spx, days, hold=126, cost=0.001, start='2000-01-01'):
    """In the S&P 500 for `hold` sessions after each signal close (a new signal extends the stay), else cash at 0%.
    Cumulative return, CAGR, worst fall and time invested, against buying and holding the S&P 500."""
    s = spx[spx.index >= pd.Timestamp(start)].dropna()
    if len(s) < 2:
        return None
    inside = pd.Series(False, index=s.index)
    for d in days:
        if d in s.index:
            i = s.index.get_loc(d)
            inside.iloc[i + 1:i + 1 + hold] = True       # bought at the signal close: the next sessions count
    daily = s.pct_change().fillna(0)
    switches = inside.astype(int).diff().abs().fillna(0)
    equity = (1 + daily * inside - switches * cost).cumprod()
    hold_eq = (1 + daily).cumprod()
    years = (s.index[-1] - s.index[0]).days / 365.25

    def stats(e):
        return dict(total=float(e.iloc[-1] - 1), cagr=float(e.iloc[-1] ** (1 / years) - 1),
                    worst=float((e / e.cummax() - 1).min()))
    return dict(start=str(s.index[0].date()), end=str(s.index[-1].date()), invested=float(inside.mean()),
                strategy=stats(equity), buy_hold=stats(hold_eq))


def robustness(spx, days, starts=20, placebo=500, seed=7):
    """The user's checks (27 Nov 2026): each period alone, 20 quarterly start dates 2000-2004, holding 63/126/252
    sessions, and a placebo of the same number of random signal days (same hold) to see how often chance does as well."""
    import numpy as np
    out = dict(periods={}, starts=[], holds={}, placebo={})
    for lo, hi in PERIODS:
        span = spx[(spx.index >= pd.Timestamp(lo)) & ((spx.index <= pd.Timestamp(hi)) if hi else True)]
        st = strategy(span, [d for d in days if d in span.index], start=lo)
        if st:
            out['periods'][f'{lo[:4]}-{(hi or "now")[:4]}'] = st
    for k in range(starts):
        start = (pd.Timestamp('2000-01-01') + pd.DateOffset(months=3 * k)).strftime('%Y-%m-%d')
        r = strategy(spx, days, start=start)
        if not r:
            continue
        out['starts'].append(dict(start=start, cagr=r['strategy']['cagr'], hold=r['buy_hold']['cagr'],
                                  worst=r['strategy']['worst'], hold_worst=r['buy_hold']['worst']))
    for h in (63, 126, 252):
        out['holds'][str(h)] = strategy(spx, days, hold=h)
    s = spx[spx.index >= pd.Timestamp('2000-01-01')]
    real = strategy(spx, days)['strategy']['cagr']
    rng = np.random.default_rng(seed)
    n = sum(1 for d in days if d >= s.index[0])
    sims = [strategy(spx, list(s.index[np.sort(rng.choice(len(s) - 1, n, replace=False))]))['strategy']['cagr']
            for _ in range(placebo)]
    out['placebo'] = dict(runs=placebo, signals=n, real=real, median=float(np.median(sims)),
                          share_at_least_real=float(np.mean([x >= real for x in sims])))
    return out


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
    cal = r.get('calibrated')
    if cal:
        lines += ['', f"## Calibrated oversold level (lowest {100 * QUANTILE:g}% of readings so far; now {cal['level']:+.1f})", '',
                  '| Signal | Period | Horizon | n | Mean | All days | Mean edge | Median edge | Positive |',
                  '|---|---|---|---:|---:|---:|---:|---:|---:|']
        for name, s in cal['signals'].items():
            for period, cells in s['periods'].items():
                for h, c in cells.items():
                    lines.append(f"| {name} | {period} | {h} | {c['n']} | {_pct(c['mean'])} | {_pct(c['base'])} | "
                                 f"{_pct(c['mean_edge'])} | {_pct(c['median_edge'])} | {100 * c['positive']:.0f}% |")
        lines += [''] + [f"Passes {k} (calibrated): {'yes' if v else 'no'}" for k, v in cal['passes'].items()]
 
        for k, st in (cal.get('strategy') or {}).items():
            a, b = st['strategy'], st['buy_hold']
            lines.append(f"Strategy {k} (6 months invested after each signal, else cash), {st['start']} → {st['end']}: "
                         f"cumulative {_pct(a['total'])}, CAGR {_pct(a['cagr'])}, worst fall {_pct(a['worst'])}, "
                         f"invested {100 * st['invested']:.0f}% of days; buy and hold {_pct(b['total'])}, CAGR "
                         f"{_pct(b['cagr'])}, worst fall {_pct(b['worst'])}.")
 
        for k, rb in (cal.get('robustness') or {}).items():
            lines += ['', f'### Robustness · {k}', '', '| Check | Strategy CAGR | Buy & hold CAGR | Strategy worst fall | Buy & hold worst fall | Invested |',
                      '|---|---:|---:|---:|---:|---:|']
            for name, st in list(rb['periods'].items()) + [(f'hold {h} sessions', st) for h, st in rb['holds'].items()]:
                lines.append(f"| {name} | {_pct(st['strategy']['cagr'])} | {_pct(st['buy_hold']['cagr'])} | "
                             f"{_pct(st['strategy']['worst'])} | {_pct(st['buy_hold']['worst'])} | {100 * st['invested']:.0f}% |")
            wins = sum(x['cagr'] > x['hold'] for x in rb['starts']) if rb['starts'] else 0
            margins = [x['cagr'] - x['hold'] for x in rb['starts']] or [0.]
            lines += ['', f"{len(rb['starts'])} start dates (quarterly 2000-2004): strategy CAGR above buy and hold in {wins}/{len(rb['starts'])}; "
                      f"smallest margin {_pct(min(margins))}, largest {_pct(max(margins))}.",
                      f"Placebo: {rb['placebo']['runs']} runs with {rb['placebo']['signals']} random signal days: median CAGR "
                      f"{_pct(rb['placebo']['median'])}; {100 * rb['placebo']['share_at_least_real']:.1f}% of runs did as well "
                      f"as the real {_pct(rb['placebo']['real'])}."]
        for k, st in (cal.get('total_return') or {}).items():
            lines.append(f"With dividends (^SP500TR) {k}: strategy CAGR {_pct(st['strategy']['cagr'])}, buy and hold "
                         f"{_pct(st['buy_hold']['cagr'])}.")
        lines += [''] + [f"{k} dates (calibrated): " + ', '.join(s['dates']) for k, s in cal['signals'].items()]
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
    fixed = study(spx, osc, signals(osc, calibrated(osc)))
    cal_sig = signals(osc, calibrated(osc))
    result['calibrated'] = dict(level=round(float(calibrated(osc).iloc[-1]), 1), signals=fixed['signals'],
                                passes=fixed['passes'],
                                strategy={k: strategy(spx, v) for k, v in cal_sig.items()},
                                robustness={k: robustness(spx, v) for k, v in cal_sig.items()})
    try:
        import yfinance as yf
        tr = yf.download('^SP500TR', start='1999-01-01', auto_adjust=False, progress=False)['Close']
        tr = (tr.iloc[:, 0] if isinstance(tr, pd.DataFrame) else tr).dropna()
        tr.index = tr.index.tz_localize(None) if tr.index.tz is not None else tr.index
        if len(tr) > 1000:
            result['calibrated']['total_return'] = {k: strategy(tr.reindex(spx.index).ffill().dropna(), v)
                                                    for k, v in cal_sig.items()}
    except Exception as exc:
        print(f'^SP500TR unavailable: {type(exc).__name__}')
    OUT_JSON.parent.mkdir(exist_ok=True)
    OUT_JSON.write_text(json.dumps(result, indent=1, allow_nan=False) + '\n', encoding='utf-8')
    OUT_MD.write_text(report(result), encoding='utf-8')
    print(report(result))


if __name__ == '__main__':
    main()
