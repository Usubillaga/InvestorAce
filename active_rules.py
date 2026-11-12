"""Claude's trading rules for the active paper account (rules v1.2; v1.1 fixed 2026-11-12 before the first order, v1.2
adds the user's moving-average, support/resistance and fast-drop rules the same day; v1.3 removes the
fast-drop rule again at the user's request, before it ever applied; v1.4 drops the resistance block and
the support priority because the evidence points the other way: stocks near their highs tend to keep
outperforming (George & Hwang 2004, The 52-Week High and Momentum Investing); v1.5 keeps only rules with
evidence: no sale before a report and no buy blackout (stocks earn more in announcement months: Frazzini &
Lamont 2007, Barber et al. 2013), no half sale at +25% and no 15-session time stop (momentum persists for
3-12 months: Jegadeesh & Titman 1993; selling winners early is the costly disposition effect: Odean 1998),
and a sale after 12 months because momentum profits reverse after about a year (Jegadeesh & Titman 1993).

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

VERSION = 'claude-rules-v1.5'
MAX_POSITIONS = 8
RISK_PER_TRADE = 0.01          # of equity, lost if the stop is hit
STOP = 0.08                    # O'Neil: cut every loss at 7-8%
STOP_CORRECTION = 0.05         # tighter while the market is below its 200-day average
MAX_POSITION = 0.20            # of equity
CASH_RESERVE = 0.03            # of capital, never spent
BREAKEVEN_AT = 0.10            # after +10% the stop moves to the entry price
TRAIL_AT, TRAIL = 0.20, 0.10   # after +20% the stop trails 10% under the highest close
FAST_GAIN, FAST_SESSIONS, HOLD_SESSIONS = 0.20, 15, 40   # O'Neil 8-week rule
PEAD_DAYS = 10                 # a report in the last 10 days with a positive reaction ranks first
PEAD_REACTION = 0.02           # close after the report vs close before it
MAX_PER_SECTOR = 2             # positions per sector
MAX_BUILD_AGE_DAYS = 4         # no orders from an older build
MAX_HOLD_SESSIONS = 252        # momentum reverses after about 12 months
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


def reaction(series, symbol, reported):
    """Close of the first session after the report over the last close before it, minus 1.

    Covers reports before the open and after the close. None while either close is missing."""
    day = reported.isoformat()
    rows = series.get(symbol) or []
    before = [c for d, c in rows if d < day]
    after = [c for d, c in rows if d > day]
    if not before or not after:
        return None
    return after[0] / before[-1] - 1


def confirmation(timing):
    """User's averages: above the 36-day = awakening, the 50-day = first confirmation,
    the 200-day = full confirmation. None when the build has no 36/50-day averages yet."""
    if 'sma36' not in timing:
        return None
    close = timing.get('close')
    levels = [timing.get('sma36'), timing.get('sma50'), timing.get('sma200')]
    if close is None or None in levels:
        return 'UNKNOWN'
    return sum(close > level for level in levels)


def build_age_days(record, today):
    captured = str((record.get('_evidence') or {}).get('captured_at') or '')[:10]
    try:
        return (today - date.fromisoformat(captured)).days
    except ValueError:
        return None


def plan(doc, record, series, today):
    """Orders for today's close and the reason for each decision."""
    today_s = today.isoformat()
    state = at.replay(doc, series, today_s)
    regime = market(record)
    stop = STOP_CORRECTION if regime == 'CORRECTION' else STOP
    orders, notes = [], [f'market {regime}; stop {stop:.0%}']
    age = build_age_days(record, today)
    if age is None or age > MAX_BUILD_AGE_DAYS:
        return dict(version=VERSION, date=today_s, market=regime, orders=[], equity=state['value'], cash=state['cash'],
                    notes=[f'no orders: the build is {age} days old (limit {MAX_BUILD_AGE_DAYS})'])
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
        first, count = None, 0
        for o in sorted((o for o in filled if o['ticker'] == ticker), key=lambda o: (o['fill_date'], o['id'])):
            if count == 0:
                first = o['fill_date']   # a new position starts
            count += o['shares'] if o['side'] == 'BUY' else -o['shares']
        path = _sessions(series, p['yahoo'], first, today_s)
        peak = max([c for _, c in path] + [close])
        gain, peak_gain = close / entry - 1, peak / entry - 1
        early = path[:FAST_SESSIONS + 1]
        fast = any(c / entry - 1 >= FAST_GAIN for _, c in early)
        holding = fast and len(path) <= HOLD_SESSIONS

        def sell(n, rule, why):
            orders.append(dict(side='SELL', ticker=ticker, shares=n, rule=rule, reason=why))

        floor = entry * (1 - stop)
        if peak_gain >= BREAKEVEN_AT:
            floor = max(floor, entry)
        if peak_gain >= TRAIL_AT and not holding:
            floor = max(floor, peak * (1 - TRAIL))
        if close <= floor:
            sell(p['shares'], 'STOP', f'close {close:.2f} at or below the stop {floor:.2f} '
                                      f'(entry {entry:.2f}, highest {peak:.2f})')
        elif holding:
            notes.append(f'{ticker}: 8-week hold (+{FAST_GAIN:.0%} within {FAST_SESSIONS} sessions), '
                         f'session {len(path)} of {HOLD_SESSIONS}')
        elif opp.get('label') in EXIT_LABELS:
            sell(p['shares'], 'LABEL', f'model label is now {opp["label"]}')
        elif timing.get('trend') == 'BELOW_SMA200':
            sell(p['shares'], 'TREND', 'close below the 200-day average')
        elif timing.get('sma50') and close < timing['sma50'] and gain < 0:
            sell(p['shares'], 'SMA50', 'close below the 50-day average while at a loss')
        elif len(path) >= MAX_HOLD_SESSIONS:
            sell(p['shares'], 'MAX_HOLD', f'{len(path)} sessions held; momentum fades after about a year')
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
    sectors = {}
    for ticker in set(held) - selling | (pending - set(held)):
        sector = _inputs(record, ticker).get('sector')
        sectors[sector] = sectors.get(sector, 0) + 1
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
        level = confirmation(timing)
        if level is not None and level != 3:          # v1.2: above the 36-, 50- and 200-day averages
            continue
        e = _earnings(record, ticker, today)
        pead = False
        if e['last'] is not None and 0 <= (today - e['last']).days <= PEAD_DAYS:
            move = reaction(series, inp.get('yf') or ticker, e['last'])
            if move is not None and move <= -PEAD_REACTION:
                notes.append(f'{ticker}: skipped, fell {move:.1%} on its report of {e["last"]}')
                continue
            pead = move is not None and move >= PEAD_REACTION   # unknown reaction: no priority
        candidates.append((not pead, -(opp.get('score') or 0), ticker, price, cur, pead, inp.get('sector')))
    for _, negscore, ticker, price, cur, pead, sector in sorted(candidates):
        if slots <= 0:
            break
        if sector and sectors.get(sector, 0) >= MAX_PER_SECTOR:   # an unknown sector is not capped
            notes.append(f'{ticker}: skipped, already {MAX_PER_SECTOR} positions in {sector}')
            continue
        unit = price * (1. if cur == doc['account_currency'] else doc['fx'][cur])
        n = math.floor(min(equity * RISK_PER_TRADE / (stop * unit), equity * MAX_POSITION / unit, cash / unit))
        if n < 1:
            notes.append(f'{ticker}: no cash for one share')
            continue
        cash -= n * unit
        slots -= 1
        sectors[sector] = sectors.get(sector, 0) + 1
        orders.append(dict(side='BUY', ticker=ticker, shares=n, rule='ENTRY',
                           reason=f'{"rose on its report, " if pead else ""}label score {-negscore:.2f}, '
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
