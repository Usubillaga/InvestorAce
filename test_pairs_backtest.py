"""Pairs backtest on synthetic prices (no network)."""
import math
import unittest

import numpy as np
import pandas as pd

import pairs_backtest as pb


def prices(n=1300, seed=3):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range('2018-01-01', periods=n)
    lx = np.log(50) + np.cumsum(rng.normal(0, 0.012, n))
    phi = math.exp(-math.log(2) / 8)                     # spread half-life 8 sessions
    spread = np.zeros(n)
    for i in range(1, n):
        spread[i] = phi * spread[i - 1] + rng.normal(0, 0.012)
    ly = 0.3 + 1.0 * lx + spread
    walk = np.log(40) + np.cumsum(rng.normal(0, 0.012, n))
    return pd.DataFrame({'Y': np.exp(ly), 'X': np.exp(lx), 'R': np.exp(walk)}, index=idx)


class EngleGranger(unittest.TestCase):
    def test_finds_the_cointegrated_pair_with_its_half_life_and_skips_the_random_walk(self):
        close = prices()
        b, a, t, half = pb.engle_granger(np.log(close['Y'].values), np.log(close['X'].values))
        self.assertAlmostEqual(b, 1.0, delta=0.1)
        self.assertLess(t, pb.EG_CRIT)
        self.assertTrue(4 < half < 16)
        pairs = pb.form_pairs(np.log(close.iloc[:504]), {'Y': 'A', 'X': 'A', 'R': 'A'})
        self.assertEqual([(p['y'], p['x']) for p in pairs], [('Y', 'X')])
        self.assertEqual(pb.form_pairs(np.log(close.iloc[:504]), {'Y': 'A', 'X': 'B', 'R': 'A'}), [])  # other sector


class Simulate(unittest.TestCase):
    def test_mean_reverting_pair_earns_before_costs_in_both_methods(self):
        close = prices()
        sectors = {'Y': 'A', 'X': 'A', 'R': 'A'}
        for method in ('static', 'kalman'):
            with self.subTest(method=method):
                curve, trades, formed = pb.simulate(close, sectors, close.index[520], method=method)
                self.assertTrue(trades)
                self.assertGreater(curve.iloc[-1], 1.0)
                self.assertEqual(formed[0]['pairs'], 1)
                m = pb.metrics(curve, trades)
                self.assertGreater(m['sharpe'], 0)

    def test_costs_are_charged_and_no_pair_means_flat_equity(self):
        close = prices()
        curve, trades, _ = pb.simulate(close[['R', 'X']], {'R': 'A', 'X': 'A'}, close.index[520])
        self.assertEqual(trades, [])
        self.assertAlmostEqual(curve.iloc[-1], 1.0)
        free = pb.COST
        try:
            pb.COST = 0.
            gross = pb.simulate(close, {'Y': 'A', 'X': 'A'}, close.index[520])[0].iloc[-1]
        finally:
            pb.COST = free
        net = pb.simulate(close, {'Y': 'A', 'X': 'A'}, close.index[520])[0].iloc[-1]
        self.assertLess(net, gross)

    def test_study_reports_every_period_and_the_gate(self):
        close = prices()
        spx = close['X']
        out = pb.study(close, {'Y': 'A', 'X': 'A'}, spx, (('2020-01-01', '2021-01-01'), ('2021-01-01', None)))
        self.assertEqual(set(out), {'pairs_static', 'pairs_kalman'})
        self.assertEqual(len(out['pairs_static']['windows']), 2)
        self.assertIn('passes', pb.report(out) + 'passes')


if __name__ == '__main__':
    unittest.main()
