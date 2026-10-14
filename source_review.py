"""Dated, source-backed reviews. This module never changes model inputs or scores."""
import json
import math
from datetime import date
from html import escape
from pathlib import Path
from urllib.parse import urlsplit


VALUATION_STATUSES = {'SOURCE_CHECKED', 'PARTIAL', 'UNAVAILABLE', 'NOT_APPLICABLE'}
INSIDER_STATUSES = {'CHECKED_WITH_EVENTS', 'CHECKED_NO_EVENTS', 'PARTIAL',
                    'UNAVAILABLE', 'NOT_APPLICABLE'}
CATEGORIES = {'P': 'Purchase (open market or private)',
              'S': 'Sale (open market or private)', 'A': 'Award/grant',
              'M': 'Exercise/conversion', 'F': 'Tax/exercise withholding', 'G': 'Gift',
              'FCPE': 'Employee fund subscription', 'SALE': 'Disclosed sale',
              'SUBSCRIPTION': 'Employee subscription',
              'AMF_ACQUISITION_EMPLOYEE_FCPE_SUBSCRIPTION': 'Employee fund subscription',
              'AMF_DISPOSAL_SHARE_PLAN_ORIGIN': 'Sale of shares from a prior award plan'}


def empty():
    """Older model bundles had no review register; absence is not a completed check."""
    return dict(schema='source-reviews-v1', as_of=None, window_start=None,
                window_end=None, entries={})


def _date(value):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValueError('Review dates must be ISO calendar dates') from exc


def _url(value):
    try:
        parsed = urlsplit(value)
        valid = (parsed.scheme == 'https' and parsed.hostname and not parsed.username
                 and not parsed.password and parsed.port in (None, 443))
    except (TypeError, ValueError):
        valid = False
    if not valid:
        raise ValueError('Review source requires a valid HTTPS URL')


def load(payload=None):
    """Validate before publication; incomplete coverage cannot certify no activity."""
    if payload is None:
        payload = Path(__file__).with_name('source_reviews.json').read_text(encoding='utf-8')
    try:
        doc = json.loads(payload)
        # Reject NaN/Infinity even in optional metadata and return a detached object.
        doc = json.loads(json.dumps(doc, allow_nan=False))
        if doc['schema'] != 'source-reviews-v1' or not isinstance(doc['entries'], dict):
            raise ValueError('Invalid source review schema')
        start, end, asof = (_date(doc[k]) for k in ('window_start', 'window_end', 'as_of'))
        if not start <= end <= asof:
            raise ValueError('Invalid source review window')
        for ticker, entry in doc['entries'].items():
            if not isinstance(ticker, str) or not ticker or not entry['issuer'] or not entry['listing']:
                raise ValueError('Review requires an issuer and listing')
            for name, statuses in (('valuation', VALUATION_STATUSES), ('insider', INSIDER_STATUSES)):
                section = entry[name]
                if section['status'] not in statuses or not isinstance(section['reason'], str) or not section['reason'].strip():
                    raise ValueError('Review requires a supported status and concrete reason')
                if not isinstance(section['sources'], list):
                    raise ValueError('Review sources must be a list')
                for source in section['sources']:
                    _url(source['url'])
                    if not source['title']:
                        raise ValueError('Review sources require a title')
            insider = entry['insider']
            complete = insider.get('coverage', {}).get('complete') is True
            transactions = insider['transactions']
            if not isinstance(transactions, list) or not isinstance(insider['limitations'], list):
                raise ValueError('Review transactions and limitations must be lists')
            if insider['status'].startswith('CHECKED_'):
                if not complete or not insider['sources']:
                    raise ValueError('A checked window requires complete coverage and sources')
                if bool(transactions) != (insider['status'] == 'CHECKED_WITH_EVENTS'):
                    raise ValueError('Review activity status disagrees with its transactions')
            for transaction in transactions:
                _url(transaction['source_url'])
                if not start <= _date(transaction['transaction_date']) <= end:
                    raise ValueError('Transaction falls outside the disclosed review window')
                if _date(transaction['filing_date']) > asof:
                    raise ValueError('Filing postdates the review')
                if not transaction['owner'] or not transaction['code']:
                    raise ValueError('Transaction requires an owner and a disclosed type')
                for field in ('shares', 'units', 'price'):
                    value = transaction.get(field)
                    if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))
                                              or not math.isfinite(value) or value < 0):
                        raise ValueError('Transaction quantities must be finite and nonnegative')
                if transaction.get('ten_b5_1') is not None and type(transaction['ten_b5_1']) is not bool:
                    raise ValueError('10b5-1 must be true, false or unknown')
        return doc
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError('Malformed source review register') from exc


def insider_cell(ticker, reviews):
    entry = reviews['entries'].get(ticker)
    if entry is None:
        return '<span class="pill empty">NOT REVIEWED</span>'
    status = entry['insider']['status'].replace('_', ' ')
    return (f'<a class="pill x-appr" href="#review-{escape(ticker)}">{escape(status)}</a>'
            f'<br><small>as of {escape(reviews["as_of"])}</small>')


def _sources(sources):
    return ' &middot; '.join(f'<a href="{escape(s["url"], quote=True)}" target="_blank" '
                             f'rel="noopener">{escape(s["title"])}</a>' for s in sources)


def panel(rows, reviews):
    entries = {t: e for t, e in reviews['entries'].items() if t in rows}
    intro = (f'{len(entries)} of {len(rows)} tickers have a dated review entry; '
             f'{len(rows) - len(entries)} not reviewed. Source inspection and a validated '
             'sustainable valuation are separate checks. These disclosures do not change Score or Regime Fit.')
    if not reviews['as_of']:
        return '<section class="box"><h2>Source and insider review</h2><p>' + intro + '</p></section>'
    body = []
    for ticker, entry in sorted(entries.items()):
        valuation, insider = entry['valuation'], entry['insider']
        events = []
        for tx in insider['transactions']:
            code = tx['code']
            category = CATEGORIES.get(code, 'Other disclosed transaction')
            plan = {True: 'yes', False: 'no', None: 'unknown'}[tx.get('ten_b5_1')]
            amount = tx.get('shares') if tx.get('shares') is not None else tx.get('units')
            quantity = '&mdash;' if amount is None else f'{amount:,.4f}'.rstrip('0').rstrip('.')
            quantity += '<br>' + escape(tx.get('unit_type') or tx.get('security_title') or tx.get('security') or '')
            price = '&mdash;' if tx.get('price') is None else f'{tx["price"]:,.4f}'.rstrip('0').rstrip('.')
            events.append('<tr>' + ''.join('<td>' + cell + '</td>' for cell in (
                escape(tx['transaction_date']), escape(tx['filing_date']),
                escape(tx['owner']) + '<br>' + escape(tx.get('role') or ''),
                escape(category) + ' [' + escape(code) + ']', quantity,
                price + ' ' + escape(tx.get('currency') or ''),
                escape(tx.get('ownership') or 'UNKNOWN') + '<br>10b5-1: ' + plan,
                f'<a href="{escape(tx["source_url"], quote=True)}" target="_blank" rel="noopener">Filing</a>'
                + '<br>' + escape(tx.get('note') or ''))) + '</tr>')
        table = ''
        if events:
            table = ('<div class="tw"><table><thead><tr><th>Transaction</th><th>Filed</th>'
                     '<th>Owner / role</th><th>Disclosed type</th><th>Quantity</th><th>Price / currency</th>'
                     '<th>Ownership / plan</th><th>Source / note</th></tr></thead><tbody>'
                     + ''.join(events) + '</tbody></table></div>')
        elif insider['status'] == 'CHECKED_NO_EVENTS':
            table = '<p>No transactions reported in the checked public register for this window.</p>'
        limits = ' '.join(insider['limitations'])
        body.append(f'<details id="review-{escape(ticker)}"><summary>{escape(ticker)} &middot; '
                    f'{escape(entry["issuer"])} &middot; {escape(insider["status"])}</summary>'
                    f'<p><b>Valuation source check: {escape(valuation["status"])}</b><br>'
                    + escape(valuation['reason']) + '</p><p>' + _sources(valuation['sources']) + '</p>'
                    + f'<p><b>Insider coverage: {escape(insider["status"])}</b><br>'
                    + escape(insider['reason']) + '</p><p>' + escape(limits) + '</p><p>'
                    + _sources(insider['sources']) + '</p>' + table + '</details>')
    return ('<section class="box"><h2>Source and insider review</h2><p>' + intro + '</p>'
            f'<p>As of {escape(reviews["as_of"])}. Transaction window '
            f'{escape(reviews["window_start"])} to {escape(reviews["window_end"])}. '
            'P/S codes include open market or private transactions; awards, exercises, '
            'withholding, gifts and employee fund subscriptions are shown separately. '
            'Quantities can refer to different security or fund-unit types; read each filing. '
            'Unknown or incomplete coverage is not evidence of no activity. No motive is inferred.</p>'
            + ''.join(body) + '</section>')
