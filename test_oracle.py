"""Reconcile Oracle's issuer statements and the dated v18 scoreboard."""
import copy
import re
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import engine
import market_scanner


class OracleScoreboard(unittest.TestCase):
    cutoff = datetime(2026, 11, 25, 23, 30, tzinfo=timezone.utc)

    def refresh(self, provider=None):
        row = copy.deepcopy(engine.DATA['ORCL'])
        with tempfile.TemporaryDirectory() as tmp, patch.dict(engine.DATA, {'ORCL': row}, clear=True), \
                patch.object(engine.LIVE_ANALYSIS, 'extract', return_value=provider), \
                patch.object(engine.WACC, 'resolve_risk_free', return_value=4.8):
            engine.refresh_dynamic_analysis(Path(tmp) / 'cache.json', as_of=self.cutoff,
                                            ticker_factory=lambda _: object())
        return row

    def test_ticker_directory_is_unique(self):
        symbols = re.findall(r'\byf\s*:\s*["\']([^"\']+)["\']', Path('tickers.js').read_text())
        self.assertEqual(symbols.count(engine.DATA['ORCL']['yf']), 1)
        self.assertCountEqual(symbols, set(symbols))

    def test_primary_cash_and_score_without_provider(self):
        row = self.refresh()
        analysis = row['dynamic_analysis']
        inputs = analysis['inputs']
        # FY26 + Q1 FY27 - Q1 FY26. Filing figures in USD millions.
        self.assertEqual(inputs['operating_cash_flow'], (31977 + 23103 - 8140) * 1e6)
        self.assertEqual(inputs['capex'], (55663 + 28499 - 8502) * 1e6)
        self.assertEqual(inputs['stock_based_compensation'], (4811 + 1127 - 1124) * 1e6)
        self.assertEqual(inputs['fcf'] - inputs['common_fcf'], (63 + 81) * 1e6)
        self.assertEqual(inputs['shares'], 3031501149)
        self.assertEqual(row['price'], 103.88)
        for key in ('ngv_per_share', 'dcf_per_share', 'reverse_dcf_growth_pct'):
            self.assertIsNone(analysis['valuation'][key])
        self.assertEqual(inputs['fcf'], -28720e6)
        self.assertEqual(inputs['common_fcf'], -28864e6)
        self.assertEqual(inputs['valuation_fcf'], -33678e6)
        self.assertEqual(inputs['valuation_net_income'], 18736e6)
        score = engine.opportunity(row, regime='REFLATION', as_of=self.cutoff)
        self.assertAlmostEqual(score['score_lower'], 4.21576376)
        self.assertEqual(score['score_upper'], 5.49)
        self.assertIsNone(score['label'])
        self.assertIsNone(score['score'])
        report = Path(row['deep_dive']).read_text()
        for lang in ('de', 'en', 'es'):
            section = report.split(f'<section id="{lang}" lang="{lang}">')[1].split('</section>')[0]
            bounds = f"{score['score_lower']:.2f}–{score['score_upper']:.2f}"
            self.assertIn(bounds if lang == 'en' else bounds.replace('.', ','), section)

    def test_primary_priority_is_period_bound(self):
        primary = engine.SOURCE_REVIEW.load()['entries']['ORCL']['valuation']['financial_packet']
        provider = dict(symbol='ORCL', currency='USD', financial_currency='USD', basis='TTM',
                        financial_period='2026-08-31', beta=1.2,
                        inputs=dict(fcf=8e9, shares=4e9, stock_based_compensation=0))
        row = self.refresh(provider)
        analysis = row['dynamic_analysis']
        self.assertEqual(analysis['data_status'], 'PRIMARY_INPUTS')
        self.assertEqual(analysis['inputs']['valuation_fcf'], -33678e6)
        self.assertEqual(analysis['parameters']['reported_beta'], 1.2)
        newer = dict(provider, financial_period='2026-11-30')
        result = engine.LIVE_ANALYSIS.prefer_primary(
            newer, primary, as_of=datetime(2027, 1, 1, tzinfo=timezone.utc))
        self.assertEqual(result['inputs'], newer['inputs'])
        self.assertFalse(result.get('primary_current'))
        before = datetime(2026, 11, 24, tzinfo=timezone.utc)
        self.assertEqual(engine.LIVE_ANALYSIS.prefer_primary(provider, primary, as_of=before), provider)

    def test_scanner_keeps_partial_score_and_issuer_date(self):
        row = self.refresh()
        register = engine.SOURCE_REVIEW.load()
        # A later register assembly (as in PR 246) is not a new Oracle review.
        register['as_of'] = '2026-11-26'
        score = engine.opportunity(row, regime='REFLATION', as_of=self.cutoff)
        record = dict(ORCL=dict(opportunity=score), _source_reviews=register,
                      _evidence=dict(inputs=dict(ORCL=row), captured_at=self.cutoff.isoformat()))
        scan = market_scanner.build_scan(record, as_of=datetime(2026, 11, 26, tzinfo=timezone.utc))
        item, = scan['rows']
        self.assertEqual(item['ticker'], 'ORCL')
        self.assertEqual(item['source_status'], 'PARTIAL')
        self.assertEqual(item['source_review_as_of'], '2026-11-25')
        self.assertEqual(item['opportunity']['score_upper'], 5.49)
        self.assertAlmostEqual(item['opportunity']['score_lower'], 4.21576376)
        self.assertIsNone(item['opportunity']['label'])
        self.assertIsNone(item['opportunity']['score'])
        self.assertIsNone(item['rating'])
