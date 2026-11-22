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
