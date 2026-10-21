import copy
import importlib
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from test_framework_contract import engine

NOW = datetime(2026, 10, 20, 16, 15, tzinfo=timezone.utc)
SOURCE = 'https://www.sec.gov/Archives/example'


def complete_row():
    return dict(yf='AAA', price=100., quote_observed_at='2026-10-20T15:40:00+00:00',
        fcf=8., shares=1., r=.08, cur='USD', sub=(8.,) * 6, pr=8., dil=8.,
        sector='Pharma', built='exact', normalization_status='VERIFIED',
        cash_flow_basis='FCFE', discount_rate_basis='COST_OF_EQUITY',
        financial_period='FY2026 scenario', financial_published_at='2026-10-20',
        shares_asof='2026-10-19')


class AssessmentIntegrity(unittest.TestCase):
    def assess(self, row, **kwargs):
        self.assertTrue(hasattr(engine, 'assessment'), 'Shared assessment contract required')
        return engine.assessment(row, ticker='AAA', as_of=NOW, **kwargs)

    def reviewed(self, row):
        initial = self.assess(row)
        mod = importlib.import_module('assessment')
        note = dict(status='APPROVED', input_sha256=initial['input_sha256'],
            reviewed_at='2026-10-20T16:00:00+00:00', valid_until='2026-10-21T16:00:00+00:00',
            reviewer='Synthetic fixture reviewer',
            category_sources={key: [SOURCE] for key in engine.W}, normalization_sources=[SOURCE])
        return dict(schema=mod.REVIEW_SCHEMA, entries={'AAA': note})

    def test_fixed_total_is_legacy_only(self):
        row = complete_row()
        row.update(sub=None, score_fixed=9.8)
        result = self.assess(row)
        self.assertEqual(result['raw_score'], 9.8)
        self.assertEqual(result['calculation_status'], 'LEGACY_TOTAL')
        self.assertIsNone(result['model_score'])
        self.assertIsNone(result['rating'])
        self.assertFalse(result['new_entry_eligible'])

    def test_high_legacy_total_cannot_emit_buy(self):
        row = complete_row()
        row.update(sub=None, score_fixed=9.8, trap=True)
        self.assertEqual(engine.verdict('AAA', row)[0], 'REVIEW REQUIRED')

    def test_missing_pr_is_not_renormalized(self):
        row = complete_row()
        row.update(fcf=None, pr=None)
        result = self.assess(row)
        self.assertAlmostEqual(result['coverage_weight'], .85)
        self.assertIsNone(result['model_score'])
        self.assertAlmostEqual(result['score_lower'], 6.8)
        self.assertAlmostEqual(result['score_upper'], 8.3)
        self.assertEqual(result['missing_components'], ['pr'])

    def test_missing_dilution_is_not_neutral_six(self):
        row = complete_row()
        row.pop('dil')
        result = self.assess(row)
        self.assertAlmostEqual(result['coverage_weight'], .95)
        self.assertIn('d', result['missing_components'])
        self.assertIsNone(result['model_score'])

    def test_complete_model_is_not_an_approved_rating(self):
        result = self.assess(complete_row())
        self.assertEqual(result['calculation_status'], 'COMPLETE')
        self.assertAlmostEqual(result['model_score'], 8.225)
        self.assertIsNone(result['rating'])
        self.assertFalse(result['quality_rank_eligible'])

    def test_bound_review_can_approve_complete_evidence(self):
        row = complete_row()
        result = self.assess(row, reviews=self.reviewed(row))
        self.assertEqual(result['review_status'], 'REVIEWED')
        self.assertEqual(result['rating'], 'BUY')
        self.assertTrue(result['new_entry_eligible'])

    def test_financial_change_withdraws_approval(self):
        row = complete_row()
        reviews = self.reviewed(row)
        row['fcf'] = 9.
        result = self.assess(row, reviews=reviews)
        self.assertIsNone(result['rating'])
        self.assertIn('REVIEW_INPUT_CHANGED', [x['code'] for x in result['issues']])

    def test_retrieval_time_does_not_renew_or_break_review(self):
        row = complete_row()
        reviews = self.reviewed(row)
        row['price_ts'] = 'later retrieval'
        self.assertEqual(self.assess(row, reviews=reviews)['review_status'], 'REVIEWED')

    def test_invalid_quote_times_cannot_approve(self):
        for timestamp in (None, '2026-10-01T12:00:00+00:00', '2026-10-21T12:00:00+00:00'):
            row = complete_row()
            row['quote_observed_at'] = timestamp
            self.assertIsNone(self.assess(row, reviews=self.reviewed(row))['rating'])

    def test_normalization_and_cash_rate_contract_are_required(self):
        for changes in ({'normalization_status': 'REVIEW_REQUIRED'}, {'r_wacc': .07},
                        {'financial_published_at': '2026-10-21'}):
            row = complete_row()
            row.update(changes)
            self.assertIsNone(self.assess(row, reviews=self.reviewed(row))['rating'])

    def test_unreviewed_new_entry_stays_cash(self):
        row = complete_row()
        row.update(sub=None, score_fixed=9.8)
        original = copy.deepcopy(row)
        with patch.object(engine, 'DATA', {'AAA': row}):
            result = engine.portfolio_proposal('REFLATION')
        self.assertEqual(result['positions'], [])
        self.assertEqual(result['cash_weight'], 1.)
        self.assertEqual(row, original)

    def test_golden_regime_and_current_holdings_are_unchanged(self):
        row = complete_row()
        row.update(held=True, weight=30.)
        before = engine.regime_scores(row)
        self.assess(row)
        self.assertEqual(engine.regime_scores(row), before)
        self.assertEqual(row['weight'], 30.)
        self.assertEqual(engine.regime_regression_errors(), [])

    def test_observation_freezes_the_exact_assessment(self):
        import evidence
        row = complete_row()
        with patch.object(engine, 'DATA', {'AAA': row}):
            rec = engine.observation({'ok': False}, evidence.model_bundle(Path(__file__).parent), NOW.isoformat())
        self.assertEqual(rec['AAA']['assessment'], self.assess(row))
        self.assertEqual(rec['AAA']['score'], engine.score(row))
        self.assertEqual(rec['AAA']['verdict'], 'REVIEW REQUIRED')

    def test_fast_price_needs_a_matching_market_timestamp(self):
        from types import SimpleNamespace
        row = complete_row()
        tk = SimpleNamespace(fast_info={'last_price': 100., 'currency': 'USD'},
            get_info=lambda: {'regularMarketPrice': 105., 'regularMarketTime': 1792510800,
                              'currency': 'USD'})
        with patch.object(engine, 'DATA', {'AAA': row}), patch.object(engine.yf, 'Ticker', return_value=tk), \
                patch.object(engine, '_fetch_momentum'), patch.object(engine.WACC, 'fetch', return_value=None):
            engine.fetch_prices()
        self.assertEqual(row['price'], 105.)
        self.assertEqual(row['quote_observed_at'], datetime.fromtimestamp(1792510800, timezone.utc).isoformat())

    def test_projection_withdraws_expired_price_contribution(self):
        row = complete_row()
        mod = importlib.import_module('assessment')
        frozen = self.assess(row)
        later = mod.project(frozen, as_of=datetime(2026, 11, 1, tzinfo=timezone.utc))
        self.assertIsNone(later['model_score'])
        self.assertAlmostEqual(later['coverage_weight'], .85)
        self.assertEqual(frozen['calculation_status'], 'COMPLETE')

    def test_regime_research_screen_does_not_impose_a_quality_threshold(self):
        high = complete_row()
        high['fcf'] = 4.8
        low = complete_row()
        low.update(yf='BBB', sub=(1., 1., 1., 8., 1., 8.), dil=1.)
        self.assertLess(engine.score(low), 5.5)
        self.assertGreater(engine.fit_now(low, 'INFLATION'), engine.fit_now(high, 'INFLATION'))
        with patch.object(engine, 'DATA', {'AAA': high, 'BBB': low}):
            result = engine.screen('regime', regime='INFLATION', reviewed_only=False)
        self.assertEqual([row['t'] for row in result], ['BBB', 'AAA'])

    def test_open_material_objection_blocks_even_a_bound_approval(self):
        row = complete_row()
        row['review_objections'] = [dict(id='NORMALIZATION', severity='major', status='corrected')]
        result = self.assess(row, reviews=self.reviewed(row))
        self.assertIsNone(result['rating'])
        self.assertIn('OPEN_OBJECTION', [item['code'] for item in result['issues']])
