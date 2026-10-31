"""Only declared cash-flow growth may change the reverse-DCF cushion."""
import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch

import autoscore
import evidence
from test_framework_contract import engine


def growth_row(**overrides):
    row = dict(yf='TEST', fcf=8, shares=1, r=.08, price=200, cur='USD',
               deliver=-5, sub=(7, 7, 7, 7, 7, 7), dil=7,
               sector='Technology', held=False)
    row.update(overrides)
    return row


class GrowthBasis(unittest.TestCase):
    def test_non_cashflow_and_missing_bases_have_no_cushion(self):
        for basis in (None, 'UNSPECIFIED', 'REVENUE_PROXY', 'PRODUCTION',
                      'OPERATING_PROXY', 'EARNINGS_PROXY', 'UNKNOWN'):
            with self.subTest(basis=basis):
                row = growth_row(deliver_basis=basis)
                self.assertIsNone(engine.cushion(row))
                self.assertFalse(engine.cushion_neg(row))

    def test_declared_cashflow_retains_formula_and_negative_penalty(self):
        row = growth_row(deliver_basis='CASH_FLOW')
        self.assertAlmostEqual(engine.cushion(row), -8.846153846153847)
        self.assertEqual(engine.priced_in_live(row), 3.5)
        self.assertTrue(engine.cushion_neg(row))

    def test_cashflow_tolerance_and_producer_exclusion_are_retained(self):
        flat = growth_row(deliver_basis='CASH_FLOW', price=100, deliver=-.5)
        self.assertFalse(engine.cushion_neg(flat))
        self.assertTrue(engine.cushion_neg(dict(flat, deliver=-.5001)))
        self.assertIsNone(engine.cushion(dict(flat, midcycle=True)))

    def test_enb_dcf_per_share_remains_an_explicit_cashflow_metric(self):
        row = dict(engine.DATA['ENB'])
        row['price'] = engine.ngv(row)
        self.assertEqual(row['deliver_basis'], 'CASH_FLOW')
        self.assertEqual(engine.cushion(row), 5)
        self.assertTrue(engine.cushion_neg(dict(row, deliver=-.5001)))

    def test_proxy_growth_cannot_change_score_risk_verdict_or_fit(self):
        baseline = growth_row(deliver=None)
        for value in (-99, 99):
            row = growth_row(deliver=value, deliver_basis='REVENUE_PROXY')
            for function in (engine.score, engine.risk, engine.regime_scores):
                self.assertEqual(function(row), function(baseline))
            self.assertEqual(engine.verdict('TEST', row), engine.verdict('TEST', baseline))

    def test_nflx_withdraws_revenue_cushion_without_repricing(self):
        row = dict(engine.DATA['NFLX'], price=70.45999908447266,
                   r_wacc=.12383038114998626)
        self.assertEqual(row.get('deliver_basis'), 'REVENUE_PROXY')
        self.assertEqual(row.get('normalization_status'), 'REVIEW_REQUIRED')
        self.assertEqual((row['fcf'], row['shares']), (11152, 4163.94))
        self.assertIsNone(engine.cushion(row))
        self.assertAlmostEqual(engine.ngv(row), 21.62823541819428)
        self.assertEqual(engine.score(row), 7)
        self.assertEqual(engine.risk(row), 2.1)
        self.assertEqual(engine.regime_scores(row)['REFLATION'], 63)

    def test_growth_contract_is_archived_and_missing_basis_is_visible(self):
        row = growth_row(deliver_basis='REVENUE_PROXY', dl='revenue growth')
        contract = evidence.row_diagnostics(row, engine.W).get('growth_contract', {})
        self.assertEqual(contract.get('basis'), 'REVENUE_PROXY')
        self.assertEqual(contract['status'], 'NOT_COMPARABLE')
        self.assertFalse(contract['comparable'])
        self.assertEqual(evidence.row_diagnostics(growth_row(), engine.W)
                         ['growth_contract']['basis'], 'UNSPECIFIED')

    def test_observation_freezes_basis_version_and_replayable_outputs(self):
        row = growth_row(deliver_basis='REVENUE_PROXY')
        bundle = {'sources': {}, 'sha256': evidence.digest({})}
        with patch.object(engine, 'DATA', {'TEST': row}):
            record = engine.observation({'ok': False}, bundle)
        saved = record['_evidence']['inputs']['TEST']
        self.assertEqual(saved['deliver_basis'], 'REVENUE_PROXY')
        self.assertEqual(record['_models']['growth'], 'explicit-cash-flow-growth-v1')
        self.assertIsNone(record['TEST']['cushion'])
        self.assertFalse(record['TEST']['diagnostics']['growth_contract']['comparable'])
        for name in ('ngv', 'cover', 'score', 'risk', 'cushion'):
            self.assertEqual(getattr(engine, name)(saved), record['TEST'][name])
        row['deliver_basis'] = 'CASH_FLOW'
        self.assertEqual(saved['deliver_basis'], 'REVENUE_PROXY')

    def test_source_review_metadata_does_not_change_model_outputs(self):
        row = growth_row(deliver_basis='CASH_FLOW')
        reviewed = dict(row, normalization_status='REVIEW_REQUIRED',
                        financial_period='2025', financial_published_at='2026-02-01')
        for function in (engine.score, engine.risk, engine.ngv, engine.regime_scores):
            self.assertEqual(function(row), function(reviewed))
        self.assertEqual(engine.verdict('TEST', row), engine.verdict('TEST', reviewed))

    def test_nflx_review_and_noncomparable_growth_are_in_the_main_row(self):
        row = dict(engine.DATA['NFLX'], price=70.45999908447266,
                   r_wacc=.12383038114998626)
        with patch.object(engine, 'DATA', {'NFLX': row}), \
             patch.object(engine, 'sector_performance', return_value={}), \
             patch.object(engine, 'forward_run', return_value={'ok': False, 'note': 'offline'}):
            html = engine.build_html(macro={'ok': False}, write=False)
        main_row = html.split('<td class="tk">NFLX', 1)[1].split('</tr>', 1)[0]
        self.assertIn('Valuation: normalization review', main_row)
        self.assertIn('Revenue +24.0%', main_row)
        self.assertIn('Required cash-flow growth: 8.3%', main_row)
        self.assertIn('No comparable cash-flow forecast', main_row)
        self.assertIn('Financial period: 2025-07-01/2026-06-30', main_row)
        self.assertIn('publication date', main_row)
        self.assertIn('2026-07-17', main_row)
        self.assertIn('NORMALIZATION REVIEW', main_row)
        self.assertNotIn('+15.7', main_row)

    def test_growth_label_is_escaped_in_report(self):
        row = growth_row(deliver_basis='REVENUE_PROXY', dl='<script>unsafe</script>')
        with patch.object(engine, 'DATA', {'TEST': row}), \
             patch.object(engine, 'sector_performance', return_value={}), \
             patch.object(engine, 'forward_run', return_value={'ok': False, 'note': 'offline'}):
            html = engine.build_html(macro={'ok': False}, write=False)
        self.assertNotIn('<script>unsafe</script>', html)
        self.assertIn('&lt;script&gt;unsafe&lt;/script&gt;', html)


class AutomaticGrowthDraft(unittest.TestCase):
    def test_revenue_decline_does_not_apply_a_cashflow_penalty(self):
        financials = dict(fcf=8e6, shares=1e6, rev=100e6, rev_prev=125e6,
                          opinc=20e6, ebitda=25e6, netdebt=0, div_yield=0,
                          price=200, cur='USD', sector='Technology', name='Test',
                          lo=100, hi=300, shares_prev=1e6)
        with patch.object(autoscore.yf, 'Ticker', return_value=object()), \
             patch.object(autoscore, '_fin', return_value=copy.deepcopy(financials)):
            row, _ = autoscore.auto_row('TEST')
        self.assertEqual(row['deliver'], -20)
        self.assertEqual(row['pr'], 5.5)
        self.assertEqual(row.get('deliver_basis'), 'REVENUE_PROXY')
        self.assertEqual(row['normalization_status'], 'REVIEW_REQUIRED')
        self.assertIsNone(engine.cushion(dict(row, price=200)))


REMOVED_TYPING = {'GOOG': dict(deliver_basis='REVENUE_PROXY')}


class FrozenGrowthReplay(unittest.TestCase):
    def test_76_saved_inputs_isolate_penalties_from_valuation_and_raw_fit(self):
        path = Path(__file__).parent / 'history/_builds' / (
            '20261014T014342186957-2301140aa7724db7bc270bf7ffc3690c/observation.json')
        record = json.loads(path.read_text(encoding='utf-8'))
        rows = copy.deepcopy(record['_evidence']['inputs'])
        for ticker, row in rows.items():
            # Only metric typing changes. Prices, WACC, cash flows, shares,
            # components and positions remain the archived controlled inputs.
            # GOOG left the universe on 2026-10-31 (duplicate of GOOGL); its
            # archived row keeps the metric typing it had when removed.
            current = engine.DATA.get(ticker) or REMOVED_TYPING[ticker]
            row['deliver_basis'] = current.get('deliver_basis')
        deltas = {'LULU': .3, 'PFE': .3, 'TSLA': .075}
        verdicts = {'LULU': 'ACCUMULATE', 'PFE': 'HOLD', 'TSLA': 'AVOID'}
        with patch.object(engine, 'DATA', rows):
            for ticker, row in rows.items():
                saved = record[ticker]
                with self.subTest(ticker=ticker):
                    self.assertEqual(engine.ngv(row), saved['ngv'])
                    self.assertEqual(engine.cover(row), saved['cover'])
                    self.assertEqual(engine.regime_scores(row), saved['regime'])
                    if saved['score'] is None:
                        self.assertIsNone(engine.score(row))
                        self.assertIsNone(engine.risk(row))
                    else:
                        self.assertAlmostEqual(engine.score(row), saved['score'] + deltas.get(ticker, 0))
                        self.assertAlmostEqual(engine.risk(row), saved['risk'] - (.6 if ticker in deltas else 0))
                    self.assertEqual(engine.legacy_verdict(ticker, row)[0], verdicts.get(ticker, saved['verdict']))
            for regime in engine.REGIMES:
                expected = sorted((t for t in rows if record[t]['regime']),
                                  key=lambda t: (-record[t]['regime'][regime], t))[:30]
                self.assertEqual([t for t, _, _ in engine.regime_book(regime)], expected)
                self.assertEqual(len(expected), 30)


if __name__ == '__main__':
    unittest.main()
