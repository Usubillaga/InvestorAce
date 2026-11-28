import unittest

import numpy as np
import pandas as pd

import credit_followup as cf


def series():
    idx = pd.bdate_range('1986-01-01', periods=3000)
    t = np.arange(len(idx))
    spx = pd.Series(100 * np.exp(0.0003 * t), index=idx)
    spx.iloc[1500:1600] *= np.linspace(1, 0.7, 100)          # a 30% fall ...
    spx.iloc[1600:1800] *= 0.7 * np.ones(200)
    spx.iloc[1800:] *= 0.7
    spx.iloc[1800:2100] *= np.linspace(1, 1 / 0.7, 300)      # ... and the recovery
    spx.iloc[2100:] *= 1 / 0.7
    credit = pd.Series(2.0, index=idx)
    credit.iloc[1450:1700] = 4.0                              # wide during the fall
    return spx, credit


class CreditFollowupTest(unittest.TestCase):
    def test_episodes_once_per_fall(self):
        spx, _ = series()
        self.assertEqual(len(cf.episodes(spx, 0.15)), 1)
        self.assertEqual(len(cf.episodes(spx, 0.20)), 1)

    def test_plans_and_bands(self):
        spx, credit = series()
        r = cf.study(spx, credit)
        row = r['depths']['15']['rows'][0]
        self.assertEqual(row['band'], 'wide (> +1.0 pp)')
        lump, dip = row['plans']['lump']['252'], row['plans']['dip3']['252']
        self.assertGreater(dip['ret'], lump['ret'])            # buying lower in a continuing fall pays
        self.assertGreater(dip['drawdown'], lump['drawdown'])
        self.assertIsNotNone(row['recovery'])
        self.assertIn('Credit stress follow-up', cf.report(r))
        self.assertTrue(r['all_days']['wide_episodes'])

    def test_buy_days(self):
        spx, _ = series()
        self.assertEqual(cf.buy_days(spx, 10, 'time3'), [10, 31, 52])
        self.assertEqual(cf.buy_days(spx, 10, 'dip3_cash'), [10, None, None])
        self.assertEqual(cf.buy_days(spx, 10, 'dip3'), [10, 136, 136])


if __name__ == '__main__':
    unittest.main()
