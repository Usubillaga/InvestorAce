"""The public InvestorAce Market Thermometer on regular-session quotes."""
import math

import pandas as pd

import market_pulse
from .market import CAL, NY, SOURCE, UTC, session

METHOD = 'https://github.com/Usubillaga/InvestorAce/blob/main/market_pulse.py'


def score_session(samples, day, fear_greed=None):
    """Use each listing's own last 200 prices, as in the published thermometer."""
    histories = {}
    cutoff = pd.Timestamp(day)
    for symbol, pair in samples.items():
        if pair is None:
            continue
        prices = pair[0].loc[:cutoff].dropna().tail(200)
        # A stale intraday equity or a missing index bar cannot contribute to today's score.
        if not prices.empty and prices.index[-1] == cutoff:
            histories[symbol] = [(d.date().isoformat(), float(v)) for d, v in prices.items()]
    indices = {k: histories.pop(k, []) for k in ('^GSPC', '^VIX')}
    if len(indices['^GSPC']) < 200 or not indices['^VIX']:
        raise ValueError('Missing same-session index or 200-session S&P history')
    return market_pulse.summarize(indices, histories, fear_greed=fear_greed)


def observe(now, symbols, samples):
    now = now.astimezone(UTC)
    samples = {s: pair for s, pair in samples.items() if s in symbols or s in ('^GSPC', '^VIX')}
    indices = ['^GSPC', '^VIX']
    if not all(samples.get(s) for s in indices):
        raise ValueError('Current S&P 500 or VIX quote unavailable')
    if sum(samples.get(s) is not None for s in symbols) < .85 * len(symbols):
        raise ValueError('Market data unavailable for too much of the universe')
    today = now.astimezone(NY).date()
    previous = CAL.previous_session(str(today)).date()
    try:
        baseline = score_session(samples, previous)
    except ValueError:
        baseline = {}
    sentiment = market_pulse._fear_greed()
    current = score_session(samples, today, sentiment)
    breadth = current['components'].get('universe_above_ma200', {})
    count = breadth.get('count', 0)
    previous_count = baseline.get('components', {}).get('universe_above_ma200', {}).get('count', 0)
    if count < max(20, .8 * previous_count):
        raise ValueError('Insufficient current breadth coverage')
    value = current['heat']
    if value is None or not math.isfinite(value) or not 0 <= value <= 100:
        raise ValueError('Unusable Market Thermometer reading')
    stamps = [samples[s][1] for s in indices]
    window = session(now)
    return dict(indicator='market-pulse-v1', heat=value, as_of=min(stamps).isoformat(),
                quotes={s: samples[s][1].isoformat() for s in indices},
                components=len(current['components']), scores=current['components'], breadth_count=count,
                universe=len(symbols), session=str(today), close=window[1].isoformat(),
                previous_close=_finite(baseline.get('heat')), previous_session=str(previous), source=SOURCE + '%5EGSPC',
                method=METHOD)


def _finite(value):
    # The previous session's thermometer on its closes (without the day's Fear & Greed, which has no history).
    return float(value) if value is not None and math.isfinite(value) else None
