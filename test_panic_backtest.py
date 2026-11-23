"""Thermometer panic study (no network)."""
import json
import unittest

import numpy as np
import pandas as pd

import backtest
import market_pulse
import panic_backtest as pb


def series(values, start='2020-01-01'):
    return pd.Series(values, index=pd.bdate_range(start, periods=len(values)), dtype=float)


class Heat(unittest.TestCase):
    def test_same_scores_as_the_live_thermometer(self):
        rng = np.random.default_rng(1)
        spx = series(100 * np.exp(np.cumsum(rng.normal(0, .01, 400))))
        vix = series(rng.uniform(12, 40, 400))
        close = pd.DataFrame({f'S{i}': 100 * np.exp(np.cumsum(rng.normal(0, .02, 400))) for i in range(25)},
                             index=spx.index)
        mine = pb.heat(spx, vix, close).iloc[-1]
        dated = lambda s: [(d.date().isoformat(), float(v)) for d, v in s.items()]
        live = market_pulse.summarize({'^GSPC': dated(spx), '^VIX': dated(vix)},
                                      {k: dated(close[k]) for k in close})['heat']
        self.assertAlmostEqual(mine, live, places=0)

    def test_one_entry_per_episode_and_the_exit(self):
        h = series([50] * 10 + [15, 12, 30, 18] + [50] * 100 + [10] + [40] * 3)
        entries, exits = pb.signals(h, gap=63)
        self.assertEqual([h.index.get_loc(d) for d in entries], [10, 114])
        self.assertEqual([h.index.get_loc(d) for d in exits], [12, 115])     # 30 closes the first panic


class Outcomes(unittest.TestCase):
    def test_leader_is_the_strongest_and_returns_include_costs(self):
        n = 600
        idx = pd.bdate_range('2018-01-01', periods=n)
        strong = pd.Series(np.linspace(50, 200, n), index=idx)
        flat = pd.Series(100., index=idx)
        frames = {'UP': backtest.indicators(strong, strong * 1.01, strong * .99),
                  'FLAT': backtest.indicators(flat, flat * 1.01, flat * .99)}
        spx = pd.Series(np.linspace(100, 60, n), index=idx)       # falling market: panic
        vix = pd.Series(45., index=idx)
        result = pb.study(frames, spx, vix)
        first = result['panic_entry']['events'][0]
        self.assertEqual(first['leader'], 'UP')
        i = idx.get_loc(pd.Timestamp(first['date'])) + 1
        self.assertAlmostEqual(first['returns']['21']['leader'],
                               strong.iloc[i + 21] / strong.iloc[i] * (1 - pb.COST) / (1 + pb.COST) - 1)
        json.dumps(result, allow_nan=False)
        self.assertIn('Panic · buy', pb.report(result))


class IndexLeaders(unittest.TestCase):
    TEXT = ('date,tickers\n2019-01-02,"AAA,BBB,GONE"\n2019-06-03,"AAA,BBB,NEW"\n')

    def test_members_are_taken_as_of_the_day(self):
        rows = pb.parse_members(self.TEXT)
        self.assertEqual(pb.members_on(rows, pd.Timestamp('2019-03-01')), ['AAA', 'BBB', 'GONE'])
        self.assertEqual(pb.members_on(rows, pd.Timestamp('2019-07-01')), ['AAA', 'BBB', 'NEW'])
        self.assertIsNone(pb.members_on(rows, pd.Timestamp('2018-12-31')))
        self.assertIsNone(pb.members_on(rows, pd.Timestamp('2020-06-01')))          # list too old to know
        self.assertEqual(pb.yahoo('BRK.B'), 'BRK-B')

    def test_leader_is_the_strongest_member_and_later_members_are_ignored(self):
        idx = pd.bdate_range('2018-06-01', periods=400)
        close = pd.DataFrame({'AAA': np.linspace(50, 150, 400), 'BBB': np.full(400, 100.),
                              'GONE': np.linspace(100, 60, 400), 'NEW': np.linspace(10, 500, 400)}, index=idx)
        close.loc[idx[300]:, 'GONE'] = np.nan                     # delisted after the signal
        spx = pd.Series(np.linspace(100, 120, 400), index=idx)
        day = idx[250]
        events = pb.index_leaders([day], pb.parse_members(self.TEXT), close, spx, horizons=(21, 63))
        self.assertEqual(events[0]['leaders'][:2], ['AAA', 'BBB'])     # NEW was not a member yet
        self.assertEqual(events[0]['priced'], 3)
        r = events[0]['returns']['21']
        self.assertAlmostEqual(r['top1'], close['AAA'].iloc[272] / close['AAA'].iloc[251] * (1 - pb.COST) / (1 + pb.COST) - 1)
        summary = pb.leader_summary(events, horizons=(21, 63))
        self.assertEqual(summary['21']['n'], 1)
        result = dict(panic_entry=dict(events=[], index=dict(events=events, summary=summary)),
                      leaders_today=dict(date='2019-05-01', members=3, priced=3, leaders=[['AAA', 1.2]]))
        text = pb.index_report(result)
        self.assertIn('Panic today', text)
        self.assertIn('Not computed', pb.index_report(dict(index_error='boom')))


class WeightLeaders(unittest.TestCase):
    def test_largest_by_cap_are_bought_in_proportion(self):
        idx = pd.bdate_range('2019-01-01', periods=200)
        close = pd.DataFrame({'AAA': np.full(200, 100.), 'BBB': np.full(200, 50.), 'GONE': np.full(200, 10.)}, index=idx)
        close.iloc[120:, 0] = 110.                                  # AAA +10% after the signal
        volume = pd.DataFrame(1e6, index=idx, columns=close.columns)
        rows = pb.parse_members('date,tickers\n2019-04-01,"AAA,BBB,GONE"\n')
        shares = {'AAA': 3e9, 'BBB': 2e9, 'GONE': None}
        spx = pd.Series(100., index=idx)
        day = idx[100]
        events = pb.weight_leaders([day], rows, close, volume, spx, lambda t, d: shares[t], horizons=(21,), top=2)
        e = events[0]
        self.assertEqual([t for t, _ in e['leaders']], ['AAA', 'BBB'])     # 300bn vs 100bn
        self.assertAlmostEqual(dict(e['leaders'])['AAA'], 0.75)
        self.assertEqual(e['missing_shares'], ['GONE'])
        expected = 0.75 * (110 / 100 * (1 - pb.COST) / (1 + pb.COST) - 1) + 0.25 * ((1 - pb.COST) / (1 + pb.COST) - 1)
        self.assertAlmostEqual(e['returns']['21']['leaders'], expected)
        s = pb.weight_summary(events, horizons=(21,))
        self.assertEqual((s['21']['n'], s['21']['beats_spx']), (1, 1))
        json.dumps(dict(events=events, summary=s), allow_nan=False)


class Stops(unittest.TestCase):
    def test_basket_and_index_stops_sell_the_close_after_the_breach(self):
        idx = pd.bdate_range('2021-01-01', periods=300)
        path = np.r_[np.full(20, 100.), np.linspace(100, 80, 40), np.full(240, 80.)]
        close = pd.DataFrame({'AAA': path}, index=idx)
        spx = pd.Series(np.r_[np.full(20, 100.), np.linspace(100, 95, 280)], index=idx)
        event = dict(date=str(idx[10].date()), leaders=[['AAA', 1.0]])
        euphoria = [idx[200]]                                            # euphoria comes late
        rules = pb.exit_rules([event], close, spx, euphoria)[0]['rules']
        breach10 = int(np.argmax(path[11:] <= 90.0)) + 11                # first close 10% under the buy at idx[11]
        self.assertEqual(rules['euphoria_stop_basket_10']['exit'], str(idx[breach10 + 1].date()))
        self.assertTrue(rules['euphoria_stop_basket_10']['stopped'])
        self.assertTrue(rules['euphoria_stop_basket_15']['stopped'])
        self.assertFalse(rules['euphoria_stop_spx_10']['stopped'])       # the S&P never falls 10%
        self.assertEqual(rules['euphoria_stop_spx_10']['exit'], rules['euphoria_or_252']['exit'])
        self.assertGreater(rules['euphoria_stop_basket_10']['ret'], rules['euphoria_or_252']['ret'])
        summary = pb.exit_summary(pb.exit_rules([event], close, spx, euphoria))
        self.assertEqual(summary['euphoria_stop_basket_15']['stopped'], 1)
        json.dumps(summary, allow_nan=False)


class Splits(unittest.TestCase):
    def test_reported_shares_are_put_in_todays_split_terms(self):
        splits = [(pd.Timestamp('2020-08-31'), 4.0), (pd.Timestamp('2021-08-02'), 0.125)]
        self.assertEqual(pb.split_factor(splits, pd.Timestamp('2019-01-02')), 0.5)
        self.assertEqual(pb.split_factor(splits, pd.Timestamp('2021-01-04')), 0.125)
        self.assertEqual(pb.split_factor(splits, pd.Timestamp('2022-01-03')), 1.0)

    def test_market_cap_uses_the_split_only_close(self):
        idx = pd.bdate_range('2019-01-01', periods=150)
        total = pd.DataFrame({'HIGH_YIELD': np.full(150, 50.), 'GROWTH': np.full(150, 90.)}, index=idx)
        split_only = pd.DataFrame({'HIGH_YIELD': np.full(150, 100.), 'GROWTH': np.full(150, 90.)}, index=idx)
        volume = pd.DataFrame(1e6, index=idx, columns=total.columns)
        rows = pb.parse_members('date,tickers\n2019-04-01,"HIGH_YIELD,GROWTH"\n')
        e = pb.weight_leaders([idx[100]], rows, total, volume, pd.Series(100., index=idx), lambda t, d: 1e9,
                              horizons=(21,), top=1, cap_close=split_only)[0]
        self.assertEqual(e['leaders'][0][0], 'HIGH_YIELD')       # 100bn, not the dividend-shrunk 50bn


class ExitRules(unittest.TestCase):
    def test_euphoria_exits_and_open_positions(self):
        idx = pd.bdate_range('2019-01-01', periods=400)
        close = pd.DataFrame({'AAA': np.linspace(100, 200, 400)}, index=idx)
        spx = pd.Series(np.linspace(100, 150, 400), index=idx)
        event = dict(date=str(idx[10].date()), leaders=[['AAA', 1.0]])
        euphoria = [idx[30], idx[120]]                       # 19 and 109 sessions after the buy at idx[11]
        row = pb.exit_rules([event], close, spx, euphoria)[0]['rules']
        self.assertEqual(row['hold_63']['exit'], str(idx[74].date()))
        self.assertEqual(row['euphoria']['exit'], str(idx[31].date()))        # the close after the signal
        self.assertEqual(row['euphoria_after_63']['exit'], str(idx[121].date()))
        self.assertEqual(row['euphoria_or_252']['exit'], str(idx[31].date()))
        expected = close['AAA'].iloc[31] / close['AAA'].iloc[11] * (1 - pb.COST) / (1 + pb.COST) - 1
        self.assertAlmostEqual(row['euphoria']['ret'], expected)
        none = pb.exit_rules([event], close, spx, [])[0]['rules']
        self.assertTrue(none['euphoria']['open'])                       # never euphoric: still held
        self.assertEqual(none['euphoria_or_252']['sessions'], 252)
        rows = pb.exit_rules([event], close, spx, euphoria)
        summary = pb.exit_summary(rows)
        self.assertEqual(summary['euphoria']['n'], 1)
        json.dumps(dict(rows=rows, summary=summary), allow_nan=False)    # numpy types broke run 45229940750


if __name__ == '__main__':
    unittest.main()
