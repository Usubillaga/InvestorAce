"""Round 2 contracts. Every quote in these tests is a synthetic close."""
import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from datetime import date, datetime, timezone

import paper_portfolio as pp
from paper_round2 import snapshot


class Round2Tests(unittest.TestCase):
    def setUp(self):
        docs = pp.load()
        self.rules = next(d for d in docs if d['_file'].endswith('round2-rules-v18.json'))
        self.pure = next(d for d in docs if d['_file'].endswith('round2-pure-model-v18.json'))
        self.entry, self.end = self.rules['entry_date'], self.rules['exit_date']
        self.series = {}
        for d in (self.rules, self.pure):
            for h in d['holdings'] + d.get('discretionary', {}).get('holdings', []):
                px = h['signal_price']
                self.series[h['yahoo']] = [(self.entry, px), (self.end, px * 1.10)]
        self.series['^GSPC'] = [(self.entry, 100.), (self.end, 109.)]

    def test_signal_reconciliation_and_limits(self):
        r = pp.evaluate(self.rules, self.series)
        self.assertAlmostEqual(r['invested'], 20960.18, places=2)
        self.assertAlmostEqual(r['cash'], 5340.27, places=2)
        self.assertAlmostEqual(r['capital'], 26300.45)
        rows = r['holdings'] + r['discretionary']
        self.assertEqual({h['ticker']: h['shares'] for h in rows}, {
            'BKNG': 13, 'MO': 23, 'CNX': 64, 'ZTS': 20, 'WKL': 15, 'GDDY': 18, 'GEN': 81,
            'ADBE': 11, 'ENS': 13, 'MU': 2, 'LULU': 6, 'TTD': 76, 'CRM': 6, 'OXY': 42})
        tech = sum(h['cost'] for h in rows if h.get('sector') in ('Technology', 'Software', 'Ad Tech'))
        self.assertAlmostEqual(tech / r['capital'], 0.3496692934)
        self.assertAlmostEqual(max(h['cost'] for h in rows) / r['capital'], 0.083433, places=5)
        self.assertAlmostEqual(r['discretionary'][0]['cost'] / r['capital'], 0.0749539530)
        self.assertEqual(r['entry_cap_breaches'], [])

    def test_common_denominator_cash_and_signed_excess(self):
        for factor in (1.10, 0.90, 1.0):
            with self.subTest(factor=factor):
                series = {k: [(self.entry, vals[0][1]), (self.end, vals[0][1]*factor)]
                          for k, vals in self.series.items()}
                series['^GSPC'] = self.series['^GSPC']
                for d, exposure in ((self.rules, 20960.1779218765), (self.pure, 26298.290565)):
                    r = pp.evaluate(d, series)
                    expected = 100 * (factor - 1) * exposure / 26300.45
                    self.assertAlmostEqual(r['account_return_pct'], expected)
                    self.assertAlmostEqual(r['combined_return_pct'], expected)
                    self.assertAlmostEqual(r['excess_combined_vs_benchmark_pct'], expected - 9)
                    self.assertAlmostEqual(r['cash'] + r['invested'], r['capital'])
                    self.assertAlmostEqual(r['value_now'] - r['capital'], r['pnl'])
                    col, = pp.comparison([r], [d])
                    self.assertAlmostEqual(col['total'], expected)
                    self.assertAlmostEqual(col['excess'], expected - 9)
                    self.assertIn(f"account {expected:+.2f}%", pp.report(r))

    def test_oxy_only_and_missing_control_have_their_proper_effect(self):
        series = {k: [(self.entry, vals[0][1]), (self.end, vals[0][1])]
                  for k, vals in self.series.items()}
        series['OXY'] = self.series['OXY']
        r = pp.evaluate(self.rules, series)
        self.assertAlmostEqual(r['account_return_pct'], 0.7495395298584254)
        self.assertAlmostEqual(pp.evaluate(self.pure, series)['account_return_pct'], 0)
        self.assertAlmostEqual(r['excess_combined_vs_benchmark_pct'], r['account_return_pct'])
        self.assertAlmostEqual(r['holdings'][0]['entry_close'], self.series['BKNG'][0][1])
        self.assertNotIn('CVX', series)
        self.assertIsNone(pp.evaluate(self.rules, dict(series, OXY=[]))['account_return_pct'])

    def test_whole_share_model_and_fixed_shares_at_changed_entry(self):
        base = pp.evaluate(self.pure, self.series)
        self.assertAlmostEqual(base['cash'], 2.16, places=2)
        self.assertEqual(len(base['holdings']), 15)
        series = dict(self.series, TTD=[(self.entry, 15), (self.end, 16)],
                      ADBE=[(self.entry, 280), (self.end, 280)])
        rules = pp.evaluate(self.rules, series)
        sizes = lambda r: {h['ticker']: h['shares'] for h in r['holdings'] + r['discretionary']}
        self.assertEqual(sizes(rules), sizes(pp.evaluate(self.rules, self.series)))
        self.assertNotEqual(sizes(base), sizes(pp.evaluate(self.pure, series)))
        self.assertEqual(set(rules['entry_cap_breaches']), {'Technology group', 'ADBE'})
        self.assertAlmostEqual(rules['cash'], 5340.2720781235 - (76*(15-14.06) + 11*(280-223.98))*.890631)
        self.assertEqual(rules['cash'], pp.evaluate(self.rules, series, date.fromisoformat(self.entry))['cash'])

    def test_missing_late_partial_and_stale_quotes(self):
        for d in (self.rules, self.pure):
            cases = [(self.series, date(2026, 11, 23)), ({}, date.fromisoformat(self.entry)),
                     (dict(self.series, ENS=[]), None),
                     (dict(self.series, ENS=[('2026-11-25', 124.35), (self.end, 133.)]), None),
                     (dict(self.series, ENS=[(self.entry, 124.35), ('2026-12-07', 133.)]), None)]
            for series, when in cases:
                r = pp.evaluate(d, series, when)
                self.assertIsNone(r['account_return_pct'])
                self.assertIsNone(r['pnl'])
                self.assertIsNone(r['value_now'])
            missing = dict(self.series)
            del missing['^GSPC']
            r = pp.evaluate(d, missing)
            self.assertIsNotNone(r['account_return_pct'])
            self.assertIsNone(r['excess_combined_vs_benchmark_pct'])
            missing['^GSPC'] = [('2026-11-25', 100), (self.end, 109)]
            self.assertIsNone(pp.evaluate(d, missing)['benchmark_return_pct'])

    def test_invalid_frozen_plan_or_negative_cash_blocks_account(self):
        for field in ('shares', 'budget', 'plan', 'fx'):
            d = copy.deepcopy(self.rules)
            if field == 'shares':
                del d['discretionary']['holdings'][0]['shares_planned']
            elif field == 'budget':
                d['holdings'][0]['shares_planned'] = 9999
            elif field == 'plan':
                d['planned_cash_eur'] += 1
            else:
                d['fx'] = {}
            r = pp.evaluate(d, self.series)
            self.assertIsNone(r['account_return_pct'])
            self.assertIsNone(r['cash'])

    def test_alternatives_never_enter_a_pooled_account(self):
        docs = [self.rules, self.pure]
        results = [pp.evaluate(d, self.series) for d in docs]
        self.assertIsNone(pp.combine(results, docs))
        self.assertEqual([x['name'] for x in pp.comparison(results, docs)], [d['short_name'] for d in docs])
        html = pp.render(results, docs, now=datetime(2026, 12, 8, 23, tzinfo=timezone.utc))
        for value in ('Round 2 · account comparison', '+7.97%', '+10.00%', '5,340.27'):
            self.assertIn(value, html)
        self.assertNotIn('Together', html)
        all_docs = pp.load()
        old = [d for d in all_docs if d.get('comparison_group') != pp.ROUND2]
        historical = [pp.evaluate(d, {}) for d in old]
        pooled = pp.combine(historical + results, old + docs)
        self.assertAlmostEqual(pooled['capital'], 28000)
        self.assertEqual(pp.combine(historical, old), pooled)

    def test_settlement_and_drawdown_have_independent_evidence_gates(self):
        docs = [self.rules, self.pure]
        dates = ['2026-11-24', '2026-11-25', '2026-11-26', '2026-11-27', '2026-11-30',
                 '2026-12-01', '2026-12-02', '2026-12-03', '2026-12-04', '2026-12-07', '2026-12-08']
        series = {k: [(d, v[0][1] * (0.8 if d == '2026-11-25' else 1)) for d in dates
                      if d != '2026-11-26' or k == 'WKL.AS'] for k, v in self.series.items()}
        final = datetime(2026, 12, 8, 22, tzinfo=timezone.utc)
        with TemporaryDirectory() as tmp:
            folder = Path(tmp)
            data = snapshot(docs, series, final, folder)
            rules = data['accounts']['rules']
            self.assertAlmostEqual(rules['final_nav'], rules['capital'])
            self.assertAlmostEqual(rules['drawdown'], 20 * rules['invested'] / rules['capital'])
            self.assertEqual(rules['trough_day'], '2026-11-25')
            self.assertIsNone(rules['net_nav'])
            self.assertIsNone(snapshot(docs, series, final.replace(hour=17), folder)['accounts']['rules']['final_nav'])
            (folder / 'round2-settlement.json').write_text(json.dumps({
                'round': pp.ROUND2, 'as_of': self.end,
                'rules': {'costs_eur': 1., 'dividends_eur': 2., 'interest_eur': 3., 'source': 'fixture'}
            }))
            series['ENS'] = [(d, p) for d, p in series['ENS'] if d != '2026-12-02']
            amended = snapshot(docs, series, final, folder)['accounts']['rules']
            self.assertIsNone(amended['drawdown'])
            self.assertAlmostEqual(amended['net_nav'], rules['capital'] + 4)
            self.assertEqual(amended['days'][6]['missing'], ['ENS'])
            series['OXY'] = series['OXY'][:-1]
            data = snapshot(docs, series, final, folder)['accounts']
            self.assertIsNone(data['rules']['final_nav'])
            self.assertIsNotNone(data['score']['final_nav'])


if __name__ == '__main__':
    unittest.main()
