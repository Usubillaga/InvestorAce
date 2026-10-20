"""Economic and publication boundaries of the dated Enagas scenario review."""
import copy
import importlib
import importlib.util
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path


class EnagasValuationTests(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('enagas_valuation'),
                             'The Enagas DCF/reverse-DCF model is not implemented')
        return importlib.import_module('enagas_valuation')

    def test_zero_growth_equity_perpetuity_does_not_subtract_debt_again(self):
        result = self.module().dcf(100, 0, .10, 0, 10)
        self.assertAlmostEqual(result['per_share'], 100, places=9)
        self.assertAlmostEqual(result['equity_value'], 1000, places=9)

    def test_pending_acquisition_and_extra_funding_are_deducted_once(self):
        result = self.module().dcf(100, 0, .10, 0, 10,
                                   one_off_cost=31, extra_cash_call=10)
        # Perpetuity100, immediate31/10 and a five-year annuity10/10.
        self.assertAlmostEqual(result['per_share'], 93.10921323059155, places=9)

    def test_reverse_dcf_solves_explicit_cash_flow_growth(self):
        module = self.module()
        self.assertAlmostEqual(module.reverse_growth(100, 100, .10, 0, 10), 0, places=9)
        # Independently calculated five-year DCF: C0=300,g=.04,Ke=.08,gT=.01.
        solved = module.reverse_growth(18.68216111745972, 300, .08, .01, 261.990074,
                                       one_off_cost=31)
        self.assertAlmostEqual(solved, .04, places=8)

    def test_invalid_perpetuities_and_nonfinite_cash_flows_fail(self):
        module = self.module()
        for args in [(100, 0, .05, .05, 10), (100, 0, .04, .05, 10),
                     (100, 0, .10, 0, 0), (float('nan'), 0, .10, 0, 10),
                     (100, -1, .10, 0, 10), (True, 0, .10, 0, 10)]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                module.dcf(*args)

    def test_cash_bridge_and_scenarios_do_not_become_verified_ngv(self):
        module = self.module()
        model = module.build_model(module.load(), now=datetime.fromisoformat('2026-10-20T20:20:00+02:00'))
        self.assertAlmostEqual(model['ttm_ffo'], 612)
        self.assertAlmostEqual(model['ttm_working_capital_outflow'], 241.1)
        self.assertAlmostEqual(model['transaction_adjusted_9m_cash'], 183.8)
        self.assertAlmostEqual(model['cases']['base']['starting_cash'], 300)
        self.assertAlmostEqual(model['cases']['base']['per_share'], 16.403565841091474, places=8)
        self.assertAlmostEqual(model['reverse_growth'], .021531461443651145, places=9)
        for key in ('ngv', 'cover', 'cushion', 'fundamental_score', 'approved_rating'):
            self.assertIsNone(model[key], key)
        self.assertEqual(model['scenario_rating'], 'HOLD NEG')

    def test_stale_or_future_quote_withdraws_current_stance(self):
        module = self.module()
        for now in ('2026-10-22T18:20:00+02:00', '2026-10-20T16:00:00+02:00'):
            model = module.build_model(module.load(), now=datetime.fromisoformat(now))
            self.assertIsNone(model['scenario_rating'])
            self.assertFalse(model['quote_fresh'])
            self.assertEqual(model['historical_scenario_rating'], 'HOLD NEG')

    def test_model_inputs_are_archived_with_executable_source(self):
        import evidence
        bundle = evidence.model_bundle(Path(__file__).parent)
        self.assertIn('enagas_review.json', bundle['sources'])

    def test_pages_are_multilingual_and_do_not_mutate_engine(self):
        module = self.module()
        import engine
        before = copy.deepcopy(engine.DATA)
        pages = dict(module.site_pages(Path(__file__).parent,
                        now=datetime.fromisoformat('2026-10-20T20:20:00+02:00')))
        self.assertEqual(engine.DATA, before)
        for language, filename in [('de', 'enagas.de.html'), ('en', 'enagas.html'),
                                   ('es', 'enagas.es.html')]:
            html = pages[Path(filename)]
            self.assertIn(f'<html lang="{language}">', html)
            self.assertIn('17.25', html)
            self.assertIn('enagas-review.json', html)
        payload = json.loads(pages[Path('enagas-review.json')])
        self.assertIsNone(payload['approved_rating'])
        with tempfile.TemporaryDirectory() as temp:
            self.assertEqual(module.site_pages(Path(temp)), [])

    def test_inputs_reject_a_claimed_approved_rating(self):
        module = self.module()
        doc = module.load()
        doc['review']['approved_rating'] = 'BUY'
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'inputs.json'
            path.write_text(json.dumps(doc))
            with self.assertRaises(ValueError):
                module.load(path)

    def test_publication_build_includes_the_review_and_navigation(self):
        import weekly_research
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'public'
            weekly_research.build_site(Path(__file__).parent, output)
            self.assertTrue((output / 'enagas.de.html').exists())
            self.assertTrue((output / 'enagas-review.json').exists())
            self.assertIn('enagas.html', (output / 'index.html').read_text())


if __name__ == '__main__':
    unittest.main()
