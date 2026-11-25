"""Metadata-only payment checks; controlled inputs, no provider calls."""
import copy
import json
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
import engine as e
import evidence
import source_review
ROOT=Path(__file__).parent
PACKET=ROOT/'docs/analysis/issuer-events-20261124/packet.json'
SELECTED=('BBW','BKNG','CAE','CAT','CEG')
class PaymentMonitoring(unittest.TestCase):
    def test_scope_payments_and_periods(self):
        p=json.loads(PACKET.read_text())['issuers']
        self.assertEqual(set(p),set(SELECTED))
        for t in SELECTED:
            self.assertIsNone((p[t]['next_common_payment'] or {}).get('actual_payment_date'))
            self.assertIsNone(p[t]['last_complete_check'])
        self.assertEqual(p['CAT']['next_common_payment']['status'],'PAYABLE_PASSED_ACTUAL_NOT_VERIFIED')
        self.assertEqual(p['BBW']['next_earnings']['event_date'],'2026-12-03')
        b=p['BKNG']['payments']
        self.assertEqual(b['ocf']-b['cash_capex'],b['reported_fcf_derived'])
        c=p['CAE']['payments']
        self.assertAlmostEqual(sum(c['fcf_components']),c['management_fcf'])
        self.assertAlmostEqual(c['ocf']-c['total_capex'],c['ocf_minus_total_capex_derived'])
        self.assertNotAlmostEqual(c['management_fcf'],c['ocf_minus_total_capex_derived'])
    def test_bad_payment_register_does_not_load(self):
        r=source_review.load()
        r['entries']['BBW']['monitoring']['next_common_payment']['actual_payment_date']='2027-01-07'
        with self.assertRaises(ValueError):
            source_review.load(json.dumps(r))
    def test_all_frozen_outputs_and_generation_match(self):
        new=source_review.load()
        old=copy.deepcopy(new)
        for t in SELECTED:
            del old['entries'][t]
        build=evidence.current_build(ROOT/'history')
        rows=copy.deepcopy(build['record']['_evidence']['inputs'])
        self.assertLessEqual(set(rows),set(e.DATA))
        self.assertLessEqual(set(e.DATA)-set(rows),{'VIS'})   # added 25 Nov, not yet in the latest build
        macro=copy.deepcopy(build['record']['_evidence']['macro'])
        at=datetime.fromisoformat(build['record']['_evidence']['captured_at'])
        def capture(register):
            with patch.object(e.SOURCE_REVIEW,'load',return_value=register):
                return dict(rows={t:(e.score(d),e.ngv(d),e.implied_growth(d),e.cover(d),e.cushion(d),e.risk(d),e.verdict(t,d),e.regime_scores(d)) for t,d in rows.items()},
                    opportunity={t:e.opportunity(d,regime=macro.get('regime'),weights=macro.get('regime_weights'),as_of=at) for t,d in rows.items()},
                    books=[e.regime_book(x) for x in e.REGIMES],
                    screens=[e.screen(x,regime=e.REGIMES[0] if x=='regime' else None,reviewed_only=False) for x in ('quality','regime','duration')],
                    proposals=[e.portfolio_proposal(x) for x in e.REGIMES])
        with patch.object(e,'DATA',rows):
            self.assertEqual(capture(old),capture(new))
            bundle=evidence.model_bundle(ROOT)
            record=e.observation(macro,bundle,'2026-11-24T07:00:00+00:00')
            self.assertEqual(record['_source_reviews'],new)
            self.assertEqual(json.loads(bundle['sources']['source_reviews.json']),new)
            with patch.object(e,'sector_performance',return_value={}),patch.object(e,'forward_run',return_value={'ok':False}):
                html=e.build_html(macro=macro,write=False,reviews=record['_source_reviews'])
            for t in SELECTED:
                self.assertIn(new['entries'][t]['monitoring']['summary'],html)
            self.assertEqual(e.regime_regression_errors(),[])
