"""Intraday observations for the four-component InvestorAce index-leader thermometer."""
import math
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from urllib.parse import quote
from zoneinfo import ZoneInfo

import exchange_calendars as xcals
import pandas as pd
import requests

from panic_backtest import heat
from .weights import HEADERS

NY = ZoneInfo('America/New_York')
UTC = timezone.utc
CAL = xcals.get_calendar('XNYS')
MAX_AGE = timedelta(minutes=25)
SOURCE = 'https://query1.finance.yahoo.com/v8/finance/chart/'
METHOD = 'https://github.com/Usubillaga/InvestorAce/blob/main/panic_backtest.py'


def session(now):
    day = now.astimezone(NY).date().isoformat()
    if CAL.is_session(day):
        opening = CAL.session_open(day).to_pydatetime()
        closing = CAL.session_close(day).to_pydatetime()
        if opening <= now < closing:
            return opening, closing
    return None


def chart(symbol):
    url = SOURCE + quote(symbol, safe='')
    response = requests.get(url, params={'range': '1y', 'interval': '1d'}, headers=HEADERS, timeout=9)
    response.raise_for_status()
    payload = response.json()['chart']['result'][0]
    meta = payload['meta']
    if meta['symbol'].upper() != symbol.upper():
        raise ValueError('Unexpected quote symbol')
    zone = ZoneInfo(meta['exchangeTimezoneName'])
    days = pd.to_datetime(payload['timestamp'], unit='s', utc=True).tz_convert(zone).normalize().tz_localize(None)
    close = pd.Series(payload['indicators']['quote'][0]['close'], index=days, dtype=float)
    return close[~close.index.duplicated(keep='last')], meta


def usable_series(symbol, now=None):
    close, meta = chart(symbol)
    now = now or datetime.now(UTC)
    stamp = datetime.fromtimestamp(meta['regularMarketTime'], UTC)
    day = now.astimezone(NY).date()
    last = pd.Timestamp(day)
    close = close.loc[:last].copy()
    fresh = timedelta(0) <= now - stamp <= MAX_AGE
    # A non-US market may already be closed. Its timestamp must be near its own close today.
    local_end = datetime.fromtimestamp(meta['currentTradingPeriod']['regular']['end'], UTC)
    foreign_close = (symbol not in ('^GSPC', '^VIX') and now >= local_end and
                     abs(local_end - stamp) <= MAX_AGE and local_end.astimezone(NY).date() == day)
    current = (stamp.astimezone(NY).date() == day and stamp <= now and (fresh or foreign_close)
               and math.isfinite(meta['regularMarketPrice']) and meta['regularMarketPrice'] > 0)
    if symbol in ('^GSPC', '^VIX'):
        window = session(now)
        if not current or not window or stamp < window[0]:
            raise ValueError('Stale or premarket index: ' + symbol)
    close.loc[last] = meta['regularMarketPrice'] if current else float('nan')
    return close, stamp


def observe(now, symbols):
    now = now.astimezone(UTC)
    indices = ['^GSPC', '^VIX']
    # Select a new reference time after the HTTP fetch so ticking quotes are not
    # rejected just because their timestamp is a few seconds after the job began.
    def get(symbol):
        try:
            return symbol, usable_series(symbol)
        except (requests.RequestException, ValueError, KeyError, IndexError, TypeError, OSError):
            return symbol, None

    with ThreadPoolExecutor(max_workers=8) as pool:
        samples = dict(pool.map(get, indices + sorted((set(symbols) | {'EURUSD=X'}) - set(indices))))
    if not all(samples.get(s) for s in indices):
        raise ValueError('Current S&P 500 or VIX quote unavailable')
    equities = {s: pair[0] for s, pair in samples.items() if s in symbols and pair}
    if len(equities) < .85 * len(symbols):
        raise ValueError('Market data unavailable for too much of the universe')
    spx, vix = (samples[s][0].dropna() for s in indices)
    # collect(intraday=True) also downloads EURUSD=X for portfolio conversion.
    # Its calendar is part of the unfilled daily grid consumed by heat().
    if not samples.get('EURUSD=X'):
        raise ValueError('Missing reference trading calendar')
    grid = samples['EURUSD=X'][0].index.union(spx.index).union(vix.index)
    if len(spx) < 201:
        raise ValueError('Insufficient S&P 500 history')
    close = pd.DataFrame(equities).round(4)
    close = close.reindex(close.index.union(grid)).sort_index()
    today = pd.Timestamp(now.astimezone(NY).date())
    previous = pd.Timestamp(CAL.previous_session(str(today.date())).date())
    valid = close.rolling(200).count().eq(200).sum(axis=1)
    count = int(valid.get(today, 0))
    # A multinational universe can have no complete 200-row windows even
    # with full data (different holidays). The strategy then uses exactly
    # three scores. Reject a feed outage that would mimic this condition.
    expected = int(close.loc[:today].iloc[-200:-1].notna().all().sum())
    if (expected >= 20 and count < max(20, .8 * expected)) or close.loc[today].count() < .75 * len(symbols):
        raise ValueError('Insufficient current breadth quotes')
    values = heat(spx.round(4), vix.round(4), close)
    value = float(values.loc[today])
    if not math.isfinite(value) or not 0 <= value <= 100:
        raise ValueError('Unusable thermometer reading')
    stamps = [samples[s][1] for s in indices]
    baseline = values.get(previous)
    window = session(now)
    return dict(heat=value, as_of=min(stamps).isoformat(), quotes=dict(zip(indices, (t.isoformat() for t in stamps))),
                breadth_count=count, components=4 if count >= 20 else 3, universe=len(symbols), session=str(today.date()), close=window[1].isoformat(),
                previous_close=float(baseline) if pd.notna(baseline) else None,
                previous_session=str(previous.date()), source=SOURCE + '%5EGSPC', method=METHOD)
