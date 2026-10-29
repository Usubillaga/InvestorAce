#!/usr/bin/env python3
"""Universe-only financial statement comparison; never changes engine scores.

Refresh: python stock_compare.py --refresh
Publish: weekly_research.build_site renders compare.html from the saved snapshot.
Yahoo's annual statements are provider data, not an InvestorAce source review.
"""
from __future__ import annotations

import argparse
import copy
import json
import assessment as ASSESSMENT
import math
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from numbers import Real
from pathlib import Path
from urllib.parse import quote

from integrity import atomic_json

VERSION = 'stock-comparison-v1'
ASSETS = Path(__file__).resolve().parent
REFRESH_DAYS = 7
REFRESH_BATCH = 16
INCOME = {
    'revenue': ('TotalRevenue',), 'gross_profit': ('GrossProfit',),
    'operating_income': ('OperatingIncome',), 'net_income': ('NetIncome',),
    'ebitda': ('EBITDA',), 'shares_diluted': ('DilutedAverageShares',),
    'shares_basic': ('BasicAverageShares',),
}
BALANCE = {
    'debt': ('TotalDebt',),
    'cash': ('CashCashEquivalentsAndShortTermInvestments', 'CashAndCashEquivalents'),
    'equity': ('StockholdersEquity',), 'assets': ('TotalAssets',),
    'liabilities': ('TotalLiabilitiesNetMinorityInterest',),
}
CASH = {
    'ocf': ('OperatingCashFlow',), 'capex': ('CapitalExpenditure',),
    'stock_comp': ('StockBasedCompensation',), 'buybacks': ('RepurchaseOfCapitalStock',),
}
NUMERIC = set(INCOME) | set(BALANCE) | set(CASH) | {
    'fcf', 'net_debt', 'revenue_growth', 'dilution', 'gross_margin',
    'operating_margin', 'net_margin', 'fcf_margin', 'net_debt_ebitda', 'debt_equity',
}


def number(value):
    if isinstance(value, bool) or not isinstance(value, Real):
        return None
    return float(value) if math.isfinite(value) else None


def ratio(a, b, multiplier=1):
    return a / b * multiplier if a is not None and b is not None and b > 0 else None


def _column(frame, end):
    if frame is not None and not frame.empty:
        for column in frame.columns:
            if str(column)[:10] == end:
                return column
    return None


def _value(frame, end, keys):
    column = _column(frame, end)
    if column is not None:
        for key in keys:
            if key in frame.index:
                value = number(frame.loc[key, column])
                if value is not None:
                    return value
    return None


def empty_row(ticker, model):
    return dict(ticker=ticker, listing=model.get('yf') or ticker, name=ticker,
        sector=model.get('sector') or '', financial_currency=None, quote_currency=None,
        retrieved_at=None, attempted_at=None, status='UNAVAILABLE', annual=[], market={},
        warnings=['NO_STATEMENTS'], sources=[])


def normalize(ticker, model, info, income, balance, cash, *, now=None):
    now = now or datetime.now(timezone.utc)
    row = empty_row(ticker, model)
    info = info if isinstance(info, dict) else {}
    currency = info.get('financialCurrency')
    row.update(name=info.get('longName') or info.get('shortName') or ticker,
        financial_currency=currency if isinstance(currency, str) and len(currency) == 3 else None,
        quote_currency=info.get('currency'), retrieved_at=now.isoformat(), warnings=[])
    if row['financial_currency'] is None:
        row['warnings'].append('FINANCIAL_CURRENCY_UNKNOWN')
    ends = sorted({str(c)[:10] for c in income.columns
                   if str(c)[:10] <= now.date().isoformat()
                   and _value(income, str(c)[:10], INCOME['revenue']) is not None},
                  reverse=True) if income is not None and not income.empty else []
    annual = []
    # Keep one extra year while calculating YoY, then display up to four years.
    for end in ends[:5]:
        item = dict(period_end=end, basis='FY')
        for frame, fields in ((income, INCOME), (balance, BALANCE), (cash, CASH)):
            item.update({key: _value(frame, end, aliases) for key, aliases in fields.items()})
        for field in ('capex', 'buybacks'):
            if item[field] is not None:
                item[field] = abs(item[field])
        item['fcf'] = item['ocf'] - item['capex'] if all(item[k] is not None for k in ('ocf', 'capex')) else None
        item['net_debt'] = item['debt'] - item['cash'] if all(item[k] is not None for k in ('debt', 'cash')) else None
        for metric, numerator in (('gross_margin', 'gross_profit'), ('operating_margin', 'operating_income'),
                                  ('net_margin', 'net_income'), ('fcf_margin', 'fcf')):
            item[metric] = ratio(item[numerator], item['revenue'], 100)
        item['net_debt_ebitda'] = ratio(item['net_debt'], item['ebitda'])
        item['debt_equity'] = ratio(item['debt'], item['equity'])
        item.update(revenue_growth=None, dilution=None)
        annual.append(item)
    for i, item in enumerate(annual[:-1]):
        prior = annual[i + 1]
        gap = (datetime.fromisoformat(item['period_end']) - datetime.fromisoformat(prior['period_end'])).days
        if not 330 <= gap <= 400:
            continue
        growth = ratio(item['revenue'], prior['revenue'])
        item['revenue_growth'] = (growth - 1) * 100 if growth is not None else None
        shares = ratio(item['shares_diluted'], prior['shares_diluted'])
        if shares is not None and 1 / 3 < shares < 3:
            item['dilution'] = (shares - 1) * 100
        elif shares is not None:
            row['warnings'].append('SHARE_ACTION_REVIEW')
    row['annual'] = annual[:4]
    shares, floating = number(info.get('sharesOutstanding')), number(info.get('floatShares'))
    shares = shares if shares is not None and shares > 0 else None
    floating = floating if floating is not None and floating >= 0 else None
    inconsistent = shares is not None and floating is not None and floating > shares
    row['market'] = dict(shares_outstanding=shares, float_shares=floating,
        float_pct=None if inconsistent else ratio(floating, shares, 100),
        retrieved_at=now.isoformat() if info else None)
    if inconsistent:
        row['warnings'].append('FLOAT_EXCEEDS_SHARES')
    if not annual:
        row['warnings'].append('NO_STATEMENTS')
    elif (now.date() - datetime.fromisoformat(annual[0]['period_end']).date()).days > 550:
        row['warnings'].append('OLD_FINANCIALS')
    if info.get('quoteType') and info['quoteType'] != 'EQUITY':
        row['warnings'].append('SECURITY_TYPE_REVIEW')
    row['status'] = ('OK' if annual and row['financial_currency'] and
        all(annual[0].get(k) is not None for k in ('revenue', 'net_income', 'debt', 'fcf')) else
        'PARTIAL' if annual else 'UNAVAILABLE')
    base = 'https://finance.yahoo.com/quote/' + quote(row['listing'], safe='')
    row['sources'] = [dict(label=label, url=base + '/' + suffix + '/') for label, suffix in
        (('Yahoo Finance · Income statement', 'financials'), ('Yahoo Finance · Balance sheet', 'balance-sheet'),
         ('Yahoo Finance · Cash flow', 'cash-flow'), ('Yahoo Finance · Share statistics', 'key-statistics'))]
    return row


def fetch_yahoo(symbol):
    import yfinance as yf
    ticker = yf.Ticker(symbol)
    result = dict(info={}, income=None, balance=None, cash=None, errors=[])
    for key, getter in (('info', ticker.get_info), ('income', ticker.get_income_stmt),
                        ('balance', ticker.get_balance_sheet), ('cash', ticker.get_cashflow)):
        try:
            result[key] = getter()
        except Exception as error:
            result['errors'].append(key + ':' + type(error).__name__)
    return result


def _cache_rows(snapshot):
    if not isinstance(snapshot, dict) or snapshot.get('schema') != VERSION:
        return {}
    rows = snapshot.get('rows', [])
    return {r['ticker']: r for r in rows if isinstance(r, dict) and isinstance(r.get('ticker'), str)}


def refresh(universe, *, previous=None, fetcher=None, now=None, workers=4):
    now = now or datetime.now(timezone.utc)
    fetcher = fetcher or fetch_yahoo
    old = _cache_rows(previous)
    retained, pending = {}, []
    for key, model in universe.items():
        cached = old.get(key)
        valid = bool(cached and cached.get('listing') == (model.get('yf') or key) and cached.get('annual'))
        try:
            stamp = datetime.fromisoformat(cached['retrieved_at']) if valid else None
            recent = bool(stamp and timedelta(0) <= now - stamp < timedelta(days=REFRESH_DAYS))
        except (TypeError, ValueError, KeyError):
            recent = False
        if valid and recent and cached.get('status') in ('OK', 'PARTIAL'):
            retained[key] = copy.deepcopy(cached)
        else:
            pending.append((key, model))
    pending.sort(key=lambda pair: (old.get(pair[0], {}).get('attempted_at') or
                                   old.get(pair[0], {}).get('retrieved_at') or '',
                                   not pair[1].get('held'), pair[0]))
    for key, model in pending[REFRESH_BATCH:]:
        cached = old.get(key)
        retained[key] = (copy.deepcopy(cached) if cached and
            cached.get('listing') == (model.get('yf') or key) else empty_row(key, model))

    def collect(pair):
        key, model = pair
        listing = model.get('yf') or key
        try:
            raw = fetcher(listing)
            row = normalize(key, model, raw['info'], raw['income'], raw['balance'], raw['cash'], now=now)
            if not row['annual']:
                raise ValueError('No annual statements')
            cached = old.get(key)
            if cached and cached.get('listing') == listing and cached.get('annual'):
                complete = cached.get('financial_currency') and all(
                    cached['annual'][0].get(k) is not None for k in ('revenue', 'net_income', 'debt', 'fcf'))
                if raw.get('errors') or (complete and row['status'] == 'PARTIAL'):
                    raise ValueError('Incomplete refresh must not replace last-good data')
            row['warnings'] += ['PROVIDER_REQUEST_PARTIAL'] if raw.get('errors') else []
            row['attempted_at'] = now.isoformat()
            return row
        except Exception:
            if key in old and old[key].get('listing') == listing and old[key].get('annual'):
                row = copy.deepcopy(old[key])
                row.update(status='CACHED', warnings=list(dict.fromkeys(row.get('warnings', []) + ['REFRESH_FAILED'])))
            else:
                row = empty_row(key, model)
            row['attempted_at'] = now.isoformat()
            return row

    with ThreadPoolExecutor(max_workers=min(workers, 2)) as executor:
        retained.update((row['ticker'], row) for row in executor.map(collect, pending[:REFRESH_BATCH]))
    rows = [retained[key] for key in sorted(universe)]
    return dict(schema=VERSION, generated_at=now.isoformat(), universe_count=len(rows), rows=rows,
        refresh_policy=dict(max_stocks_per_run=REFRESH_BATCH, reuse_days=REFRESH_DAYS))


def load_snapshot(path):
    try:
        def reject(value):
            raise ValueError('Non-finite JSON: ' + value)
        return json.loads(Path(path).read_text(encoding='utf-8'), parse_constant=reject)
    except (OSError, ValueError):
        return None


def apply_primary_annuals(row, review, *, as_of):
    """Repair exact fiscal years using the source facts frozen with the build."""
    valuation = (review or {}).get('valuation', {})
    packet = valuation.get('financial_packet') or {}
    published = ASSESSMENT.timestamp(packet.get('published_at'))
    retrieved = ASSESSMENT.timestamp(packet.get('fetched_at'))
    if (not published or not retrieved or not published <= retrieved <= as_of or
            packet.get('symbol') != row.get('listing') or
            packet.get('financial_currency') != row.get('financial_currency')):
        return row
    ledger = valuation.get('calculation_ledger', {})
    if ledger.get('unit') != 'USD millions except per-share amounts':
        return row
    result = copy.deepcopy(row)
    years = {item['period']: item for item in ledger.get('annual', [])}
    for item in result.get('annual', []):
        source = years.get(item.get('period_end'))
        if not source:
            continue
        for field, source_field in (('ocf','operating_cash_flow'), ('capex','capex'),
                ('fcf','fcf'), ('net_income','net_income'), ('revenue','revenue'),
                ('operating_income','operating_income')):
            if number(source.get(source_field)) is not None:
                item[field] = source[source_field] * 1e6
        for field, numerator in (('gross_margin','gross_profit'), ('operating_margin','operating_income'),
                ('net_margin','net_income'), ('fcf_margin','fcf')):
            item[field] = ratio(item.get(numerator), item.get('revenue'), 100)
    for item, prior in zip(result.get('annual', []), result.get('annual', [])[1:]):
        gap = (datetime.fromisoformat(item['period_end'])-datetime.fromisoformat(prior['period_end'])).days
        growth = ratio(item.get('revenue'), prior.get('revenue'))
        item['revenue_growth'] = (growth-1)*100 if growth is not None and 330 <= gap <= 400 else None
    result.setdefault('sources', []).extend(
        dict(label=source['title'], url=source['url']) for source in valuation.get('sources', []))
    result.setdefault('warnings', []).append('PRIMARY_ANNUAL_CASH_FLOW_CORRECTION')
    return result


def site_pages(root, build, *, now=None):
    now = now or datetime.now(timezone.utc)
    record = build['record']
    evidence = record.get('_evidence', {})
    inputs = evidence.get('inputs', {})
    saved = load_snapshot(Path(root) / 'comparison' / 'latest.json')
    cache = _cache_rows(saved)
    notes = load_snapshot(Path(root) / 'scanner_notes.json') or {}
    rows = []
    # Never expose a cached outsider, even through a hand-written URL or export.
    for key, model in sorted(inputs.items()):
        row = copy.deepcopy(cache.get(key))
        if not row or row.get('listing') != (model.get('yf') or key):
            row = empty_row(key, model)
        row = apply_primary_annuals(row, record.get('_source_reviews', {}).get('entries', {}).get(key), as_of=now)
        output = record.get(key) or {}
        objections = notes.get('entries', {}).get(key, {}).get('objections', [])
        checked = ASSESSMENT.project(output.get('assessment'), raw_score=output.get('score'), as_of=now,
                                     objections=objections)
        row['model'] = dict(score=checked['model_score'], raw_score=checked['raw_score'],
            score_status=(output.get('score_explanation') or {}).get('status') or 'UNAVAILABLE',
            captured_at=evidence.get('captured_at'),
            assessment_schema=checked['schema'], assessed_at=checked.get('as_of'),
            expires_at=checked.get('expires_at'), rating=checked['rating'],
            review_required=not checked['quality_rank_eligible'],
            quality_rank_eligible=checked['quality_rank_eligible'], assessment=checked,
            archived_assessment=output.get('assessment'), objections=objections)
        rows.append(row)
    payload = dict(schema=VERSION, generated_at=now.isoformat(),
        snapshot_at=(saved or {}).get('generated_at'), universe_count=len(rows), rows=rows,
        duel_policy='finance-duel-v1')
    raw = json.dumps(payload, ensure_ascii=False, allow_nan=False, indent=2) + '\n'
    safe = raw.replace('<', '\\u003c').replace('&', '\\u0026')
    template = (ASSETS / 'compare_template.html').read_text(encoding='utf-8')
    styles = (ASSETS / 'compare.css').read_text(encoding='utf-8') + '\n' + (ASSETS / 'compare_duel.css').read_text(encoding='utf-8')
    page = template.replace('__STYLE__', styles)
    page = page.replace('__DUEL__', (ASSETS / 'compare_duel.js').read_text(encoding='utf-8'))
    page = page.replace('__SCRIPT__', (ASSETS / 'assessment_view.js').read_text(encoding='utf-8') + '\n'
                        + (ASSETS / 'compare.js').read_text(encoding='utf-8')).replace('__DATA__', safe)
    return [(Path('compare.html'), page), (Path('compare.json'), raw)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh', action='store_true', required=True)
    parser.add_argument('--output', type=Path, default=ASSETS / 'comparison' / 'latest.json')
    args = parser.parse_args()
    from engine import DATA
    snapshot = refresh(DATA, previous=load_snapshot(args.output))
    atomic_json(args.output, snapshot)
    counts = {status: sum(r['status'] == status for r in snapshot['rows'])
              for status in ('OK', 'PARTIAL', 'CACHED', 'UNAVAILABLE')}
    print('Comparison snapshot:', len(snapshot['rows']), 'universe stocks;', counts)


if __name__ == '__main__':
    main()
