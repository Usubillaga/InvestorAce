from datetime import datetime
import unittest

from codex_trading import fresh, settle, value, advance, site_pages
from pathlib import Path
from tempfile import TemporaryDirectory


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
