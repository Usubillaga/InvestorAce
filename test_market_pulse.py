"""Index line and market thermometer: only fetched data, never estimates."""
import unittest
from datetime import date, timedelta

import market_pulse as mp


def series(values, start=date(2025, 11, 1)):
    return [((start + timedelta(days=i)).isoformat(), v) for i, v in enumerate(values)]


class PulseTests(unittest.TestCase):
    def closes(self):
        spx = [100.] * 199 + [110.]
        return {'^GSPC': series(spx), '^VIX': series([20., 19.]), '^NDX': series([200., 198.]),
                'EURUSD=X': series([1.15, 1.16]), 'COP=X': series([3900., 3910.])}

    def test_moves_and_components_are_computed_from_closes(self):
        universe = {f'S{i}': series([10.] * 199 + ([11.] if i < 15 else [9.])) for i in range(25)}
        pulse = mp.summarize(self.closes(), universe, dict(value=28., date='2026-10-30'))
        spx = next(m for m in pulse['moves'] if m['symbol'] == '^GSPC')
        self.assertAlmostEqual(spx['change_pct'], 10.)
        c = pulse['components']
        self.assertAlmostEqual(c['vix']['score'], round((40 - 19) / 30 * 100, 1))
        self.assertEqual(c['universe_above_ma200']['score'], 60.)
        self.assertEqual(c['fear_greed']['score'], 28.)
        self.assertAlmostEqual(pulse['heat'], round(sum(x['score'] for x in c.values()) / len(c), 1))
        self.assertEqual(pulse['band'], mp.band(pulse['heat']))

    def test_too_few_inputs_give_no_heat_and_omissions_are_named(self):
        pulse = mp.summarize({'^VIX': series([20., 19.])}, {})
        self.assertIsNone(pulse['heat'])
        self.assertTrue(any('AAII' in x for x in pulse['omitted']))
        self.assertEqual(mp.thermometer(pulse), '')

    def test_bands(self):
        self.assertEqual([mp.band(x) for x in (5, 25, 54, 70, 95)], ['Panic', 'Fear', 'Neutral', 'Greed', 'Euphoria'])

    def test_strip_and_box_render_and_translate_without_gaps(self):
        import i18n
        universe = {f'S{i}': series([10.] * 200) for i in range(25)}
        pulse = mp.summarize(self.closes(), universe, dict(value=28., date='2026-10-30'))
        html = mp.strip(pulse) + mp.thermometer(pulse)
        self.assertIn('S&amp;P 500</b> 110.00 <span class="pulse-up">+10.00%', html)
        self.assertIn('Market heat', html)
        self.assertEqual(i18n.translation_gaps(html), [])
        self.assertIn('Calor del mercado', i18n.localize(html, 'es'))

    def test_failed_download_returns_none(self):
        def broken(*a, **k):
            raise OSError('offline')
        self.assertIsNone(mp.read(['AAPL'], download=broken, fear_greed=lambda url: {}))


if __name__ == '__main__':
    unittest.main()
