"""Financial comparisons must preserve units, dates, missing data and membership."""
import copy
import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

NOW = datetime(2026, 10, 19, 11, 0, tzinfo=timezone.utc)


def statements():
    dates = pd.to_datetime(['2025-12-31', '2024-12-31', '2023-12-31'])
    income = pd.DataFrame({dates[0]: [1200, 300, 240, -12, 102, 100],
                           dates[1]: [1000, 250, 200, 50, 100, 99],
                           dates[2]: [800, 200, 160, 40, 98, 97]},
                          index=['TotalRevenue', 'GrossProfit', 'OperatingIncome',
                                 'NetIncome', 'DilutedAverageShares', 'BasicAverageShares'])
    balance = pd.DataFrame({dates[0]: [500, 200, 400, 2000],
                            dates[1]: [400, 150, 350, 1800]},
                           index=['TotalDebt', 'CashCashEquivalentsAndShortTermInvestments',
                                  'StockholdersEquity', 'TotalAssets'])
    cash = pd.DataFrame({dates[0]: [200, -50, 30, -10], dates[1]: [150, -40, 25, -8]},
                        index=['OperatingCashFlow', 'CapitalExpenditure',
                               'StockBasedCompensation', 'RepurchaseOfCapitalStock'])
    return income, balance, cash


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('stock_compare'),
                             'The stock comparison feature does not exist yet')
        import stock_compare
        self.compare = stock_compare

    def normalize(self, info=None, income=None, balance=None, cash=None):
        frames = statements()
        return self.compare.normalize('TEST', {'yf': 'TEST', 'cur': 'EUR'},
            info if info is not None else {'longName': 'Test', 'financialCurrency': 'USD',
                 'currency': 'USD', 'sharesOutstanding': 100, 'floatShares': 80},
            income if income is not None else frames[0],
            balance if balance is not None else frames[1],
            cash if cash is not None else frames[2], now=NOW)

    def test_reported_fcf_and_net_debt_use_matching_dates(self):
        row = self.normalize()
        fy = row['annual'][0]
        self.assertEqual(fy['fcf'], 150)
        self.assertEqual(fy['net_debt'], 300)
        self.assertEqual(fy['net_income'], -12)
        self.assertEqual(fy['net_margin'], -1)
        self.assertAlmostEqual(fy['revenue_growth'], 20)
        self.assertEqual(fy['period_end'], '2025-12-31')
        self.assertEqual(row['financial_currency'], 'USD')
        self.assertAlmostEqual(row['market']['float_pct'], 80)

    def test_dilution_is_actual_average_share_change_not_engine_score(self):
        row = self.normalize()
        self.assertAlmostEqual(row['annual'][0]['dilution'], 2)
        self.assertAlmostEqual(row['annual'][1]['dilution'], 100 * (100 / 98 - 1))
        self.assertIsNone(row['annual'][-1]['dilution'])

    def test_missing_capex_is_not_zero_and_positive_capex_is_normalized(self):
        income, balance, cash = statements()
        cash.loc['CapitalExpenditure', cash.columns[0]] = float('nan')
        self.assertIsNone(self.normalize(cash=cash)['annual'][0]['fcf'])
        cash.loc['CapitalExpenditure', cash.columns[0]] = 50
        self.assertEqual(self.normalize(cash=cash)['annual'][0]['fcf'], 150)

    def test_does_not_borrow_debt_or_cashflow_from_another_year(self):
        income, balance, cash = statements()
        row = self.normalize(balance=balance.drop(columns=balance.columns[0]),
                             cash=cash.drop(columns=cash.columns[0]))
        self.assertIsNone(row['annual'][0]['debt'])
        self.assertIsNone(row['annual'][0]['ocf'])
        self.assertIsNone(row['annual'][0]['fcf'])

    def test_float_inconsistency_is_flagged_and_percentage_is_withheld(self):
        row = self.normalize(info={'financialCurrency': 'EUR', 'floatShares': 101,
                                   'sharesOutstanding': 100})
        self.assertEqual(row['market']['float_shares'], 101)
        self.assertIsNone(row['market']['float_pct'])
        self.assertIn('FLOAT_EXCEEDS_SHARES', row['warnings'])

    def test_quote_currency_never_fills_missing_financial_currency(self):
        row = self.normalize(info={'currency': 'USD', 'longName': 'ADR'})
        self.assertIsNone(row['financial_currency'])
        self.assertIn('FINANCIAL_CURRENCY_UNKNOWN', row['warnings'])

    def test_zero_and_negative_values_are_preserved_and_future_columns_excluded(self):
        income, balance, cash = statements()
        cash.loc['OperatingCashFlow', cash.columns[0]] = 0
        income[pd.Timestamp('2027-12-31')] = 999
        row = self.normalize(income=income, cash=cash)
        self.assertEqual(row['annual'][0]['ocf'], 0)
        self.assertEqual(row['annual'][0]['fcf'], -50)
        self.assertNotIn('2027-12-31', [a['period_end'] for a in row['annual']])
        json.dumps(row, allow_nan=False)

    def test_refresh_only_fetches_members_and_keeps_last_good_timestamp_on_failure(self):
        old = self.normalize()
        old['retrieved_at'] = '2026-10-01T11:00:00+00:00'
        old['listing'] = 'TEST'
        cache = {'schema': self.compare.VERSION, 'rows': [old, dict(old, ticker='OUTSIDE')]}

        def failed_fetch(symbol):
            self.assertEqual(symbol, 'TEST')
            raise OSError('provider unavailable')

        result = self.compare.refresh({'TEST': {'yf': 'TEST'}}, previous=cache,
                                      fetcher=failed_fetch, now=NOW)
        self.assertEqual([r['ticker'] for r in result['rows']], ['TEST'])
        self.assertEqual(result['rows'][0]['status'], 'CACHED')
        self.assertEqual(result['rows'][0]['retrieved_at'], old['retrieved_at'])
        self.assertEqual(result['rows'][0]['annual'][0]['revenue'], 1200)

    def test_changed_listing_cannot_reuse_a_different_securitys_cache(self):
        old = self.normalize()
        cache = {'schema': self.compare.VERSION, 'rows': [old]}
        result = self.compare.refresh({'TEST': {'yf': 'DIFFERENT'}}, previous=cache,
            fetcher=lambda symbol: (_ for _ in ()).throw(OSError()), now=NOW)
        self.assertEqual(result['rows'][0]['status'], 'UNAVAILABLE')
        self.assertEqual(result['rows'][0]['annual'], [])

    def test_recent_successful_snapshot_does_not_consume_another_provider_request(self):
        old = self.normalize()
        result = self.compare.refresh({'TEST': {'yf': 'TEST'}},
            previous={'schema': self.compare.VERSION, 'rows': [old]}, now=NOW,
            fetcher=lambda symbol: self.fail('Recent data should be reused'))
        self.assertEqual(result['rows'][0]['retrieved_at'], old['retrieved_at'])
        self.assertEqual(result['rows'][0]['status'], old['status'])

    def test_refresh_caps_provider_requests_and_keeps_all_universe_members(self):
        fetched = []
        def fetch(symbol):
            fetched.append(symbol)
            income, balance, cash = statements()
            return dict(info={'financialCurrency': 'USD'}, income=income, balance=balance, cash=cash)
        result = self.compare.refresh({f'T{i}': {'yf': f'T{i}'} for i in range(20)},
            fetcher=fetch, now=NOW)
        self.assertLessEqual(len(fetched), 16)
        self.assertEqual(len(result['rows']), 20)

    def test_partial_transport_failure_preserves_complete_last_good_snapshot(self):
        old = self.normalize()
        old['retrieved_at'] = '2026-10-01T11:00:00+00:00'
        income, _, _ = statements()
        result = self.compare.refresh({'TEST': {'yf': 'TEST'}},
            previous={'schema': self.compare.VERSION, 'rows': [old]}, now=NOW,
            fetcher=lambda symbol: dict(info={}, income=income, balance=None, cash=None,
                                        errors=['info:YFRateLimitError']))
        row = result['rows'][0]
        self.assertEqual(row['annual'][0]['fcf'], 150)
        self.assertEqual(row['annual'][0]['debt'], 500)
        self.assertEqual(row['financial_currency'], 'USD')
        self.assertEqual(row['retrieved_at'], old['retrieved_at'])
        self.assertEqual(row['status'], 'CACHED')

    def test_failed_batches_rotate_without_redating_financial_data(self):
        universe = {f'T{i:02}': {'yf': f'T{i:02}'} for i in range(20)}
        fetched = []
        def failed(symbol):
            fetched.append(symbol)
            raise OSError('unavailable')
        first = self.compare.refresh(universe, fetcher=failed, now=NOW)
        first_requested = set(fetched)
        fetched.clear()
        second = self.compare.refresh(universe, previous=first,
                                       fetcher=failed, now=NOW+timedelta(days=1))
        self.assertTrue(set(universe)-first_requested <= set(fetched))
        self.assertTrue(all(r['retrieved_at'] is None for r in second['rows']))

    def test_clean_partial_response_cannot_degrade_a_previously_cached_complete_row(self):
        old = self.normalize()
        old['retrieved_at'] = '2026-10-01T11:00:00+00:00'
        universe = {'TEST': {'yf': 'TEST'}}
        first = self.compare.refresh(universe, now=NOW,
            previous={'schema': self.compare.VERSION, 'rows': [old]},
            fetcher=lambda symbol: (_ for _ in ()).throw(OSError()))
        income, _, _ = statements()
        second = self.compare.refresh(universe, previous=first, now=NOW+timedelta(days=1),
            fetcher=lambda symbol: dict(info={'financialCurrency': 'USD'}, income=income,
                                        balance=None, cash=None, errors=[]))
        self.assertEqual(second['rows'][0]['annual'][0]['fcf'], 150)
        self.assertEqual(second['rows'][0]['retrieved_at'], old['retrieved_at'])

    def test_public_page_projects_cache_to_frozen_universe_and_escapes_json(self):
        row = self.normalize()
        row['name'] = '</script><script>alert(1)</script>'
        record = {'_evidence': {'inputs': {'TEST': {'yf': 'TEST'}}}, 'TEST': {'score': 7}}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'comparison').mkdir()
            (root / 'comparison/latest.json').write_text(json.dumps({
                'schema': self.compare.VERSION, 'generated_at': NOW.isoformat(),
                'rows': [row, dict(row, ticker='OUTSIDE')]}))
            original = copy.deepcopy(record)
            pages = dict(self.compare.site_pages(root, {'record': record}, now=NOW))
        payload = json.loads(pages[Path('compare.json')])
        self.assertEqual([r['ticker'] for r in payload['rows']], ['TEST'])
        self.assertNotIn('</script><script>alert(1)', pages[Path('compare.html')])
        self.assertEqual(record, original)

    def test_site_missing_cache_still_lists_only_the_allowed_universe(self):
        record = {'_evidence': {'inputs': {'WKL': {'yf': 'WKL.AS'}, 'DIS': {'yf': 'DIS'}}}}
        with tempfile.TemporaryDirectory() as temp:
            pages = dict(self.compare.site_pages(Path(temp), {'record': record}, now=NOW))
        data = json.loads(pages[Path('compare.json')])
        self.assertEqual({r['ticker'] for r in data['rows']}, {'WKL', 'DIS'})
        self.assertTrue(all(r['status'] == 'UNAVAILABLE' for r in data['rows']))

    def test_scoreboard_comparison_link_survives_all_three_languages(self):
        import i18n
        import weekly_research
        source = '<!DOCTYPE html><html lang="en"><body><h1>Master Scoreboard</h1></body></html>'
        nav = weekly_research.add_research_link(source, include_comparison=True)
        labels = {'en': 'Compare stocks ↗', 'de': 'Aktienvergleich ↗', 'es': 'Comparar acciones ↗'}
        for language, label in labels.items():
            page = i18n.localize(nav, language)
            self.assertIn('href="compare.html?lang=' + language + '"', page)
            self.assertIn(label, page)

    def test_comparison_uses_frozen_model_score_instead_of_a_cached_or_recomputed_score(self):
        row = self.normalize()
        row['model'] = {'score': 10}
        record = {'_evidence': {'captured_at': NOW.isoformat(), 'inputs': {
            'TEST': {'yf': 'TEST', 'built': 'auto', 'normalization_status': 'REVIEW_REQUIRED'}}},
            'TEST': {'score': 5.62, 'score_explanation': {'status': 'PUBLISHED_TOTAL'}}}
        original = copy.deepcopy(record)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'comparison').mkdir()
            (root / 'comparison/latest.json').write_text(json.dumps({
                'schema': self.compare.VERSION, 'rows': [row]}))
            pages = dict(self.compare.site_pages(root, {'record': record}, now=NOW))
        data = json.loads(pages[Path('compare.json')])
        self.assertEqual(data['rows'][0]['model']['score'], 5.62)
        self.assertEqual(data['rows'][0]['model']['score_status'], 'PUBLISHED_TOTAL')
        self.assertTrue(data['rows'][0]['model']['review_required'])
        self.assertEqual(data['rows'][0]['model']['captured_at'], NOW.isoformat())
        self.assertEqual(data['duel_policy'], 'finance-duel-v1')
        self.assertEqual(record, original)

    def test_nonfinite_and_out_of_range_frozen_scores_are_withheld(self):
        for score in (float('nan'), float('inf'), True, -1, 11):
            record = {'_evidence': {'inputs': {'TEST': {'yf': 'TEST'}}}, 'TEST': {'score': score}}
            with tempfile.TemporaryDirectory() as temp:
                pages = dict(self.compare.site_pages(Path(temp), {'record': record}, now=NOW))
            self.assertIsNone(json.loads(pages[Path('compare.json')])['rows'][0]['model']['score'])


if __name__ == '__main__':
    unittest.main()
