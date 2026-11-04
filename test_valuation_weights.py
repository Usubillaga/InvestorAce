"""v18 weights: free cash flow / price is counted once; quality and valuation both matter."""
import copy
import json
import re
import statistics
import unittest
from html import unescape
from pathlib import Path

import i18n
import opportunity
import opportunity_view
from test_opportunity import ASOF, row, spec


COMPONENTS = json.loads(Path(__file__).with_name('tests').joinpath(
    'fixtures', 'opportunity_components_2026-11-04.json').read_text())['rows']
V17 = dict(p=.12, c=.105, b=.075, fcfy=.15, pe=.10, expectations=.15, g=.10, r=.03, d=.02, macro=.15)
BLOCKS = dict(quality=('p', 'c', 'b'), cash=('fcfy', 'expectations'), pe=('pe',))


def variance_shares(weights):
    """Euler decomposition: each block's covariance with the score over the score's variance."""
    data = list(COMPONENTS.values())
    score = [sum(weights[k] * row[k] for k in weights) for row in data]

    def cov(a, b):
        ma, mb = statistics.mean(a), statistics.mean(b)
        return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / len(a)
    total = cov(score, score)
    return {name: cov([sum(weights[k] * row[k] for k in keys) for row in data], score) / total
            for name, keys in BLOCKS.items()}


class WeightTests(unittest.TestCase):
    def test_weights_and_blocks(self):
        w = opportunity.WEIGHTS
        self.assertAlmostEqual(sum(w.values()), 1.0, places=12)
        self.assertAlmostEqual(sum(w[k] for k in opportunity.QUALITY), .45, places=12)
        self.assertAlmostEqual(sum(w[k] for k in opportunity.VALUATION), .25, places=12)
        self.assertEqual(w['fcfy'], w['expectations'])
        self.assertAlmostEqual(w['fcfy'] + w['expectations'], .15, places=12)
        self.assertEqual((w['macro'], w['g'], w['r'] + w['d']), (.15, .10, .05))
        self.assertEqual(opportunity.VERSION, 'opportunity-v18.1')

    def test_the_two_cash_measures_are_one_signal(self):
        fcfy = [row['fcfy'] for row in COMPONENTS.values()]
        expectations = [row['expectations'] for row in COMPONENTS.values()]
        self.assertGreater(statistics.correlation(fcfy, expectations), .85)

    def test_cash_valuation_no_longer_dominates_the_score(self):
        old, new = variance_shares(V17), variance_shares(opportunity.WEIGHTS)
        self.assertGreater(old['cash'], .55)             # v17: FCF / price drove the ranking
        self.assertLess(old['quality'], .15)
        self.assertLess(new['cash'], .35)
        self.assertGreater(new['quality'], .35)
        self.assertGreater(new['cash'] + new['pe'], new['quality'])   # valuation still leads


class GateTests(unittest.TestCase):
    def test_block_scores_use_the_v18_block_weights(self):
        result = opportunity.assess(copy.deepcopy(row()), regime='REFLATION', spec=spec(), as_of=ASOF)
        c = {x['key']: x['value'] for x in result['components']}
        w = opportunity.WEIGHTS
        self.assertAlmostEqual(result['quality_score'], (w['p'] * c['p'] + w['c'] * c['c'] + w['b'] * c['b']) / .45)
        self.assertAlmostEqual(result['valuation_score'],
            (w['fcfy'] * c['fcfy'] + w['pe'] * c['pe'] + w['expectations'] * c['expectations']) / .25)
        self.assertEqual(result['label'], 'Buy')

    def test_guide_states_the_weights_in_all_languages(self):
        guide = opportunity_view.guide('INFLATION')
        self.assertIn('Financial quality 45%', guide)
        for node in re.split(r'<[^>]+>', guide):
            for language in ('de', 'es'):
                _, missing = i18n._translate(unescape(node), language)
                self.assertEqual(missing, '', (language, node))


if __name__ == '__main__':
    unittest.main()
