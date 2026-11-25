"""Forgent's post-IPO share count and the cash available per economic interest."""
import copy
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import engine
import live_analysis
import source_review


class Forgent(unittest.TestCase):
    now = datetime.fromisoformat('2026-11-25T20:37:00+00:00')

    def test_upc_units_and_pre_ipo_financials_survive_vendor_refresh(self):
        for period in ('2026-09-30', '2026-12-31'):
            with self.subTest(period=period):
                row = copy.deepcopy(engine.DATA['FPS'])
                provider = dict(symbol='FPS', schema=live_analysis.VERSION, currency='USD',
                                financial_currency='USD', financial_period=period, basis='TTM',
                                inputs=dict(shares=274527094, net_income=145302000),
                                share_change_pct=80, annual_net_income_series=[
                                    dict(period='2025-06-30', value=15196000)])
                with tempfile.TemporaryDirectory() as tmp, patch.dict(engine.DATA, {'FPS': row}, clear=True), \
                        patch.object(live_analysis, 'extract', return_value=provider), \
                        patch.object(engine.WACC, 'resolve_risk_free', return_value=4.838):
                    engine.refresh_dynamic_analysis(Path(tmp) / 'facts.json', as_of=self.now,
                                                    ticker_factory=lambda _: object())
                a = row['dynamic_analysis']
                self.assertEqual(a['financial_period'], '2026-09-30')
                self.assertEqual(a['inputs']['shares'], 274527094 + 29901795)
                self.assertEqual(a['inputs']['valuation_fcf'],
                                 (109081 + 136115 - 5935 - (115905 + 31706 - 29889)
                                  - (10036 + 13884 - 560)) * 1000)
                self.assertAlmostEqual(a['metrics']['fcf_yield_pct'], 1.731091, places=5)
                for key in ('reported_pe', 'share_change_pct'):
                    self.assertIsNone(a['metrics'][key])
                self.assertIsNone(a['valuation']['reverse_dcf_growth_pct'])
                model = engine.opportunity(row, regime='REFLATION', as_of=self.now)
                self.assertAlmostEqual(model['quality_score'], 6.244444, places=5)
                self.assertIsNone(model['label'])
                self.assertLess(model['score_lower'], model['score_upper'])

    def test_rejects_double_counted_exchangeable_interests(self):
        p = copy.deepcopy(source_review.load()['entries']['FPS']['valuation']['financial_packet'])
        p['inputs']['shares'] += p['upc_interests']['paired_opco_units']
        with self.assertRaisesRegex(ValueError, 'Up-C share bridge'):
            live_analysis.prefer_primary(dict(symbol='FPS'), p, as_of=self.now)
