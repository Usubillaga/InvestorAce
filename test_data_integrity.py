"""Provider-data corrections: share classes, gains in earnings, missing EBITDA, cycle growth.

Numbers are the ones recorded in history/_dynamic_cache.json on 2026-11-04 or
filed on Alphabet's 10-Q cover page for the quarter to 2026-09-30.
"""
import copy
import unittest

import live_analysis
import opportunity
import opportunity_view
from test_live_analysis import ASOF as LIVE_ASOF, ticker_fixture
from test_opportunity import ASOF, row, spec


class ShareClassTests(unittest.TestCase):
    # Alphabet 10-Q cover, 21 Oct 2026: Class A 5,888m, B 827m, C 5,579m.
    GOOGL_LISTED, GOOGL_TOTAL = 5.888e9, 5.888e9 + 0.827e9 + 5.579e9

    def test_one_listed_class_is_replaced_by_the_whole_company_count(self):
        whole = live_analysis.all_class_shares(self.GOOGL_LISTED, self.GOOGL_TOTAL, 12.21e9)
        self.assertEqual(whole, 12.21e9)                 # the smaller of the two whole-company counts
        self.assertEqual(live_analysis.all_class_shares(2.214e9, 2.52e9, 2.55e9), 2.52e9)   # META

    def test_single_class_splits_and_adr_ordinaries_keep_the_listed_count(self):
        self.assertIsNone(live_analysis.all_class_shares(1.0e9, 1.01e9, 1.02e9))   # one class
        self.assertIsNone(live_analysis.all_class_shares(744e6, 744e6, 30e6))      # split after the quarter
        self.assertIsNone(live_analysis.all_class_shares(50e6, 50e6, 500e6))       # reverse split
        self.assertIsNone(live_analysis.all_class_shares(2.4e9, 19.1e9, 19.2e9))   # ADS vs ordinaries
        self.assertIsNone(live_analysis.all_class_shares(5.9e9, 12.3e9, None))     # one source only

    def fixture(self, implied, diluted):
        t = ticker_fixture(shares=10e6)
        t.info.update(impliedSharesOutstanding=implied)
        if diluted is not None:
            t.income_stmt.loc['Diluted Average Shares'] = diluted
        return t

    def test_extract_and_valuation_use_the_whole_company(self):
        result = live_analysis.analyze(self.fixture(20.9e6, 20.5e6), 'GOOGL', risk_free=.05, mrp=.05,
                                       as_of=LIVE_ASOF)
        self.assertEqual(result['inputs']['shares'], 20.5e6)
        self.assertEqual(result['parameters']['shares_basis'], 'ALL_CLASSES_MIN_IMPLIED_DILUTED')
        self.assertAlmostEqual(result['metrics']['market_cap'], 100. * 20.5e6)
        self.assertTrue(any('one share class of several' in w for w in result['warnings']))
        listed = live_analysis.analyze(self.fixture(20.9e6, None), 'GOOGL', risk_free=.05, mrp=.05,
                                       as_of=LIVE_ASOF)
        self.assertEqual(listed['inputs']['shares'], 10e6)
        self.assertEqual(listed['parameters']['shares_basis'], 'YAHOO_CURRENT_SNAPSHOT_UNDATED')


class EarningsAboveOperatingIncomeTests(unittest.TestCase):
    def analyze(self, net_income, operating_income=200e6):
        t = ticker_fixture()
        t.income_stmt.loc['Net Income'] = net_income
        t.income_stmt.loc['Operating Income'] = operating_income
        return live_analysis.analyze(t, 'GOOGL', risk_free=.05, mrp=.05, as_of=LIVE_ASOF)

    def test_gains_above_operating_income_do_not_lower_the_multiple(self):
        # Alphabet TTM: net income 235.69bn, operating income 156.98bn.
        result = self.analyze(net_income=300e6, operating_income=200e6)
        self.assertAlmostEqual(result['metrics']['reported_pe'], 1000e6 / 300e6)
        self.assertAlmostEqual(result['metrics']['valuation_pe'], 1000e6 / 200e6)
        self.assertEqual(result['inputs']['valuation_net_income'], 200e6)
        self.assertEqual(result['parameters']['earnings_basis'], 'CAPPED_AT_OPERATING_INCOME')
        self.assertTrue(any('Net income exceeds operating income' in w for w in result['warnings']))

    def test_ordinary_earnings_are_unchanged(self):
        result = self.analyze(net_income=150e6)
        self.assertAlmostEqual(result['metrics']['valuation_pe'], 1000e6 / 150e6)
        self.assertEqual(result['parameters']['earnings_basis'], 'REPORTED_NET_INCOME')

    def test_operating_loss_with_gains_scores_no_earnings_points(self):
        value = row(); dynamic = value['dynamic_analysis']
        dynamic['inputs'].update(net_income=40., valuation_net_income=-5.)
        dynamic['metrics'].update(valuation_pe=None)
        result = opportunity.assess(value, regime='REFLATION', spec=spec(), as_of=ASOF)
        self.assertEqual(next(c for c in result['components'] if c['key'] == 'pe')['value'], 0.)


class MissingEbitdaTests(unittest.TestCase):
    # Salesforce TTM to 2026-07-31; the EBITDA row was absent in two of four builds.
    CRM = dict(operating_income=9.46e9, ebitda=None, debt=41.74e9, cash=8.31e9)

    def test_a_missing_row_uses_operating_income_plus_da_then_the_floor(self):
        self.assertEqual(live_analysis.leverage_ebitda(dict(self.CRM, depreciation=3.5e9)),
                         (12.96e9, 'OPERATING_INCOME_PLUS_DA'))
        self.assertEqual(live_analysis.leverage_ebitda(dict(self.CRM)), (9.46e9, 'OPERATING_INCOME_FLOOR'))

    def test_balance_component_no_longer_disappears(self):
        t = ticker_fixture(debt=410e6)
        t.income_stmt = t.income_stmt.drop('EBITDA')
        result = live_analysis.analyze(t, 'CRM', risk_free=.05, mrp=.05, as_of=LIVE_ASOF)
        self.assertIsNotNone(result['components']['b'])
        self.assertEqual(result['parameters']['leverage_ebitda_basis'], 'OPERATING_INCOME_FLOOR')
        self.assertTrue(any(w.startswith('Provider EBITDA is missing') for w in result['warnings']))


class CycleGrowthTests(unittest.TestCase):
    def facts(self, revenues, years=('2025-12-31', '2024-12-31', '2023-12-31')):
        facts = live_analysis.extract(ticker_fixture(), 'CNX', as_of=LIVE_ASOF)
        facts.update(midcycle=True,
                     annual_fcf_series=[dict(period=y, value=100e6) for y in years],
                     annual_net_income_series=[dict(period=y, value=150e6) for y in years],
                     annual_revenue_series=[dict(period=y, value=v) for y, v in zip(years, revenues)])
        return facts

    def test_producer_growth_is_the_cycle_cagr_not_one_year(self):
        # CNX FY2025 revenue +49% after a gas-price trough; the cycle path is flat.
        result = live_analysis.calculate(self.facts([1490e6, 1000e6, 1490e6]), risk_free=.05, mrp=.05,
                                         as_of=LIVE_ASOF)
        self.assertAlmostEqual(result['metrics']['cycle_revenue_growth_pct'], 0., places=9)
        unaligned = live_analysis.calculate(self.facts([1490e6, 1000e6, None]), risk_free=.05, mrp=.05,
                                            as_of=LIVE_ASOF)
        self.assertIsNone(unaligned['metrics']['cycle_revenue_growth_pct'])
        # Four cash-flow years, revenue only for the newest three: CAGR over those three.
        longer = self.facts([1210e6, 1100e6, 1000e6, None],
                            years=('2025-12-31', '2024-12-31', '2023-12-31', '2022-12-31'))
        longer = live_analysis.calculate(longer, risk_free=.05, mrp=.05, as_of=LIVE_ASOF)
        self.assertAlmostEqual(longer['metrics']['cycle_revenue_growth_pct'], 10., places=9)

    def test_opportunity_scores_cycle_growth_or_leaves_it_unknown(self):
        value = row(); value['midcycle'] = True; value['sector'] = 'Energy'
        dynamic = value['dynamic_analysis']
        dynamic['parameters']['cash_flow_policy'] = 'MIDCYCLE_MEAN_PROXY'
        dynamic['components']['g'] = 9.5                  # one-year +49%
        dynamic['metrics']['revenue_growth_pct'] = 48.9
        dynamic['metrics']['cycle_revenue_growth_pct'] = 2.0
        result = opportunity.assess(copy.deepcopy(value), regime='REFLATION', spec=spec(), as_of=ASOF)
        self.assertEqual(next(c for c in result['components'] if c['key'] == 'g')['value'], 4.0)
        self.assertIn('CYCLE_REVENUE_GROWTH', result['flags'])
        del dynamic['metrics']['cycle_revenue_growth_pct']
        result = opportunity.assess(copy.deepcopy(value), regime='REFLATION', spec=spec(), as_of=ASOF)
        self.assertIsNone(next(c for c in result['components'] if c['key'] == 'g')['value'])
        self.assertIn('CYCLE_REVENUE_GROWTH_UNAVAILABLE', result['flags'])
        self.assertLess(result['score_lower'], result['score_upper'])

    def test_ordinary_companies_keep_reported_growth(self):
        result = opportunity.assess(row(), regime='REFLATION', spec=spec(), as_of=ASOF)
        self.assertEqual(next(c for c in result['components'] if c['key'] == 'g')['value'], 4.)


class ShortInterestDisplayTests(unittest.TestCase):
    def test_a_one_month_collapse_in_provider_data_is_not_displayed(self):
        oxy = dict(pct_float=0.02, days_to_cover=0.01, shares=131831., prior_month_shares=21630230.,
                   settlement_date='2026-10-15', change_pct=-99.39)
        html = opportunity_view.short(dict(short_interest=oxy))
        self.assertIn('Short interest not shown', html)
        self.assertNotIn('0.0% of float', html)
        normal = dict(oxy, shares=20e6, pct_float=2.1, days_to_cover=2.4, change_pct=-7.5)
        self.assertIn('2.1% of float', opportunity_view.short(dict(short_interest=normal)))


if __name__ == '__main__':
    unittest.main()
