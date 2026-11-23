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
    def setUp(self):
        self.days = sessions(il.HOLD + 30)

    def buy_on(self, state, days, heat, prices, i, heat_now):
        """Intraday decision on days[i], then the close run through days[i]."""
        order = il.decide(state, days[:i], heat, days[i], heat_now)
        events = il.advance(state, days[:i + 1], heat, prices, HOLDINGS)
        return order, events

    def test_buys_only_while_still_in_panic_before_the_close(self):
        days = self.days
        heat, prices = book(days, [50] * 5 + [15, 25, 18] + [50] * (len(days) - 8))
        state = il.fresh(days[0])
        il.advance(state, days[:6], heat, prices, HOLDINGS)                   # signal: first panic close days[5]
        order, events = self.buy_on(state, days, heat, prices, 6, heat_now=25)   # rebounded: no order
        self.assertIsNone(order)
        self.assertEqual(events, [])
        order, events = self.buy_on(state, days, heat, prices, 7, heat_now=18)   # panic again before the close
        self.assertEqual(order['signal'], days[5])
        self.assertEqual((events[0]['type'], events[0]['date'], events[0]['signal']), ('BUY', days[7], days[5]))
        self.assertAlmostEqual(state['positions']['AAA']['shares'] / state['positions']['BBB']['shares'], 3)
        self.assertIsNone(state['pending'])
        self.assertIsNone(il.decide(state, days[:8], heat, days[8], 10))         # holding: no second buy

    def test_sells_after_the_maximum_hold_and_at_the_close_after_euphoria(self):
        days = self.days
        heat, prices = book(days, [50] * 5 + [15] + [50] * (len(days) - 6))
        state = il.fresh(days[0])
        il.advance(state, days[:6], heat, prices, HOLDINGS)
        self.buy_on(state, days, heat, prices, 6, heat_now=12)
        events = il.advance(state, days, heat, prices, HOLDINGS)
        self.assertEqual([(e['type'], e['date'], e['why']) for e in events], [('SELL', days[6 + il.HOLD], 'MAX_HOLD')])
        self.assertLess(state['trades'][0]['ret'], 0)                         # flat prices, two costs
        heat, prices = book(days, [50] * 5 + [15] + [50] * 10 + [85] + [70] * (len(days) - 17))
        del prices['BBB'][days[17]]                                           # no close on the planned sell day
        state = il.fresh(days[0])
        il.advance(state, days[:6], heat, prices, HOLDINGS)
        self.buy_on(state, days, heat, prices, 6, heat_now=12)
        events = il.advance(state, days[:30], heat, prices, HOLDINGS)
        self.assertEqual([(e['date'], e['why']) for e in events], [(days[18], 'EUPHORIA')])
        self.assertIsNone(state['selling'])

    def test_an_old_or_unfilled_signal(self):
        days = self.days
        heat, prices = book(days, [50] * 5 + [15] + [10] * 70 + [50] * (len(days) - 76))
        state = il.fresh(days[0])
        il.advance(state, days[:75], heat, prices, HOLDINGS)
        self.assertIsNone(il.decide(state, days[:75], heat, days[75], 10))      # episode began 70 sessions ago
        state = il.fresh(days[0])
        il.advance(state, days[:6], heat, prices, HOLDINGS)
        il.decide(state, days[:6], heat, days[6], 12)
        for s in prices.values():
            del s[days[6]]                                                   # no close at all that day
        il.advance(state, days[:7], heat, prices, HOLDINGS)
        self.assertIsNone(state['pending'])
        self.assertEqual(state['positions'], {})

    def test_no_panic_no_buy(self):
        days = sessions(20)
        heat, prices = book(days, [45] * 20)
        state = il.fresh(days[0])
        self.assertIsNone(il.decide(state, days[:10], heat, days[10], 45))
        self.assertEqual(il.advance(state, days, heat, prices, HOLDINGS), [])
        self.assertEqual(state['marks'][-1]['equity'], il.CAPITAL)


class Page(unittest.TestCase):
    def test_page_from_the_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'index-leaders').mkdir()
            (root / 'index-leaders' / 'latest.json').write_text(json.dumps(dict(
                session='2026-11-20', heat=15.4, heat_recent=[['2026-11-19', 25.0], ['2026-11-20', 15.4]],
                intraday=dict(date='2026-11-23', heat=24.0, order=False, checked_at='2026-11-23T20:40+00:00'),
                holdings={'SPY': [dict(symbol='NVDA', weight=0.07, name='NVIDIA')], 'QQQ': []})))
            pages = dict(il.site_pages(root))
            html = pages[Path(il.PAGE)]
            self.assertIn('PANIC · buy signal', html)
            self.assertIn('7.00%', html)
            self.assertIn('no buy order', html)
            self.assertIn('Holdings not available', html)
            self.assertIn(il.YELLOW, html)
            self.assertEqual(il.site_pages(Path(tmp) / 'missing'), [])


if __name__ == '__main__':
    unittest.main()
