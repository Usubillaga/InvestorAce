"""Experimental paper account "McClellan Thrust" (the user's request, 27 Nov 2026).

Rule: after the US close, rebuild the McClellan Oscillator from today's S&P 500 members (mcclellan_backtest.oscillator)
and read a thrust: the oscillator crosses above 0 within 20 sessions of a reading under the calibrated oversold level
(the latest value in backtests/mcclellan.json, refreshed by the monthly backtest). A thrust buys SPY at that close with
the whole account; the position is held 126 sessions from the latest thrust (a new thrust extends it) and sold at the
close of the last one. 10,000 USD, 0.1% per side, no stop. EXPERIMENTAL: the strategy failed the user's rule
(2010-2019 below buy and hold) although it beat buy and hold from all 20 start dates and every placebo run.

The account starts with the thrust of 25 Nov 2026; it is bought at the first close the script sees (never backdated).
"""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATE = ROOT / 'paper_trades' / 'mcclellan-thrust.json'
STUDY = ROOT / 'backtests' / 'mcclellan.json'
CAPITAL, COST, HOLD, LOOKBACK, SYMBOL = 10000., 0.001, 126, 20, 'SPY'
FIRST_SIGNAL = '2026-11-25'


def fresh():
    return dict(schema='mcclellan-thrust-v1', capital=CAPITAL, cash=CAPITAL, symbol=SYMBOL, shares=0., entry=None,
                bought=None, bought_signal=None, signal=FIRST_SIGNAL, hold_until=None, trades=[], marks=[], experimental=True,
                note='Failed the 3-period rule (2010-2019 below buy and hold); 20/20 starts and 0% placebo beat it.')


def thrusts(osc, level, lookback=LOOKBACK):
    """Dates of thrust closes: above 0 after a close at or under 0, with a reading under `level` in the prior window."""
    low = osc.rolling(lookback).min().shift()
    flags = (osc > 0) & (osc.shift() <= 0) & (low < level)
    return [str(d.date()) for d, f in flags.items() if f]


def advance(state, sessions, closes, signals):
    """sessions: completed session dates; closes: {date: SPY close}; signals: thrust dates. Returns events.
    The account trades from its first run's latest close on (state['start']); earlier sessions are never replayed."""
    events = []
    if not sessions:
        return events
    state.setdefault('start', sessions[-1])
    done = {m['date'] for m in state['marks']}
    for day in sessions:
        if day < state['start'] or day in done or day not in closes:
            continue
        price = closes[day]
        if day in signals and day > (state.get('signal') or ''):
            state['signal'] = day                      # a new thrust extends the holding
        k = sessions.index(state['signal']) if state['signal'] in sessions else None
        state['hold_until'] = sessions[k + HOLD] if k is not None and k + HOLD < len(sessions) else None
        if state['shares'] and state['hold_until'] and day >= state['hold_until']:
            state['cash'] = state['shares'] * price * (1 - COST)
            state['shares'] = 0.
            events.append(dict(type='SELL', date=day, price=price, signal=state['signal']))
        elif (not state['shares'] and state['signal'] and state.get('bought_signal') != state['signal']
              and day >= state['signal'] and state['hold_until'] is None):
            state['shares'] = state['cash'] * (1 - COST) / price
            state.update(cash=0., entry=price, bought=day, bought_signal=state['signal'])
            events.append(dict(type='BUY', date=day, price=price, signal=state['signal']))
        state['marks'].append(dict(date=day, equity=round(state['cash'] + state['shares'] * price, 2)))
    state['trades'] += events
    return events


def main():
    import pandas as pd
    import yfinance as yf
    import mcclellan_backtest as mb
    import panic_backtest as pb
    rows = pb.fetch_members()
    members = sorted({pb.yahoo(t) for t in rows[-1][1]})
    raw = yf.download(members + [SYMBOL], period='2y', auto_adjust=True, progress=False, threads=True)['Close']
    raw.index = raw.index.tz_localize(None) if raw.index.tz is not None else raw.index
    cutoff = pd.Timestamp.now(tz='America/New_York')
    done = (cutoff.hour, cutoff.minute) >= (16, 15)
    raw = raw[raw.index < cutoff.normalize().tz_localize(None) + pd.Timedelta(days=1 if done else 0)]
    close = raw[[m for m in members if m in raw.columns]]
    osc = mb.oscillator(close, pd.DataFrame(True, index=close.index, columns=close.columns))
    level = json.loads(STUDY.read_text())['calibrated']['level']
    sessions = [str(d.date()) for d in raw[SYMBOL].dropna().index]
    closes = {str(d.date()): float(v) for d, v in raw[SYMBOL].dropna().items()}
    state = json.loads(STATE.read_text()) if STATE.exists() else fresh()
    events = advance(state, sessions, closes, set(thrusts(osc, level)))
    state.update(oscillator=dict(date=str(osc.index[-1].date()), value=round(float(osc.iloc[-1]), 1), level=level),
                 updated=datetime.now(timezone.utc).isoformat(timespec='minutes'))
    STATE.write_text(json.dumps(state, indent=1) + '\n', encoding='utf-8')
    print(json.dumps(dict(events=events, oscillator=state['oscillator'], equity=state['marks'][-1:]), indent=1))


if __name__ == '__main__':
    main()
