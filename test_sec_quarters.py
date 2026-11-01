"""A lagging Yahoo quarter is replaced by the newer SEC 10-Q window."""
import copy
import json
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch

import market_universe as mu
import sec_quarters
from test_market_universe import TODAY, calendar_company

YAHOO = dict(financial_period='2026-03-31', last_earnings='2026-08-01', financial_currency='USD',
             inputs=dict(revenue=10e9, fcf=2e9, shares=100e6, net_income=1e9, debt=3e9, cash=1e9, dividends=-3e8),
             source_urls=['https://finance.yahoo.com/quote/X'])


class Client:
    def __init__(self):
        self.urls = []

    def get_json(self, url):
        self.urls.append(url)
        return calendar_company()


class SecQuarterTests(unittest.TestCase):
    def test_lagging_means_older_than_the_last_report_or_simply_old(self):
        self.assertTrue(sec_quarters.lagging(YAHOO, TODAY))
        self.assertFalse(sec_quarters.lagging(dict(YAHOO, financial_period='2026-06-30'), TODAY))
        self.assertTrue(sec_quarters.lagging(dict(YAHOO, last_earnings=None, financial_period='2026-03-31'), date(2026, 9, 1)))
        self.assertFalse(sec_quarters.lagging(dict(YAHOO, last_earnings=None), date(2026, 7, 1)))

    def test_newer_sec_window_replaces_statement_inputs_consistently(self):
        metrics = mu.company_metrics(calendar_company(), TODAY)
        packet = sec_quarters.newer_packet(YAHOO, metrics, 1, TODAY)
        self.assertEqual(packet['financial_period'], '2026-06-30')
        self.assertEqual(packet['financial_source'], 'SEC_COMPANYFACTS')
        self.assertAlmostEqual(packet['inputs']['fcf'], 3300e6 - 550e6)
        self.assertAlmostEqual(packet['inputs']['revenue'], 11000e6)
        self.assertAlmostEqual(packet['inputs']['ebitda'], 2900e6 + 420e6)
        self.assertEqual(packet['inputs']['shares'], 97e6)
        self.assertLess(packet['inputs']['dividends'], 0)
        self.assertEqual(packet['yahoo_financial_period'], '2026-03-31')
        self.assertTrue(any('sec.gov' in u for u in packet['source_urls']))
        self.assertIsNone(sec_quarters.newer_packet(dict(YAHOO, financial_period='2026-06-30'), metrics, 1, TODAY))

    def test_catch_up_skips_current_data_and_foreign_filers(self):
        client = Client()
        self.assertIsNone(sec_quarters.catch_up(dict(YAHOO, financial_period='2026-06-30'), 'X', client, {'X': 1}, TODAY))
        self.assertIsNone(sec_quarters.catch_up(dict(YAHOO, financial_currency='DKK'), 'X', client, {'X': 1}, TODAY))
        self.assertEqual(client.urls, [])
        self.assertEqual(sec_quarters.catch_up(YAHOO, 'X', client, {'X': 1}, TODAY)['financial_period'], '2026-06-30')

    def test_build_uses_sec_for_a_lagging_stock_and_counts_it(self):
        from test_framework_contract import engine
        import live_analysis
        from test_live_analysis import ticker_fixture
        asof = datetime(2026, 10, 18, 12, tzinfo=timezone.utc)
        row = copy.deepcopy(engine.DATA['ZTS']); row.update(price=100., quote_observed_at='2026-10-17T20:00:00Z')
        stored = live_analysis.extract(ticker_fixture(), 'ZTS', as_of=asof)
        stored['earnings'] = dict(date='2026-08-01')
        with tempfile.TemporaryDirectory() as tmp, patch.object(engine, 'DATA', {'ZTS': row}):
            path = Path(tmp) / 'facts.json'
            path.write_text(json.dumps(dict(schema=live_analysis.VERSION, entries={'ZTS': stored})))
            counts = engine.refresh_dynamic_analysis(cache_path=path, as_of=asof,
                ticker_factory=lambda s: ticker_fixture(), sec=dict(client=Client(), ciks={'ZTS': 1}))
            cached = json.loads(path.read_text())['entries']['ZTS']
        self.assertEqual(counts['sec_newer_quarter'], 1)
        self.assertEqual(row['dynamic_analysis']['financial_period'], '2026-06-30')
        self.assertEqual(cached['financial_source'], 'SEC_COMPANYFACTS')


if __name__ == '__main__':
    unittest.main()


class ShareOverrideTests(unittest.TestCase):
    def test_documented_issuer_share_count_replaces_the_provider_count(self):
        from test_framework_contract import engine
        from test_live_analysis import ticker_fixture
        asof = datetime(2026, 10, 18, 12, tzinfo=timezone.utc)
        row = copy.deepcopy(engine.DATA['ZTS']); row.update(price=100., quote_observed_at='2026-10-17T20:00:00Z',
            share_count_override=dict(shares=20e6, asof='2026-08-03', basis='A_AND_B_SHARES_EX_TREASURY'))
        with tempfile.TemporaryDirectory() as tmp, patch.object(engine, 'DATA', {'ZTS': row}):
            engine.refresh_dynamic_analysis(cache_path=Path(tmp) / 'f.json', as_of=asof,
                                            ticker_factory=lambda s: ticker_fixture(shares=10e6))
        self.assertEqual(row['dynamic_analysis']['inputs']['shares'], 20e6)
        self.assertIn('ISSUER_A_AND_B_SHARES_EX_TREASURY', json.dumps(row['dynamic_analysis']))

    def test_nvo_carries_the_issuer_share_count(self):
        from test_framework_contract import engine
        self.assertAlmostEqual(engine.DATA['NVO']['share_count_override']['shares'], 4465e6 - 44249480)


class CatchUpLogTests(unittest.TestCase):
    def test_every_lagging_stock_logs_why_it_did_or_did_not_catch_up(self):
        lines = []
        sec_quarters.catch_up(YAHOO, 'X', Client(), {}, TODAY, log=lines.append)
        sec_quarters.catch_up(dict(YAHOO, financial_period='2026-06-30', last_earnings='2026-10-20'),
                              'X', Client(), {'X': 1}, TODAY, log=lines.append)
        sec_quarters.catch_up(YAHOO, 'X', Client(), {'X': 1}, TODAY, log=lines.append)
        self.assertEqual(lines[0], 'SEC catch-up X: no CIK')
        self.assertIn('SEC not newer: TTM to 2026-06-30 vs stored 2026-06-30', lines[1])
        self.assertTrue(lines[2].startswith('SEC detail X:'))
        self.assertEqual(lines[-1], 'SEC catch-up X: 2026-03-31 -> 2026-06-30 (TTM)')


class DiagnosticTests(unittest.TestCase):
    def test_detail_line_names_last_window_per_element_and_newest_fact(self):
        text = sec_quarters.diagnostics(calendar_company(), TODAY)
        self.assertIn('revenue:Revenues=2026-06-30/', text)
        self.assertIn('ocf:NetCashProvidedByUsedInOperatingActivities=2026-06-30/180d', text)
        self.assertIn('newest us-gaap duration:', text)

    def test_a_lagging_stock_that_cannot_catch_up_logs_the_detail(self):
        lines = []
        sec_quarters.catch_up(dict(YAHOO, financial_period='2026-06-30', last_earnings='2026-10-20'),
                              'X', Client(), {'X': 1}, TODAY, log=lines.append)
        self.assertTrue(lines[1].startswith('SEC detail X: revenue:Revenues=2026-06-30/'))
