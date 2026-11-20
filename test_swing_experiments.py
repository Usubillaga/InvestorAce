import unittest

import pandas as pd

from swing_experiments import RISK_NAV, SIZE, gap_size, size_trial


class SwingExperimentTests(unittest.TestCase):
    def test_cap_uses_only_gaps_strictly_before_the_decision(self):
        now = '2026-11-05'
        days = pd.date_range(end='2026-11-04', periods=126).strftime('%Y-%m-%d')
        gaps = pd.Series(-.20, index=days)
        gaps.loc[now] = -.80
        weight, risk = gap_size(gaps, now)
        self.assertAlmostEqual(risk, .20)
        self.assertAlmostEqual(weight, RISK_NAV / .20)

    def test_insufficient_data_keeps_control_size_and_reports_no_estimate(self):
        series = pd.Series([-.30], index=['2026-10-10'])
        self.assertEqual(gap_size(series, '2026-11-05'), (SIZE, None))

    def test_matched_fill_and_opening_gap_use_scaled_position_and_same_dates(self):
        days = ('2026-11-03', '2026-11-04', '2026-11-05')
        submitted = days[0] + 'T23:00:00+00:00'
        ledger = {
            'decisions': [{'session': d, 'at': d + 'T23:00:00+00:00'} for d in days],
            'accounts': {'timing': {'orders': [
                dict(status='Filled', side='Buy', ticker='A', symbol='A', currency='EUR',
                     euros=1200., day=days[1], submitted=submitted, fx=1.),
                dict(status='Filled', side='Sell', ticker='A', symbol='A', currency='EUR',
                     day=days[2])
            ]}},
        }
        prices = {'tracked': {'^GSPC': [(d, 1.) for d in days]},
                  'paper_eurusd': [], 'paper_returns': {'A': [(days[2], days[1], .8, 80.)]}}
        dates = pd.date_range(end='2026-11-02', periods=126).strftime('%Y-%m-%d')
        data = pd.DataFrame({'gap': -.20, 'previous': ''}, index=dates)
        data.loc[days[2], ['gap','previous']] = [-.20, days[1]]
        control = size_trial(ledger, prices, {'A': data}, use_cap=False)
        capped = size_trial(ledger, prices, {'A': data}, use_cap=True)
        self.assertEqual(control['buys'], capped['buys'])
        self.assertEqual(capped['capped'], 1)
        self.assertEqual(control['incomplete_marks'], 0)
        self.assertAlmostEqual(control['ending_pct'], -2.4216)
        self.assertAlmostEqual(capped['ending_pct'], -.9686)
        self.assertAlmostEqual(control['worst_observed_open_pct'], -2.4003)
        self.assertAlmostEqual(capped['worst_observed_open_pct'], -.9600)


if __name__ == '__main__':
    unittest.main()
