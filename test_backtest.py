"""Backtest mechanics on synthetic prices (no network)."""
import unittest

import numpy as np
import pandas as pd

import backtest as bt


def frame(seed, n=700, drift=0.0008):
    rng = np.random.default_rng(seed)
    close = pd.Series(100 * np.exp(np.cumsum(rng.normal(drift, 0.02, n))),
                      index=pd.bdate_range('2020-01-01', periods=n))
    return close, close * 1.01, close * 0.99


class Indicators(unittest.TestCase):
    def test_levels_use_only_past_data(self):
        c, h, lo = frame(1)
        f = bt.indicators(c, h, lo)
        self.assertAlmostEqual(f['sma36'].iloc[100], c.iloc[65:101].mean())
        self.assertAlmostEqual(f['res'].iloc[100], c.iloc[36:96].max())     # 60 sessions ending 5 before
        changed = c.copy()
        changed.iloc[350:] *= 2                                              # a future change
        self.assertAlmostEqual(bt.indicators(changed, h, lo)['sma200'].iloc[349], f['sma200'].iloc[349])


class Runs(unittest.TestCase):
    def setUp(self):
        self.spx = frame(0, drift=0.0005)[0]
        self.frames = {f'S{i}': bt.indicators(*frame(i + 1)).reindex(self.spx.index) for i in range(12)}
        self.start = self.spx.index[260]

    def test_event_study_buckets_and_breakouts(self):
        out = bt.event_study(self.frames, self.spx, self.start)
        self.assertIn('30..+%', out['extension_36'])
        self.assertEqual(sum(v['n'] for v in out['extension_36'].values()) > 0, True)
        self.assertIsNotNone(out['breakouts']['failure_rate'])

    def test_every_variant_simulates_with_costs_and_limits(self):
        sectors = {k: 'A' if i % 2 else 'B' for i, k in enumerate(self.frames)}
        for name, rule in bt.VARIANTS.items():
            m = bt.simulate(self.frames, self.spx, sectors, self.start, **rule)
            self.assertGreater(m['final'], 0, name)
            self.assertLessEqual(m['max_drawdown'], 0, name)

    def test_missing_quote_carries_equity_but_cannot_fill(self):
        days = pd.bdate_range('2020-01-01', periods=275)
        close = pd.Series(100 + np.arange(len(days)) * .02, index=days)
        stock = bt.indicators(close, close + 1, close - 1)
        normal = bt.simulate({'A': stock}, close, {}, days[-10])
        stock.loc[days[-4], 'close'] = np.nan
        gap = bt.simulate({'A': stock}, close, {}, days[-10])
        self.assertEqual(normal['max_drawdown'], gap['max_drawdown'])
        self.assertEqual(gap['longest_carried_mark'], {'A': 1})
        stock.loc[days[-1], 'close'] = np.nan
        self.assertEqual(bt.simulate({'A': stock}, close, {}, days[-10])['unpriced_at_end'], ['A'])

    def test_report_renders(self):
        res = dict(window='x', generated_at='y', symbols=12, event_study=bt.event_study(self.frames, self.spx, self.start),
                   portfolio={'base_v1_5': bt.simulate(self.frames, self.spx, {}, self.start)},
                   spx=bt._metrics(self.spx[self.spx.index >= self.start], []))
        self.assertIn('Portfolio simulation', bt.report(res))


if __name__ == '__main__':
    unittest.main()


class Page(unittest.TestCase):
    def test_page_from_committed_results(self):
        import tempfile
        from pathlib import Path
        self.assertEqual(bt.site_pages(tempfile.mkdtemp()), [])
        pages = bt.site_pages(Path(__file__).parent)
        if pages:                                  # the repository carries a committed result
            html = pages[0][1]
            self.assertIn('<table>', html)
            self.assertIn('first day of each month', html)
            self.assertNotIn('| ---', html)


class Shorts(unittest.TestCase):
    def test_falling_market_short_variant_opens_covers_and_profits(self):
        frames = {f'S{i}': bt.indicators(*frame(i, drift=-0.0015)) for i in range(6)}
        spx = frame(99, drift=-0.001)[0]
        start = spx.index[300]
        sectors = {k: 'A' for k in frames}
        base = bt.simulate(frames, spx, sectors, start, **bt.VARIANTS[bt.BASE])
        short = bt.simulate(frames, spx, sectors, start, **bt.VARIANTS['shorts_in_correction'])
        self.assertGreater(short['final'], base['final'])

    def test_short_variant_never_shorts_in_an_uptrend_when_limited_to_corrections(self):
        frames = {f'S{i}': bt.indicators(*frame(i)) for i in range(6)}
        spx = pd.Series(np.linspace(100, 300, 700), index=pd.bdate_range('2020-01-01', periods=700))
        m = bt.simulate(frames, spx, {k: 'A' for k in frames}, spx.index[300],
                        **bt.VARIANTS['shorts_in_correction'])
        base = bt.simulate(frames, spx, {k: 'A' for k in frames}, spx.index[300], **bt.VARIANTS[bt.BASE])
        self.assertEqual(m['final'], base['final'])
