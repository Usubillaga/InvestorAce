import copy
import io
import json
import random
import unittest
from contextlib import redirect_stderr
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch

import decision_view
import evidence
import timing
from test_framework_contract import engine
from test_timing import AS_OF, history, price_history


def row(**changes):
    item = engine._regime_fixture('Pharma', .7, 7, 8)
    item.update(yf='TEST', cur='USD', held=False, dil=8)
    item.update(changes)
    return item


def explanations(rows):
    return {t: {'score': engine.score_components(d), 'regimes': engine.regime_fit_components(d),
                'ngv': engine.ngv(d), 'cover': engine.cover(d),
                'implied_growth': engine.implied_growth(d), 'cushion': engine.cushion(d)}
            for t, d in rows.items()}


class ScoreExplanation(unittest.TestCase):
    def test_all_eight_categories_reconcile_to_existing_score(self):
        data = row()
        result = engine.score_components(data)
        self.assertEqual(result['status'], 'DECOMPOSED')
        self.assertEqual([c['key'] for c in result['components']], list(engine.W))
        self.assertAlmostEqual(sum(c['contribution'] for c in result['components']), engine.score(data))
        self.assertEqual(result['total'], engine.score(data))
        self.assertTrue(result['reconciles'])
        self.assertEqual(next(c for c in result['components'] if c['key'] == 'pr')['value'],
                         engine.priced_in_live(data))

    def test_missing_priced_in_score_exposes_existing_renormalisation(self):
        data = row(price=None, pr=None)
        result = engine.score_components(data)
        self.assertAlmostEqual(result['denominator'], .85)
        self.assertTrue(result['reconciles'])
        self.assertAlmostEqual(sum(c['effective_weight'] for c in result['components']), 1)
        self.assertAlmostEqual(sum(c['contribution'] for c in result['components']), engine.score(data))
        priced = next(c for c in result['components'] if c['key'] == 'pr')
        self.assertIsNone(priced['value'])
        self.assertEqual(priced['effective_weight'], 0)
        self.assertEqual(priced['contribution'], 0)

    def test_published_total_never_invents_subscores(self):
        result = engine.score_components(row(sub=None, score_fixed=7.88))
        self.assertEqual(result['status'], 'PUBLISHED_TOTAL')
        self.assertEqual(result['total'], 7.88)
        self.assertEqual(result['components'], [])
        self.assertIsNone(result['reconciles'])
        self.assertEqual(engine.score_components(row(sub=None))['status'], 'UNAVAILABLE')

    def test_random_complete_and_missing_pr_cases_reconcile(self):
        rng = random.Random(20261015)
        for i in range(300):
            data = row(sub=tuple(rng.uniform(0, 10) for _ in range(6)),
                       dil=rng.uniform(0, 10), price=rng.uniform(10, 300),
                       deliver_basis='CASH_FLOW', deliver=rng.uniform(-10, 30))
            if i % 3 == 0:
                data.update(price=None, pr=None)
            self.assertTrue(engine.score_components(data)['reconciles'])

    def test_observation_archives_explanations_and_sources(self):
        rows = {'TEST': row()}
        bundle = evidence.model_bundle(Path(__file__).parent)
        self.assertIn('timing.py', bundle['sources'])
        self.assertIn('decision_view.py', bundle['sources'])
        with patch.object(engine, 'DATA', rows):
            record = engine.observation({'ok': False}, bundle)
        self.assertEqual(record['TEST']['score_explanation'], engine.score_components(rows['TEST']))
        self.assertEqual(record['TEST']['regime_components'], engine.regime_fit_components(rows['TEST']))


class DecisionView(unittest.TestCase):
    def test_view_exposes_exact_components_and_timing_without_trade_language(self):
        rows = {'TEST': row(timing=timing.calculate(history(), AS_OF))}
        html = decision_view.panel(rows, explanations(rows), 'REFLATION')
        for text in ('Experimental', 'SMA 200', 'EMA 21', 'ATR 14', 'Contribution',
                     'GOLDILOCKS', 'REFLATION', 'STAGFLATION', 'No automatic trades',
                     '2026-10-14', 'Priced-In Expectations', 'Category assessment'):
            self.assertIn(text, html)
        self.assertNotIn('BUY NOW', html)
        self.assertNotIn('SELL 25%', html)



    def test_current_alert_overview_is_visible_and_only_contains_latest_events(self):
        rows = {'BUY': row(timing=timing.calculate(price_history([100.] * 219 + [120.]), AS_OF)),
                'SELL': row(timing=timing.calculate(price_history([100.] * 219 + [80.]), AS_OF)),
                'HIST': row(timing=timing.calculate(price_history([100.] * 218 + [120., 120.]), AS_OF))}
        html = decision_view.panel(rows, explanations(rows), None)
        overview = html.split('<details', 1)[0]
        self.assertIn('Current experimental BUY/SELL alerts', overview)
        self.assertIn('EXPERIMENTAL BUY · BUY · 2026-10-14', overview)
        self.assertIn('EXPERIMENTAL SELL · SELL · 2026-10-14', overview)
        self.assertNotIn('· HIST ·', overview)
        self.assertNotIn('2026-10-13', overview)
        self.assertIn('No automatic trades', overview)

    def test_no_new_signal_and_recent_historical_event_have_distinct_dated_labels(self):
        observed = timing.calculate(price_history([100.] * 218 + [120., 120.]), AS_OF)
        rows = {'TEST': row(timing=observed)}
        html = decision_view.panel(rows, explanations(rows), None)
        self.assertIn('Current signal: NO_NEW_SIGNAL · 2026-10-14', html)
        self.assertIn('Latest historical event (last 20 completed sessions): '
                      'EXPERIMENTAL BUY · 2026-10-13 · 1 completed session ago', html)
        self.assertIn('No current BUY/SELL alerts.', html.split('<details', 1)[0])

    def test_old_timing_without_signal_contract_stays_explicitly_unavailable(self):
        old = timing.calculate(history(), AS_OF)
        old['schema'] = 'observational-timing-v1'
        old.pop('signal', None)
        rows = {'TEST': row(timing=old)}
        html = decision_view.panel(rows, explanations(rows), None)
        self.assertIn('Current signal: UNAVAILABLE', html)
        self.assertIn('No signal contract archived; no signal is inferred.', html)
        self.assertNotIn('NO_NEW_SIGNAL', html)
        self.assertIn('observational-timing-v1', html)

    def test_renderer_suppresses_current_alerts_when_observation_is_not_available(self):
        for state in ('STALE', 'PARTIAL', 'UNAVAILABLE'):
            with self.subTest(state=state):
                observed = timing.calculate(price_history([100.] * 219 + [120.]), AS_OF)
                observed['status'] = state
                rows = {'TEST': row(timing=observed)}
                html = decision_view.panel(rows, explanations(rows), None)
                self.assertIn('Current signal: UNAVAILABLE', html)
                self.assertNotIn('EXPERIMENTAL BUY', html.split('<details', 1)[0])
        warmup = timing.calculate(price_history([100.] * 199 + [120.]), AS_OF)
        rows = {'TEST': row(timing=warmup)}
        html = decision_view.panel(rows, explanations(rows), None)
        self.assertIn('Current signal: UNAVAILABLE', html)
        self.assertIn('Latest historical event (last 20 completed sessions): UNAVAILABLE.', html)

    def test_signal_contract_version_and_crossing_rules_are_visible(self):
        rows = {'TEST': row(timing=timing.calculate(history(), AS_OF))}
        html = decision_view.panel(rows, explanations(rows), None)
        self.assertIn('experimental-timing-v2', html)
        self.assertIn('Signal rule contract: close-crossings-v1', html)
        self.assertIn('Signal comparisons need at least 201 valid completed bars.', html)
        self.assertIn('previous close ≤ previous EMA 21', html)
        self.assertIn('previous close ≥ previous SMA 200', html)

    def test_missing_timing_and_published_total_remain_explicit(self):
        rows = {'TEST': row(sub=None, score_fixed=7.88)}
        html = decision_view.panel(rows, explanations(rows), None)
        self.assertIn('Published total only', html)
        self.assertIn('Category breakdown unavailable', html)
        self.assertIn('UNAVAILABLE', html)
        self.assertNotIn('0.00 ATR', html)

    def test_report_exposes_the_exact_archived_diagnostic_versions(self):
        rows = {'TEST': row(timing=timing.calculate(history(), AS_OF))}
        with patch.object(engine, 'DATA', rows):
            record = engine.observation({'ok': False}, {'sources': {}, 'sha256': 'test'})
        html = decision_view.panel(rows, explanations(rows), None)
        self.assertIn(record['TEST']['timing']['schema'], html)
        self.assertIn(record['TEST']['score_explanation']['schema'], html)

    def test_external_strings_are_escaped_and_html_parses(self):
        bad = '<script>alert(1)</script>'
        observed = timing.unavailable(bad, AS_OF)
        rows = {bad: row(timing=observed, cur=bad)}
        html = decision_view.panel(rows, explanations(rows), bad)
        self.assertNotIn(bad, html)
        self.assertIn('&lt;script&gt;', html)
        HTMLParser().feed(html)

    def test_full_universe_decisions_rankings_and_portfolios_are_unchanged(self):
        rows = copy.deepcopy(engine.DATA)
        for data in rows.values():
            data['price'] = 100
        with patch.object(engine, 'DATA', rows):
            def decisions():
                return {t: [engine.score(d), engine.risk(d), engine.ngv(d), engine.cover(d),
                            engine.cushion(d), engine.verdict(t, d), engine.regime_scores(d),
                            engine.entry_price(d)] for t, d in rows.items()}
            before = decisions()
            books = [[t for t, _, _ in engine.regime_book(regime)] for regime in engine.REGIMES]
            proposals = [engine.portfolio_proposal(regime) for regime in engine.REGIMES]
            for data in rows.values():
                data['timing'] = timing.calculate(history(), AS_OF)
            frozen = copy.deepcopy(rows)
            decision_view.panel(rows, explanations(rows), 'REFLATION')
            self.assertEqual(rows, frozen)
            self.assertEqual(decisions(), before)
            self.assertEqual([[t for t, _, _ in engine.regime_book(r)] for r in engine.REGIMES], books)
            self.assertEqual([engine.portfolio_proposal(r) for r in engine.REGIMES], proposals)

    def test_full_report_includes_the_separate_view_and_preserves_order(self):
        rows = {'TEST': row(timing=timing.calculate(history(), AS_OF))}
        with patch.object(engine, 'DATA', rows), \
             patch.object(engine, 'sector_performance', return_value={'ok': False}), \
             patch.object(engine, 'forward_run', return_value={}), \
             patch.object(engine, 'regime_history', return_value=([], {})), redirect_stderr(io.StringIO()):
            html = engine.build_html(macro={'ok': False}, write=False)
        self.assertIn('id="decision-observations"', html)
        self.assertIn('Score explanations and entry observations', html)
        self.assertIn('Mom 12-1', html)
        self.assertTrue(html.endswith('</body></html>'))
        json.dumps(explanations(rows), allow_nan=False)


if __name__ == '__main__':
    unittest.main()
