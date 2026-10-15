import copy
import json
import unittest
from unittest.mock import Mock, patch

import pandas as pd

import timing
from test_framework_contract import engine


AS_OF = '2026-10-15T12:00:00+00:00'


def history(count=220, end='2026-10-14', tz='UTC', price=100.0):
    index = pd.bdate_range(end=end, periods=count, tz=tz)
    return pd.DataFrame({'High': price + 1, 'Low': price - 1, 'Close': price}, index=index)


class TimingCalculation(unittest.TestCase):
    def test_known_sma_seeded_ema_and_wilder_atr(self):
        bars = history()
        bars.iloc[-1] = [121.0, 119.0, 120.0]
        result = timing.calculate(bars, AS_OF)
        self.assertEqual(result['status'], 'AVAILABLE')
        self.assertEqual(result['trend'], 'ABOVE_SMA200')
        self.assertAlmostEqual(result['sma200'], 100.1)
        self.assertAlmostEqual(result['ema21'], 100 + 20 / 11)
        self.assertAlmostEqual(result['atr14'], 47 / 14)
        self.assertAlmostEqual(result['extension_atr'], (120 - (100 + 20 / 11)) / (47 / 14))
        self.assertEqual(result['last_bar'][:10], '2026-10-14')
        self.assertEqual(result['parameters'], {'sma': 200, 'ema': 21, 'atr': 14})
        self.assertEqual(len(result['input_sha256']), 64)
        json.dumps(result, allow_nan=False)

    def test_current_and_future_bars_do_not_change_past_observation(self):
        bars = history()
        before = bars.copy(deep=True)
        extra = history(2, end='2026-10-16', price=999)
        full = pd.concat([bars, extra])
        self.assertEqual(timing.calculate(bars, AS_OF), timing.calculate(full, AS_OF))
        pd.testing.assert_frame_equal(before, bars)

    def test_cutoff_uses_exchange_local_date(self):
        bars = history(end='2026-10-15', tz='Asia/Tokyo')
        result = timing.calculate(bars, '2026-10-14T18:30:00+00:00')
        self.assertEqual(result['last_bar'][:10], '2026-10-14')
        self.assertEqual(result['source_timezone'], 'Asia/Tokyo')

    def test_insufficient_history_and_missing_columns_are_explicit(self):
        short = timing.calculate(history(199), AS_OF)
        self.assertEqual(short['status'], 'UNAVAILABLE')
        self.assertIn('200', short['reason'])
        self.assertIsNone(short['trend'])
        self.assertIsNone(short['extension_atr'])
        missing = timing.calculate(history().drop(columns=['Low']), AS_OF)
        self.assertEqual(missing['status'], 'UNAVAILABLE')
        self.assertIn('OHLC', missing['reason'])

    def test_invalid_ohlc_is_not_silently_dropped_or_filled(self):
        for value in (float('nan'), float('inf'), 0, -10, True):
            with self.subTest(value=value):
                bars = history().astype(object)
                bars.iloc[50, bars.columns.get_loc('Close')] = value
                result = timing.calculate(bars, AS_OF)
                self.assertEqual(result['status'], 'UNAVAILABLE')
                self.assertIsNone(result['trend'])
                json.dumps(result, allow_nan=False)
        bars = history()
        bars.iloc[-1] = [99, 101, 100]
        self.assertEqual(timing.calculate(bars, AS_OF)['status'], 'UNAVAILABLE')

    def test_duplicate_unordered_and_naive_dates_are_rejected(self):
        bars = history()
        bad = [pd.concat([bars, bars.iloc[[-1]]]), bars.iloc[::-1], bars.tz_localize(None)]
        for frame in bad:
            with self.subTest(index=frame.index):
                self.assertEqual(timing.calculate(frame, AS_OF)['status'], 'UNAVAILABLE')

    def test_stale_values_are_labelled_and_zero_atr_has_no_extension(self):
        stale = timing.calculate(history(end='2026-09-30'), AS_OF)
        self.assertEqual(stale['status'], 'STALE')
        self.assertGreater(stale['age_calendar_days'], 7)
        flat = history()
        flat[['High', 'Low', 'Close']] = 100
        result = timing.calculate(flat, AS_OF)
        self.assertEqual(result['status'], 'PARTIAL')
        self.assertEqual(result['trend'], 'AT_SMA200')
        self.assertIsNone(result['extension_atr'])
        self.assertIn('ATR', result['reason'])


class TimingIntegration(unittest.TestCase):
    def test_existing_history_pull_is_shared_and_legacy_momentum_unchanged(self):
        bars = history(280)
        bars['Close'] = [100 + i for i in range(len(bars))]
        bars['High'], bars['Low'] = bars['Close'] + 1, bars['Close'] - 1
        ticker = Mock()
        ticker.history.return_value = bars
        row = {}
        engine._fetch_momentum(ticker, row)
        ticker.history.assert_called_once_with(period='13mo', auto_adjust=True)
        self.assertEqual(row['mom_12_1'], round(100 * (bars['Close'].iloc[-21] / 100 - 1), 1))
        self.assertEqual(row['from_high'], 0)
        self.assertIn('timing', row)
        self.assertEqual(row['timing']['schema'], timing.VERSION)

    def test_fetch_failure_never_retains_previous_timing(self):
        row = {'timing': timing.calculate(history(), AS_OF)}
        ticker = Mock()
        ticker.history.side_effect = RuntimeError('offline')
        engine._fetch_momentum(ticker, row)
        self.assertEqual(row['timing']['status'], 'UNAVAILABLE')
        self.assertIn('RuntimeError', row['timing']['reason'])

    def test_optional_timing_failure_does_not_suppress_legacy_momentum(self):
        ticker = Mock()
        ticker.history.return_value = history(280)
        row = {}
        with patch.object(engine.TIMING, 'calculate', side_effect=RuntimeError('diagnostic failed')):
            engine._fetch_momentum(ticker, row)
        self.assertEqual(row.get('mom_12_1'), 0)
        self.assertEqual(row.get('from_high'), 0)
        self.assertEqual(row['timing']['status'], 'UNAVAILABLE')

    def test_rejected_quote_clears_previous_timing_without_history_request(self):
        row = engine._regime_fixture('Pharma', .7, 7, 8)
        row.update(yf='TEST', cur='USD', timing=timing.calculate(history(), AS_OF))
        ticker = Mock()
        ticker.fast_info = {'last_price': 0, 'currency': 'USD'}
        with patch.object(engine, 'DATA', {'TEST': row}), patch.object(engine.yf, 'Ticker', return_value=ticker):
            engine.fetch_prices()
        self.assertEqual(row['timing']['status'], 'UNAVAILABLE')
        ticker.history.assert_not_called()

    def test_observation_freezes_timing_and_version(self):
        row = engine._regime_fixture('Pharma', .7, 7, 8)
        row.update(yf='TEST', cur='USD', held=False)
        row['timing'] = timing.calculate(history(), AS_OF)
        original = copy.deepcopy(row['timing'])
        with patch.object(engine, 'DATA', {'TEST': row}):
            record = engine.observation({'ok': False}, {'sources': {}, 'sha256': 'test'})
        self.assertEqual(record['TEST']['timing'], original)
        self.assertEqual(record['_models']['timing'], timing.VERSION)
        row['timing']['trend'] = 'changed later'
        self.assertEqual(record['TEST']['timing'], original)


if __name__ == '__main__':
    unittest.main()
