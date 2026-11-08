"""Paper portfolio test: frozen holdings, dated closes, no hindsight."""
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

import market_pulse
import paper_portfolio as pp


def doc():
    return dict(schema='paper-portfolio-v1', name='T', entry_date='2026-11-09', exit_date='2026-11-23',
                holdings=[dict(ticker='A', yahoo='A', label='Buy', score=8.5, weight_pct=75.),
                          dict(ticker='B', yahoo='B', label='Buy', score=7.0, weight_pct=25.)],
                control_basket=dict(holdings=[dict(ticker='C', yahoo='C', weight_pct=100.)]),
                benchmark=dict(name='S&P 500', yahoo='^GSPC'))


def snapshot(tracked):
    return {'_evidence': {'macro': {'pulse': {'tracked': tracked}}}}


class PaperPortfolioTests(unittest.TestCase):
    def series(self):
        return pp.merge_series([
            snapshot({'A': [['2026-11-06', 90.], ['2026-11-09', 100.]], 'B': [['2026-11-09', 50.]],
                      'C': [['2026-11-09', 10.]], '^GSPC': [['2026-11-09', 7000.]]}),
            snapshot({'A': [['2026-11-20', 108.], ['2026-11-23', 110.], ['2026-11-24', 200.]],
                      'B': [['2026-11-23', 45.]], 'C': [['2026-11-23', 12.]], '^GSPC': [['2026-11-23', 7070.]]})])

    def test_weighted_return_uses_entry_and_exit_closes_only(self):
        r = pp.evaluate(doc(), self.series())
        self.assertAlmostEqual(r['portfolio_return_pct'], 0.75 * 10 + 0.25 * -10)
        self.assertAlmostEqual(r['benchmark_return_pct'], 1.0)
        self.assertAlmostEqual(r['control_return_pct'], 20.0)
        self.assertAlmostEqual(r['excess_vs_benchmark_pct'], 4.0)
        self.assertTrue(r['final'])
        self.assertIn('InvestorAce Buy portfolio +5.00%', pp.report(r))

    def test_interim_valuation_never_looks_past_its_date(self):
        r = pp.evaluate(doc(), self.series(), as_of=date(2026, 11, 20))
        self.assertFalse(r['final'])
        a = next(h for h in r['holdings'] if h['ticker'] == 'A')
        self.assertEqual((a['exit_close_date'], a['exit_close']), ('2026-11-20', 108.))
        self.assertEqual(next(h for h in r['holdings'] if h['ticker'] == 'B')['status'], 'NO_PRICE')

    def test_user_pick_is_a_separate_sleeve(self):
        d = dict(doc(), discretionary=dict(name='Pick', sleeve_weight_pct=10.,
                                           holdings=[dict(ticker='D', yahoo='D', weight_pct=100.)]))
        series = dict(self.series(), D=[('2026-11-09', 50.), ('2026-11-23', 60.)])
        r = pp.evaluate(d, series)
        self.assertAlmostEqual(r['portfolio_return_pct'], 5.0)   # model result unchanged
        self.assertAlmostEqual(r['discretionary_return_pct'], 20.0)
        self.assertAlmostEqual(r['combined_return_pct'], 0.9 * 5 + 0.1 * 20)
        self.assertIn('combined (90% model + 10% pick) +6.50%', pp.report(r))
        self.assertIsNone(pp.evaluate(d, self.series())['combined_return_pct'])   # unpriced pick: no blend
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, 'x.json').write_text(json.dumps(d))
            self.assertIn('D', pp.tracked_symbols(date(2026, 11, 8), tmp))

    def test_entry_is_the_first_close_on_or_after_the_entry_date(self):
        # Only Friday's close is known when Monday's build runs before the close: no entry yet.
        early = pp.merge_series([snapshot({'A': [['2026-11-06', 90.]], 'B': [['2026-11-06', 50.]],
                                           'C': [['2026-11-06', 10.]], '^GSPC': [['2026-11-06', 6990.]]})])
        r = pp.evaluate(doc(), early, as_of=date(2026, 11, 9))
        self.assertTrue(all(h['status'] == 'NO_PRICE' for h in r['holdings']))
        self.assertIsNone(r['portfolio_return_pct'])
        a = next(h for h in pp.evaluate(doc(), self.series())['holdings'] if h['ticker'] == 'A')
        self.assertEqual((a['entry_close_date'], a['entry_close']), ('2026-11-09', 100.))

    def test_nothing_is_held_before_the_entry_date(self):
        r = pp.evaluate(doc(), self.series(), as_of=date(2026, 11, 8))
        self.assertEqual(r['status'], 'PENDING')
        self.assertIsNone(r['portfolio_return_pct'])
        self.assertIn('starts with the close of 2026-11-09', pp.report(r))

    def test_page_is_built_from_committed_snapshots(self):
        from datetime import datetime, timezone
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, 'paper_trades').mkdir()
            Path(tmp, 'paper_trades', 'x.json').write_text(json.dumps(doc()))
            runs = Path(tmp, 'history', 'runs')
            runs.mkdir(parents=True)
            Path(runs, '20261110T230000-a.json').write_text(json.dumps(
                snapshot({'A': [['2026-11-09', 100.], ['2026-11-10', 104.]], '^GSPC': [['2026-11-09', 7000.]]})))
            build = dict(record=snapshot({'A': [['2026-11-11', 106.]]}))
            pages = pp.site_pages(tmp, build, now=datetime(2026, 11, 11, 23, 30, tzinfo=timezone.utc))
            self.assertEqual([str(p) for p, _ in pages], ['paper-test.html'])
            html = pages[0][1]
            self.assertIn('Running: valued to 2026-11-11', html)
            self.assertIn('+6.00%', html)
            self.assertIn('Not priced yet', html)
            Path(tmp, 'paper_trades', 'x.json').unlink()
            self.assertEqual(pp.site_pages(tmp, build), [])

    def test_tracking_window_and_frozen_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, 'x.json').write_text(json.dumps(doc()))
            self.assertEqual(pp.tracked_symbols(date(2026, 11, 8), tmp), ['A', 'B', 'C', '^GSPC'])
            self.assertEqual(pp.tracked_symbols(date(2026, 12, 15), tmp), [])
        real = pp.load()
        self.assertTrue(real)
        for d in real:
            self.assertAlmostEqual(sum(h['weight_pct'] for h in d['holdings']), 100., delta=0.1)
            self.assertLess(d['signal_snapshot_captured'][:10], d['entry_date'])
            for pick in (d.get('discretionary') or {}).get('holdings', []):
                self.assertNotIn(pick['ticker'], {h['ticker'] for h in d['holdings']})

    def test_pulse_records_tracked_closes(self):
        import pandas as pd
        idx = pd.to_datetime(['2026-11-06', '2026-11-09'])
        frame = pd.DataFrame({('Close', 'A'): [90., 100.], ('Close', '^GSPC'): [6990., 7000.]}, index=idx)
        pulse = market_pulse.read(download=lambda *a, **k: frame, fear_greed=lambda url: {}, tracked_symbols=['A'])
        self.assertEqual(pulse['tracked']['A'], [['2026-11-06', 90.0], ['2026-11-09', 100.0]])


if __name__ == '__main__':
    unittest.main()
