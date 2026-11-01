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


def lagging_companyfacts_and_instance():
    """calendar_company without 2026 facts, plus those facts as one 10-Q instance."""
    full = calendar_company()
    old, new = copy.deepcopy(full), []
    for taxonomy, tags in full['facts'].items():
        for name, body in tags.items():
            for unit, items in body['units'].items():
                keep = [f for f in items if not f['end'].startswith('2026')]
                old['facts'][taxonomy][name]['units'][unit] = keep
                new += [(taxonomy, name, unit, f) for f in items if f['end'].startswith('2026')]
                if name != 'Revenues':
                    continue
                # the 10-Q also restates the prior-year comparative window
                new += [(taxonomy, name, unit, f) for f in items if f['end'] == '2025-06-30' and f.get('start') == '2025-01-01']
    contexts, facts = {}, []
    for i, (taxonomy, name, unit, f) in enumerate(new):
        key = (f.get('start'), f['end'])
        cid = contexts.setdefault(key, f'c{len(contexts)}')
        ns = 'us' if taxonomy == 'us-gaap' else 'dei'
        facts.append(f'<{ns}:{name} contextRef="{cid}" unitRef="{"u1" if unit == "USD" else "u2"}" decimals="-6">{f["val"]:.0f}</{ns}:{name}>')
    ctx = ''.join(
        f'<xbrli:context id="{cid}"><xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">1</xbrli:identifier></xbrli:entity>'
        + (f'<xbrli:period><xbrli:startDate>{s}</xbrli:startDate><xbrli:endDate>{e}</xbrli:endDate></xbrli:period>' if s
           else f'<xbrli:period><xbrli:instant>{e}</xbrli:instant></xbrli:period>') + '</xbrli:context>'
        for (s, e), cid in contexts.items())
    ctx += ('<xbrli:context id="dim"><xbrli:entity><xbrli:identifier scheme="x">1</xbrli:identifier><xbrli:segment>'
            '<xbrldi:explicitMember dimension="a">b</xbrldi:explicitMember></xbrli:segment></xbrli:entity>'
            '<xbrli:period><xbrli:startDate>2026-01-01</xbrli:startDate><xbrli:endDate>2026-06-30</xbrli:endDate></xbrli:period></xbrli:context>')
    xml = ('<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance" xmlns:us="http://fasb.org/us-gaap/2026" '
           'xmlns:dei="http://xbrl.sec.gov/dei/2026" xmlns:xbrldi="http://xbrl.org/2006/xbrldi">' + ctx
           + '<xbrli:unit id="u1"><xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unit>'
           + '<xbrli:unit id="u2"><xbrli:measure>xbrli:shares</xbrli:measure></xbrli:unit>' + ''.join(facts)
           + '<us:Revenues contextRef="dim" unitRef="u1" decimals="-6">1</us:Revenues></xbrli:xbrl>')
    return old, xml


class DirectFilingTests(unittest.TestCase):
    def submissions(self):
        return {'filings': {'recent': {'form': ['10-Q', '10-Q', '8-K'],
            'accessionNumber': ['0000000001-26-000020', '0000000001-26-000010', '0000000001-26-000030'],
            'reportDate': ['2026-06-30', '2026-03-31', '2026-07-20'], 'filingDate': ['2026-08-01', '2026-05-01', '2026-07-20'],
            'primaryDocument': ['x-20260630.htm', 'x-20260331.htm', 'x8k.htm']}}}

    def test_newer_filing_picks_the_latest_periodic_report_after_the_stored_period(self):
        f = sec_quarters.newer_filing(self.submissions(), date(2026, 3, 31), TODAY)
        self.assertEqual((f['form'], f['report'].isoformat()), ('10-Q', '2026-06-30'))
        self.assertTrue(sec_quarters.instance_url(1, f).endswith('/1/000000000126000020/x-20260630_htm.xml'))
        self.assertIsNone(sec_quarters.newer_filing(self.submissions(), date(2026, 6, 30), TODAY))

    def test_instance_skips_dimensional_facts_and_keeps_units(self):
        _, xml = lagging_companyfacts_and_instance()
        doc = sec_quarters.parse_instance(xml, dict(form='10-Q', accession='a', filed='2026-08-01'))
        revenue = doc['facts']['us-gaap']['Revenues']['units']['USD']
        self.assertNotIn(1.0, [f['val'] for f in revenue])
        self.assertIn('EntityCommonStockSharesOutstanding', doc['facts']['dei'])
        self.assertIsNone(sec_quarters.parse_instance('<not xml', {}))

    def test_missing_10q_in_companyfacts_is_read_from_the_filing(self):
        old, xml = lagging_companyfacts_and_instance()
        self.assertEqual(mu.company_metrics(old, TODAY)['period_end'], '2025-12-31')
        subs = self.submissions()

        class Direct:
            def get_json(self, url):
                return subs if 'submissions' in url else old

            def get_text(self, url):
                return xml
        lines = []
        packet = sec_quarters.catch_up(YAHOO, 'X', Direct(), {'X': 1}, TODAY, log=lines.append)
        self.assertEqual(packet['financial_period'], '2026-06-30')
        self.assertAlmostEqual(packet['inputs']['revenue'], 11000e6)
        self.assertAlmostEqual(packet['inputs']['fcf'], 3300e6 - 550e6)
        self.assertTrue(any('read 10-Q 2026-06-30' in line and 'directly; usable' in line for line in lines))
