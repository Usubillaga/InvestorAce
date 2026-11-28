"""Experimental McClellan Thrust paper account (no network)."""
import unittest

import pandas as pd

import mcclellan_paper as mp


def days(n, start='2026-11-23'):
    return [str(d.date()) for d in pd.bdate_range(start, periods=n)]


class Account(unittest.TestCase):
    def test_buys_at_first_close_holds_126_and_extends(self):
        s = days(300)
        closes = {d: 100. + i * 0.1 for i, d in enumerate(s)}
        state = mp.fresh()
        ev = mp.advance(state, s[:5], closes, {'2026-11-25'})               # first run on 27 Nov: no backdating
        self.assertEqual([(e['type'], e['date']) for e in ev], [('BUY', '2026-11-27')])
        k = s.index('2026-11-25')
        ev = mp.advance(state, s[:k + 126 + 1], closes, {'2026-11-25'})
        self.assertEqual(ev[-1]['type'], 'SELL')
        self.assertEqual(ev[-1]['date'], s[k + 126])
        state2 = mp.fresh()
        mp.advance(state2, s[:5], closes, set())
        extra = s[k + 100]
        ev = mp.advance(state2, s[:k + 240], closes, {'2026-11-25', extra})   # a new thrust extends the hold
        self.assertEqual([e['type'] for e in ev], ['SELL'])
        self.assertEqual(ev[0]['date'], s[s.index(extra) + 126])

    def test_thrust_detection(self):
        osc = pd.Series([10, -50, -100, -120, -40, -5, 3, 8], index=pd.bdate_range('2026-01-01', periods=8), dtype=float)
        self.assertEqual(mp.thrusts(osc, -88.8, lookback=5), ['2026-01-09'])


if __name__ == '__main__':
    unittest.main()
