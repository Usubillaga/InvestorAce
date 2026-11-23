"""Thermometer panic study (no network)."""
import json
import unittest

import numpy as np
import pandas as pd

import backtest
import market_pulse
import panic_backtest as pb


def series(values, start='2020-01-01'):
    return pd.Series(values, index=pd.bdate_range(start, periods=len(values)), dtype=float)


class Heat(unittest.TestCase):
    def test_same_scores_as_the_live_thermometer(self):
        rng = np.random.default_rng(1)
        spx = series(100 * np.exp(np.cumsum(rng.normal(0, .01, 400))))
        vix = series(rng.uniform(12, 40, 400))
        close = pd.DataFrame({f'S{i}': 100 * np.exp(np.cumsum(rng.normal(0, .02, 400))) for i in range(25)},
                             index=spx.index)
        mine = pb.heat(spx, vix, close).iloc[-1]
        dated = lambda s: [(d.date().isoformat(), float(v)) for d, v in s.items()]
        live = market_pulse.summarize({'^GSPC': dated(spx), '^VIX': dated(vix)},
                                      {k: dated(close[k]) for k in close})['heat']
        self.assertAlmostEqual(mine, live, places=0)

    def test_one_entry_per_episode_and_the_exit(self):
        h = series([50] * 10 + [15, 12, 30, 18] + [50] * 100 + [10] + [40] * 3)
        entries, exits = pb.signals(h, gap=63)
        self.assertEqual([h.index.get_loc(d) for d in entries], [10, 114])
        self.assertEqual([h.index.get_loc(d) for d in exits], [12, 115])     # 30 closes the first panic


class Outcomes(unittest.TestCase):
    def test_leader_is_the_strongest_and_returns_include_costs(self):
        n = 600
        idx = pd.bdate_range('2018-01-01', periods=n)
        strong = pd.Series(np.linspace(50, 200, n), index=idx)
        flat = pd.Series(100., index=idx)
        frames = {'UP': backtest.indicators(strong, strong * 1.01, strong * .99),
                  'FLAT': backtest.indicators(flat, flat * 1.01, flat * .99)}
        spx = pd.Series(np.linspace(100, 60, n), index=idx)       # falling market: panic
        vix = pd.Series(45., index=idx)
        result = pb.study(frames, spx, vix)
        first = result['panic_entry']['events'][0]
        self.assertEqual(first['leader'], 'UP')
        i = idx.get_loc(pd.Timestamp(first['date'])) + 1
        self.assertAlmostEqual(first['returns']['21']['leader'],
                               strong.iloc[i + 21] / strong.iloc[i] * (1 - pb.COST) / (1 + pb.COST) - 1)
        json.dumps(result, allow_nan=False)
        self.assertIn('Panic · buy', pb.report(result))


if __name__ == '__main__':
    unittest.main()
