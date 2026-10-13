"""Source gaps stay visible without changing valuation or frozen evidence."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import evidence
from test_evidence_framework import row
from test_framework_contract import engine


def status(tickers=('RCAT', 'GRAB')):
    return {'schema': 'filing-monitoring-v1', 'entries': {
        ticker: {'status': 'PARTIAL', 'checked_at': '2026-10-13T09:18:00Z',
                 'reason': 'Cached filing list <not complete>',
                 'next_review': 'Reconcile the missing interval against primary filings.',
                 'sources': ['https://www.sec.gov/Archives/edgar/data/748268/']}
        for ticker in tickers}}


class FilingMonitoring(unittest.TestCase):
    def renderer(self, rows, monitoring):
        self.assertTrue(callable(getattr(engine, 'filing_monitoring', None)),
                        'Report has no filing-coverage diagnostic yet')
        with patch.object(engine, 'DATA', rows), \
             patch.object(engine, 'sector_performance', return_value={}), \
             patch.object(engine, 'forward_run', return_value={'ok': False, 'note': 'offline'}):
            return engine.build_html(macro={'ok': False}, write=False,
                                     monitoring=engine.filing_monitoring(json.dumps(monitoring)))

    def test_complete_quotes_do_not_hide_ticker_filing_gaps(self):
        rows = {ticker: dict(row(), yf=ticker) for ticker in ('RCAT', 'GRAB', 'OTHER')}
        html = self.renderer(rows, status())
        self.assertIn('Quote coverage: COMPLETE', html)
        self.assertIn('Filing coverage: PARTIAL', html)
        for ticker in ('RCAT', 'GRAB'):
            self.assertIn(f'href="#filing-{ticker}"', html)
            self.assertIn(f'id="filing-{ticker}"', html)
        self.assertEqual(html.count('FILING GAP</a>'), 2)
        self.assertIn('2026-10-13T09:18:00Z', html)
        self.assertIn('&lt;not complete&gt;', html)
        self.assertNotIn('Cached filing list <not complete>', html)
        self.assertNotIn('href="#filing-OTHER"', html)
        self.assertIn('not a full-coverage certification', html)

    def test_resolved_gap_removes_badge_and_absence_is_not_certified_complete(self):
        doc = status(('RCAT',))
        doc['entries']['RCAT']['status'] = 'RESOLVED'
        html = self.renderer({'RCAT': row()}, doc)
        self.assertNotIn('FILING GAP</a>', html)
        self.assertIn('Filing coverage: NO RECORDED GAPS', html)
        empty = self.renderer({'RCAT': row()}, {'schema': doc['schema'], 'entries': {}})
        self.assertIn('Filing coverage: NOT RECORDED', empty)
        self.assertNotIn('Filing coverage: COMPLETE', empty)

    def test_invalid_metadata_cannot_publish_unsafe_or_undated_warnings(self):
        self.assertTrue(callable(getattr(engine, 'filing_monitoring', None)))
        for field, value in [('status', 'GOOD'), ('checked_at', '2026-10-13'),
                             ('sources', ['javascript:alert(1)']),
                             ('sources', ['https://:1234']),
                             ('sources', ['https://sec.gov:bad']), ('reason', '')]:
            with self.subTest(field=field):
                doc = status(('RCAT',))
                doc['entries']['RCAT'][field] = value
                with self.assertRaises(ValueError):
                    engine.filing_monitoring(json.dumps(doc))

    def test_open_warnings_require_an_explicit_resolution_before_removal(self):
        self.assertTrue(callable(getattr(engine, 'validate_filing_transition', None)))
        empty = {'schema': 'filing-monitoring-v1', 'entries': {}}
        previous = status(('RCAT',))
        with self.assertRaisesRegex(ValueError, 'RCAT.*RESOLVED'):
            engine.validate_filing_transition(empty, previous)
        resolved = copy.deepcopy(previous)
        resolved['entries']['RCAT']['status'] = 'RESOLVED'
        engine.validate_filing_transition(resolved, previous)
        engine.validate_filing_transition(empty, resolved)

    def test_dropped_warning_prevents_publication_and_preserves_previous_pair(self):
        from test_evidence_framework import directory
        rows = {'RCAT': dict(row(), yf='RCAT')}
        with tempfile.TemporaryDirectory() as tmp, directory(tmp):
            old_bundle = {'sources': {'monitoring_status.json': json.dumps(status(('RCAT',)))}}
            old_bundle['sha256'] = evidence.digest(old_bundle['sources'])
            new_bundle = {'sources': {}}
            new_bundle['sha256'] = evidence.digest(new_bundle['sources'])
            with patch.object(engine, 'DATA', rows):
                record = engine.observation({'ok': False}, old_bundle, '2026-10-13T09:19:00Z')
                evidence.publish_build(record, old_bundle, 'last good report')
                pointer = Path('history/_current.json').read_bytes()
                with patch.object(engine, 'sync_risk_free'), \
                     patch.object(engine, 'bootstrap_fundamentals'), \
                     patch.object(engine, 'fetch_prices'), patch.object(engine, 'populate_epv'), \
                     patch.object(engine, 'read_macro', return_value={'ok': False}), \
                     patch.object(engine.EVIDENCE, 'model_bundle', return_value=new_bundle), \
                     patch.object(engine, 'freeze_cohorts'), \
                     patch.object(engine, 'build_html', return_value='unexpected report') as render:
                    with self.assertRaisesRegex(ValueError, 'RCAT.*RESOLVED'):
                        engine.run_build()
                    render.assert_not_called()
                self.assertEqual(Path('history/_current.json').read_bytes(), pointer)
                self.assertEqual(evidence.current_build()['report_path'].read_text(), 'last good report')

    def test_warning_is_bound_to_archived_generation_and_cannot_change_outputs(self):
        rows = {ticker: dict(row(), yf=ticker) for ticker in ('RCAT', 'GRAB')}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'monitoring_status.json'
            source.write_text(json.dumps(status()), encoding='utf-8')
            bundle = evidence.model_bundle(root)
            self.assertIn('monitoring_status.json', bundle['sources'])
            doc = status()
            for entry in doc['entries'].values():
                entry['status'] = 'RESOLVED'
            source.write_text(json.dumps(doc), encoding='utf-8')
            self.assertNotEqual(bundle['sha256'], evidence.model_bundle(root)['sha256'])
            with patch.object(engine, 'DATA', rows):
                record = engine.observation({'ok': False}, bundle, '2026-10-13T09:19:00Z')
                plain = engine.observation({'ok': False}, {'sources': {}, 'sha256': 'control'},
                                           '2026-10-13T09:19:00Z')
            frozen = record['_filing_monitoring']
            self.assertEqual(frozen['entries']['RCAT']['status'], 'PARTIAL')
            for ticker in rows:
                self.assertEqual(record[ticker]['filing_coverage'], frozen['entries'][ticker])
                for field in ('score', 'risk', 'ngv', 'cover', 'cushion', 'verdict', 'regime'):
                    self.assertEqual(record[ticker][field], plain[ticker][field], field)
            self.assertEqual(record['_portfolio_proposal'], plain['_portfolio_proposal'])
            self.assertEqual(record['_evidence']['inputs'], json.loads(json.dumps(rows)))
            html = self.renderer(rows, frozen)
            evidence.publish_build(record, bundle, html, root=root / 'history',
                                   report_path=root / 'index.html')
            current = evidence.current_build(root / 'history')
            self.assertEqual(current['record']['_filing_monitoring'], frozen)
            self.assertIn('FILING GAP</a>', current['report_path'].read_text())

    def test_warning_does_not_change_screens_regime_book_or_portfolio(self):
        rows = copy.deepcopy(engine.DATA)
        for entry in rows.values():
            entry['price'] = 100
        with patch.object(engine, 'DATA', rows):
            before = [engine.screen('quality'), engine.screen('regime', regime='REFLATION'),
                      engine.regime_book('REFLATION'), engine.portfolio_proposal('REFLATION')]
            self.renderer(rows, status())
            after = [engine.screen('quality'), engine.screen('regime', regime='REFLATION'),
                     engine.regime_book('REFLATION'), engine.portfolio_proposal('REFLATION')]
        self.assertEqual(before, after)


if __name__ == '__main__':
    unittest.main()
