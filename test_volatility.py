"""Volatility forecasts and the GARCH/EWMA backtest variants (synthetic data, no network)."""
import math
import unittest

import numpy as np
import pandas as pd

import backtest as bt
import volatility as vol


def garch_path(n=3000, omega=2e-6, alpha=0.08, beta=0.90, seed=7):
    rng = np.random.default_rng(seed)
    var, out = omega / (1 - alpha - beta), []
    for _ in range(n):
        x = math.sqrt(var) * rng.standard_normal()
        out.append(x)
        var = omega + alpha * x * x + beta * var
    return np.array(out)


class Forecasts(unittest.TestCase):
    def test_ewma_matches_the_recursion(self):
        r = pd.Series([0.01, -0.02, 0.015, 0.0, -0.01])
        var = r.iloc[0] ** 2
        for x in r.iloc[1:]:
            var = 0.94 * var + 0.06 * x * x
        self.assertAlmostEqual(vol.ewma_vol(r).iloc[-1], math.sqrt(252 * var))

    def test_garch_fit_recovers_the_parameters_of_a_garch_path(self):
        omega, alpha, beta = vol.garch_fit(garch_path())
        self.assertAlmostEqual(alpha, 0.08, delta=0.04)
        self.assertAlmostEqual(beta, 0.90, delta=0.05)
        self.assertIsNone(vol.garch_fit(np.zeros(100)))

    def test_forecasts_never_use_later_data(self):
        idx = pd.bdate_range('2015-01-01', periods=1600)
        r = pd.Series(garch_path(1600), index=idx)
        changed = r.copy()
        changed.iloc[1400:] *= 5                   # a shock after the cut-off
        for fn in (vol.ewma_vol, vol.garch_vol):
            a, b = fn(r), fn(changed)
            pd.testing.assert_series_equal(a.iloc[:1400], b.iloc[:1400], check_names=False)
            self.assertGreater(b.iloc[1500], a.iloc[1500])


class Variants(unittest.TestCase):
    def test_volatility_variants_run_and_change_sizing(self):
        rng = np.random.default_rng(3)
        idx = pd.bdate_range('2016-01-01', periods=1100)
        frames = {}
        for i, sigma in enumerate((0.008, 0.012, 0.03, 0.04)):
            close = pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0008, sigma, len(idx)))), index=idx)
            frames[f'S{i}'] = bt.indicators(close, close * 1.01, close * 0.99)
        spx = pd.Series(4000 * np.exp(np.cumsum(rng.normal(0.0005, 0.01, len(idx)))), index=idx)
        prepared = bt.portfolio_inputs(frames)
        base = bt.simulate(frames, spx, {}, idx[700], prepared=prepared, precise=True, **bt.VARIANTS[bt.BASE])
        for name in ('garch_position_size', 'ewma_position_size', 'garch_exposure', 'ewma_exposure'):
            with self.subTest(name=name):
                m = bt.simulate(frames, spx, {}, idx[700], prepared=prepared, precise=True, **bt.VARIANTS[name])
                self.assertGreater(m['final'], 0)
                self.assertLessEqual(m['max_drawdown'], 0)
        sized = bt.simulate(frames, spx, {}, idx[700], prepared=prepared, precise=True,
                            **bt.VARIANTS['ewma_position_size'])
        self.assertNotEqual(sized['final'], base['final'])


if __name__ == '__main__':
    unittest.main()
