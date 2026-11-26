"""Reconcile Oracle's issuer statements and the dated v18 scoreboard."""
import copy
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import engine


class OracleScoreboard(unittest.TestCase):
    def test_primary_cash_and_score_without_provider(self):
        row = copy.deepcopy(engine.DATA['ORCL'])
        cutoff = datetime(2026, 11, 25, 23, 30, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as tmp, patch.dict(engine.DATA, {'ORCL': row}, clear=True), \
                patch.object(engine.LIVE_ANALYSIS, 'extract', return_value=None), \
                patch.object(engine.WACC, 'resolve_risk_free', return_value=4.8):
            engine.refresh_dynamic_analysis(Path(tmp) / 'cache.json', as_of=cutoff,
                                            ticker_factory=lambda _: object())
        inputs = row['dynamic_analysis']['inputs']
        self.assertEqual(inputs['fcf'], -28720e6)
        self.assertEqual(inputs['common_fcf'], -28864e6)
        self.assertEqual(inputs['valuation_fcf'], -33678e6)
        self.assertEqual(inputs['valuation_net_income'], 18736e6)
        score = engine.opportunity(row, regime='REFLATION', as_of=cutoff)
        self.assertAlmostEqual(score['score_lower'], 4.21576376)
        self.assertEqual(score['score_upper'], 5.49)
        self.assertIsNone(score['label'])
        self.assertIsNone(score['score'])
        self.assertTrue(Path(row['deep_dive']).is_file())
