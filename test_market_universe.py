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
        self.assertEqual(mu.net_debt_from(get), (-200, 0.0, 200, ['DEBT_NOT_TAGGED']))


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

    def test_company_without_annual_revenue_is_not_guessed(self):
        self.assertIsNone(mu.company_metrics(facts_doc({}), TODAY))


class Scoring(unittest.TestCase):
    def metrics(self):
        return mu.company_metrics(calendar_company(), TODAY)

    def test_score_matches_engine_arithmetic_for_the_same_categories(self):
        result = mu.score_metrics(self.metrics(), 100.0)
        self.assertEqual([c['value'] for c in result['components']], [8.5, 7.5, 9.0, 8.0, 9.0, 9.5, 9.0, 8.5])
        self.assertAlmostEqual(result['score'], 8.525)   # FCF margin 25 % -> 9.0
        draft = dict(sub=result['sub'], dil=8.5, fcf=2750.0, shares=97.0, price=100.0, r=mu.DISCOUNT)
        self.assertAlmostEqual(engine.score(draft), result['score'])
        self.assertAlmostEqual(sum(c['contribution'] for c in result['components']), result['score'])
        self.assertEqual(mu.model_band(result['score']), 'Strong Buy')

    def test_without_price_there_is_no_score(self):
        result = mu.score_metrics(self.metrics(), None)
        self.assertIsNone(result['score'])
        self.assertIn('NO_PRICE', result['flags'])

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
        self.assertEqual(counts, [5, 3, 3, 3, 2, 1, 2])
        self.assertEqual(payload['rejected'], {'REVENUE_BELOW_1BN': 1, 'NO_OPERATING_PROFIT': 1})
        tickers = [c['ticker'] for c in payload['candidates']]
        self.assertNotIn('BNKX', tickers)
        alpha = next(c for c in payload['candidates'] if c['ticker'] == 'ALFA')
        self.assertEqual((alpha['source'], alpha['basis'], alpha['sector']), ('companyfacts', 'TTM', 'Software'))
        self.assertAlmostEqual(alpha['score'], 8.525)
        self.assertFalse(alpha['in_universe'])
        self.assertEqual(alpha['price_date'], '2026-10-16')
        self.assertTrue(all(s['url'].startswith('https://') for s in alpha['sources']))
        model = next(c for c in payload['candidates'] if c['ticker'] == 'ADBE')
        self.assertTrue(model['in_universe'])
        self.assertIn('FRAMES_ONLY', model['flags'])
        self.assertEqual(model['basis'], 'FY')
        self.assertEqual(tickers, sorted(tickers, key=lambda t: -next(
            c['score'] for c in payload['candidates'] if c['ticker'] == t)))
        self.assertEqual(mu.validate_payload(payload, now=NOW), [])
        json.dumps(payload, allow_nan=False)

    def test_shortlist_and_keep_limits(self):
        payload = self.run_scan(shortlist=1, keep=1)
        self.assertEqual(len(payload['candidates']), 1)

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

        self.assertIsNone(mu.SecClient(session=Session(404), rate=1000).get_json('https://x'))
        self.assertEqual(mu.SecClient(session=Session(200), rate=1000).get_json('https://x'), {'ok': True})
        with self.assertRaises(RuntimeError):
            mu.SecClient(session=Session(403), rate=1000).get_json('https://x')
        client = mu.SecClient(session=Session(200), rate=1000)
        self.assertIn('@', client.session.headers['User-Agent'])


if __name__ == '__main__':
    unittest.main()
