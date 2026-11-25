"""Publish the paired EUR paper accounts from frozen entry quantities and dated closes."""
import json
import math
from datetime import date, timedelta

from paper_portfolio import ROUND2, ROUND2_FILES, US_CLOSE_UTC, evaluate


# This particular window spans one US holiday. Amsterdam trades on that Thursday.
# https://www.nyse.com/trade/hours-calendars
# https://www.euronext.com/en/trading/trading-hours-holidays
US_HOLIDAY = '2026-11-26'


def price(quotes, symbol, day):
    if day == US_HOLIDAY and symbol != 'WKL.AS':
        day = '2026-11-25'
    value = quotes.get(symbol, {}).get(day)
    return value if isinstance(value, (float, int)) and math.isfinite(value) and value > 0 else None


def prior_holdings(rules):
    """Previous account per the frozen round-two decision, including the TTD trim from 128."""
    previous = {h['yahoo']: h['shares_planned'] for h in rules['holdings'] if h['action'] != 'BUY'}
    previous.update({h['yahoo']: h['shares_planned'] for h in rules['discretionary']['holdings']})
    previous.update({h['yahoo']: h['shares_sold'] for h in rules['control_basket']['holdings']})
    previous['TTD'] = 128
    return previous


def trading_volume(previous, positions, quotes, entry, usd):
    target = {p['symbol']: p['shares'] for p in positions}
    volume, orders = 0., 0
    for symbol in previous.keys() | target.keys():
        change = abs(target.get(symbol, 0) - previous.get(symbol, 0))
        if change:
            close = price(quotes, symbol, entry)
            if close is None:
                return None, None
            volume += change * close * (1 if symbol == 'WKL.AS' else usd)
            orders += 1
    return volume, orders


def snapshot(docs, series, now, folder):
    plans = {ROUND2_FILES[d['_file']]: d for d in docs if d.get('_file') in ROUND2_FILES}
    rules = plans['rules']
    entry, exit_ = rules['entry_date'], rules['exit_date']
    until = now.date()
    if now.strftime('%H:%M') < US_CLOSE_UTC:
        until -= timedelta(days=1)
    day = date.fromisoformat(entry)
    sessions = []
    while day <= min(until, date.fromisoformat(exit_)):
        if day.weekday() < 5:
            sessions.append(day.isoformat())
        day += timedelta(days=1)
    quotes = {s: dict(rows) for s, rows in series.items()}
    path = folder / 'round2-settlement.json'
    settlement = json.loads(path.read_text()) if path.exists() else {}
    if settlement.get('round') != ROUND2 or settlement.get('as_of') != exit_:
        settlement = {}
    accounts = {}
    previous = prior_holdings(rules)
    for key, doc in plans.items():
        opening = evaluate(doc, series, date.fromisoformat(entry)) if sessions else {}
        rows = opening.get('holdings', []) + opening.get('discretionary', [])
        positions = []
        if opening.get('account_return_pct') is not None:
            for h in rows:
                positions.append(dict(symbol=h['yahoo'], shares=h['shares'], entry=h['entry_close'],
                                      currency=h.get('currency', 'USD'), cost=h['cost']))
        capital = doc.get('account_value_eur', doc['capital'])
        cash = opening.get('cash')
        volume, orders = trading_volume(previous, positions, quotes, entry, doc['fx']['USD']) if positions else (None, None)
        trail = []
        peak, high_day, trough, drawdown = capital, entry, entry, 0.
        worst_high = entry
        for session in sessions:
            missing = []
            stock_value = 0.
            for p in positions:
                close = price(quotes, p['symbol'], session)
                if close is None:
                    missing.append(p['symbol'])
                else:
                    stock_value += p['shares'] * close * (1 if p['currency'] == 'EUR' else doc['fx']['USD'])
            nav = None if missing or cash is None else stock_value + cash
            if session == entry and nav is not None:
                nav = capital
            trail.append(dict(day=session, nav=nav, missing=missing))
            if nav is None:
                continue
            if nav > peak:
                peak, high_day = nav, session
            loss = 100 * (1 - nav / peak)
            if loss > drawdown:
                drawdown, worst_high, trough = loss, high_day, session
        complete_path = bool(trail) and all(t['nav'] is not None for t in trail)
        fees = settlement.get(key, {})
        confirmed = all(type(fees.get(k)) in (int, float) and math.isfinite(fees[k])
                        for k in ('dividends_eur', 'interest_eur', 'costs_eur'))
        confirmed = confirmed and fees['costs_eur'] >= 0 and bool(str(fees.get('source') or '').strip())
        close_nav = trail[-1]['nav'] if sessions and sessions[-1] == exit_ else None
        net = (close_nav + fees['dividends_eur'] + fees['interest_eur'] - fees['costs_eur']
               if confirmed and close_nav is not None else None)
        mark = sessions[-1] if sessions else None
        for p in positions:
            p['close'] = price(quotes, p['symbol'], mark) if mark else None
        accounts[key] = dict(capital=capital, budget=doc['capital'], invested=opening.get('invested'),
                             cash=cash, positions=positions, days=trail, volume=volume, orders=orders,
                             drawdown=drawdown if complete_path else None,
                             peak_day=worst_high if complete_path else None, trough_day=trough if complete_path else None,
                             final_nav=close_nav, net_nav=net, settlement=fees if confirmed else None)
    benchmark = {d: price(quotes, '^GSPC', d) for d in sessions}
    return dict(schema=1, round=ROUND2, entry=entry, end=exit_, mark=sessions[-1] if sessions else None,
                built=now.isoformat(), fx=rules['fx']['USD'], accounts=accounts, benchmark=benchmark)
