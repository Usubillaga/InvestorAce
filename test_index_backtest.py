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
        import json
        json.dumps(out)                                  # the backtest stores it in latest.json


if __name__ == '__main__':
    unittest.main()


class IntradayAccount(unittest.TestCase):
    def test_matches_the_day_trade_accounting_of_index_paper(self):
        idx = pd.bdate_range('2020-01-01', periods=40)
        c = pd.Series(np.linspace(100, 139, 40), index=idx)        # steady rise: LONG signal
        frame = lambda s: pd.DataFrame({'SPY': s})
        h, l, o = c + 1, c - 1, c.copy()
        # day 39: opens 140, stop distance = 2 x mean true range (2 per day here) = 4, low 135 hits the stop at 136
        o.iloc[-1], h.iloc[-1], l.iloc[-1], c.iloc[-1] = 140., 141., 135., 138.
        ohlc = {'Open': frame(o), 'High': frame(h), 'Low': frame(l), 'Close': frame(c)}
        curve = ib.equity_intraday(ohlc, idx[-1])
        dist = 4.0
        weight = min(0.15, 0.005 * 140 / dist)
        expected = weight * ((136 - 140) / 140 - 2 * ib.COST)        # index_paper.settle with fractional shares
        self.assertAlmostEqual(curve.iloc[-1] - 1, expected, places=9)
        l.iloc[-1] = 137.                                            # no stop: out at the close
        curve = ib.equity_intraday({'Open': frame(o), 'High': frame(h), 'Low': frame(l), 'Close': frame(c)}, idx[-1])
        self.assertAlmostEqual(curve.iloc[-1] - 1, weight * ((138 - 140) / 140 - 2 * ib.COST), places=9)
