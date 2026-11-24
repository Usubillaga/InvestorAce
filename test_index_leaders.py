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
    prices = {s: {d: price for d in days} for s in ('AAA', 'BBB', il.EQUAL_WEIGHT, 'SPCX', 'ANT')}
    prices[il.FX] = {d: 1.25 for d in days}
    return heat, prices


HOLDINGS = lambda: [('AAA', 0.06), ('BBB', 0.02)]


class Account(unittest.TestCase):
    def setUp(self):
        self.days = sessions(il.MIN_HOLD + 40)

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
        self.assertAlmostEqual(state['positions']['AAA']['shares'] / state['positions']['BBB']['shares'], 3, places=5)
        rsp = state['positions'][il.EQUAL_WEIGHT]
        self.assertAlmostEqual(rsp['account_share'], 0.5)                     # half the account in RSP
        self.assertAlmostEqual(state['positions']['AAA']['account_share'] + state['positions']['BBB']['account_share'], 0.5)
        self.assertIsNone(state['pending'])
        self.assertIsNone(il.decide(state, days[:8], heat, days[8], 10))         # holding: no second buy

    def test_the_last_check_before_the_close_decides(self):
        days = self.days
        heat, prices = book(days, [50] * 5 + [15] + [50] * (len(days) - 6))
        state = il.fresh(days[0])
        il.advance(state, days[:6], heat, prices, HOLDINGS)
        self.assertIsNotNone(il.decide(state, days[:6], heat, days[6], 18))      # 15:10: still panic
        self.assertIsNone(il.decide(state, days[:6], heat, days[6], 23))         # 15:40: over, order withdrawn
        self.assertIsNone(state['pending'])
        self.assertEqual(il.advance(state, days[:7], heat, prices, HOLDINGS), [])

    def test_holds_42_months_and_then_sells_at_the_close_after_euphoria(self):
        days = self.days
        hold = il.MIN_HOLD
        values = [50.] * len(days)
        values[5] = 15.                                                        # panic: bought at days[6]
        values[16] = 85.                                                       # euphoria too early
        euphoric_day = 6 + hold + 5                                            # euphoria after 42 months
        values[euphoric_day] = 85.
        heat, prices = book(days, values)
        state = il.fresh(days[0])
        il.advance(state, days[:6], heat, prices, HOLDINGS)
        self.buy_on(state, days, heat, prices, 6, heat_now=12)
        events = il.advance(state, days[:hold], heat, prices, HOLDINGS)
        self.assertEqual(events, [])                                          # euphoria at day 16 is too early
        del prices['BBB'][days[euphoric_day + 1]]                             # no close on the planned sell day
        events = il.advance(state, days, heat, prices, HOLDINGS)
        self.assertEqual([(e['date'], e['why']) for e in events],
                         [(days[euphoric_day + 2], 'EUPHORIA_AFTER_42_MONTHS')])   # sold the next day instead
        self.assertIsNone(state['selling'])
        self.assertLess(state['trades'][0]['ret'], 0)                         # flat prices, two costs
        heat, prices = book(days, [50] * 5 + [15] + [50] * (len(days) - 6))   # no euphoria: never sold
        state = il.fresh(days[0])
        il.advance(state, days[:6], heat, prices, HOLDINGS)
        self.buy_on(state, days, heat, prices, 6, heat_now=12)
        self.assertEqual(il.advance(state, days, heat, prices, HOLDINGS), [])
        self.assertTrue(state['positions'])

    def test_level_17_needs_a_deeper_panic(self):
        days = self.days
        heat, prices = book(days, [50] * 5 + [18, 16] + [50] * (len(days) - 7))
        twenty, seventeen = il.fresh(days[0], 20.), il.fresh(days[0], 17.)
        for state in (twenty, seventeen):
            il.advance(state, days[:6], heat, prices, HOLDINGS)
        self.assertIsNotNone(il.decide(twenty, days[:6], heat, days[6], 18.5))      # under 20
        self.assertIsNone(il.decide(seventeen, days[:6], heat, days[6], 18.5))      # not under 17, no 17-signal yet
        il.advance(seventeen, days[:7], heat, prices, HOLDINGS)                    # days[6] closes at 16
        self.assertIsNotNone(il.decide(seventeen, days[:7], heat, days[7], 16.5))
        self.assertIsNone(il.decide(seventeen, days[:7], heat, days[7], 17.5))

    def test_euro_account_with_spacex_and_anthropic(self):
        days = self.days
        heat, prices = book(days, [50] * 5 + [15] + [50] * (len(days) - 6))
        state = il.fresh(days[0], 17., '17-spcx-ant')
        self.assertEqual((state['capital'], state['currency']), (25000., 'EUR'))
        il.advance(state, days[:6], heat, prices, HOLDINGS)
        self.buy_on(state, days, heat, prices, 6, heat_now=12)
        pos = state['positions']
        self.assertAlmostEqual(pos['SPCX']['account_share'], 0.15)
        self.assertAlmostEqual(pos['ANT']['account_share'], 0.15)
        self.assertAlmostEqual(pos[il.EQUAL_WEIGHT]['account_share'], 0.35)
        self.assertAlmostEqual(pos['AAA']['account_share'] + pos['BBB']['account_share'], 0.35)
        usd = 25000 * 1.25                                                   # converted at the buy close
        self.assertAlmostEqual(pos['SPCX']['shares'], usd * 0.15 / (100 * (1 + il.COST)), places=4)
        self.assertAlmostEqual(il.value(state, prices, days[6]), 25000 / (1 + il.COST), places=1)
        for d in days[7:]:
            prices[il.FX][d] = 1.0                                            # the dollar strengthens 25%
        self.assertAlmostEqual(il.value(state, prices, days[8]), 25000 * 1.25 / (1 + il.COST), places=1)
        self.assertFalse(il.fresh(days[0], 17., '17')['currency'] == 'EUR')

    def test_upgrade_of_the_flat_account_only(self):
        old = dict(schema='index-leaders-v1', start='2026-11-20', hold=252, positions={}, marks=[])
        new = il.upgrade(old, 20.)
        self.assertEqual((new['schema'], new['level'], new['min_hold']), ('index-leaders-v2', 20., il.MIN_HOLD))
        self.assertNotIn('hold', new)
        self.assertTrue(new['rule_changes'])
        with self.assertRaises(ValueError):
            il.upgrade(dict(schema='index-leaders-v1', positions={'AAA': {}}), 20.)

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


class Cutoff(unittest.TestCase):
    def test_todays_bar_only_after_the_close_or_intraday(self):
        ny = lambda h, m: pd.Timestamp(2026, 11, 23, h, m, tz='America/New_York')
        self.assertEqual(il.session_cutoff(ny(17, 41)), pd.Timestamp('2026-11-24'))     # after the close
        self.assertEqual(il.session_cutoff(ny(12, 0)), pd.Timestamp('2026-11-23'))      # partial bar left out
        self.assertEqual(il.session_cutoff(ny(15, 40), intraday=True), pd.Timestamp('2026-11-24'))
        self.assertEqual(il.session_cutoff(ny(20, 41)), pd.Timestamp('2026-11-24'))


class Page(unittest.TestCase):
    def test_page_from_the_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'index-leaders').mkdir()
            (root / 'index-leaders' / 'latest.json').write_text(json.dumps(dict(
                session='2026-11-20', heat=15.4, heat_recent=[['2026-11-19', 25.0], ['2026-11-20', 15.4]],
                intraday=dict(date='2026-11-23', heat=24.0, order=False, orders={'20': False, '17': False},
                              checked_at='2026-11-23T20:40+00:00'),
                holdings={'SPY': [dict(symbol='NVDA', weight=0.07, name='NVIDIA')], 'QQQ': []})))
            pages = dict(il.site_pages(root))
            html = pages[Path(il.PAGE)]
            self.assertIn('PANIC · buy signal', html)
            self.assertIn('7.00%', html)
            self.assertIn('no buy order', html)
            self.assertIn('buys under 20', html)
            self.assertIn('buys under 17', html)
            self.assertIn('with SpaceX and Anthropic', html)
            self.assertIn('25,000 EUR', html)
            self.assertIn('RSP', html)
            self.assertIn('Holdings not available', html)
            self.assertIn(il.YELLOW, html)
            self.assertEqual(il.site_pages(Path(tmp) / 'missing'), [])
            (root / 'backtests').mkdir()
            cell = dict(n=7, mean=0.05, median=0.04, worst=-0.4, positive=5, beats_spx=3)
            (root / 'backtests' / 'panic_history.json').write_text(json.dumps(dict(
                start='1999-01-04', summary={'252': {'top10_weight': cell, 'spx': cell}},
                events=[dict(date='2008-01-22', heat=12.0, basis='dollar volume (no share history)',
                             returns={'252': dict(top10_weight=-0.38, busted=-0.45, spx=-0.40)})])))
            html = dict(il.site_pages(root))[Path(il.PAGE)]
            self.assertIn('Panic buys since 2000', html)
            self.assertIn('2008-01-22', html)
            self.assertIn('-38.0%', html)


if __name__ == '__main__':
    unittest.main()
