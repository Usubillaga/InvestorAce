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


class QuoteCloses(unittest.TestCase):
    def test_fills_the_missing_session_from_a_quote_after_the_close(self):
        import market_pulse as mp
        pulse = dict(tracked={'GEN': [['2026-11-11', 30.64]], 'WKL.AS': [['2026-11-11', 88.42]],
                              'MO': [['2026-11-11', 77.39]], 'AB': [['2026-11-12', 10.0]], 'X': [['2026-11-11', 5.0]]})
        rows = {'GEN': dict(price=29.69, quote_observed_at='2026-11-12T21:00:01+00:00', quote_time_status='REGULAR_MARKET'),
                'WKL.AS': dict(price=89.5, quote_observed_at='2026-11-12T16:35:20+00:00', quote_time_status='REGULAR_MARKET'),
                'MO': dict(price=77.9, quote_observed_at='2026-11-12T18:30:00+00:00', quote_time_status='REGULAR_MARKET'),
                'AB': dict(price=11.0, quote_observed_at='2026-11-12T21:00:00+00:00', quote_time_status='REGULAR_MARKET'),
                'X': dict(price=6.0, quote_observed_at='2026-11-12T21:00:00+00:00', quote_time_status='CACHED_DATED')}
        self.assertEqual(mp.add_quote_closes(pulse, rows), ['GEN', 'WKL.AS'])
        self.assertEqual(pulse['tracked']['GEN'][-1], ['2026-11-12', 29.69])
        self.assertEqual(pulse['tracked']['MO'][-1][0], '2026-11-11')      # intraday quote: not a close
        self.assertEqual(pulse['tracked']['AB'], [['2026-11-12', 10.0]])   # the download already has the day
        self.assertEqual(pulse['tracked']['X'][-1][0], '2026-11-11')       # cached quote: not used
        self.assertEqual(pulse['tracked_from_quote'], ['GEN', 'WKL.AS'])
