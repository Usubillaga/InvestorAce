"""Common-share inputs need matched scope and distinct cash/earnings bridges."""
import copy
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import live_analysis
import sec_quarters
import source_review
from test_live_analysis import ticker_fixture
from test_framework_contract import engine


ASOF = datetime(2026, 11, 5, tzinfo=timezone.utc)


def calculate(facts):
    return live_analysis.calculate(facts, risk_free=.05, mrp=.05, as_of=ASOF)


def facts_with_row(**changes):
    facts = live_analysis.extract(ticker_fixture(), 'TEST', as_of=ASOF)
    row = dict(period='2025-12-31', basis='FY', scope='REPORTED',
               operating_cash_flow=120e6, capex=20e6, net_income=150e6,
               preferred_claims_known=True, preferred_cash_paid=10e6,
               preferred_earnings_deduction=12e6)
    row.update(changes)
    facts['equity_periods'] = [row]
    return facts


class CommonEquityBasis(unittest.TestCase):
    def test_cash_and_earnings_adjustments_differ_and_raw_inputs_survive(self):
        result = calculate(facts_with_row())
        self.assertEqual(result['inputs']['fcf'], 100e6)
        self.assertEqual(result['inputs']['net_income'], 150e6)
        self.assertEqual(result['inputs']['valuation_fcf'], 90e6)
        self.assertEqual(result['inputs']['valuation_net_income'], 138e6)

    def test_already_common_earnings_are_not_deducted_again(self):
        result = calculate(facts_with_row(net_income_common=138e6))
        self.assertEqual(result['inputs']['valuation_net_income'], 138e6)

    def test_signed_and_explicit_zero_cash_are_valid_but_missing_is_unknown(self):
        for paid, expected in ((-10e6, 90e6), (0., 100e6), (None, None)):
            with self.subTest(paid=paid):
                result = calculate(facts_with_row(preferred_cash_paid=paid))
                self.assertEqual(result['inputs']['valuation_fcf'], expected)
        self.assertTrue(calculate(facts_with_row(preferred_cash_paid=None))['valuation_input_conflicts'])

    def test_cash_dividend_does_not_substitute_for_missing_earnings_deduction(self):
        result = calculate(facts_with_row(preferred_earnings_deduction=None))
        self.assertIsNone(result['inputs']['valuation_net_income'])

    def test_mixed_cash_scope_cannot_be_capitalised(self):
        result = calculate(facts_with_row(scope='UNRESOLVED', has_discontinued_operations=True))
        self.assertIsNone(result['valuation']['ngv_per_share'])
        self.assertTrue(result['valuation_input_conflicts'])

    def test_provider_fields_work_without_a_ticker_register_entry(self):
        tk = ticker_fixture()
        tk.cashflow.loc['Preferred Stock Dividend Paid'] = [-10e6] * 3
        tk.income_stmt.loc['Preferred Stock Dividends'] = [12e6] * 3
        tk.income_stmt.loc['Net Income Common Stockholders'] = [138e6] * 3
        facts = live_analysis.extract(tk, 'UNREGISTERED', as_of=ASOF)
        result = calculate(facts)
        self.assertEqual(result['inputs']['valuation_fcf'], 90e6)
        self.assertEqual(result['inputs']['valuation_net_income'], 138e6)
        self.assertEqual(result['common_equity_basis']['current']['earnings_method'], 'ALREADY_COMMON')

    def test_known_preferred_balance_without_paid_cash_is_not_zero(self):
        tk = ticker_fixture()
        tk.balance_sheet.loc['Preferred Stock'] = [100e6] * 3
        result = calculate(live_analysis.extract(tk, 'UNREGISTERED', as_of=ASOF))
        self.assertIsNone(result['valuation']['ngv_per_share'])

    def test_continuing_cash_does_not_certify_consolidated_epv_or_revenue(self):
        tk = ticker_fixture()
        tk.cashflow.loc['Cash Flow From Discontinued Operating Activities'] = [5e6] * 3
        tk.income_stmt.loc['Net Income Discontinuous Operations'] = [2e6] * 3
        tk.cashflow.loc['Cash Flow From Continuing Operating Activities'] = [115e6] * 3
        tk.cashflow.loc['Capital Expenditure From Continuing Operations'] = [-20e6] * 3
        result = calculate(live_analysis.extract(tk, 'UNREGISTERED', as_of=ASOF))
        self.assertEqual(result['inputs']['valuation_fcf'], 95e6)
        self.assertIsNone(result['inputs']['valuation_net_income'])
        self.assertIsNone(result['metrics']['fcf_margin_pct'])
        self.assertIsNone(engine.epv(dict(epv_value=67., dynamic_analysis=result)))

    def test_ordinary_company_keeps_its_formulas(self):
        facts = live_analysis.extract(ticker_fixture(), 'TEST', as_of=ASOF)
        result = calculate(facts)
        self.assertEqual(result['inputs']['valuation_fcf'], 100e6)
        self.assertEqual(result['inputs']['valuation_net_income'], 150e6)
        self.assertEqual(result['valuation_input_conflicts'], [])

    def test_explicit_zero_common_dividend_survives_common_income_metadata(self):
        tk = ticker_fixture()
        tk.cashflow = tk.cashflow.drop('Cash Dividends Paid')
        tk.info.update(trailingAnnualDividendRate=0., dividendRate=0.)
        tk.income_stmt.loc['Net Income Common Stockholders'] = [150e6] * 3
        facts = live_analysis.extract(tk, 'TEST', as_of=ASOF)
        facts['quote_observed_at'] = '2026-11-04T21:00:00+00:00'
        result = calculate(facts)
        self.assertEqual(result['inputs']['dividends'], 0.)
        self.assertEqual(result['metrics']['shareholder_yield_pct'], 0.)

    def test_primary_packet_overrides_provider_equity_metadata(self):
        facts = facts_with_row(preferred_claims_known=False, preferred_cash_paid=None,
                               preferred_earnings_deduction=None, net_income_common=140e6)
        primary = copy.deepcopy(facts)
        primary.pop('equity_periods')
        primary.update(published_at='2026-02-20T00:00:00+00:00', fetched_at='2026-11-01T00:00:00+00:00')
        primary['inputs'].update(operating_cash_flow=100e6, capex=20e6, fcf=80e6, net_income=130e6)
        primary['annual_fcf_series'] = [dict(period=f'{y}-12-31', value=80e6) for y in (2025,2024,2023)]
        primary['annual_net_income_series'] = [dict(period=f'{y}-12-31', value=130e6) for y in (2025,2024,2023)]
        corrected = live_analysis.prefer_primary(facts, primary, as_of=ASOF)
        result = calculate(corrected)
        self.assertEqual(result['inputs']['valuation_fcf'], 80e6)
        self.assertEqual(result['inputs']['valuation_net_income'], 130e6)
        corrected['midcycle'] = True
        result = calculate(corrected)
        self.assertEqual(result['inputs']['valuation_fcf'], 80e6)
        self.assertEqual(result['inputs']['valuation_net_income'], 130e6)

    def test_epv_conflicts_block_cached_values_and_skip_fetch(self):
        row = copy.deepcopy(engine.DATA['OXY'])
        row.update(epv_value=67., dynamic_analysis=dict(valuation_input_conflicts=[
            dict(code='COMMON_EQUITY_CLAIMS_OMITTED', reason='Missing senior claim.')]))
        self.assertIsNone(engine.epv(row))
        with patch.object(engine, 'DATA', {'OXY': row}), \
             patch.object(engine, '_epv_cache_load', return_value={}), \
             patch.object(engine.EPV, 'fetch') as fetch:
            engine.populate_epv()
        fetch.assert_not_called()
        self.assertIsNone(row['epv_value'])
        self.assertIn('blocked', row['epv_note'].lower())

    def test_new_sec_window_does_not_reuse_old_preferred_cash(self):
        facts = facts_with_row()
        metrics = dict(period_end='2026-06-30', basis='TTM', revenue=1000e6,
                       operating_income=200e6, fcf=120e6, shares=10e6,
                       operating_cash_flow=140e6, capex=20e6, net_income=150e6,
                       depreciation=10e6, debt=50e6, cash=10e6, accns=[])
        newer = sec_quarters.newer_packet(facts, metrics, 123, ASOF.date())
        result = calculate(newer)
        self.assertIsNone(result['inputs']['valuation_fcf'])
        self.assertIsNone(result['common_equity_basis']['current']['preferred_cash_paid'])

    def test_new_sec_window_cannot_clear_known_scope_uncertainty(self):
        facts = facts_with_row(preferred_claims_known=False, preferred_cash_paid=None,
                               preferred_earnings_deduction=None, scope='CONTINUING',
                               has_discontinued_operations=True)
        facts.update(financial_period='2026-06-30', basis='TTM')
        # SEC catch-up replaced amounts but supplies no matching perimeter row.
        result = calculate(facts)
        self.assertIsNone(result['inputs']['valuation_fcf'])
        self.assertTrue(result['valuation_input_conflicts'])


class DatedPrimaryBridge(unittest.TestCase):
    def setUp(self):
        self.facts = json.loads((Path(__file__).parent / 'tests/fixtures/oxy-inputs-20261104.json').read_text())
        self.facts['midcycle'] = True
        self.section = source_review.load()['entries']['OXY']['valuation']
        self.facts['common_equity_bridge'] = self.section.get('common_equity_bridge')
        self.facts['valuation_input_conflicts'] = source_review.valuation_input_conflicts(self.section, as_of=ASOF)

    def test_original_filings_reconcile_cash_capex_and_common_earnings(self):
        result = calculate(self.facts)
        basis = result['common_equity_basis']
        self.assertIsNotNone(basis)
        rows = {r['period']: r for r in basis['annual']}
        for year, cash, income in ((2025, 2532e6, 1385e6), (2024, 3677e6, 2165e6), (2023, 3755e6, 2409e6)):
            self.assertEqual(rows[f'{year}-12-31']['common_fcf'], cash)
            self.assertEqual(rows[f'{year}-12-31']['common_net_income'], income)
        self.assertIsNone(rows['2022-12-31']['common_fcf'])
        self.assertEqual(result['inputs']['fcf'], 4793e6)
        self.assertEqual(basis['current']['fcf_before_preferred'], 5081e6)
        self.assertEqual(basis['current']['common_net_income'], 3439e6)
        self.assertIsNone(basis['current']['common_fcf'])
        self.assertIsNone(result['valuation']['dcf_per_share'])
        self.assertTrue(result['valuation_input_conflicts'])
        self.assertEqual(rows['2023-12-31']['preferred_cash_paid'], 762e6)
        self.assertEqual(rows['2023-12-31']['preferred_earnings_deduction'], 923e6)

    def test_future_retrieval_does_not_rewrite_a_past_observation(self):
        self.assertIsNotNone(self.facts['common_equity_bridge'])
        self.facts['common_equity_bridge']['fetched_at'] = '2026-11-06T00:00:00+00:00'
        result = calculate(self.facts)
        self.assertIsNone(result['common_equity_basis'])

    def test_wrong_currency_identity_or_capex_reconciliation_is_rejected(self):
        self.assertIsNotNone(self.facts['common_equity_bridge'])
        for field, value in (('currency', 'EUR'), ('symbol', 'OTHER')):
            with self.subTest(field=field):
                facts = copy.deepcopy(self.facts)
                facts['common_equity_bridge'][field] = value
                with self.assertRaises(ValueError):
                    calculate(facts)
        self.facts['common_equity_bridge']['periods'][0]['capex'] += 1e6
        with self.assertRaises(ValueError):
            calculate(self.facts)

    def test_only_complete_matching_current_data_can_resolve_typed_conflicts(self):
        self.assertIsNotNone(self.facts['common_equity_bridge'])
        self.facts['common_equity_bridge']['periods'][0]['preferred_cash_paid'] = 679e6
        result = calculate(self.facts)
        self.assertEqual(result['valuation_input_conflicts'], [])
        self.assertEqual(len(result['common_equity_basis']['resolved_input_conflicts']), 2)
        self.assertAlmostEqual(result['inputs']['valuation_fcf'], (2532e6+3677e6+3755e6)/3)
        self.assertAlmostEqual(result['metrics']['fcf_margin_pct'], 100*4402/23926)
        self.assertEqual(result['parameters']['earnings_basis'], 'CYCLE_MEAN')
        # A later provider quarter must not inherit the completed June bridge.
        self.facts['financial_period'] = '2026-09-30'
        result = calculate(self.facts)
        self.assertTrue(result['valuation_input_conflicts'])
        self.assertIsNone(result['inputs']['valuation_fcf'])

    def test_register_issuer_and_listing_symbol_are_distinct_identities(self):
        doc = source_review.load()
        bridge = copy.deepcopy(self.facts['common_equity_bridge'])
        self.assertIsNotNone(bridge)
        bridge.update(issuer_key='WKL', symbol='WKL.AS', currency='EUR')
        doc['entries']['WKL']['valuation']['common_equity_bridge'] = bridge
        source_review.load(json.dumps(doc))
        synthetic = copy.deepcopy(self.facts)
        synthetic.update(symbol='WKL.AS', currency='EUR', financial_currency='EUR', common_equity_bridge=bridge)
        self.assertIsNotNone(calculate(synthetic)['common_equity_basis'])
        bridge['issuer_key'] = 'OTHER'
        with self.assertRaises(ValueError):
            source_review.load(json.dumps(doc))


if __name__ == '__main__':
    unittest.main()
