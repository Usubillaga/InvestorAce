"""Crash monitor: French data parsing, run-up rules, live status, page; retired report series."""
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

import pandas as pd

import crash_monitor as cm
import weekly_research as research
from test_daily_briefing import daily_example


def zipped(name, text):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        archive.writestr(name, text)
    return buffer.getvalue()


def months(n, start=(2020, 1)):
    year, month = start
    out = []
    for _ in range(n):
        out.append(year * 100 + month)
        month += 1
        if month == 13:
            year, month = year + 1, 1
    return out


def bubble(n_before=30, run=24, after=24, crash=True):
    """Monthly returns: flat, a +150% run-up, then a 55% fall or a gentle rise."""
    up = 2.5 ** (1 / run) - 1
    down = (0.45 ** (1 / 12) - 1) if crash else 0.005
    tail = [down] * 12 + [0.] * (after - 12) if crash else [down] * after
    return [0.002] * n_before + [up] * run + tail


class FrenchData(unittest.TestCase):
    def test_parses_sections_missing_values_and_market(self):
        industry = ('Header\n\n  Average Value Weighted Returns -- Monthly\n,Agric,Chips \n'
                    '192607,   2.00, -99.99\n192608,  -1.00,   3.00\n\n'
                    '  Number of Firms in Portfolios\n,Agric,Chips \n192607, 12, 9\n192608, 12, 11\n\n')
        factors = 'Note\n\n,Mkt-RF,SMB,HML,RF\n192607,   2.89,  -2.42,  -2.75,   0.22\n\n Annual Factors\n'
        industries, firms, market = cm.load_french(zipped('a.csv', industry), zipped('b.csv', factors))
        self.assertEqual(industries['Chips'], [(192608, .03)])
        self.assertEqual(industries['Agric'][1], (192608, -.01))
        self.assertEqual(firms['Chips'][192608], 11)
        self.assertAlmostEqual(market[0][1], .0311)


class Rules(unittest.TestCase):
    def series(self, returns):
        stamps = months(len(returns))
        return list(zip(stamps, returns)), [(m, 0.004) for m in stamps]

    def test_run_up_is_found_once_and_a_crash_is_measured_from_the_peak(self):
        series, market = self.series(bubble())
        found = cm.episodes('X', series, market)
        self.assertEqual(len(found), 1)
        episode = found[0]
        self.assertTrue(episode['raw'] > 1 and episode['net'] > 1)
        self.assertTrue(episode['crash'])
        self.assertLessEqual(episode['max_drawdown'], -.4)
        self.assertEqual(len(episode['path']), 2 * cm.HORIZON + 1)
        self.assertEqual(episode['path'][cm.HORIZON], 1.0)

    def test_a_run_up_without_a_fall_is_not_a_crash_and_short_windows_stay_open(self):
        series, market = self.series(bubble(crash=False))
        self.assertFalse(cm.episodes('X', series, market)[0]['crash'])
        series, market = self.series(bubble(after=6, crash=False))
        self.assertFalse(cm.episodes('X', series, market)[0]['complete'])

    def test_small_industries_and_market_wide_rallies_are_not_run_ups(self):
        series, market = self.series(bubble())
        self.assertEqual(cm.episodes('X', series, market, {m: 5 for m, _ in series}), [])
        stamps = [m for m, _ in series]
        same = list(zip(stamps, [r for _, r in series]))
        self.assertEqual(cm.episodes('X', series, same), [])     # net of market is zero

    def test_wilson_interval(self):
        low, high = cm.wilson(25, 67)
        self.assertTrue(low < 25 / 67 < high)
        self.assertEqual(cm.wilson(0, 0), (None, None))

    def test_committed_calibration(self):
        cal = cm.load_calibration()
        self.assertEqual(cal['schema'], cm.SCHEMA)
        self.assertGreaterEqual(cal['base']['n'], 40)
        self.assertTrue(cal['baseline']['p'] < cal['base']['p'])
        self.assertEqual(len(cal['paths']['crash']), 2 * cm.HORIZON + 1)
        self.assertEqual(set(cal['after_drawdown']), {'20', '30'})


class Refresh(unittest.TestCase):
    def test_stale_calibration_is_refreshed_and_failure_keeps_the_old_one(self):
        from datetime import datetime, timezone
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'cal.json'
            path.write_text(json.dumps(dict(schema=cm.SCHEMA, generated_at='2026-01-01T00:00:00+00:00', base={})))
            fresh_now = datetime(2026, 1, 20, tzinfo=timezone.utc)
            def offline(url):
                raise OSError('offline')
            self.assertEqual(cm.fresh_calibration(path, now=fresh_now, fetch=offline, log=lambda *a: None)['base'], {})
            late = datetime(2026, 3, 1, tzinfo=timezone.utc)
            kept = cm.fresh_calibration(path, now=late, fetch=offline, log=lambda *a: None)
            self.assertEqual(kept['generated_at'], '2026-01-01T00:00:00+00:00')
            stamps = months(84, (2015, 1))
            body = '\n'.join(f'{m},{r:.2f}' for m, r in zip(stamps, [100 * x for x in bubble(30, 24, 30)]))
            firms = '\n'.join(f'{m},20' for m in stamps)
            industry = ('x\n\n  Average Value Weighted Returns -- Monthly\n,Chips\n' + body + '\n\n'
                        '  Number of Firms in Portfolios\n,Chips\n' + firms + '\n\n')
            factors = 'x\n\n,Mkt-RF,SMB,HML,RF\n' + '\n'.join(f'{m},0.30,0,0,0.10' for m in stamps) + '\n\n'
            blobs = {cm.FF_BASE + cm.FF_FILES[0]: zipped('a.csv', industry),
                     cm.FF_BASE + cm.FF_FILES[1]: zipped('b.csv', factors)}
            new = cm.fresh_calibration(path, now=late, fetch=blobs.__getitem__, log=lambda *a: None)
            self.assertEqual(new['base']['n'], 1)
            self.assertEqual(json.loads(path.read_text())['base']['n'], 1)


class Live(unittest.TestCase):
    def frame(self, closes):
        index = pd.date_range('2021-11-01', periods=len(next(iter(closes.values()))), freq='MS')
        return pd.DataFrame({('Close', k): v for k, v in closes.items()}, index=index)

    def prices(self, returns, start=100.):
        out = [start]
        for r in returns[1:]:
            out.append(out[-1] * (1 + r))
        return out

    def test_status_of_an_open_run_up_uses_the_drawdown_odds(self):
        cal = cm.load_calibration()
        returns = [0.002] * 30 + [2.5 ** (1 / 24) - 1] * 24 + [-0.05] * 5
        stamps = [f'{m // 100}-{m % 100:02d}-01' for m in months(len(returns))]
        series = list(zip(stamps, self.prices(returns)))
        market = list(zip(stamps, self.prices([0.004] * len(returns))))
        out = cm.status(series, market, cal)
        self.assertEqual(out['state'], 'RUN_UP')
        self.assertEqual(out['probability']['basis'], 'Already fell 20% from the peak')
        self.assertAlmostEqual(out['crash_line'], .6 * out['peak'])
        self.assertIn(out['path_closer_to'], ('crash', 'calm'))

    def test_a_closed_window_is_no_longer_an_open_run_up(self):
        returns = [0.002] * 30 + [2.5 ** (1 / 24) - 1] * 24 + [0.003] * 30
        stamps = [f'{m // 100}-{m % 100:02d}-01' for m in months(len(returns))]
        series = list(zip(stamps, self.prices(returns)))
        market = list(zip(stamps, self.prices([0.004] * len(returns))))
        self.assertEqual(cm.status(series, market, cm.load_calibration())['state'], 'NO_RUN_UP')

    def test_read_builds_industries_and_stocks_and_the_page(self):
        n = 59
        run = self.prices([0.002] * 30 + [2.5 ** (1 / 24) - 1] * 24 + [-0.05] * 5)
        flat = self.prices([0.004] * n)
        closes = {etf: flat for etf, _ in cm.INDUSTRY_ETFS}
        closes.update(SOXX=run, SPY=flat, NVDA=run, KO=flat)
        rows = {'NVDA': dict(yf='NVDA', cur='USD', sector='Semis'),
                'KO': dict(yf='KO', cur='USD', sector='Consumer Defensive'),
                'WKL': dict(yf='WKL.AS', cur='EUR', sector='Info Svcs')}
        monitor = cm.read(rows, download=lambda *a, **k: self.frame(closes))
        soxx = next(i for i in monitor['industries'] if i['etf'] == 'SOXX')
        self.assertEqual(soxx['state'], 'RUN_UP')
        self.assertEqual(soxx['members'], ['NVDA'])
        self.assertEqual([s['ticker'] for s in monitor['stocks']], ['KO', 'NVDA'])   # USD listings only
        record = {'_evidence': {'macro': {'crash_monitor': json.loads(json.dumps(monitor))}}}
        pages = cm.site_pages('.', dict(record=record))
        self.assertEqual([str(p) for p, _ in pages], ['crash-monitor.html'])
        html = pages[0][1]
        for text in ('SOXX · Semiconductors', '<svg', 'Already fell 20% from the peak', 'NVDA', 'Bubbles for Fama'):
            self.assertIn(text, html)
        self.assertEqual(cm.site_pages('.', dict(record={'_evidence': {'macro': {}}})), [])
        self.assertIsNone(cm.read(rows, download=lambda *a, **k: (_ for _ in ()).throw(RuntimeError('offline'))))


class RetiredSeries(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'repo'
        self.output = Path(self.temp.name) / 'public'
        for folder in ('weekly-research', 'daily-briefings'):
            (self.root / folder).mkdir(parents=True)
        self.write('weekly-research/config.json', {'first_issue_date': '2026-10-16', 'schedule_label': 'Fridays',
                                                   'retired_on': '2026-11-09'})
        self.daily = {'first_issue_date': '2026-10-18', 'schedule_label': 'Daily', 'languages': ['es', 'en', 'de'],
                      'default_language': 'de', 'verify_translation_claims': True,
                      'schedule_labels': {'es': 'Cada día', 'de': 'Täglich'}, 'retired_on': '2026-11-09'}
        self.write('daily-briefings/config.json', self.daily)
        self.write('daily-briefings/2026-10-18.json', daily_example())
        (self.root / 'index.html').write_text('<!DOCTYPE html><html><body><h1>Scoreboard</h1></body></html>')

    def write(self, path, value):
        (self.root / path).write_text(json.dumps(value), encoding='utf-8')

    def test_retired_series_leave_the_site_but_return_with_a_newer_edition(self):
        research.build_site(self.root, self.output)
        self.assertFalse((self.output / 'research.html').exists())
        self.assertFalse((self.output / 'daily.html').exists())
        home = (self.output / 'index.html').read_text()
        self.assertNotIn('Friday research', home)
        self.assertNotIn('Daily briefing', home)
        self.assertTrue((self.root / 'daily-briefings' / '2026-10-18.json').exists())   # files stay
        later = daily_example()
        later.update(issue_date='2026-11-10', period_start='2026-11-09', period_end='2026-11-10',
                     data_cutoff='2026-11-10T07:40:00+01:00')
        self.write('daily-briefings/2026-11-10.json', later)
        output = Path(self.temp.name) / 'public2'
        research.build_site(self.root, output)
        self.assertTrue((output / 'daily.html').exists())
        self.assertIn('Daily briefing ↗', (output / 'index.html').read_text())
        self.assertNotIn('Friday research', (output / 'index.html').read_text())
        self.assertNotIn('href="research.html"', (output / 'daily.html').read_text())

    def test_retired_on_must_be_a_date(self):
        self.daily['retired_on'] = 'soon'
        self.write('daily-briefings/config.json', self.daily)
        with self.assertRaises(ValueError):
            research.build_site(self.root, self.output)


if __name__ == '__main__':
    unittest.main()
