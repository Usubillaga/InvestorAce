"""Build failures must preserve the last committed report/evidence pair."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import evidence
import forward
from integrity import numeric_input_faults
from test_evidence_framework import directory, row
from test_framework_contract import engine

HERE = Path(__file__).parent


class NumericBoundaries(unittest.TestCase):
    def test_bad_inputs_are_blocked_before_derived_arithmetic(self):
        for field in ('price', 'shares', 'r', 'r_wacc', 'fcf', 'epv_value', 'dil', 'weight'):
            for value in (float('nan'), float('inf'), float('-inf'), True, '1'):
                with self.subTest(field=field, value=value):
                    rows = {'TEST': dict(row(), **{field: value})}
                    with patch.object(engine, 'DATA', rows), \
                         patch.object(engine, 'ngv', side_effect=AssertionError('arithmetic ran')):
                        faults, _ = engine.validate_full()
                    self.assertTrue(any(field in fault for fault in faults))

    def test_positive_inputs_reject_zero_and_negative_values(self):
        for field in ('price', 'shares', 'r', 'r_wacc', 'epv_wacc'):
            for value in (0, -1):
                with self.subTest(field=field, value=value):
                    self.assertTrue(numeric_input_faults({'TEST': dict(row(), **{field: value})}))

    def test_optional_inputs_and_negative_epv_remain_supported(self):
        d = dict(row(), price=None, fcf=None, shares=None, epv_value=-10)
        self.assertEqual(numeric_input_faults({'TEST': d}), [])

    def test_malformed_components_are_not_a_fixed_score_fallback(self):
        for sub in ([], [1] * 5, '123456', [1] * 5 + [float('nan')], [11] * 6):
            with self.subTest(sub=sub):
                self.assertTrue(numeric_input_faults({'TEST': dict(row(), sub=sub)}))

    def test_invalid_static_input_prevents_fetch_and_publish(self):
        with tempfile.TemporaryDirectory() as tmp, directory(tmp):
            with patch.object(engine, 'DATA', {'TEST': dict(row(), shares=0)}), \
                 patch.object(engine, 'bootstrap_fundamentals') as fetch:
                with self.assertRaisesRegex(ValueError, 'shares must be positive'):
                    engine.run_build()
                fetch.assert_not_called()
            self.assertFalse(Path('history/_current.json').exists())

    def test_required_module_failure_is_not_a_validated_fallback(self):
        with patch.object(engine, 'WACC', None):
            faults, _ = engine.validate_full()
        self.assertIn('required module wacc is unavailable', faults)


class RuntimeImports(unittest.TestCase):
    def test_real_runtime_imports_in_clean_process(self):
        result = subprocess.run([sys.executable, '-c',
                                 'import engine, integrity, evidence, wacc, epv, forward, macro'],
                                cwd=HERE, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_broken_required_module_keeps_its_traceback(self):
        for name, source, error in (
            ('wacc.py', "raise RuntimeError('broken WACC implementation')\n", 'broken WACC implementation'),
            ('forward.py', '# missing required exports\n', "cannot import name 'run'"),
        ):
            with self.subTest(module=name), tempfile.TemporaryDirectory() as tmp:
                Path(tmp, name).write_text(source)
                result = subprocess.run([sys.executable, '-c', 'import engine'], cwd=tmp,
                                        env=dict(os.environ, PYTHONPATH=str(HERE)),
                                        capture_output=True, text=True, timeout=30)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(error, result.stderr)


class QuoteCoverage(unittest.TestCase):
    def test_invalid_unbounded_quotes_never_enter_the_report(self):
        for value in (0, -1, float('nan'), float('inf')):
            with self.subTest(price=value):
                class Quote:
                    fast_info = {'currency': 'USD', 'last_price': value}
                rows = {'TEST': row()}
                with patch.object(engine, 'DATA', rows), patch.object(engine.yf, 'Ticker', return_value=Quote()):
                    engine.fetch_prices()
                self.assertIsNone(rows['TEST']['price'])
                self.assertIn('REJECTED invalid quote', rows['TEST']['price_note'])

    def test_missing_quote_cannot_produce_an_action_or_screen_candidate(self):
        d = dict(row(), held=True, weight=10, price=None, score_fixed=9.5,
                 price_note='REJECTED outside band')
        with patch.object(engine, 'DATA', {'TEST': d}):
            self.assertEqual(engine.verdict('TEST', d)[0], 'NO QUOTE')
            self.assertEqual(engine.screen('quality'), [])
            quality = engine.data_quality()
            self.assertEqual(quality['status'], 'DEGRADED')
            self.assertEqual(quality['held_missing_quotes'], ['TEST'])
            with patch.object(engine, 'sector_performance', return_value={}), \
                 patch.object(engine, 'forward_run', return_value={'ok': False, 'note': 'offline'}):
                html = engine.build_html(macro={'ok': False}, write=False)
            self.assertIn('Quote coverage: DEGRADED', html)
            self.assertIn('REJECTED outside band', html)

    def test_ngv_unavailable_does_not_hide_quote_issues(self):
        d = dict(row(), na='no applicable NGV', fcf=None, price=None, price_note='no quote')
        with patch.object(engine, 'DATA', {'TEST': d}), \
             patch.object(engine, 'sector_performance', return_value={}), \
             patch.object(engine, 'forward_run', return_value={'ok': False, 'note': 'offline'}):
            html = engine.build_html(macro={'ok': False}, write=False)
        self.assertTrue('Price issues this run' in html)
        self.assertTrue('TEST: no quote' in html)

    def test_wacc_data_failure_is_visible_with_manual_rate(self):
        class Quote:
            fast_info = {'currency': 'USD', 'last_price': 100}
        rows = {'TEST': dict(row(), sanity=(50, 200))}
        with patch.object(engine, 'DATA', rows), patch.object(engine.yf, 'Ticker', return_value=Quote()), \
             patch.object(engine, '_fetch_momentum'), \
             patch.object(engine.WACC, 'fetch', side_effect=RuntimeError('offline')):
            engine.fetch_prices()
            self.assertIn('TEST', engine.data_quality()['wacc_fallbacks'])
        self.assertNotIn('r_wacc', rows['TEST'])
        self.assertIn('RuntimeError', rows['TEST']['wacc_note'])

    def test_cache_rejects_nonfinite_without_replacing_last_good_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp, 'cache.json')
            cache.write_text('{"last": "good"}')
            with patch.object(engine, 'EPV_CACHE_FILE', str(cache)):
                with self.assertRaises(ValueError):
                    engine._epv_cache_write({'bad': float('nan')})
            self.assertEqual(json.loads(cache.read_text()), {'last': 'good'})


class PairedPublication(unittest.TestCase):
    def record(self, stamp='2026-10-11T12:00:00+00:00', score=7):
        bundle = {'sources': {'engine.py': 'frozen source'}}
        bundle['sha256'] = evidence.digest(bundle['sources'])
        rec = evidence.create_record({'TEST': row()}, {'TEST': {'score': score}}, {'ok': False},
                                     {'engine': 'test'}, bundle['sha256'], stamp)
        return rec, bundle

    def publish(self, tmp, html='<html>first report</html>', stamp='2026-10-11T12:00:00+00:00', score=7):
        rec, bundle = self.record(stamp, score)
        return evidence.publish_build(rec, bundle, html, root=Path(tmp, 'history'),
                                      report_path=Path(tmp, 'index.html'))

    def test_pair_verifies_and_same_day_first_capture_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp, 'history')
            a = self.publish(tmp)
            b = self.publish(tmp, '<html>second report</html>', score=2)
            current = evidence.current_build(root)
            self.assertEqual(current['manifest']['run_id'], b['run_id'])
            self.assertEqual(current['manifest']['previous_run_id'], a['run_id'])
            self.assertEqual(current['report_path'].read_text(), '<html>second report</html>')
            self.assertEqual(current['record']['TEST']['score'], 2)
            self.assertEqual(evidence.daily_records(root)[0][1]['TEST']['score'], 7)
            self.assertTrue(a['daily_created'])
            self.assertFalse(b['daily_created'])

    def test_report_stage_failure_keeps_old_pointer_and_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.publish(tmp)
            root = Path(tmp, 'history')
            before = (root / '_current.json').read_bytes()
            write = evidence.atomic_text
            def fail_report(path, text):
                if Path(path).name == 'index.html':
                    raise OSError('report write failed')
                return write(path, text)
            with patch.object(evidence, 'atomic_text', side_effect=fail_report):
                with self.assertRaisesRegex(OSError, 'report write failed'):
                    self.publish(tmp, '<html>failed report</html>', stamp='2026-10-12T12:00:00+00:00')
            self.assertEqual((root / '_current.json').read_bytes(), before)
            self.assertEqual(Path(tmp, 'index.html').read_text(), '<html>first report</html>')
            self.assertEqual([day for day, _ in evidence.daily_records(root)], ['2026-10-11'])
            self.assertEqual(len(list((root / '_builds').iterdir())), 1)

    def test_pointer_failure_keeps_old_report_and_removes_uncommitted_generation(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.publish(tmp)
            root = Path(tmp, 'history')
            before = (root / '_current.json').read_bytes()
            with patch.object(evidence, 'atomic_json', side_effect=OSError('pointer write failed')):
                with self.assertRaisesRegex(OSError, 'pointer write failed'):
                    self.publish(tmp, '<html>uncommitted</html>', stamp='2026-10-12T12:00:00+00:00')
            self.assertEqual((root / '_current.json').read_bytes(), before)
            self.assertEqual(evidence.current_build(root)['report_path'].read_text(), '<html>first report</html>')
            self.assertEqual(len(list((root / '_builds').iterdir())), 1)
            self.assertFalse((root / '2026-10-12.json').exists())

    def test_observation_stage_failure_never_publishes_the_new_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.publish(tmp)
            root = Path(tmp, 'history')
            before = (root / '_current.json').read_bytes()
            write = evidence.atomic_text
            def fail_observation(path, text):
                if Path(path).name == 'observation.json':
                    raise OSError('observation write failed')
                return write(path, text)
            with patch.object(evidence, 'atomic_text', side_effect=fail_observation):
                with self.assertRaisesRegex(OSError, 'observation write failed'):
                    self.publish(tmp, '<html>uncommitted</html>')
            self.assertEqual((root / '_current.json').read_bytes(), before)
            self.assertEqual(Path(tmp, 'index.html').read_text(), '<html>first report</html>')
            self.assertEqual(len(list((root / '_builds').iterdir())), 1)

    def test_compatibility_mirror_failures_do_not_split_committed_pair(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.publish(tmp)
            root = Path(tmp, 'history')
            write = evidence.atomic_text
            immutable = evidence.immutable_json
            def fail_mirror(path, text):
                if Path(path) == Path(tmp, 'index.html'):
                    raise OSError('mirror write failed')
                return write(path, text)
            def fail_alias(path, value):
                if Path(path).parent == root or Path(path).parent.name == 'runs':
                    raise OSError('archive mirror write failed')
                return immutable(path, value)
            with patch.object(evidence, 'atomic_text', side_effect=fail_mirror), \
                 patch.object(evidence, 'immutable_json', side_effect=fail_alias):
                result = self.publish(tmp, '<html>new authoritative report</html>',
                                      stamp='2026-10-12T12:00:00+00:00', score=2)
            self.assertEqual(len(result['compatibility_warnings']), 3)
            current = evidence.current_build(root)
            self.assertEqual(current['record']['TEST']['score'], 2)
            self.assertEqual(current['report_path'].read_text(), '<html>new authoritative report</html>')
            self.assertEqual(Path(tmp, 'index.html').read_text(), '<html>first report</html>')
            self.assertEqual([day for day, _ in evidence.daily_records(root)], ['2026-10-11', '2026-10-12'])
            with directory(tmp):
                self.assertEqual(forward._days(), evidence.daily_records())

    def test_abandoned_generation_is_not_forward_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.publish(tmp)
            root = Path(tmp, 'history')
            abandoned = root / '_builds' / ('20261012T120000000000-' + 'f' * 32)
            abandoned.mkdir()
            rec, _ = self.record('2026-10-12T12:00:00+00:00')
            (abandoned / 'observation.json').write_text(evidence.canonical(rec))
            self.assertEqual(len(evidence.daily_records(root)), 1)

    def test_same_day_retry_after_failed_daily_mirror_preserves_first_capture(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp, 'history')
            immutable = evidence.immutable_json
            def fail_day(path, value):
                if Path(path) == root / '2026-10-11.json':
                    raise OSError('daily mirror failed')
                return immutable(path, value)
            with patch.object(evidence, 'immutable_json', side_effect=fail_day):
                self.publish(tmp, score=7)
            result = self.publish(tmp, '<html>retry</html>', score=2)
            self.assertFalse(result['daily_created'])
            self.assertEqual(evidence.current_build(root)['record']['TEST']['score'], 2)
            self.assertEqual(evidence.daily_records(root)[0][1]['TEST']['score'], 7)
            self.assertEqual(json.loads((root / '2026-10-11.json').read_text())['TEST']['score'], 7)

    def test_report_and_model_tampering_block_deployment_resolution(self):
        for target in ('report', 'model', 'record'):
            with self.subTest(target=target), tempfile.TemporaryDirectory() as tmp:
                result = self.publish(tmp)
                root = Path(tmp, 'history')
                if target == 'report':
                    Path(result['report_path']).write_text('<html>tampered</html>')
                elif target == 'model':
                    model = next((root / 'models').glob('*.json'))
                    value = json.loads(model.read_text())
                    value['sources']['engine.py'] = 'tampered'
                    model.write_text(json.dumps(value))
                else:
                    path = root / '_builds' / result['run_id'] / 'observation.json'
                    value = json.loads(path.read_text())
                    value['TEST']['score'] = 999
                    path.write_text(json.dumps(value))
                with self.assertRaises(ValueError):
                    evidence.current_build(root)

    def test_existing_legacy_day_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp, 'history')
            root.mkdir()
            day = root / '2026-10-11.json'
            day.write_text('{"TEST": {"score": 3}}')
            before = day.read_bytes()
            result = self.publish(tmp)
            self.assertFalse(result['daily_created'])
            self.assertEqual(day.read_bytes(), before)
            self.assertEqual(evidence.daily_records(root)[0][1]['TEST']['score'], 3)


if __name__ == '__main__':
    unittest.main()
