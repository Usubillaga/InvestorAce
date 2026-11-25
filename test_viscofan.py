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
    """Yahoo's packet for VIS.MC: a newer period but no cash flow or share count."""
    return dict(schema=live_analysis.VERSION, symbol='VIS.MC', fetched_at=NOW.isoformat(),
                currency='EUR', financial_currency='EUR', financial_period='2026-09-30', basis='TTM',
                beta=.45, quote_price=54.0, quote_observed_at=NOW.isoformat(), inputs=inputs)


class Viscofan(unittest.TestCase):
    def setUp(self):
        self.packet = source_review.load()['entries']['VIS']['valuation']['financial_packet']

    def test_packet_bridges_the_issuer_net_debt_walk(self):
        i = self.packet['inputs']
        # FY2025 net-bank-debt bridge (EUR m): 146.9 - 290.0 + 46.4 + 49.9 + 84.1 + 8.9 + 14.8 + 145.1 = 206.1
        self.assertAlmostEqual(146.9 - 290.0 + 46.4 + 49.9 + 84.1 + 8.9 + 14.8 + 145.1, 206.1, places=6)
        self.assertEqual(i['operating_cash_flow'], round((290.0 - 46.4 - 49.9 - 14.8) * 1e6))
        self.assertEqual(i['operating_cash_flow'] - i['capex'], i['fcf'])
        self.assertEqual((i['debt'] - i['cash']) / 1e6, 206.103)        # matches the reported 206.1
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
        self.assertEqual((a['inputs']['fcf'], a['inputs']['shares']), (94.8e6, 46e6))
        self.assertAlmostEqual(a['metrics']['fcf_yield_pct'], 100 * 94.8 / (46 * 54))
        self.assertEqual(a['metrics']['revenue_growth_pct'], 100 * (1252.0 / 1204.0 - 1))
        result = engine.opportunity(row, regime='REFLATION', as_of=NOW)
        self.assertIsNotNone(result['label'])

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
        for figure in ('965.4', '207.7', '111.8', '266.6', '290', '94.8'):
            self.assertIn(figure, page)


if __name__ == '__main__':
    unittest.main()
