"""Insider purchase clusters in the S&P 500 since 2006 (asked for on 27 Nov 2026 after COHR and FPS).

Rule tested: an issuer's open-market purchases (Form 4, code P, acquired) by at least MIN_BUYERS different insiders
within WINDOW calendar days, or at least MIN_VALUE dollars in total, counted by filing date (when the market could
know). Buy at the close of the first session after the filing that completes the cluster, one signal per issuer per
COOLDOWN days, 0.1% cost per side. Returns after 63, 126 and 252 sessions against the S&P 500 over the same
sessions. Only stocks that were in the S&P 500 on the signal day (point-in-time members, as in panic_history.py).

Data: SEC Insider Transactions Data Sets (quarterly, from 2006); prices from Yahoo, so members without prices are
left out (survivorship, as in the panic study). The rule passes only with at least MIN_SIGNALS signals and a
positive mean and median excess return at 126 sessions in each of the three periods. Research only.
"""
import io
import json
import statistics
import zipfile
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
OUT_JSON = ROOT / 'backtests' / 'insider_clusters.json'
OUT_MD = ROOT / 'backtests' / 'insider_clusters.md'
URL = 'https://www.sec.gov/files/structureddata/data/insider-transactions-data-sets/{y}q{q}_form345.zip'
AGENT = 'InvestorAce research bot research@example.com'
MIN_BUYERS, MIN_VALUE, WINDOW, COOLDOWN = 3, 1_000_000., 30, 90
HORIZONS = (63, 126, 252)
PERIODS = (('2006-01-01', '2012-12-31'), ('2013-01-01', '2019-12-31'), ('2020-01-01', None))
COST = 0.001
MIN_SIGNALS = 30


def purchases(sub, trans):
    """Open-market purchases: [symbol, filed, owner, value] from the data-set tables (DataFrames)."""
    t = trans[(trans['TRANS_CODE'] == 'P') & (trans['TRANS_ACQUIRED_DISP_CD'] == 'A')].copy()
    t['value'] = pd.to_numeric(t['TRANS_SHARES'], errors='coerce') * pd.to_numeric(t['TRANS_PRICEPERSHARE'],
                                                                                   errors='coerce')
    t = t.merge(sub[['ACCESSION_NUMBER', 'FILING_DATE', 'ISSUERTRADINGSYMBOL', 'RPTOWNERCIK']], on='ACCESSION_NUMBER')
    t['filed'] = pd.to_datetime(t['FILING_DATE'], format='%d-%b-%Y', errors='coerce')
    t['symbol'] = t['ISSUERTRADINGSYMBOL'].astype(str).str.strip().str.upper().str.replace('.', '-', regex=False)
    t = t.dropna(subset=['filed', 'value'])
    return t.groupby(['symbol', 'filed', 'RPTOWNERCIK'], as_index=False)['value'].sum().rename(
        columns={'RPTOWNERCIK': 'owner'})


def clusters(p, min_buyers=MIN_BUYERS, min_value=MIN_VALUE, window=WINDOW, cooldown=COOLDOWN):
    """[(symbol, filing date, buyers, value)]: the filing that completes a cluster, one per cooldown."""
    out = []
    for symbol, g in p.sort_values('filed').groupby('symbol'):
        last = None
        for day in sorted(g['filed'].unique()):
            day = pd.Timestamp(day)
            w = g[(g['filed'] > day - pd.Timedelta(days=window)) & (g['filed'] <= day)]
            buyers, value = w['owner'].nunique(), float(w['value'].sum())
            if (buyers >= min_buyers or value >= min_value) and (last is None or day - last > pd.Timedelta(days=cooldown)):
                out.append((symbol, day, int(buyers), value))
                last = day
    return out


def returns(signals, adj, spx, members, horizons=HORIZONS):
    """Per signal: entry at the first close after the filing; return and excess over the S&P 500."""
    idx = adj.index
    rows = []
    for symbol, filed, buyers, value in signals:
        if symbol not in adj.columns:
            continue
        i = idx.searchsorted(filed, side='right')
        if i >= len(idx) or not members.get(symbol, pd.Series(dtype=bool)).get(idx[i], False):
            continue
        entry = adj[symbol].iloc[i]
        if entry != entry:
            continue
        row = dict(symbol=symbol, filed=str(filed.date()), entry=str(idx[i].date()), buyers=buyers, value=value)
        for h in horizons:
            if i + h >= len(idx):
                row[str(h)] = None
                continue
            path = adj[symbol].iloc[i:i + h + 1].dropna()
            ret = path.iloc[-1] / entry * (1 - COST) / (1 + COST) - 1
            bench = spx.iloc[i + h] / spx.iloc[i] - 1
            row[str(h)] = dict(ret=float(ret), excess=float(ret - bench))
        rows.append(row)
    return rows


def summary(rows, h):
    xs = [r[str(h)] for r in rows if r.get(str(h))]
    if not xs:
        return dict(n=0)
    exc = [x['excess'] for x in xs]
    return dict(n=len(xs), mean=statistics.fmean(x['ret'] for x in xs), mean_excess=statistics.fmean(exc),
                median_excess=statistics.median(exc), beat=sum(e > 0 for e in exc) / len(exc))


def study(rows):
    periods = {}
    for lo, hi in PERIODS:
        sel = [r for r in rows if r['entry'] >= lo and (hi is None or r['entry'] <= hi)]
        periods[f'{lo[:4]}-{(hi or "now")[:4]}'] = {str(h): summary(sel, h) for h in HORIZONS}
    by = {}
    for name, test in (('3+ buyers', lambda r: r['buyers'] >= 3), ('$1M+, 1-2 buyers', lambda r: r['buyers'] < 3)):
        by[name] = {str(h): summary([r for r in rows if test(r)], h) for h in HORIZONS}
    passes = all(p['126'].get('n', 0) >= MIN_SIGNALS and p['126']['mean_excess'] > 0 and p['126']['median_excess'] > 0
                 for p in periods.values())
    return dict(schema='insider-clusters-v1', signals=len(rows), all={str(h): summary(rows, h) for h in HORIZONS},
                periods=periods, by_type=by, passes=passes, rule=dict(min_buyers=MIN_BUYERS, min_value=MIN_VALUE,
                window=WINDOW, cooldown=COOLDOWN), recent=rows[-15:])


def _pct(x):
    return '—' if x is None else f'{100 * x:+.1f}%'


def report(r):
    lines = ['# Insider purchase clusters (S&P 500 members, since 2006)', '',
             f"Signal: open-market purchases by {MIN_BUYERS}+ insiders within {WINDOW} days, or ${MIN_VALUE/1e6:.0f}M+ "
             f'in total, by filing date; buy at the next close; one signal per {COOLDOWN} days; 0.1% per side. '
             f"Passes only with {MIN_SIGNALS}+ signals and positive mean and median 6-month excess in every period.", '',
             f"Signals: {r['signals']} · passes: {'yes' if r['passes'] else 'no'}", '',
             '| Group | Horizon | n | Mean | Mean vs S&P | Median vs S&P | Beat S&P |', '|---|---|---:|---:|---:|---:|---:|']
    groups = [('All', r['all'])] + list(r['periods'].items()) + list(r['by_type'].items())
    for name, cells in groups:
        for h, s in cells.items():
            if s.get('n'):
                lines.append(f"| {name} | {h} sessions | {s['n']} | {_pct(s['mean'])} | {_pct(s['mean_excess'])} | "
                             f"{_pct(s['median_excess'])} | {100 * s['beat']:.0f}% |")
    return '\n'.join(lines) + '\n'


def fetch_quarters(start=2006, today=None, get=None):
    """Concatenated purchases from every available quarterly data set."""
    import time
    from urllib.request import Request, urlopen
    today = today or date.today()
    get = get or (lambda url: urlopen(Request(url, headers={'User-Agent': AGENT}), timeout=120).read())
    parts = []
    for y in range(start, today.year + 1):
        for q in range(1, 5):
            if (y, q) > (today.year, (today.month - 1) // 3 + 1):
                break
            try:
                z = zipfile.ZipFile(io.BytesIO(get(URL.format(y=y, q=q))))
                read = lambda n: pd.read_csv(z.open(next(f for f in z.namelist() if f.upper().endswith(n))),
                                             sep='\t', dtype=str, low_memory=False)
                sub, owner, trans = read('SUBMISSION.TSV'), read('REPORTINGOWNER.TSV'), read('NONDERIV_TRANS.TSV')
                sub = sub.merge(owner[['ACCESSION_NUMBER', 'RPTOWNERCIK']].drop_duplicates('ACCESSION_NUMBER'),
                                on='ACCESSION_NUMBER')
                parts.append(purchases(sub, trans))
            except Exception as exc:          # a missing quarter is reported, not fatal
                print(f'{y}q{q}: {type(exc).__name__}')
            time.sleep(0.2)
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=['symbol', 'filed', 'owner', 'value'])


def main():
    import panic_backtest as pb
    import panic_history as ph
    rows = pb.fetch_members()
    tickers = sorted({pb.yahoo(t) for d, m in rows if d >= pd.Timestamp('2005-01-01') for t in m})
    spx, _ = ph.index_series()
    data = ph.download(tickers)
    adj = data['adj'].reindex(spx.index)
    members = ph.membership(rows, adj.index, adj.columns)
    p = fetch_quarters()
    sig = [s for s in clusters(p) if s[0] in adj.columns]
    result = study(returns(sig, adj, spx, members))
    OUT_JSON.parent.mkdir(exist_ok=True)
    OUT_JSON.write_text(json.dumps(result, indent=1, allow_nan=False) + '\n', encoding='utf-8')
    OUT_MD.write_text(report(result), encoding='utf-8')
    print(report(result))


if __name__ == '__main__':
    main()
