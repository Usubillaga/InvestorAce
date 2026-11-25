"""Use the dated Corpay filing figures through the regular TTM valuation path."""
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pandas as pd

import live_analysis


class CorpayCashFlow(unittest.TestCase):
    def setUp(self):
        # Standalone quarters from FY 2025 and Q1–Q3 2026 cash statements.
        # Place issuer-defined “FCF” in the provider FCF row to catch substitution.
        quarters = pd.to_datetime(['2025-12-31', '2026-03-31', '2026-06-30', '2026-09-30'])
        cash = pd.DataFrame({
            'Operating Cash Flow': [812_738, -56_620, 1_470_099, -697_196],
            'Capital Expenditure': [-52_441, -51_092, -54_437, -37_853],
            'Stock Based Compensation': [27_811, 27_495, 32_014, 33_419],
            'Free Cash Flow': [423_576, 397_170, 464_384, 500_704],
        }, index=quarters).T * 1_000
        income = pd.DataFrame({'Net Income': [265_616, 353_714, 251_788, 382_280]},
                              index=quarters).T * 1_000
        shares = 63_971_827
        self.issuer = SimpleNamespace(
            quarterly_cashflow=cash, quarterly_income_stmt=income,
            get_info=lambda: dict(sharesOutstanding=shares, currency='USD',
                                  financialCurrency='USD', beta=1.0),
        )
        self.as_of = datetime(2026, 11, 25, 9, tzinfo=timezone.utc)
        self.pricing = dict(risk_free=.05, mrp=.05,
                            quote={'price': 447.91, 'observed_at': '2026-11-24T21:00:00+00:00'})

    def test_cash_components_take_precedence_over_management_adjusted_earnings(self):
        result = live_analysis.analyze(self.issuer, 'CPAY', as_of=self.as_of, **self.pricing)
        self.assertEqual(result['basis'], 'TTM')
        self.assertEqual(result['parameters']['cash_flow_calculation'], 'OCF_MINUS_ABS_CAPEX')
        self.assertEqual(result['inputs']['fcf'], 1_333_198_000)
        self.assertEqual(result['inputs']['stock_based_compensation'], 120_739_000)
        self.assertEqual(result['inputs']['valuation_fcf'], 1_212_459_000)
        self.assertAlmostEqual(result['metrics']['fcf_yield_pct'],
                               100 * 1_212_459_000 / (447.91 * 63_971_827))

    def test_missing_component_rejects_adjusted_earnings_in_new_and_legacy_packets(self):
        complete = self.issuer.quarterly_cashflow
        earlier = self.as_of - timedelta(seconds=1)
        for absent in ('Operating Cash Flow', 'Capital Expenditure'):
            with self.subTest(absent=absent):
                self.issuer.quarterly_cashflow = complete.drop(index=absent)
                legacy = live_analysis.extract(self.issuer, 'CPAY', as_of=earlier)
                self.assertEqual(legacy['inputs']['fcf'], 1_785_834_000)
                # Older caches can repeat the issuer-defined figure in the
                # common-equity row. Neither copy can supply a cash valuation.
                legacy['equity_periods'] = [
                    dict(legacy['inputs'], period=legacy['financial_period'], basis='TTM',
                         reported_fcf=1_785_834_000, scope='REPORTED')]
                fresh = live_analysis.extract(self.issuer, 'CPAY', as_of=self.as_of)
                self.assertEqual(fresh['basis'], 'TTM')
                self.assertIsNotNone(fresh['inputs']['net_income'])
                for facts in (fresh, legacy):
                    result = live_analysis.calculate(facts, as_of=self.as_of, **self.pricing)
                    self.assertIsNone(result['inputs']['fcf'])
                    self.assertIsNone(result['inputs']['valuation_fcf'])
                    self.assertIsNone(result['valuation']['ngv_per_share'])
                    self.assertIsNone(result['metrics']['fcf_yield_pct'])
                    self.assertEqual(result['parameters']['cash_flow_calculation'],
                                     'CASH_COMPONENTS_UNAVAILABLE')
                self.assertEqual(legacy['inputs']['fcf'], 1_785_834_000)
                before = live_analysis.calculate(legacy, as_of=earlier, **self.pricing)
                other = live_analysis.analyze(self.issuer, 'OTHER', as_of=self.as_of, **self.pricing)
                self.assertEqual(before['inputs']['valuation_fcf'], 1_665_095_000)
                self.assertEqual(other['inputs']['fcf'], 1_785_834_000)

    def test_incomplete_ttm_can_use_a_fully_reconciled_fiscal_year(self):
        self.issuer.quarterly_cashflow = self.issuer.quarterly_cashflow.drop(index='Capital Expenditure')
        year = pd.to_datetime(['2025-12-31'])
        self.issuer.cashflow = pd.DataFrame({
            'Operating Cash Flow': [1_499_901], 'Capital Expenditure': [-200_756],
            'Free Cash Flow': [1_518_145], 'Stock Based Compensation': [102_637],
        }, index=year).T * 1_000
        self.issuer.income_stmt = pd.DataFrame({'Net Income': [1_071_948_000]}, index=year).T
        result = live_analysis.analyze(self.issuer, 'CPAY', as_of=self.as_of, **self.pricing)
        self.assertEqual((result['financial_period'], result['basis']), ('2025-12-31', 'FY'))
        self.assertEqual(result['inputs']['valuation_fcf'], 1_196_508_000)
