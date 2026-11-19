from datetime import datetime
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import evidence
from codex_trading import FILE, advance, fresh, settle, site_pages, tracked_symbols, update, value


def instant(day):
    return datetime.fromisoformat(day + 'T23:00:00+00:00')


class PaperLedger(unittest.TestCase):
    def test_fill_after_decision_fx_dividends_and_replay(self):
        account = fresh()['accounts']['timing']
        order = dict(ticker='A', symbol='A', side='Buy', currency='USD', sector='Tech', euros=1200.,
                     submitted=instant('2026-11-16').isoformat(), expires='2026-11-23', status='Pending')
        account['orders'].append(order)
        bars = {'A': {'2026-11-16': ('2026-11-13', 1.5, 100.),
                      '2026-11-17': ('2026-11-16', 1.1, 110.),
                      '2026-11-18': ('2026-11-17', 1.02, 110.)}}
        rates = {'2026-11-16': 1., '2026-11-17': 1.2, '2026-11-18': 1.1}
        settle(account, bars, rates, instant('2026-11-18'))
        self.assertEqual(order['day'], '2026-11-17')
        expected = 10000 - 1201.2 + 1200 * 1.2 * 1.02 / 1.1
        self.assertAlmostEqual(value(account), expected)
        settle(account, bars, rates, instant('2026-11-18'))
        self.assertAlmostEqual(value(account), expected)
        self.assertAlmostEqual(account['fees'], 1.2)

    def test_one_decision_per_completed_session(self):
        now = instant('2026-11-19')
        record = {'_evidence': {'captured_at': now.isoformat(), 'inputs': {},
                  'macro': {'pulse': {'tracked': {'^GSPC': [['2026-11-19', 6000]]}}}}}
        build = {'manifest': {'run_id': 'example'}, 'record': record}
        doc = fresh()
        self.assertTrue(advance(doc, build, now))
        self.assertFalse(advance(doc, build, now))
        self.assertEqual(len(doc['decisions']), 1)
        with TemporaryDirectory() as folder:
            self.assertIn('Awaiting the first verified close',site_pages(Path(folder))[0][1])

    def test_account_values_require_replay_from_committed_lineage(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            history = root / 'history'
            bundle = {'sources': {'engine.py': 'fixture'}}
            bundle['sha256'] = evidence.digest(bundle['sources'])

            def publish(day):
                pulse = {'tracked': {'^GSPC': [[day, 6000.]]}}
                record = evidence.create_record({}, {}, {'pulse': pulse}, {}, bundle['sha256'],
                                                instant(day).isoformat())
                return evidence.publish_build(record, bundle, '<html>Report</html>',
                                              root=history, report_path=root / 'index.html')

            publish('2026-11-18')
            first_pointer = (history / '_current.json').read_text()
            update(root, now=instant('2026-11-18'))
            journal = root / FILE
            original = journal.read_text()
            publish('2026-11-19')
            newest = evidence.current_build(history)
            self.assertIn('€10,000.00', site_pages(root, newest)[0][1])

            doc = json.loads(original)
            doc['accounts']['timing']['cash'] = 43210.
            journal.write_text(json.dumps(doc))
            with self.assertLogs(level='WARNING'):
                self.assertNotIn('43,210', site_pages(root, newest)[0][1])
                self.assertEqual(tracked_symbols(root), [])
                update(root, now=instant('2026-11-19'))
            self.assertEqual(json.loads(journal.read_text()), doc)

            journal.write_text(original)
            update(root, now=instant('2026-11-19'))
            self.assertEqual(len(json.loads(journal.read_text())['decisions']), 2)
            # An intact archived build outside the selected pointer's lineage is ineligible.
            (history / '_current.json').write_text(first_pointer)
            with self.assertLogs(level='WARNING'):
                self.assertIn('journal could not be verified', site_pages(root)[0][1])
