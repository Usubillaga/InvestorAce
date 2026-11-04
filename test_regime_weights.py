"""The macro fit is continuous in the macro inputs; the labour signal is neutral when flat."""
import copy
import html
import json
import re
import statistics
import unittest
from pathlib import Path

import i18n
import macro
import opportunity
import opportunity_view
from engine import regime_input_line
from test_opportunity import ASOF, row, spec


# Official data as of the 2026-11-04 build (FRED, data month 2026-09).
SIGNALS = dict(cpi_yoy=3.72, cpi_yoy_3m_change=0.25, unemployment_gap=0.0, unemployment_12m_change=-0.2,
               payrolls_3m_avg_thousands=50.7)
# Single-close market impulses read by consecutive builds 31 Oct - 4 Nov 2026.
RECORDED_SPOT = [(7.1, 7.4), (8.5, 4.4), (9.0, 0.2), (8.0, 0.4), (6.0, 3.4), (5.3, 2.6)]
# engine.REGIME_GOLDEN NVDA fits (frozen v15.1 formula).
NVDA = {'GOLDILOCKS': 88.9, 'REFLATION': 63.5, 'INFLATION': 13.3, 'STAGFLATION': 12.4, 'RECESSION': 29.8}


class RegimeWeightTests(unittest.TestCase):
    def test_weights_are_a_partition_that_is_sharp_far_from_boundaries(self):
        for gs, is_ in [(0.47, 0.59), (-0.3, 0.2), (0.0, 0.5), (0.9, -0.9)]:
            w = macro.regime_weights(gs, is_)
            self.assertAlmostEqual(sum(w.values()), 1.0, places=12)
            self.assertTrue(all(v >= 0 for v in w.values()))
        self.assertGreater(macro.regime_weights(0.9, 1.0)['INFLATION'], 0.9)
        self.assertGreater(macro.regime_weights(-0.9, -0.9)['RECESSION'], 0.9)
        edge = macro.regime_weights(0.9, 0.5)
        self.assertAlmostEqual(edge['INFLATION'], edge['REFLATION'] + edge['GOLDILOCKS'], places=6)

    def test_a_small_move_changes_weights_a_little(self):
        a, b = macro.regime_weights(0.40, 0.49), macro.regime_weights(0.40, 0.51)
        self.assertLess(max(abs(a[k] - b[k]) for k in a), 0.03)

    def test_recorded_noise_moves_the_weighted_fit_not_a_cliff(self):
        hard, weighted = [], []
        for g, i in RECORDED_SPOT:
            reading = macro.classify(g, i, SIGNALS)
            hard.append(NVDA[reading['regime']])
            weighted.append(sum(w * NVDA[r] for r, w in reading['weights'].items()))
        self.assertGreater(max(hard) - min(hard), 50)
        self.assertLess(max(weighted) - min(weighted), 10)

    def test_step_constants_reproduce_from_the_archived_history(self):
        fixture = json.loads(Path(__file__).with_name('tests').joinpath(
            'fixtures', 'regime_monthly_scores.json').read_text())
        rows = fixture['rows']
        self.assertEqual(len(rows), 17)
        for key, field in (('growth', 'growth_score'), ('inflation', 'inflation_score')):
            changes = [b[field] - a[field] for a, b in zip(rows, rows[1:])]
            self.assertEqual(round(statistics.stdev(changes), 2), macro.REGIME_SCORE_STEP[key])
        flips = sum(a['regime'] != b['regime'] for a, b in zip(rows, rows[1:]))
        self.assertEqual(flips, 10)

    def test_classify_reports_weights_and_market_only_is_single(self):
        reading = macro.classify(9.86, 9.29, SIGNALS)
        self.assertEqual(reading['regime'], 'INFLATION')
        self.assertAlmostEqual(reading['weights']['INFLATION'], 0.59, places=2)
        self.assertAlmostEqual(reading['weights']['REFLATION'], 0.34, places=2)
        self.assertEqual(macro.classify(3, 10, {})['weights'], {'REFLATION': 1.0})


class LabourSignalTests(unittest.TestCase):
    def test_flat_unemployment_is_neutral_not_maximum_growth(self):
        self.assertEqual(macro.labour_signal(0.0, 0.0), 0.0)
        self.assertEqual(macro.labour_signal(0.0, None), 0.0)
        self.assertAlmostEqual(macro.labour_signal(0.0, -0.2), 0.4)
        self.assertEqual(macro.labour_signal(-0.1, -0.5), 1.0)

    def test_a_rise_from_the_low_still_pulls_growth_down(self):
        self.assertEqual(macro.labour_signal(0.5, 0.5), -1.0)
        self.assertAlmostEqual(macro.labour_signal(0.5, -0.1), -2 / 3)

    def test_breakeven_payrolls_are_neutral(self):
        reading = macro.classify(0., 0., dict(payrolls_3m_avg_thousands=macro.PAYROLL_BREAKEVEN_THOUSANDS,
                                              cpi_yoy=2.5))
        self.assertEqual(reading['components']['growth']['payrolls'], 0.0)

    def test_signals_carry_the_twelve_month_change(self):
        months = [f'{y}-{m:02d}-01' for y in (2025, 2026) for m in range(1, 13)][:21]
        values = [4.4] * 9 + [4.3] * 3 + [4.2] * 9
        signals = macro.economic_signals({'unemployment': [dict(date=d, value=v) for d, v in zip(months, values)]})
        self.assertEqual(signals['unemployment_12m_change'], -0.2)


class WeightedOpportunityTests(unittest.TestCase):
    def assess(self, weights=None, regime='INFLATION', value=None):
        return opportunity.assess(copy.deepcopy(value or row()), regime=regime, spec=spec(), as_of=ASOF,
                                  weights=weights)

    def test_macro_component_uses_the_weighted_fit(self):
        weights = dict(INFLATION=0.59, REFLATION=0.34, GOLDILOCKS=0.04, STAGFLATION=0.02, RECESSION=0.002)
        result = self.assess(weights)
        bounds = result['regime_fit_bounds']
        mix = result['regime_weights']
        self.assertNotIn('RECESSION', mix)                       # below 0.5%, dropped and renormalized
        self.assertAlmostEqual(sum(mix.values()), 1.0, places=3)
        expected = round(sum(w * bounds[r][0] for r, w in mix.items()), 1)
        self.assertAlmostEqual(result['current_fit'], expected, places=6)
        macro_component = next(c for c in result['components'] if c['key'] == 'macro')
        self.assertAlmostEqual(macro_component['value'], expected / 10)
        self.assertEqual(result['macro_basis'], 'REGIME_WEIGHTED')

    def test_without_weights_the_single_regime_is_scored(self):
        result = self.assess(None, regime='REFLATION')
        self.assertEqual(result['regime_weights'], {'REFLATION': 1.0})
        self.assertEqual(result['current_fit'], result['regime_fit']['REFLATION'])
        self.assertEqual(result['macro_basis'], 'SINGLE_REGIME')

    def test_unknown_balance_keeps_the_weighted_fit_bounded(self):
        value = row(); dynamic = value['dynamic_analysis']
        dynamic['components']['b'] = None; dynamic['inputs']['cash'] = None
        result = self.assess(dict(INFLATION=0.6, REFLATION=0.4), value=value)
        low, high = result['current_fit_bounds']
        self.assertLess(low, high)
        self.assertIsNone(result['current_fit'])

    def test_display_names_the_weighted_regimes(self):
        result = self.assess(dict(INFLATION=0.59, REFLATION=0.34, GOLDILOCKS=0.04, STAGFLATION=0.03))
        self.assertIn('INFLATION 59% · REFLATION 34%', opportunity_view.fit(result))
        self.assertNotIn('GOLDILOCKS', opportunity_view.fit(result))
        self.assertIn('<th>Weight</th>', opportunity_view.detail('WKL', result))

    def test_regime_weight_line_is_fully_translated(self):
        line = regime_input_line(dict(regime_input=dict(basis='MEAN_OF_SESSIONS', growth=9.86, inflation=9.29,
            sessions=21, start='2026-10-05', end='2026-11-03'), regime_margin=0.09,
            regime_weights=dict(INFLATION=0.59, REFLATION=0.34, GOLDILOCKS=0.04, STAGFLATION=0.02)))
        self.assertIn('INFLATION 59%', line)
        for language in ('de', 'es'):
            _, missing = i18n._translate(html.unescape(line.replace('<br>', ' ')), language)
            self.assertEqual(missing, '', language)
            for node in re.split(r'<[^>]+>', opportunity_view.guide('INFLATION')):
                _, missing = i18n._translate(html.unescape(node), language)
                self.assertEqual(missing, '', (language, node))


if __name__ == '__main__':
    unittest.main()
