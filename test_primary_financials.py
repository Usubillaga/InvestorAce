"""Issuer cash-flow corrections must survive repricing and later provider refreshes."""
import copy
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

import live_analysis
import source_review
import stock_compare

NOW = datetime(2026, 10, 29, 8, tzinfo=timezone.utc)
ROOT = Path(__file__).parent


class PrimaryFinancials(unittest.TestCase):
    def setUp(self):
        self.review = source_review.load()['entries']['AR']
        self.primary = self.review['valuation']['financial_packet']
        self.provider = json.loads((ROOT/'history/_dynamic_cache.json').read_text())['entries']['AR']
        # Freeze the deliberately incomplete provider fixture, independent of future cache refreshes.
        self.provider.update(financial_period='2026-06-30', beta=.544)
        self.provider['inputs']['fcf'] = 1594733000.
        self.provider['annual_fcf_series'] = [dict(period=f'{y}-12-31',value=v*1e6)
            for y,v in [(2025,1243.148),(2024,747.364),(2023,827.204),(2022,2888.020)]]

    def test_primary_repairs_full_capex_and_preserves_market_inputs(self):
        original = copy.deepcopy(self.provider)
        facts = live_analysis.prefer_primary(self.provider,self.primary,as_of=NOW)
        self.assertEqual(self.provider, original)
        self.assertEqual(facts['inputs']['fcf'], 1133678000)
        self.assertEqual(facts['inputs']['capex'], 1110173000)
        self.assertEqual(facts['inputs']['cash'], 0)
        self.assertEqual(facts['inputs']['shares'], 307136000)
        self.assertEqual(facts['shares_asof'], '2026-10-23')
        self.assertEqual(facts['beta'], .544)
        self.assertEqual(facts['quote_price'], self.provider['quote_price'])

    def test_not_available_before_retrieval(self):
        earlier = datetime(2026,10,28,21,tzinfo=timezone.utc)
        self.assertEqual(live_analysis.prefer_primary(self.provider,self.primary,as_of=earlier),self.provider)

    def test_broken_cash_bridge_blocks_use(self):
        self.primary['inputs']['fcf'] += 1000000
        with self.assertRaisesRegex(ValueError,'bridge'):
            live_analysis.prefer_primary(self.provider,self.primary,as_of=NOW)

    def test_newer_period_retained_but_exact_years_stay_corrected(self):
        self.provider['financial_period']='2026-12-31'
        facts=live_analysis.prefer_primary(self.provider,self.primary,
            as_of=datetime(2027,2,20,tzinfo=timezone.utc))
        self.assertEqual(facts['inputs']['fcf'],1594733000)
        self.assertEqual(facts['annual_fcf_series'][0]['value'],810808000)
        self.assertEqual(facts['financial_period'],'2026-12-31')

    def test_cycle_and_valuation_reproduce_dated_calculations(self):
        facts=live_analysis.prefer_primary(self.provider,self.primary,as_of=NOW)
        facts['midcycle']=True
        result=live_analysis.calculate(facts,quote=dict(price=42.11,observed_at='2026-10-28T20:03:53+00:00'),
            risk_free=.05045000076293945,mrp=.0472,as_of=NOW)
        self.assertAlmostEqual(result['inputs']['valuation_fcf'],728386500)
        self.assertAlmostEqual(result['metrics']['reported_pe'],9.40825954,places=5)
        self.assertAlmostEqual(result['metrics']['valuation_pe'],18.73277222,places=5)
        self.assertAlmostEqual(result['metrics']['fcf_yield_pct'],5.63178437,places=5)
        self.assertFalse(result['can_approve'])
        ledger=self.review['valuation']['calculation_ledger']
        self.assertAlmostEqual(sum(ledger['adjusted_income_bridge']),255.949)
        self.assertAlmostEqual(ledger['quarter']['ocf']-ledger['quarter']['capex'],214.754)

    def test_comparison_repairs_same_fiscal_year_without_mutating_cache(self):
        row=dict(listing='AR',financial_currency='USD',annual=[dict(period_end='2025-12-31',
            revenue=5013610000,gross_profit=1108250000,ocf=1630930000,capex=387782000,fcf=1243148000),
            dict(period_end='2024-12-31',revenue=4118700000)],sources=[],warnings=[])
        corrected=stock_compare.apply_primary_annuals(row,self.review,as_of=NOW)
        self.assertEqual(corrected['annual'][0]['fcf'],810808000)
        self.assertEqual(corrected['annual'][0]['capex'],820122000)
        self.assertAlmostEqual(corrected['annual'][0]['gross_margin'],1108250000/5275823000*100)
        self.assertAlmostEqual(corrected['annual'][0]['revenue_growth'],(5275.823/4325.596-1)*100)
        self.assertEqual(row['annual'][0]['fcf'],1243148000)
        early=datetime(2026,10,28,tzinfo=timezone.utc)
        self.assertEqual(stock_compare.apply_primary_annuals(row,self.review,as_of=early),row)


if __name__=='__main__':
    unittest.main()
