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
HORIZONS = (63, 126, 252, 378)
TEN_YEARS = 2520
BASKETS = ('top10_weight', 'leaders', 'broken', 'busted', 'all_members', 'spx')
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
        row['returns'][str(h)] = cell
    end = euphoria_exit(index, start, heat)
    row['euphoria_exit'] = dict(exit=str(index[end].date()), sessions=int(end - start),
                                top10_weight=basket_return(adj, top, top_w, start, end),
                                **{k: basket_return(adj, v, [1.] * len(v), start, end) if v else None
                                   for k, v in groups.items()},
                                spx=float(spx.loc[index[end]] / spx.loc[index[start]] - 1)
                                if index[end] in spx.index and index[start] in spx.index else None)
    return row


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
        out[str(h)] = cell
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
                last_heat=dict(date=str(last.index[-1].date()), value=round(float(last.iloc[-1]), 1)) if len(last) else None,
                breadth_now=breadth_on(index[-1], adj, dd, members, recent_high))


# ------------------------------------------------------------------ report
def _pct(x, digits=1):
    return '—' if x is None else f'{100 * x:+.{digits}f}%'


def report(result):
    lines = ['# Panic buys since 2000', '',
             f"Thermometer panic signals {result['start']} → {result['end']}: {result['signals']} first panic closes. "
             'Members as on each day (S&P 500), bought at the next close, 0.1% per side, delisted names carried at '
             'their last price. Survivorship: members without Yahoo prices are left out (counted per signal), so '
             'early busted baskets look better than they were.', '']
    names = dict(top10_weight='Top 10 by weight', leaders='Leaders (<20% off high)', broken='Broken (20-40%)',
                 busted='Busted (>40%)', all_members='All members, equal', spx='S&P 500')
    for h, cells in result['summary'].items():
        months = {63: 3, 126: 6, 252: 12, 378: 18}[int(h)]
        lines += [f'## {months} months ({h} sessions)', '',
                  '| Basket | Signals | Mean | Median | Worst | Positive | Beats S&P |', '|---|---:|---:|---:|---:|---:|---:|']
        for k in BASKETS:
            c = cells.get(k)
            if c:
                lines.append(f"| {names[k]} | {c['n']} | {_pct(c['mean'])} | {_pct(c['median'])} | {_pct(c['worst'])} | "
                             f"{c['positive']}/{c['n']} | {'—' if k == 'spx' else str(c['beats_spx']) + '/' + str(c['n'])} |")
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
                     f"{_pct(b.get('broken'), 0)} | {_pct(b.get('busted'), 0)} | {e['basis']} | "
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
def download(tickers):
    import yfinance as yf
    raw = yf.download(sorted(tickers), start='1988-01-01', auto_adjust=False, progress=False, threads=True,
                      group_by='column')
    out = {}
    for field, name in (('Adj Close', 'adj'), ('Close', 'split_close'), ('Volume', 'volume')):
        frame = raw[field]
        frame.index = frame.index.tz_localize(None) if frame.index.tz is not None else frame.index
        out[name] = frame.round(4) if name != 'volume' else frame
    return out


def main():
    import yfinance as yf
    rows = pb.fetch_members()
    tickers = sorted({pb.yahoo(t) for d, members in rows if d >= pd.Timestamp('1998-01-01') for t in members})
    idx = yf.download(['^GSPC', '^VIX'], start='1988-01-01', auto_adjust=False, progress=False, threads=False,
                      group_by='column')['Close']
    idx.index = idx.index.tz_localize(None) if idx.index.tz is not None else idx.index
    cutoff = pd.Timestamp.now(tz='America/New_York').normalize().tz_localize(None)
    spx, vix = idx['^GSPC'].dropna(), idx['^VIX'].dropna()
    spx = spx[spx.index < cutoff]
    data = download(tickers)
    result = study(spx, vix, data['adj'], data['split_close'], data['volume'], rows, pb.yahoo_shares)
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
