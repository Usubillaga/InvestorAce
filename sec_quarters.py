"""Catch up with a reported quarter from the SEC when Yahoo still lags.

Yahoo often needs days to weeks to load a new quarter after a report (KO,
ABT, GILD in November 2026). US filers publish the same figures in their
10-Q/10-K XBRL right away. For a stock whose data lags its last report, the
build reads SEC companyfacts and, if they carry a newer period, replaces the
statement inputs on one consistent window. Market data stays from Yahoo.
"""
from datetime import date

import market_universe

LAG_AFTER_REPORT_DAYS = 100   # a report covers a quarter that ended at most ~100 days earlier
STALE_PERIOD_DAYS = 135       # without a known report date: older than one quarter plus filing time


def _day(value):
    try:
        return date.fromisoformat(str(value)[:10]) if value else None
    except ValueError:
        return None


def lagging(facts, today):
    """True when the stored period predates the last report or is simply old."""
    period = _day(facts.get('financial_period'))
    if period is None:
        return False
    last = _day(facts.get('last_earnings'))
    if last is not None and (last - period).days > LAG_AFTER_REPORT_DAYS:
        return True
    return (today - period).days > STALE_PERIOD_DAYS


def why_not(facts, metrics, today):
    """Reason the SEC window cannot replace the stored one, or None if it can."""
    if not metrics:
        return 'no consistent SEC window (revenue/operating/cash-flow tags missing or misaligned)'
    missing = [k for k in ('revenue', 'fcf', 'shares') if not metrics.get(k)]
    if missing:
        return 'SEC window lacks ' + ', '.join(missing) + ' (flags: ' + ','.join(metrics.get('flags') or []) + ')'
    end, period = _day(metrics.get('period_end')), _day(facts.get('financial_period'))
    if end is None or end > today:
        return 'SEC period end unusable: ' + str(metrics.get('period_end'))
    if period is not None and end <= period:
        return (f"SEC not newer: {metrics.get('basis')} to {end.isoformat()} vs stored {period.isoformat()}"
                f" (flags: {','.join(metrics.get('flags') or []) or '-'})")
    return None


def newer_packet(facts, metrics, cik, today):
    """Facts with SEC statement inputs, or None if SEC is not newer or incomplete."""
    if why_not(facts, metrics, today) is not None:
        return None
    end = _day(metrics.get('period_end'))
    old = facts.get('inputs') or {}
    dep, operating = metrics.get('depreciation'), metrics.get('operating_income')
    inputs = dict(old,
        revenue=metrics['revenue'], operating_income=operating, net_income=metrics.get('net_income'),
        ebitda=operating + dep if operating is not None and dep is not None else None,
        operating_cash_flow=metrics.get('operating_cash_flow'), capex=metrics.get('capex'),
        fcf=metrics['fcf'], shares=metrics['shares'],
        dividends=-abs(metrics['dividends']) if metrics.get('dividends') is not None else old.get('dividends'),
        debt=metrics['debt'] if metrics.get('debt') is not None else old.get('debt'),
        cash=metrics['cash'] if metrics.get('cash') is not None else old.get('cash'))
    urls = list(facts.get('source_urls') or [])
    urls += [market_universe.filing_url(cik, accn) for accn in metrics.get('accns') or []]
    return dict(facts, inputs=inputs, financial_period=end.isoformat(), period_ends=[end.isoformat()],
                basis=metrics['basis'], shares_basis='SEC_' + str(metrics.get('shares_basis')),
                shares_asof=metrics.get('shares_date'), cash_flow_calculation='OCF_MINUS_ABS_CAPEX',
                financial_source='SEC_COMPANYFACTS', financial_currency='USD',
                sec_flags=list(metrics.get('flags') or []), source_urls=urls,
                yahoo_financial_period=facts.get('financial_period'))


def catch_up(facts, symbol, client, ciks, today, log=None):
    """Newer SEC packet for a lagging US filer; None when nothing newer is filed.

    Every lagging stock logs its outcome, so a build shows why one did not
    catch up (no filing yet, misaligned tags, missing shares...)."""
    if facts.get('financial_currency') not in (None, 'USD') or not lagging(facts, today):
        return None
    note = log or (lambda message: None)
    cik = ciks.get(symbol.upper()) or ciks.get(symbol.upper().replace('-', '.'))
    if not cik:
        note(f'SEC catch-up {symbol}: no CIK')
        return None
    payload = client.get_json(market_universe.companyfacts_url(cik))
    if not payload:
        note(f'SEC catch-up {symbol}: companyfacts unavailable')
        return None
    metrics = market_universe.company_metrics(payload, today)
    reason = why_not(facts, metrics, today)
    if reason:
        note(f'SEC catch-up {symbol}: {reason}')
        return None
    note(f"SEC catch-up {symbol}: {facts.get('financial_period')} -> {metrics['period_end']} ({metrics['basis']})")
    return newer_packet(facts, metrics, cik, today)

