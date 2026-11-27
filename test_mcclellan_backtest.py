"""McClellan rebuilt from member breadth (no network)."""
import json
import unittest

import numpy as np
import pandas as pd

import mcclellan_backtest as mb


class McClellan(unittest.TestCase):
    def test_oscillator_signals_and_report(self):
        idx = pd.bdate_range('2005-01-03', periods=900)
        rng = np.random.default_rng(1)
        steps = rng.normal(0, 1, (900, 60))
        steps[400:420] -= 3                                    # a broad sell-off: almost everything falls
        steps[420:440] += 3                                    # then a broad recovery
        close = pd.DataFrame(100 + steps.cumsum(axis=0), index=idx, columns=[f'S{i}' for i in range(60)])
        members = pd.DataFrame(True, index=idx, columns=close.columns)
        osc = mb.oscillator(close, members)
        self.assertLess(osc.loc[idx[400]:idx[425]].min(), mb.OVERSOLD)
        sig = mb.signals(osc)
        self.assertTrue(any(pd.Timestamp(idx[420]) <= d <= pd.Timestamp(idx[460]) for d in sig['thrust']))
        spx = pd.Series(np.linspace(100, 200, 900), index=idx)
        r = mb.study(spx, osc, sig)
        json.dumps(r, allow_nan=False)
        self.assertIn('McClellan Oscillator from S&P 500 members', mb.report(r))
        lvl = mb.calibrated(osc, warmup=200)
        self.assertTrue(lvl.iloc[:199].isna().all() and lvl.iloc[-1] < 0)
        self.assertIsInstance(mb.signals(osc, lvl)['thrust'], list)
        st = mb.strategy(spx, sig['oversold'], start='2005-01-01')
        self.assertLessEqual(st['invested'], 1) and self.assertGreaterEqual(st['strategy']['total'], -1)
        self.assertGreater(st['buy_hold']['total'], 0.9)                 # 100 -> 200 over the sample
        rb = mb.robustness(spx, sig['oversold'], starts=3, placebo=5)
        self.assertEqual(len(rb['starts']), 3)
        self.assertEqual(sorted(rb['holds']), ['126', '252', '63'])
        self.assertTrue(0 <= rb['placebo']['share_at_least_real'] <= 1)
        members.iloc[:, 15:] = False                           # under 50 counted stocks: no reading
        self.assertTrue(mb.oscillator(close, members).empty)


if __name__ == '__main__':
    unittest.main()
