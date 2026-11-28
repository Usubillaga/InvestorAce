"""Panic buys since 2000 (no network)."""
import json
import unittest

import numpy as np
import pandas as pd

import panic_backtest as pb
import panic_history as ph


def panel(n=900, start='2004-01-01'):
    idx = pd.bdate_range(start, periods=n)
    t = np.arange(n)
    # LEAD keeps rising, BUST fell 60% early on, MID falls 30%, GONE stops trading after the signal.
    adj = pd.DataFrame({
        'LEAD': 50 + t * 0.1,
        'BUST': np.r_[np.full(300, 100.), np.linspace(100, 40, 100), np.full(n - 400, 40.)],
        'MID': np.r_[np.full(300, 100.), np.linspace(100, 70, 100), np.full(n - 400, 70.)],
        'GONE': np.r_[np.full(650, 30.), np.full(n - 650, np.nan)],
    }, index=idx)
    for i in range(20):
        adj[f'F{i}'] = 100 + np.sin(t / (10 + i)) * 5          # filler members for the breadth score
    return idx, adj


class Breadth(unittest.TestCase):
    def test_membership_follows_the_change_dates(self):
        idx = pd.bdate_range('2005-01-03', periods=10)
        rows = [(pd.Timestamp('2004-12-01'), ['AAA', 'BRK.B']), (idx[5], ['AAA', 'CCC'])]
        m = ph.membership(rows, idx, ['AAA', 'BRK-B', 'CCC'])
        self.assertTrue(m.loc[idx[0], 'BRK-B'])
        self.assertFalse(m.loc[idx[0], 'CCC'])
        self.assertTrue(m.loc[idx[5], 'CCC'])
        self.assertFalse(m.loc[idx[9], 'BRK-B'])

    def test_broken_busted_and_fresh_highs(self):
        idx, adj = panel()
        members = pd.DataFrame(True, index=idx, columns=adj.columns)
        dd = ph.drawdowns(adj)
        fresh = ph.fresh_high(adj)
        b = ph.breadth_on(idx[500], adj, dd, members, fresh)
        self.assertEqual(b['busted_names'], 1)                       # BUST -60%
        self.assertAlmostEqual(b['broken'], 2 / b['priced'])          # BUST and MID
        self.assertEqual(b['busted_fresh_high'], 1)                   # BUST's high is ~1 year old
        self.assertFalse(fresh.loc[idx[899], 'BUST'])                 # by then its high is over two years old
        self.assertTrue(fresh.loc[idx[899], 'LEAD'])


class Events(unittest.TestCase):
    def test_baskets_returns_carry_delisted_names_and_the_account_exit(self):
        idx, adj = panel()
        members = pd.DataFrame(True, index=idx, columns=adj.columns)
        dd, fresh = ph.drawdowns(adj), ph.fresh_high(adj)
        spx = pd.Series(np.linspace(100, 120, len(idx)), index=idx)
        heat = pd.Series(50., index=idx)
        heat.iloc[800] = 85.                                          # euphoria 100 sessions after the buy
        volume = pd.DataFrame(1e6, index=idx, columns=adj.columns)
        shares = {'LEAD': 4e9, 'BUST': 1e9, 'MID': 1e9, 'GONE': 1e9}
        e = ph.event(idx[699], adj, adj, volume, members, dd, fresh, spx, heat,
                     lambda t, d: shares.get(t, 1e8), horizons=(63, 252))
        self.assertEqual(e['basis'], 'market cap')
        self.assertEqual(e['top10'][0][0], 'LEAD')
        r = e['returns']['63']
        expected_gone = 30 / 30 * (1 - pb.COST) / (1 + pb.COST) - 1  # carried at its last price
        self.assertAlmostEqual(r['busted'], (40 / 40) * (1 - pb.COST) / (1 + pb.COST) - 1)
        self.assertLess(r['busted'], r['leaders'])
        self.assertIn('GONE', [t for t, _ in e['top10']] + ['GONE'])
        self.assertAlmostEqual(ph.basket_return(adj, ['GONE'], [1.], 600, 800), expected_gone)
        self.assertEqual(e['euphoria_exit']['exit'], str(idx[801].date()))
        self.assertIsNone(e['returns']['252'])                        # past the end of the data
        s = ph.summary([e], horizons=(63, 252))
        self.assertEqual(s['63']['spx']['n'], 1)
        json.dumps(e, allow_nan=False)

    def test_dollar_volume_stands_in_without_share_history(self):
        idx, adj = panel()
        volume = pd.DataFrame(1e6, index=idx, columns=adj.columns)
        volume['LEAD'] = 5e7
        top, w, basis = ph.top10(idx[599], list(adj.columns), adj, volume, lambda t, d: None)
        self.assertEqual(basis, 'dollar volume (no share history)')
        self.assertEqual(top[0], 'LEAD')
        self.assertAlmostEqual(sum(w), 1.0)


class Download(unittest.TestCase):
    def test_throttled_chunks_are_fetched_again_and_dead_tickers_left_out(self):
        idx = pd.bdate_range('2020-01-01', periods=5)
        calls = []

        def fetch(batch):
            calls.append(list(batch))
            throttled = len(calls) == 1                              # the first request is rate limited
            data = {}
            for field in ('Adj Close', 'Close', 'Volume'):
                data[field] = pd.DataFrame({t: (np.nan if throttled or t == 'DEAD' else 1.0) for t in batch},
                                           index=idx)
            return pd.concat(data, axis=1), throttled

        waits = []
        out = ph.download(['AAA', 'BBB', 'DEAD'], fetch=fetch, chunk=2, sleep=waits.append, pause=5)
        self.assertEqual(calls, [['AAA', 'BBB'], ['AAA', 'BBB'], ['DEAD']])   # a dead ticker is not retried
        self.assertIn(5, waits)                                      # waited before the second try
        self.assertEqual(sorted(out['adj'].columns), ['AAA', 'BBB', 'DEAD'])
        self.assertTrue(out['adj']['AAA'].notna().all())
        self.assertTrue(out['adj']['DEAD'].isna().all())


class Holding(unittest.TestCase):
    def test_drawdown_long_exit_mix_and_shares_cache(self):
        path = pd.Series([1., 1.2, 0.9, 1.1])
        self.assertAlmostEqual(ph.max_drawdown(path), 0.9 / 1.2 - 1)
        idx = pd.bdate_range('2001-01-01', periods=1200)
        heat = pd.Series(50., index=idx)
        heat.iloc[10 + ph.LONG + 30] = 85.
        self.assertEqual(ph.long_euphoria_exit(idx, 10, heat), (10 + ph.LONG + 31, False))
        heat.iloc[40] = 90.                                           # euphoria before 42 months does not count
        self.assertEqual(ph.long_euphoria_exit(idx, 10, heat)[0], 10 + ph.LONG + 31)
        self.assertEqual(ph.long_euphoria_exit(idx, 10, pd.Series(50., index=idx)), (len(idx) - 1, True))
        calls = []

        def fetch(t):
            calls.append(t)
            return pd.Series([1e9, 2e9], index=pd.to_datetime(['2010-01-01', '2012-01-01'])), [(pd.Timestamp('2015-01-01'), 2.0)]
        shares = ph.CachedShares(fetch)
        self.assertEqual(shares('A', pd.Timestamp('2011-06-01')), 2e9)          # 1e9 x the later 2-for-1 split
        self.assertEqual(shares('A', pd.Timestamp('2012-06-01')), 4e9)
        self.assertIsNone(shares('A', pd.Timestamp('2016-01-01')))            # last report too old (>550 days)
        self.assertEqual(calls, ['A'])                                       # fetched once

    def test_event_mix_and_drawdowns(self):
        idx, adj = panel(n=1700)
        members = pd.DataFrame(True, index=idx, columns=adj.columns)
        dd, fresh = ph.drawdowns(adj), ph.fresh_high(adj)
        spx = pd.Series(np.linspace(100, 120, len(idx)), index=idx)
        heat = pd.Series(50., index=idx)
        volume = pd.DataFrame(1e6, index=idx, columns=adj.columns)
        e = ph.event(idx[500], adj, adj, volume, members, dd, fresh, spx, heat, lambda t, d: 1e9, horizons=(252, ph.LONG))
        r = e['returns']['252']
        self.assertAlmostEqual(r['mix'], 0.5 * r['top10_weight'] + 0.5 * r['all_members'])
        self.assertLessEqual(r['drawdown']['all_members'], 0)
        self.assertEqual(r['drawdown']['spx'], 0.0)                         # a rising index never falls
        self.assertTrue(e['long_exit']['open'])                             # no euphoria at all
        json.dumps(e, allow_nan=False)


class Staged(unittest.TestCase):
    def test_two_halves_with_cash_or_fallback(self):
        idx, adj = panel(n=1300)
        members = pd.DataFrame(True, index=idx, columns=adj.columns)
        spx = pd.Series(np.r_[np.full(500, 100.), np.linspace(100, 80, 20), np.linspace(80, 120, 780)], index=idx)
        heat = pd.Series(50., index=idx)
        heat.iloc[500] = 18.
        heat.iloc[515] = 8.                                          # deeper panic 15 sessions later
        volume = pd.DataFrame(1e6, index=idx, columns=adj.columns)
        r = ph.staged(idx[500], heat, adj, adj, volume, members, spx, lambda t, d: None, horizons=(252,))
        self.assertEqual(r['reached_10'], str(idx[516].date()))
        p = r['plans']['252']
        # the S&P leg: buying half at 100 and half near the low beats buying everything at 100
        self.assertGreater(p['staged_cash']['spx']['ret'], p['all_at_20']['spx']['ret'])
        self.assertGreater(p['all_at_20']['spx']['drawdown'], -0.21)
        self.assertGreater(p['staged_cash']['spx']['drawdown'], p['all_at_20']['spx']['drawdown'])   # smaller fall
        self.assertEqual(p['staged_cash'], p['staged_fallback'])                                   # 10 was reached
        heat.iloc[515] = 30.                                         # never deeper than 18
        r = ph.staged(idx[500], heat, adj, adj, volume, members, spx, lambda t, d: None, horizons=(252,))
        p = r['plans']['252']
        self.assertIsNone(r['reached_10'])
        self.assertEqual(p['all_at_10']['spx']['ret'], 0.0)                                         # all cash
        self.assertNotEqual(p['staged_cash']['spx']['ret'], p['staged_fallback']['spx']['ret'])
        s = ph.staged_summary([r], horizons=(252,))
        self.assertEqual(s['252']['staged_cash:spx']['n'], 1)
        json.dumps(dict(r=r, s=s), allow_nan=False)


class Touch(unittest.TestCase):
    def test_touch_episodes_earlier_and_touch_only(self):
        idx = pd.bdate_range('2001-01-01', periods=600)
        heat = pd.Series(50., index=idx)
        touch = heat.copy()
        touch.iloc[100] = 15.                     # touched intraday, never closed under 20: touch-only
        heat.iloc[300] = 15.                      # a close under 20 ...
        touch.iloc[298:301] = 15.                 # ... touched two sessions earlier
        r = ph.touch_study(heat, touch, '2001-01-01', lambda d: None, levels=(20.,))['20']
        self.assertEqual(r['touch_only'], [str(idx[100].date())])
        self.assertEqual(r['sessions_earlier'], [2])
        json.dumps(r, allow_nan=False)

    def test_touch_heat_is_at_or_below_the_close_heat(self):
        idx, adj = panel(n=700)
        members = pd.DataFrame(True, index=idx, columns=adj.columns)
        spx = pd.Series(np.linspace(100, 90, len(idx)), index=idx)
        vix = pd.Series(25., index=idx)
        close = ph.breadth_heat(spx, vix, adj, members)
        touch = ph.touch_heat(spx, vix, adj, members, spx * 0.98, vix * 1.2)
        both = pd.concat([close, touch], axis=1).dropna()
        self.assertTrue((both.iloc[:, 1] <= both.iloc[:, 0]).all())
        self.assertTrue((both.iloc[:, 1] < both.iloc[:, 0]).any())


class Move(unittest.TestCase):
    def test_excess_over_three_years_and_bands(self):
        idx = pd.bdate_range('2005-01-03', periods=900)
        move = pd.Series(100., index=idx)
        move.iloc[850:] = 130.
        x = ph.excess(move, idx)
        self.assertTrue(np.isnan(x.iloc[100]))                       # under 18 months of history
        self.assertEqual(x.iloc[500], 0.)
        self.assertGreater(x.iloc[860], 15.)
        events = [dict(date=str(idx[860].date()), returns={}, long_exit=None),
                  dict(date=str(idx[500].date()), returns={}, long_exit=None),
                  dict(date=str(idx[50].date()), returns={}, long_exit=None)]
        r = ph.move_study({'20': events}, move, move, idx)['20']
        self.assertEqual(r['groups']['high (> +15)']['signals'], [str(idx[860].date())])
        self.assertEqual(r['groups']['calm (< 0)']['signals'], [])
        self.assertEqual(r['groups']['elevated (0 to +15)']['signals'], [str(idx[500].date())])
        self.assertEqual(r['no_move'], [str(idx[50].date())])
        json.dumps(r, allow_nan=False)


class Study(unittest.TestCase):
    def test_end_to_end_with_a_panic_and_the_report(self):
        idx, adj = panel(n=1300, start='1999-06-01')
        spx = pd.Series(np.r_[np.linspace(100, 140, 700), np.linspace(140, 90, 120), np.linspace(90, 150, 480)],
                        index=idx)
        vix = pd.Series(np.r_[np.full(700, 14.), np.full(120, 45.), np.full(480, 14.)], index=idx)
        rows = [(pd.Timestamp('1999-01-04'), list(adj.columns))]
        volume = pd.DataFrame(1e6, index=idx, columns=adj.columns)
        result = ph.study(spx, vix, adj, adj, volume, rows, lambda t, d: None, start='2000-01-01',
                          extremes=(spx * 0.99, vix * 1.1), move=pd.Series(100., index=idx),
                          credit=('BAA10Y', pd.Series(2.0, index=idx)))
        self.assertGreaterEqual(result['signals'], 1)
        json.dumps(result, allow_nan=False)
        md = ph.report(result)
        self.assertIn('Panic buys since 2000', md)
        self.assertIn('Breadth check against Scion', md)
        self.assertEqual(sorted(result['delays']), ['0', '10', '5'])
        self.assertIn('Timing sensitivity', md)
        self.assertEqual(sorted(result['levels'], key=float), [str(x) for x in range(10, 21)])
        self.assertEqual(sorted(result['staged_grid'], key=float), ['10', '12', '14', '15', '16', '18'])
        for deeper in ('15', '10'):                                  # deeper levels only ever drop signals
            self.assertLessEqual(len(result['levels'][deeper]['signals']), len(result['levels']['20']['signals']))
        self.assertIn('Buying deeper in the panic', md)
        self.assertIn('staged', result)
        self.assertEqual(sorted(result['touch']), ['17', '20'])
        self.assertGreaterEqual(len(result['touch']['20']['touch_signals']), 1)
        self.assertIn('Touching the level intraday', md)
        self.assertEqual(sorted(result['move']), ['17', '20'])
        self.assertEqual(len(result['move']['20']['per_signal']), len(result['levels']['20']['signals']))
        self.assertIn('bond-market stress', md)
        self.assertEqual(result['credit']['series'], 'BAA10Y')
        self.assertIn('credit stress', md)
        sid, ser = ph.credit_series(fetch=lambda sid: b'DATE,X\n2000-01-03,3.1\n2000-01-04,3.2\n' if sid == 'BAA10Y'
                                    else b'DATE,X\n2023-01-03,4.0\n')
        self.assertEqual((sid, len(ser)), ('BAA10Y', 2))                  # the longer history wins


if __name__ == '__main__':
    unittest.main()
