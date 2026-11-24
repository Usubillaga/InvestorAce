"""Panic buys since 2000: what to buy when the thermometer panics, including the bear markets of 2000-2002 and
2007-2009 (asked for on 24 Nov 2026, after Scion's "Bear market heroes" tables).

The panic backtest in panic_backtest.py starts in 2012 (Yahoo's 14-year panel), so its five panic signals
(2016-2025) all came in markets that recovered. This study starts in 2000 and asks what each basket did after
every first panic close:

* top10_weight: the ten largest S&P 500 members by market cap, cap-weighted (the index-leaders paper account).
  Cap = split-adjusted close x Yahoo shares outstanding on the day in today's split terms; Yahoo's share history
  is thin before about 2010, so when fewer than six of the candidates have shares the ten most traded members
  (63-day dollar volume) stand in, weighted by dollar volume, and the event says so (basis).
* leaders: members within 20% of their own ten-year high (Scion's "leaders"), equal weight.
* broken: 20% to 40% below the ten-year high; busted: more than 40% below; equal weight.
* all_members: every priced member, equal weight; spx: the S&P 500 index.

Members are the S&P 500 as on the signal day (fja05680/sp500, from 1996). The thermometer is market_pulse's
four scores, with the breadth score taken from those members (not from today's InvestorAce universe). Buys
at the close after the signal, 0.1% per side; returns use dividend-adjusted closes; a member that stops
trading is carried at its last price (as Scion carries delisted names). Holding periods 63/126/252/378
sessions, plus the paper account's exit (the close after the first thermometer close at or above 80, at most
252 sessions).

Survivorship: Yahoo has no prices for many companies that left the index long ago (bankrupt, acquired). They are
counted on every signal and left out, so before about 2010 the busted basket in particular looks better than it
was (the worst failures are missing). The breadth check against Scion's own counts on their top dates shows how
large that gap is. Research only.
"""
import json
import statistics
from pathlib import Path

import numpy as np
import pandas as pd

import panic_backtest as pb

ROOT = Path(__file__).resolve().parent
OUT_JSON = ROOT / 'backtests' / 'panic_history.json'
OUT_MD = ROOT / 'backtests' / 'panic_history.md'
START = '1999-01-01'                  # first signals need 200 sessions of history
HORIZONS = (63, 126, 252, 378, 882)          # 882 sessions = 42 months
TEN_YEARS = 2520
BASKETS = ('top10_weight', 'leaders', 'broken', 'busted', 'all_members', 'mix', 'spx')
RISK = ('top10_weight', 'all_members', 'mix', 'spx')   # baskets whose drawdown during the holding is measured
DELAYS = (0, 5, 10)
LEVELS = tuple(float(x) for x in range(20, 9, -1))     # buy at the first close under this level: 20, 19, ..., 10
SECOND = (18., 16., 15., 14., 12., 10.)               # second-half level of the two-tranche buy
STAGE_WAIT = 63                                       # the second tranche waits at most this long for a close under 10                                   # entry later by this many sessions (timing sensitivity)
LONG = 882
# Scion's "Bear market heroes II" (Bloomberg, adjusted closes): members, broken 20%+ and busted 40%+ on each top.
SCION_TOPS = {'2000-03-24': (489, 0.71, 0.32), '2007-10-09': (497, 0.43, 0.22), '2011-04-29': (493, 0.49, 0.25),
              '2015-05-21': (495, 0.26, 0.12), '2018-09-20': (501, 0.28, 0.11), '2020-02-19': (505, 0.31, 0.13),
              '2022-01-03': (500, 0.22, 0.08), '2025-02-19': (503, 0.43, 0.19), '2026-10-06': (503, 0.55, 0.23)}


# ------------------------------------------------------------------ membership and breadth
def membership(rows, index, tickers):
    """Boolean frame (dates x Yahoo tickers): member of the S&P 500 on that date."""
    changes = pd.DataFrame(False, index=pd.DatetimeIndex([d for d, _ in rows]), columns=sorted(tickers))
    for date, members in rows:
        cols = [pb.yahoo(t) for t in members if pb.yahoo(t) in changes.columns]
        changes.loc[date, cols] = True
    changes = changes[~changes.index.duplicated(keep='last')]
    return changes.reindex(changes.index.union(index)).ffill().reindex(index).fillna(False).astype(bool)


def breadth_heat(spx, vix, close, members):
    """market_pulse's thermometer with the breadth score from the members of the day."""
    ma200, ma50 = spx.rolling(200).mean(), spx.rolling(50).mean()
    s200 = pb._clip(50 + 5 * 100 * (spx / ma200 - 1))
    s50 = pb._clip(50 + 10 * 100 * (spx / ma50 - 1))
    svix = pb._clip((40 - vix.reindex(spx.index).ffill()) / 30 * 100)
    sma = close.rolling(200).mean()
    valid = sma.notna() & close.notna() & members
    count = valid.sum(axis=1)
    share = 100 * ((close > sma) & valid).sum(axis=1) / count.where(count >= 20)
    frame = pd.concat([s200, s50, svix, share], axis=1)
    return frame.mean(axis=1).where(frame.notna().sum(axis=1) >= 3)


def drawdowns(adj):
    """Distance from each stock's own trailing ten-year high close (dividend-adjusted), and the date of that high."""
    high = adj.rolling(TEN_YEARS, min_periods=252).max()
    return adj / high - 1


def fresh_high(adj, window=504):
    """True where the ten-year high was set within the last two years (its two-year max equals its ten-year max)."""
    ten = adj.rolling(TEN_YEARS, min_periods=252).max()
    two = adj.rolling(window, min_periods=1).max()
    return (two >= ten * (1 - 1e-9)) & ten.notna()


def breadth_on(day, close, dd, members, recent_high):
    """Shares of priced members broken (20%+) and busted (40%+) below their ten-year high on `day`."""
    on = members.loc[day]
    priced = dd.loc[day][on].dropna()
    n = len(priced)
    if not n:
        return None
    busted = priced[priced <= -0.40]
    fresh = int(recent_high.loc[day][busted.index].sum()) if len(busted) else 0
    return dict(members=int(on.sum()), priced=int(n), broken=float((priced <= -0.20).mean()),
                busted=float((priced <= -0.40).mean()), busted_names=int(len(busted)), busted_fresh_high=fresh)


# ------------------------------------------------------------------ baskets
def basket_return(adj, picks, weights, start, end):
    """Weighted return from the close at `start` to the close at `end` (positions), last price carried."""
    total, wsum = 0., 0.
    for t, w in zip(picks, weights):
        series = adj[t]
        a = series.iloc[start]
        if not np.isfinite(a) or a <= 0:
            continue
        b = series.iloc[:end + 1].ffill().iloc[end]          # carried at its last price after it stops trading
        if not np.isfinite(b):
            continue
        total += w * (b / a * (1 - pb.COST) / (1 + pb.COST) - 1)
        wsum += w
    return float(total / wsum) if wsum > 0 else None


def basket_path(adj, picks, weights, start, end):
    """Value of a buy-and-hold basket (1 at the close at `start`) on every close up to `end`, last price carried."""
    parts, wsum = [], 0.
    for t, w in zip(picks, weights):
        series = adj[t].iloc[start:end + 1].ffill()
        a = series.iloc[0]
        if not np.isfinite(a) or a <= 0:
            continue
        parts.append(w * series / a)
        wsum += w
    if wsum <= 0:
        return None
    return sum(parts) / wsum


def max_drawdown(path):
    """Largest fall from a running high, as a negative fraction (0 when it never falls)."""
    if path is None or not len(path):
        return None
    values = path.to_numpy(dtype=float)
    peak = np.maximum.accumulate(values)
    return float(np.nanmin(values / peak - 1))


def top10(day, cols, split_close, volume, shares, candidates=30):
    """(tickers, weights, basis) of the ten largest members by cap on `day`, or by dollar volume as a stand-in."""
    dollar = (split_close.loc[:day, cols].iloc[-63:] * volume.loc[:day, cols].iloc[-63:]).mean().dropna()
    pool = list(dollar.sort_values(ascending=False).index[:candidates])
    caps = {}
    for t in pool:
        n = shares(t, day)
        px = split_close.at[day, t]
        if n and np.isfinite(px):
            caps[t] = float(px) * float(n)
    if len(caps) >= 6:
        ranked = sorted(caps.items(), key=lambda kv: -kv[1])[:10]
        total = sum(c for _, c in ranked)
        return [t for t, _ in ranked], [c / total for _, c in ranked], 'market cap'
    ranked = dollar.sort_values(ascending=False).iloc[:10]
    return list(ranked.index), list(ranked / ranked.sum()), 'dollar volume (no share history)'


def euphoria_exit(index, start, heat, cap=252):
    """Position of the close after the first close at or above 80 after `start`, at most `cap` sessions."""
    after = heat.iloc[start + 1:start + cap]
    hits = np.nonzero((after >= pb.EUPHORIA).to_numpy())[0]
    end = start + 1 + int(hits[0]) + 1 if len(hits) else start + cap
    return min(end, len(index) - 1)


def long_euphoria_exit(index, start, heat, minimum=LONG):
    """Position of the close after the first close at or above 80 at least `minimum` sessions after `start`;
    (last position, True) when there was none yet."""
    after = heat.iloc[start + minimum:]
    hits = np.nonzero((after >= pb.EUPHORIA).to_numpy())[0]
    if len(hits) and start + minimum + int(hits[0]) + 1 < len(index):
        return start + minimum + int(hits[0]) + 1, False
    return len(index) - 1, True


def event(day, adj, split_close, volume, members, dd, recent_high, spx, heat, shares, horizons=HORIZONS):
    index = adj.index
    pos = index.get_loc(day)
    start = pos + 1
    if start >= len(index):
        return None
    on = members.loc[day]
    cols = [t for t in adj.columns if on.get(t, False)]
    priced = [t for t in cols if np.isfinite(adj.at[day, t])]
    d = dd.loc[day, priced]
    groups = dict(leaders=list(d[d > -0.20].index), broken=list(d[(d <= -0.20) & (d > -0.40)].index),
                  busted=list(d[d <= -0.40].index), all_members=priced)
    top, top_w, basis = top10(day, priced, split_close, volume, shares)
    spx_i = spx.index.get_loc(index[start]) if index[start] in spx.index else None
    row = dict(date=str(day.date()), heat=round(float(heat.loc[day]), 1), basis=basis,
               top10=[[t, round(float(w), 4)] for t, w in zip(top, top_w)],
               breadth=breadth_on(day, adj, dd, members, recent_high),
               sizes={k: len(v) for k, v in groups.items()}, returns={})
    for h in horizons:
        end = start + h
        if end >= len(index):
            row['returns'][str(h)] = None
            continue
        cell = dict(top10_weight=basket_return(adj, top, top_w, start, end))
        for k, names in groups.items():
            cell[k] = basket_return(adj, names, [1.] * len(names), start, end) if names else None
        cell['spx'] = (float(spx.iloc[spx_i + h] / spx.iloc[spx_i] - 1)
                       if spx_i is not None and spx_i + h < len(spx) else None)
        cell['mix'] = (0.5 * cell['top10_weight'] + 0.5 * cell['all_members']
                       if None not in (cell['top10_weight'], cell['all_members']) else None)
        if h in (252, LONG):
            cell['drawdown'] = holding_drawdowns(adj, top, top_w, groups['all_members'], spx, start, end)
        row['returns'][str(h)] = cell
    end = euphoria_exit(index, start, heat)
    row['euphoria_exit'] = dict(exit=str(index[end].date()), sessions=int(end - start),
                                top10_weight=basket_return(adj, top, top_w, start, end),
                                **{k: basket_return(adj, v, [1.] * len(v), start, end) if v else None
                                   for k, v in groups.items()},
                                spx=float(spx.loc[index[end]] / spx.loc[index[start]] - 1)
                                if index[end] in spx.index and index[start] in spx.index else None)
    end, open_ = long_euphoria_exit(index, start, heat)
    if end > start:
        top_r = basket_return(adj, top, top_w, start, end)
        all_r = basket_return(adj, groups['all_members'], [1.] * len(priced), start, end)
        row['long_exit'] = dict(exit=str(index[end].date()), sessions=int(end - start), open=open_,
                                top10_weight=top_r, all_members=all_r,
                                mix=0.5 * top_r + 0.5 * all_r if None not in (top_r, all_r) else None,
                                spx=float(spx.loc[index[end]] / spx.loc[index[start]] - 1),
                                drawdown=holding_drawdowns(adj, top, top_w, groups['all_members'], spx, start, end))
    return row


def holding_drawdowns(adj, top, top_w, members, spx, start, end):
    """Worst fall from a running high while held, per basket (the mix rebalances nowhere: half each at the buy)."""
    t = basket_path(adj, top, top_w, start, end)
    a = basket_path(adj, members, [1.] * len(members), start, end)
    idx = adj.index
    s_ = spx.reindex(idx).iloc[start:end + 1].ffill()
    return dict(top10_weight=max_drawdown(t), all_members=max_drawdown(a),
                mix=max_drawdown(0.5 * t + 0.5 * a) if t is not None and a is not None else None,
                spx=max_drawdown(s_ / s_.iloc[0]))


def summary(events, horizons=HORIZONS):
    out = {}
    for h in horizons:
        rows = [e['returns'].get(str(h)) for e in events if e['returns'].get(str(h))]
        cell = {}
        for k in BASKETS:
            xs = [r[k] for r in rows if r.get(k) is not None]
            if xs:
                cell[k] = dict(n=len(xs), mean=float(statistics.fmean(xs)), median=float(statistics.median(xs)),
                               worst=float(min(xs)), positive=int(sum(x > 0 for x in xs)),
                               beats_spx=int(sum(r[k] > r['spx'] for r in rows
                                                 if r.get(k) is not None and r.get('spx') is not None)))
        dds = [r.get('drawdown') for r in rows if r.get('drawdown')]
        if dds:
            cell['drawdown'] = {k: dict(mean=float(statistics.fmean(d[k] for d in dds if d.get(k) is not None)),
                                        worst=float(min(d[k] for d in dds if d.get(k) is not None)))
                                for k in RISK if any(d.get(k) is not None for d in dds)}
        out[str(h)] = cell
    return out


STAGED = ('all_at_20', 'all_at_10', 'staged_cash', 'staged_fallback')


def staged(day, heat, adj, split_close, volume, members, spx, shares, horizons=(252, LONG), second=10.):
    """Half at the close after the first panic close (under 20), half at the close after the first close under 10
    within STAGE_WAIT sessions. staged_cash keeps the second half in cash if 10 never comes; staged_fallback buys it
    after STAGE_WAIT sessions anyway. all_at_20 / all_at_10 put everything in at one of the two points (all_at_10 is
    cash until then, and cash throughout when 10 never comes). The basket is the mix (half the ten largest by weight,
    half all members) chosen on the signal day; the same timing is applied to the S&P 500. Returns and the worst
    fall are for the whole account, cash included, from the first buy."""
    index = adj.index
    pos = index.get_loc(day)
    a = pos + 1
    if a >= len(index):
        return None
    window = heat.iloc[pos:pos + STAGE_WAIT + 1]
    deep = np.nonzero((window < second).to_numpy())[0]
    b10 = pos + int(deep[0]) + 1 if len(deep) else None
    on = members.loc[day]
    priced = [t for t in adj.columns if on.get(t, False) and np.isfinite(adj.at[day, t])]
    top, top_w, _ = top10(day, priced, split_close, volume, shares)
    spx_full = spx.reindex(index).ffill()
    row = dict(date=str(day.date()), reached_10=str(index[b10].date()) if b10 is not None and b10 < len(index) else None,
               plans={})
    for h in horizons:
        end = a + h
        if end >= len(index):
            continue
        def leg(start):
            t = basket_path(adj, top, top_w, start, end)
            m = basket_path(adj, priced, [1.] * len(priced), start, end)
            mix = 0.5 * t + 0.5 * m if t is not None and m is not None else None
            s_ = spx_full.iloc[start:end + 1]
            return mix, s_ / s_.iloc[0]
        def account(parts):
            vals = {}
            for which in (0, 1):
                v = pd.Series(0., index=index[a:end + 1])
                for weight, start in parts:
                    if start is None or start > end:
                        v += weight                                      # stays in cash
                        continue
                    path = leg(start)[which]
                    if path is None:
                        return None
                    v.loc[index[a:start]] += weight                      # cash before this tranche is bought
                    v.loc[path.index] += weight * path * (1 - pb.COST) / (1 + pb.COST)
                vals['mix' if which == 0 else 'spx'] = dict(ret=float(v.iloc[-1] - 1), drawdown=max_drawdown(v))
            return vals
        fallback = b10 if b10 is not None else pos + STAGE_WAIT + 1
        plans = dict(all_at_20=[(1., a)], all_at_10=[(1., b10)], staged_cash=[(.5, a), (.5, b10)],
                     staged_fallback=[(.5, a), (.5, fallback)])
        row['plans'][str(h)] = {name: account(parts) for name, parts in plans.items()}
    return row


def staged_summary(rows, horizons=(252, LONG)):
    out = {}
    for h in horizons:
        cell = {}
        for name in STAGED:
            for which in ('mix', 'spx'):
                xs = [r['plans'][str(h)][name][which] for r in rows
                      if str(h) in r['plans'] and r['plans'][str(h)].get(name)]
                if xs:
                    cell[f'{name}:{which}'] = dict(n=len(xs), mean=float(statistics.fmean(x['ret'] for x in xs)),
                                                   worst=float(min(x['ret'] for x in xs)),
                                                   dd_mean=float(statistics.fmean(x['drawdown'] for x in xs)),
                                                   dd_worst=float(min(x['drawdown'] for x in xs)))
        out[str(h)] = cell
    return out


def long_summary(events):
    """The 42-months-then-euphoria exit: completed and still open holdings, against the S&P 500."""
    rows = [e['long_exit'] for e in events if e.get('long_exit')]
    out = dict(n=len(rows), open=int(sum(r['open'] for r in rows)))
    for k in RISK:
        xs = [r[k] for r in rows if r.get(k) is not None]
        if xs:
            out[k] = dict(mean=float(statistics.fmean(xs)), median=float(statistics.median(xs)), worst=float(min(xs)),
                          beats_spx=int(sum(r[k] > r['spx'] for r in rows if r.get(k) is not None)) if k != 'spx' else None,
                          drawdown_worst=float(min(r['drawdown'][k] for r in rows if r['drawdown'].get(k) is not None)))
    return out


def study(spx, vix, adj, split_close, volume, rows, shares, start=START):
    index = spx.index[spx.index >= pd.Timestamp(start) - pd.Timedelta(days=400)]
    adj, split_close, volume = (f.reindex(index) for f in (adj, split_close, volume))
    spx, vix = spx.reindex(index), vix.reindex(index).ffill()
    members = membership(rows, index, adj.columns)
    heat = breadth_heat(spx, vix, adj, members)
    dd = drawdowns(adj)
    recent_high = fresh_high(adj)
    entries = [d for d in pb.signals(heat[heat.index >= pd.Timestamp(start)])[0]]
    events = [e for e in (event(d, adj, split_close, volume, members, dd, recent_high, spx, heat, shares)
                          for d in entries) if e]
    delays = {}
    for lag in DELAYS:
        if not lag:
            delayed = events
        else:
            days = [index[index.get_loc(d) + lag] for d in entries if index.get_loc(d) + lag < len(index) - 1]
            delayed = [e for e in (event(d, adj, split_close, volume, members, dd, recent_high, spx, heat, shares,
                                         horizons=(252, LONG)) for d in days) if e]
        full = summary(delayed, horizons=(252, LONG))
        delays[str(lag)] = {h: {k: v for k, v in cells.items() if k in RISK} for h, cells in full.items()}
    levels = {}
    for level in LEVELS:
        if level == pb.PANIC:
            lev_events = events
        else:
            lev_days = pb.signals(heat[heat.index >= pd.Timestamp(start)], panic=level)[0]
            lev_events = [e for e in (event(d, adj, split_close, volume, members, dd, recent_high, spx, heat, shares,
                                            horizons=(252, LONG)) for d in lev_days) if e]
        full = summary(lev_events, horizons=(252, LONG))
        levels[f'{level:g}'] = dict(signals=[e['date'] for e in lev_events],
                                    summary={h: {k: v for k, v in c.items() if k in RISK or k == 'drawdown'}
                                             for h, c in full.items()},
                                    long_exit=long_summary(lev_events))
    staged_rows = [r for r in (staged(d, heat, adj, split_close, volume, members, spx, shares) for d in entries) if r]
    staged_grid = {}
    for second in SECOND:
        rows_ = staged_rows if second == 10. else [r for r in (staged(d, heat, adj, split_close, volume, members, spx,
                                                                      shares, second=second) for d in entries) if r]
        staged_grid[f'{second:g}'] = dict(summary=staged_summary(rows_),
                                          reached=sum(1 for r in rows_ if r['reached_10']), n=len(rows_))
    checks = {}
    for date, (n, broken, busted) in SCION_TOPS.items():
        day = pd.Timestamp(date)
        if day in index:
            b = breadth_on(day, adj, dd, members, recent_high)
            if b:
                checks[date] = dict(ours=b, scion=dict(members=n, broken=broken, busted=busted))
    last = heat.dropna()
    return dict(schema='panic-history-v1', start=str(index[0].date()), end=str(index[-1].date()),
                signals=len(events), events=events, summary=summary(events), breadth_checks=checks,
                long_exit=long_summary(events), delays=delays, levels=levels,
                staged=dict(rows=staged_rows, summary=staged_summary(staged_rows)), staged_grid=staged_grid,
                last_heat=dict(date=str(last.index[-1].date()), value=round(float(last.iloc[-1]), 1)) if len(last) else None,
                breadth_now=breadth_on(index[-1], adj, dd, members, recent_high))


# ------------------------------------------------------------------ report
def _pct(x, digits=1):
    return '—' if x is None else f'{100 * x:+.{digits}f}%'


def _share(x):
    return '—' if x is None else f'{100 * x:.0f}%'


def report(result):
    first = result['events'][0]['date'] if result.get('events') else '—'
    lines = ['# Panic buys since 2000', '',
             f"Thermometer panic signals {first} → {result['end']}: {result['signals']} first panic closes. "
             'Members as on each day (S&P 500), bought at the next close, 0.1% per side, delisted names carried at '
             'their last price. Survivorship: members without Yahoo prices are left out (counted per signal), so '
             'early busted baskets look better than they were.', '']
    names = dict(top10_weight='Top 10 by weight', leaders='Leaders (<20% off high)', broken='Broken (20-40%)',
                 busted='Busted (>40%)', all_members='All members, equal', mix='Half top 10, half all members',
                 spx='S&P 500')
    for h, cells in result['summary'].items():
        months = {63: 3, 126: 6, 252: 12, 378: 18, 882: 42}[int(h)]
        lines += [f'## {months} months ({h} sessions)', '',
                  '| Basket | Signals | Mean | Median | Worst | Positive | Beats S&P |', '|---|---:|---:|---:|---:|---:|---:|']
        for k in BASKETS:
            c = cells.get(k)
            if c:
                lines.append(f"| {names[k]} | {c['n']} | {_pct(c['mean'])} | {_pct(c['median'])} | {_pct(c['worst'])} | "
                             f"{c['positive']}/{c['n']} | {'—' if k == 'spx' else str(c['beats_spx']) + '/' + str(c['n'])} |")
        dd = cells.get('drawdown')
        if dd:
            lines.append('Worst fall from a high while held (mean / worst signal): ' + '; '.join(
                f"{names[k]} {_pct(v['mean'])} / {_pct(v['worst'])}" for k, v in dd.items()))
        lines.append('')
    lx = result.get('long_exit') or {}
    if lx.get('n'):
        lines += ['## Hold at least 42 months, then sell at the close after the first euphoria close', '',
                  f"{lx['n']} signals, {lx['open']} still open (no euphoria after 42 months yet, marked at the last close).",
                  '', '| Basket | Mean | Median | Worst | Beats S&P | Worst fall while held |', '|---|---:|---:|---:|---:|---:|']
        for k in RISK:
            c = lx.get(k)
            if c:
                lines.append(f"| {names[k]} | {_pct(c['mean'])} | {_pct(c['median'])} | {_pct(c['worst'])} | "
                             f"{'—' if c['beats_spx'] is None else str(c['beats_spx']) + '/' + str(lx['n'])} | "
                             f"{_pct(c['drawdown_worst'])} |")
        lines += ['', 'Per signal: ' + '; '.join(
            f"{e['date']} → {e['long_exit']['exit']}{' (open)' if e['long_exit']['open'] else ''}: top 10 "
            f"{_pct(e['long_exit']['top10_weight'])}, all {_pct(e['long_exit']['all_members'])}, S&P "
            f"{_pct(e['long_exit']['spx'])}" for e in result['events'] if e.get('long_exit')), '']
    if result.get('levels'):
        lines += ['## Buying deeper in the panic: first close under each level from 20 to 10', '',
                  'Eleven levels on 11-14 overlapping signals: the best-looking level is partly luck. Look for a smooth '
                  'pattern across neighbouring levels, not for the single best row.', '',
                  '| Level | Signals | Top 10 12 m mean / worst | Top 10 worst fall while held, 12 m | Mix 42 m mean / worst | '
                  'Mix worst fall while held, 42 m | S&P 12 m mean |', '|---|---:|---|---:|---|---:|---:|']
        for level, block in result['levels'].items():
            y1, y42 = block['summary'].get('252') or {}, block['summary'].get(str(LONG)) or {}
            t1, m42, s1 = y1.get('top10_weight'), y42.get('mix'), y1.get('spx')
            d1, d42 = (y1.get('drawdown') or {}).get('top10_weight'), (y42.get('drawdown') or {}).get('mix')
            lines.append(f"| < {level} | {len(block['signals'])} | "
                         f"{_pct(t1['mean']) + ' / ' + _pct(t1['worst']) if t1 else '—'} | {_pct(d1['worst']) if d1 else '—'} | "
                         f"{_pct(m42['mean']) + ' / ' + _pct(m42['worst']) if m42 else '—'} | {_pct(d42['worst']) if d42 else '—'} | "
                         f"{_pct(s1['mean']) if s1 else '—'} |")
        lines += ['', '42 months then euphoria (mixed basket): ' + '; '.join(
            f"< {lv}: {_pct(b['long_exit']['mix']['mean'])} mean, worst {_pct(b['long_exit']['mix']['worst'])}, beats S&P "
            f"{b['long_exit']['mix']['beats_spx']}/{b['long_exit']['n']}"
            for lv, b in result['levels'].items() if (b.get('long_exit') or {}).get('mix'))]
        lines += [''] + [f"Signals under {lv}: " + ', '.join(b['signals']) for lv, b in result['levels'].items()] + ['']
    st = result.get('staged')
    if st and st.get('summary'):
        lines += ['## Buying in two halves: under 20, then under 10', '',
                  f'Mixed basket (half the ten largest, half all members) and the S&P 500 with the same timing; whole '
                  f'account including cash, from the first buy. staged_cash keeps the second half in cash if the '
                  f'thermometer does not reach 10 within {STAGE_WAIT} sessions; staged_fallback buys it then anyway.', '',
                  '| Plan | Months | Mix mean / worst | Mix worst fall (mean / worst) | S&P mean / worst | S&P worst fall (mean / worst) |',
                  '|---|---:|---|---|---|---|']
        for h, cell in st['summary'].items():
            months = {252: 12, LONG: 42}[int(h)]
            for name in STAGED:
                m, x = cell.get(f'{name}:mix'), cell.get(f'{name}:spx')
                if m and x:
                    lines.append(f"| {name} | {months} | {_pct(m['mean'])} / {_pct(m['worst'])} | {_pct(m['dd_mean'])} / "
                                 f"{_pct(m['dd_worst'])} | {_pct(x['mean'])} / {_pct(x['worst'])} | {_pct(x['dd_mean'])} / "
                                 f"{_pct(x['dd_worst'])} |")
        grid = result.get('staged_grid') or {}
        if grid:
            lines += ['', '### Second half under 18, 16, 15, 14, 12 or 10 (first half under 20, mixed basket)', '',
                      '| Second half under | Reached | 12 m mean / worst | 12 m worst fall mean | 42 m mean / worst | '
                      '42 m worst fall mean | Everything under that level: 42 m mean |', '|---:|---:|---|---:|---|---:|---:|']
            for lv, g in grid.items():
                y1, y42 = g['summary'].get('252') or {}, g['summary'].get(str(LONG)) or {}
                a1, a42, b42 = y1.get('staged_cash:mix'), y42.get('staged_cash:mix'), y42.get('all_at_10:mix')
                lines.append(f"| {lv} | {g['reached']}/{g['n']} | "
                             f"{_pct(a1['mean']) + ' / ' + _pct(a1['worst']) if a1 else '—'} | {_pct(a1['dd_mean']) if a1 else '—'} | "
                             f"{_pct(a42['mean']) + ' / ' + _pct(a42['worst']) if a42 else '—'} | {_pct(a42['dd_mean']) if a42 else '—'} | "
                             f"{_pct(b42['mean']) if b42 else '—'} |")
        lines += ['', 'Reached 10 within the wait: ' + ', '.join(
            f"{r['date']} → {r['reached_10'] or 'no'}" for r in st['rows']), '']
    if result.get('delays'):
        lines += ['## Timing sensitivity: buying 5 or 10 sessions later', '',
                  '| Entry | Months | Top 10 mean / worst | All members mean / worst | Mix mean / worst | S&P mean / worst |',
                  '|---|---:|---|---|---|---|']
        for lag, by_h in result['delays'].items():
            for h, cells in by_h.items():
                months = {252: 12, 882: 42}[int(h)]
                cell = lambda k: (f"{_pct(cells[k]['mean'])} / {_pct(cells[k]['worst'])} (n={cells[k]['n']})"
                                  if cells.get(k) else '—')
                lines.append(f"| +{lag} sessions | {months} | {cell('top10_weight')} | {cell('all_members')} | "
                             f"{cell('mix')} | {cell('spx')} |")
        lines.append('')
    lines += ['## Every signal', '',
              '| Signal | Heat | Priced / members | Broken | Busted | Basis | Top 10 (12 m) | Leaders (12 m) | Busted (12 m) | '
              'All (12 m) | S&P (12 m) | Account exit | Top 10 at exit |',
              '|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---|---:|']
    for e in result['events']:
        r = e['returns'].get('252') or {}
        b = e['breadth'] or {}
        x = e['euphoria_exit']
        lines.append(f"| {e['date']} | {e['heat']} | {b.get('priced', '—')}/{b.get('members', '—')} | "
                     f"{_share(b.get('broken'))} | {_share(b.get('busted'))} | {e['basis']} | "
                     f"{_pct(r.get('top10_weight'))} | {_pct(r.get('leaders'))} | {_pct(r.get('busted'))} | "
                     f"{_pct(r.get('all_members'))} | {_pct(r.get('spx'))} | {x['exit']} ({x['sessions']}) | "
                     f"{_pct(x.get('top10_weight'))} |")
    lines += ['', 'Top 10 on each signal: ' + '; '.join(
        f"{e['date']}: " + ', '.join(f"{t} {100 * w:.0f}%" for t, w in e['top10'][:5]) + '…' for e in result['events'])]
    lines += ['', '## Breadth check against Scion (their top dates)', '',
              'Our share of priced members broken/busted versus Scion\'s Bloomberg counts. A lower share here means '
              'missing (delisted) members, i.e. survivorship in our data.', '',
              '| Top | Members (ours / Scion) | Priced | Broken ours / Scion | Busted ours / Scion |',
              '|---|---|---:|---|---|']
    for date, c in result['breadth_checks'].items():
        o, s = c['ours'], c['scion']
        lines.append(f"| {date} | {o['members']} / {s['members']} | {o['priced']} | {100 * o['broken']:.0f}% / "
                     f"{100 * s['broken']:.0f}% | {100 * o['busted']:.0f}% / {100 * s['busted']:.0f}% |")
    now = result.get('breadth_now')
    if now:
        lines += ['', f"Now ({result['end']}): {100 * now['broken']:.0f}% broken, {100 * now['busted']:.0f}% busted "
                  f"({now['busted_names']} names, {now['busted_fresh_high']} of them with a ten-year high set in the "
                  f"last two years); thermometer {result['last_heat']['value'] if result.get('last_heat') else '—'}."]
    return '\n'.join(lines) + '\n'


# ------------------------------------------------------------------ data (GitHub Actions)
CHUNK, RETRIES, PAUSE = 100, 5, 30


def _yahoo(tickers):
    """(frame, throttled): throttled when yfinance reported a rate-limit error for any ticker."""
    import yfinance as yf
    raw = yf.download(sorted(tickers), start='1988-01-01', auto_adjust=False, progress=False, threads=True,
                      group_by='column')
    errors = ' '.join(str(e) for e in getattr(yf.shared, '_ERRORS', {}).values())
    return raw, ('RateLimit' in errors or 'Too Many Requests' in errors)


def download(tickers, fetch=_yahoo, chunk=CHUNK, retries=RETRIES, pause=PAUSE, sleep=None):
    """{'adj', 'split_close', 'volume'} for all tickers, fetched in chunks.

    Yahoo throttles bulk requests (run 45338277691: every one of 1,162 tickers came back 'Too Many Requests' right
    after the main backtest's own download). A chunk that yfinance reports as rate limited is fetched again after
    a growing pause; tickers that stay empty are left out (most are long delisted, which is not throttling)."""
    import time
    sleep = sleep or time.sleep
    parts = {name: [] for name in ('adj', 'split_close', 'volume')}
    tickers = sorted(tickers)
    for i in range(0, len(tickers), chunk):
        batch = tickers[i:i + chunk]
        raw = None
        for attempt in range(retries):
            raw, throttled = fetch(batch)
            if not throttled or attempt == retries - 1:
                break
            sleep(pause * (attempt + 1))
        if raw is None or not len(raw):
            continue
        for field, name in (('Adj Close', 'adj'), ('Close', 'split_close'), ('Volume', 'volume')):
            frame = raw[field]
            if isinstance(frame, pd.Series):
                frame = frame.to_frame(batch[0])
            frame.index = frame.index.tz_localize(None) if frame.index.tz is not None else frame.index
            parts[name].append(frame.round(4) if name != 'volume' else frame)
        sleep(2)                                        # be polite between chunks
    return {name: pd.concat(frames, axis=1) if frames else pd.DataFrame() for name, frames in parts.items()}


def index_series(sleep=None, retries=RETRIES, pause=PAUSE):
    """S&P 500 and VIX closes since 1988, retried while Yahoo throttles; raises if either stays empty."""
    import time
    import yfinance as yf
    sleep = sleep or time.sleep
    for attempt in range(retries):
        idx = yf.download(['^GSPC', '^VIX'], start='1988-01-01', auto_adjust=False, progress=False, threads=False,
                          group_by='column')['Close']
        if len(idx) and idx['^GSPC'].notna().sum() > 1000 and idx['^VIX'].notna().sum() > 1000:
            idx.index = idx.index.tz_localize(None) if idx.index.tz is not None else idx.index
            return idx['^GSPC'].dropna(), idx['^VIX'].dropna()
        sleep(pause * (attempt + 1))
    raise RuntimeError('Yahoo returned no S&P 500 / VIX history (rate limited?); keeping the previous results')


class CachedShares:
    """Shares outstanding in today's split terms, with each ticker's share history and splits fetched once.

    The timing-sensitivity runs look up the same companies on many nearby days; one request per ticker instead of
    one per (ticker, day) keeps Yahoo from throttling the run."""

    def __init__(self, fetch=None):
        self.fetch = fetch or self._yahoo
        self.cache = {}

    @staticmethod
    def _yahoo(ticker):
        import yfinance as yf
        t = yf.Ticker(ticker)
        s = t.get_shares_full(start='1998-01-01')
        splits = []
        for when, ratio in (t.splits.items() if t.splits is not None else ()):
            when = pd.Timestamp(when)
            splits.append((when.tz_localize(None) if when.tz is not None else when, float(ratio)))
        if s is not None and len(s):
            s.index = s.index.tz_localize(None) if getattr(s.index, 'tz', None) is not None else s.index
            s = s.sort_index()
        return s, splits

    def __call__(self, ticker, day):
        if ticker not in self.cache:
            try:
                self.cache[ticker] = self.fetch(ticker)
            except Exception:
                self.cache[ticker] = (None, [])
        s, splits = self.cache[ticker]
        if s is None or not len(s):
            return None
        s = s[(s.index <= day + pd.Timedelta(days=1)) & (s.index >= day - pd.Timedelta(days=550))]
        return float(s.iloc[-1]) * pb.split_factor(splits, day) if len(s) else None


def main():
    rows = pb.fetch_members()
    tickers = sorted({pb.yahoo(t) for d, members in rows if d >= pd.Timestamp('1998-01-01') for t in members})
    spx, vix = index_series()
    cutoff = pd.Timestamp.now(tz='America/New_York').normalize().tz_localize(None)
    spx = spx[spx.index < cutoff]
    data = download(tickers)
    priced = int(data['adj'].notna().any().sum()) if len(data['adj'].columns) else 0
    if priced < 0.5 * len(tickers):
        raise RuntimeError(f'Only {priced} of {len(tickers)} tickers priced (rate limited?); keeping the previous '
                           'results')
    result = study(spx, vix, data['adj'], data['split_close'], data['volume'], rows, CachedShares())
    result['tickers_requested'] = len(tickers)
    result['tickers_priced'] = int(data['adj'].notna().any().sum())
    OUT_JSON.parent.mkdir(exist_ok=True)
    OUT_JSON.write_text(json.dumps(result, indent=1, allow_nan=False) + '\n', encoding='utf-8')
    md = report(result) + (f"\nTickers ever in the index since 1998: {result['tickers_requested']}; with Yahoo prices: "
                           f"{result['tickers_priced']}.\n")
    OUT_MD.write_text(md, encoding='utf-8')
    print(md)


if __name__ == '__main__':
    main()
