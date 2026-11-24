import copy
import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import coreweave_financials as crwv
import engine
import live_analysis
import source_review


ROOT = Path(__file__).parent
NOW = datetime(2026, 11, 24, 8, tzinfo=timezone.utc)


def packet():
    return dict(schema=live_analysis.VERSION, symbol='CRWV', fetched_at=NOW.isoformat(),
                financial_currency='USD', currency='USD', financial_period='2026-09-30',
                basis='TTM', period_ends=list(crwv.TTM_ENDS), beta=1,
                inputs=dict(debt=66_219e6, cash=4_122e6, ebitda=5_346.33e6,
                            fcf=-20_420.812e6, shares=559e6))


def calculate(facts, when=NOW):
    return live_analysis.calculate(facts, as_of=when, risk_free=.04, mrp=.05)


class CoreWeaveBridge(unittest.TestCase):
    def test_scopes_and_historical_cash_are_reproducible(self):
        raw = packet()
        original = copy.deepcopy(raw)
        result = calculate(raw)
        i, m = result['inputs'], result['metrics']
        self.assertEqual(raw, original)
        self.assertEqual((i['debt'], i['cash'], m['net_debt']), (47_522e6, 4_184e6, 43_338e6))
        self.assertEqual((i['provider_debt'], i['provider_cash'], i['provider_ebitda']),
                         (66_219e6, 4_122e6, 5_346.33e6))
        self.assertEqual(m['net_debt_ebitda'], 43_338 / 5_174)
        self.assertEqual(i['net_debt_including_operating_leases'], 62_035e6)
        self.assertEqual((i['adjusted_ebitda_after_rent'], i['adjusted_ebitdar']), (5_819e6, 7_696e6))
        self.assertEqual(i['issuer_ttm_ocf_less_cash_capex'], -20_421e6)
        self.assertEqual(i['fcf'], raw['inputs']['fcf'])
        self.assertEqual((i['shares'], result['overlay']['shares_asof']), (556_125_724, '2026-10-30'))
        self.assertIn(crwv.Q3, result['source_urls'])
        raw.update(shares_asof='2026-11-20', shares_basis='SEC_DILUTED_AVG')
        self.assertEqual(calculate(raw)['inputs']['shares'], 556_125_724)
        raw.update(shares_basis='ISSUER_COVER_ALL_CLASSES')
        self.assertEqual(calculate(raw)['inputs']['shares'], 559e6)

    def test_publication_cutoff_currency_and_reporting_window(self):
        early = crwv.ACCEPTED - timedelta(seconds=1)
        for changes, when in [({}, early), ({'basis': 'FY'}, NOW),
                              ({'financial_currency': 'EUR'}, NOW),
                              ({'period_ends': ['2026-09-30']}, NOW),
                              ({'financial_period': '2026-12-31'}, NOW + timedelta(days=100))]:
            with self.subTest(changes=changes, when=when):
                result = calculate(dict(packet(), **changes), when)
                self.assertIsNone(result['metrics']['net_debt_ebitda'])
                self.assertIsNone(result['metrics']['net_debt'])
                self.assertIsNone(result['components']['b'])
                self.assertIsNone(result['overlay']['shares_asof'])
                self.assertNotIn(crwv.Q3, result['source_urls'])
        self.assertEqual(calculate(packet(), crwv.ACCEPTED)['metrics']['net_debt'], 43_338e6)
        other = calculate(dict(packet(), symbol='OTHER'))
        self.assertEqual(other['metrics']['net_debt_ebitda'], (66_219-4_122)/5_346.33)

    def test_cached_refresh_keeps_legacy_score_and_dcf_gate_even_with_positive_raw_cash(self):
        row = copy.deepcopy(engine.DATA['CRWV'])
        raw = packet()
        raw['inputs']['fcf'] = 1e9
        raw.update(quote_price=50, quote_observed_at=NOW.isoformat())
        with tempfile.TemporaryDirectory() as tmp, patch.dict(engine.DATA, clear=True, values={'CRWV': row}), \
                patch.object(live_analysis, 'extract', return_value=None):
            cache = Path(tmp) / 'facts.json'
            stored = json.dumps(dict(schema=live_analysis.VERSION, entries={'CRWV': raw}))
            cache.write_text(stored)
            engine.refresh_dynamic_analysis(cache, as_of=NOW, ticker_factory=lambda _: object())
            self.assertEqual(cache.read_text(), stored)
        analysis = row['dynamic_analysis']
        self.assertEqual(row['score_fixed'], 3.41)
        self.assertIsNone(engine.score(row))
        self.assertIsNone(analysis['inputs']['valuation_fcf'])
        self.assertIsNone(engine.ngv(row))
        self.assertIsNone(engine.cushion(row))
        self.assertIsNone(engine.epv(dict(row, epv_value=99)))
        self.assertIsNone(analysis['valuation']['reverse_dcf_growth_pct'])
        self.assertTrue(all(s['value_per_share'] is None for s in analysis['valuation']['scenarios']))
        self.assertEqual(analysis['metrics']['net_debt'], 43_338e6)

    def test_sources_match_dated_packets(self):
        current = source_review.load()['entries']['CRWV']['monitoring']
        while current['as_of'] != '2026-11-23':
            current = current['previous_attempt']
        previous = current['previous_attempt']
        for event, path in [(current, ROOT/current['evidence_packet']/'due.json'),
                            (previous, ROOT/previous['evidence_packet'])]:
            doc = json.loads(path.read_text())['issuers']['CRWV']
            q3 = next(s for s in doc['sources'] if s['url'] == crwv.Q3)
            self.assertEqual(q3['published_at'], crwv.ACCEPTED.date().isoformat())
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), event['evidence_sha256'][path.name])
        balance = json.loads((ROOT/current['evidence_packet']/'due.json').read_text())['issuers']['CRWV']['balance']
        inputs = calculate(packet())['inputs']
        self.assertEqual(inputs['debt_carrying_ex_leases'], sum(balance['debt_carrying_components'])*1e6)
        self.assertEqual(inputs['debt_principal_ex_leases'], balance['debt_principal']*1e6)
        self.assertEqual(inputs['finance_lease_liabilities'], balance['finance_leases']*1e6)
        self.assertEqual(inputs['operating_lease_liabilities'], balance['operating_leases']*1e6)


if __name__ == '__main__':
    unittest.main()
