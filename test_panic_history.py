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


class Study(unittest.TestCase):
    def test_end_to_end_with_a_panic_and_the_report(self):
        idx, adj = panel(n=1300, start='1999-06-01')
        spx = pd.Series(np.r_[np.linspace(100, 140, 700), np.linspace(140, 90, 120), np.linspace(90, 150, 480)],
                        index=idx)
        vix = pd.Series(np.r_[np.full(700, 14.), np.full(120, 45.), np.full(480, 14.)], index=idx)
        rows = [(pd.Timestamp('1999-01-04'), list(adj.columns))]
        volume = pd.DataFrame(1e6, index=idx, columns=adj.columns)
        result = ph.study(spx, vix, adj, adj, volume, rows, lambda t, d: None, start='2000-01-01')
        self.assertGreaterEqual(result['signals'], 1)
        json.dumps(result, allow_nan=False)
        md = ph.report(result)
        self.assertIn('Panic buys since 2000', md)
        self.assertIn('Breadth check against Scion', md)


if __name__ == '__main__':
    unittest.main()
