"""Source review must explain limits without creating model or insider signals."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import evidence
from test_framework_contract import engine


def review_fixture():
    return {'schema': 'source-reviews-v1', 'as_of': '2026-10-14',
            'window_start': '2026-07-16', 'window_end': '2026-10-14', 'entries': {
                'TEST': {'issuer': 'Test issuer', 'listing': 'TEST',
                         'valuation': {'status': 'PARTIAL', 'reason': 'Sustainable FCF bridge missing.',
                                       'sources': [{'url': 'https://www.sec.gov/filing',
                                                    'title': 'Issuer filing', 'published_at': '2026-08-01'}]},
                         'insider': {'status': 'PARTIAL', 'reason': 'Only one filing inspected.',
                                     'coverage': {'complete': False},
                                     'sources': [{'url': 'https://www.sec.gov/form4', 'title': 'Form 4'}],
                                     'limitations': ['Window coverage incomplete.'],
                                     'transactions': [
                                         {'owner': 'Owner', 'role': 'Officer', 'code': code,
                                          'transaction_date': '2026-08-01', 'filing_date': '2026-08-03',
                                          'shares': 10, 'price': 5, 'currency': 'USD',
                                          'ten_b5_1': None, 'ownership': 'DIRECT',
                                          'security_title': 'Common Stock',
                                          'source_url': 'https://www.sec.gov/form4', 'note': ''}
                                         for code in ('P', 'S', 'A', 'M', 'F', 'G')]}}}}


class SourceReview(unittest.TestCase):
    def module(self):
        module = getattr(engine, 'SOURCE_REVIEW', None)
        self.assertIsNotNone(module, 'A source review boundary must be available to report builds')
        return module

    def test_zero_activity_requires_complete_coverage(self):
        module = self.module()
        doc = review_fixture()
        insider = doc['entries']['TEST']['insider']
        insider.update(status='CHECKED_NO_EVENTS', transactions=[])
        with self.assertRaises(ValueError):
            module.load(json.dumps(doc))
        insider['coverage']['complete'] = True
        loaded = module.load(json.dumps(doc))
        self.assertEqual(loaded['entries']['TEST']['insider']['status'], 'CHECKED_NO_EVENTS')

    def test_invalid_links_and_nonfinite_transactions_are_rejected(self):
        module = self.module()
        for field, value in (('source_url', 'javascript:alert(1)'), ('shares', float('inf')),
                             ('transaction_date', '2026-10-15'), ('ten_b5_1', 1)):
            doc = review_fixture()
            doc['entries']['TEST']['insider']['transactions'][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                module.load(json.dumps(doc))

    def test_employee_fund_units_are_not_hidden_or_called_stock_purchases(self):
        module = self.module()
        doc = review_fixture()
        tx = doc['entries']['TEST']['insider']['transactions'][0]
        tx.update(code='AMF_ACQUISITION_EMPLOYEE_FCPE_SUBSCRIPTION', shares=None,
                  units=1505.7538, unit_type='FCPE employee fund units')
        doc['entries']['TEST']['insider']['transactions'] = [tx]
        html = module.panel({'TEST': {}}, module.load(json.dumps(doc)))
        self.assertIn('1,505.7538', html)
        self.assertIn('Employee fund subscription', html)
        self.assertIn('FCPE employee fund units', html)
        self.assertNotIn('Purchase (open market or private)', html)

    def test_verified_share_denominators_exclude_treasury_and_duplicate_votes(self):
        expected = {'WKL': (222.439643, '2026-09-18'),
                    'NVDA': (24147, '2026-07-26'),
                    'PFE': (5699.673589, '2026-07-29'),
                    'LULU': (110.710025, '2026-08-28')}
        for ticker, (shares, asof) in expected.items():
            with self.subTest(ticker=ticker):
                row = engine.DATA[ticker]
                self.assertAlmostEqual(row['shares'], shares, places=6)
                self.assertEqual(row.get('shares_asof'), asof)
        # Primary WKL: 224,716,153 issued less 2,276,510 treasury.
        self.assertAlmostEqual(engine.ngv(dict(engine.DATA['WKL'], r_wacc=None, price=100)),
                               70.24377394815366)

    def test_reported_us_cashflows_have_explicit_period_bridges(self):
        expected = {'NVDA': (126886, '2026-08-26'), 'PFE': (10985, '2026-08-04'),
                    'NFLX': (11152, '2026-07-17')}
        for ticker, (fcf, published) in expected.items():
            with self.subTest(ticker=ticker):
                row = engine.DATA[ticker]
                self.assertEqual(row['fcf'], fcf)
                self.assertEqual(row.get('financial_published_at'), published)
                self.assertIn('fcf_reconciliation', row)
                self.assertEqual(row.get('normalization_status'), 'REVIEW_REQUIRED')
        # $13.1bn is a model assumption, not LVMH's published H1 cash flow.
        self.assertEqual(engine.DATA['LVMH'].get('reported_cash_flow', {}).get('h1_2026_operating_fcf'), 4100)
        self.assertEqual(engine.DATA['LVMH']['fcf'], 13100)

    def test_report_separates_disclosure_codes_and_unknown_coverage(self):
        module = self.module()
        doc = module.load(json.dumps(review_fixture()))
        html = module.panel({'TEST': {}, 'OTHER': {}}, doc)
        self.assertIn('1 of 2', html)
        self.assertIn('1 not reviewed', html)
        self.assertIn('open market or private', html)
        self.assertIn('Award', html)
        self.assertIn('Exercise', html)
        self.assertIn('withholding', html)
        self.assertIn('Gift', html)
        self.assertIn('10b5-1: unknown', html)
        self.assertIn('Common Stock', html)
        self.assertIn('Window coverage incomplete.', html)
        self.assertNotIn('No transactions reported', html)
        self.assertIn('NOT REVIEWED', module.insider_cell('OTHER', doc))

    def test_observation_and_html_use_the_same_detached_register(self):
        module = self.module()
        doc = review_fixture()
        source = json.dumps(doc)
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, 'source_reviews.json').write_text(source)
            bundle = evidence.model_bundle(tmp)
        self.assertEqual(bundle['sources'].get('source_reviews.json'), source)
        row = dict(engine.DATA['NFLX'], price=70.46, r_wacc=.1238)
        with patch.object(engine, 'DATA', {'TEST': row}), \
             patch.object(engine, 'sector_performance', return_value={}), \
             patch.object(engine, 'forward_run', return_value={'ok': False}):
            record = engine.observation({'ok': False}, bundle)
            frozen = record.get('_source_reviews')
            self.assertEqual(frozen, doc)
            doc['entries']['TEST']['valuation']['reason'] = 'later edit'
            html = engine.build_html(macro={'ok': False}, write=False, reviews=frozen)
        self.assertIn('Sustainable FCF bridge missing.', html)
        self.assertNotIn('later edit', html)
        self.assertEqual(module.load(source), frozen)

    def test_declaring_fcff_cannot_hide_the_missing_equity_bridge(self):
        row = dict(fcf=100, shares=10, r=.1, cur='USD', cash_flow_basis='FCFF',
                   discount_rate_basis='WACC', financial_period='2025',
                   financial_published_at='2026-02-01')
        contract = evidence.valuation_contract(row)
        self.assertNotEqual(contract['status'], 'DECLARED')
        self.assertTrue(any('net debt' in text.lower() for text in contract.get('issues', [])))

    def test_cost_of_equity_label_cannot_override_the_actual_wacc_used(self):
        row = dict(fcf=100, shares=10, r=.1, r_wacc=.08, cur='USD', cash_flow_basis='FCFE',
                   discount_rate_basis='COST_OF_EQUITY', financial_period='2025',
                   financial_published_at='2026-02-01')
        contract = evidence.valuation_contract(row)
        self.assertEqual(contract['status'], 'MISMATCH')
        self.assertEqual(contract['discount_rate_basis'], 'WACC')

    def test_concrete_growth_metric_and_required_cashflow_are_visible(self):
        row = dict(engine.DATA['NFLX'], price=70.45999908447266, r_wacc=.12383038114998626)
        html = engine.growth_comparison_badge(row)
        self.assertIn('Revenue', html)
        self.assertIn('+24.0%', html)
        self.assertIn('8.3%', html)
        self.assertIn('cash-flow', html)
        self.assertIn('No comparable', html)

    def test_source_notes_do_not_change_frozen_model_decisions(self):
        module = self.module()
        rows = copy.deepcopy(engine.DATA)
        for row in rows.values():
            row['price'] = 100
        def decisions():
            return {t: (engine.score(d), engine.risk(d), engine.ngv(d), engine.cushion(d),
                        engine.regime_scores(d), engine.verdict(t, d)) for t, d in rows.items()}
        with patch.object(engine, 'DATA', rows):
            before = decisions()
            books = [engine.regime_book(r) for r in engine.REGIMES]
            proposals = [engine.portfolio_proposal(r) for r in engine.REGIMES]
            module.panel(rows, module.load(json.dumps(review_fixture())))
            self.assertEqual(decisions(), before)
            self.assertEqual([engine.regime_book(r) for r in engine.REGIMES], books)
            self.assertEqual([engine.portfolio_proposal(r) for r in engine.REGIMES], proposals)


if __name__ == '__main__':
    unittest.main()
