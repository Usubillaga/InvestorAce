import unittest
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd
import autoscore


def financials():
    return dict(fcf=80e6, shares=10e6, rev=1000e6, rev_prev=900e6, opinc=200e6,
        ebitda=220e6, netdebt=100e6, div_yield=1., price=100., cur='USD',
        sector='Technology', name='Fixture', lo=50., hi=150., shares_prev=11e6,
        periods={key: ['TTM', '2026-09-30', '2026-06-30', '2026-03-31', '2025-12-31']
                 for key in ('rev', 'opinc', 'fcf', 'ebitda')} | {'netdebt': '2026-09-30'})


class AutoScoreIntegrity(unittest.TestCase):
    def test_unknown_categories_are_not_neutral_scores(self):
        data = financials()
        data.update(rev_prev=None, netdebt=None, div_yield=None, shares_prev=None)
        with patch.object(autoscore.yf, 'Ticker', return_value=object()), patch.object(autoscore, '_fin', return_value=data):
            row, _ = autoscore.auto_row('AAA')
        self.assertIsNone(row['sub'])
        self.assertIsNone(row['dil'])
        self.assertIsNone(row['draft_components']['g'])
        self.assertIsNone(row['draft_components']['b'])
        self.assertIsNone(row['draft_components']['r'])

    def test_complete_mechanical_draft_keeps_all_categories(self):
        with patch.object(autoscore.yf, 'Ticker', return_value=object()), patch.object(autoscore, '_fin', return_value=financials()):
            row, _ = autoscore.auto_row('AAA')
        self.assertEqual(len(row['sub']), 6)
        self.assertEqual(row['normalization_status'], 'REVIEW_REQUIRED')

    def test_ttm_is_not_compared_to_prior_annual_period(self):
        quarters = pd.to_datetime(['2026-09-30', '2026-06-30', '2026-03-31', '2025-12-31'])
        annual = pd.to_datetime(['2025-12-31', '2024-12-31'])
        tk = SimpleNamespace(fast_info={}, get_info=lambda: {},
            quarterly_cashflow=pd.DataFrame(), quarterly_balance_sheet=pd.DataFrame(),
            quarterly_income_stmt=pd.DataFrame([[100.] * 4], index=['Total Revenue'], columns=quarters),
            income_stmt=pd.DataFrame([[350., 300.]], index=['Total Revenue'], columns=annual))
        result = autoscore._fin(tk)
        self.assertEqual(result['rev'], 400.)
        self.assertIsNone(result['rev_prev'])
        self.assertIsNone(result['div_yield'])
