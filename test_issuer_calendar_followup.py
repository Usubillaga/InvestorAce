"""Forward calendars, complete disclosure inventories and cash-payment evidence."""
import copy
import hashlib
import json
import unittest
from pathlib import Path

import source_review


ROOT = Path(__file__).parent
BATCH = ROOT / 'docs/analysis/issuer-events-20261125'


class NovemberCalendarFollowup(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.register = source_review.load()
        cls.calendar = cls.register['calendar_checks']['issuers']
        cls.insiders = json.loads((BATCH / 'insiders.json').read_text())['issuers']

    def test_calendar_initializations_cover_the_unmonitored_active_listings(self):
        observation = ROOT / 'history/runs/20261125T060416260690-22422c486bb94c3d9f83d74343db38c2.json'
        baseline = json.loads(observation.read_text())
        listings = baseline['_evidence']['inputs']
        earlier = baseline['_source_reviews']['entries']
        batch = json.loads((BATCH / 'packet.json').read_text())
        already_monitored = {k for k, e in earlier.items() if e.get('monitoring')} | set(batch['issuers'])
        self.assertEqual(set(self.calendar), set(listings) - already_monitored)
        self.assertEqual(len(self.calendar), 96)
        for ticker, row in self.calendar.items():
            self.assertEqual(row['listing_symbol'], listings[ticker].get('yf') or ticker)
            self.assertTrue(row['sources'])
        self.assertEqual(self.calendar['SAN']['listing_symbol'], 'SAN.PA')
        fund = self.calendar['JEQE']
        self.assertEqual(fund['asset_type'], 'FUND')
        self.assertTrue(all(e['kind'] == 'fund' for e in fund['events']))
        self.assertEqual(fund['events'][0]['amount'], .2096)
        self.assertIsNone(fund['events'][1]['amount'])
        events = self.calendar['REP']['events']
        self.assertEqual({e['status'] for e in events}, {'APPROVED_SCHEDULED', 'PROPOSED'})

    def test_future_and_unverified_payments_stay_separate(self):
        monitoring = self.register['entries']['ENS']['monitoring']
        self.assertEqual(monitoring['next_common_payment']['payable_date'], '2026-12-31')
        self.assertIsNone(monitoring['next_common_payment']['actual_payment_date'])
        paid = next(e for e in monitoring['payment_events'] if e.get('status') == 'PAYMENT_CONFIRMED')
        self.assertEqual(paid['actual_payment_date'], '2026-10-02')
        self.assertTrue(paid['payment_evidence_url'])
        html = source_review.panel({'ENS', 'ELE', 'CTVA'}, self.register)
        self.assertIn('Scheduled payable date · 2026-12-31 · common', html)
        self.assertIn('Payment confirmed · 2026-10-02 · common', html)
        self.assertNotIn('Payment confirmed · 2026-12-31', html)
        self.assertEqual(html.count('Scheduled payable date · 2027-01-12 · common'), 1)
        self.assertIn('2027-01-25 · EIDP, Inc. preferred', html)
        for field in ('actual_payment_date', 'actual_paid_date'):
            doc = copy.deepcopy(self.register)
            doc['calendar_checks']['issuers']['JEQE']['events'][0][field] = '2026-11-27'
            with self.assertRaises(ValueError):
                source_review.load(json.dumps(doc))
        doc = copy.deepcopy(self.register)
        preferred = doc['entries']['CTVA']['monitoring']['payment_events'][0]
        preferred['actual_paid_date'] = preferred['payable_date']
        with self.assertRaises(ValueError):
            source_review.load(json.dumps(doc))
        for field in ('payment_evidence_url', 'actual_payment_date'):
            doc = copy.deepcopy(self.register)
            doc['entries']['ENS']['monitoring']['payment_events'][-1].pop(field)
            with self.assertRaises(ValueError):
                source_review.load(json.dumps(doc))

    def test_disclosure_rows_and_partial_windows_match_the_evidence(self):
        digest = hashlib.sha256((BATCH / 'insiders.json').read_bytes()).hexdigest()
        for ticker, evidence in self.insiders.items():
            entry = self.register['entries'][ticker]
            insider = entry['insider']
            self.assertEqual(insider['coverage']['complete'], evidence['whole_window_disclosure_coverage'])
            self.assertEqual(entry['monitoring']['evidence_sha256']['insiders.json'], digest)
            self.assertEqual(entry['monitoring']['insider_attempt']['status'], insider['status'])
        partial = {k for k in self.insiders if self.register['entries'][k]['insider']['status'] == 'PARTIAL'}
        self.assertEqual(partial, {'ANT', 'FNV'})
        self.assertEqual(self.register['entries']['CPAY']['insider']['transactions'], [])
        self.assertEqual(len(self.register['entries']['ELE']['insider']['transactions']), 7)
        self.assertEqual(len(self.register['entries']['FICO']['insider']['transactions']), 43)
