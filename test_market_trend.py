"""Market-wide trend scan on synthetic prices (no network)."""
import unittest

import numpy as np
import pandas as pd

import market_trend as mt
import trading_desk as td


def market(n=360):
    idx = pd.bdate_range('2025-08-01', periods=n)
    t = np.arange(n)
    close = pd.DataFrame({
        'UP': 50 * np.exp(0.002 * t),                                    # steady uptrend all year
        'TURN': np.r_[np.linspace(80, 40, n - 60), np.linspace(40, 75, 60)],   # fell, now turning up
        'DOWN': 100 * np.exp(-0.002 * t),
        'CHEAP': np.full(n, 2.),                                         # under 5 USD: excluded
        'THIN': 50 * np.exp(0.002 * t),
        'JUMP': np.r_[np.full(n - 30, 20.), np.full(30, 40.)]}, index=idx)          # one +100% day                      # too little traded: excluded
    volume = pd.DataFrame(1e6, index=idx, columns=close.columns)
    volume['THIN'] = 1000.
    spx = pd.Series(5000 * np.exp(0.0005 * t), index=idx)
    return close, volume, spx


class Analyse(unittest.TestCase):
    def test_opportunities_require_same_listing_session_and_rank_eligibility(self):
        trend = dict(schema='market-trend-v1', as_of='2026-11-20',
                     opportunity_trends=[dict(ticker='X', new_uptrend=True)])
        row = dict(yahoo='X', price_date='2026-11-20', rank_eligible=True, band='Buy', score=7)
        for override in ({'price_date':'2026-11-19'}, {'yahoo':'X.L'}, {'rank_eligible':False}, {'band':'Hold positiv'}):
            scan = dict(schema='market-scan-v1', candidates=[dict(row, **override)])
            self.assertFalse(td.opportunity_candidates(scan, trend))
        self.assertEqual(td.opportunity_candidates(dict(schema='market-scan-v1', candidates=[row,row]), trend)[0]['ticker'], 'X')

    def test_population_trends_new_uptrends_and_breadth(self):
        close, volume, spx = market()
        doc = mt.analyse(close, volume, spx, names={'UP': 'Up Inc'})
        self.assertEqual(doc['population'], 4)                           # CHEAP and THIN filtered out
        self.assertNotIn('JUMP', {r['ticker'] for r in doc['leaders'] + doc['new_uptrends']})
        self.assertEqual({r['ticker'] for r in doc['leaders']}, {'UP', 'TURN'})
        self.assertEqual([r['ticker'] for r in doc['new_uptrends']], ['TURN'])
        self.assertEqual({r['ticker']: r['name'] for r in doc['leaders']}['UP'], 'Up Inc')
        last = doc['breadth'][-1]
        self.assertAlmostEqual(last['pct200'], 100 * 3 / 4, places=0)
        self.assertTrue(all(r['uptrend'] > 0 for r in doc['breadth']))   # never a fake 0% from short history
        self.assertEqual(len(doc['breadth']), mt.BREADTH_SESSIONS)
        self.assertGreater(doc['leaders'][0]['rs6'], 0)

    def test_page_section_marks_universe_members_and_handles_a_missing_file(self):
        close, volume, spx = market()
        doc = mt.analyse(close, volume, spx)
        html = td.render_market(doc, {'UP': dict(yf='UP')})
        self.assertIn('Turning up', html)
        self.assertIn('<b>UP</b> ✓', html)
        self.assertIn('<b>TURN</b></td>', html)
        self.assertIn('not available yet', td.render_market(None, {}))
        self.assertIn('not available yet', td.render_market({'schema': 'other'}, {}))


if __name__ == '__main__':
    unittest.main()
