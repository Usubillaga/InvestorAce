"""Panic & index leaders paper account and page (no network)."""
import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

import index_leaders as il


def sessions(n, start='2026-11-02'):
    return [str(d.date()) for d in pd.bdate_range(start, periods=n)]


def book(days, heat_values, price=100.):
    heat = dict(zip(days, heat_values))
    prices = {s: {d: price for d in days} for s in ('AAA', 'BBB')}
    return heat, prices


HOLDINGS = lambda: [('AAA', 0.06), ('BBB', 0.02)]


class Account(unittest.TestCase):
    def test_buys_after_the_first_panic_close_in_proportion_and_sells_after_63_sessions(self):
        days = sessions(90)
        heat, prices = book(days, [50] * 5 + [15, 12] + [50] * 83)
        state = il.fresh(days[0])
        events = il.advance(state, days[:10], heat, prices, HOLDINGS)
        self.assertEqual(events[0]['type'], 'BUY')
        self.assertEqual((events[0]['signal'], events[0]['date']), (days[5], days[6]))   # bought the next close
        self.assertFalse(events[0]['late'])
        self.assertAlmostEqual(state['positions']['AAA']['shares'] / state['positions']['BBB']['shares'], 3)
        self.assertAlmostEqual(il.value(state, prices, days[6]), il.CAPITAL / (1 + il.COST), places=2)
        events = il.advance(state, days, heat, prices, HOLDINGS)                          # resumes, no double buy
        self.assertEqual([e['type'] for e in events], ['SELL'])
        self.assertEqual(events[0]['date'], days[6 + il.HOLD])
        self.assertEqual(len(state['trades']), 1)
        self.assertLess(state['trades'][0]['ret'], 0)                                     # flat prices, two costs

    def test_a_signal_just_before_the_start_is_bought_late_and_old_ones_never(self):
        days = sessions(30)
        heat, prices = book(days, [50] * 20 + [15, 12, 30] + [50] * 7)
        state = il.fresh(days[22])
        events = il.advance(state, days, heat, prices, HOLDINGS)
        self.assertEqual(events[0]['date'], days[22])
        self.assertTrue(events[0]['late'])
        self.assertEqual(events[0]['signal'], days[20])
        old = il.fresh(days[29])
        self.assertEqual(il.advance(old, days, heat, prices, HOLDINGS), [])              # nine sessions old

    def test_no_panic_no_buy(self):
        days = sessions(20)
        heat, prices = book(days, [45] * 20)
        state = il.fresh(days[0])
        self.assertEqual(il.advance(state, days, heat, prices, HOLDINGS), [])
        self.assertEqual(state['marks'][-1]['equity'], il.CAPITAL)


class Page(unittest.TestCase):
    def test_page_from_the_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'index-leaders').mkdir()
            (root / 'index-leaders' / 'latest.json').write_text(json.dumps(dict(
                session='2026-11-20', heat=15.4, heat_recent=[['2026-11-19', 25.0], ['2026-11-20', 15.4]],
                holdings={'SPY': [dict(symbol='NVDA', weight=0.07, name='NVIDIA')], 'QQQ': []})))
            pages = dict(il.site_pages(root))
            html = pages[Path(il.PAGE)]
            self.assertIn('PANIC · buy signal', html)
            self.assertIn('7.00%', html)
            self.assertIn('Holdings not available', html)
            self.assertIn(il.YELLOW, html)
            self.assertEqual(il.site_pages(Path(tmp) / 'missing'), [])


if __name__ == '__main__':
    unittest.main()
