"""SEC Form 4 insider purchases: only code P counts and nothing enters the score."""
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import insider

ASOF = datetime(2026, 10, 31, 12, tzinfo=timezone.utc)


def form4(code, shares, price, when, director=True, title=None, name='Habiger David'):
    officer = f'<isOfficer>1</isOfficer><officerTitle>{title}</officerTitle>' if title else ''
    return f'''<?xml version="1.0"?><ownershipDocument>
<reportingOwner><reportingOwnerId><rptOwnerName>{name}</rptOwnerName></reportingOwnerId>
<reportingOwnerRelationship><isDirector>{1 if director else 0}</isDirector>{officer}</reportingOwnerRelationship></reportingOwner>
<nonDerivativeTable><nonDerivativeTransaction><transactionDate><value>{when}</value></transactionDate>
<transactionCoding><transactionCode>{code}</transactionCode></transactionCoding>
<transactionAmounts><transactionShares><value>{shares}</value></transactionShares>
<transactionPricePerShare><value>{price}</value></transactionPricePerShare>
<transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode></transactionAmounts>
</nonDerivativeTransaction></nonDerivativeTable></ownershipDocument>'''


class FakeClient:
    def __init__(self, documents):
        self.documents = documents
        self.texts = 0

    def get_json(self, url):
        if url == insider.TICKERS_URL:
            return dict(fields=['cik', 'name', 'ticker', 'exchange'], data=[[885725, 'Boston Scientific', 'BSX', 'NYSE']])
        names = list(self.documents)
        return dict(filings=dict(recent=dict(form=['4'] * len(names), accessionNumber=names,
            filingDate=['2026-08-06'] * len(names), primaryDocument=['xslF345X05/' + n + '.xml' for n in names])))

    def get_text(self, url):
        self.texts += 1
        return self.documents[url.rsplit('/', 1)[-1][:-4]]


class InsiderTests(unittest.TestCase):
    def test_only_open_market_purchases_count_as_buys(self):
        rows = (insider.parse_form4(form4('P', 2100, 47.589, '2026-08-05'))
                + insider.parse_form4(form4('I', 22119, 48.43, '2026-08-03', director=False, title='CEO', name='Mahoney'))
                + insider.parse_form4(form4('A', 3800, 0, '2026-05-07', name='Zane'))
                + insider.parse_form4(form4('P', 3580, 56.68, '2026-05-21', name='Ludwig')))
        summary = insider.summarize(rows, as_of=ASOF)
        self.assertEqual(summary['purchases'], 2)
        self.assertEqual(summary['buyers'], 2)
        self.assertEqual(summary['shares_bought'], 5680)
        self.assertAlmostEqual(summary['value_bought'], 2100 * 47.589 + 3580 * 56.68)
        self.assertEqual(summary['last_purchase'], '2026-08-05')
        self.assertEqual(summary['buyer_roles'], ['Director'])

    def test_purchases_outside_the_window_are_ignored(self):
        rows = insider.parse_form4(form4('P', 1000, 90, '2026-03-01'))
        self.assertEqual(insider.summarize(rows, as_of=ASOF)['purchases'], 0)

    def test_malformed_filing_is_empty_not_an_error(self):
        self.assertEqual(insider.parse_form4('<not xml'), [])

    def test_refresh_attaches_us_rows_and_reuses_cached_filings(self):
        client = FakeClient({'0001': form4('P', 2100, 47.589, '2026-08-05')})
        data = {'BSX': dict(yf='BSX', cur='USD'), 'ASML': dict(yf='ASML.AS', cur='EUR')}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'cache.json'
            insider.refresh(data, client, as_of=ASOF, cache_path=path, log=lambda *a: None)
            self.assertEqual(data['BSX']['insider_activity']['purchases'], 1)
            self.assertIsNone(data['ASML']['insider_activity'])
            insider.refresh(data, client, as_of=ASOF, cache_path=path, log=lambda *a: None)
            self.assertEqual(client.texts, 1)
            self.assertIn('0001', json.loads(path.read_text())['filings'])

    def test_view_shows_buys_and_signal_ignores_them(self):
        import opportunity_view
        from test_opportunity import ASOF as OASOF, priced_row
        from test_framework_contract import engine
        plain = engine.opportunity(priced_row(), regime='REFLATION', as_of=OASOF)
        value = priced_row()
        value['insider_activity'] = insider.summarize(
            insider.parse_form4(form4('P', 2100, 47.589, '2026-08-05')), as_of=ASOF)
        bought = engine.opportunity(value, regime='REFLATION', as_of=OASOF)
        self.assertEqual(plain['score'], bought['score'])
        self.assertIn('1 insider buyers', opportunity_view.insiders(bought))
        self.assertIn('not available', opportunity_view.insiders(plain))

    def test_build_skips_quietly_without_an_sec_agent(self):
        from unittest.mock import patch
        from test_framework_contract import engine
        with patch.dict('os.environ', {'SEC_USER_AGENT': ''}):
            self.assertIsNone(engine.refresh_insiders())


if __name__ == '__main__':
    unittest.main()
