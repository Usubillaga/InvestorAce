"""Mechanical projection of the dated primary-source packets; no model inputs."""
import json
import hashlib
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parents[2]
SELECTED = ('OXY', 'ENB', 'CRWV', 'MRNA', 'NBIS', 'OPEN', 'AVGO', 'BYRN', 'INTU', 'NVDA')
SUMMARIES = {
    'OXY': 'YTD USD million: combined common/preferred cash paid 1271; preferred declared 509, not proof of cash paid. Common USD0.28 payable 2027-01-15; record 2026-12-10; actual payment unknown.',
    'ENB': 'YTD CAD million: preferred cash paid 319; common cash paid 6355. Management DCF already deducts preference dividends. Common CAD0.97 payable 2026-12-01; record 2026-11-13; actual payment unknown.',
    'CRWV': '2026 YTD preferred dividends paid zero and no preferred shares outstanding, expressly reported; historical 2025 payment is not a current claim. September debt/lease definition remains open.',
    'MRNA': 'YTD USD million: OCF -2715; PPE cash capex 146; intangible purchases 74 separate. Missing preference payment evidence remains unknown, not zero.',
    'NBIS': 'September30 outstanding all-class shares excluding treasury 292902405 agree with cache. No preference payment zero inferred from omission.',
    'OPEN': 'Q3 and nine months 2026/2025: issuer explicitly reports no common/preferred dividends declared, paid or accumulated. This does not certify redemptions or other periods.',
    'AVGO': 'No preferred outstanding at August2 and opening November2 dates; historical conversion fix supported. YTD common cash dividends USD9281000000. September30 payable is not independently confirmed paid. Next earnings December9 after US close.',
    'BYRN': 'No preferred issued at August31 and opening November30 dates. Historical Series A converted April15 2021. YTD OCF less cash PPE is -USD4707000, not TTM or normalized FCFE.',
    'INTU': 'Q1 USD million: common dividends and rights cash paid 378 versus declared 383. Common USD1.38 payable 2027-01-15, record 2027-01-08; not yet paid. November12 outstanding shares 264015000 require provider reconciliation.',
    'NVDA': 'YTD USD million: OCF122675 less PPE/intangibles8856 and principal147 gives issuer FCF113672; common dividends paid12316. Common USD0.25 payable 2026-12-23, record 2026-12-02; not yet paid. October25 period not yet reconciled to cached July inputs.'}


def packets():
    result = {}
    for path in sorted(HERE.glob('*.json')):
        data = json.loads(path.read_text())
        if isinstance(data.get('issuers'), dict):
            result.update(data['issuers'])
    return result


def sources(row):
    raw = row.get('sources', row.get('report_sources', []))
    if not raw and row.get('report_url'):
        raw = [dict(url=row['report_url'], published_at=row.get('published_at'),
                    locator='Original 10-Q; see linked evidence observations')]
    return [dict(s, title=s.get('title') or s.get('locator') or 'Issuer original report') for s in raw]


def main():
    doc = json.loads((ROOT / 'source_reviews.json').read_text())
    for ticker in ('ASML', 'ENB', 'LULU', 'LVMH', 'NFLX', 'NVDA', 'PFE', 'SAN', 'UNH', 'WKL'):
        # Preserve the legacy completed window, never re-date it to this attempt.
        doc['entries'][ticker]['insider'].setdefault('reviewed_at', '2026-10-14')
    for ticker, row in packets().items():
        if ticker not in SELECTED:
            continue
        refs = sources(row)
        gap = row.get('open_gap') or '; '.join(row.get('gaps', []))
        entry = doc['entries'].setdefault(ticker, dict(
            issuer=row.get('issuer', ticker), listing=ticker + ' / NASDAQ / USD',
            valuation=dict(status='PARTIAL', reason='No completed historical valuation source review. See separately dated monitoring.', sources=[]),
            insider=dict(status='PARTIAL', reason='No complete historical insider window certified.', coverage=dict(complete=False), sources=[], limitations=['See separately dated monitoring for current attempted coverage.'], transactions=[])))
        entry['monitoring'] = dict(as_of='2026-11-22', attempted_at='2026-11-22T08:03:19+00:00',
            window_start='2026-08-24', window_end='2026-11-22', coverage='PARTIAL',
            sources=refs, gap=gap, next_check_date=row.get('next_check_date') or '2026-11-30',
            financial_period=row.get('financial_period'),
            evidence_packet='docs/analysis/issuer-events-20261122/' + next(
                p.name for p in sorted(HERE.glob('*.json')) if ticker in json.loads(p.read_text()).get('issuers', {})),
            payments=row.get('payment_ledger', row.get('payments', row.get('observations', []))),
            next_common_payment=row.get('next_common_payment'),
            insider_attempt=row.get('insider'),
            summary=SUMMARIES[ticker],
            note='Partial source/payment review only. Existing valuation and insider checks retain their old dates. YTD is not TTM; payable is not proof of payment.')
        monitor = entry['monitoring']
        monitor['evidence_sha256'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                    for p in HERE.glob('*.json')}
        if ticker in ('INTU', 'NVDA'):
            packet = json.loads((HERE / (ticker.lower() + '-insider-evidence.json')).read_text())
            monitor['insider_attempt'] = dict(status='PARTIAL', window_start=packet['window_start'],
                window_end=packet['window_end'], retrieved_at=packet['retrieved_at'],
                documents_read=len(packet['documents']),
                gap='Native SEC listing and original documents retrieved; complete row/plan adjudication remains partial. No net trade signal.',
                packet=ticker.lower() + '-insider-evidence.json')
            monitor['summary'] += (' Current insider window: 24/24 documents read, rows remain unaggregated.'
                                   if ticker == 'INTU' else ' Current insider window: 16/16 documents read; Parker 4/A replaces original award, not an extra trade.')
    (ROOT / 'source_reviews.json').write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n')


if __name__ == '__main__':
    main()
