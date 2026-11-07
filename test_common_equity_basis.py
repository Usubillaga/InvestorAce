"""Common-share inputs need matched scope and distinct cash/earnings bridges."""
import copy
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pandas as pd

import i18n
import live_analysis
import opportunity_view
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

    @staticmethod
    def disposal(tk, *, separated=True, continuing_income=True):
        """A material disposal (20% of income and of operating cash) in yfinance's own row names."""
        tk.income_stmt.loc['Net Income Discontinuous Operations'] = [30e6] * 3
        if continuing_income:
            tk.income_stmt.loc['Net Income From Continuing Operation Net Minority Interest'] = [120e6] * 3
        if separated:
            tk.cashflow.loc['Cash From Discontinued Operating Activities'] = [25e6] * 3
            tk.cashflow.loc['Cash From Discontinued Investing Activities'] = [-6e6] * 3
            tk.cashflow.loc['Cash Flow From Continuing Operating Activities'] = [95e6] * 3
        return tk

    def test_separated_disposal_uses_continuing_cash_earnings_and_revenue(self):
        result = calculate(live_analysis.extract(self.disposal(ticker_fixture()), 'UNREGISTERED', as_of=ASOF))
        current = result['common_equity_basis']['current']
        self.assertEqual(current['scope'], 'CONTINUING')
        self.assertTrue(current['discontinued_material'])
        self.assertEqual(current['discontinued_operating_cash_flow'], 25e6)
        self.assertEqual(result['inputs']['fcf'], 100e6)                 # raw provider value survives
        self.assertEqual(result['inputs']['valuation_fcf'], 75e6)        # 95 continuing OCF - 20 capex
        self.assertEqual(result['inputs']['valuation_net_income'], 120e6)
        self.assertAlmostEqual(result['metrics']['fcf_margin_pct'], 7.5)  # revenue excludes the sold unit
        self.assertEqual(result['valuation_input_conflicts'], [])
        self.assertEqual(result['parameters']['common_equity_scope'], 'CONTINUING')
        # A continuing proxy still does not certify the enterprise EPV bridge.
        self.assertIsNone(engine.epv(dict(epv_value=67., dynamic_analysis=result)))

    def test_cash_growth_never_compares_two_business_perimeters(self):
        tk = self.disposal(ticker_fixture())
        for row in ('Net Income Discontinuous Operations', 'Cash From Discontinued Operating Activities',
                    'Cash From Discontinued Investing Activities'):
            frame = tk.income_stmt if row.startswith('Net Income') else tk.cashflow
            frame.loc[row, frame.columns[1:]] = float('nan')     # only FY2025 is recast
        result = calculate(live_analysis.extract(tk, 'UNREGISTERED', as_of=ASOF))
        scopes = [r['scope'] for r in result['common_equity_basis']['annual'][:2]]
        self.assertEqual(scopes, ['CONTINUING', 'REPORTED'])
        self.assertIsNone(result['metrics']['fcf_growth_pct'])
        self.assertEqual(result['parameters']['growth_rate_pct'], 0.)

    def test_continuing_operating_cash_can_be_derived_from_the_discontinued_row(self):
        tk = self.disposal(ticker_fixture())
        tk.cashflow = tk.cashflow.drop('Cash Flow From Continuing Operating Activities')
        result = calculate(live_analysis.extract(tk, 'UNREGISTERED', as_of=ASOF))
        self.assertEqual(result['inputs']['valuation_fcf'], 75e6)        # 120 total - 25 discontinued - 20

    def test_material_disposal_without_separated_cash_stays_unresolved(self):
        tk = self.disposal(ticker_fixture(), separated=False)
        result = calculate(live_analysis.extract(tk, 'UNREGISTERED', as_of=ASOF))
        self.assertEqual(result['common_equity_basis']['current']['scope'], 'UNRESOLVED')
        self.assertIsNone(result['valuation']['ngv_per_share'])
        self.assertEqual([c['code'] for c in result['valuation_input_conflicts']],
                         ['DISPOSED_BUSINESS_IN_CYCLE_PROXY'])

    def test_continuing_cash_without_continuing_income_leaves_the_multiple_unknown(self):
        tk = self.disposal(ticker_fixture(), continuing_income=False)
        result = calculate(live_analysis.extract(tk, 'UNREGISTERED', as_of=ASOF))
        self.assertEqual(result['inputs']['valuation_fcf'], 75e6)
        self.assertIsNone(result['inputs']['valuation_net_income'])

    def test_quarters_after_a_disposal_count_as_zero_discontinued(self):
        # OXY-like TTM to September: only the oldest quarter still holds the
        # sold business; Yahoo leaves the later quarters of those rows empty.
        tk = ticker_fixture()
        quarters = pd.to_datetime(['2026-09-30', '2026-06-30', '2026-03-31', '2025-12-31'])
        nan = float('nan')
        tk.quarterly_cashflow = pd.DataFrame(
            [[30e6] * 4, [-5e6] * 4, [nan, nan, nan, 10e6], [nan, nan, nan, -2e6]],
            index=['Operating Cash Flow', 'Capital Expenditure', 'Cash From Discontinued Operating Activities',
                   'Cash From Discontinued Investing Activities'], columns=quarters)
        tk.quarterly_income_stmt = pd.DataFrame(
            [[250e6] * 4, [50e6] * 4, [40e6, 40e6, 40e6, 60e6], [nan, nan, nan, 20e6], [40e6] * 4],
            index=['Total Revenue', 'Operating Income', 'Net Income', 'Net Income Discontinuous Operations',
                   'Net Income From Continuing Operation Net Minority Interest'], columns=quarters)
        facts = live_analysis.extract(tk, 'UNREGISTERED', as_of=ASOF)
        self.assertEqual(facts['basis'], 'TTM')
        current = next(r for r in facts['equity_periods'] if r['basis'] == 'TTM')
        self.assertEqual((current['discontinued_operating_cash_flow'], current['discontinued_net_income']),
                         (10e6, 20e6))
        result = calculate(facts)
        self.assertEqual(result['common_equity_basis']['current']['scope'], 'CONTINUING')
        self.assertEqual(result['inputs']['valuation_fcf'], 90e6)        # 120 - 10 discontinued - 20
        self.assertEqual(result['inputs']['valuation_net_income'], 160e6)

    def test_immaterial_legacy_discontinued_line_keeps_reported_figures(self):
        # Pfizer: USD -5m over nine months against USD 5,710m of net income.
        tk = ticker_fixture()
        tk.income_stmt.loc['Net Income Discontinuous Operations'] = [-.5e6] * 3
        tk.cashflow.loc['Cash From Discontinued Operating Activities'] = [-.4e6] * 3
        result = calculate(live_analysis.extract(tk, 'UNREGISTERED', as_of=ASOF))
        current = result['common_equity_basis']['current']
        self.assertEqual(current['scope'], 'REPORTED')
        self.assertIs(current['discontinued_material'], False)
        self.assertEqual(result['inputs']['valuation_fcf'], 100e6)
        self.assertEqual(result['inputs']['valuation_net_income'], 150e6)
        self.assertEqual(result['valuation_input_conflicts'], [])
        self.assertTrue(any('at or below 5%' in w for w in result['warnings']))
        self.assertEqual(engine.epv(dict(epv_value=67., dynamic_analysis=result)), 67.)

    def test_rows_extracted_before_the_materiality_field_stay_conservative(self):
        facts = facts_with_row(preferred_claims_known=False, preferred_cash_paid=None,
                               preferred_earnings_deduction=None, has_discontinued_operations=True,
                               scope='UNRESOLVED')
        self.assertTrue(calculate(facts)['valuation_input_conflicts'])

    def test_a_disposal_outside_the_current_window_does_not_reach_it(self):
        # Broadcom's FY2024 VMware disposal against a later window without its
        # own provider row (an SEC catch-up packet, for example).
        facts = live_analysis.extract(ticker_fixture(), 'TEST', as_of=ASOF)
        facts['equity_periods'] = [dict(period='2023-12-31', basis='FY', scope='UNRESOLVED',
                                        has_discontinued_operations=True, discontinued_material=True)]
        result = calculate(facts)
        self.assertEqual(result['common_equity_basis']['current']['scope'], 'REPORTED')
        self.assertEqual(result['inputs']['valuation_fcf'], 100e6)
        facts['equity_periods'][0]['period'] = '2025-06-30'
        facts['equity_periods'][0]['basis'] = 'TTM'
        self.assertIsNone(calculate(facts)['inputs']['valuation_fcf'])

    def test_declared_dividend_on_an_unchanged_balance_is_the_cash_claim(self):
        facts = facts_with_row(preferred_cash_paid=None, preferred_outstanding=200e6)
        facts['equity_periods'].append(dict(period='2024-12-31', basis='FY', scope='REPORTED',
                                            preferred_outstanding=200e6))
        result = calculate(facts)
        current = result['common_equity_basis']['current']
        self.assertEqual(current['preferred_cash_basis'], 'DECLARED_STABLE_BALANCE')
        self.assertIsNone(current['preferred_cash_paid'])                # the raw field stays unknown
        self.assertEqual(result['inputs']['valuation_fcf'], 88e6)        # 100 - 12 declared
        self.assertEqual(result['valuation_input_conflicts'], [])
        self.assertTrue(any('declared dividend' in w for w in result['warnings']))
        # Cash paid, when reported, wins over the declaration.
        facts['equity_periods'][0]['preferred_cash_paid'] = 10e6
        self.assertEqual(calculate(facts)['inputs']['valuation_fcf'], 90e6)

    def test_a_moved_preferred_balance_keeps_the_cash_claim_unknown(self):
        # Issues, conversions and redemptions (OXY 2023: 9,762m -> 8,287m with
        # a 151m premium in the deduction) break the declared-to-paid link.
        for opening in (300e6, 0., None):
            with self.subTest(opening=opening):
                facts = facts_with_row(preferred_cash_paid=None, preferred_outstanding=200e6)
                facts['equity_periods'].append(dict(period='2024-12-31', basis='FY', scope='REPORTED',
                                                    preferred_outstanding=opening))
                result = calculate(facts)
                self.assertIsNone(result['inputs']['valuation_fcf'])
                self.assertTrue(result['valuation_input_conflicts'])

    def test_ordinary_company_keeps_its_formulas(self):
        facts = live_analysis.extract(ticker_fixture(), 'TEST', as_of=ASOF)
        result = calculate(facts)
        self.assertEqual(result['inputs']['valuation_fcf'], 100e6)
        self.assertEqual(result['inputs']['valuation_net_income'], 150e6)
        self.assertEqual(result['valuation_input_conflicts'], [])

    def test_old_preferred_charge_does_not_impose_a_current_payment(self):
        facts = facts_with_row(preferred_claims_known=False, preferred_cash_paid=None,
                               preferred_earnings_deduction=None, preferred_outstanding=0.,
                               net_income_common=150e6)
        facts['equity_periods'].append(dict(period='2021-12-31', basis='FY', scope='REPORTED',
            operating_cash_flow=120e6, capex=20e6, net_income=150e6,
            preferred_earnings_deduction=12e6, preferred_cash_paid=None))
        result = calculate(facts)
        self.assertEqual(result['inputs']['valuation_fcf'], 100e6)
        self.assertEqual(result['valuation_input_conflicts'], [])
        old = next(r for r in result['common_equity_basis']['annual'] if r['period']=='2021-12-31')
        self.assertIsNone(old['common_fcf'])

    def test_claim_at_start_of_window_still_requires_a_payment_bridge(self):
        facts = facts_with_row(preferred_claims_known=False, preferred_cash_paid=None,
                               preferred_earnings_deduction=None, preferred_outstanding=0.)
        facts['equity_periods'].append(dict(period='2024-12-31', basis='FY', scope='REPORTED',
                                           preferred_outstanding=50e6))
        result = calculate(facts)
        self.assertIsNone(result['inputs']['valuation_fcf'])
        self.assertTrue(result['valuation_input_conflicts'])

    def test_paid_dividend_ending_at_opening_does_not_enter_the_next_year(self):
        facts = facts_with_row(preferred_claims_known=False, preferred_cash_paid=None,
                               preferred_earnings_deduction=None, preferred_outstanding=0.)
        facts['equity_periods'].append(dict(period='2024-12-31', basis='FY', scope='REPORTED',
                                           preferred_outstanding=0., preferred_cash_paid=10e6))
        self.assertEqual(calculate(facts)['inputs']['valuation_fcf'], 100e6)

    def test_known_balance_survives_without_a_later_opening_balance(self):
        facts = facts_with_row(preferred_claims_known=False, preferred_cash_paid=None,
                               preferred_earnings_deduction=None, preferred_outstanding=0.)
        facts['equity_periods'].append(dict(period='2023-12-31', basis='FY', scope='REPORTED',
                                           preferred_outstanding=50e6))
        # A closing zero alone cannot date the intervening redemption.
        self.assertIsNone(calculate(facts)['inputs']['valuation_fcf'])

    def test_one_annual_claim_does_not_invalidate_other_complete_years(self):
        facts = facts_with_row(preferred_claims_known=False, preferred_cash_paid=None,
                               preferred_earnings_deduction=None, preferred_outstanding=0.)
        facts['equity_periods'].append(dict(period='2023-12-31', basis='FY', scope='REPORTED',
            operating_cash_flow=120e6, capex=20e6, net_income=150e6,
            preferred_cash_paid=10e6, preferred_earnings_deduction=12e6))
        result = calculate(facts)
        annual = {r['period']:r for r in result['common_equity_basis']['annual']}
        self.assertEqual(annual['2025-12-31']['common_fcf'],100e6)
        self.assertEqual(annual['2023-12-31']['common_fcf'],90e6)

    def test_explicit_claim_policy_blocks_unbridged_cycle_years(self):
        facts = facts_with_row()
        facts.update(midcycle=True, preferred_claims_required=True,
                     annual_fcf_series=[dict(period=f'{y}-12-31', value=100e6) for y in (2025, 2024, 2023)],
                     annual_net_income_series=[dict(period=f'{y}-12-31', value=150e6) for y in (2025, 2024, 2023)])
        self.assertIsNone(calculate(facts)['inputs']['valuation_fcf'])

    def test_expired_claim_does_not_remove_a_reported_fcf_fallback(self):
        facts = facts_with_row()
        facts['equity_periods'][0].update(period='2021-12-31')
        facts['inputs'].update(capex=None)
        self.assertEqual(calculate(facts)['inputs']['valuation_fcf'], 100e6)

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

    def test_new_sec_window_does_not_revive_expired_preferred_evidence(self):
        facts = facts_with_row(preferred_claims_known=False, preferred_cash_paid=None,
                               preferred_earnings_deduction=None, preferred_outstanding=0.)
        facts['equity_periods'].append(dict(period='2021-12-31', basis='FY', scope='REPORTED',
                                           preferred_earnings_deduction=12e6))
        metrics = dict(period_end='2026-06-30', basis='TTM', revenue=1000e6,
                       operating_income=200e6, fcf=120e6, shares=10e6,
                       operating_cash_flow=140e6, capex=20e6, net_income=150e6,
                       depreciation=10e6, debt=50e6, cash=10e6, accns=[])
        newer = sec_quarters.newer_packet(facts, metrics, 123, ASOF.date())
        result = calculate(newer)
        self.assertEqual(result['inputs']['valuation_fcf'], 120e6)
        self.assertEqual(result['valuation_input_conflicts'], [])
        # Old cached SEC packets carried the inferred flag over all history.
        newer['financial_source'] = 'SEC_COMPANYFACTS'
        newer['preferred_claims_required'] = True
        self.assertEqual(calculate(newer)['inputs']['valuation_fcf'], 120e6)
        # With no rows that could have produced an inferred flag, the policy
        # was explicit and the newer packet still needs a payment bridge.
        newer['equity_periods'] = []
        self.assertIsNone(calculate(newer)['inputs']['valuation_fcf'])
        facts['preferred_claims_required'] = True
        newer = sec_quarters.newer_packet(facts, metrics, 123, ASOF.date())
        self.assertIsNone(calculate(newer)['inputs']['valuation_fcf'])

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
        # June 2026 TTM: cash paid is not separately confirmed, the declared
        # 679m on the unchanged 8,287m Berkshire balance is the claim.
        self.assertIsNone(basis['current']['preferred_cash_paid'])
        self.assertEqual(basis['current']['preferred_cash_basis'], 'DECLARED_STABLE_BALANCE')
        self.assertEqual(basis['current']['common_fcf'], 4402e6)
        self.assertEqual(result['valuation_input_conflicts'], [])
        self.assertAlmostEqual(result['inputs']['valuation_fcf'], (2532e6+3677e6+3755e6)/3)
        self.assertIsNotNone(result['valuation']['dcf_per_share'])
        # 2023 had redemptions: its cash dividend, not the 923m deduction, counts.
        self.assertEqual(rows['2023-12-31']['preferred_cash_paid'], 762e6)
        self.assertEqual(rows['2023-12-31']['preferred_cash_basis'], 'PAID')
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
        self.assertEqual(result['common_equity_basis']['current']['preferred_cash_basis'], 'PAID')
        # A later provider quarter does not inherit the completed June bridge:
        # its current cash ratios are unknown. The commodity value rests on the
        # FY2023-25 years, which the issuer bridge still covers completely.
        self.facts['financial_period'] = '2026-09-30'
        result = calculate(self.facts)
        self.assertEqual(result['valuation_input_conflicts'], [])
        self.assertIsNone(result['common_equity_basis']['current']['common_fcf'])
        self.assertIsNone(result['metrics']['fcf_margin_pct'])
        self.assertTrue(result['common_equity_basis']['current_window_open'])
        self.assertAlmostEqual(result['inputs']['valuation_fcf'], (2532e6+3677e6+3755e6)/3)
        self.assertTrue(any('current window lacks' in w for w in result['warnings']))

    def test_a_current_valuation_never_inherits_an_earlier_window_bridge(self):
        # Outside a commodity cycle the current window is the valuation input.
        self.facts.update(midcycle=False, financial_period='2026-09-30')
        result = calculate(self.facts)
        self.assertTrue(result['valuation_input_conflicts'])
        self.assertIsNone(result['inputs']['valuation_fcf'])

    def test_a_cycle_without_an_issuer_scope_still_blocks_on_a_current_disposal(self):
        facts = facts_with_row(preferred_claims_known=False, preferred_cash_paid=None,
                               preferred_earnings_deduction=None, scope='UNRESOLVED',
                               has_discontinued_operations=True, discontinued_material=True)
        facts.update(midcycle=True,
                     annual_fcf_series=[dict(period=f'{y}-12-31', value=100e6) for y in (2024, 2023, 2022)],
                     annual_net_income_series=[dict(period=f'{y}-12-31', value=150e6) for y in (2024, 2023, 2022)])
        result = calculate(facts)
        self.assertIn('DISPOSED_BUSINESS_IN_CYCLE_PROXY', [c['code'] for c in result['valuation_input_conflicts']])
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


class PrimaryFieldCorrections(unittest.TestCase):
    def facts(self):
        facts = facts_with_row(preferred_cash_paid=None, net_income_common=138e6, revenue=1000e6)
        url = 'https://issuer.example/2025-report'
        facts['common_equity_bridge'] = dict(schema='common-equity-bridge-v1', issuer_key='TEST',
            symbol='TEST', currency='USD', units='currency_units', required_scope='REPORTED',
            preferred_claims_required=True, published_at='2026-02-01T00:00:00+00:00',
            fetched_at='2026-11-01T00:00:00+00:00', source_urls=[url], periods=[dict(
                period='2025-12-31', basis='FY', scope='REPORTED', preferred_cash_paid=10e6,
                patch_fields=['preferred_cash_paid'], source_urls=[url])])
        return facts

    def test_dated_preferred_cash_correction_preserves_other_reported_fields(self):
        result = calculate(self.facts())
        self.assertEqual(result['inputs']['valuation_fcf'], 90e6)
        self.assertEqual(result['inputs']['valuation_net_income'],138e6)
        self.assertEqual(result['inputs']['fcf'],100e6)
        current = result['common_equity_basis']['current']
        self.assertEqual(current['revenue'],1000e6)
        self.assertIn('preferred_cash_paid',current['field_sources'])

    def test_malformed_patch_cannot_override_policy_or_fill_unlisted_values(self):
        for fields in ([], ['valuation_input_conflicts'], ['preferred_cash_paid','preferred_cash_paid']):
            facts = self.facts()
            facts['common_equity_bridge']['periods'][0]['patch_fields'] = fields
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                calculate(facts)

    def test_merged_earnings_fields_must_reconcile(self):
        facts = self.facts()
        patch_row = facts['common_equity_bridge']['periods'][0]
        patch_row.update(preferred_earnings_deduction=20e6, patch_fields=['preferred_earnings_deduction'])
        with self.assertRaisesRegex(ValueError, 'common-income bridge does not reconcile'):
            calculate(facts)

    def test_payment_correction_does_not_roll_into_a_different_period(self):
        facts = self.facts()
        facts['financial_period'] = '2026-06-30'
        facts['basis'] = 'TTM'
        result = calculate(facts)
        self.assertIsNone(result['inputs']['valuation_fcf'])
        self.assertIsNone(result['common_equity_basis']['current']['preferred_cash_paid'])

    def test_source_claim_survives_when_provider_no_longer_has_the_prior_row(self):
        facts = self.facts()
        facts.update(financial_period='2026-06-30', basis='TTM', equity_periods=[])
        facts['common_equity_bridge']['preferred_claims_required'] = False
        result = calculate(facts)
        self.assertIsNone(result['inputs']['valuation_fcf'])
        self.assertTrue(result['common_equity_basis']['preferred_claims_required'])
        self.assertIsNone(result['common_equity_basis']['current']['preferred_cash_paid'])

    def test_payment_correction_requires_known_statement_currency(self):
        facts = self.facts()
        facts['financial_currency'] = None
        result = calculate(facts)
        self.assertIsNone(result['inputs']['valuation_fcf'])
        self.assertIsNone(result['common_equity_basis']['current']['preferred_cash_paid'])

    def test_payment_correction_cannot_clear_a_disposed_business_conflict(self):
        facts = self.facts()
        facts['valuation_input_conflicts'] = [dict(code='DISPOSED_BUSINESS_IN_CYCLE_PROXY',
            reason='The same-period cash still includes an exited business.', detected_at='2026-11-01')]
        result = calculate(facts)
        self.assertEqual(result['valuation_input_conflicts'], facts['valuation_input_conflicts'])
        self.assertIsNone(result['inputs']['valuation_fcf'])

    def test_correction_for_reported_cash_is_skipped_for_recast_scope(self):
        facts = self.facts()
        facts['equity_periods'][0]['scope'] = 'CONTINUING'
        result = calculate(facts)
        self.assertEqual(result['common_equity_basis']['current']['scope'], 'CONTINUING')
        self.assertIsNone(result['common_equity_basis']['current']['preferred_cash_paid'])
        self.assertTrue(result['valuation_input_conflicts'])

    def test_historic_full_bridge_cannot_clear_a_new_disposal_conflict(self):
        facts = self.facts()
        facts['equity_periods'][0].update(scope='CONTINUING', preferred_cash_paid=10e6)
        bridge = facts['common_equity_bridge']
        bridge['required_scope'] = 'CONTINUING'
        bridge['periods'] = [dict(period='2021-12-31', basis='FY', scope='CONTINUING',
            operating_cash_flow=120e6, capex=20e6, preferred_cash_paid=10e6, net_income_common=138e6,
            source_urls=bridge['source_urls'])]
        facts['valuation_input_conflicts'] = [dict(code='DISPOSED_BUSINESS_IN_CYCLE_PROXY',
            reason='Current provider scope has not been reconciled.', detected_at='2026-11-01')]
        result = calculate(facts)
        self.assertEqual(result['valuation_input_conflicts'], facts['valuation_input_conflicts'])


class InputGapsAndDisplay(unittest.TestCase):
    def test_engine_conflicts_are_translated_and_recorded_ones_stay_source_text(self):
        tk = CommonEquityBasis.disposal(ticker_fixture(), separated=False)
        result = calculate(live_analysis.extract(tk, 'UNREGISTERED', as_of=ASOF))
        self.assertEqual(result['valuation_input_conflicts'][0]['origin'], 'ENGINE')
        html = ('<html><body>' + opportunity_view.conflicts(
            'TEST', dict(valuation_input_conflicts=result['valuation_input_conflicts'])) + '</body></html>')
        self.assertNotIn('review-input-conflicts', html)
        self.assertEqual(i18n.translation_gaps(html), [])
        self.assertIn('Geschäftsumfang', i18n.localize(html, 'de'))

    def test_input_gaps_name_stale_issuer_bridges_and_blocked_valuations(self):
        reviews = source_review.load()
        rows = {'OXY': dict(dynamic_analysis=dict(financial_period='2026-09-30', basis='TTM',
                                                  valuation_input_conflicts=[],
                                                  common_equity_basis=dict(current_window_open=['open']))),
                'PG': dict(dynamic_analysis=dict(financial_period='2026-09-30', basis='TTM',
                                                 valuation_input_conflicts=[])),
                'SMCI': dict(dynamic_analysis=dict(financial_period='2026-09-30', basis='TTM',
                    valuation_input_conflicts=[dict(code='COMMON_EQUITY_CLAIMS_OMITTED', reason='Missing.')]))}
        with patch.object(engine, 'DATA', rows):
            gaps = engine.input_gaps(reviews)
            box = engine.input_gap_box(gaps)
        self.assertEqual(sorted(gaps), ['OXY', 'SMCI'])       # PG's bridge covers its current window
        self.assertFalse(gaps['OXY']['issuer_bridge_current'])
        self.assertIn('2026-06-30 TTM', gaps['OXY']['issuer_bridge_windows'])
        self.assertEqual(gaps['SMCI']['conflicts'], ['COMMON_EQUITY_CLAIMS_OMITTED'])
        self.assertEqual(i18n.translation_gaps('<html><body>' + box + '</body></html>'), [])


if __name__ == '__main__':
    unittest.main()
