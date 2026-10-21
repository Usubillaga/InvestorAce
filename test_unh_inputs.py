"""Primary-report regression: use a full TTM, retain normalization limits."""
import copy
import unittest
from unittest.mock import patch

import evidence
from test_framework_contract import engine


class UnitedHealthInputs(unittest.TestCase):
    def test_reported_ttm_replaces_undated_bootstrap(self):
        row = copy.deepcopy(engine.DATA['UNH'])
        # FY2025 less 9M2025 plus 9M2026, issuer statements in USD millions.
        # A 9M annualization or a reserve-development haircut would fail this.
        self.assertEqual(row['fcf'], 22826)
        self.assertEqual(row['fcf_ttm'], 22826)
        self.assertEqual(row['cash_flow_basis'], 'OCF_MINUS_CAPEX')
        self.assertEqual(row['financial_period'], '2025-10-01/2026-09-30')
        self.assertEqual(row['financial_published_at'], '2026-10-13')
        self.assertEqual(row['normalization_status'], 'REVIEW_REQUIRED')
        bridge = row['fcf_reconciliation']
        ocf = bridge['fy2025']['ocf'] - bridge['ytd2025_9m']['ocf'] + bridge['ytd2026_9m']['ocf']
        capex = bridge['fy2025']['capex'] - bridge['ytd2025_9m']['capex'] + bridge['ytd2026_9m']['capex']
        self.assertEqual(ocf, 26195)
        self.assertEqual(capex, 3369)
        self.assertEqual(row['fcf'], ocf - capex)
        self.assertIsNone(row['deliver'])
        self.assertIsNone(row['sub'])
        self.assertEqual(row['score_fixed'], 6.35)

    def test_shares_have_a_primary_date_and_are_not_eps_weighted(self):
        row = engine.DATA['UNH']
        self.assertEqual(row['shares'], 897.594847)
        self.assertEqual(row['shares_asof'], '2026-07-31')
        self.assertEqual(row['shares_basis'], 'ISSUED_AND_OUTSTANDING')
        self.assertIn('UNH_2026.6.30_10-Q.pdf', row['shares_source_url'])

    def test_bootstrap_cannot_overwrite_primary_inputs(self):
        row = copy.deepcopy(engine.DATA['UNH'])
        expected = copy.deepcopy(row)
        with patch.object(engine, 'DATA', {'UNH': row}), \
             patch.object(engine.yf, 'Ticker', side_effect=AssertionError('unexpected Yahoo pull')):
            engine.bootstrap_fundamentals()
        self.assertEqual(row, expected)
        self.assertEqual(row['fcf'], 22826)

    def test_unnormalized_proxy_is_not_a_declared_fcfe_or_fcff(self):
        contract = evidence.valuation_contract(engine.DATA['UNH'])
        self.assertEqual(contract['cash_flow_basis'], 'OCF_MINUS_CAPEX')
        self.assertEqual(contract['status'], 'UNVERIFIED')

    def test_reported_ttm_does_not_claim_midcycle_normalization(self):
        self.assertIsNone(engine.cycle_pos(engine.DATA['UNH']))
        self.assertEqual(engine.cycle_note(engine.DATA['UNH']), '')
        # Producer normalization still has a separate TTM/mid-cycle ratio.
        producer = dict(fcf=180, fcf_ttm=614, midcycle=True)
        self.assertEqual(engine.cycle_pos(producer), 3.41)
        self.assertIn('PEAK 3.41x mid-cycle', engine.cycle_note(producer))

    def test_normalization_limit_is_visible_next_to_valuation(self):
        row = dict(engine.DATA['UNH'], price=378.5199890136719,
                   r_wacc=0.07507895299289014)
        with patch.object(engine, 'DATA', {'UNH': row}), \
             patch.object(engine, 'sector_performance', return_value={}), \
             patch.object(engine, 'forward_run', return_value={'ok': False, 'note': 'offline'}):
            html = engine.build_html(macro={'ok': False}, write=False)
        self.assertIn('NORMALIZATION REVIEW', html)
        self.assertIn('not normalized distributable cash', html)
        self.assertIn('2026-07-31', html)

    def test_fixed_score_and_regime_formula_stay_independent(self):
        row = dict(engine.DATA['UNH'], price=378.5199890136719,
                   r_wacc=0.07507895299289014)
        self.assertEqual(engine.score(row), 6.35)
        self.assertEqual(engine.legacy_verdict('UNH', row)[0], 'HOLD')
        self.assertEqual(engine.verdict('UNH', row)[0], 'REVIEW REQUIRED')
        self.assertIsNone(engine.cushion(row))
        self.assertEqual(engine.regime_spec_sha256(), engine.REGIME_SPEC_EXPECTED_SHA256)
        weighted = dict(row, weight=99)
        self.assertEqual(engine.regime_scores(weighted), engine.regime_scores(row))

    def test_same_quote_and_rate_expose_priced_in_band_crossing(self):
        after = dict(engine.DATA['UNH'], price=378.5199890136719,
                     r_wacc=0.07507895299289014)
        before = dict(after, fcf=23617, shares=897.59)
        self.assertGreaterEqual(engine.cover(before), .90)
        self.assertLess(engine.cover(after), .90)
        self.assertEqual(engine.priced_in_live(before), 9.0)
        self.assertEqual(engine.priced_in_live(after), 8.0)
        self.assertAlmostEqual(engine.ngv(after), 338.7125236583921)
        self.assertAlmostEqual(engine.implied_growth(after) * 100, .7398691812223118)


if __name__ == '__main__':
    unittest.main()
