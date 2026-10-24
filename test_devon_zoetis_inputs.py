"""Primary-review packets must not be replaced with incompatible Yahoo periods."""
import copy
from datetime import datetime, timezone
import unittest
from unittest.mock import patch

import pandas as pd

import evidence
import source_review
from test_framework_contract import engine


class PrimaryReviewBootstrap(unittest.TestCase):
    def test_unresolved_primary_packets_survive_both_bootstrap_paths(self):
        rows = {
            'MERGER': dict(yf='MERGER', fcf=None, shares=1149.9, midcycle=True,
                           fundamentals_refresh='PRIMARY_REVIEW_ONLY',
                           boot_note='Full combined normalization unresolved'),
            'RECAST': dict(yf='RECAST', fcf=None, shares=414.154046,
                           fundamentals_refresh='PRIMARY_REVIEW_ONLY',
                           boot_note='Annual recast unresolved'),
            'REVIEWED': dict(yf='REVIEWED', fcf=4500, shares=1160, midcycle=True,
                            fundamentals_refresh='PRIMARY_REVIEW_ONLY'),
        }
        expected = copy.deepcopy(rows)

        class Yahoo:
            fast_info = {'shares': 999e6}
            quarterly_cashflow = pd.DataFrame(
                [[900e6] * 4], index=['Free Cash Flow'])
            cashflow = quarterly_cashflow

        with patch.object(engine, 'DATA', rows), \
             patch.object(engine.yf, 'Ticker', return_value=Yahoo()):
            engine.bootstrap_fundamentals()
        self.assertEqual(rows, expected)

    def test_opt_in_guard_keeps_ordinary_draft_and_producer_refresh(self):
        rows = {'DRAFT': dict(fcf=None, shares=None),
                'PRODUCER': dict(fcf=100, shares=20, midcycle=True)}

        class Yahoo:
            fast_info = {'shares': 40e6}
            quarterly_cashflow = pd.DataFrame(
                [[50e6] * 4], index=['Free Cash Flow'])
            cashflow = quarterly_cashflow

        with patch.object(engine, 'DATA', rows), \
             patch.object(engine.yf, 'Ticker', return_value=Yahoo()):
            engine.bootstrap_fundamentals()
        self.assertEqual(rows['DRAFT']['fcf'], 200)
        self.assertEqual(rows['DRAFT']['shares'], 40)
        self.assertEqual(rows['PRODUCER']['fcf'], 50)
        self.assertEqual(rows['PRODUCER']['shares'], 20)


class DevonZoetisReview(unittest.TestCase):
    def test_no_quarter_or_half_year_cash_is_capitalized_as_annual_ngv(self):
        for ticker, price in (('DVN', 51.51), ('ZTS', 80.93)):
            with self.subTest(ticker=ticker):
                row = copy.deepcopy(engine.DATA[ticker])
                row.update(price=price, quote_observed_at='2026-10-23T18:39:00Z')
                original = copy.deepcopy(row)
                with patch.object(engine, 'DATA', {ticker: row}), \
                     patch.object(engine.yf, 'Ticker', side_effect=RuntimeError('offline')):
                    engine.bootstrap_fundamentals()
                self.assertEqual(row, original)
                self.assertIsNone(engine.ngv(row))
                self.assertIsNone(engine.cover(row))
                self.assertIsNone(engine.cushion(row))
                self.assertEqual(row['normalization_status'], 'REVIEW_REQUIRED')
                checked = engine.assessment(row, ticker=ticker,
                    as_of=datetime(2026, 10, 23, 20, tzinfo=timezone.utc))
                self.assertIsNone(checked['rating'])
                self.assertIsNone(checked['model_score'])
                self.assertFalse(checked['new_entry_eligible'])

    def test_devon_cash_bridge_retains_working_capital_and_acquisition_limits(self):
        row = engine.DATA['DVN']
        self.assertAlmostEqual(row['shares'], 1149.9)
        self.assertEqual(row['shares_asof'], '2026-06-30')
        q = row['reported_cash_flow']['q2_2026']
        self.assertEqual(q['ocf'] - q['cash_capex'], 2356)
        self.assertEqual(q['ocf'] - q['balance_sheet_changes']
                         + q['after_tax_restructuring'] - q['accrued_operating_capex'], 1655)
        self.assertEqual(q['ocf'] - q['cash_capex'] - q['property_acquisitions'], -373)
        self.assertIsNone(row['fcf_ttm'])
        self.assertEqual(evidence.valuation_contract(row)['status'], 'UNVERIFIED')

    def test_zoetis_uses_recast_half_year_and_dated_outstanding_shares(self):
        row = engine.DATA['ZTS']
        self.assertAlmostEqual(row['shares'], 413.223602)
        self.assertEqual(row['shares_asof'], '2026-07-31')
        cash = row['reported_cash_flow']
        self.assertEqual(cash['h1_2026']['ocf'] - cash['h1_2026']['cash_capex'], 829)
        self.assertEqual(cash['h1_2025_recast']['ocf'] - cash['h1_2025_recast']['cash_capex'], 796)
        self.assertEqual(cash['h1_2026']['cash_dividends']
                         + cash['h1_2026']['cash_buybacks_including_excise'], 1637)
        self.assertIsNone(row['fcf_ttm'])
        self.assertEqual(row['score_fixed'], 4.55)  # historical total, no new approval

    def test_existing_report_exposes_partial_checks_and_preserves_evidence(self):
        reviews = source_review.load()
        rows = {t: dict(engine.DATA[t], price=p) for t, p in (('DVN', 51.51), ('ZTS', 80.93))}
        for t in rows:
            self.assertIn(t, reviews['entries'])
            self.assertFalse(reviews['entries'][t]['insider']['coverage']['complete'])
        with patch.object(engine, 'DATA', rows), \
             patch.object(engine, 'sector_performance', return_value={}), \
             patch.object(engine, 'forward_run', return_value={'ok': False, 'note': 'offline'}):
            html = engine.build_html(macro={'ok': False}, write=False, reviews=reviews)
        for phrase in ('review-DVN', 'review-ZTS', 'Coterra', 'recast',
                       '36.91', '6.15', 'Eagle Ford', 'NORMALIZATION REVIEW'):
            self.assertIn(phrase, html)
        record = evidence.create_record(rows, {}, {}, {}, 'test-source')
        self.assertEqual(record['_evidence']['inputs']['DVN']['reported_cash_flow'],
                         rows['DVN']['reported_cash_flow'])
        self.assertEqual(engine.regime_spec_sha256(), engine.REGIME_SPEC_EXPECTED_SHA256)


if __name__ == '__main__':
    unittest.main()
