"""Mechanical diagnostic projection; no authority, dates or numerical inputs replaced."""
import hashlib
import json
from pathlib import Path
HERE=Path(__file__).parent
ROOT=HERE.parents[2]
def main():
    packet=json.loads((HERE/'packet.json').read_text())
    register=json.loads((ROOT/'source_reviews.json').read_text())
    for ticker,row in packet['issuers'].items():
        if ticker in register['entries']:
            raise ValueError('Expected new unreviewed entry; reconcile before replacing')
        register['entries'][ticker]=dict(issuer=row['issuer'],listing=row['listing_symbol']+' / '+row['currency'],
            valuation=dict(status='PARTIAL',reason='No completed valuation tie-out; separately dated monitoring only.',sources=[]),
            insider=dict(status='PARTIAL',reason='No complete current disclosure window certified.',sources=[],
                         coverage=dict(complete=False),limitations=['See dated partial monitoring.'],transactions=[]),
            monitoring=dict(as_of='2026-11-24',attempted_at=packet['as_of'],window_start=packet['window_start'],
                window_end=packet['window_end'],coverage='PARTIAL',sources=row['sources'],gap=row['gap'],
                next_check_date=row['next_check_date'],financial_period=row['financial_period'],summary=row['summary'],
                payments=row['payments'],next_common_payment=row['next_common_payment'],next_earnings=row['next_earnings'],
                payment_events=[],insider_attempt=dict(status='PARTIAL',complete=False,gap=row['insider_gap'],events=[],sources=[]),
                evidence_packet='docs/analysis/issuer-events-20261124',
                evidence_sha256={'packet.json':hashlib.sha256((HERE/'packet.json').read_bytes()).hexdigest()},
                note='Partial source check only. Does not refresh valuation or insider checks; actual payment date unknown.'))
    (ROOT/'source_reviews.json').write_text(json.dumps(register,indent=2,ensure_ascii=False)+'\n')
if __name__=='__main__':
    main()
