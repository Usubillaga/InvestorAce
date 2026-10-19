"""Market-wide scan contracts. Offline: SEC and Yahoo are replaced by fixtures."""
import copy
import json
import unittest
from datetime import date, datetime, timezone

import autoscore
import engine
import market_universe as mu


TODAY = date(2026, 10, 18)
NOW = datetime(2026, 10, 18, 7, 0, tzinfo=timezone.utc)


def fact(start, end, val, filed='2026-08-01', accn='0000000001-26-000010', form='10-Q'):
    item = dict(end=end, val=val, filed=filed, accn=accn, form=form)
    if start is not None:
        item['start'] = start
    return item


def facts_doc(us_gaap, dei=None):
    doc = {'facts': {'us-gaap': {}, 'dei': {}}}
    for tag, (unit, items) in us_gaap.items():
        doc['facts']['us-gaap'][tag] = {'units': {unit: items}}
    for tag, (unit, items) in (dei or {}).items():
        doc['facts']['dei'][tag] = {'units': {unit: items}}
    return doc


def calendar_company():
    """FY = calendar year; latest 10-Q is H1 2026."""
    def flow(fy24, fy25, h124, h125, h126):
        return ('USD', [fact('2024-01-01', '2024-12-31', fy24, '2025-02-10', '0000000001-25-000002', '10-K'),
                        fact('2025-01-01', '2025-12-31', fy25, '2026-02-10', '0000000001-26-000002', '10-K'),
                        fact('2024-01-01', '2024-06-30', h124, '2025-08-01'),
                        fact('2025-01-01', '2025-06-30', h125),
                        fact('2026-01-01', '2026-06-30', h126)])
    revenue = flow(8000e6, 10000e6, 3700e6, 4600e6, 5600e6)
    revenue[1].append(fact('2026-04-01', '2026-06-30', 2900e6))   # a 3-month fact must not confuse YTD
    return facts_doc({
        'Revenues': revenue,
        'OperatingIncomeLoss': flow(2000e6, 2500e6, 900e6, 1100e6, 1500e6),
        'NetCashProvidedByUsedInOperatingActivities': flow(2600e6, 3000e6, 1200e6, 1400e6, 1700e6),
        'PaymentsToAcquirePropertyPlantAndEquipment': flow(450e6, 500e6, 220e6, 250e6, 300e6),
        'DepreciationDepletionAndAmortization': flow(380e6, 400e6, 190e6, 200e6, 220e6),
        'PaymentsOfDividends': flow(280e6, 300e6, 140e6, 150e6, 160e6),
        'WeightedAverageNumberOfDilutedSharesOutstanding': ('shares', [
            fact('2025-04-01', '2025-06-30', 100e6), fact('2026-04-01', '2026-06-30', 98e6),
            fact('2025-01-01', '2025-12-31', 99e6, '2026-02-10')]),
        'LongTermDebt': ('USD', [fact(None, '2026-06-30', 3000e6), fact(None, '2025-12-31', 3500e6)]),
        'ShortTermBorrowings': ('USD', [fact(None, '2026-06-30', 200e6)]),
        'CashAndCashEquivalentsAtCarryingValue': ('USD', [fact(None, '2026-06-30', 1000e6),
                                                          fact(None, '2025-12-31', 900e6)]),
        'ShortTermInvestments': ('USD', [fact(None, '2026-06-30', 500e6)]),
    }, dei={'EntityCommonStockSharesOutstanding': ('shares', [fact(None, '2026-07-25', 97e6)])})


class Helpers(unittest.TestCase):
    def test_bands_and_weights_cannot_drift_from_autoscore_and_engine(self):
        for name, table in mu._FALLBACK_BANDS.items():
            self.assertEqual(getattr(autoscore, name), table, name)
        self.assertEqual(mu.WEIGHTS, engine.W)
        import market_scanner
        self.assertEqual(mu.BANDS, market_scanner.BANDS)
        for value in (10, 50, 99.9, 100, 250):
            self.assertEqual(mu.priced_in(value), autoscore.priced_in_from_cover(value))

    def test_universe_keeps_one_primary_listing_per_cik(self):
        rows = mu.parse_universe({'fields': ['cik', 'name', 'ticker', 'exchange'], 'data': [
            [1, 'Alpha', 'ALFA', 'Nasdaq'], [1, 'Alpha', 'ALFAW', 'Nasdaq'], [2, 'Otc', 'OTCX', 'OTC'],
            [3, 'Berk', 'BRK.B', 'NYSE'], [4, 'Bad', '<script>', 'NYSE'], [5, 'None', None, 'NYSE']]})
        self.assertEqual([(r['ticker'], r['yahoo']) for r in rows], [('ALFA', 'ALFA'), ('BRK.B', 'BRK-B')])
        with self.assertRaises(ValueError):
            mu.parse_universe({'fields': ['a'], 'data': []})

    def test_sic_sectors_and_financial_exclusion(self):
        self.assertEqual(mu.sector_from_sic(7372), 'Software')
        self.assertEqual(mu.sector_from_sic(3674), 'Semis')
        self.assertEqual(mu.sector_from_sic(2834), 'Pharma')
        self.assertEqual(mu.sector_from_sic(3841), 'MedTech')
        self.assertEqual(mu.sector_from_sic(None), 'Unbekannt')
        for sic in (6022, 6324, 6798):
            self.assertTrue(mu.is_financial(sic))
            self.assertEqual(mu.sector_from_sic(sic), 'Financials')
        self.assertFalse(mu.is_financial(7372))
        for _, _, label in mu.SIC_SECTORS:
            self.assertIn(label, engine.AFF['GOLDILOCKS'], label)   # regime fit knows every sector

    def test_quarter_ends_leave_time_for_filings(self):
        self.assertEqual(mu.recent_quarter_ends(TODAY), [date(2026, 6, 30), date(2026, 3, 31)])
        self.assertEqual(mu.recent_quarter_ends(date(2026, 2, 20)), [date(2025, 12, 31), date(2025, 9, 30)])
        self.assertEqual(mu.quarter_label(date(2026, 6, 30)), 'CY2026Q2I')

    def test_net_debt_never_double_counts_current_debt(self):
        values = dict(LongTermDebtNoncurrent=900, DebtCurrent=150, ShortTermBorrowings=100,
                      CashAndCashEquivalentsAtCarryingValue=200)
        get = lambda tags: next((values[t] for t in tags if t in values), None)   # noqa: E731
        net, debt, cash, flags = mu.net_debt_from(get)
        self.assertEqual((net, debt, cash, flags), (850, 1050, 200, []))   # DebtCurrent includes borrowings
        values = dict(LongTermDebt=1000, ShortTermBorrowings=100, CommercialPaper=50,
                      CashAndCashEquivalentsAtCarryingValue=200, MarketableSecuritiesCurrent=30)
        self.assertEqual(mu.net_debt_from(get)[:3], (920, 1150, 230))
        values = dict(CashAndCashEquivalentsAtCarryingValue=200)
        self.assertEqual(mu.net_debt_from(get), (None, None, 200, ['DEBT_NOT_TAGGED']))

    def test_partial_debt_is_not_a_complete_balance_sheet(self):
        for values in (dict(LongTermDebtNoncurrent=900), dict(DebtCurrent=150)):
            values['CashAndCashEquivalentsAtCarryingValue'] = 200
            get = lambda tags: next((values[t] for t in tags if t in values), None)  # noqa: E731
            net, debt, cash, flags = mu.net_debt_from(get)
            self.assertIsNone(net)
            self.assertIsNone(debt)
            self.assertEqual(cash, 200)
            self.assertIn('DEBT_PARTIAL', flags)


class CompanyFacts(unittest.TestCase):
    def test_ttm_is_fiscal_year_plus_ytd_minus_prior_ytd(self):
        m = mu.company_metrics(calendar_company(), TODAY)
        self.assertEqual(m['basis'], 'TTM')
        self.assertEqual(m['period_end'], '2026-06-30')
        self.assertAlmostEqual(m['revenue'], 11000e6)
        self.assertAlmostEqual(m['revenue_prior'], 8900e6)          # 8000 + 4600 - 3700
        self.assertEqual(m['growth_basis'], 'TTM')
        self.assertAlmostEqual(m['operating_income'], 2900e6)
        self.assertAlmostEqual(m['fcf'], 3300e6 - 550e6)
        self.assertAlmostEqual(m['depreciation'], 420e6)
        self.assertAlmostEqual(m['dividends'], 310e6)
        self.assertEqual((m['shares'], m['shares_basis']), (97e6, 'COVER_PAGE'))
        self.assertAlmostEqual(m['share_change_pct'], -2.0)
        self.assertEqual(m['balance_date'], '2026-06-30')
        self.assertAlmostEqual(m['net_debt'], 3000e6 + 200e6 - 1000e6 - 500e6)
        self.assertEqual(m['accns'], ['0000000001-26-000002', '0000000001-26-000010'])
        self.assertEqual(m['flags'], [])

    def test_restated_comparatives_replace_older_filings(self):
        doc = calendar_company()
        doc['facts']['us-gaap']['Revenues']['units']['USD'].append(
            fact('2025-01-01', '2025-06-30', 4500e6, filed='2026-08-15'))   # later restatement
        self.assertAlmostEqual(mu.company_metrics(doc, TODAY)['revenue'], 11100e6)

    def test_future_and_undated_filings_do_not_replace_available_facts(self):
        doc = calendar_company()
        items = doc['facts']['us-gaap']['Revenues']['units']['USD']
        items.append(fact('2025-01-01', '2025-06-30', 1, filed='2026-10-19'))
        items.append(fact('2025-01-01', '2025-06-30', 2, filed=None))
        self.assertAlmostEqual(mu.company_metrics(doc, TODAY)['revenue'], 11000e6)

    def test_non_calendar_fiscal_year_uses_its_own_windows(self):
        def flow(fy24, fy25, ytd24, ytd25, ytd26):
            return ('USD', [fact('2023-10-01', '2024-09-28', fy24, '2024-11-01'),
                            fact('2024-09-29', '2025-09-27', fy25, '2025-10-31'),
                            fact('2023-10-01', '2024-06-29', ytd24, '2024-08-02'),
                            fact('2024-09-29', '2025-06-28', ytd25, '2025-08-01'),
                            fact('2025-09-28', '2026-06-27', ytd26, '2026-07-31')])
        doc = facts_doc({
            'RevenueFromContractWithCustomerExcludingAssessedTax': flow(380, 400, 285, 300, 320),
            'OperatingIncomeLoss': flow(110, 120, 80, 90, 100),
            'NetCashProvidedByUsedInOperatingActivities': flow(100, 110, 70, 80, 90),
            'PaymentsToAcquirePropertyPlantAndEquipment': flow(10, 11, 7, 8, 9),
            'WeightedAverageNumberOfDilutedSharesOutstanding': ('shares', [
                fact('2025-03-30', '2025-06-28', 15.0), fact('2026-03-29', '2026-06-27', 14.7)]),
            'CashAndCashEquivalentsAtCarryingValue': ('USD', [fact(None, '2026-06-27', 30)]),
        })
        m = mu.company_metrics(doc, TODAY)
        self.assertEqual((m['basis'], m['period_end']), ('TTM', '2026-06-27'))
        self.assertAlmostEqual(m['revenue'], 420)          # 400 + 320 - 300
        self.assertAlmostEqual(m['revenue_prior'], 395)    # 380 + 300 - 285
        self.assertAlmostEqual(m['fcf'], (110 + 90 - 80) - (11 + 9 - 8))
        self.assertEqual(m['shares_basis'], 'DILUTED_AVG')
        self.assertIn('DEBT_NOT_TAGGED', m['flags'])

    def test_missing_ytd_capex_moves_every_measure_to_the_fiscal_year(self):
        doc = calendar_company()
        capex = doc['facts']['us-gaap']['PaymentsToAcquirePropertyPlantAndEquipment']['units']['USD']
        capex[:] = [f for f in capex if f['form'] == '10-K']
        m = mu.company_metrics(doc, TODAY)
        self.assertEqual(m['basis'], 'FY')
        self.assertAlmostEqual(m['revenue'], 10000e6)
        self.assertAlmostEqual(m['fcf'], 3000e6 - 500e6)
        self.assertAlmostEqual(m['revenue_prior'], 8000e6)
        self.assertIn('FISCAL_YEAR_ONLY', m['flags'])

    def test_fresh_annual_report_is_not_flagged_as_fiscal_year_only(self):
        doc = calendar_company()
        for tag in doc['facts']['us-gaap'].values():      # as if the 10-K were the latest filing
            for unit in tag['units'].values():
                unit[:] = [f for f in unit if 'start' not in f or f['end'] <= '2025-12-31']
        m = mu.company_metrics(doc, TODAY)
        self.assertEqual((m['basis'], m['period_end']), ('FY', '2025-12-31'))
        self.assertNotIn('FISCAL_YEAR_ONLY', m['flags'])

    def test_capex_uses_the_largest_tag_per_window(self):
        doc = calendar_company()
        flow = lambda fy24, fy25, h124, h125, h126: [   # noqa: E731
            fact('2024-01-01', '2024-12-31', fy24, '2025-02-10', '0000000001-25-000002', '10-K'),
            fact('2025-01-01', '2025-12-31', fy25, '2026-02-10', '0000000001-26-000002', '10-K'),
            fact('2024-01-01', '2024-06-30', h124, '2025-08-01'), fact('2025-01-01', '2025-06-30', h125),
            fact('2026-01-01', '2026-06-30', h126)]
        doc['facts']['us-gaap']['PaymentsToAcquireOilAndGasPropertyAndEquipment'] = {
            'units': {'USD': flow(900e6, 1000e6, 450e6, 500e6, 600e6)}}   # wells, larger than PP&E
        m = mu.company_metrics(doc, TODAY)
        self.assertAlmostEqual(m['capex'], 1100e6)                      # 1000 + 600 - 500
        self.assertAlmostEqual(m['fcf'], 3300e6 - 1100e6)
        self.assertNotIn('CAPEX_NOT_TAGGED', m['flags'])

    def test_untagged_capex_falls_back_to_depreciation_not_zero(self):
        doc = calendar_company()
        del doc['facts']['us-gaap']['PaymentsToAcquirePropertyPlantAndEquipment']
        m = mu.company_metrics(doc, TODAY)
        self.assertAlmostEqual(m['capex'], 420e6)                       # TTM D&A: 400 + 220 - 200
        self.assertAlmostEqual(m['fcf'], 3300e6 - 420e6)
        self.assertIn('CAPEX_NOT_TAGGED', m['flags'])
        del doc['facts']['us-gaap']['DepreciationDepletionAndAmortization']
        m = mu.company_metrics(doc, TODAY)
        self.assertIsNone(m['capex'])
        self.assertIsNone(m['fcf'])
        self.assertIn('CAPEX_AND_DA_MISSING', m['flags'])

    def test_misscaled_diluted_shares_fall_back_to_the_cover_page(self):
        doc = calendar_company()
        shares = doc['facts']['us-gaap']['WeightedAverageNumberOfDilutedSharesOutstanding']['units']['shares']
        for item in shares:
            item['val'] /= 1e6                                           # 98 instead of 98 million
        m = mu.company_metrics(doc, TODAY)
        self.assertEqual((m['shares'], m['shares_basis']), (97e6, 'COVER_PAGE'))
        self.assertIn('SHARES_SCALE_FIXED', m['flags'])
        self.assertAlmostEqual(m['share_change_pct'], -2.0)             # same scale on both sides
        shares[1]['val'] *= 1e6                                         # only the latest corrected
        self.assertIsNone(mu.company_metrics(doc, TODAY)['share_change_pct'])

    def test_company_without_annual_revenue_is_not_guessed(self):
        self.assertIsNone(mu.company_metrics(facts_doc({}), TODAY))


class Scoring(unittest.TestCase):
    def metrics(self):
        return dict(mu.company_metrics(calendar_company(), TODAY), sic=7372)

    def values(self, result):
        return {c['key']: c['value'] for c in result['components']}

    def test_score_matches_engine_arithmetic_for_the_same_categories(self):
        result = mu.score_metrics(self.metrics(), 100.0)
        self.assertEqual([c['value'] for c in result['components']], [8.5, 7.5, 9.0, 8.0, 9.0, 9.5, 9.0, 8.5])
        self.assertAlmostEqual(result['score'], 8.525)   # FCF margin 25 % -> 9.0
        draft = dict(sub=result['sub'], dil=8.5, fcf=2750.0, shares=97.0, price=100.0, r=mu.DISCOUNT)
        self.assertAlmostEqual(engine.score(draft), result['score'])
        self.assertAlmostEqual(sum(c['contribution'] for c in result['components']), result['score'])
        self.assertEqual(mu.model_band(result['score']), 'Strong Buy')

    def test_outliers_are_flagged_not_hidden(self):
        m = dict(self.metrics(), revenue_prior=4000e6, share_change_pct=30.0)
        result = mu.score_metrics(m, 100.0)
        self.assertIn('GROWTH_OUTLIER', result['flags'])                # +175 %, e.g. Micron FY2026
        self.assertIn('SHARES_JUMP', result['flags'])
        self.assertEqual(result['components'][0]['value'], 9.5)       # the band itself is unchanged
        self.assertEqual(mu.implausible(m, result['metrics']), [])

    def test_without_price_there_is_no_score(self):
        result = mu.score_metrics(self.metrics(), None)
        self.assertIsNone(result['score'])
        self.assertIn('NO_PRICE', result['flags'])

    def test_missing_inputs_keep_fixed_weight_bounds_without_default_points(self):
        m = dict(self.metrics(), revenue_prior=None, net_debt=None, share_change_pct=None)
        result = mu.score_metrics(m, 100.0)
        self.assertEqual(len(result['components']), 8)
        self.assertIsNone(result['score'])
        self.assertEqual(result['status'], 'PARTIAL')
        for key in ('g', 'b', 'r', 'd'):
            self.assertIsNone(self.values(result)[key])
            component = next(c for c in result['components'] if c['key'] == key)
            self.assertIsNone(component['contribution'])
        self.assertAlmostEqual(result['coverage_weight'], .6)
        subtotal = sum(c['contribution'] for c in result['components'] if c['contribution'] is not None)
        self.assertAlmostEqual(result['selection_score'], subtotal)
        self.assertAlmostEqual(result['score_bounds']['lower'], subtotal)
        self.assertAlmostEqual(result['score_bounds']['upper'], subtotal + 4)

    def test_legacy_flags_invalidate_cached_numeric_values(self):
        cases = {
            'DEBT_NOT_TAGGED': ('b',), 'BALANCE_DEFAULT': ('b',),
            'CAPEX_AND_DA_MISSING': ('c', 'v', 'pr'),
            'CAPEX_NOT_TAGGED': ('c', 'v', 'pr'),
            'SHARES_DILUTED_AVG': ('v', 'pr', 'r'),
            'FOREIGN_FILER': ('v', 'pr', 'r'),
            'OPERATING_INCOME_PROXY': ('p', 'b'),
        }
        for flag, missing in cases.items():
            with self.subTest(flag=flag):
                result = mu.score_metrics(dict(self.metrics(), flags=[flag]), 100)
                self.assertIsNone(result['score'])
                for key in missing:
                    self.assertIsNone(self.values(result)[key])

    def test_missing_depreciation_does_not_assume_zero_for_ebitda(self):
        result = mu.score_metrics(dict(self.metrics(), depreciation=None), 100)
        self.assertIsNone(result['metrics']['ebitda'])
        self.assertIsNone(self.values(result)['b'])

    def test_legacy_zero_dividends_are_unknown_without_a_verified_tag(self):
        m = dict(self.metrics(), dividends=0, share_change_pct=-2)
        m.pop('dividends_verified', None)
        result = mu.score_metrics(m, 100)
        self.assertIsNone(result['metrics']['dividend_yield_pct'])
        self.assertIsNone(self.values(result)['r'])
        self.assertIsNone(result['score'])
        self.assertIn('DIVIDENDS_NOT_TAGGED', result['flags'])
        verified = mu.score_metrics(dict(m, dividends_verified=True), 100)
        self.assertEqual(verified['metrics']['dividend_yield_pct'], 0)
        self.assertIsNotNone(self.values(verified)['r'])

    def test_saturated_shareholder_return_uses_a_lower_bound_without_inventing_dividends(self):
        m = dict(self.metrics(), dividends=None, share_change_pct=-6.74)
        result = mu.score_metrics(m, 100)
        returns = next(c for c in result['components'] if c['key'] == 'r')
        self.assertEqual(returns['value'], 9.0)
        self.assertEqual(returns['input'], 6.74)
        self.assertEqual(returns['input_basis'], 'SATURATED_LOWER_BOUND')
        self.assertIsNotNone(returns['reason'])
        self.assertIsNone(result['metrics']['dividend_yield_pct'])
        for payout in (0, 100e6, 1e9):
            known = mu.score_metrics(dict(m, dividends=payout, dividends_verified=True), 100)
            self.assertEqual(self.values(known)['r'], returns['value'])
        self.assertIsNone(self.values(mu.score_metrics(dict(m, dividends=-1), 100))['r'])
        self.assertIsNone(self.values(mu.score_metrics(dict(m, flags=['FOREIGN_FILER']), 100))['r'])

    def test_unknown_sic_retains_analysis_but_blocks_valuation(self):
        result = mu.score_metrics(dict(self.metrics(), sic=None), 100)
        self.assertIsNone(result['score'])
        self.assertIsNone(self.values(result)['v'])
        self.assertIsNone(self.values(result)['pr'])
        self.assertIsNotNone(self.values(result)['g'])
        self.assertIn('CLASSIFICATION_MISSING', result['flags'])

    def test_producers_need_midcycle_including_fertilizer(self):
        for sic in (1040, 1221, 1311, 2911, 2870, 2873, 2879):
            with self.subTest(sic=sic):
                result = mu.score_metrics(dict(self.metrics(), sic=sic), 100)
                self.assertEqual(result['valuation_status'], 'PENDING_MIDCYCLE')
                self.assertIsNone(self.values(result)['v'])
                self.assertIsNone(self.values(result)['pr'])
                self.assertIsNotNone(self.values(result)['c'])
                self.assertIsNone(result['metrics']['ngv_per_share'])

    def test_verified_normalization_clears_producer_without_changing_reported_cashgen(self):
        m = dict(self.metrics(), sic=1040, normalized_fcf=0, normalization_status='VERIFIED',
                 normalization_sources=['https://www.sec.gov/Archives/edgar/data/1/filing.htm'])
        result = mu.score_metrics(m, 100)
        self.assertEqual(result['valuation_status'], 'VERIFIED_NORMALIZED_FCF')
        self.assertIsNotNone(result['score'])
        self.assertEqual(result['metrics']['ngv_per_share'], 0)
        self.assertEqual(result['metrics']['cover_pct'], 0)
        self.assertEqual(self.values(result)['c'], 9.0)
        self.assertEqual(self.values(result)['v'], 1.5)
        for sources in ([], ['TODO']):
            result = mu.score_metrics(dict(m, normalization_sources=sources), 100)
            self.assertIsNone(self.values(result)['v'])

    def test_reported_fcf_is_explicitly_a_discount_rate_scenario(self):
        result = mu.score_metrics(self.metrics(), 100)
        self.assertEqual(result['valuation_status'], 'SCENARIO_REPORTED_FCF')
        self.assertEqual(result['status'], 'COMPLETE')
        self.assertAlmostEqual(result['coverage_weight'], 1)
        self.assertAlmostEqual(result['selection_score'], result['score'])

    def test_dated_denomination_and_ads_bridge_restore_only_supported_valuation(self):
        m = dict(self.metrics(), flags=['SHARES_DILUTED_AVG', 'FOREIGN_FILER'],
                 denominator_status='VERIFIED', denominator_date='2026-07-25',
                 denominator_sources=['https://www.sec.gov/Archives/edgar/data/1/filing.htm'],
                 valuation_shares=97e6, ads_status='VERIFIED', ads_ratio=2,
                 ads_sources=['https://www.sec.gov/Archives/edgar/data/1/depositary.htm'])
        result = mu.score_metrics(m, 100)
        self.assertIsNotNone(self.values(result)['v'])
        self.assertAlmostEqual(result['metrics']['market_cap'], 100 * 97e6 / 2)
        self.assertIsNotNone(result['score'])
        result = mu.score_metrics(dict(m, denominator_date=None), 100)
        self.assertIsNone(self.values(result)['v'])

    def test_regime_fit_uses_the_unchanged_engine_formula(self):
        m = dict(self.metrics(), price=100.0, sector='Software')
        result = mu.score_metrics(m, 100.0)
        fit = mu.regime_fit(m, result['sub'])
        draft = dict(fcf=m['fcf'] / 1e6, shares=m['shares'] / 1e6, r=mu.DISCOUNT, price=100.0,
                     sector='Software', sub=result['sub'])
        self.assertEqual(fit, engine.regime_scores(draft))
        self.assertEqual(set(fit), set(engine.REGIMES))


class FakeSec:
    def __init__(self, routes):
        self.routes, self.calls, self.failures = routes, 0, 0

    def get_json(self, url):
        self.calls += 1
        if url in self.routes:
            return copy.deepcopy(self.routes[url])
        if '/frames/' in url:
            return {'data': [{'cik': 999, 'val': 1, 'end': '2025-12-31', 'accn': 'x'}]}
        return None


def frame(rows):
    return {'data': [dict(cik=cik, val=val, start=start, end=end, accn=f'000000000{cik}-26-000001')
                     for cik, val, start, end in rows]}


def market_routes():
    y = ('2025-01-01', '2025-12-31')
    p = ('2024-01-01', '2024-12-31')
    url = mu.frame_url
    routes = {
        mu.TICKERS_URL: {'fields': ['cik', 'name', 'ticker', 'exchange'], 'data': [
            [1, 'Alpha Corp', 'ALFA', 'Nasdaq'], [1, 'Alpha Corp', 'ALFAW', 'Nasdaq'],
            [2, 'Bank Co', 'BNKX', 'NYSE'], [3, 'Small Co', 'SMOL', 'NYSE'],
            [4, 'Loss Co', 'LOSS', 'NYSE'], [5, 'Otc Co', 'OTCX', 'OTC'], [6, 'Model Co', 'ADBE', 'Nasdaq']]},
        url('Revenues', 'USD', 'CY2025'): frame([(1, 10000e6, *y), (2, 5000e6, *y), (3, 500e6, *y),
                                                 (4, 3000e6, *y), (6, 20000e6, *y)]),
        url('Revenues', 'USD', 'CY2024'): frame([(1, 8000e6, *p), (2, 4800e6, *p), (6, 18000e6, *p)]),
        url('OperatingIncomeLoss', 'USD', 'CY2025'): frame([(1, 2500e6, *y), (2, 1500e6, *y), (3, 50e6, *y),
                                                            (4, -10e6, *y), (6, 7000e6, *y)]),
        url('NetCashProvidedByUsedInOperatingActivities', 'USD', 'CY2025'): frame(
            [(1, 3000e6, *y), (2, 2000e6, *y), (3, 60e6, *y), (4, 100e6, *y), (6, 8000e6, *y)]),
        url('PaymentsToAcquirePropertyPlantAndEquipment', 'USD', 'CY2025'): frame(
            [(1, 500e6, *y), (2, 100e6, *y), (6, 300e6, *y)]),
        url('WeightedAverageNumberOfDilutedSharesOutstanding', 'shares', 'CY2025'): frame(
            [(1, 99e6, *y), (2, 50e6, *y), (3, 10e6, *y), (4, 10e6, *y), (6, 420e6, *y)]),
        url('CashAndCashEquivalentsAtCarryingValue', 'USD', 'CY2026Q2I'): frame(
            [(1, 1000e6, None, '2026-06-30'), (2, 9000e6, None, '2026-06-30'), (6, 5000e6, None, '2026-06-30')]),
        mu.submissions_url(1): {'sic': '7372', 'sicDescription': 'Services-Prepackaged Software',
                                'name': 'ALPHA CORP', 'tickers': ['ALFA']},
        mu.submissions_url(2): {'sic': '6022', 'sicDescription': 'State commercial banks', 'name': 'BANK CO'},
        mu.submissions_url(6): {'sic': '7372', 'sicDescription': 'Services-Prepackaged Software',
                                'name': 'MODEL CO'},
        mu.companyfacts_url(1): calendar_company(),
    }
    return routes


def fake_prices(symbols):
    table = {'ALFA': 100.0, 'BNKX': 40.0, 'ADBE': 400.0}
    return {s: dict(price=table[s], date='2026-10-16') for s in symbols if s in table}


class EndToEnd(unittest.TestCase):
    def run_scan(self, **kwargs):
        return mu.run(sec=FakeSec(market_routes()), prices=fake_prices, universe={'ADBE'},
                      today=TODAY, now=NOW, log=lambda *_: None, **kwargs)

    def test_funnel_filters_prices_and_excludes_financials(self):
        payload = self.run_scan()
        counts = [stage['count'] for stage in payload['funnel']]
        self.assertEqual(counts, [5, 3, 3, 2, 2, 2])
        self.assertEqual(payload['excluded_financials'], 1)
        self.assertEqual(payload['implausible'], [])
        self.assertEqual(payload['rejected'], {'REVENUE_BELOW_1BN': 1, 'NO_OPERATING_PROFIT': 1})
        tickers = [c['ticker'] for c in payload['candidates']]
        self.assertNotIn('BNKX', tickers)
        alpha = next(c for c in payload['candidates'] if c['ticker'] == 'ALFA')
        self.assertEqual((alpha['source'], alpha['basis'], alpha['sector']), ('companyfacts', 'TTM', 'Software'))
        self.assertAlmostEqual(alpha['score'], 8.525)
        self.assertFalse(alpha['in_universe'])
        self.assertEqual(alpha['price_date'], '2026-10-16')
        self.assertEqual(alpha['status'], 'COMPLETE')
        self.assertIn('input_metadata', alpha)
        self.assertTrue(all(s['url'].startswith('https://') for s in alpha['sources']))
        model = next(c for c in payload['candidates'] if c['ticker'] == 'ADBE')
        self.assertTrue(model['in_universe'])
        self.assertIn('FRAMES_ONLY', model['flags'])
        self.assertEqual(model['basis'], 'FY')
        self.assertEqual(model['status'], 'PARTIAL')
        self.assertIsNone(model['score'])
        self.assertIsNone(model['band'])
        self.assertEqual(tickers[0], 'ALFA')
        self.assertEqual(mu.validate_payload(payload, now=NOW), [])
        json.dumps(payload, allow_nan=False)

    def test_shortlist_and_keep_limits(self):
        payload = self.run_scan(shortlist=1, keep=1)
        self.assertEqual(len(payload['candidates']), 1)

    def test_financials_do_not_take_shortlist_places(self):
        # Put the bank first on supported growth/profit/cash contributions. Two places must
        # go to the two non-financials; the bank is skipped before companyfacts.
        routes = market_routes()
        prior = routes[mu.frame_url('Revenues', 'USD', 'CY2024')]['data']
        next(item for item in prior if item['cik'] == 2)['val'] = 1000e6
        sec = FakeSec(routes)
        seen = []
        original = sec.get_json
        sec.get_json = lambda url: seen.append(url) or original(url)
        payload = mu.run(sec=sec, prices=fake_prices, universe={'ADBE'}, today=TODAY, now=NOW,
                         log=lambda *_: None, shortlist=2)
        self.assertEqual(sorted(c['ticker'] for c in payload['candidates']), ['ADBE', 'ALFA'])
        self.assertEqual(payload['excluded_financials'], 1)
        self.assertIn(mu.submissions_url(2), seen)          # considered for the shortlist ...
        self.assertNotIn(mu.companyfacts_url(2), seen)      # ... and skipped as a bank
        self.assertLess(seen.index(mu.submissions_url(2)), seen.index(mu.submissions_url(6)))

    def test_foreign_filer_flag_survives_companyfacts(self):
        routes = market_routes()
        routes[mu.submissions_url(1)]['filings'] = {'recent': {'form': ['6-K', '20-F/A', '6-K']}}
        payload = mu.run(sec=FakeSec(routes), prices=fake_prices, universe=set(), today=TODAY, now=NOW,
                         log=lambda *_: None)
        alpha = next(c for c in payload['candidates'] if c['ticker'] == 'ALFA')
        self.assertEqual(alpha['source'], 'companyfacts')
        self.assertIn('FOREIGN_FILER', alpha['flags'])
        self.assertIn('ADS', alpha['flag_text']['FOREIGN_FILER'])
        model = next(c for c in payload['candidates'] if c['ticker'] == 'ADBE')
        self.assertNotIn('FOREIGN_FILER', model['flags'])

    def test_missing_classification_or_capex_stays_visible_for_source_review(self):
        for missing in ('classification', 'capex'):
            with self.subTest(missing=missing):
                routes = market_routes()
                if missing == 'classification':
                    routes[mu.submissions_url(1)] = {}
                else:
                    facts = routes[mu.companyfacts_url(1)]['facts']['us-gaap']
                    del facts['PaymentsToAcquirePropertyPlantAndEquipment']
                    del facts['DepreciationDepletionAndAmortization']
                payload = mu.run(sec=FakeSec(routes), prices=fake_prices, universe=set(),
                                 today=TODAY, now=NOW, log=lambda *_: None)
                alpha = next(c for c in payload['candidates'] if c['ticker'] == 'ALFA')
                self.assertIsNone(alpha['score'])
                self.assertEqual(alpha['status'], 'PARTIAL')
                self.assertEqual(mu.validate_payload(payload, now=NOW), [])

    def test_future_missing_and_old_quote_dates_are_not_preselected(self):
        for stamp in ('2026-10-19', '2026-10-13', None):
            with self.subTest(stamp=stamp):
                prices = lambda symbols: {s: dict(q, date=stamp) for s, q in fake_prices(symbols).items()}
                payload = mu.run(sec=FakeSec(market_routes()), prices=prices, universe=set(),
                                 today=TODAY, now=NOW, log=lambda *_: None)
                self.assertEqual(payload['candidates'], [])

    def test_implausible_rows_leave_the_ranking_with_reasons(self):
        # Live 2026-10-18: McDonald's tagged 711.1 diluted shares and no usable
        # cover page here, so its FCF yield read 4.5 million percent.
        routes = market_routes()
        doc = routes[mu.companyfacts_url(1)]
        doc['facts']['dei'] = {}
        for item in doc['facts']['us-gaap']['WeightedAverageNumberOfDilutedSharesOutstanding']['units']['shares']:
            item['val'] /= 1e6
        payload = mu.run(sec=FakeSec(routes), prices=fake_prices, universe={'ADBE'}, today=TODAY, now=NOW,
                         log=lambda *_: None)
        self.assertNotIn('ALFA', [c['ticker'] for c in payload['candidates']])
        [aside] = payload['implausible']
        self.assertEqual(aside['ticker'], 'ALFA')
        self.assertTrue(any('Aktienzahl' in r for r in aside['reasons']))
        self.assertTrue(aside['source_url'].startswith('https://data.sec.gov/'))
        self.assertIn('1 unplausibel beiseitegelegt', payload['funnel'][-2]['stage'])
        self.assertEqual(mu.validate_payload(payload, now=NOW), [])
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'latest.json'
            path.write_text(json.dumps(payload), encoding='utf-8')
            self.assertIn('Beiseitegelegt (unplausibel): ALFA', mu.report_markdown(path))
        broken = copy.deepcopy(payload)
        broken['implausible'][0]['source_url'] = 'http://x'
        self.assertTrue(mu.validate_payload(broken, now=NOW))

    def test_annual_form_is_the_latest_annual_report(self):
        doc = {'sic': '3571', 'filings': {'recent': {'form': ['8-K', '10-Q', '10-K/A', '20-F']}}}
        self.assertEqual(mu.parse_submission(doc)['annual_form'], '10-K')
        self.assertIsNone(mu.parse_submission({'sic': '3571'})['annual_form'])

    def test_thin_frames_refuse_to_publish(self):
        class Broken(FakeSec):
            def get_json(self, url):
                return None if '/frames/' in url else super().get_json(url)
        with self.assertRaises(RuntimeError):
            mu.run(sec=Broken(market_routes()), prices=fake_prices, universe=set(), today=TODAY,
                   now=NOW, log=lambda *_: None)


class Validation(unittest.TestCase):
    def payload(self):
        return EndToEnd().run_scan()

    def test_validation_rejects_broken_payloads(self):
        good = self.payload()
        cases = []
        bad = copy.deepcopy(good); bad['candidates'][0]['metrics']['revenue'] = float('nan'); cases.append(bad)   # noqa: E702
        bad = copy.deepcopy(good); bad['candidates'][0]['sources'][0]['url'] = 'http://x'; cases.append(bad)   # noqa: E702
        bad = copy.deepcopy(good); bad['candidates'][0]['band'] = 'Sell'; cases.append(bad)   # noqa: E702
        bad = copy.deepcopy(good); bad['candidates'][0]['score'] = 9.9; bad['candidates'][0]['band'] = 'Strong Buy'; cases.append(bad)   # noqa: E702,E501
        bad = copy.deepcopy(good); bad['generated_at'] = '2026-10-19T09:00:00+00:00'; cases.append(bad)   # noqa: E702
        bad = copy.deepcopy(good); bad['candidates'].append(copy.deepcopy(bad['candidates'][0])); cases.append(bad)   # noqa: E702,E501
        bad = copy.deepcopy(good); bad['schema'] = 'other'; cases.append(bad)   # noqa: E702
        for case in cases:
            with self.subTest(case=case.get('schema')):
                self.assertTrue(mu.validate_payload(case, now=NOW))
        self.assertIn('scan is stale', mu.validate_payload(good, now=datetime(2026, 11, 30, tzinfo=timezone.utc),
                                                           max_age_days=14))

    def test_partial_rows_cannot_be_given_a_fabricated_composite(self):
        good = self.payload()
        partial = next(c for c in good['candidates'] if c['status'] == 'PARTIAL')
        self.assertEqual(mu.validate_payload(good, now=NOW), [])
        partial.update(score=partial['selection_score'], band=mu.model_band(partial['selection_score']))
        self.assertTrue(mu.validate_payload(good, now=NOW))

    def test_legacy_frozen_packet_still_loads_for_guarded_replay(self):
        from pathlib import Path
        packet = json.loads((Path(__file__).parent / 'market-scan/latest.json').read_text())
        self.assertEqual(mu.validate_payload(packet), [])


class Client(unittest.TestCase):
    def test_sec_client_stops_on_403_and_maps_404_to_none(self):
        class Response:
            def __init__(self, status):
                self.status_code = status

            def json(self):
                return {'ok': True}

        class Session:
            def __init__(self, status):
                self.status, self.headers = status, {}

            def get(self, url, timeout):
                return Response(self.status)

        agent = 'InvestorAce Test Owner owner@investorace-test.org'
        self.assertIsNone(mu.SecClient(agent, session=Session(404), rate=1000).get_json('https://x'))
        self.assertEqual(mu.SecClient(agent, session=Session(200), rate=1000).get_json('https://x'), {'ok': True})
        with self.assertRaises(RuntimeError) as refused:
            mu.SecClient(agent, session=Session(403), rate=1000).get_json('https://x')
        self.assertIn('SEC_USER_AGENT', str(refused.exception))
        self.assertNotIn(agent, str(refused.exception))          # the contact never reaches public logs
        client = mu.SecClient(agent, session=Session(200), rate=1000)
        self.assertEqual(client.session.headers['User-Agent'], agent)

    def test_agent_needs_a_real_contact_address(self):
        for bad in (None, '', '   ', 'InvestorAce', 'InvestorAce bot@users.noreply.github.com',
                    'X no-reply@firma.de', 'Sample Company Name AdminContact@samplecompany.com',
                    'InvestorAce Vorname Nachname name@beispiel.de', 'A a@example.com'):
            with self.subTest(agent=bad):
                with self.assertRaises(RuntimeError) as stop:
                    mu.sec_agent(bad)
                self.assertIn('Secrets and variables', str(stop.exception))
        self.assertEqual(mu.sec_agent('  InvestorAce  Ana Ruiz\tana.ruiz@mail.es '),
                         'InvestorAce Ana Ruiz ana.ruiz@mail.es')

    def test_scan_stops_before_any_request_without_agent(self):
        import os
        from unittest import mock
        with mock.patch.dict(os.environ, {'SEC_USER_AGENT': ''}), \
                mock.patch('requests.Session.get', side_effect=AssertionError('network')):
            with self.assertRaises(RuntimeError):
                mu.run(prices=fake_prices, universe=set(), today=TODAY, now=NOW, log=lambda *_: None)


class Report(unittest.TestCase):
    def test_failed_run_never_shows_the_previous_scan(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            scan, log = Path(tmp) / 'latest.json', Path(tmp) / 'scan.log'
            scan.write_text(json.dumps(EndToEnd().run_scan()), encoding='utf-8')
            log.write_text('Marktscan abgebrochen: SEC_USER_AGENT fehlt\n', encoding='utf-8')
            failed = mu.report_markdown(scan, log, 'failure')
            self.assertIn('Kein gültiges Ergebnis', failed)
            self.assertIn('Aktion nötig', failed)
            self.assertNotIn('ALFA', failed)
            ok = mu.report_markdown(scan, log, 'success')
            self.assertIn('ALFA', ok)
            self.assertNotIn('Aktion nötig', ok)


if __name__ == '__main__':
    unittest.main()
