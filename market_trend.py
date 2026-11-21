"""Market-wide technical trend scan: breadth over time and stocks turning up. Information only.

Asked for on 21 Nov 2026: in a weak market, which stocks outside the universe are still in an uptrend or
are starting one? Runs in the market-scan workflow (GitHub Actions can reach SEC and Yahoo; this
sandbox cannot) and writes market-scan/trend.json. technical-scan.html shows it next to the universe scan.

Population: every NYSE/Nasdaq primary listing in the SEC ticker list with at least 210 daily closes, a
price of 5 USD or more and a median traded value of 10m USD a day over 50 sessions. Definitions:

* uptrend: close above the 50-day average, the 50-day above the 200-day, and the 200-day higher than
  20 sessions ago (Minervini's trend template, reduced).
* new uptrend: an uptrend today that was not one 20 sessions ago.
* relative strength: 63 and 126-session return minus the S&P 500's over the same sessions.
* breadth: share of the population above its 50 and 200-day average, and new 52-week highs and lows,
  for each of the last 120 sessions.

A technical list is an idea list, not a signal: the trading rules still need a model Buy label, which
only universe members have, and a market uptrend.
"""
import argparse
import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = 'market-trend-v1'
OUT = Path('market-scan') / 'trend.json'
MIN_PRICE, MIN_VALUE, MIN_BARS = 5., 10e6, 210
BREADTH_SESSIONS, LIST_SIZE = 120, 50


def _f(x, digits=2):
    return None if x is None or not math.isfinite(float(x)) else round(float(x), digits)


def analyse(close, volume, spx, names=None):
    """close/volume: DataFrames (dates x symbols), spx: Series. Returns the trend document body."""
    import pandas as pd
    close = close.sort_index()
    volume = volume.reindex_like(close)
    spx = spx.reindex(close.index).ffill()
    bars = close.notna().sum()
    value = (close * volume).rolling(50, min_periods=40).median()
    last = close.ffill().iloc[-1]
    liquid = [s for s in close.columns if bars.get(s, 0) >= MIN_BARS and (last.get(s) or 0) >= MIN_PRICE
              and (value[s].iloc[-1] if s in value else 0) >= MIN_VALUE]
    c = close[liquid].ffill(limit=3)
    sma50, sma200 = c.rolling(50).mean(), c.rolling(200).mean()
    trend = (c > sma50) & (sma50 > sma200) & (sma200 > sma200.shift(20))
    hi, lo = c.rolling(252, min_periods=200).max(), c.rolling(252, min_periods=200).min()
    valid = sma200.notna()
    n = valid.sum(axis=1).replace(0, float('nan'))
    breadth = pd.DataFrame({
        'pct50': 100 * ((c > sma50) & valid).sum(axis=1) / n,
        'pct200': 100 * ((c > sma200) & valid).sum(axis=1) / n,
        'uptrend': 100 * (trend & valid).sum(axis=1) / n,
        'highs': (c >= hi).sum(axis=1), 'lows': (c <= lo).sum(axis=1), 'count': n}).dropna().tail(BREADTH_SESSIONS)
    t = c.index[-1]

    def ret(series, k):
        s = series.dropna()
        return s.iloc[-1] / s.iloc[-1 - k] - 1 if len(s) > k and s.iloc[-1 - k] > 0 else None

    spx3, spx6 = ret(spx, 63), ret(spx, 126)
    rows = []
    for s in liquid:
        if pd.isna(sma200.at[t, s]) or pd.isna(c.at[t, s]):
            continue
        r3, r6 = ret(c[s], 63), ret(c[s], 126)
        now, before = bool(trend.at[t, s]), bool(trend[s].shift(20).iloc[-1]) if len(c) > 20 else False
        rows.append(dict(
            ticker=s, name=(names or {}).get(s), close=_f(c.at[t, s]),
            vs50=_f(100 * (c.at[t, s] / sma50.at[t, s] - 1), 1), vs200=_f(100 * (c.at[t, s] / sma200.at[t, s] - 1), 1),
            rs3=_f(100 * (r3 - spx3), 1) if None not in (r3, spx3) else None,
            rs6=_f(100 * (r6 - spx6), 1) if None not in (r6, spx6) else None,
            from_high=_f(100 * (c.at[t, s] / hi.at[t, s] - 1), 1) if not pd.isna(hi.at[t, s]) else None,
            value_musd=_f(value.at[t, s] / 1e6, 1), uptrend=now, new_uptrend=now and not before))

    def top(items, key):
        return sorted(items, key=lambda r: -(r[key] if r[key] is not None else -1e9))[:LIST_SIZE]

    return dict(
        schema=SCHEMA, as_of=t.date().isoformat(), population=len(rows),
        uptrend_count=sum(r['uptrend'] for r in rows), new_uptrend_count=sum(r['new_uptrend'] for r in rows),
        breadth=[dict(date=d.date().isoformat(), **{k: _f(v, 1) for k, v in row.items()})
                 for d, row in breadth.iterrows()],
        new_uptrends=top([r for r in rows if r['new_uptrend']], 'rs3'),
        leaders=top([r for r in rows if r['uptrend']], 'rs6'))


def _download(symbols, log=print, chunk=100, pause=2.):
    import pandas as pd
    import yfinance as yf
    closes, volumes = {}, {}
    for i in range(0, len(symbols), chunk):
        part = symbols[i:i + chunk]
        for attempt in range(3):
            try:
                frame = yf.download(part, period='14mo', interval='1d', auto_adjust=True, actions=False,
                                    progress=False, group_by='ticker', threads=True)
                break
            except Exception as exc:          # one failed batch must not end the scan
                log(f'Yahoo batch {i // chunk} failed ({type(exc).__name__}); retry {attempt + 1}')
                time.sleep(5 * (attempt + 1))
                frame = None
        for s in part:
            try:
                sub = frame[s] if frame is not None and len(part) > 1 else frame
                closes[s], volumes[s] = sub['Close'], sub['Volume']
            except (KeyError, TypeError):
                continue
        time.sleep(pause)
    close, volume = pd.DataFrame(closes), pd.DataFrame(volumes)
    close.index = close.index.tz_localize(None) if close.index.tz is not None else close.index
    volume.index = close.index
    return close, volume


def main(argv=None):
    import market_universe as mu
    import yfinance as yf
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default=str(OUT))
    args = parser.parse_args(argv)
    client = mu.SecClient(os.environ.get('SEC_USER_AGENT'))
    listing = mu.parse_universe(client.get_json(mu.TICKERS_URL))
    symbols = [r['yahoo'] for r in listing]
    names = {r['yahoo']: r['name'] for r in listing}
    print(f'{len(symbols)} SEC listings; downloading 14 months of daily closes')
    close, volume = _download(symbols)
    spx = yf.download('^GSPC', period='14mo', interval='1d', auto_adjust=True, progress=False)['Close']
    spx = spx.iloc[:, 0] if getattr(spx, 'ndim', 1) == 2 else spx
    spx.index = spx.index.tz_localize(None) if spx.index.tz is not None else spx.index
    cutoff = datetime.now(timezone.utc).date().isoformat()   # drop a partial bar of a running session
    keep = close.index.strftime('%Y-%m-%d') < cutoff
    close, volume = close[keep], volume[keep]
    spx = spx[spx.index.strftime('%Y-%m-%d') < cutoff]
    doc = analyse(close, volume, spx, names)
    if doc['population'] < 300:
        print(f'Only {doc["population"]} liquid symbols priced; keeping the previous file', file=sys.stderr)
        return 1
    doc['generated_at'] = datetime.now(timezone.utc).isoformat(timespec='minutes')
    doc['listings'] = len(symbols)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(doc, indent=1, allow_nan=False) + '\n', encoding='utf-8')
    print(f'{doc["population"]} liquid symbols, {doc["uptrend_count"]} in an uptrend, '
          f'{doc["new_uptrend_count"]} new; breadth above 200-day {doc["breadth"][-1]["pct200"]}%')
    return 0


if __name__ == '__main__':
    sys.exit(main())
