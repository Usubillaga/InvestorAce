"""Viscofan (VIS.MC) enters the universe from issuer documents (no network)."""
import copy
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import engine
import live_analysis
import source_review

ROOT = Path(__file__).parent
NOW = datetime(2026, 11, 25, 18, tzinfo=timezone.utc)


def provider(**inputs):
    """An incomplete provider packet for a more recent period."""
    return dict(schema=live_analysis.VERSION, symbol='VIS.MC', fetched_at=NOW.isoformat(),
                currency='EUR', financial_currency='EUR', financial_period='2026-09-30', basis='TTM',
                beta=.45, quote_price=54.0, quote_observed_at=NOW.isoformat(), inputs=inputs)


class Viscofan(unittest.TestCase):
    def setUp(self):
        self.packet = source_review.load()['entries']['VIS']['valuation']['financial_packet']

    def test_audited_cash_flow_and_outstanding_shares(self):
        i = self.packet['inputs']
        self.assertEqual(i['operating_cash_flow'], 195_369_000)
        self.assertEqual(i['capex'], 80_447_000)
        self.assertEqual(i['fcf'], i['operating_cash_flow'] - i['capex'])
        self.assertEqual(i['fcf'] - i['stock_based_compensation'], 108_147_000)
        self.assertEqual(i['dividends'] + 93_984_000, 145_128_000)
        self.assertEqual(i['debt'] - i['cash'], 238_226_000)
        self.assertEqual(i['shares'], 46_000_000 - 396_357)
        self.assertAlmostEqual(self.packet['share_change_pct'], 100 * (i['shares'] / (46_500_000 - 572_358) - 1))
        self.assertEqual(i['ebitda'] - i['operating_income'], i['depreciation'])
        self.assertEqual(self.packet['symbol'], engine.DATA['VIS']['yf'])

    def test_issuer_packet_replaces_a_provider_without_cash_flow(self):
        row = copy.deepcopy(engine.DATA['VIS'])
        row.update(price=54.0, quote_observed_at=NOW.isoformat())
        with tempfile.TemporaryDirectory() as tmp, patch.dict(engine.DATA, clear=True, values={'VIS': row}), \
                patch.object(live_analysis, 'extract', return_value=provider(revenue=1280e6)):
            engine.refresh_dynamic_analysis(Path(tmp) / 'facts.json', as_of=NOW, ticker_factory=lambda _: object())
        a = row['dynamic_analysis']
        self.assertEqual(a['data_status'], 'PRIMARY_INPUTS')
        self.assertEqual((a['inputs']['fcf'], a['inputs']['shares']), (114_922_000, 45_603_643))
        self.assertAlmostEqual(a['metrics']['fcf_yield_pct'], 100 * 108_147_000 / (45_603_643 * 54))
        self.assertEqual(a['metrics']['revenue_growth_pct'], 100 * (1251983 / 1203994 - 1))
        result = engine.opportunity(row, regime='REFLATION', as_of=NOW)
        self.assertIsNotNone(result['label'])

    def test_dated_score_uses_audited_cash_and_preserves_review_status(self):
        # Archived regime mix and risk-free rate at the last build before the quote.
        weights = dict(GOLDILOCKS=.469, REFLATION=.4316, INFLATION=.0758,
                       STAGFLATION=.0122, RECESSION=.0113)
        row = copy.deepcopy(engine.DATA['VIS'])
        row.update(price=53.70, quote_observed_at='2026-11-25T15:24:00+00:00')
        with tempfile.TemporaryDirectory() as tmp, patch.dict(engine.DATA, clear=True, values={'VIS': row}), \
                patch.object(live_analysis, 'extract', return_value=provider(revenue=1280e6)), \
                patch.object(engine.WACC, 'resolve_risk_free', return_value=4.8380003):
            engine.refresh_dynamic_analysis(Path(tmp) / 'facts.json', as_of=NOW, ticker_factory=lambda _: object())
        result = engine.opportunity(row, regime='REFLATION', weights=weights, as_of=NOW)
        self.assertAlmostEqual(result['score'], 5.98515, places=4)
        self.assertEqual((result['label'], result['review_status']), ('Hold Positive', 'REVIEW_REQUIRED'))
        self.assertIsNone(result['price_thresholds']['buy'])

    def test_flag_is_needed_for_a_newer_provider_period(self):
        row = copy.deepcopy(engine.DATA['VIS'])
        row.pop('primary_inputs_only')
        row.update(price=54.0, quote_observed_at=NOW.isoformat())
        with tempfile.TemporaryDirectory() as tmp, patch.dict(engine.DATA, clear=True, values={'VIS': row}), \
                patch.object(live_analysis, 'extract', return_value=provider(revenue=1280e6)):
            engine.refresh_dynamic_analysis(Path(tmp) / 'facts.json', as_of=NOW, ticker_factory=lambda _: object())
        self.assertNotEqual(row['dynamic_analysis']['data_status'], 'PRIMARY_INPUTS')

    def test_listed_with_its_deep_dive(self):
        self.assertIn('{yf:"VIS.MC",name:"Viscofan"', (ROOT / 'tickers.js').read_text())
        page = (ROOT / 'earnings' / 'viscofan-deep-dive-2026-11-25.html').read_text()
        for figure in ('965.4', '207.7', '111.8', '266.6', '290', '114.922', '108.147'):
            self.assertIn(figure, page)


if __name__ == '__main__':
    unittest.main()
