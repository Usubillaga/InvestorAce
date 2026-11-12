"""Claude's trading rules for the active paper account (rules v1, fixed 2026-11-12).

The rules are written down before the first order and applied mechanically, so the
account measures these rules, not ad-hoc decisions. Sources (from memory of the
books, not re-checked): William O'Neil, How to Make Money in Stocks (market
direction, 7-8% loss limit, 20-25% profit taking, 8-week hold, no earnings without
a cushion); Mark Minervini, Trade Like a Stock Market Wizard (trend template:
above the 200-day average, do not chase extended stocks); Alexander Elder and Van
Tharp (risk a fixed small share of equity per trade); Bernard & Thomas (1989),
post-earnings-announcement drift (strength after a report tends to persist).

The fundamental filter is InvestorAce's own label: only Buy or Strong Buy is bought.
Decisions use the latest committed build (yesterday's close); orders fill at the
close of the session they are sent in (active_trading.py). Paper only.
"""
import json
import math
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import active_trading as at
from earnings_view import status as earnings_status

VERSION = 'claude-rules-v1'
MAX_POSITIONS = 8
RISK_PER_TRADE = 0.01          # of equity, lost if the stop is hit
STOP = 0.08                    # O'Neil: cut every loss at 7-8%
STOP_CORRECTION = 0.05         # tighter while the market is below its 200-day average
MAX_POSITION = 0.20            # of equity
CASH_RESERVE = 0.03            # of capital, never spent
BREAKEVEN_AT = 0.10            # after +10% the stop moves to the entry price
TRAIL_AT, TRAIL = 0.20, 0.10   # after +20% the stop trails 10% under the highest close
TAKE_PROFIT = 0.25             # sell half at +25% (once)
FAST_GAIN, FAST_SESSIONS, HOLD_SESSIONS = 0.20, 15, 40   # O'Neil 8-week rule
EARNINGS_CUSHION = 0.10        # hold through a report only with +10% or more
EARNINGS_EXIT_DAYS = 3         # calendar days before a report
EARNINGS_BLACKOUT_DAYS = 5     # no new position this close to a report
PEAD_DAYS = 10                 # a report in the last 10 days ranks a candidate first
TIME_STOP_SESSIONS, TIME_STOP_GAIN = 15, 0.02
MAX_EXTENSION_ATR = 3.0        # do not chase more than 3 ATR above the 21-day average
COOLDOWN_SESSIONS = 10         # no re-entry right after a sale
BUY_LABELS = ('Buy', 'Strong Buy')
EXIT_LABELS = ('Hold Negative', 'Sell')


def market(record):
    """UPTREND when the S&P 500 is above its 200-day average, otherwise CORRECTION (O'Neil's M)."""
    comp = ((((record.get('_evidence') or {}).get('macro') or {}).get('pulse') or {}).get('components') or {})
    value = (comp.get('sp500_ma200') or {}).get('value')
    if value is None:
        return 'UNKNOWN'
    return 'UPTREND' if value > 0 else 'CORRECTION'


def _sessions(series, symbol, start, end):
    return [r for r in series.get(symbol) or [] if start <= r[0] <= end]


def _inputs(record, ticker):
    return ((record.get('_evidence') or {}).get('inputs') or {}).get(ticker) or {}


def _earnings(record, ticker, today):
    return earnings_status(_inputs(record, ticker), today)


def plan(doc, record, series, today):
    """Orders for today's close and the reason for each decision."""
    today_s = today.isoformat()
    state = at.replay(doc, series, today_s)
    regime = market(record)
    stop = STOP_CORRECTION if regime == 'CORRECTION' else STOP
    orders, notes = [], [f'market {regime}; stop {stop:.0%}']
    filled = [o for o in state['orders'] if o['status'] == 'FILLED']
    pending = {o['ticker'] for o in state['orders'] if o['status'] == 'PENDING'}
    held = {p['ticker']: p for p in state['positions']}

    for ticker, p in sorted(held.items()):
        if ticker in pending:
            notes.append(f'{ticker}: order pending, no decision')
            continue
        opp = (record.get(ticker) or {}).get('opportunity') or {}
        timing = _inputs(record, ticker).get('timing') or {}
        rate = 1. if p['currency'] == doc['account_currency'] else doc['fx'][p['currency']]
        entry = p['cost'] / (p['shares'] * rate)
        close = p['last_close']
        if close is None:
            notes.append(f'{ticker}: no close, no decision')
            continue
        first, partial, count = None, False, 0
        for o in sorted((o for o in filled if o['ticker'] == ticker), key=lambda o: (o['fill_date'], o['id'])):
            if count == 0:
                first, partial = o['fill_date'], False   # a new position starts
            count += o['shares'] if o['side'] == 'BUY' else -o['shares']
            partial = partial or o['side'] == 'SELL'
        path = _sessions(series, p['yahoo'], first, today_s)
        peak = max([c for _, c in path] + [close])
        gain, peak_gain = close / entry - 1, peak / entry - 1
        early = path[:FAST_SESSIONS + 1]
        fast = any(c / entry - 1 >= FAST_GAIN for _, c in early)
        holding = fast and len(path) <= HOLD_SESSIONS
        nxt = _earnings(record, ticker, today)['next']

        def sell(n, rule, why):
            orders.append(dict(side='SELL', ticker=ticker, shares=n, rule=rule, reason=why))

        floor = entry * (1 - stop)
        if peak_gain >= BREAKEVEN_AT:
            floor = max(floor, entry)
        if peak_gain >= TRAIL_AT and not holding:
            floor = max(floor, peak * (1 - TRAIL))
        if opp.get('label') in EXIT_LABELS:
            sell(p['shares'], 'LABEL', f'model label is now {opp["label"]}')
        elif close <= floor:
            sell(p['shares'], 'STOP', f'close {close:.2f} at or below the stop {floor:.2f} '
                                      f'(entry {entry:.2f}, highest {peak:.2f})')
        elif holding:
            notes.append(f'{ticker}: 8-week hold (+{FAST_GAIN:.0%} within {FAST_SESSIONS} sessions), '
                         f'session {len(path)} of {HOLD_SESSIONS}')
        elif gain >= TAKE_PROFIT and not partial and p['shares'] >= 2:
            sell(p['shares'] // 2, 'TAKE_PROFIT', f'+{gain:.1%}: half sold, the rest trails')
        elif nxt is not None and (nxt - today).days <= EARNINGS_EXIT_DAYS and gain < EARNINGS_CUSHION:
            sell(p['shares'], 'EARNINGS', f'report on {nxt} without a +{EARNINGS_CUSHION:.0%} cushion '
                                          f'({gain:+.1%})')
        elif timing.get('trend') == 'BELOW_SMA200':
            sell(p['shares'], 'TREND', 'close below the 200-day average')
        elif len(path) >= TIME_STOP_SESSIONS and gain < TIME_STOP_GAIN:
            sell(p['shares'], 'TIME_STOP', f'{len(path)} sessions and only {gain:+.1%}')
        else:
            notes.append(f'{ticker}: hold ({gain:+.1%}, stop {floor:.2f})')

    selling = {o['ticker'] for o in orders if o['side'] == 'SELL' and o['shares'] == held[o['ticker']]['shares']}
    slots = MAX_POSITIONS - (len(held) - len(selling)) - len(pending - set(held))
    if regime != 'UPTREND':
        notes.append('no new positions: the market is not in an uptrend')
        slots = 0
    equity = state['value'] if state['value'] is not None else state['cash']
    cash = state['cash'] - doc['capital'] * CASH_RESERVE
    recent_sales = {o['ticker'] for o in filled if o['side'] == 'SELL' and
                    len(_sessions(series, o['yahoo'], o['fill_date'], today_s)) <= COOLDOWN_SESSIONS}
    candidates = []
    for ticker in sorted(k for k in record if not k.startswith('_') and isinstance(record[k], dict)):
        if ticker in held or ticker in pending or ticker in recent_sales:
            continue
        opp = record[ticker].get('opportunity') or {}
        inp = _inputs(record, ticker)
        timing = inp.get('timing') or {}
        cur = inp.get('cur')
        price = opp.get('price')
        if (opp.get('label') not in BUY_LABELS or opp.get('withdrawn') or not price
                or (cur != doc['account_currency'] and cur not in doc['fx'])):
            continue
        if timing.get('status') != 'AVAILABLE' or timing.get('trend') != 'ABOVE_SMA200':
            continue
        ext = timing.get('extension_atr')
        if ext is None or ext < 0 or ext > MAX_EXTENSION_ATR:
            continue
        e = _earnings(record, ticker, today)
        if e['next'] is not None and (e['next'] - today).days <= EARNINGS_BLACKOUT_DAYS:
            continue
        pead = e['last'] is not None and 0 <= (today - e['last']).days <= PEAD_DAYS
        candidates.append((not pead, -(opp.get('score') or 0), ticker, price, cur, pead))
    for _, negscore, ticker, price, cur, pead in sorted(candidates)[:max(slots, 0)]:
        unit = price * (1. if cur == doc['account_currency'] else doc['fx'][cur])
        n = math.floor(min(equity * RISK_PER_TRADE / (stop * unit), equity * MAX_POSITION / unit, cash / unit))
        if n < 1:
            notes.append(f'{ticker}: no cash for one share')
            continue
        cash -= n * unit
        orders.append(dict(side='BUY', ticker=ticker, shares=n, rule='ENTRY',
                           reason=f'{"post-earnings drift, " if pead else ""}label score {-negscore:.2f}, '
                                  f'above the 200-day average, not extended; about €{n * unit:,.0f}'))
    return dict(version=VERSION, date=today_s, market=regime, orders=orders, notes=notes,
                equity=equity, cash=state['cash'])


def title(order):
    return f'paper-order: {order["side"]} {order["shares"]} {order["ticker"]}'


def main(argv=None):
    import argparse
    from evidence import current_build
    from paper_portfolio import merge_series
    parser = argparse.ArgumentParser(description='Plan today\'s orders for the active paper account.')
    parser.add_argument('--today', help='YYYY-MM-DD (default: today UTC)')
    args = parser.parse_args(argv)
    today = date.fromisoformat(args.today) if args.today else datetime.now(timezone.utc).date()
    root = Path(__file__).resolve().parent
    build = current_build(root / 'history')
    doc = at.load()
    snapshots = [json.loads(p.read_text(encoding='utf-8'))
                 for p in sorted((root / 'history' / 'runs').glob('*.json'))
                 if p.name[:8] >= (date.fromisoformat(doc['opened']) - timedelta(days=90)).strftime('%Y%m%d')]
    result = plan(doc, build['record'], merge_series(snapshots + [build['record']]), today)
    print(json.dumps(dict(result, titles=[title(o) for o in result['orders']]), indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
