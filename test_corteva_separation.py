"""A post-spin symbol must not inherit predecessor cash, margins or beta."""
import copy
import json
import tempfile
import unittest
from types import SimpleNamespace
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pandas as pd

import engine
import live_analysis
import source_review
import stock_compare


AS_OF = datetime(2026, 11, 25, 9, tzinfo=timezone.utc)
ROOT = Path(__file__).parent


class CortevaSeparation(unittest.TestCase):
    def setUp(self):
        self.review = source_review.load()['entries']['CTVA']
        self.packet = self.review['valuation']['financial_packet']
        self.provider = dict(schema=live_analysis.VERSION, symbol='CTVA', currency='USD',
            financial_currency='USD', basis='TTM', financial_period='2026-09-30',
            fetched_at='2026-11-25T06:00:00Z', inputs=dict(fcf=2046e6, shares=667e6),
            beta=1.1, annual_fcf_series=[dict(period='2025-12-31', value=2815e6)],
            share_change_pct=-2., quote_price=8.16, quote_observed_at='2026-11-24T21:00:00Z')

    def test_scoped_cash_and_returns_on_fresh_and_cached_refresh(self):
        for cached in (False, True):
            with self.subTest(cached=cached), tempfile.TemporaryDirectory() as tmp:
                row = copy.deepcopy(engine.DATA['CTVA'])
                row.update(price=8.16, quote_observed_at='2026-11-24T21:00:00Z')
                cache = Path(tmp)/'facts.json'
                cache.write_text(json.dumps(dict(schema=live_analysis.VERSION, entries={'CTVA': self.provider})))
                with patch.object(engine, 'DATA', {'CTVA':row}), patch.object(live_analysis, 'extract',
                        return_value=None if cached else self.provider), patch.object(engine.WACC,
                        'resolve_risk_free', return_value=4.5):
                    engine.refresh_dynamic_analysis(cache, as_of=AS_OF, ticker_factory=lambda _: object())
                    with patch.object(engine.EPV, 'fetch', side_effect=AssertionError('pre-spin EPV fetch')):
                        engine.populate_epv()
                result = row['dynamic_analysis']
                self.assertEqual(result['data_status'], 'PRIMARY_INPUTS')
                self.assertEqual(result['inputs']['shares'], 667323000)
                self.assertEqual(result['inputs']['fcf'], -1063e6)
                self.assertEqual(result['inputs']['common_fcf'], -1073e6)
                self.assertEqual(result['parameters']['preferred_cash_basis'], 'DECLARED_STABLE_BALANCE')
                self.assertEqual(result['common_equity_basis']['current']['common_net_income'], 450e6)
                self.assertIsNone(result['inputs']['valuation_fcf'])
                self.assertIsNone(result['components']['b'])
                self.assertIsNone(result['parameters']['reported_beta'])
                self.assertIsNone(result['metrics']['share_change_pct'])
                op = engine.opportunity(row, regime='INFLATION', as_of=AS_OF)
                self.assertEqual(op['status'], 'BLOCKED_INPUTS')
                self.assertIsNone(op['label'])
                self.assertIsNone(op['score_lower'])
                self.assertIsNone(op['price_thresholds']['buy'])
                self.assertIsNone(engine.ngv(row))
                self.assertIsNone(engine.epv(row))

    def test_pre_spin_inputs_and_new_provider_quarter(self):
        old = live_analysis.prefer_primary(self.provider, self.packet,
            as_of=datetime(2026, 9, 30, tzinfo=timezone.utc))
        self.assertEqual(old, self.provider)
        before_review = live_analysis.prefer_primary(self.provider, self.packet,
            as_of=datetime(2026, 11, 24, tzinfo=timezone.utc))
        self.assertNotIn('inputs', before_review)
        self.assertNotIn('beta', before_review)
        self.assertEqual(before_review['quote_price'], 8.16)
        later = live_analysis.prefer_primary(dict(self.provider, financial_period='2026-12-31'),
            self.packet, as_of=datetime(2027, 2, 1, tzinfo=timezone.utc))
        self.assertEqual(later['unverified_financial_period'], '2026-12-31')
        self.assertTrue(later['awaiting_perimeter_packet'])
        self.assertNotIn('inputs', later)
        self.assertNotIn('financial_period', later)
        self.assertNotIn('primary_current', later)
        self.assertNotIn('annual_fcf_series', later)
        self.assertNotIn('share_change_pct', later)

    def test_new_incomplete_quarter_also_withdraws_old_current_inputs(self):
        december = dict(self.provider, financial_period='2026-12-31', inputs={'shares':667e6})
        row = copy.deepcopy(engine.DATA['CTVA'])
        february = datetime(2027, 2, 1, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as tmp, patch.object(engine, 'DATA', {'CTVA':row}), \
                patch.object(live_analysis, 'extract', return_value=december), \
                patch.object(engine.WACC, 'resolve_risk_free', return_value=4.5):
            cache = Path(tmp)/'facts.json'
            cache.write_text(json.dumps(dict(schema=live_analysis.VERSION, entries={'CTVA': self.provider})))
            engine.refresh_dynamic_analysis(cache, as_of=february, ticker_factory=lambda _: object())
            self.assertEqual(json.loads(cache.read_text())['entries']['CTVA']['financial_period'], '2026-12-31')
            for next_fetch in (None, self.provider):
                with patch.object(live_analysis, 'extract', return_value=next_fetch):
                    engine.refresh_dynamic_analysis(cache, as_of=february, ticker_factory=lambda _: object())
                self.assertEqual(row['dynamic_analysis']['data_status'], 'UNAVAILABLE')
        result = row['dynamic_analysis']
        self.assertEqual(result['unverified_financial_period'], '2026-12-31')
        self.assertEqual(result['data_status'], 'UNAVAILABLE')
        self.assertIsNone(result['financial_period'])
        self.assertIsNone(result['components']['p'])
        self.assertIsNone(result['metrics']['fcf_margin_pct'])
        self.assertIsNone(engine.ngv(row))

    def test_quote_history_and_rates_do_not_use_the_predecessor(self):
        dates = pd.bdate_range('2025-11-03', '2026-11-24', tz='UTC')
        tape = pd.DataFrame({'Close': [80 if d.month == 9 else 8.16 for d in dates]}, index=dates)
        ticker = SimpleNamespace(history=lambda **_: tape, fast_info={'lastPrice': 8.16},
            get_info=lambda: {'currency':'USD', 'regularMarketPrice':8.16,
                              'regularMarketTime':dates[-1].timestamp()})
        row = copy.deepcopy(engine.DATA['CTVA'])
        with patch.object(engine, 'DATA', {'CTVA':row}), patch.dict(engine._LIVE_TICKERS), \
                patch.object(engine.yf, 'Ticker', return_value=ticker), \
                patch.object(engine.WACC, 'fetch', side_effect=AssertionError('predecessor beta')) as fetch:
            engine.fetch_prices()
        fetch.assert_not_called()
        self.assertEqual(row['price'], 8.16)
        self.assertIsNone(row.get('mom_12_1'))
        self.assertIsNone(row.get('r_wacc'))
        self.assertEqual(engine.rate_used(row), (None, 'unavailable'))

    def test_peer_comparison_replaces_entire_predecessor_years(self):
        dirty = dict(listing='CTVA', financial_currency='USD', annual=[
            dict(period_end='2025-12-31', revenue=17401e6, debt=17e9),
            dict(period_end='2022-12-31', revenue=20e9)], market=dict(float_pct=98))
        output = stock_compare.apply_primary_annuals(dirty, self.review, as_of=AS_OF)
        self.assertEqual([r['period_end'][:4] for r in output['annual']], ['2025','2024','2023'])
        self.assertEqual(output['annual'][0]['revenue'], 7840e6)
        self.assertEqual(output['annual'][0]['fcf'], 214e6)
        self.assertIsNone(output['annual'][0].get('debt'))
        self.assertIsNone(output['market'].get('float_pct'))
        self.assertEqual(output['market']['shares_outstanding'], 667323000)
        self.assertEqual(dirty['annual'][0]['debt'], 17e9)


if __name__ == '__main__':
    unittest.main()
