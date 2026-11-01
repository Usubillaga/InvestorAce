"""Catch up with a reported quarter from the SEC when Yahoo still lags.

Yahoo often needs days to weeks to load a new quarter after a report (KO,
ABT, GILD in November 2026). US filers publish the same figures in their
10-Q/10-K XBRL right away. For a stock whose data lags its last report, the
build reads SEC companyfacts and, if they carry a newer period, replaces the
statement inputs on one consistent window. Market data stays from Yahoo.
"""
import copy
import xml.etree.ElementTree as ET
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


DIAGNOSTIC_GROUPS = (('revenue', 'REVENUE'), ('operating', 'OPERATING_INCOME'), ('ocf', 'OPERATING_CASH'),
                     ('capex', 'CAPEX'), ('net_income', 'NET_INCOME'))


def diagnostics(companyfacts, today):
    """Latest window per us-gaap element of the core measures, for the build log.

    Shows, per element, the last period end and the lengths (days) of the
    windows reported for it, plus the newest end any us-gaap USD duration
    reaches. That is enough to see whether newer 10-Qs exist and which
    element or window length the reader would need."""
    parts = []
    for name, constant in DIAGNOSTIC_GROUPS:
        for tag in getattr(market_universe, constant):
            rows = [f for f in market_universe._clean(market_universe._units(companyfacts, tag, 'USD'), today)
                    if f['start']]
            if not rows:
                continue
            end = max(f['end'] for f in rows)
            lengths = sorted({(f['end'] - f['start']).days for f in rows if f['end'] == end})
            parts.append(f"{name}:{tag}={end.isoformat()}/{','.join(map(str, lengths))}d")
    newest = None
    for tag, body in ((companyfacts or {}).get('facts') or {}).get('us-gaap', {}).items():
        for fact in (body.get('units') or {}).get('USD', []):
            if fact.get('start') and fact.get('end') and fact['end'] <= today.isoformat():
                if newest is None or fact['end'] > newest[0]:
                    newest = (fact['end'], tag)
    if newest:
        parts.append(f'newest us-gaap duration: {newest[1]}={newest[0]}')
    return '; '.join(parts) or 'no us-gaap USD duration facts'


XBRLI = '{http://www.xbrl.org/2003/instance}'


def newer_filing(submissions, after, today):
    """Latest 10-Q/10-K whose report date is after `after` (a date), or None."""
    recent = ((submissions or {}).get('filings') or {}).get('recent') or {}
    best = None
    rows = zip(recent.get('form', []), recent.get('accessionNumber', []), recent.get('reportDate', []),
               recent.get('filingDate', []), recent.get('primaryDocument', []))
    for form, accession, report, filed, document in rows:
        if form not in ('10-Q', '10-K') or not document or not document.endswith('.htm'):
            continue
        report_day, filed_day = _day(report), _day(filed)
        if report_day is None or filed_day is None or filed_day > today or report_day <= after:
            continue
        if best is None or report_day > best['report']:
            best = dict(form=form, accession=accession, report=report_day, filed=filed, document=document)
    return best


def instance_url(cik, filing):
    """EDGAR's extracted XBRL instance of an inline-XBRL filing."""
    folder = filing['accession'].replace('-', '')
    name = filing['document'].rsplit('.', 1)[0] + '_htm.xml'
    return f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{folder}/{name}'


def parse_instance(xml_text, filing):
    """us-gaap/dei facts of one filing in companyfacts shape; dimensional facts are skipped."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return None
    contexts, units = {}, {}
    for context in root.iter(XBRLI + 'context'):
        if context.find('.//' + XBRLI + 'segment') is not None or context.find('.//' + XBRLI + 'scenario') is not None:
            continue
        period = context.find(XBRLI + 'period')
        if period is None:
            continue
        start, end = period.findtext(XBRLI + 'startDate'), period.findtext(XBRLI + 'endDate')
        instant = period.findtext(XBRLI + 'instant')
        contexts[context.get('id')] = (start, end) if end else (None, instant)
    for unit in root.iter(XBRLI + 'unit'):
        measures = [m.text or '' for m in unit.iter(XBRLI + 'measure')]
        if len(measures) == 1:
            units[unit.get('id')] = measures[0].split(':')[-1]
    doc = {'facts': {'us-gaap': {}, 'dei': {}}}
    count = 0
    for element in root:
        tag = element.tag
        if not isinstance(tag, str) or '}' not in tag:
            continue
        namespace, name = tag[1:].split('}', 1)
        taxonomy = 'us-gaap' if 'fasb.org/us-gaap' in namespace else 'dei' if 'xbrl.sec.gov/dei' in namespace else None
        context = contexts.get(element.get('contextRef'))
        unit = units.get(element.get('unitRef'))
        if taxonomy is None or context is None or unit not in ('USD', 'shares'):
            continue
        try:
            value = float((element.text or '').strip())
        except ValueError:
            continue
        item = dict(end=context[1], val=value, filed=filing['filed'], accn=filing['accession'], form=filing['form'])
        if context[0]:
            item['start'] = context[0]
        doc['facts'][taxonomy].setdefault(name, {'units': {}})['units'].setdefault(unit, []).append(item)
        count += 1
    return doc if count else None


def merge_facts(companyfacts, extra):
    """companyfacts plus the facts of one more filing (same shape)."""
    merged = copy.deepcopy(companyfacts or {'facts': {}})
    for taxonomy, tags in (extra or {}).get('facts', {}).items():
        target = merged.setdefault('facts', {}).setdefault(taxonomy, {})
        for name, body in tags.items():
            units = target.setdefault(name, {'units': {}}).setdefault('units', {})
            for unit, items in body['units'].items():
                units.setdefault(unit, []).extend(items)
    return merged


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
    if reason and hasattr(client, 'get_text'):
        # The SEC aggregation can miss a filed report (ABT 2026: its Q2 10-Q
        # is on EDGAR but absent from companyfacts). Read that filing itself.
        stored = _day(facts.get('financial_period'))
        filing = newer_filing(client.get_json(market_universe.submissions_url(cik)), stored, today) if stored else None
        if filing is not None:
            extra = parse_instance(client.get_text(instance_url(cik, filing)) or '', filing)
            if extra:
                payload = merge_facts(payload, extra)
                metrics = market_universe.company_metrics(payload, today)
                reason = why_not(facts, metrics, today)
                note(f"SEC catch-up {symbol}: read {filing['form']} {filing['report'].isoformat()} "
                     f"({filing['accession']}) directly; " + (reason or 'usable'))
            else:
                note(f"SEC catch-up {symbol}: {filing['form']} {filing['report'].isoformat()} instance unreadable")
    if reason:
        note(f'SEC catch-up {symbol}: {reason}')
        note(f'SEC detail {symbol}: {diagnostics(payload, today)}')
        return None
    note(f"SEC catch-up {symbol}: {facts.get('financial_period')} -> {metrics['period_end']} ({metrics['basis']})")
    return newer_packet(facts, metrics, cik, today)

