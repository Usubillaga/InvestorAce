import json
import math
import unittest
from types import SimpleNamespace

import pandas as pd
import epv


def inputs(**changes):
    values = dict(revenue=[100.] * 3, gross_profit=[50.] * 3, rd=[1.] * 3,
                  sga=[10.] * 3, capex=[2.] * 5, dep_amort=[1.] * 5,
                  tax_rate=.2, net_debt=0., shares=10., wacc=.1)
    values.update(changes)
    return values


def ticker(debt=True, cash=True):
    dates = pd.to_datetime(['2025-12-31', '2024-12-31', '2023-12-31'])
    income = pd.DataFrame([[100.] * 3, [50.] * 3, [1.] * 3, [10.] * 3],
        index=['Total Revenue', 'Gross Profit', 'Research And Development',
               'Selling General And Administration'], columns=dates)
    flow = pd.DataFrame([[-2.] * 3, [1.] * 3],
        index=['Capital Expenditure', 'Depreciation And Amortization'], columns=dates)
    balance = {'Ordinary Shares Number': [10.] * 3}
    if debt:
        balance['Total Debt'] = [0.] * 3
    if cash:
        balance['Cash And Cash Equivalents'] = [0.] * 3
    return SimpleNamespace(income_stmt=income, cashflow=flow,
        balance_sheet=pd.DataFrame.from_dict(balance, orient='index', columns=dates))


class EpvIntegrity(unittest.TestCase):
    def test_missing_net_debt_is_not_zero(self):
        self.assertIsNone(epv.compute(**inputs(net_debt=None)))

    def test_known_zero_and_net_cash_are_valid(self):
        self.assertAlmostEqual(epv.compute(**inputs())['epv_per_share'], 30.2)
        self.assertAlmostEqual(epv.compute(**inputs(net_debt=-10.))['epv_per_share'], 31.2)

    def test_invalid_scalars_do_not_make_a_valuation(self):
        for key in ('shares', 'wacc', 'tax_rate', 'net_debt'):
            for value in (math.inf, -math.inf, math.nan, True):
                with self.subTest(key=key, value=value):
                    self.assertIsNone(epv.compute(**inputs(**{key: value})))
        for value in (0., -10.):
            self.assertIsNone(epv.compute(**inputs(shares=value)))

    def test_income_window_uses_same_years_without_older_outlier(self):
        a = inputs(revenue=[100., 200., 300., 1000.],
                   gross_profit=[50., None, 150., 1000.], rd=[1.] * 4, sga=[10.] * 4)
        b = dict(a, revenue=[100., 200., 300., 100000.],
                 gross_profit=[50., None, 150., 100000.])
        self.assertAlmostEqual(epv.compute(**a)['epv_per_share'], 70.2)
        self.assertAlmostEqual(epv.compute(**a)['epv_per_share'], epv.compute(**b)['epv_per_share'])

    def test_absent_debt_or_cash_stays_unknown(self):
        for debt, cash in ((False, True), (True, False)):
            with self.subTest(debt=debt, cash=cash):
                result = epv.fetch_ticker(ticker(debt, cash))
                self.assertTrue(result is None or result['net_debt'] is None)

    def test_nonfinite_statement_cells_are_serializable(self):
        tk = ticker()
        tk.income_stmt.loc['Total Revenue', tk.income_stmt.columns[0]] = math.inf
        json.dumps(epv.fetch_ticker(tk), allow_nan=False)

    def test_assumed_rd_is_disclosed(self):
        tk = ticker()
        tk.income_stmt = tk.income_stmt.drop('Research And Development')
        result = epv.fetch_ticker(tk)
        self.assertEqual(result.get('rd_source'), 'assumed-zero-unavailable')
        self.assertTrue(any('R&D' in x for x in epv.confidence(result)['reasons']))
