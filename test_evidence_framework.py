import copy
import importlib.util
import json
import os
import random
import tempfile
import types
import unittest
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

import test_framework_contract
import evidence
import macro
import portfolio
import research
from path_features import diagnostics, signature2

engine = test_framework_contract.engine
HERE = Path(__file__).parent


@contextmanager
def directory(path):
    before = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(before)


def row():
    d = engine._regime_fixture('Pharma', .7, 7, 8)
    d.update(yf='TEST', cur='USD', dil=7, held=False)
    return d


class LegacyEquivalence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = HERE / 'tests/fixtures/upstream_engine.txt'
        cls.old = types.ModuleType('frozen_upstream')
        cls.old.__file__ = str(path)
        exec(compile(path.read_text(encoding='utf-8'), str(path), 'exec'), cls.old.__dict__)

    def test_5000_identical_input_cases_against_frozen_upstream(self):
        rng = random.Random(20260915)
        sectors = list(engine.AFF['GOLDILOCKS'])
        for _ in range(5000):
            d = row()
            d.update(price=rng.uniform(1, 500), fcf=rng.uniform(1, 5000),
                     shares=rng.uniform(1, 1000), r=rng.uniform(.04, .15),
                     sub=tuple(rng.uniform(0, 10) for _ in range(6)),
                     sector=rng.choice(sectors), deliver=rng.uniform(-20, 40),
                     dil=rng.uniform(0, 10))
            if rng.random() < .2:
                d.update(sub=None, score_fixed=rng.uniform(0, 10))
            for name in ('ngv', 'cover', 'cushion', 'score', 'risk', 'regime_scores'):
                self.assertEqual(getattr(engine, name)(d), getattr(self.old, name)(d), name)
            self.assertEqual(engine.verdict('TEST', d), self.old.verdict('TEST', d))

    def test_entire_stored_universe_identical_at_controlled_prices(self):
        for ticker, original in self.old.DATA.items():
            d = copy.deepcopy(original)
            d['price'] = 100
            for name in ('score', 'risk', 'ngv', 'regime_scores'):
                self.assertEqual(getattr(engine, name)(d), getattr(self.old, name)(d), ticker)


class EvidenceContract(unittest.TestCase):
    def record(self):
        bundle = {'sources': {'engine.py': 'frozen source'}}
        bundle['sha256'] = evidence.digest(bundle['sources'])
        rows = {'TEST': row()}
        rec = evidence.create_record(rows, {'TEST': {'score': 7}}, {'regime': 'REFLATION'},
                                     {'engine': 'test'}, bundle['sha256'], '2026-09-15T12:00:00+00:00')
        return rec, bundle

    def test_daily_first_write_and_every_run_retained(self):
        rec, bundle = self.record()
        with tempfile.TemporaryDirectory() as tmp:
            first = evidence.publish_record(rec, bundle, tmp)
            daily = Path(tmp, '2026-09-15.json').read_bytes()
            rec['TEST']['score'] = 2
            second = evidence.publish_record(rec, bundle, tmp)
            self.assertTrue(first['daily_created'])
            self.assertFalse(second['daily_created'])
            self.assertEqual(daily, Path(tmp, '2026-09-15.json').read_bytes())
            self.assertEqual(len(list(Path(tmp, 'runs').glob('*.json'))), 2)
            self.assertNotEqual(first['run_id'], second['run_id'])

    def test_reject_nonfinite_before_publish(self):
        rec, bundle = self.record()
        rec['TEST']['score'] = float('nan')
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                evidence.publish_record(rec, bundle, tmp)
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_source_mismatch_rejected(self):
        rec, bundle = self.record()
        bundle['sources']['engine.py'] = 'changed'
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                evidence.publish_record(rec, bundle, tmp)

    def test_parallel_build_refused_and_lock_released(self):
        with tempfile.TemporaryDirectory() as tmp:
            with evidence.build_lock(tmp):
                with self.assertRaises(RuntimeError):
                    with evidence.build_lock(tmp):
                        pass
            self.assertFalse(Path(tmp, '_build.lock').exists())

    def test_quality_invariant_to_price_and_no_fixed_total_imputation(self):
        d = row()
        a = evidence.business_quality(d, engine.W)
        d.update(price=100000, r_wacc=.2, epv_value=1, score_fixed=10)
        self.assertEqual(a, evidence.business_quality(d, engine.W))
        d['sub'] = None
        self.assertIsNone(evidence.business_quality(d, engine.W))

    def test_ngv_na_does_not_remove_price_status(self):
        d = row()
        d.update(na='not applicable', fcf=None)
        got = evidence.row_diagnostics(d, engine.W)
        self.assertEqual(got['ngv'], 'NOT_APPLICABLE')
        self.assertEqual(got['price'], 'AVAILABLE')

    def test_cash_flow_rate_matching_and_equity_bridge(self):
        self.assertEqual(evidence.declared_perpetuity(10, 10, .1, 'FCFF', 'WACC', 20), 8)
        self.assertEqual(evidence.declared_perpetuity(10, 10, .1, 'FCFE', 'COST_OF_EQUITY'), 10)
        with self.assertRaises(ValueError):
            evidence.declared_perpetuity(10, 10, .1, 'FCFE', 'WACC')
        with self.assertRaises(ValueError):
            evidence.declared_perpetuity(10, 10, .1, 'FCFE', 'COST_OF_EQUITY', 20)

    def test_input_replay_matches_saved_outputs(self):
        with patch.object(engine, 'DATA', {'TEST': row()}):
            bundle = evidence.model_bundle(HERE)
            record = engine.observation({'ok': False}, bundle)
            saved = record['_evidence']['inputs']['TEST']
            for name in ('ngv', 'cover', 'score', 'risk'):
                self.assertEqual(getattr(engine, name)(saved), record['TEST'][name])
            engine.DATA['TEST']['price'] = 9999
            self.assertNotEqual(saved['price'], 9999)

    def test_render_failure_publishes_no_observation(self):
        with tempfile.TemporaryDirectory() as tmp, directory(tmp):
            Path('index.html').write_text('last good report')
            with patch.object(engine, 'DATA', {'TEST': row()}), \
                 patch.object(engine, 'bootstrap_fundamentals'), patch.object(engine, 'fetch_prices'), \
                 patch.object(engine, 'populate_epv'), patch.object(engine, 'read_macro', return_value={'ok': False}), \
                 patch.object(engine, 'build_html', side_effect=RuntimeError('render failed')):
                with self.assertRaises(RuntimeError):
                    engine.run_build()
            self.assertEqual(Path('index.html').read_text(), 'last good report')
            self.assertFalse(list(Path('history').rglob('*.json')))

    def test_invalid_input_never_calls_renderer(self):
        with tempfile.TemporaryDirectory() as tmp, directory(tmp):
            with patch.object(engine, 'bootstrap_fundamentals'), patch.object(engine, 'fetch_prices'), \
                 patch.object(engine, 'populate_epv'), patch.object(engine, 'read_macro', return_value={}), \
                 patch.object(engine, 'validate_full', return_value=(['bad row'], [])), \
                 patch.object(engine, 'build_html') as render:
                with self.assertRaises(ValueError):
                    engine.run_build()
                render.assert_not_called()

    def test_end_to_end_offline_report_and_shared_macro(self):
        m = {'ok': False, 'note': 'offline fixture'}
        with tempfile.TemporaryDirectory() as tmp, directory(tmp):
            with patch.object(engine, 'DATA', {'TEST': row()}), \
                 patch.object(engine, 'bootstrap_fundamentals'), patch.object(engine, 'fetch_prices'), \
                 patch.object(engine, 'populate_epv'), patch.object(engine, 'read_macro', return_value=m) as read, \
                 patch.object(engine, 'sector_performance', return_value={}), \
                 patch.object(engine, 'forward_run', return_value={'ok': False, 'note': 'offline'}), \
                 patch.object(engine, 'freeze_cohorts'):
                result = engine.run_build()
            read.assert_called_once()
            text = Path('index.html').read_text(encoding='utf-8')
            self.assertIn('Evidence and path diagnostics', text)
            self.assertIn('Legacy Score', text)
            record = json.loads(Path('history', result['day'] + '.json').read_text())
            self.assertEqual(record['_evidence']['macro'], m)

    def test_full_universe_with_available_macro_and_missing_vix(self):
        rows = copy.deepcopy(engine.DATA)
        saved = json.loads((HERE / 'tests/fixtures/2026-09-15.json').read_text())
        for ticker, d in rows.items():
            d.update(price=saved.get(ticker, {}).get('price'), price_note='')
        points = [{'date': '2026-09-14', 'g': 1, 'i': 1},
                  {'date': '2026-09-15', 'g': 2, 'i': 1}]
        m = dict(ok=True, regime='REFLATION', growth=2, inflation=1, vix=None,
                 vix_state=None, recession_score=0, recession_legs=[], detail={},
                 trail=[], heading=None, path_diagnostics=diagnostics(points))
        with directory(HERE), patch.object(engine, 'DATA', rows), \
             patch.object(engine, 'sector_performance', return_value={}):
            html = engine.build_html(macro=m, write=False)
            record = engine.observation(m, evidence.model_bundle(HERE))
        self.assertIn('2+ consecutive sampled sessions', html)
        self.assertIn('Constrained portfolio proposal', html)
        self.assertIn('unavailable', html)
        self.assertIsNotNone(record['_portfolio_proposal'])

    def test_quote_fallback_timestamp_does_not_leak_to_next_ticker(self):
        class Quote:
            def __init__(self, symbol):
                self.fast_info = {'currency': 'USD', 'last_price': None if symbol == 'A' else 100}
            def history(self, **kwargs):
                return pd.DataFrame({'Close': [100.]}, index=pd.to_datetime(['2026-09-14']))
        rows = {'A': dict(row(), yf='A'), 'B': dict(row(), yf='B')}
        with patch.object(engine, 'DATA', rows), patch.object(engine.yf, 'Ticker', Quote), \
             patch.object(engine, 'WACC', None), patch.object(engine, '_fetch_momentum'), \
             patch.object(engine, '_year_range', return_value=(50, 200)):
            engine.fetch_prices()
        self.assertEqual(rows['A']['quote_time_status'], 'DAILY_CLOSE')
        self.assertEqual(rows['B']['quote_time_status'], 'UNKNOWN')
        self.assertIsNone(rows['B']['quote_observed_at'])


class PathContract(unittest.TestCase):
    def test_same_endpoint_different_order(self):
        first, a = signature2([[0, 0], [1, 0], [1, 1]])
        second, b = signature2([[0, 0], [0, 1], [1, 1]])
        self.assertEqual(first, second)
        self.assertEqual(a[0][1], 1)
        self.assertEqual(b[0][1], 0)
        self.assertEqual(a[1][0], 0)
        self.assertEqual(b[1][0], 1)

    def test_straight_line_subdivision_and_translation(self):
        a = signature2([[0, 0], [2, 4]])
        b = signature2([[10, 10], [11, 12], [12, 14]])
        self.assertEqual(a, b)

    def test_persistence_counts_observations_not_months(self):
        points = [{'date': '2026-09-01', 'g': -1, 'i': 1},
                  {'date': '2026-09-02', 'g': 1, 'i': 1},
                  {'date': '2026-09-03', 'g': 2, 'i': 2}]
        d = diagnostics(points)
        self.assertEqual(d['persistence_observations'], 2)
        self.assertEqual(d['transitions'], 1)
        self.assertNotIn('transition_probability', d)
        with self.assertRaises(ValueError):
            diagnostics(points + [points[-1]])

    def test_dates_aligned_without_forward_filling(self):
        dates = pd.date_range('2026-01-01', periods=8)
        c = {k: pd.Series(range(1, 9), index=dates, dtype=float)
             for k in ('SPY', 'HG=F', 'CL=F', '^TNX')}
        c['CL=F'] = c['CL=F'].drop(dates[4])
        p = macro.aligned_path(c, lookback=2, window=8)
        self.assertNotIn(dates[4].date().isoformat(), [x['date'] for x in p])
        expected = 100 * (6 / 3 - 1)
        self.assertEqual(next(x['g'] for x in p if x['date'] == '2026-01-06'), expected)


class PortfolioContract(unittest.TestCase):
    def test_caps_cash_and_fit_independence(self):
        candidates = [(str(i), dict(price=100, sector='A' if i < 5 else 'B'), 100-i) for i in range(8)]
        before = copy.deepcopy(candidates)
        book = portfolio.construct(candidates, target_size=6, max_per_sector=2, max_weight=.1)
        self.assertEqual(len(book['positions']), 4)
        self.assertAlmostEqual(book['cash_weight'], .6)
        self.assertEqual(candidates, before)


class ResearchContract(unittest.TestCase):
    def rows(self, count=100):
        rng = random.Random(5)
        price, rows = 100, []
        for t in range(count):
            stamp = (datetime(2020, 1, 1, tzinfo=timezone.utc) + timedelta(days=t)).isoformat()
            price *= 1 + rng.uniform(-.02, .02)
            rows.append(dict(timestamp=stamp, known_at=stamp, price=price,
                             growth=rng.uniform(-5, 5), inflation=rng.uniform(-5, 5)))
        return rows

    def test_future_signal_rejected(self):
        rows = self.rows()
        rows[0]['known_at'] = rows[1]['timestamp']
        with self.assertRaises(ValueError):
            research.evaluate(rows)

    def test_future_changes_cannot_change_earlier_decisions(self):
        rows = self.rows()
        a = research.evaluate(rows, window=5, min_train=10)
        changed = copy.deepcopy(rows)
        for row_ in changed[80:]:
            row_['price'] *= 3
            row_['growth'] *= -2
        b = research.evaluate(changed, window=5, min_train=10)
        for name in a['observations']:
            old = [v for v in a['observations'][name] if v['outcome_at'] < rows[80]['timestamp']]
            new = [v for v in b['observations'][name] if v['outcome_at'] < rows[80]['timestamp']]
            self.assertEqual(old, new)

    def test_execution_delay_and_training_purge(self):
        rows = self.rows()
        report = research.evaluate(rows, window=5, min_train=10)
        lookup = {r['timestamp']: i for i, r in enumerate(rows)}
        for v in report['observations']['signature2']:
            decision = lookup[v['decision_at']]
            self.assertEqual(lookup[v['execution_at']], decision + 1)
            self.assertEqual(lookup[v['outcome_at']], decision + 2)
            self.assertLess(lookup[v['last_training_outcome_at']], decision - 4)

    def test_costs_reduce_buy_hold_and_include_round_trip(self):
        rows = self.rows()
        a = research.evaluate(rows, 5, 10, cost_bps=0)
        b = research.evaluate(rows, 5, 10, cost_bps=10)
        self.assertLess(b['summaries']['buy_hold']['net_total_return'], a['summaries']['buy_hold']['net_total_return'])
        self.assertEqual(b['summaries']['buy_hold']['total_turnover'], 2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
