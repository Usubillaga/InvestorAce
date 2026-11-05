"""Known monetary input defects must not survive as automatic purchase signals."""
import copy
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import i18n
import live_analysis
import opportunity_view
import source_review
from test_framework_contract import engine


ASOF = datetime(2026, 11, 5, tzinfo=timezone.utc)
FIXTURE = Path(__file__).parent / 'tests/fixtures/oxy-inputs-20261104.json'
CONFLICT = dict(code='COMMON_EQUITY_CLAIMS_OMITTED', detected_at='2026-11-02',
                reason='Preferred claims are absent from the common-equity cash flow.')


class ValuationInputConflicts(unittest.TestCase):
    def setUp(self):
        self.facts = json.loads(FIXTURE.read_text())
        self.facts['midcycle'] = True
        self.row = copy.deepcopy(engine.DATA['OXY'])
        self.row.update(price=57.33, quote_observed_at='2026-11-04T21:00:02+00:00')

    def refresh(self, fresh=False):
        with tempfile.TemporaryDirectory() as tmp, patch.object(engine, 'DATA', {'OXY': self.row}), \
             patch.object(engine.WACC, 'resolve_risk_free', return_value=4.894), \
             patch.object(engine.WACC, 'MARKET_RISK_PREMIUM', 4.72):
            path = Path(tmp) / 'facts.json'
            path.write_text(json.dumps(dict(schema=live_analysis.VERSION, entries={'OXY': self.facts})))
            def offline(_):
                raise RuntimeError('offline')
            if fresh:
                with patch.object(live_analysis, 'extract', return_value=copy.deepcopy(self.facts)):
                    engine.refresh_dynamic_analysis(cache_path=path, as_of=ASOF,
                                                    ticker_factory=lambda _: object())
            else:
                engine.refresh_dynamic_analysis(cache_path=path, as_of=ASOF, ticker_factory=offline)
            return json.loads(path.read_text())['entries']['OXY']

    def test_known_oxy_input_faults_block_fresh_and_cached_purchase_values(self):
        for fresh in (False, True):
            with self.subTest(fresh=fresh):
                cached = self.refresh(fresh)
                analysis = self.row['dynamic_analysis']
                self.assertIsNone(analysis['valuation']['ngv_per_share'])
                self.assertIsNone(analysis['valuation']['dcf_per_share'])
                self.assertIsNone(analysis['valuation']['reverse_dcf_growth_pct'])
                self.assertIsNone(analysis['metrics']['valuation_pe'])
                self.assertIsNone(analysis['model_score'])
                self.assertEqual(analysis['inputs']['fcf'], 4793000000.)
                self.assertEqual(analysis['components']['p'], 7.5)
                self.assertNotIn('valuation_input_conflicts', cached)
                result = engine.opportunity(self.row, regime='INFLATION', as_of=ASOF)
                self.assertIsNone(result['label'])
                self.assertIsNone(result['score'])
                self.assertIsNotNone(result['quality_score'])
                self.assertEqual(len(result['regime_fit_bounds']), 5)
                self.assertIsNone(result['price_thresholds']['buy'])
                self.assertIsNone(result['price_thresholds']['basis'])
                self.assertIn('Valuation blocked', opportunity_view.signal(result))
                self.assertIn('OxyChem', opportunity_view.detail('OXY', result))
                self.assertIsNone(engine.score(self.row))

    def test_calculator_cannot_ignore_explicit_input_conflicts(self):
        self.facts['valuation_input_conflicts'] = [CONFLICT]
        result = live_analysis.calculate(self.facts, risk_free=.04894, mrp=.0472, as_of=ASOF)
        self.assertIsNone(result['inputs']['valuation_fcf'])
        self.assertEqual(result['inputs']['rejected_valuation_fcf'], 7051500000.)
        self.assertIsNone(result['valuation']['ngv_per_share'])
        self.assertEqual(result['valuation_input_conflicts'], [CONFLICT])

    def test_pending_review_alone_does_not_remove_a_supported_automatic_label(self):
        result = live_analysis.calculate(self.facts, risk_free=.04894, mrp=.0472, as_of=ASOF)
        self.row.update(result['overlay'], dynamic_analysis=result)
        automatic = engine.opportunity(self.row, regime='INFLATION', as_of=ASOF)
        self.assertEqual(result['review_status'], 'REVIEW_REQUIRED')
        self.assertEqual(automatic['label'], 'Buy')
        self.assertAlmostEqual(result['valuation']['ngv_per_share'], 91.30285, places=5)

    def test_conflict_cannot_be_bypassed_by_a_previously_computed_packet(self):
        result = live_analysis.calculate(self.facts, risk_free=.04894, mrp=.0472, as_of=ASOF)
        result['valuation_input_conflicts'] = [CONFLICT]
        self.row.update(result['overlay'], dynamic_analysis=result)
        automatic = engine.opportunity(self.row, regime='INFLATION', as_of=ASOF)
        self.assertIsNone(automatic['label'])
        self.assertIsNone(automatic['score_lower'])
        self.assertIsNone(automatic['metrics']['valuation_pe'])
        self.assertIsNone(automatic['implied_growth_pct'])
        self.assertIsNone(automatic['price_thresholds']['buy'])

    def test_bad_conflict_records_cannot_silently_allow_publication(self):
        original = source_review.load()
        for value in ('not a list', [{}], [dict(CONFLICT, reason='')],
                      [dict(CONFLICT, detected_at='2035-01-01')]):
            with self.subTest(value=value):
                doc = copy.deepcopy(original)
                doc['entries']['OXY']['valuation']['input_conflicts'] = value
                with self.assertRaises(ValueError):
                    source_review.load(json.dumps(doc))

    def test_future_review_cannot_change_an_earlier_asof_calculation(self):
        section = dict(input_conflicts=[CONFLICT])
        self.assertTrue(callable(getattr(source_review, 'valuation_input_conflicts', None)))
        self.assertEqual(source_review.valuation_input_conflicts(
            section, as_of=datetime(2026, 11, 1, tzinfo=timezone.utc)), [])
        self.assertEqual(source_review.valuation_input_conflicts(section, as_of=ASOF), [CONFLICT])


class ConflictDisplayLanguages(unittest.TestCase):
    def test_reasons_stay_source_text_and_codes_are_known(self):
        facts = json.loads(FIXTURE.read_text())
        facts.update(midcycle=True, valuation_input_conflicts=source_review.valuation_input_conflicts(
            source_review.load()['entries']['OXY']['valuation'], as_of=ASOF))
        analysis = live_analysis.calculate(facts, quote=dict(price=57.33, observed_at='2026-11-04T21:00:02+00:00'),
                                           risk_free=.04894, mrp=.0472, as_of=ASOF)
        row = copy.deepcopy(engine.DATA['OXY'])
        row.update(analysis['overlay'], dynamic_analysis=analysis, price=57.33,
                   quote_observed_at='2026-11-04T21:00:02+00:00')
        result = engine.opportunity(row, regime='INFLATION', as_of=ASOF)
        page = ('<html><body>' + opportunity_view.signal(result) + opportunity_view.detail('OXY', result)
                + '</body></html>')
        self.assertEqual(result['cash_flow_policy'], 'BLOCKED_INPUT_CONFLICT')
        self.assertEqual(i18n.translation_gaps(page), [])
        german = i18n.localize(page, 'de')
        self.assertIn('Bewertung blockiert', german)
        self.assertIn('OxyChem was sold on 2026-01-02', german)      # review text keeps its original language
        self.assertIn('source-original', german)
