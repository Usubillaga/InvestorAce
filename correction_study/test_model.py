import unittest
from .build import episodes


class HistoricalCycles(unittest.TestCase):
    def test_nested_corrections_and_independent_recovery(self):
        prices = [100, 90, 81, 91, 80, 90, 100]
        self.assertEqual(episodes(prices, False), [(0, 4, 6)])
        self.assertEqual(episodes(prices, True), [(0, 2, 3), (3, 4, 5)])

    def test_open_minimum_and_subthreshold_move(self):
        self.assertEqual(episodes([100, 91, 101, 90, 89], False), [(2, 4, None)])
        self.assertEqual(episodes([100, 91], True), [])


class ReboundEstimates(unittest.TestCase):
    def test_loss_before_rally_and_confirmed_pullback(self):
        from .rebounds import path_stats
        path = [100, 94, 105, 110, 108, 104]
        row = path_stats(list(range(6)), path, 0)
        self.assertEqual((row['down'],row['five'],row['duration']), (1,2,2))
        self.assertEqual((row['peak'],row['end']), ('3','5'))

    def test_censoring_and_one_reference_per_cycle(self):
        from .rebounds import study
        prices = [100, 89, 80] + [95]*63 + [110, 90]
        report = study(list(range(len(prices))), prices, [(0,2,65),(66,67,None)],.1)
        self.assertEqual(len(report['events']),1)
        self.assertEqual(report['censored'],1)
        self.assertEqual(report['bands'][0]['k'],1)
