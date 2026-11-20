"""Codex long/short swing experiment on InvestorAce's verified daily archive."""
import argparse
from bisect import bisect_left
from datetime import date, datetime, time, timedelta
from html import escape
import json
import logging
from pathlib import Path
import re
from zoneinfo import ZoneInfo

import assessment
import evidence
from codex_trading import table
from integrity import atomic_json, positive_number
import opportunity
from war_scenario import shell

SCHEMA = 'codex-long-short-v1'
TIMING_VERSION = 'experimental-timing-v2'
FUNDAMENTAL_VERSION = 'opportunity-v18.1'
REPORT = Path('history/long_short_lab.json')
PAGE = Path('codex-long-short.html')
NY = ZoneInfo('America/New_York')
# Declared before the first forward evaluation, in New York session dates.
FORWARD_AFTER = '2026-11-20'
CONFIRMED_SIDES = frozenset(('LONG', 'SHORT'))
FORWARD_FUNDAMENTAL_SIDES = frozenset(('LONG',))
CAPITAL, NOTIONAL = 10_000., 500.
SLOTS, COST, BORROW, STRESS_BORROW = 3, .001, .02, .05
TREND_SPREAD, MAX_ATR = .02, 3.
LONG_FUNDAMENTAL, LONG_QUALITY = 7., 6.
SHORT_FUNDAMENTAL, SHORT_QUALITY = 5.5, 6.


def collect(builds):
    """Find completed US sessions, first known daily bars and frozen signal snapshots."""
    sessions, observations, bars, forward_bars = set(), {}, {}, {}
    for build in builds:
        record, run = build['record'], build['manifest']['run_id']
        meta = record['_evidence']
        captured = datetime.fromisoformat(meta['captured_at']).astimezone(NY)
        today = captured.date().isoformat()
        pulse = (meta.get('macro') or {}).get('pulse') or {}
        tracked = (pulse.get('tracked') or {}).get('^GSPC') or []
        completed = {d for d, value in tracked if positive_number(value) is not None
                     and (d < today or (d == today and captured.time() >= time(16, 10)))}
        sessions.update(completed)
        for symbol, rows in (pulse.get('paper_returns') or {}).items():
            for day, previous, relative, close in rows:
                if (day not in completed or previous >= day or positive_number(relative) is None
                        or positive_number(close) is None):
                    continue
                mark = dict(day=day, previous=previous, relative=relative, close=close, build=run, known_at=captured)
                bars.setdefault(day, {}).setdefault(symbol, mark)
                deadline = date.fromisoformat(day) + timedelta(days=1)
                if day >= FORWARD_AFTER and captured < datetime.combine(deadline, time(12), NY):
                    forward_bars.setdefault(day, {}).setdefault(symbol, mark)
        # timing.py only accepts dates strictly before the exchange-local date.
        previous_sessions = [d for d in completed if d < today]
        if not previous_sessions:
            continue
        day = max(previous_sessions)
        if day in observations:
            continue
        rows = {}
        for ticker, inp in meta['inputs'].items():
            symbol = inp.get('yf') or ticker
            technical = inp.get('timing') or {}
            if (inp.get('cur') != 'USD' or not re.fullmatch(r'[A-Z]{1,5}(?:-[A-Z])?', symbol)
                    or technical.get('schema') != TIMING_VERSION or technical.get('status') != 'AVAILABLE'
                    or (technical.get('last_bar') or '')[:10] != day
                    or technical.get('source_timezone') != 'America/New_York'
                    or any(positive_number(technical.get(k)) is None for k in ('close', 'sma36', 'sma50', 'sma200', 'atr14'))):
                continue
            rows[ticker] = (symbol, technical, (record.get(ticker) or {}).get('opportunity'))
        if rows:
            observations[day] = dict(rows=rows, captured=captured, build=run, day=day)
    return sorted(sessions), observations, bars, forward_bars


def entry_side(now, previous):
    close, fast, mid, slow = (now[k] for k in ('close', 'sma36', 'sma50', 'sma200'))
    was_above = previous['close'] - previous['sma36']
    if abs(close - fast) > MAX_ATR * now['atr14']:
        return None
    if close > max(fast, mid) and mid >= slow * (1 + TREND_SPREAD) and was_above <= 0:
        return 'LONG'
    if close < min(fast, mid) and mid <= slow * (1 - TREND_SPREAD) and was_above >= 0:
        return 'SHORT'
    return None


def fundamentals(stored, stamp):
    if not isinstance(stored, dict) or stored.get('schema') != FUNDAMENTAL_VERSION:
        return None, None
    captured = assessment.timestamp(stored.get('as_of'))
    fundamental, quality = stored.get('fundamental_score'), stored.get('quality_score')
    if (captured is None or captured > stamp or assessment.quote_status(stored, stamp) != 'DATED'
            or not opportunity.financial_current(stored.get('financial_period'), stamp)
            or stored.get('withdrawn') or stored.get('status') == 'BLOCKED_INPUTS'
            or type(fundamental) not in (int, float) or type(quality) not in (int, float)
            or not 0 <= fundamental <= 10 or not 0 <= quality <= 10):
        return None, None
    return fundamental, quality


def confirmed(side, fundamental, quality):
    if fundamental is None or quality is None:
        return False
    if side == 'LONG':
        return fundamental >= LONG_FUNDAMENTAL and quality >= LONG_QUALITY
    return fundamental <= SHORT_FUNDAMENTAL and quality <= SHORT_QUALITY


def signal_orders(snapshot, prior, positions, fundamental_sides, last_equity):
    if snapshot is None:
        return []
    exits, candidates = [], []
    rows = snapshot['rows']
    old = prior['rows'] if prior is not None else {}
    for ticker, (symbol, now, stored) in rows.items():
        pos = positions.get(ticker)
        source = dict(ticker=ticker, symbol=symbol, signal_session=snapshot['day'],
                      submitted_at=snapshot['captured'].isoformat(), signal_build=snapshot['build'],
                      signal_close=now['close'], sma36=now['sma36'], sma50=now['sma50'], sma200=now['sma200'])
        if pos is not None:
            side = pos['side']
            if pos['symbol'] == symbol and (side == 'LONG' and now['close'] < now['sma36']
                                            or side == 'SHORT' and now['close'] > now['sma36']):
                exits.append(dict(source, side=side, action='CLOSE', reason='Close reversed through SMA36'))
            continue
        if ticker not in old or old[ticker][0] != symbol or last_equity is None or last_equity <= 0:
            continue
        side = entry_side(now, old[ticker][1])
        if side is None:
            continue
        needs_fundamentals = side in fundamental_sides
        fundamental, quality = fundamentals(stored, snapshot['captured']) if needs_fundamentals else (None, None)
        if needs_fundamentals and not confirmed(side, fundamental, quality):
            continue
        strength = abs(now['sma50'] / now['sma200'] - 1)
        candidates.append((-strength, ticker, dict(source, side=side, action='OPEN',
            entry_basis='FUNDAMENTAL_AND_TECHNICAL' if needs_fundamentals else 'TECHNICAL_ONLY',
            fundamental_score=fundamental, quality_score=quality, reason='Trend and SMA36 crossing')))
    # Keep pre-order slots reserved until an exit fills. Failed exits cannot free a seat.
    slots = {side: SLOTS - sum(p['side'] == side for p in positions.values()) for side in ('LONG', 'SHORT')}
    for _, _, order in sorted(candidates):
        side = order['side']
        if slots[side] > 0:
            slots[side] -= 1
            exits.append(order)
    return exits


def marking_chain(day, pos, bars, catchup_bars):
    symbol = pos['symbol']
    current = bars.get(day, {}).get(symbol)
    if current is None:
        return []
    chain = [dict(current, day=day)]
    # Previously missed sessions remain gaps in the journal. A verified late
    # close can reconnect the mark at a later session, never execute an old order.
    deadline = datetime.combine(date.fromisoformat(day) + timedelta(days=1), time(12), NY)
    while chain[-1]['previous'] > pos['marked_on']:
        missing_day = chain[-1]['previous']
        earlier = catchup_bars.get(missing_day, {}).get(symbol)
        if earlier is None or earlier['known_at'] >= deadline or earlier['previous'] >= missing_day:
            return []
        chain.append(earlier)
    return list(reversed(chain)) if chain[-1]['previous'] == pos['marked_on'] else []


def book_results(sessions, observations, bars, *, fundamental_sides, first=None, as_of, catchup_bars=None):
    sessions = list(sessions)
    catchup_bars = catchup_bars or {}
    start = bisect_left(sessions, first) if first else 0
    positions, orders, equity_curve = {}, [], []
    side_pnl = {'LONG': 0., 'SHORT': 0.}
    fees, borrow_base, peak, drawdown, last_equity, gaps, observed_sessions = 0., 0., CAPITAL, 0., CAPITAL, 0, 0

    def proposed(i, cutoff):
        # A snapshot first seen after noon can still execute at the next
        # session close. A setup older than two sessions expires.
        if i < 1:
            return [], False
        prior_cutoff = datetime.combine(date.fromisoformat(sessions[i - 1]), time(12), NY)
        for signal_index in range(i - 1, max(-1, i - 3), -1):
            snap = observations.get(sessions[signal_index])
            if not snap or not prior_cutoff <= snap['captured'] < cutoff:
                continue
            old = observations.get(sessions[signal_index - 1]) if signal_index >= 1 else None
            if old and old['captured'] >= snap['captured']:
                old = None
            return signal_orders(snap, old, positions, fundamental_sides, last_equity), True
        return [], False

    for i in range(start, len(sessions)):
        day = sessions[i]
        cutoff = datetime.combine(date.fromisoformat(day), time(12), NY)
        due, observed = proposed(i, cutoff)
        observed_sessions += observed
        for pos in positions.values():
            for mark in marking_chain(day, pos, bars, catchup_bars):
                elapsed = (date.fromisoformat(mark['day']) - date.fromisoformat(pos['marked_on'])).days
                if pos['side'] == 'SHORT':
                    borrow_base += pos['marked_notional'] * elapsed / 365
                pos.update(marked_on=mark['day'], marked_notional=pos['marked_notional'] * mark['relative'])
        for order in due:
            ticker, side = order['ticker'], order['side']
            mark = bars.get(day, {}).get(order['symbol'])
            order.update(execution_session=day, status='MISSED_PRICE')
            if not mark or (order['action'] == 'CLOSE' and positions[ticker]['marked_on'] != day):
                orders.append(order)
                continue
            if order['action'] == 'OPEN':
                turnover = NOTIONAL
                positions[ticker] = dict(symbol=order['symbol'], side=side, opened_on=day,
                    entry_close=mark['close'], marked_on=day, marked_notional=NOTIONAL)
            else:
                pos = positions.pop(ticker)
                turnover = pos['marked_notional']
                side_pnl[side] += (turnover - NOTIONAL) * (1 if side == 'LONG' else -1)
            fee = COST * turnover
            side_pnl[side] -= fee
            fees += fee
            order.update(status='FILLED', price_build=mark['build'], execution_close=mark['close'],
                         turnover=turnover, fee=fee)
            orders.append(order)
        missing = sorted(t for t, pos in positions.items() if pos['marked_on'] != day)
        gaps += bool(missing)
        marked_pnl = dict(side_pnl)
        for ticker, pos in positions.items():
            if ticker not in missing:
                side = pos['side']
                marked_pnl[side] += (pos['marked_notional'] - NOTIONAL) * (1 if side == 'LONG' else -1)
        marked_pnl['SHORT'] -= borrow_base * BORROW
        last_equity = None if missing else CAPITAL + sum(marked_pnl.values())
        if last_equity is not None:
            peak = max(peak, last_equity)
            drawdown = min(drawdown, last_equity / peak - 1)
        equity_curve.append(dict(session=day, equity=last_equity, missing=missing))

    # Present the latest already-observed setup as awaiting execution. Its
    # market price will only enter the journal after a later completed session.
    pending = []
    if sessions and (first is None or sessions[-1] >= FORWARD_AFTER):
        tomorrow = date.fromisoformat(sessions[-1]) + timedelta(days=1)
        expected = max(tomorrow, as_of.date())
        if expected.weekday() >= 5:
            expected += timedelta(days=7 - expected.weekday())
        due, _ = proposed(len(sessions), datetime.combine(expected, time(12), NY))
        pending = [dict(order, status='PENDING') for order in due]
    fills = [o for o in orders if o['status'] == 'FILLED']
    entered = any(o['action'] == 'OPEN' for o in fills)
    return dict(
        sessions=len(equity_curve), decision_sessions=observed_sessions,
        first=equity_curve[0]['session'] if equity_curve else None,
        last=equity_curve[-1]['session'] if equity_curve else None,
        final_equity=last_equity if equity_curve else None,
        return_pct=100 * (last_equity / CAPITAL - 1) if entered and last_equity is not None else None,
        drawdown_pct=100 * drawdown if entered else None, gap_sessions=gaps, execution_fees=fees,
        borrow_cost=borrow_base * BORROW, borrow_stress_cost=borrow_base * STRESS_BORROW,
        by_side={side: dict(entries=sum(o['action'] == 'OPEN' and o['side'] == side for o in fills),
                            exits=sum(o['action'] == 'CLOSE' and o['side'] == side for o in fills),
                            net_pnl=marked_pnl[side] if equity_curve and last_equity is not None else None)
                 for side in ('LONG', 'SHORT')},
        fundamental_sides=sorted(fundamental_sides), positions=positions, pending=pending, orders=orders,
        daily_equity=equity_curve)


def experiment(history, through_build=None):
    builds = list(reversed(list(evidence.committed_builds(history))))
    if through_build is not None:
        end = next((i for i, build in enumerate(builds) if build['manifest']['run_id'] == through_build), None)
        if end is None:
            raise ValueError('Unknown verified build')
        builds = builds[:end + 1]
    ref = builds[-1]
    as_of = datetime.fromisoformat(ref['record']['_evidence']['captured_at']).astimezone(NY)
    dates, observations, bars, forward_bars = collect(builds)
    retrospective = [d for d in dates if d <= FORWARD_AFTER]
    first = min(bars) if bars else FORWARD_AFTER
    kwargs = {'as_of': as_of}
    return dict(
        schema=SCHEMA, archive_build=ref['manifest']['run_id'], as_of=as_of.isoformat(),
        opportunity_version=FUNDAMENTAL_VERSION, timing_version=TIMING_VERSION, verified_builds=len(builds),
        parameters=dict(capital_usd=CAPITAL, position_usd=NOTIONAL, slots_per_side=SLOTS,
            fee_per_fill=COST, short_borrow=BORROW, stress_borrow=STRESS_BORROW, forward_after=FORWARD_AFTER,
            trend_sma_spread=TREND_SPREAD, max_trigger_atr=MAX_ATR,
            long_min_fundamental=LONG_FUNDAMENTAL, long_min_quality=LONG_QUALITY,
            short_max_fundamental=SHORT_FUNDAMENTAL, short_max_quality=SHORT_QUALITY),
        backtest={
            'confirmed': book_results(retrospective, observations, bars, fundamental_sides=CONFIRMED_SIDES, first=first, **kwargs),
            'technical_only': book_results(retrospective, observations, bars, fundamental_sides=(), first=first, **kwargs),
            'forward_rules': book_results(retrospective, observations, bars,
                                          fundamental_sides=FORWARD_FUNDAMENTAL_SIDES, first=first, **kwargs),
        },
        paper=book_results(dates, observations, forward_bars,
                           fundamental_sides=FORWARD_FUNDAMENTAL_SIDES, catchup_bars=bars,
                           first=(date.fromisoformat(FORWARD_AFTER) + timedelta(days=1)).isoformat(), **kwargs))


def render(report):
    def summary(label, x):
        long, short = x['by_side']['LONG'], x['by_side']['SHORT']
        pct = lambda value: '—' if value is None else f'{value:+.2f}%'
        pnl = lambda side: '—' if side['net_pnl'] is None else f"{side['net_pnl']:+.2f}"
        dates = f"{x['first']} – {x['last']}" if x['sessions'] else '—'
        counts = lambda side: f"{side['entries']} / {side['exits']}"
        return (label, dates, x['decision_sessions'], counts(long), counts(short), pnl(long), pnl(short),
                pct(x['return_pct']), pct(x['drawdown_pct']), x['gap_sessions'])
    x = report['paper']
    bt = report['backtest']
    stats = table(('Sample', 'Window', 'Decision sessions', 'Long in / out', 'Short in / out', 'Long P&L (USD)',
                   'Short P&L (USD)', 'Net return', 'Observed max drawdown', 'Missing marks'),
                  [summary('Backtest · both sides confirmed', bt['confirmed']),
                   summary('Backtest · both sides technical', bt['technical_only']),
                   summary('Backtest · forward rules', bt['forward_rules']),
                   summary('Forward paper account', x)])
    positions = table(('Ticker', 'Side', 'Entry date', 'Entry close', 'Last mark', 'Marked notional'),
        [(t, p['side'], p['opened_on'], f"${p['entry_close']:.2f}", p['marked_on'], f"${p['marked_notional']:.2f}")
         for t, p in sorted(x['positions'].items())]) if x['positions'] else '<p>No open paper positions.</p>'
    events = [*x['orders'], *x['pending']]
    basis = {'TECHNICAL_ONLY': 'Technical only', 'FUNDAMENTAL_AND_TECHNICAL': 'Fundamental and technical'}
    journal = table(('Setup', 'Execution', 'Ticker', 'Side', 'Action', 'Entry basis', 'Status'),
        [(o['signal_session'], o.get('execution_session', '—'), o['ticker'], o['side'], o['action'],
          basis.get(o.get('entry_basis'), '—'), o['status'])
         for o in reversed(events[-30:])]) if events else '<p>No forward orders yet.</p>'
    body = ('<h1>Codex long/short swing test</h1><p>Daily simulation in USD. '
            'The forward account starts after the 20 November 2026 session.</p>'
            '<h2>Rules</h2><p>Forward longs require a fundamental score ≥ 7 and quality ≥ 6. '
            'Forward shorts use technicals only. SMA50 must be at least 2% above SMA200 for long or below for short. '
            'The closing price must cross SMA36 in the same direction, finish beyond SMA50 and stay within '
            '3 ATR of SMA36. Exit when a completed close reverses across SMA36. Orders use the first session '
            'close after the setup is recorded before noon New York time. Setups expire after two sessions.</p>'
            '<p>$10,000 paper capital, $500 per position and three slots per side. '
            'The simulation uses a total-return proxy for cash distributions and 0.10% per execution. '
            'Indicative short borrowing costs use 2% annually, with a 5% sensitivity in the data. '
            'Historical locates, borrow recalls, spreads, taxes and margin mechanics are unavailable. '
            'Drawdown uses observed closes. The market trend and VIX are context for a later comparison.</p>'
            '<h2>Backtest and forward results</h2>' + stats
            + '<p>The comparison with fundamental confirmation on both sides requires a short fundamental score ≤ 5.5 '
            'and quality ≤ 6. All backtests use archived point-in-time model inputs with reconstructed execution closes. '
            'Forward execution closes must be verified by noon New York time on the following calendar day. '
            'Late data can repair an open position’s next mark. Missed orders stay missed. '
            'A dash indicates no filled entries or an incomplete mark.</p>'
            '<h2>Open paper positions</h2>' + positions + '<h2>Forward order journal</h2>' + journal
            + '<p><a href="codex-long-short.json">Results, orders and source build IDs</a> · '
            f'<a href="https://github.com/Usubillaga/InvestorAce/tree/main/history/_builds/{escape(report["archive_build"])}">'
            'Verified source build</a></p>')
    return shell('Codex long/short swing test', body)


def site_pages(root, build):
    try:
        report = json.loads((Path(root) / REPORT).read_text(encoding='utf-8'))
        if report['schema'] != SCHEMA or report['archive_build'] != build['manifest']['run_id']:
            return []
        return [(PAGE, render(report)), (PAGE.with_suffix('.json'), evidence.canonical(report) + '\n')]
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        if not isinstance(exc, FileNotFoundError):
            logging.warning('Optional long/short experiment report unavailable: %s', exc)
        return []


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--through-build', help='Pin the last verified build')
    parser.add_argument('--write', action='store_true', help='Save the report for GitHub Pages')
    args = parser.parse_args()
    result = experiment(Path('history'), args.through_build)
    if args.write:
        atomic_json(REPORT, result)
    else:
        print(json.dumps(result, allow_nan=False, indent=2))
