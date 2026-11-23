"""Oversold-rebound study (no network)."""
import json
import unittest

import numpy as np
import pandas as pd

import backtest
import rebound_backtest as rb


def frame(closes):
    idx = pd.bdate_range('2020-01-01', periods=len(closes))
    c = pd.Series(closes, index=idx, dtype=float)
    return backtest.indicators(c, c * 1.01, c * 0.99), pd.Series(100., index=idx)


class Rebound(unittest.TestCase):
    def test_three_red_closes_far_below_the_ema_buy_and_sell_the_rebound(self):
        closes = [100.] * 60 + [97, 93, 88, 82] + [84, 95, 96, 97] + [97.] * 20
        f, spx = frame(closes)
        out = rb.trades(f, spx, f.index[0], oversold=2.0)
        self.assertEqual(len(out), 1)
        t = out[0]
        self.assertEqual(t['date'], str(f.index[62].date()))          # third red close: 97, 93, 88
        self.assertEqual(t['reason'], 'rebound')
        self.assertGreater(t['ret'], 0)
        self.assertAlmostEqual(t['excess'], t['ret'])                 # flat S&P

    def test_stop_and_no_stop(self):
        closes = [100.] * 60 + [97, 93, 88, 82, 79, 74] + [74.] * 3 + [90] * 20
        f, spx = frame(closes)
        stopped = rb.trades(f, spx, f.index[0], oversold=2.0)[0]
        self.assertEqual(stopped['reason'], 'stop')
        self.assertLess(stopped['ret'], -0.08)
        held = rb.trades(f, spx, f.index[0], oversold=2.0, stop=False)[0]
        self.assertEqual(held['reason'], 'rebound')
        self.assertGreater(held['ret'], 0)

    def test_open_trades_are_left_out_and_the_study_serialises(self):
        closes = list(100 + np.sin(np.arange(1200) / 7) * 15) + [97, 93, 88, 82]
        f, spx = frame(closes)
        last = rb.trades(f, spx, f.index[0], oversold=0.5)[-1]
        self.assertEqual(last['reason'], 'open')
        self.assertEqual(rb.summary([last]), dict(trades=0))
        windows = (('2020-01-01', '2022-01-01'), ('2022-01-01', None))
        result = rb.study({'X': f}, spx, windows)
        json.dumps(result, allow_nan=False)
        self.assertIn('Buy the oversold dip', rb.report(result))
        self.assertFalse(result['_passes']['all'])                    # fewer than 30 trades


if __name__ == '__main__':
    unittest.main()
