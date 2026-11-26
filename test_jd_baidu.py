"""Issuer cash-flow and ADS identity through the production refresh and scoring paths."""
import copy
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import engine
import live_analysis
import source_review


NOW = datetime(2026, 11, 25, 18, 38, tzinfo=timezone.utc)
MIX = dict(GOLDILOCKS=.468, REFLATION=.4327, INFLATION=.0763, STAGFLATION=.012, RECESSION=.011)


class DepositaryShares(unittest.TestCase):
    def refresh(self, ticker, as_of=NOW, provider=None):
        row = copy.deepcopy(engine.DATA[ticker])
        with tempfile.TemporaryDirectory() as tmp, patch.dict(engine.DATA, {ticker: row}, clear=True), \
                patch.object(live_analysis, 'extract', return_value=provider), \
                patch.object(engine.WACC, 'resolve_risk_free', return_value=4.840000152587891):
            engine.refresh_dynamic_analysis(Path(tmp) / 'facts.json', as_of=as_of, ticker_factory=lambda _: object())
        return row

    def test_jd_model_and_proxy_bridge(self):
        # Even a complete provider with a later period cannot replace the ADS
        # and capex reconciliation. A contemporaneous issuer price stays dated.
        provider = dict(symbol='JD', schema=live_analysis.VERSION, currency='USD',
                        financial_currency='CNY', financial_period='2026-10-31',
                        inputs=dict(fcf=99, shares=5))
        row = self.refresh('JD', provider=provider)
        a = row['dynamic_analysis']
        self.assertEqual(a['financial_period'], '2026-09-30')
        self.assertEqual(a['inputs']['shares'], 2691000000 / 2)
        self.assertEqual(a['inputs']['valuation_fcf'], (40444-20898-4487) * 1e6)
        self.assertAlmostEqual(a['metrics']['fcf_yield_pct'], 6.52687, places=4)
        self.assertAlmostEqual(a['metrics']['shareholder_yield_pct'], 100/25.73+100*(1-2691/2838))
        opp = engine.opportunity(row, regime='REFLATION', weights=MIX, as_of=NOW)
        self.assertEqual((opp['label'], opp['review_status']), ('Hold Positive', 'REVIEW_REQUIRED'))
        self.assertAlmostEqual(opp['score'], 5.94893, places=4)

    def test_baidu_negative_cash_has_no_reverse_dcf(self):
        row = self.refresh('BIDU')
        a = row['dynamic_analysis']
        self.assertEqual(a['inputs']['shares'], (2211573730+524020320-15029832)/8)
        self.assertEqual(a['inputs']['fcf'], -15134e6)
        self.assertEqual(a['inputs']['valuation_fcf'], -18165e6)
        self.assertIsNone(a['valuation']['reverse_dcf_growth_pct'])
        self.assertAlmostEqual(a['metrics']['fcf_yield_pct'], -12.61992, places=4)
        o = engine.opportunity(row, regime='REFLATION', weights=MIX, as_of=NOW)
        self.assertIsNone(o['label'])
        self.assertIsNone(o['score'])
        self.assertLess(o['score_lower'], o['score_upper'])

    def test_stale_reference_or_future_publication_cannot_create_a_score(self):
        for as_of in (NOW - timedelta(days=1), NOW + timedelta(days=4)):
            with self.subTest(as_of=as_of):
                row = self.refresh('JD', as_of=as_of)
                self.assertIsNone(row.get('price'))
                self.assertIsNone(engine.opportunity(row, regime='REFLATION', as_of=as_of)['label'])

    def test_mismatched_depositary_units_rejected(self):
        p = copy.deepcopy(source_review.load()['entries']['BIDU']['valuation']['financial_packet'])
        p['inputs']['shares'] *= 8
        with self.assertRaisesRegex(ValueError, 'share bridge'):
            live_analysis.prefer_primary(dict(symbol='BIDU'), p, as_of=NOW)
