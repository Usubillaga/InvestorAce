"""Pairs-trading backtest on the InvestorAce universe (asked for on 21 Nov 2026). Research only.

Method (Gatev, Goetzmann and Rouwenhorst 2006, with a cointegration screen as in Vidyamurthy 2004):

* Each calendar year the pairs are formed again on the 504 sessions before it: same sector, both
  priced throughout, log prices correlated above 0.8, Engle-Granger cointegrated (Dickey-Fuller t
  of the residual below -3.34, the 5% critical value for two variables) and an Ornstein-Uhlenbeck
  half-life of 2 to 30 sessions. The ten strongest pairs are kept, each stock in at most one pair.
* Spread z-score, two versions: static OLS hedge ratio and mean/std from the formation window, or a
  Kalman filter whose hedge ratio keeps adapting, with the spread standardised over the previous 60 sessions.
* Decisions on close t, fills at close t+1, as in backtest.py. Enter at |z| > 2 (short the rich leg,
  buy the cheap one, dollar-neutral, 5% of the year-start equity per leg), exit at |z| < 0.5, stop at
  |z| > 4, close everything at the year end. Costs 0.1% per leg per fill, borrow 2% a year on the short leg.

A rule is only trusted if it helps in each of the three periods (2014-17, 2018-21, 2022-26): here, a
positive return after costs and a Sharpe ratio of at least 0.5 in every period.
"""
import math

import numpy as np
import pandas as pd

FORMATION, PAIRS, LEG = 504, 10, 0.05
MIN_CORR, EG_CRIT, HALF_LIFE = 0.8, -3.34, (2, 30)
Z_IN, Z_OUT, Z_STOP = 2.0, 0.5, 4.0
COST, BORROW = 0.001, 0.02
KALMAN_Q = 1e-5


def engle_granger(ly, lx):
    """(beta, alpha, Dickey-Fuller t of the residual, half-life in sessions)."""
    X = np.column_stack([np.ones(len(lx)), lx])
    (a, b), *_ = np.linalg.lstsq(X, ly, rcond=None)
    e = ly - a - b * lx
    de, lag = np.diff(e), e[:-1]
    Z = np.column_stack([np.ones(len(lag)), lag])
    coef, *_ = np.linalg.lstsq(Z, de, rcond=None)
    resid = de - Z @ coef
    dof = max(len(de) - 2, 1)
    var = resid @ resid / dof * np.linalg.inv(Z.T @ Z)
    gamma = coef[1]
    t = gamma / math.sqrt(var[1, 1]) if var[1, 1] > 0 else 0.
    half = -math.log(2) / math.log(1 + gamma) if -1 < gamma < 0 else math.inf
    return b, a, t, half


def kalman_z(ly, lx, q, r, start, window=60):
    """Kalman hedge ratio: the beta drifts as a random walk (variance q), the intercept does not.

    A drifting intercept would absorb the spread itself and leave nothing to trade. The spread uses the
    state known before each close; its z-score uses the previous 60 sessions only."""
    th, P = np.zeros(2), np.eye(2)
    Q = np.diag([0., q])
    e_all = np.full(len(ly), np.nan)
    for i, (x, y) in enumerate(zip(lx, ly)):
        P = P + Q
        h = np.array([1., x])
        e = y - h @ th
        e_all[i] = e
        S = h @ P @ h + r
        K = P @ h / S
        th, P = th + K * e, P - np.outer(K, h) @ P
    spread = pd.Series(e_all)
    mu = spread.shift(1).rolling(window).mean()
    sd = spread.shift(1).rolling(window).std()
    z = ((spread - mu) / sd).to_numpy(copy=True)
    z[:start] = np.nan
    return z


def form_pairs(logp, sectors):
    """Ten cointegrated same-sector pairs on one formation window (DataFrame of log prices)."""
    found = []
    by_sector = {}
    for s in logp.columns:
        if sectors.get(s):
            by_sector.setdefault(sectors[s], []).append(s)
    for members in by_sector.values():
        for i, y in enumerate(members):
            for x in members[i + 1:]:
                if np.corrcoef(logp[y], logp[x])[0, 1] < MIN_CORR:
                    continue
                b, a, t, half = engle_granger(logp[y].values, logp[x].values)
                if t < EG_CRIT and HALF_LIFE[0] <= half <= HALF_LIFE[1] and b > 0:
                    found.append((t, y, x, b, a, half))
    chosen, used = [], set()
    for t, y, x, b, a, half in sorted(found):
        if y in used or x in used:
            continue
        chosen.append(dict(y=y, x=x, beta=b, alpha=a, t=t, half_life=half))
        used |= {y, x}
        if len(chosen) == PAIRS:
            break
    return chosen


def simulate(close, sectors, start, end=None, method='static'):
    """Equity curve and trades of the pairs book over [start, end)."""
    close = close.sort_index()
    days = close.index[(close.index >= start) & ((close.index < end) if end is not None else True)]
    equity, curve, trades, formed = 1.0, [], [], []
    for year in sorted({d.year for d in days}):
        trade_days = days[days.year == year]
        first = close.index.get_loc(trade_days[0])
        if first < FORMATION:
            continue
        window = close.iloc[first - FORMATION:first]
        priced = [s for s in close.columns if window[s].notna().all() and close.loc[trade_days, s].notna().all()]
        logp = np.log(window[priced])
        pairs = form_pairs(logp, sectors)
        formed.append(dict(year=year, pairs=len(pairs)))
        leg = LEG * equity
        signals = {}
        for p in pairs:
            ly_all = np.log(close[p['y']].iloc[first - FORMATION:first + len(trade_days)].values)
            lx_all = np.log(close[p['x']].iloc[first - FORMATION:first + len(trade_days)].values)
            if method == 'kalman':
                r = np.var(ly_all[:FORMATION] - p['alpha'] - p['beta'] * lx_all[:FORMATION])
                z = kalman_z(ly_all, lx_all, KALMAN_Q, r, FORMATION)[FORMATION:]
            else:
                spread = ly_all - p['alpha'] - p['beta'] * lx_all
                mu, sd = spread[:FORMATION].mean(), spread[:FORMATION].std()
                z = (spread[FORMATION:] - mu) / sd if sd > 0 else np.zeros(len(trade_days))
            signals[(p['y'], p['x'])] = z
        state = {k: 0 for k in signals}                 # +1 long y / short x, -1 short y / long x
        open_pnl, pending = {}, {}
        for i, day in enumerate(trade_days):
            pnl = 0.
            if i:                                          # mark positions held since the last close
                prev = trade_days[i - 1]
                for (y, x), side in state.items():
                    if side:
                        move = side * leg * (close.at[day, y] / close.at[prev, y] - close.at[day, x] / close.at[prev, x])
                        move -= leg * BORROW / 252
                        pnl += move
                        open_pnl[(y, x)] += move
            for key, target in pending.items():            # orders decided at the last close fill now
                if state[key]:
                    pnl -= 2 * leg * COST
                    trades.append(dict(pair='/'.join(key), pnl=open_pnl.pop(key) - 2 * leg * COST))
                if target:
                    pnl -= 2 * leg * COST
                    open_pnl[key] = -2 * leg * COST
                state[key] = target
            pending = {}
            if i < len(trade_days) - 1:
                for key, z in signals.items():
                    zi, side = z[i], state[key]
                    if np.isnan(zi):
                        continue
                    if side and (abs(zi) < Z_OUT or abs(zi) > Z_STOP):
                        pending[key] = 0
                    elif not side and Z_IN < abs(zi) < Z_STOP:
                        pending[key] = -1 if zi > 0 else 1
            else:                                          # year end: close everything at the last close
                for key, side in state.items():
                    if side:
                        pnl -= 2 * leg * COST
                        trades.append(dict(pair='/'.join(key), pnl=open_pnl.pop(key) - 2 * leg * COST))
                        state[key] = 0
            equity += pnl
            curve.append((day, equity))
    return pd.Series(dict(curve)).sort_index() if curve else pd.Series(dtype=float), trades, formed


def metrics(curve, trades, spx=None):
    if len(curve) < 30:
        return dict(cagr=None, sharpe=None, max_drawdown=None, trades=len(trades))
    rets = curve.pct_change().dropna()
    years = max((curve.index[-1] - curve.index[0]).days / 365.25, 1e-9)
    out = dict(cagr=round(100 * ((curve.iloc[-1] / curve.iloc[0]) ** (1 / years) - 1), 2),
               sharpe=round(float(rets.mean() / rets.std() * math.sqrt(252)), 2) if rets.std() > 0 else None,
               max_drawdown=round(100 * float((curve / curve.cummax() - 1).min()), 2), trades=len(trades),
               win_rate=round(100 * sum(t['pnl'] > 0 for t in trades) / len(trades), 1) if trades else None)
    if spx is not None:
        s = spx.reindex(curve.index).pct_change()
        out['corr_spx'] = round(float(rets.corr(s.reindex(rets.index))), 2)
    return out


def study(close, sectors, spx, windows):
    """Both methods in each period; passes only if every period has a positive return and Sharpe >= 0.5."""
    out = {}
    for method in ('static', 'kalman'):
        rows = []
        for lo, hi in windows:
            curve, trades, formed = simulate(close, sectors, pd.Timestamp(lo), pd.Timestamp(hi) if hi else None, method)
            rows.append(dict(window=f'{lo} → {hi or "now"}', pairs_per_year=[f['pairs'] for f in formed],
                             **metrics(curve, trades, spx)))
        ok = all(r['cagr'] is not None and r['cagr'] > 0 and (r['sharpe'] or 0) >= 0.5 for r in rows)
        out[f'pairs_{method}'] = dict(windows=rows, passes=ok)
    return out


def report(result):
    lines = ['', '## Pairs trading (same-sector, Engle-Granger + Ornstein-Uhlenbeck)', '',
             'Yearly formation on 504 sessions, entry |z|>2, exit |z|<0.5, stop |z|>4, dollar-neutral 5% legs, '
             '0.1% per fill, 2% borrow. Passes only with a positive return and Sharpe ≥ 0.5 in every period.', '',
             '| Method | Period | Pairs/year | CAGR | Sharpe | Max DD | Trades | Win rate | Corr. S&P |',
             '|---|---|---|---:|---:|---:|---:|---:|---:|']
    for name, res in result.items():
        for r in res['windows']:
            lines.append(f"| {name} | {r['window']} | {','.join(map(str, r['pairs_per_year']))} | {r['cagr']} | "
                         f"{r['sharpe']} | {r['max_drawdown']} | {r['trades']} | {r.get('win_rate')} | {r.get('corr_spx')} |")
        lines.append(f"| {name} | **{'passes' if res['passes'] else 'fails'}** | | | | | | | |")
    return '\n'.join(lines) + '\n'
