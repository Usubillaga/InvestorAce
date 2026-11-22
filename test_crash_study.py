"""Claude's drawdown and rebound study (synthetic series, no network)."""
import json
import unittest
from datetime import date, timedelta

import crash_study as cs


def days(n, start=date(2000, 1, 3)):
    out, d = [], start
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


class Episodes(unittest.TestCase):
    def test_episode_boundaries_and_open_episode(self):
        closes = [100, 105, 94, 90, 99, 106, 110, 95, 97]
        eps = cs.episodes(days(len(closes)), closes)
        self.assertEqual(eps, [(1, 3, 5), (6, 7, None)])       # 105 -> 90 -> 106; 110 -> 95 still open

    def test_recession_overlap_by_month(self):
        self.assertTrue(cs.recession('2007-10-09', '2009-03-09'))
        self.assertFalse(cs.recession('1987-08-25', '1987-12-04'))


class Analogs(unittest.TestCase):
    def series(self):
        # three past falls to -12% with different aftermaths, then an open fall to -12% today
        up = [100 + i for i in range(30)]
        fall = lambda top: [top * (1 - 0.006 * i) for i in range(1, 21)]      # -12% after 20 sessions
        path = up[:]
        for after in (1.004, 0.996, 1.0):                                       # rebound, more falls, flat
            path += fall(path[-1])
            base = path[-1]
            path += [base * after ** k for k in range(1, 70)]
            path += [max(path) * 1.01 + i for i in range(80)]                   # regain the record
        path += fall(path[-1])
        return days(len(path)), path

    def test_analogs_and_stats(self):
        d, c = self.series()
        out = cs.study({'^GSPC': (d, c)})['^GSPC']
        self.assertEqual(len(out['episodes']), 4)
        self.assertIsNone(out['episodes'][-1]['recovery'])
        a = out['analogs']
        self.assertEqual(a['n'], 3)
        self.assertEqual(sum(a['first'].values()), 3)
        self.assertEqual(len(a['band']), cs.HORIZON + 1)
        self.assertEqual(a['band'][0][1], 0)
        json.dumps(out, allow_nan=False)                        # stored as backtests/crash_study.json
        html = cs.render({'^GSPC': json.loads(json.dumps(out))})
        self.assertIn('Median path', html)
        self.assertIn('every fall of 10% or more', html)

    def test_wilson_interval(self):
        lo, hi = cs.wilson(11, 20)
        self.assertAlmostEqual(lo, 0.342, places=3)
        self.assertAlmostEqual(hi, 0.742, places=3)


if __name__ == '__main__':
    unittest.main()


class ShallowCycles(unittest.TestCase):
    def test_a_cycle_that_never_reached_ten_percent_still_counts(self):
        import crash_study as cs
        closes = [100, 92, 100, 101] + [101] * 70 + [110, 102]      # -8% cycle, then today at -7.3%
        dates = [f'd{i:03d}' for i in range(len(closes))]
        eps = cs.episodes(dates, closes)
        self.assertEqual(eps, [])                                    # no 10% episode at all
        cases = cs.analogs(dates, closes, eps, -0.07)
        self.assertEqual([c['signal'] for c in cases], ['d001'])
        self.assertAlmostEqual(cases[0]['path'][1], 100 / 92 - 1)
