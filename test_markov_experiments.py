import unittest
from datetime import date, timedelta

from markov_experiments import evaluate, paper_return, TRENDS


class Experiments(unittest.TestCase):
    def test_next_week_cannot_train_its_own_forecast(self):
        day = date(2026, 11, 6)
        samples = {}
        for i, b in enumerate(('PULLBACK', 'UPTREND', 'PULLBACK')):
            samples[day + timedelta(weeks=i)] = ({'A': ('PULLBACK', 'v'), 'B': (b, 'v')}, str(i))
        result = evaluate(samples, TRENDS, False, {}, [])
        self.assertEqual(len(result['scores']), 1)
        self.assertEqual(result['scores'][0]['losses']['markov'], 0.25)

    def test_version_change_and_gaps_are_excluded(self):
        samples = {date(2026, m, d): ({'US': ('REFLATION', v)}, str(m))
                   for m, d, v in [(6, 30, 'v1'), (7, 31, 'v2'), (9, 30, 'v2')]}
        result = evaluate(samples, ('REFLATION',), True, {}, [])
        self.assertEqual(result['matrix'], [])
        self.assertEqual(result['missing_or_changed'], 1)

    def test_stop_fills_after_breach_with_costs(self):
        sessions = ['2026-11-' + str(i) for i in range(16, 21)]
        prices = {'A': dict(zip(sessions, [100, 91, 85, 100, 110]))}
        args = ('A', date(2026, 11, 13), date(2026, 11, 20), prices, sessions)
        self.assertAlmostEqual(paper_return(*args), 85 * .999 / 100.1 - 1)
        del prices['A'][sessions[1]]
        self.assertIsNone(paper_return(*args))
