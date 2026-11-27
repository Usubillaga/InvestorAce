"""The dated partial batch must preserve the authoritative numerical boundaries."""
import copy
import json
import hashlib
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import engine as e
import evidence
import source_review

ROOT = Path(__file__).parent
BASE = '194f3291951e3c617b3c292f7506327350c3ec59'
BASE_ENTRIES = ["CRM","ASML","SAN","WKL","LVMH","ENB","UNH","NFLX","NVDA","PFE","LULU","DVN","ZTS","AR","OXY","ENG","VICI","GOOGL","SMCI","PG","APP","SPGI","ISRG","PL","REP","WIX","BYRN","AWK","BABA","BNTX","GRAB","IBST","CRWV","MRNA","NBIS","OPEN","RIVN","AVGO","O","RCAT","SPCX","TEM","JEQE","VOW3","MELI","INTU","VNT","ALLE","ADT"]
BASE_PROJECTION_SHA256 = 'c8e2fbe4cb401ea2ef8a4c2df18c2cba24ca9308aac82fa5f3d818d0be68bc91'
SELECTED = ('VNT', 'ALLE', 'ADT', 'OXY', 'CRWV', 'ALC', 'ALM', 'AMD', 'ANT', 'B')


class DatedBatch(unittest.TestCase):
    def test_only_monitoring_changes_and_old_dates_survive(self):
        new = source_review.load((ROOT / 'source_reviews.json').read_text())
        # The hash covers the November 23 register envelope. Compare current
        # issuer fields against it while allowing later, independently dated calendars.
        archive = ROOT / 'history/runs/20261125T060416260690-22422c486bb94c3d9f83d74343db38c2.json'
        baseline = json.loads(archive.read_text())['_source_reviews']
        projection = {k: v for k, v in baseline.items() if k != 'entries'}
        projection['entries'] = {t: copy.deepcopy(new['entries'][t]) for t in BASE_ENTRIES}
        for ticker in BASE_ENTRIES:
            self.assertEqual(source_review.entry_dates(new['entries'][ticker], new),
                             source_review.entry_dates(baseline['entries'][ticker], baseline))
        for value in projection['entries'].values():
            value.pop('monitoring', None)
        digest = hashlib.sha256(json.dumps(projection,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        self.assertEqual(digest,BASE_PROJECTION_SHA256)
        for key in SELECTED:
            entry = new['entries'][key]
            m = next(item for item in [entry['monitoring'], *entry.get('monitoring_history', [])]
                     if item['as_of'] == '2026-11-23')
            self.assertEqual(m['as_of'], '2026-11-23')
            self.assertEqual(m['coverage'], 'PARTIAL')
            self.assertTrue(m['gap'])

    def test_fixed_all_watchlist_outputs_and_frozen_register(self):
        new = source_review.load((ROOT / 'source_reviews.json').read_text())
        # Reconstruct the identical authoritative base without requiring Git history
        # in Actions' shallow checkout; monitoring is deliberately diagnostic only.
        old = copy.deepcopy(new)
        old['entries'] = {t: old['entries'][t] for t in BASE_ENTRIES}
        for value in old['entries'].values():
            value.pop('monitoring', None)
        build = evidence.current_build(ROOT / 'history')
        rows = copy.deepcopy(build['record']['_evidence']['inputs'])
        # Tickers added after the latest build (e.g. an add-ticker draft) are not in it yet; none may vanish.
        self.assertLessEqual(set(rows), set(e.DATA))
        macro = copy.deepcopy(build['record']['_evidence']['macro'])
        def capture(register):
            with patch.object(e.SOURCE_REVIEW, 'load', return_value=register):
                return dict(rows={t:(e.score(d),e.ngv(d),e.implied_growth(d),e.cover(d),e.cushion(d),e.risk(d),e.verdict(t,d),e.regime_scores(d)) for t,d in rows.items()},
                    opportunities={t:e.opportunity(d,regime=macro.get('regime'),weights=macro.get('regime_weights'),as_of=datetime.fromisoformat('2026-11-23T08:00:00+00:00')) for t,d in rows.items()},
                    books=[e.regime_book(r) for r in e.REGIMES],
                    screens=[e.screen(p, regime=e.REGIMES[0] if p=='regime' else None, reviewed_only=False) for p in ('quality','regime','duration')],
                    proposals=[e.portfolio_proposal(r) for r in e.REGIMES])
        with patch.object(e, 'DATA', rows):
            self.assertEqual(capture(old),capture(new))
            bundle=evidence.model_bundle(ROOT)
            record=e.observation(macro,bundle,'2026-11-23T08:00:00+00:00')
            self.assertEqual(record['_source_reviews'],new)
            self.assertEqual(json.loads(bundle['sources']['source_reviews.json']),new)
            with patch.object(e,'sector_performance',return_value={}), patch.object(e,'forward_run',return_value={'ok':False}):
                html=e.build_html(macro=macro,write=False,reviews=record['_source_reviews'])
            for t in SELECTED:
                self.assertIn(new['entries'][t]['monitoring']['summary'],html)
            self.assertEqual(e.regime_regression_errors(),[])

    def test_cash_arithmetic_does_not_equate_declarations_or_lease_definitions(self):
        p=json.loads((ROOT/'docs/analysis/issuer-events-20261123/due.json').read_text())['issuers']
        o=p['OXY']['payments']
        self.assertNotEqual(o['preferred_declared']+o['common_declared'],o['combined_cash_paid'])
        self.assertIsNone(o['preferred_cash_paid'])
        b=p['CRWV']['balance']
        self.assertEqual(sum(b['debt_carrying_components']),b['debt_carrying_derived'])
        self.assertNotEqual(b['debt_carrying_derived'],b['debt_principal'])
        self.assertEqual(b['cash']+b['marketable'],b['cash_plus_marketable'])


if __name__ == '__main__':
    unittest.main()
