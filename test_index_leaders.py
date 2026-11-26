"""Panic & index leaders paper account and page (no network)."""
import json
import tempfile
import unittest
import unittest.mock
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

    def test_euro_account_combines_index_and_fixed_allocations_through_sale(self):
        days = self.days[:4]
        heat, prices = book(days, [12, 12, 85, 50])
        prices['SPCX'][days[1]] = 345.67
        holdings = lambda: [('SPCX', .06), ('ANT', .02)]
        state = il.fresh(days[0], 17., '17-spcx-ant')
        self.assertIsNotNone(il.decide(state, days[:1], heat, days[1], 12))
        buy, = il.advance(state, days[:2], heat, prices, holdings)
        expected = {'SPCX': .4125, 'ANT': .2375, 'RSP': .35}
        self.assertCountEqual(buy['symbols'], expected.keys())
        self.assertEqual(set(state['positions']), set(expected))
        rate = state['fx_buy']
        cost = 0.
        for symbol, weight in expected.items():
            p = state['positions'][symbol]
            self.assertEqual(p['account_share'], weight)
            self.assertEqual(p['entry'], prices[symbol][days[1]])
            self.assertEqual(p['index_weight'], dict(holdings()).get(symbol))
            self.assertAlmostEqual(p['shares'], 25000 * rate * weight / (p['entry'] * (1 + il.COST)), delta=1e-6)
            cost += p['shares'] * p['entry'] * (1 + il.COST) / rate
        self.assertGreaterEqual(state['cash'], 0)
        self.assertAlmostEqual(state['cash'] + cost, 25000, places=6)
        self.assertEqual(state['marks'][-1]['equity'], round(25000 / (1 + il.COST), 2))
        self.assertEqual(il.advance(state, days[:2], heat, prices, holdings), [])

        state['min_hold'] = 1
        prices[il.FX][days[-1]] = 1.10
        proceeds = sum(p['shares'] * prices[s][days[-1]] * (1 - il.COST)
                       for s, p in state['positions'].items()) / 1.10
        cash = state['cash']
        sell, = il.advance(state, days, heat, prices, holdings)
        self.assertEqual(sell['type'], 'SELL')
        self.assertEqual(state['positions'], {})
        self.assertAlmostEqual(state['cash'], cash + proceeds, places=6)
        self.assertEqual(state['trades'][0]['cost'], round(cost, 2))
        self.assertEqual(state['trades'][0]['proceeds'], round(proceeds, 2))

    def test_account_cards_show_positions_value_and_gain(self):
        days = self.days
        heat, prices = book(days, [50] * 5 + [15] + [50] * (len(days) - 6))
        state = il.fresh(days[0], 17., '17-spcx-ant')
        il.advance(state, days[:6], heat, prices, HOLDINGS)
        self.buy_on(state, days, heat, prices, 6, heat_now=12)
        snapshot = dict(heat=27.7, prices={'SPCX': ['x', 110.], 'ANT': ['x', 90.], il.FX: ['x', 1.25],
                                           'AAA': ['x', 100.], 'BBB': ['x', 100.], il.EQUAL_WEIGHT: ['x', 100.]})
        html = il.accounts_html([('17-spcx-ant', 17., state)], snapshot, {})
        self.assertIn('INVESTED', html)
        self.assertIn('SPCX', html)
        self.assertIn('Gain / loss', html)
        self.assertIn('class="mono up"', html)                               # SPCX up 10%
        self.assertIn('class="mono down"', html)                             # ANT down 10%
        flat = il.accounts_html([('20', 20., il.fresh(days[0], 20.))], snapshot, {})
        self.assertIn('7.7 points to go', flat)

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


class Windows(unittest.TestCase):
    def test_close_time_and_check_windows(self):
        ny = lambda day, h, m: pd.Timestamp(f'{day} {h:02d}:{m:02d}', tz='America/New_York')
        self.assertEqual(il.close_minutes('2026-11-25'), 16 * 60)
        self.assertEqual(il.close_minutes('2026-11-27'), 13 * 60)          # day after Thanksgiving
        self.assertEqual(il.close_minutes('2027-11-26'), 13 * 60)
        self.assertEqual(il.close_minutes('2026-12-24'), 13 * 60)
        self.assertEqual(il.close_minutes('2026-07-03'), 13 * 60)
        self.assertEqual(il.window(ny('2026-11-25', 15, 40)), 'pre-close')
        self.assertIsNone(il.window(ny('2026-11-25', 15, 56)))
        self.assertEqual(il.window(ny('2026-11-25', 10, 30)), 'morning')
        self.assertIsNone(il.window(ny('2026-11-25', 12, 10)))
        self.assertEqual(il.window(ny('2026-11-27', 12, 25)), 'pre-close')   # early close
        self.assertIsNone(il.window(ny('2026-11-27', 15, 40)))               # the market is already closed

    def test_morning_reading_records_without_an_order(self):
        days = sessions(30)
        today = days[-1]
        heat = {d: 50. for d in days}
        heat[days[20]] = 12.                                                 # an open panic episode
        heat[today] = 15.
        with tempfile.TemporaryDirectory() as tmp:
            latest = Path(tmp) / 'latest.json'
            accounts = []
            for name, level, path in il.ACCOUNTS:
                accounts.append((name, level, Path(tmp) / Path(path).name, il.fresh(days[0], level, name)))
            collect = lambda intraday: (days, heat, None, None)
            with unittest.mock.patch.object(il, '_accounts', return_value=accounts):
                morning = pd.Timestamp(f'{today} 10:31', tz='America/New_York')
                self.assertIsNone(il.decide_run(latest, now=morning, collect_fn=collect, move_fn=lambda d: 5.))
                snap = json.loads(latest.read_text())
                self.assertEqual(snap['morning']['heat'], 15.)
                self.assertEqual(snap['morning']['under'], {'20': True, '17': True, '17-spcx-ant': True,
                                                            '20-move': True})
                self.assertNotIn('intraday', snap)
                self.assertTrue(all(state.get('pending') is None for *_, state in accounts))
                close = pd.Timestamp(f'{today} 15:40', tz='America/New_York')
                orders = il.decide_run(latest, now=close, collect_fn=collect, move_fn=lambda d: 5.)
                self.assertTrue(all(orders.values()))
                snap = json.loads(latest.read_text())
                self.assertTrue(snap['intraday']['order'])
                self.assertIn('Morning reading', il.render(snap, [(n, l, s) for n, l, _, s in accounts]))


class MoveAccount(unittest.TestCase):
    def test_buys_only_while_bond_stress_is_not_high(self):
        days = sessions(30)
        today = days[-1]
        heat = {d: 50. for d in days}
        heat[days[20]] = 12.
        state = il.fresh(days[0], 20., '20-move')
        self.assertEqual(state['move_max'], 15.)
        self.assertIsNone(il.decide(state, days[:-1], heat, today, 15., move_now=22.))   # high bond stress: waits
        self.assertIsNone(il.decide(state, days[:-1], heat, today, 15., move_now=None))  # unknown MOVE: no buy
        order = il.decide(state, days[:-1], heat, today, 15., move_now=9.)
        self.assertEqual((order['signal'], order['move_excess']), (days[20], 9.))
        plain = il.fresh(days[0], 20., '20')
        self.assertNotIn('move_max', plain)
        self.assertIsNotNone(il.decide(plain, days[:-1], heat, today, 15., move_now=22.))  # other accounts ignore it

    def test_move_excess_and_page(self):
        idx = pd.bdate_range('2021-01-04', periods=900)
        move = pd.Series(100., index=idx)
        move.iloc[-5:] = 130.
        ex = il.move_excess(today=pd.Timestamp('2030-01-01'), download=lambda: move)
        last = str(idx[-1].date())
        self.assertGreater(ex[last], 15.)
        self.assertEqual(ex[str(idx[700].date())], 0.)
        self.assertIn('High bond stress', il._move_html(ex[last]))
        self.assertIn('Not high', il._move_html(3.))
        html = il.accounts_html([('20-move', 20., il.fresh('2026-11-20', 20., '20-move'))], {}, {})
        self.assertIn('only if MOVE', html)


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
            self.assertIn('Buys under 20', html)
            self.assertIn('Buys under 17', html)
            self.assertIn('SpaceX + Anthropic', html)
            self.assertIn('25,000 EUR', html)
            self.assertIn('IN CASH · waiting', html)
            self.assertIn('No backtest', html)
            self.assertIn('#b57bff', html)                                     # the third account's own colour
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
