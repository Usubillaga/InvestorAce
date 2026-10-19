"""Daily trend/extension metrics and experimental display-only crossing events."""
from datetime import datetime, timezone

import pandas as pd

from evidence import digest
from integrity import positive_number

VERSION = 'experimental-timing-v2'
SIGNAL_VERSION = 'close-crossings-v1'
SIGNAL_LOOKBACK_SESSIONS = 20
SIGNAL_MIN_BARS = 201
PARAMETERS = {'sma': 200, 'ema': 21, 'atr': 14}
STALE_AFTER_CALENDAR_DAYS = 7


def _signal_observation():
    return dict(schema=SIGNAL_VERSION, status='UNAVAILABLE', event=None, date=None,
                reason='Timing is unavailable; no current signal can be computed.',
                lookback_sessions=SIGNAL_LOOKBACK_SESSIONS, latest_event=None)


def _calculate_signals(result, values, emas):
    """Versioned display events evaluated from causal indicator prefixes only."""
    signal = result['signal']
    signal['date'] = values[-1][0][:10]
    if len(values) < SIGNAL_MIN_BARS:
        signal['reason'] = 'At least 201 valid completed daily bars are required for signal comparisons.'
        return
    closes = [row[3] for row in values]

    def event_at(index):
        close, previous = closes[index], closes[index - 1]
        sma = sum(closes[index - 199:index + 1]) / 200
        previous_sma = sum(closes[index - 200:index]) / 200
        event = None
        if previous <= emas[index - 1] and close > emas[index] and close > sma:
            event = 'BUY'
        elif previous >= previous_sma and close < sma:
            event = 'SELL'
        if event is None:
            return None
        return dict(event=event, date=values[index][0][:10],
                    age_sessions=len(values) - index - 1,
                    close=close, ema21=emas[index], sma200=sma,
                    previous_close=previous, previous_ema21=emas[index - 1],
                    previous_sma200=previous_sma)

    latest = event_at(len(values) - 1)
    first = max(SIGNAL_MIN_BARS - 1, len(values) - SIGNAL_LOOKBACK_SESSIONS)
    for index in range(len(values) - 1, first - 1, -1):
        event = latest if index == len(values) - 1 else event_at(index)
        if event is not None:
            signal['latest_event'] = event
            break
    if result['status'] != 'AVAILABLE':
        signal['reason'] = 'Current signal suppressed because timing is ' + result['status'] + '.'
        return
    signal.update(status='AVAILABLE', event=latest['event'] if latest else 'NO_NEW_SIGNAL', reason='')


def unavailable(reason, as_of=None):
    stamp = pd.Timestamp(as_of if as_of is not None else datetime.now(timezone.utc))
    return dict(schema=VERSION, status='UNAVAILABLE', reason=reason,
                parameters=dict(PARAMETERS), source='Yahoo Finance / yfinance',
                price_basis='auto_adjust=True daily High/Low/Close',
                calculated_at=stamp.isoformat(), source_timezone=None,
                cutoff_policy='Strictly before the current exchange-local date',
                history_start=None, last_bar=None, bars=0, age_calendar_days=None,
                input_sha256=None, close=None, sma200=None, ema21=None,
                atr14=None, trend=None, distance_sma_pct=None, extension_atr=None,
                signal=_signal_observation())


def calculate(history, as_of=None):
    """Use only prior exchange-local dates, including after the current close.

    EMA(21) starts at the mean of the first 21 closes. Wilder ATR(14) starts
    at the mean of the first 14 true ranges; the first TR is High-Low.
    No row is dropped for a missing price and no price is forward-filled.
    Full retrieved-window values influence the recursive EMA and ATR seed.
    """
    result = unavailable('Adjusted daily OHLC history is unavailable.', as_of)
    now = pd.Timestamp(result['calculated_at'])
    if now.tzinfo is None:
        result['reason'] = 'Calculation time must include a timezone.'
        return result
    if not isinstance(history, pd.DataFrame) or history.empty:
        return result
    if not {'High', 'Low', 'Close'}.issubset(history.columns):
        result['reason'] = 'Adjusted daily OHLC requires High, Low and Close columns.'
        return result
    if (not isinstance(history.index, pd.DatetimeIndex) or history.index.tz is None
            or history.index.hasnans):
        result['reason'] = 'Daily bar timestamps must be valid and timezone-aware.'
        return result
    cutoff = now.tz_convert(history.index.tz).date()
    eligible = history.loc[history.index.date < cutoff, ['High', 'Low', 'Close']]
    result['source_timezone'] = str(history.index.tz)
    days = list(eligible.index.date)
    if any(a >= b for a, b in zip(days, days[1:])):
        result['reason'] = 'Daily bars must be chronological with unique exchange dates.'
        return result
    if eligible.empty:
        result['reason'] = 'No completed prior-session daily bars.'
        return result
    result.update(history_start=eligible.index[0].isoformat(),
                  last_bar=eligible.index[-1].isoformat(), bars=len(eligible),
                  age_calendar_days=(cutoff - days[-1]).days)
    values = []
    for stamp, row in eligible.iterrows():
        high, low, close = (positive_number(row[key]) for key in ('High', 'Low', 'Close'))
        if (None in (high, low, close) or low > high or not low <= close <= high):
            result['reason'] = 'Invalid OHLC at ' + stamp.isoformat() + '; no rows filled or discarded.'
            return result
        values.append((stamp.isoformat(), high, low, close))
    result['input_sha256'] = digest(values)
    if len(values) < PARAMETERS['sma']:
        result['reason'] = 'At least 200 valid completed daily bars are required.'
        return result
    closes = [row[3] for row in values]
    sma = sum(closes[-200:]) / 200
    ema = sum(closes[:21]) / 21
    emas = [None] * 20 + [ema]
    for close in closes[21:]:
        ema += (close - ema) * (2 / 22)
        emas.append(ema)
    ranges = []
    for i, (_, high, low, _) in enumerate(values):
        ranges.append(high - low if i == 0 else
                      max(high - low, abs(high - closes[i-1]), abs(low - closes[i-1])))
    atr = sum(ranges[:14]) / 14
    for value in ranges[14:]:
        atr = (13 * atr + value) / 14
    close = closes[-1]
    trend = 'ABOVE_SMA200' if close > sma else ('BELOW_SMA200' if close < sma else 'AT_SMA200')
    result.update(status='AVAILABLE', reason='', close=close, sma200=sma, ema21=ema,
                  atr14=atr, trend=trend, distance_sma_pct=100 * (close / sma - 1),
                  extension_atr=(close - ema) / atr if atr > 0 else None)
    if atr <= 0:
        result.update(status='PARTIAL', reason='ATR is zero; extension is unavailable.')
    if result['age_calendar_days'] > STALE_AFTER_CALENDAR_DAYS:
        result.update(status='STALE', reason=('Last bar is more than 7 calendar days old. '
                                            + result['reason']).strip())
    _calculate_signals(result, values, emas)
    return result
