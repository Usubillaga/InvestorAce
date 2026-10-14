"""ASML primary-guidance reconciliation and unnormalized-estimate boundaries."""
import copy
import unittest
from unittest.mock import patch

import evidence
from portfolio import trade_plan
from test_framework_contract import engine


class ASMLInputs(unittest.TestCase):
    def test_deliver_reconciles_primary_guidance_in_percentage_units(self):
        row = engine.DATA['ASML']
        # Q3 release: EUR44-45bn, FY2025 statement: EUR32,667.3m.
        self.assertAlmostEqual(row['deliver'], 36.22184876007506, places=10)
        source = row['deliver_reconciliation']
        midpoint = (source['guidance_low'] + source['guidance_high']) / 2
        self.assertEqual(source['unit'], 'EUR million')
        self.assertEqual(source['published_at'], '2026-10-14')
        self.assertAlmostEqual(100 * (midpoint / source['baseline_revenue'] - 1),
                               row['deliver'], places=10)
        self.assertEqual(row['yf'], 'ASML.AS')
        self.assertEqual(row['cur'], 'EUR')

    def test_reported_cash_flow_includes_intangibles_without_overwriting_estimate(self):
        row = engine.DATA['ASML']
        self.assertIn('reported_cash_flow', row)
        reported = row['reported_cash_flow']
        def fcf(period):
            return period['ocf'] - period['ppe_purchases'] - period['intangible_purchases']
        self.assertAlmostEqual(fcf(reported['fy2025']), 11027.3)
        self.assertAlmostEqual(fcf(reported['ytd2025_9m']), 87.4)
        self.assertAlmostEqual(fcf(reported['ytd2026_9m']), 10059.5)
        ttm = fcf(reported['fy2025']) - fcf(reported['ytd2025_9m']) + fcf(reported['ytd2026_9m'])
        self.assertAlmostEqual(ttm, reported['ttm_fcf'])
        self.assertAlmostEqual(ttm, 20999.4)
        self.assertEqual(row['fcf'], 10000)
        self.assertEqual(row['shares'], 383)
        self.assertEqual(row['built'], 'est')

    def test_dated_guidance_does_not_certify_undated_fcf(self):
        row = engine.DATA['ASML']
        self.assertEqual(row.get('normalization_status'), 'REVIEW_REQUIRED')
        contract = evidence.valuation_contract(row)
        self.assertEqual(contract['status'], 'UNVERIFIED')
        self.assertEqual(contract['cash_flow_basis'], 'UNSPECIFIED')
        self.assertIn('financial_period', contract['missing'])
        self.assertIn('financial_published_at', contract['missing'])

    def test_bootstrap_preserves_guidance_and_review_metadata(self):
        row = copy.deepcopy(engine.DATA['ASML'])
        before = copy.deepcopy(row)
        with patch.object(engine, 'DATA', {'ASML': row}), \
             patch.object(engine.yf, 'Ticker', side_effect=AssertionError('unexpected Yahoo pull')):
            engine.bootstrap_fundamentals()
        self.assertEqual(row, before)

    def test_revenue_guidance_has_no_cashflow_cushion_or_decision_effect(self):
        after = dict(engine.DATA['ASML'], price=1509.6, r_wacc=0.1133827008662827)
        before = dict(after, deliver=35.0)
        self.assertEqual(after['deliver_basis'], 'REVENUE_PROXY')
        self.assertIsNone(engine.cushion(after))
        self.assertIsNone(engine.cushion(before))
        for fn in (engine.ngv, engine.cover, engine.implied_growth, engine.priced_in_live,
                   engine.score, engine.risk, engine.regime_scores):
            self.assertEqual(fn(before), fn(after), fn.__name__)
        self.assertEqual(engine.verdict('ASML', after)[0], 'ACCUMULATE')
        self.assertEqual(engine.regime_spec_sha256(), engine.REGIME_SPEC_EXPECTED_SHA256)
        before_plan = trade_plan(before, engine.entry_price(before), as_of='2026-10-14')
        after_plan = trade_plan(after, engine.entry_price(after), as_of='2026-10-14')
        self.assertEqual(before_plan, after_plan)
        self.assertEqual(after_plan['status'], 'WAIT_FOR_PULLBACK')

    def test_review_is_captured_and_visible_in_existing_report(self):
        row = dict(engine.DATA['ASML'], price=1509.6, r_wacc=0.1133827008662827)
        record = evidence.create_record({'ASML': row}, {}, {}, {}, 'test-source')
        archived = record['_evidence']['inputs']['ASML']
        self.assertEqual(archived.get('normalization_status'), 'REVIEW_REQUIRED')
        self.assertEqual(archived['reported_cash_flow']['ttm_fcf'], 20999.4)
        with patch.object(engine, 'DATA', {'ASML': row}), \
             patch.object(engine, 'sector_performance', return_value={}), \
             patch.object(engine, 'forward_run', return_value={'ok': False, 'note': 'offline'}):
            html = engine.build_html(macro={'ok': False}, write=False)
        self.assertIn('NORMALIZATION REVIEW', html)
        self.assertIn('Revenue +36.2%', html)
        self.assertIn('No comparable cash-flow forecast', html)
        self.assertIn('intangible', html)
        self.assertIn('undated', html)


if __name__ == '__main__':
    unittest.main()
