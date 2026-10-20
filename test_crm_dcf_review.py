"""CRM DCF notes must reproduce the reviewed math without changing decisions."""
import copy
import json
import unittest
from unittest.mock import patch

import source_review
from test_framework_contract import engine


def dcf_fixture():
    return {
        'schema': 'equity-dcf-review-v1', 'status': 'CONDITIONAL',
        'as_of': '2026-10-20', 'currency': 'USD',
        'cash_flow_basis': 'NORMALIZED_FCFF_PROXY',
        'normalization': {
            'reported_fy_fcf': 14402, 'guided_fcf_growth_low': .04,
            'guided_fcf_growth_high': .05, 'guided_revenue': 46250,
            'sbc_share': .09, 'quarterly_interest': 473,
            'half_year_other_income': 214, 'half_year_financing_principal': 306,
            'tax_rate': .223},
        'capital_bridge': {
            'as_of': '2026-07-31', 'cash': 8310, 'marketable_securities': 3093,
            'financial_debt': 39500, 'strategic_investments': 11324,
            'strategic_value_fraction': .5, 'diluted_shares': 827,
            'shares_basis': 'Q3 FY2027 guided diluted weighted-average proxy'},
        'reference_quote': {
            'price': 242.45, 'as_of': '2026-10-19T20:00:00Z',
            'purpose': 'DATED_REFERENCE_NOT_LIVE',
            'source_url': 'https://investor.salesforce.com/stock-info/default.aspx'},
        'scenarios': {
            'downside': {'growth_first5': .04, 'growth_second5': .025,
                         'discount_rate': .11, 'terminal_growth': .02},
            'base': {'growth_first5': .08, 'growth_second5': .04,
                     'discount_rate': .10, 'terminal_growth': .025},
            'upside': {'growth_first5': .11, 'growth_second5': .06,
                       'discount_rate': .09, 'terminal_growth': .03}},
        'reverse': {'discount_rates': [.09, .10, .11], 'terminal_growth': .025},
        'braze': {'enterprise_value': 5660, 'assumed_incremental_npv': 0},
    }


class SalesforceDcfReview(unittest.TestCase):
    def calculate(self, note):
        function = getattr(source_review, 'dcf_results', None)
        self.assertTrue(callable(function), 'A conditional DCF calculation boundary is required')
        return function(note)

    def test_reviewed_cashflow_and_enterprise_equity_bridge_reproduce(self):
        result = self.calculate(dcf_fixture())
        self.assertAlmostEqual(result['starting_fcff'], 11413.118, places=6)
        self.assertAlmostEqual(result['capital_bridge'], -22435, places=6)
        for case, expected in (('downside', 145.17231302534225),
                               ('base', 221.56593137325436),
                               ('upside', 340.98727546169073)):
            self.assertAlmostEqual(result['scenarios'][case]['value_per_share'], expected, places=6)
        self.assertAlmostEqual(result['scenarios']['base']['terminal_share'], .5227024436273918)

    def test_reverse_growth_solves_the_same_dated_reference_price(self):
        result = self.calculate(dcf_fixture())
        for row, expected in zip(result['reverse'], (.05339810204215445,
                                                      .07390686792099055,
                                                      .0930312412719182)):
            self.assertAlmostEqual(row['growth'], expected, places=8)
            self.assertAlmostEqual(row['reproduced_price'], 242.45, places=6)

    def test_transaction_npv_is_counted_once_and_does_not_change_starting_cash(self):
        note = dcf_fixture()
        before = self.calculate(note)
        note['braze']['assumed_incremental_npv'] = 1000
        after = self.calculate(note)
        self.assertAlmostEqual(after['starting_fcff'], before['starting_fcff'])
        self.assertAlmostEqual(after['scenarios']['base']['value_per_share']
                               - before['scenarios']['base']['value_per_share'], 1000 / 827)

    def test_invalid_economic_or_quote_inputs_are_rejected(self):
        edits = [
            lambda n: n['capital_bridge'].update(diluted_shares=0),
            lambda n: n['normalization'].update(reported_fy_fcf=True),
            lambda n: n['normalization'].update(tax_rate=float('nan')),
            lambda n: n['scenarios']['base'].update(terminal_growth=.10),
            lambda n: n['reference_quote'].update(as_of='2026-10-21T20:00:00Z'),
            lambda n: n['reference_quote'].update(source_url='javascript:alert(1)'),
            lambda n: n.update(status='VERIFIED'),
        ]
        for edit in edits:
            note = dcf_fixture()
            edit(note)
            with self.subTest(edit=edit), self.assertRaises(ValueError):
                self.calculate(note)

    def test_conditional_panel_keeps_reference_and_review_limits_visible(self):
        from test_source_review import review_fixture
        doc = review_fixture()
        doc['as_of'] = '2026-10-20'
        doc['entries']['TEST']['valuation']['dcf'] = dcf_fixture()
        html = source_review.panel({'TEST': {}}, source_review.load(json.dumps(doc)))
        self.assertIn('dcf-TEST', html)
        self.assertIn('221.57', html)
        self.assertIn('7.39%', html)
        self.assertIn('2026-10-19T20:00:00Z', html)
        self.assertIn('Conditional', html)
        self.assertIn('Vorläufig', html)
        self.assertIn('Condicional', html)
        self.assertIn('not a live quote', html)
        self.assertIn('cash-flow growth', html)
        self.assertIn('Braze', html)
        self.assertIn('827', html)

    def test_crm_register_and_scoreboard_have_a_reproducible_review_link(self):
        doc = source_review.load()
        self.assertIn('CRM', doc['entries'])
        note = doc['entries']['CRM']['valuation'].get('dcf')
        self.assertIsNotNone(note, 'The committed CRM review needs its model inputs')
        self.assertEqual(doc['entries']['CRM']['valuation']['status'], 'PARTIAL')
        self.assertEqual(doc['entries']['CRM']['insider']['status'], 'UNAVAILABLE')
        self.assertAlmostEqual(self.calculate(note)['scenarios']['base']['value_per_share'],
                               221.56593137325436, places=6)
        row = dict(engine.DATA['CRM'], price=242.45, r_wacc=.1003)
        with patch.object(engine, 'DATA', {'CRM': row}), \
             patch.object(engine, 'sector_performance', return_value={}), \
             patch.object(engine, 'forward_run', return_value={'ok': False}):
            html = engine.build_html(macro={'ok': False}, write=False, reviews=doc)
        self.assertIn('href="#dcf-CRM"', html)

    def test_register_update_does_not_redate_old_insider_coverage(self):
        from test_source_review import review_fixture
        doc = review_fixture()
        doc['as_of'] = '2026-10-20'
        cell = source_review.insider_cell('TEST', doc)
        self.assertIn('2026-10-14', cell)
        self.assertNotIn('2026-10-20', cell)

    def test_dcf_publication_leaves_scores_regimes_and_portfolio_decisions_unchanged(self):
        rows = copy.deepcopy(engine.DATA)
        for row in rows.values():
            row['price'] = 100
        def decisions():
            return {t: (engine.score(d), engine.ngv(d), engine.cushion(d),
                        engine.regime_scores(d), engine.verdict(t, d)) for t, d in rows.items()}
        with patch.object(engine, 'DATA', rows):
            before = decisions()
            books = [engine.regime_book(r) for r in engine.REGIMES]
            proposals = [engine.portfolio_proposal(r) for r in engine.REGIMES]
            source_review.panel(rows, source_review.load())
            self.assertEqual(decisions(), before)
            self.assertEqual(books, [engine.regime_book(r) for r in engine.REGIMES])
            self.assertEqual(proposals, [engine.portfolio_proposal(r) for r in engine.REGIMES])


if __name__ == '__main__':
    unittest.main()
