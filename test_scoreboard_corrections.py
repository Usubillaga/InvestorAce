"""Corrections from the 2026-11-04 scoreboard review: regime noise, ranking, leverage EBITDA.

Each case reproduces numbers recorded in history/_builds or history/_dynamic_cache.json.
"""
import copy
import html
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

import i18n
import live_analysis
import macro
import opportunity
from test_live_analysis import ASOF as LIVE_ASOF, ticker_fixture
from test_opportunity import ASOF, row, spec


# Economic signals as recorded by every build from 2026-11-01 19:09 UTC to
# 2026-11-04 03:09 UTC (FRED, data month 2026-09).
RECORDED_SIGNALS = dict(cpi_yoy=3.72, cpi_yoy_3m_change=0.25, unemployment_gap=0.0,
                        payrolls_3m_avg_thousands=50.7)
# Daily market inflation impulse (%) on the aligned path, 25 sessions to 2026-11-03.
RECORDED_INFLATION_PATH = [6.0, 7.0, 2.0, 1.0, 0.3, 8.2, 7.7, 8.3, 8.3, 12.9, 12.7, 10.8, 20.5,
                           18.3, 14.9, 12.2, 9.2, 12.6, 10.3, 7.3, 5.2, 5.4, 7.4, 0.4, 2.6]
# (growth, inflation) single-close impulses read by consecutive builds.
RECORDED_SPOT = [(7.1, 7.4), (8.6, 4.4), (9.0, 0.2), (8.0, 0.4), (6.0, 3.4), (5.3, 2.6)]


def path(inflation, growth=9.0):
    return [dict(date=f'2026-10-{n + 1:02d}', g=growth, i=i) for n, i in enumerate(inflation)]


class RegimeSmoothingTests(unittest.TestCase):
    def test_latest_close_flipped_the_regime_without_new_economic_data(self):
        regimes = {macro.classify(g, i, RECORDED_SIGNALS)['regime'] for g, i in RECORDED_SPOT}
        self.assertEqual(regimes, {'INFLATION', 'REFLATION'})

    def test_smoothed_reading_is_the_mean_of_the_last_21_sessions(self):
        smooth = macro.smoothed_impulses(path(RECORDED_INFLATION_PATH))
        self.assertEqual(smooth['sessions'], 21)
        self.assertAlmostEqual(smooth['inflation'], sum(RECORDED_INFLATION_PATH[-21:]) / 21)
        self.assertEqual(smooth['end'], '2026-10-25')

    def test_smoothed_reading_holds_one_regime_through_the_recorded_noise(self):
        regimes = []
        for end in range(21, len(RECORDED_INFLATION_PATH) + 1):
            smooth = macro.smoothed_impulses(path(RECORDED_INFLATION_PATH[:end]))
            regimes.append(macro.classify(smooth['growth'], smooth['inflation'], RECORDED_SIGNALS)['regime'])
        self.assertEqual(set(regimes), {'INFLATION'})

    def test_short_or_non_finite_paths_do_not_invent_a_mean(self):
        self.assertIsNone(macro.smoothed_impulses(path([1.0] * 20)))
        self.assertIsNone(macro.smoothed_impulses([]))
        broken = path([1.0] * 21)
        broken[-1]['i'] = float('nan')
        self.assertIsNone(macro.smoothed_impulses(broken))

    def test_boundary_margin_names_the_closest_edge(self):
        self.assertEqual(macro.boundary_margin(dict(growth_score=0.40, inflation_score=0.48)), 0.02)
        self.assertEqual(macro.boundary_margin(dict(growth_score=-0.30, inflation_score=0.48)), 0.30)
        self.assertEqual(macro.boundary_margin(dict(growth_score=0.03, inflation_score=0.20)), 0.03)
        self.assertIsNone(macro.boundary_margin(dict(growth_score=None, inflation_score=None)))

    def test_read_macro_classifies_the_smoothed_reading(self):
        dates = pd.bdate_range(end='2026-11-03', periods=320)
        n = len(dates)
        rng = np.random.default_rng(7)
        trend = np.linspace(0, 1, n)
        closes = {
            'SPY': 500 * (1 + 0.25 * trend), 'HG=F': 4 * (1 + 0.2 * trend),
            'CL=F': 70 * (1 + 0.15 * trend + rng.normal(0, 0.03, n)),
            '^TNX': 4 * (1 + 0.15 * trend + rng.normal(0, 0.03, n)),
            '^VIX': np.full(n, 16.), '^FVX': np.full(n, 3.8), 'RSP': 170 * (1 + 0.2 * trend),
            'IYT': 70 * (1 + 0.1 * trend), 'RHI': 40 * (1 + 0.05 * trend),
            'XLY': 200 * (1 + 0.2 * trend), 'XLP': 80 * (1 + 0.05 * trend)}
        closes = {k: pd.Series(v, index=dates) for k, v in closes.items()}
        with patch.object(macro, '_closes', return_value=closes), \
                patch.object(macro, 'economic_data', return_value={}), \
                patch.object(macro, 'economic_signals', return_value=dict(RECORDED_SIGNALS)):
            reading = macro.read_macro()
        smooth = macro.smoothed_impulses(reading['path_points'])
        self.assertEqual(reading['regime_input']['basis'], 'MEAN_OF_SESSIONS')
        self.assertEqual(reading['regime_input']['sessions'], 21)
        self.assertAlmostEqual(reading['regime_input']['inflation'], smooth['inflation'], places=2)
        self.assertEqual(reading['regime'],
                         macro.classify(smooth['growth'], smooth['inflation'], RECORDED_SIGNALS)['regime'])
        self.assertEqual(reading['market_regime'], macro.quadrant_of(smooth['growth'], smooth['inflation']))
        self.assertIsNotNone(reading['regime_margin'])

    def test_regime_input_line_is_fully_translated(self):
        from engine import regime_input_line
        lines = [regime_input_line(dict(regime_input=dict(basis='MEAN_OF_SESSIONS', growth=9.86,
                     inflation=9.29, sessions=21, start='2026-10-05', end='2026-11-03'), regime_margin=0.03)),
                 regime_input_line(dict(regime_input=dict(basis='LATEST_CLOSE'), regime_margin=0.2))]
        self.assertIn('near a boundary', lines[0])
        self.assertEqual(regime_input_line({}), '')
        for line in lines:
            for language in ('de', 'es'):
                _, missing = i18n._translate(html.unescape(line), language)
                self.assertEqual(missing, '', (language, line))


class RankingTests(unittest.TestCase):
    def test_unlabelled_interval_ranks_by_its_lower_bound_not_below_sells(self):
        sanofi = dict(label=None, score_lower=6.92, score_upper=7.29)
        intel = dict(label='Sell', score_lower=2.89, score_upper=2.89)
        lvmh = dict(label='Hold Positive', score_lower=6.96, score_upper=6.96)
        bbw = dict(label='Hold Positive', score_lower=6.83, score_upper=6.83)
        rows = {'SAN': sanofi, 'INTC': intel, 'LVMH': lvmh, 'BBW': bbw}
        order = [t for t, _ in sorted(rows.items(), key=lambda kv: opportunity.rank_order(kv[1], kv[0]))]
        self.assertEqual(order, ['LVMH', 'SAN', 'BBW', 'INTC'])

    def test_withdrawn_or_unknown_rows_rank_last(self):
        rows = {'ENB': dict(label=None, score_lower=None), 'VST': dict(label='Hold Negative', score_lower=4.95),
                'X': None}
        order = [t for t, _ in sorted(rows.items(), key=lambda kv: opportunity.rank_order(kv[1], kv[0]))]
        self.assertEqual(order, ['VST', 'ENB', 'X'])

    def test_equal_bounds_put_the_labelled_row_first(self):
        rows = {'WIX': dict(label=None, score_lower=5.49), 'GILD': dict(label='Hold Negative', score_lower=5.49)}
        order = [t for t, _ in sorted(rows.items(), key=lambda kv: opportunity.rank_order(kv[1], kv[0]))]
        self.assertEqual(order, ['GILD', 'WIX'])


class LeverageEbitdaTests(unittest.TestCase):
    # Gilead TTM to 2026-09-30 as cached on 2026-11-04.
    GILD = dict(operating_income=11.699e9, ebitda=1.292e9, debt=26.231e9, cash=6.437e9)

    def test_provider_ebitda_below_operating_income_is_not_used_for_leverage(self):
        value, basis = live_analysis.leverage_ebitda(dict(self.GILD, depreciation=2.0e9))
        self.assertEqual((value, basis), (13.699e9, 'OPERATING_INCOME_PLUS_DA'))
        value, basis = live_analysis.leverage_ebitda(dict(self.GILD))
        self.assertEqual((value, basis), (11.699e9, 'OPERATING_INCOME_FLOOR'))
        net = self.GILD['debt'] - self.GILD['cash']
        self.assertAlmostEqual(net / self.GILD['ebitda'], 15.32, places=2)
        self.assertLess(net / value, 2.)

    def test_consistent_or_unusable_rows_are_unchanged(self):
        self.assertEqual(live_analysis.leverage_ebitda(dict(operating_income=200., ebitda=250.)),
                         (250., 'REPORTED_EBITDA'))
        self.assertEqual(live_analysis.leverage_ebitda(dict(operating_income=-5., ebitda=-1.)), (None, None))
        self.assertEqual(live_analysis.leverage_ebitda(dict(ebitda=40.)), (40., 'REPORTED_EBITDA'))
        self.assertEqual(live_analysis.leverage_ebitda({}), (None, None))

    def test_balance_component_uses_the_consistent_ebitda(self):
        t = ticker_fixture(debt=410e6)
        t.income_stmt.loc['EBITDA'] = 50e6               # below operating income 200e6
        t.cashflow.loc['Depreciation And Amortization'] = 50e6
        result = live_analysis.analyze(t, 'GILD', risk_free=.05, mrp=.05, as_of=LIVE_ASOF)
        self.assertEqual(result['inputs']['depreciation'], 50e6)
        self.assertEqual(result['inputs']['leverage_ebitda'], 250e6)
        self.assertEqual(result['parameters']['leverage_ebitda_basis'], 'OPERATING_INCOME_PLUS_DA')
        self.assertAlmostEqual(result['metrics']['net_debt_ebitda'], 400e6 / 250e6)
        self.assertEqual(result['components']['b'], 7.0)
        self.assertTrue(any('Provider EBITDA is below operating income' in w for w in result['warnings']))
        consistent = live_analysis.analyze(ticker_fixture(debt=410e6), 'GILD', risk_free=.05, mrp=.05,
                                           as_of=LIVE_ASOF)
        self.assertEqual(consistent['parameters']['leverage_ebitda_basis'], 'REPORTED_EBITDA')
        self.assertAlmostEqual(consistent['metrics']['net_debt_ebitda'], 400e6 / 250e6)

    def test_missing_cash_lower_bound_uses_the_same_ebitda(self):
        value = row(); dynamic = value['dynamic_analysis']
        dynamic['components']['b'] = None
        dynamic['inputs'].update(cash=None, debt=400., ebitda=10., leverage_ebitda=150.)
        result = opportunity.assess(copy.deepcopy(value), regime='REFLATION', spec=spec(), as_of=ASOF)
        self.assertIn('BALANCE_LOWER_BOUND', result['flags'])
        balance = next(c for c in result['components'] if c['key'] == 'b')
        self.assertAlmostEqual(balance['lower_contribution'], opportunity.WEIGHTS['b'] * 6.0)   # 400/150 = 2.7x, not 40x
        legacy = copy.deepcopy(value)
        del legacy['dynamic_analysis']['inputs']['leverage_ebitda']      # packets built before this field
        result = opportunity.assess(legacy, regime='REFLATION', spec=spec(), as_of=ASOF)
        balance = next(c for c in result['components'] if c['key'] == 'b')
        self.assertAlmostEqual(balance['lower_contribution'], opportunity.WEIGHTS['b'] * 1.5)


if __name__ == '__main__':
    unittest.main()
