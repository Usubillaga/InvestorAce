"""Start-date sensitivity of backtest variants (synthetic prices, no network)."""
import unittest

import numpy as np
import pandas as pd

import backtest as bt
import start_offsets as so


def market(n=900, seed=1):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range('2018-01-01', periods=n)
    frames = {}
    for i in range(8):
        close = pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0006, 0.018, n))), index=idx)
        frames[f'S{i}'] = bt.indicators(close, close * 1.01, close * 0.99)
    spx = pd.Series(4000 * np.exp(np.cumsum(rng.normal(0.0004, 0.01, n))), index=idx)
    return frames, spx


class StartOffsets(unittest.TestCase):
    def test_paired_runs_counts_ties_and_original_start(self):
        frames, spx = market()
        variants = {bt.BASE: bt.VARIANTS[bt.BASE], 'same': dict(bt.VARIANTS[bt.BASE]),
                    'sell_all_in_correction': bt.VARIANTS['sell_all_in_correction']}
        out = so.study(bt.simulate, frames, spx, {}, bt.portfolio_inputs(frames), (('2019-01-01', None),),
                       variants, bt.BASE, starts=4, step=5)
        (period,) = out
        same = out[period]['same']
        self.assertEqual((same['starts'], same['wins'], same['ties'], same['losses']), (4, 0, 4, 0))
        self.assertEqual(same['cagr'], dict(median=0.0, min=0.0, max=0.0))
        self.assertEqual(len(same['observations']), 4)
        self.assertEqual(len({r['end'] for r in same['observations']}), 1)
        other = out[period]['sell_all_in_correction']
        self.assertEqual(other['wins'] + other['ties'] + other['losses'], 4)
        base0 = bt.simulate(frames, spx, {}, pd.Timestamp('2019-01-01'), prepared=bt.portfolio_inputs(frames),
                            precise=True, **bt.VARIANTS[bt.BASE])
        var0 = bt.simulate(frames, spx, {}, pd.Timestamp('2019-01-01'), prepared=bt.portfolio_inputs(frames),
                           precise=True, **bt.VARIANTS['sell_all_in_correction'])
        self.assertAlmostEqual(other['original']['cagr'], var0['cagr'] - base0['cagr'])
        self.assertIn('W / T / L', so.report(out))

    def test_subunit_gain_counts_as_win(self):
        row = so.summarise([({'final': 10000.1}, {'final': 10000.2})])
        self.assertEqual((row['wins'], row['ties']), (1, 0))

    def test_short_periods_are_skipped(self):
        frames, spx = market(n=400)
        out = so.study(bt.simulate, frames, spx, {}, bt.portfolio_inputs(frames), (('2019-01-01', None),),
                       {bt.BASE: bt.VARIANTS[bt.BASE]}, bt.BASE)
        self.assertEqual(out, {})


if __name__ == '__main__':
    unittest.main()


class Determinism(unittest.TestCase):
    def test_same_inputs_give_identical_results_including_shorts(self):
        frames, spx = market()
        prepared = bt.portfolio_inputs(frames)
        for name in (bt.BASE, 'shorts_in_correction', 'shorts_always'):
            first = bt.simulate(frames, spx, {}, spx.index[300], prepared=prepared, precise=True, **bt.VARIANTS[name])
            again = bt.simulate(frames, spx, {}, spx.index[300], prepared=bt.portfolio_inputs(frames), precise=True,
                                **bt.VARIANTS[name])
            self.assertEqual(first['final'], again['final'], name)
