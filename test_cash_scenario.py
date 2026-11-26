"""Dated issuer cash scenarios are shown next to the label and never change it (no network)."""
import copy
import json
import unittest
from datetime import datetime
from pathlib import Path

import engine
import opportunity_view

ROOT = Path(__file__).parent
RUN = ROOT / 'history/runs/20261126T141158074008-604fa6ca480a41728cccc682440eb1f6.json'


class FirstSolarCredits(unittest.TestCase):
    def setUp(self):
        record = json.loads(RUN.read_text())
        self.row = copy.deepcopy(record['_evidence']['inputs']['FSLR'])
        self.row['cash_scenario'] = engine.DATA['FSLR']['cash_scenario']
        macro = record['_evidence']['macro']
        self.context = dict(regime=macro.get('regime'), weights=macro.get('regime_weights'),
                            as_of=datetime.fromisoformat(record['_evidence']['captured_at']))

    def test_scenario_beside_an_unchanged_label(self):
        plain = copy.deepcopy(self.row)
        plain.pop('cash_scenario')
        base = engine.opportunity(plain, **self.context)
        result = engine.opportunity(self.row, **self.context)
        self.assertEqual((result['label'], result['score']), (base['label'], base['score']))
        s = result['cash_scenario']
        self.assertAlmostEqual(s['add'], 894.532 * 668.2 / 699.7, delta=0.1)
        added = self.row['dynamic_analysis']['inputs']['valuation_fcf'] + s['add'] * 1e6
        cap = self.row['dynamic_analysis']['metrics']['market_cap']
        self.assertAlmostEqual(s['fcf_yield_pct'], 100 * added / cap, places=6)
        self.assertGreater(s['score'], result['score'])
        self.assertIn('Scenario, not the label', opportunity_view.decision_context(result))

    def test_another_window_is_not_rolled_forward(self):
        self.row['dynamic_analysis']['financial_period'] = '2026-12-31'
        self.assertNotIn('cash_scenario', engine.opportunity(self.row, **self.context))


if __name__ == '__main__':
    unittest.main()
