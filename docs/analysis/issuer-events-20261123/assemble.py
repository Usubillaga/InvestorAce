"""Project only dated monitoring; no valuation or insider authority is replaced."""
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parents[2]
SELECTED = ('VNT', 'ALLE', 'ADT', 'OXY', 'CRWV', 'ALC', 'ALM', 'AMD', 'ANT', 'B')
SUMMARIES = {
    'VNT': '9M common cash dividends USD10.4m; no preferred outstanding at balance dates. November dividend notice discovered, not yet read.',
    'ALLE': '9M ordinary cash dividends USD140.2m. Tariff benefit mixes received and expected cash; no normalization certified.',
    'ADT': '9M common cash dividends USD130.493m differ from equity deductions USD125.784m; takeover suppressions preserved.',
    'ALC': '9M reported OCF1689 less cash PPE344 = non-IFRS FCF1345mUSD; returned748m includes buybacks, not just dividends.',
    'ALM': '9M management FCF82.6mEUR includes total investing cashflow; not OCF less cash capex. FY2026 results confirmed 2027-02-22.',
    'AMD': '9M continuing OCF6523 less PPE1845 = FCF4678mUSD; prior continuing3437m differs from prior total. One Form4 read, incomplete90d coverage.',
    'ANT': 'IPO close and Nasdaq ClassA listing confirmed by issuer. Offering shares are not total spot all-class outstanding; no valuation inferred.',
    'B': 'Common USD0.175 declared November6, announced November9, record November30, payable December15; payment not proven. Attributable FCF differs from consolidated.'}


def packets():
    rows = {}
    for path in HERE.glob('*.json'):
        doc = json.loads(path.read_text())
        rows.update(doc.get('issuers', {}))
    return rows


def main():
    doc = json.loads(subprocess.check_output(['git','show','194f3291951e3c617b3c292f7506327350c3ec59:source_reviews.json'],cwd=ROOT))
    rows = packets()
    assert set(rows) == set(SELECTED), set(rows)
    at = datetime.now(timezone.utc).isoformat()
    for ticker, row in rows.items():
        entry = doc['entries'].setdefault(ticker, dict(
            issuer=row['issuer'], listing=row.get('listing') or ' / '.join((row['listing_symbol'],row.get('exchange',''),row.get('currency',''))),
            valuation=dict(status='PARTIAL', reason='No completed valuation tie-out; see separately dated monitoring.', sources=[]),
            insider=dict(status='PARTIAL', reason='No complete current disclosure window certified.', sources=[],
                         coverage={'complete': False}, limitations=['Current attempted coverage is separately dated.'], transactions=[])))
        refs = row.get('sources', row.get('source_documents', []))
        refs = [dict(s, title=s.get('title') or s.get('locator') or 'Original issuer source') for s in refs]
        previous = entry.get('monitoring', {})
        refs = list({s['url']: s for s in previous.get('sources', []) + refs}.values())
        entry['monitoring'] = dict(as_of='2026-11-23', attempted_at=at,
            window_start='2026-08-25', window_end='2026-11-23', coverage='PARTIAL', sources=refs,
            gap=row.get('gap') or row['open_gap'], next_check_date=row.get('next_check_date', '2026-11-30'),
            financial_period=row.get('financial_period'), summary=row.get('summary') or SUMMARIES[ticker],
            payments=row.get('payments',row.get('payment_ledger')), next_common_payment=row.get('next_common_payment',previous.get('next_common_payment')),
            next_earnings=row.get('next_earnings'), payment_events=row.get('payment_events', []),
            insider_attempt=row.get('insiders', {'status': row.get('insider_status', 'PARTIAL'), 'complete': False,
                'gap':row.get('insider_gap'), 'events':row.get('insider_events',[]), 'sources':row.get('insider_sources',[])}),
            evidence_packet='docs/analysis/issuer-events-20261123',
            evidence_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in HERE.glob('*.json')},
            note='Partial source check, not a sustainable valuation or full90d insider certification. Historical reviews keep their own dates.')
        if previous:
            entry['monitoring']['previous_attempt'] = previous
    (ROOT / 'source_reviews.json').write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n')


if __name__ == '__main__':
    main()
