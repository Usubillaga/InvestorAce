"""Open-market insider purchases from SEC Form 4; positioning, never scored.

Only transaction code P (open-market or private purchase) counts as a buy.
Grants (A), option exercises (M), plan transactions (I, e.g. a 401(k)
rebalance), gifts and conversions are excluded. Sales (S) are summarised
separately because many are pre-planned (Rule 10b5-1).
"""
import json
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

SCHEMA = 'insider-activity-v1'
WINDOW_DAYS = 180
CACHE = Path('history/_insider_cache.json')
TICKERS_URL = 'https://www.sec.gov/files/company_tickers_exchange.json'
ARCHIVE = 'https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{document}'


def _text(node, path):
    found = node.find(path)
    if found is None:
        return None
    value = found.findtext('value')
    value = value if value is not None else found.text
    return value.strip() if isinstance(value, str) and value.strip() else None


def _number(value):
    try:
        number = float(str(value).replace(',', ''))
    except (TypeError, ValueError):
        return None
    return number if number == number and abs(number) != float('inf') else None


def _strip_namespaces(root):
    for node in root.iter():
        if isinstance(node.tag, str) and '}' in node.tag:
            node.tag = node.tag.split('}', 1)[1]
    return root


def parse_form4(xml_text):
    """Non-derivative transactions of one Form 4, with the owner's roles."""
    try:
        root = _strip_namespaces(ET.fromstring(xml_text))
    except ET.ParseError:
        return []
    owners, roles = [], set()
    for owner in root.findall('reportingOwner'):
        name = (owner.findtext('reportingOwnerId/rptOwnerName') or '').strip()
        if name:
            owners.append(name)
        rel = owner.find('reportingOwnerRelationship')
        if rel is None:
            continue
        flag = lambda tag: (rel.findtext(tag) or '').strip().lower() in ('1', 'true')
        if flag('isDirector'):
            roles.add('Director')
        if flag('isOfficer'):
            roles.add('Officer')
        if flag('isTenPercentOwner'):
            roles.add('10% owner')
    out = []
    for item in root.findall('nonDerivativeTable/nonDerivativeTransaction'):
        code = (item.findtext('transactionCoding/transactionCode') or '').strip().upper()
        shares = _number(_text(item, 'transactionAmounts/transactionShares'))
        price = _number(_text(item, 'transactionAmounts/transactionPricePerShare'))
        when = _text(item, 'transactionDate')
        if not code or shares is None or not when:
            continue
        out.append(dict(date=when[:10], code=code, shares=shares, price=price,
                        direction=_text(item, 'transactionAmounts/transactionAcquiredDisposedCode'),
                        owner=' / '.join(owners) or None, roles=sorted(roles)))
    return out


def summarize(transactions, *, as_of, days=WINDOW_DAYS):
    """Purchases and sales within the window; unknown prices are not valued."""
    start = (as_of.date() if isinstance(as_of, datetime) else as_of) - timedelta(days=days)
    end = as_of.date() if isinstance(as_of, datetime) else as_of
    def window(x):
        try:
            return start <= date.fromisoformat(x['date']) <= end
        except (TypeError, ValueError):
            return False
    buys = [x for x in transactions if x['code'] == 'P' and window(x)]
    sells = [x for x in transactions if x['code'] == 'S' and window(x)]
    priced = [x for x in buys if x['price']]
    value = sum(x['shares'] * x['price'] for x in priced)
    priced_shares = sum(x['shares'] for x in priced)
    roles = sorted({role for x in buys for role in x['roles']})
    return dict(schema=SCHEMA, source='SEC_FORM_4', window_days=days, as_of=end.isoformat(),
        purchases=len(buys), buyers=len({x['owner'] for x in buys}),
        shares_bought=sum(x['shares'] for x in buys), value_bought=value if priced else None,
        avg_price=value / priced_shares if priced_shares else None,
        min_price=min((x['price'] for x in priced), default=None),
        max_price=max((x['price'] for x in priced), default=None),
        last_purchase=max((x['date'] for x in buys), default=None), buyer_roles=roles,
        sales=len(sells), value_sold=sum(x['shares'] * x['price'] for x in sells if x['price']) or None,
        largest=sorted(({k: x[k] for k in ('date', 'owner', 'roles', 'shares', 'price')} for x in buys),
                       key=lambda x: -(x['shares'] * (x['price'] or 0)))[:3])


def ciks(payload):
    """company_tickers_exchange.json -> {ticker: cik}."""
    fields = (payload or {}).get('fields') or []
    try:
        i, t = fields.index('cik'), fields.index('ticker')
    except ValueError:
        return {}
    return {str(row[t]).upper(): int(row[i]) for row in payload.get('data') or []
            if row and row[t] and row[i]}


def recent_form4(submissions, *, as_of, days=WINDOW_DAYS):
    """Accession and raw XML document of Form 4 filings in the window."""
    recent = ((submissions or {}).get('filings') or {}).get('recent') or {}
    start = (as_of.date() - timedelta(days=days + 10)).isoformat()
    rows = zip(recent.get('form', []), recent.get('accessionNumber', []),
               recent.get('filingDate', []), recent.get('primaryDocument', []))
    return [dict(accession=a, filed=f, document=d.rsplit('/', 1)[-1])
            for form, a, f, d in rows if form in ('4', '4/A') and f >= start and d]


def us_symbol(row, ticker):
    symbol = row.get('yf', ticker)
    return None if not symbol or '.' in symbol or row.get('cur') not in (None, 'USD') else symbol.upper()


def refresh(data, client, *, as_of=None, cache_path=CACHE, log=print):
    """Attach `insider_activity` to every US-listed row; reuse parsed filings."""
    as_of = as_of or datetime.now(timezone.utc)
    try:
        cache = json.loads(Path(cache_path).read_text(encoding='utf-8'))
        if cache.get('schema') != SCHEMA:
            cache = {}
    except (OSError, ValueError, AttributeError):
        cache = {}
    filings = cache.get('filings', {})
    mapping = ciks(client.get_json(TICKERS_URL))
    counts = dict(covered=0, with_purchases=0, unavailable=0, filings_fetched=0)
    for ticker, row in data.items():
        symbol = us_symbol(row, ticker)
        cik = (mapping.get(symbol) or mapping.get(symbol.replace('-', '.'))) if symbol else None
        if not cik:
            row['insider_activity'] = None
            continue
        submissions = client.get_json(f'https://data.sec.gov/submissions/CIK{cik:010d}.json')
        if submissions is None:
            row['insider_activity'] = None
            counts['unavailable'] += 1
            continue
        transactions, complete = [], True
        for filing in recent_form4(submissions, as_of=as_of):
            key = filing['accession']
            if key not in filings:
                url = ARCHIVE.format(cik=cik, accession=key.replace('-', ''), document=filing['document'])
                text = client.get_text(url)
                if text is None:
                    complete = False
                    continue
                filings[key] = dict(filed=filing['filed'], transactions=parse_form4(text))
                counts['filings_fetched'] += 1
            transactions.extend(filings[key]['transactions'])
        summary = summarize(transactions, as_of=as_of)
        summary.update(cik=cik, complete=complete,
                       source_url=f'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany'
                                  f'&CIK={cik:010d}&type=4&dateb=&owner=only&count=40')
        row['insider_activity'] = summary
        counts['covered'] += 1
        counts['with_purchases'] += bool(summary['purchases'])
    keep = (as_of.date() - timedelta(days=WINDOW_DAYS + 40)).isoformat()
    filings = {k: v for k, v in filings.items() if v.get('filed', '') >= keep}
    Path(cache_path).write_text(json.dumps(dict(schema=SCHEMA, filings=filings), sort_keys=True),
                                encoding='utf-8')
    log(f'Insider activity: {counts}')
    return counts

