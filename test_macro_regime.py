"""The live regime combines market impulses with dated official data; all five regimes are reachable."""
import html
import unittest
from unittest.mock import patch

import i18n
import macro
from engine import economic_line


def series(values, start_year=2023):
    out = []
    for n, v in enumerate(values):
        y, m = divmod(n, 12)
        out.append({'date': f'{start_year + y}-{m + 1:02d}-01', 'value': v})
    return out


def cpi_path(yoy_now, yoy_3m_ago, months=20):
    """Index whose year-on-year rate moves linearly from yoy_3m_ago to yoy_now."""
    base = [100.0 * (1.0025 ** k) for k in range(12)]
    vals = list(base)
    for k in range(12, months):
        step = min(1.0, max(0.0, (k - (months - 4)) / 3))
        yoy = yoy_3m_ago + (yoy_now - yoy_3m_ago) * step if k >= months - 4 else yoy_3m_ago
        vals.append(vals[k - 12] * (1 + yoy / 100))
    return vals


def economy(cpi_now=2.5, cpi_before=2.5, unemployment=None, payroll_step=150):
    unemployment = unemployment or [4.0] * 20
    return {'cpi': series(cpi_path(cpi_now, cpi_before)),
            'unemployment': series(unemployment),
            'payrolls': series([150000 + payroll_step * k for k in range(20)])}


class SignalTests(unittest.TestCase):
    def test_signals_read_dated_levels_trends_and_labour_gap(self):
        u = [4.0] * 16 + [4.2, 4.4, 4.6, 4.8]
        s = macro.economic_signals(economy(3.7, 3.2, unemployment=u, payroll_step=30))
        self.assertAlmostEqual(s['cpi_yoy'], 3.7, places=1)
        self.assertAlmostEqual(s['cpi_yoy_3m_change'], 0.5, places=1)
        self.assertGreater(s['unemployment_gap'], 0.5)
        self.assertEqual(s['payrolls_3m_avg_thousands'], 30.0)
        self.assertTrue(s['cpi_date'].startswith('2024-'))

    def test_short_or_missing_series_are_omitted_not_invented(self):
        self.assertEqual(macro.economic_signals({}), {})
        self.assertEqual(macro.economic_signals({'cpi': series([100, 101])}), {})

    def test_fred_csv_parser_skips_missing_values(self):
        csv_text = 'observation_date,UNRATE\n2026-08-01,4.3\n2026-09-01,.\n2026-10-01,4.2\n'

        class Response:
            def __enter__(self):
                return self
            def __exit__(self, *a):
                return False
            def read(self):
                return csv_text.encode()
        with patch('urllib.request.urlopen', return_value=Response()):
            self.assertEqual(macro._fred('UNRATE'), [('2026-08-01', 4.3), ('2026-10-01', 4.2)])

    def test_failed_series_is_absent(self):
        def fetch(series_id):
            if series_id == 'PAYEMS':
                raise OSError('blocked')
            return [('2026-01-01', 1.0)]
        self.assertEqual(sorted(macro.economic_data(fetch)), ['cpi', 'unemployment'])


class ClassifyTests(unittest.TestCase):
    def reading(self, g, i, **kw):
        return macro.classify(g, i, macro.economic_signals(economy(**kw)))

    def test_all_five_regimes_are_reachable(self):
        weak = [4.0] * 16 + [4.3, 4.6, 4.9, 5.2]
        cases = {
            'GOLDILOCKS': self.reading(8, -10, cpi_now=2.0, cpi_before=2.4),
            'REFLATION': self.reading(8, 5, cpi_now=2.8, cpi_before=2.7),
            'INFLATION': self.reading(8, 15, cpi_now=4.0, cpi_before=3.4),
            'STAGFLATION': self.reading(-4, 15, cpi_now=3.8, cpi_before=3.3, unemployment=weak, payroll_step=10),
            'RECESSION': self.reading(-10, -10, cpi_now=2.0, cpi_before=2.6, unemployment=weak, payroll_step=-50),
        }
        for expected, got in cases.items():
            with self.subTest(expected):
                self.assertEqual(got['regime'], expected)
                self.assertEqual(got['basis'], macro.REGIME_BASIS)

    def test_rising_stocks_do_not_hide_a_weak_labour_market(self):
        weak = [4.0] * 16 + [4.3, 4.6, 4.9, 5.2]
        got = self.reading(3, 10, cpi_now=3.8, cpi_before=3.3, unemployment=weak, payroll_step=0)
        self.assertEqual(macro.quadrant_of(3, 10), 'REFLATION')
        self.assertEqual(got['regime'], 'STAGFLATION')

    def test_without_economic_data_the_market_quadrant_is_kept(self):
        got = macro.classify(3, 10, {})
        self.assertEqual((got['regime'], got['basis']), ('REFLATION', 'MARKET_ONLY'))


class DisplayTests(unittest.TestCase):
    def test_economic_line_is_dated_and_fully_translated(self):
        signals = macro.economic_signals(economy(3.7, 3.2, payroll_step=30))
        r = macro.classify(5, 10, signals)
        M = dict(regime=r['regime'], regime_basis=r['basis'], growth_score=r['growth_score'],
                 inflation_score=r['inflation_score'], economic=signals, market_regime='REFLATION')
        for line in (economic_line(M), economic_line({'regime_basis': 'MARKET_ONLY'}),
                     'Read off market and official economic data, not opinion.'):
            with self.subTest(line=line[:30]):
                for language in ('de', 'es'):
                    _, missing = i18n._translate(html.unescape(line), language)
                    self.assertEqual(missing, '', (language, line))
        self.assertIn(signals['cpi_date'], economic_line(M))


if __name__ == '__main__':
    unittest.main()
