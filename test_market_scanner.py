"""Scanner contracts: evidence gaps cannot become investment ratings."""
import copy
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import market_scanner as scanner


ASOF = datetime(2026, 10, 18, 12, tzinfo=timezone.utc)


def observation():
    row = dict(yf='EX', cur='USD', sector='Software', price=100,
               quote_observed_at='2026-10-16T20:00:00+00:00',
               quote_time_status='DAILY_CLOSE', shares=10, fcf=80)
    diagnostics = dict(valuation_contract=dict(status='DECLARED', issues=[]),
                       score_basis='LIVE_COMPOSITE')
    output = dict(score=7.6, price=100, cover=1.0, ngv=100, cushion=None,
                  diagnostics=diagnostics, regime={'GOLDILOCKS': 80},
                  score_explanation=dict(status='DECOMPOSED', reconciles=True,
                                         total=7.6, components=[]))
    return {'EX': output, '_evidence': dict(captured_at='2026-10-17T12:00:00Z',
             inputs={'EX': row}, model_source_sha256='a' * 64), '_models': {},
            '_source_reviews': dict(as_of='2026-10-17', entries={
                'EX': dict(issuer='Example', listing='EX / USD', valuation=dict(
                    status='SOURCE_CHECKED', reason='Reported cash flow read.',
                    sources=[dict(title='Filing', url='https://example.org/filing')]))})}


class ScannerTests(unittest.TestCase):
    def scan(self, record=None, notes=None):
        return scanner.build_scan(record or observation(), as_of=ASOF, notes=notes)

    def test_bands_match_unrounded_engine_boundaries(self):
        for value, expected in [(0, 'Sell'), (3.4999, 'Sell'), (3.5, 'Hold negativ'),
                                (5.4999, 'Hold negativ'), (5.5, 'Hold positiv'),
                                (6.9999, 'Hold positiv'), (7, 'Buy'), (8.4999, 'Buy'),
                                (8.5, 'Strong Buy'), (10, 'Strong Buy')]:
            with self.subTest(value=value):
                self.assertEqual(scanner.model_band(value), expected)
        for value in (None, True, float('nan'), float('inf'), -1, 10.1):
            self.assertIsNone(scanner.model_band(value))

    def test_source_checked_is_not_completed_cross_review(self):
        result = self.scan()['rows'][0]
        self.assertIsNone(result['model_band'])
        self.assertEqual(result['raw_score'], 7.6)
        self.assertIsNone(result['rating'])
        self.assertEqual(result['review_status'], 'REVIEW_REQUIRED')
        self.assertIn('CROSS_REVIEW_PENDING', [x['code'] for x in result['issues']])

    def test_missing_quote_timestamp_does_not_use_retrieval_time(self):
        record = observation()
        record['_evidence']['inputs']['EX'].update(quote_observed_at=None,
            price_ts='2026-10-18 11:59 UTC', quote_time_status='UNKNOWN')
        row = self.scan(record)['rows'][0]
        self.assertEqual(row['quote_status'], 'TIME_UNKNOWN')
        self.assertIsNone(row['rating'])
        self.assertIsNone(row['valuation']['cover'])
        self.assertIsNone(row['model_score'])
        self.assertEqual(row['raw_score'], 7.6)

    def test_stale_future_and_invalid_quotes_cannot_pass(self):
        for stamp, price, expected in [('2026-10-10T20:00:00Z', 100, 'STALE'),
             ('2026-10-19T20:00:00Z', 100, 'FUTURE'),
             ('2026-10-16T20:00:00Z', None, 'MISSING'),
             ('2026-10-16T20:00:00Z', -1, 'MISSING'),
             ('2026-10-16', 100, 'TIME_UNKNOWN')]:
            record = observation()
            record['_evidence']['inputs']['EX'].update(quote_observed_at=stamp, price=price)
            record['EX']['price'] = price
            with self.subTest(stamp=stamp, price=price):
                row = self.scan(record)['rows'][0]
                self.assertEqual(row['quote_status'], expected)
                self.assertIsNone(row['valuation']['cover'])

    def test_basis_issue_blocks_valuation_and_preserves_model_archive(self):
        record = observation()
        record['EX']['diagnostics']['valuation_contract'].update(
            status='MISMATCH', issues=['FCFE needs cost of equity.'])
        row = self.scan(record)['rows'][0]
        self.assertIsNone(row['valuation']['ngv'])
        self.assertEqual(row['archived_valuation']['ngv'], 100)
        self.assertIn('FCFE needs cost of equity.', [x['message'] for x in row['issues']])

    def test_rank_preserves_score_order_and_does_not_mix_regime_fit(self):
        record = observation()
        record['_evidence']['inputs']['LOW'] = copy.deepcopy(record['_evidence']['inputs']['EX'])
        record['LOW'] = copy.deepcopy(record['EX'])
        record['LOW'].update(score=7.1, regime={'GOLDILOCKS': 100})
        rows = self.scan(record)['rows']
        self.assertEqual([r['ticker'] for r in rows], ['EX', 'LOW'])
        self.assertEqual(rows[1]['regime_fit']['GOLDILOCKS'], 100)
        self.assertEqual(self.scan(record)['universe_count'], 2)

    def test_fixed_total_and_recorded_objections_stay_visible(self):
        record = observation()
        record['EX']['score_explanation']['status'] = 'PUBLISHED_TOTAL'
        notes = dict(schema_version=1, as_of='2026-10-18', entries={'EX': dict(
            issuer='Example', thesis='Research lead.', counterargument='Demand may fall.',
            next_check='Reconcile shares.', sources=[], objections=[dict(
                id='EX-1', severity='major', status='open', message='Shares unresolved.')])})
        row = self.scan(record, notes)['rows'][0]
        self.assertEqual(row['objections'][0]['status'], 'open')
        self.assertIn('FIXED_TOTAL', [x['code'] for x in row['issues']])
        self.assertEqual(row['review_status'], 'REVIEW_REQUIRED')

    def test_no_input_mutation_or_nan_json(self):
        original = observation()
        frozen = copy.deepcopy(original)
        scanner.build_scan(original, as_of=ASOF)
        self.assertEqual(original, frozen)
        json.dumps(self.scan(), allow_nan=False)

    def test_page_has_offline_data_and_does_not_execute_source_text(self):
        record = observation()
        record['_source_reviews']['entries']['EX']['issuer'] = '</script><script>alert(1)</script>'
        html = scanner.render_scan(self.scan(record))
        self.assertNotIn('</script><script>alert(1)</script>', html)
        self.assertIn('id="scanner-data"', html)
        self.assertIn('Hold positiv', html)
        self.assertIn('id="scanner-rows"', html)

    def test_site_export_uses_committed_generation_and_creates_nav(self):
        from unittest.mock import patch
        import weekly_research
        with tempfile.TemporaryDirectory() as tmp:
            root, output = Path(tmp) / 'repo', Path(tmp) / 'public'
            (root / 'weekly-research').mkdir(parents=True)
            (root / 'history').mkdir()
            (root / 'history' / '_current.json').write_text('{}')
            (root / 'weekly-research' / 'config.json').write_text(json.dumps(dict(
                schema_version=1, first_issue_date='2026-10-16', schedule_label='Friday')))
            report = root / 'report.html'
            report.write_text('<!DOCTYPE html><html><body>Verified report</body></html>')
            with patch('evidence.current_build', return_value=dict(
                    report_path=report, record=observation(), manifest={'run_id': 'test'})):
                weekly_research.build_site(root, output, require_committed=True)
            self.assertTrue((output / 'scanner.html').is_file())
            data = json.loads((output / 'scanner.json').read_text())
            self.assertEqual(data['universe_count'], 1)
            self.assertIn('href="scanner.html"', (output / 'index.html').read_text())


def market_payload(generated='2026-10-17T07:00:00+00:00', **candidate):
    """Minimal valid weekly scan (built by hand: this module must not need yfinance)."""
    base = dict(ticker='NEWCO', yahoo='NEWCO', cik=1, name='New Co', exchange='NYSE', sic=7372,
                sic_description='Software', sector='Software', in_universe=False, price=50.0,
                price_date='2026-10-16', currency='USD', basis='TTM', period_start='2025-07-01',
                period_end='2026-06-30', growth_basis='TTM', shares_basis='COVER_PAGE',
                balance_date='2026-06-30', source='companyfacts', metrics=dict(
                    revenue=2e9, revenue_prior=1.8e9, operating_income=600e6,
                    operating_cash_flow=800e6, capex=100e6, fcf=700e6, depreciation=100e6,
                    dividends=10e6, shares=100e6, net_debt=-100e6, debt=200e6, cash=300e6,
                    share_change_pct=-2, market_cap=5e9),
                score=7.5, band='Buy', components=[dict(key='g', label='Growth', value=7.5, weight=1.0,
                                                         contribution=7.5, input=12.0)],
                regime_fit={'REFLATION': 55.0}, flags=[], flag_text={},
                sources=[dict(title='SEC', url='https://data.sec.gov/api/xbrl/companyfacts/CIK0000000001.json')])
    base.update(candidate)
    return dict(schema='market-scan-v1', generated_at=generated, as_of=generated[:10],
                coverage='USA', funnel=[dict(stage='Liste', count=5000)], method={}, rejected={},
                sources={}, candidates=[base])


class MarketSectionTests(unittest.TestCase):
    def audited_market(self, ticker='EX'):
        raw = dict(revenue=2e9, revenue_prior=1.8e9, operating_income=600e6,
            operating_cash_flow=800e6, capex=100e6, fcf=700e6, depreciation=100e6,
            dividends=10e6, shares=100e6, net_debt=-100e6, debt=200e6, cash=300e6,
            share_change_pct=-2)
        import market_universe
        calc = market_universe.score_metrics(dict(raw, sic=7372), 50)
        return market_payload(ticker=ticker, yahoo=ticker, metrics=raw, score=calc['score'],
            band=market_universe.model_band(calc['score']), components=calc['components'])

    def test_cache_scores_are_recomputed_from_inputs(self):
        doc = self.audited_market()
        # A self-consistent stored total is still not a recalculation.
        doc['candidates'][0].update(score=1, band='Sell', components=[])
        row = scanner.build_scan(observation(), as_of=ASOF, market=doc)['market']['candidates'][0]
        self.assertGreater(row['score'], 7)
        self.assertEqual(row['archived_screen']['score'], 1)
        self.assertEqual(len(row['components']), 8)

    def test_old_quote_suppresses_current_valuation_but_keeps_research(self):
        doc = self.audited_market()
        doc['candidates'][0]['price_date'] = '2026-10-10'
        row = scanner.build_scan(observation(), as_of=ASOF, market=doc)['market']['candidates'][0]
        self.assertEqual(row['quote_status'], 'STALE')
        self.assertIsNone(row['score'])
        self.assertIsNone(row['band'])
        self.assertIsNone(row['metrics']['fcf_yield_pct'])
        self.assertIsNotNone(row['components'][0]['value'])
        self.assertFalse(row['rank_eligible'])
        self.assertIsNotNone(row['archived_screen']['score'])

    def test_future_quote_blocks_one_name_without_discarding_other_names(self):
        doc = self.audited_market()
        other = copy.deepcopy(doc['candidates'][0])
        other.update(ticker='OTHER', price_date='2026-10-19')
        doc['candidates'].append(other)
        section = scanner.build_scan(observation(), as_of=ASOF, market=doc)['market']
        self.assertEqual(len(section['candidates']), 2)
        by = {c['ticker']: c for c in section['candidates']}
        self.assertIsNotNone(by['EX']['score'])
        self.assertIsNone(by['OTHER']['score'])
        self.assertEqual(by['OTHER']['quote_status'], 'FUTURE')

    def test_unknown_or_invalid_quote_blocks_only_its_issuer(self):
        for change in (dict(price_date=None), dict(price_date='bad'), dict(price=-1), dict(price=None)):
            doc = self.audited_market()
            other = copy.deepcopy(doc['candidates'][0])
            other.update(ticker='OTHER', yahoo='OTHER', **change)
            doc['candidates'].append(other)
            section = scanner.build_scan(observation(), as_of=ASOF, market=doc)['market']
            self.assertEqual(len(section['candidates']), 2)
            by = {c['ticker']: c for c in section['candidates']}
            self.assertIsNotNone(by['EX']['score'])
            self.assertIsNone(by['OTHER']['score'])

    def test_missing_debt_and_ads_stay_visible_without_a_current_band(self):
        for flag in ('DEBT_NOT_TAGGED', 'FOREIGN_FILER'):
            doc = self.audited_market()
            doc['candidates'][0]['flags'] = [flag]
            row = scanner.build_scan(observation(), as_of=ASOF, market=doc)['market']['candidates'][0]
            self.assertIsNone(row['score'])
            self.assertIsNone(row['band'])
            self.assertTrue(row['issues'])
            self.assertLess(row['coverage_weight'], 1)

    def test_scenario_is_not_a_verified_rating_and_fixed_weights_remain(self):
        row = scanner.build_scan(observation(), as_of=ASOF,
            market=self.audited_market())['market']['candidates'][0]
        self.assertIsNone(row['rating'])
        self.assertEqual(row['review_status'], 'REVIEW_PENDING')
        self.assertEqual([c['weight'] for c in row['components']], [.15,.20,.15,.15,.10,.15,.05,.05])

    def test_refresh_preserves_full_scan_date_and_marks_missing_quote(self):
        doc = self.audited_market()
        old = copy.deepcopy(doc)
        updated = scanner.refresh_market_prices(doc, {}, as_of=ASOF)
        self.assertEqual(updated['generated_at'], old['generated_at'])
        self.assertEqual(doc, old)
        self.assertIsNone(updated['candidates'][0]['score'])
        self.assertIsNone(updated['candidates'][0]['price'])
        self.assertTrue(updated['quote_refresh']['failures'])
        import market_universe
        self.assertEqual(market_universe.validate_payload(updated), [])
        self.assertEqual(updated['candidates'][0]['archived_screen']['price'], 50)

    def test_quote_recovery_clears_prior_failure_without_changing_financial_inputs(self):
        doc = self.audited_market()
        missing = scanner.refresh_market_prices(doc, {}, as_of=ASOF)
        recovered = scanner.refresh_market_prices(missing, {'EX': dict(price=51, date='2026-10-16')}, as_of=ASOF)
        row = recovered['candidates'][0]
        self.assertEqual(row['quote_status'], 'DATED')
        self.assertIsNotNone(row['score'])
        self.assertNotIn('QUOTE_MISSING', row['flags'])
        self.assertNotIn('NO_PRICE', row['flags'])
        self.assertEqual(recovered['generated_at'], doc['generated_at'])
        self.assertEqual(row['archived_screen']['price'], 50)

    def test_refresh_archives_price_before_replacing_it(self):
        doc = self.audited_market()
        updated = scanner.refresh_market_prices(doc, {'EX': dict(price=51, date='2026-10-16')}, as_of=ASOF)
        row = updated['candidates'][0]
        self.assertEqual(row['price'], 51)
        self.assertEqual(row['archived_screen']['price'], 50)
        self.assertEqual(row['archived_screen']['score'], doc['candidates'][0]['score'])

    def test_regime_column_defaults_to_the_engine_reading(self):
        record = observation()
        self.assertIsNone(scanner.build_scan(record, as_of=ASOF)['current_regime'])
        record['_evidence']['macro'] = dict(ok=True, regime='REFLATION')
        self.assertEqual(scanner.build_scan(record, as_of=ASOF)['current_regime'], 'REFLATION')
        record['_evidence']['macro'] = dict(ok=False, regime='REFLATION')
        self.assertIsNone(scanner.build_scan(record, as_of=ASOF)['current_regime'])

    def test_market_scan_states(self):
        record = observation()
        self.assertEqual(scanner.build_scan(record, as_of=ASOF)['market']['status'], 'MISSING')
        ok = scanner.build_scan(record, as_of=ASOF, market=market_payload())['market']
        self.assertEqual((ok['status'], len(ok['candidates'])), ('OK', 1))
        stale = scanner.build_scan(record, as_of=ASOF, market=market_payload('2026-09-20T07:00:00+00:00'))
        self.assertEqual(stale['market']['status'], 'STALE')
        broken = market_payload(); broken['candidates'][0]['band'] = 'Sell'   # noqa: E702
        bad = scanner.build_scan(record, as_of=ASOF, market=broken)['market']
        self.assertEqual((bad['status'], bad['candidates']), ('INVALID', []))
        future = scanner.build_scan(record, as_of=ASOF, market=market_payload('2026-10-20T07:00:00+00:00'))
        self.assertEqual(future['market']['status'], 'INVALID')

    def test_universe_membership_comes_from_the_current_record(self):
        record = observation()
        market = market_payload(ticker='EX', in_universe=False)
        row = scanner.build_scan(record, as_of=ASOF, market=market)['market']['candidates'][0]
        self.assertEqual((row['in_universe'], row['universe_key'], row['universe_score']), (True, 'EX', 7.6))
        self.assertIsNone(row['add_url'])
        new = scanner.build_scan(record, as_of=ASOF, market=market_payload())['market']['candidates'][0]
        self.assertFalse(new['in_universe'])
        self.assertTrue(new['add_url'].startswith('https://github.com/'))
        self.assertIn('add-ticker%3A%20NEWCO', new['add_url'])

    def test_calibration_compares_screening_and_model_scores(self):
        record = observation()
        none = scanner.build_scan(record, as_of=ASOF, market=market_payload())['market']
        self.assertIsNone(none['calibration'])                     # no overlap, no claim
        market = market_payload(ticker='EX', in_universe=False)
        joined = scanner.build_scan(record, as_of=ASOF, market=market)['market']
        row = joined['candidates'][0]
        cal = joined['calibration']
        self.assertEqual(cal['n'], 1)
        self.assertAlmostEqual(cal['mean_diff'], row['score'] - 7.6)
        self.assertEqual(cal['min_diff'], cal['max_diff'])
        self.assertIsNone(scanner.build_scan(record, as_of=ASOF)['market']['calibration'])

    def test_market_rows_never_change_universe_ranking(self):
        record = observation()
        plain = scanner.build_scan(record, as_of=ASOF)
        joined = scanner.build_scan(record, as_of=ASOF, market=market_payload(score=9.9, band='Strong Buy'))
        self.assertEqual(plain['rows'], joined['rows'])

    def test_market_text_is_escaped_in_the_page(self):
        market = market_payload(name='</script><script>alert(1)</script>')
        html = scanner.render_scan(scanner.build_scan(observation(), as_of=ASOF, market=market))
        self.assertNotIn('</script><script>alert(1)</script>', html)
        self.assertIn('NEWCO', html)
        self.assertIn('id="tab-market"', html)

    def test_committed_market_scan_is_valid(self):
        path = Path(scanner.__file__).parent / 'market-scan' / 'latest.json'
        if not path.exists():
            self.skipTest('no committed market scan yet')
        payload = json.loads(path.read_text(encoding='utf-8'))
        import market_universe
        self.assertEqual(market_universe.validate_payload(payload), [])


if __name__ == '__main__':
    unittest.main()
