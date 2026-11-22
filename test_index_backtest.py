"""Index ETF timing study (synthetic prices, no network)."""
import unittest

import numpy as np
import pandas as pd

import index_backtest as ib


def prices(n=1400, seed=5):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range('2014-01-01', periods=n)
    return pd.DataFrame({e: 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.011, n))) for e in ib.ETFS}, index=idx)


class Rules(unittest.TestCase):
    def test_signal_definitions(self):
        idx = pd.bdate_range('2020-01-01', periods=260)
        up = pd.DataFrame({'A': np.linspace(100, 200, 260)}, index=idx)
        self.assertEqual(ib.signals(up, 'codex_20d_5d_long_short')['A'].iloc[-1], 1.)
        self.assertEqual(ib.signals(up[::-1].set_axis(idx), 'codex_20d_5d_long_short')['A'].iloc[-1], -1.)
        self.assertEqual(ib.signals(up[::-1].set_axis(idx), 'codex_20d_5d_long_only')['A'].iloc[-1], 0.)
        self.assertEqual(ib.signals(up, 'trend_200d')['A'].iloc[-1], 1.)
        self.assertTrue(np.isnan(ib.signals(up, 'trend_200d')['A'].iloc[150]))

    def test_buy_and_hold_tracks_prices_and_shorts_pay_costs(self):
        close = prices()
        start = close.index[300]
        bh = ib.equity(close, 'buy_and_hold', start)
        expected = (close.pct_change().loc[start:].mean(axis=1) + 1).cumprod()
        self.assertAlmostEqual(bh.iloc[-1], expected.iloc[-1] * (1 - ib.COST), places=4)
        flat = pd.DataFrame(100., index=close.index, columns=close.columns)
        self.assertLessEqual(ib.equity(flat, 'codex_20d_5d_long_short', start).iloc[-1], 1.)

    def test_study_reports_three_rules_and_the_gate(self):
        close = prices()
        out = ib.study(close, (('2015-06-01', '2017-01-01'), ('2017-01-01', None)), starts=4)
        periods = [k for k in out if not k.startswith('_')]
        self.assertEqual(len(periods), 2)
        self.assertEqual(set(out['_passes']), {'codex_20d_5d_long_short', 'codex_20d_5d_long_only', 'trend_200d'})
        self.assertIn('buy_and_hold', ib.report(out))


if __name__ == '__main__':
    unittest.main()
