"""Prospective, independently funded strategy comparison. One ledger owned by publish_build."""
import json
import logging
from datetime import date, datetime, timedelta, timezone
from html import escape
from pathlib import Path

import opportunity
from active_rules import confirmation, market, plan, swing_entry
import active_trading
from paper_portfolio import merge_series
from evidence import canonical, committed_builds, current_build
from integrity import atomic_json
from war_scenario import shell

FILE = Path('history/codex_trading.json')
PAGE = Path('codex-trading.html')
CAPITAL, COST = 10000., .001
SWING_ENTRY_POLICY = 'fundamental-and-technical-v1'
ENTRY_PAUSED = 'New swings require fundamental and technical confirmation.'
NAMES = {'timing': 'Codex active · opportunity + timing', 'opportunity': 'Opportunity only',
         'fundamental': 'Fundamentals only'}


def fresh():
    return dict(version=1, decisions=[], accounts={
        key: dict(cash=CAPITAL, holdings={}, orders=[], turnover=0., fees=0.) for key in NAMES})


def value(account):
    return account['cash'] + sum(p['local_value'] / p['fx'] for p in account['holdings'].values())


def settle(account, bars, rates, now):
    """Apply each verified return once and before that session's closing fills."""
    pending = [o for o in account['orders'] if o['status'] == 'Pending']
    symbols = {o['symbol'] for o in pending} | {p['symbol'] for p in account['holdings'].values()}
    days = sorted({d for s in symbols for d in bars.get(s, {})})
    for day in days:
        for p in account['holdings'].values():
            bar = bars.get(p['symbol'], {}).get(day)
            if bar and day > p['day'] and bar[0] == p['day']:
                p['local_value'] *= bar[1]
                p['day'] = day
            if day >= p['fx_day'] and (p['currency'] == 'EUR' or day in rates):
                p.update(fx=1. if p['currency'] == 'EUR' else rates[day], fx_day=day)
        for o in pending:
            if o['status'] != 'Pending' or not o['submitted'][:10] < day <= o['expires']:
                continue
            symbol, ticker = o['symbol'], o['ticker']
            bar = bars.get(symbol, {}).get(day)
            if not bar:
                continue
            rate = 1. if o['currency'] == 'EUR' else rates.get(day)
            if not rate:
                o.update(status='Rejected', detail='Missing execution-date EUR/USD', day=day)
                continue
            if o['side'] == 'Buy':
                amount = o['euros']
                if amount * (1 + COST) > account['cash'] or ticker in account['holdings']:
                    o.update(status='Rejected', detail='Insufficient cash or duplicate holding', day=day)
                    continue
                account['cash'] -= amount * (1 + COST)
                account['holdings'][ticker] = dict(symbol=symbol, sector=o['sector'], currency=o['currency'],
                    day=day, fx_day=day, local_value=amount * rate, fx=rate)
            else:
                p = account['holdings'].get(ticker)
                if not p or p['day'] != day:
                    o.update(status='Rejected', detail='Unreconciled total-return history', day=day)
                    continue
                amount = p['local_value'] / rate
                account['cash'] += amount * (1 - COST)
                del account['holdings'][ticker]
            account['turnover'] += amount
            account['fees'] += amount * COST
            o.update(status='Filled', day=day, close=bar[2], fx=rate, euros=amount)
    for o in pending:
        if o['status'] == 'Pending' and o['expires'] < now.date().isoformat():
            o['status'] = 'Expired'


def decide(key, account, record, now, *, confirmed_swings=True):
    inputs = record['_evidence']['inputs']
    positions = account['holdings']
    pending = {o['ticker']: o for o in account['orders'] if o['status'] == 'Pending'}
    cash = account['cash'] - sum(o['euros'] * (1 + COST) for o in pending.values() if o['side'] == 'Buy')
    slots = len(positions) + sum(o['side'] == 'Buy' for o in pending.values())
    sectors = [p['sector'] for p in positions.values()] + [o['sector'] for o in pending.values() if o['side'] == 'Buy']
    candidates = []
    market_trend = market(record)

    def submit(t, side, amount, reason):
        inp = inputs[t]
        order = dict(submitted=now.isoformat(), expires=(now.date()+timedelta(days=7)).isoformat(),
            side=side, ticker=t, sector=inp['sector'], symbol=inp.get('yf') or t, currency=inp['cur'],
            euros=amount, reason=reason, status='Pending')
        if confirmed_swings and side == 'Buy':
            order['entry_policy'] = SWING_ENTRY_POLICY
        account['orders'].append(order)
    for ticker, inp in inputs.items():
        if ticker in pending or inp.get('cur') not in ('EUR','USD') or not inp.get('sector'):
            continue
        timing = inp.get('timing') or {}
        technical = timing.get('status') == 'AVAILABLE'
        if (confirmed_swings and ticker in positions and key == 'timing'
                and technical and timing.get('trend') == 'BELOW_SMA200'):
            submit(ticker, 'Sell', None, 'Close below SMA 200')
            continue
        signal = opportunity.project((record.get(ticker) or {}).get('opportunity'), as_of=now) or {}
        if signal.get('withdrawn'):
            continue
        score = signal.get('fundamental_score' if key == 'fundamental' else 'score')
        if score is None:
            continue
        if ticker in positions:
            if score < 6.5:
                submit(ticker, 'Sell', None, f'Score {score:.3f} below 6.5')
            elif key == 'timing' and technical and timing.get('trend') == 'BELOW_SMA200':
                submit(ticker, 'Sell', None, 'Close below SMA 200')
        elif confirmed_swings:
            if key == 'timing' and swing_entry(signal, timing, market_trend):
                candidates.append((-score, ticker))
        elif score >= 7 and (key == 'fundamental' or signal.get('label') in ('Buy','Strong Buy')):
            if key == 'timing' and not (market_trend == 'UPTREND' and technical and confirmation(timing) == 3
                                        and timing.get('extension_atr') is not None and 0 <= timing['extension_atr'] <= 3):
                continue
            candidates.append((-score, ticker))
    budget = .12 * value(account)
    for negscore, t in sorted(candidates):
        if slots >= 8 or cash < budget * (1 + COST):
            break
        sector = inputs[t]['sector']
        if sectors.count(sector) >= 2:
            continue
        submit(t, 'Buy', budget, f'Entry score {-negscore:.3f}')
        sectors.append(sector)
        slots += 1
        cash -= budget * (1 + COST)


def breakout_comparison(ledger, record, now, *, confirmed_swings):
    """Pair the existing active account rules with exactly one exit toggled."""
    twins = ledger.setdefault('breakout_comparison', {})
    frozen = ledger.setdefault('execution_closes', {})
    available = merge_series([record])
    symbols = {active_trading.BENCHMARK}
    for doc in twins.values():
        symbols.update(o['yahoo'] for o in doc['orders'])
    def freeze(symbol):
        series = frozen.setdefault(symbol, {})
        for day, price in available.get(symbol, []):
            if day <= now.date().isoformat():
                series.setdefault(day, price)
    for symbol in symbols:
        freeze(symbol)
    series = dict(available)
    series.update({s:sorted(rows.items()) for s, rows in frozen.items()})
    for version in ('v1.5','v1.6'):
        if version not in twins:
            twins[version] = active_trading.new_account(now.date().isoformat())
            twins[version]['name'] = version
        doc = twins[version]
        if confirmed_swings and not doc.get('entry_policy'):
            existing = active_trading.replay(doc, series, now.date())['orders']
            pending_buys = {o['id'] for o in existing if o['status'] == 'PENDING' and o['side'] == 'BUY'}
            for order in doc['orders']:
                if order['id'] in pending_buys:
                    order['cancelled_at'] = now.isoformat()
            doc['entry_policy'] = SWING_ENTRY_POLICY
        proposed = plan(doc, record, series, now.date(), decision_at=now, failed_breakout=version=='v1.6',
                        confirmed_swings=confirmed_swings)
        for order in proposed['orders']:
            t = order['ticker']
            inp = record['_evidence']['inputs'][t]
            symbol = inp.get('yf') or t
            freeze(symbol)
            doc['orders'].append(dict(id=len(doc['orders'])+1, submitted_at=now.isoformat(),
                ticker=t, side=order['side'], shares=order['shares'], reason=order['reason'],
                resistance=order.get('resistance'), yahoo=symbol, currency=inp['cur']))
        state = active_trading.replay(doc, series, now.date())
        doc['summary'] = dict(value=state['value'], cash=state['cash'], return_pct=state['return_pct'],
                              fills=sum(o['status']=='FILLED' for o in state['orders']),
                              pending=sum(o['status']=='PENDING' for o in state['orders']))


def tracked_symbols(root):
    doc = verified_ledger(root)
    if doc is None:
        return []
    symbols = set(doc.get('execution_closes', {}))
    for account in doc['accounts'].values():
        symbols.update(p['symbol'] for p in account['holdings'].values())
        symbols.update(o['symbol'] for o in account['orders'] if o['status']=='Pending')
    return sorted(symbols)


def advance(ledger, build, now, *, entry_policy=SWING_ENTRY_POLICY, include_exit_experiment=True):
    if entry_policy not in (None, SWING_ENTRY_POLICY):
        raise ValueError('Unsupported swing entry policy')
    confirmed_swings = entry_policy == SWING_ENTRY_POLICY
    if ledger['decisions'] and ledger['decisions'][-1].get('entry_policy') and not confirmed_swings:
        raise ValueError('Swing entry policy cannot be reverted in the journal')
    record = build['record']
    evidence = record['_evidence']
    captured = datetime.fromisoformat(evidence['captured_at'])
    if not timedelta(0) <= now - captured <= timedelta(days=1):
        return False
    pulse = (evidence.get('macro') or {}).get('pulse') or {}
    # Same-day daily data are accepted only in captures after the US regular session.
    latest = (captured.date() if captured.strftime('%H:%M') >= '21:05' else captured.date()-timedelta(days=1)).isoformat()
    sessions = [d for d,v in (pulse.get('tracked') or {}).get('^GSPC', []) if d <= latest and v > 0]
    if not sessions:
        return False
    session = max(sessions)
    previous = ledger['decisions'][-1] if ledger['decisions'] else None
    if previous and session <= previous['session']:
        return False
    bars = {s:{d:(prev, rel, close) for d,prev,rel,close in rows if d <= session and rel > 0 and close > 0}
            for s,rows in (pulse.get('paper_returns') or {}).items()}
    rates = {d:v for d,v in pulse.get('paper_eurusd',[]) if d <= session and v > 0}
    outcomes = {}
    for key, account in ledger['accounts'].items():
        if confirmed_swings:
            for order in account['orders']:
                if order['status'] == 'Pending' and order['side'] == 'Buy' and (
                        key != 'timing' or order.get('entry_policy') != SWING_ENTRY_POLICY):
                    order.update(status='Cancelled', detail=ENTRY_PAUSED)
        settle(account, bars, rates, now)
        gaps = []
        for t,p in account['holdings'].items():
            history = bars.get(p['symbol'], {})
            if (not history or max(history) > p['day'] or (date.fromisoformat(session)-date.fromisoformat(p['day'])).days > 4
                    or (p['currency']=='USD' and p['fx_day'] < session)):
                gaps.append(t)
        count = len(account['orders'])
        if not gaps:
            decide(key, account, record, now, confirmed_swings=confirmed_swings)
        outcomes[key] = dict(equity=None if gaps else value(account), cash=account['cash'], gaps=gaps,
                             new_orders=len(account['orders'])-count)
    if include_exit_experiment:
        breakout_comparison(ledger, record, now, confirmed_swings=confirmed_swings)
    decision = dict(session=session, market=market(record), at=now.isoformat(), run=build['manifest']['run_id'], outcomes=outcomes)
    if confirmed_swings:
        decision['entry_policy'] = entry_policy
    ledger['decisions'].append(decision)
    return True


def update(root, now=None):
    root = Path(root)
    build = current_build(root / 'history')
    ledger = verified_ledger(root, build)
    if ledger is not None and advance(ledger, build, now or datetime.now(timezone.utc)):
        try:
            atomic_json(root / FILE, ledger)
        except (OSError, ValueError) as exc:
            logging.warning('Codex trading journal update skipped: %s', exc)


def verified_ledger(root, build=None):
    """Replay v1 decisions using only verified observations on the selected build's history."""
    root = Path(root)
    try:
        ledger = json.loads((root / FILE).read_text(encoding='utf-8'))
    except FileNotFoundError:
        return fresh()
    except (OSError, ValueError) as exc:
        logging.warning('Codex trading journal unavailable: %s', exc)
        return None

    try:
        if not isinstance(ledger, dict) or ledger.get('version') != 1:
            raise ValueError('Unsupported journal format')
        decisions = ledger['decisions']
        if not isinstance(decisions, list):
            raise ValueError('Invalid journal decisions')
        replay = fresh()
        if decisions:
            lineage = committed_builds(root / 'history', current=build)
            archived = []
            for decision in reversed(decisions):
                matched = next((item for item in lineage if item['manifest']['run_id'] == decision['run']), None)
                if matched is None:
                    raise ValueError('Journal decision has no matching committed build in order')
                at = datetime.fromisoformat(decision['at'])
                if at.utcoffset() != timedelta(0):
                    raise ValueError('Journal decision time must be UTC')
                archived.append((matched, at, decision.get('entry_policy')))
            for matched, at, entry_policy in reversed(archived):
                if not advance(replay, matched, at, entry_policy=entry_policy):
                    raise ValueError('Journal decision cannot be replayed')
        if canonical(replay) != canonical(ledger):
            raise ValueError('Journal state differs from verified replay')
        return replay
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        logging.warning('Codex trading journal unavailable: %s', exc)
        return None


def table(headers, rows):
    cells = lambda tag, values: ''.join(f'<{tag}>{escape(str(v))}</{tag}>' for v in values)
    body = ''.join('<tr>'+cells('td', row)+'</tr>' for row in rows)
    return ('<div class="tw"><table><thead><tr>'+cells('th', headers)+'</tr></thead><tbody>'+body+'</tbody></table></div>')


def site_pages(root, build=None):
    text = '<h1>Codex active trading</h1><p>Forward paper trading · EUR · gross dividends reinvested</p>'
    ledger = verified_ledger(root, build)
    if ledger is None:
        text += '<p>Paper trading results are unavailable because the journal could not be verified.</p>'
        return [(PAGE,shell('Codex active trading',text))]
    latest = ledger['decisions'][-1] if ledger['decisions'] else None
    if latest:
        text += f'<p>Decision {escape(latest["at"][:16])} UTC · market close {escape(latest["session"])}</p>'
        text += f'<p>Verified decision build <code>{escape(latest["run"])}</code></p>'
        if latest.get('market') and latest['market'] != 'UPTREND':
            text += '<p>Active entries paused. S&amp;P 500 trend: '+escape(latest['market'])+'.</p>'
    else:
        text += '<p>Awaiting the first verified close.</p>'
    summary, positions, orders = [], [], []
    for key,name in NAMES.items():
        a = ledger['accounts'][key]
        out = latest['outcomes'][key] if latest else dict(equity=CAPITAL,gaps=[],new_orders=0)
        equity = out['equity']
        summary.append((name, 'Unavailable' if equity is None else f'€{equity:,.2f}',
                        '—' if equity is None else f'{100*(equity/CAPITAL-1):+.2f}%', f'€{a["cash"]:,.2f}',
                        f'€{a["turnover"]:,.2f}', f'€{a["fees"]:,.2f}', out['new_orders'], ', '.join(out['gaps']) or '—'))
        for ticker,p in a['holdings'].items():
            positions.append((name,ticker,p['day'],f'€{p["local_value"]/p["fx"]:,.2f}'))
        for o in a['orders']:
            paused = o['status'] == 'Pending' and o['side'] == 'Buy' and (
                key != 'timing' or o.get('entry_policy') != SWING_ENTRY_POLICY)
            orders.append((o['submitted'][:16], name,o['side'],o['ticker'],
                           'Legacy entry blocked' if paused else o['status'],o.get('day','—'),
                           format(o['euros'],',.2f') if o['euros'] is not None else '—',
                           ENTRY_PAUSED if paused else o.get('detail') or o['reason']))
    text += table(('Strategy','Equity','Return','Cash','Gross traded','Fees','New orders','Price gaps'),summary)
    twins = [(v, f'€{doc["summary"]["cash"]:,.2f}', active_trading._money(doc['summary']['value']),
              doc['summary']['fills'],doc['summary']['pending']) for v,doc in ledger.get('breakout_comparison',{}).items()]
    if twins:
        text += '<h2>Failed-breakout exit experiment</h2><p>Identical active rules. Only v1.6 sells a failed breakout. Both use whole shares and the original account’s fixed FX and price-return basis.</p>'
        text += table(('Rules','Cash','Equity','Fills','Pending'),twins)
    text += ('<p><a href="https://github.com/Usubillaga/InvestorAce/blob/main/docs/analysis/swing-confirmation-2026-11-20.md">'
             'Swing entry validation · point-in-time pilot</a></p>')
    text += '<h2>Holdings</h2>' +(table(('Strategy','Ticker','Local mark date','EUR value'),positions) if positions else '<p>No filled positions.</p>')
    text += '<h2>Order journal</h2>'+(table(('Decision UTC','Strategy','Side','Ticker','Status','Execution date','EUR','Reason'),sorted(orders,reverse=True)) if orders else '<p>No orders recorded.</p>')
    text += ('<h2>Trading rules</h2><p>Each strategy starts with €10,000. New swings require a fundamental score of at least 7, and an Opportunity score of at least 7 with a Buy or Strong Buy label. '
             'Each entry commits 12% of equity, with eight positions and two per sector at most. Sell below 6.5. '
             'The Fundamentals and Opportunity accounts retain their history and can close existing positions. New swings also require '
             'an S&amp;P uptrend, a close above SMA 36/50/200 and extension of 0–3 ATR. It exits below SMA 200.</p>'
             '<p>Orders use fractional exposure at the next available close after the UTC decision date and expire '
             'after seven calendar days. Fees are 0.10% per fill. Local adjusted-close returns include reinvested '
             'distributions before tax. USD exposure uses dated EUR/USD. The journal retains the original decisions.</p>')
    return [(PAGE,shell('Codex active trading',text))]


if __name__ == '__main__':
    update(Path(__file__).resolve().parent)
