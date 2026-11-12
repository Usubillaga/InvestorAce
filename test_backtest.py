"""Backtest mechanics on synthetic prices (no network)."""
import unittest

import numpy as np
import pandas as pd

import backtest as bt


def frame(seed, n=700, drift=0.0008):
    rng = np.random.default_rng(seed)
    close = pd.Series(100 * np.exp(np.cumsum(rng.normal(drift, 0.02, n))),
                      index=pd.bdate_range('2020-01-01', periods=n))
    return close, close * 1.01, close * 0.99


class Indicators(unittest.TestCase):
    def test_levels_use_only_past_data(self):
        c, h, lo = frame(1)
        f = bt.indicators(c, h, lo)
        self.assertAlmostEqual(f['sma36'].iloc[100], c.iloc[65:101].mean())
        self.assertAlmostEqual(f['res'].iloc[100], c.iloc[36:96].max())     # 60 sessions ending 5 before
        changed = c.copy()
        changed.iloc[350:] *= 2                                              # a future change
        self.assertAlmostEqual(bt.indicators(changed, h, lo)['sma200'].iloc[349], f['sma200'].iloc[349])


class Runs(unittest.TestCase):
    def setUp(self):
        self.spx = frame(0, drift=0.0005)[0]
        self.frames = {f'S{i}': bt.indicators(*frame(i + 1)).reindex(self.spx.index) for i in range(12)}
        self.start = self.spx.index[260]

    def test_event_study_buckets_and_breakouts(self):
        out = bt.event_study(self.frames, self.spx, self.start)
        self.assertIn('30..+%', out['extension_36'])
        self.assertEqual(sum(v['n'] for v in out['extension_36'].values()) > 0, True)
        self.assertIsNotNone(out['breakouts']['failure_rate'])

    def test_every_variant_simulates_with_costs_and_limits(self):
        sectors = {k: 'A' if i % 2 else 'B' for i, k in enumerate(self.frames)}
        for name, rule in bt.VARIANTS.items():
            m = bt.simulate(self.frames, self.spx, sectors, self.start, **rule)
            self.assertGreater(m['final'], 0, name)
            self.assertLessEqual(m['max_drawdown'], 0, name)

    def test_report_renders(self):
        res = dict(window='x', generated_at='y', symbols=12, event_study=bt.event_study(self.frames, self.spx, self.start),
                   portfolio={'base_v1_5': bt.simulate(self.frames, self.spx, {}, self.start)},
                   spx=bt._metrics(self.spx[self.spx.index >= self.start], []))
        self.assertIn('Portfolio simulation', bt.report(res))


if __name__ == '__main__':
    unittest.main()
