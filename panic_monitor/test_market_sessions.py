import unittest

import exchange_calendars as xcals
import pandas as pd

from panic_monitor.published import score_session


class Sessions(unittest.TestCase):
    def test_holidays_in_other_countries_do_not_clear_us_breadth(self):
        day = '2026-11-25'
        us = xcals.get_calendar('XNYS').sessions_in_range('2025-11-20', day).tz_localize(None)
        de = xcals.get_calendar('XETR').sessions_in_range('2025-11-20', day).tz_localize(None)
        def pair(dates, sign):
            prices = pd.Series(500.0 + sign * pd.RangeIndex(len(dates)), index=dates)
            return prices, None

        pairs = {f'us{i}': pair(us, 1) for i in range(24)}
        pairs.update({f'de{i}': pair(de, -1) for i in range(6)})
        pairs.update({'^VIX': (pd.Series(25.0, index=us), None), '^GSPC': pair(us, 1)})
        result = score_session(pairs, day)
        self.assertEqual(result['components']['universe_above_ma200']['count'], 30)
        self.assertEqual(result['components']['universe_above_ma200']['score'], 80)
        self.assertEqual(result['heat'], 78.4)
        with_sentiment = score_session(pairs, day, {'value': 0, 'date': day})
        self.assertEqual(with_sentiment['heat'], 62.7)
        pairs['us1'][0].iloc[-1] = float('nan')
        self.assertEqual(score_session(pairs, day)['components']['universe_above_ma200']['count'], 29)

    def test_two_simultaneous_crossings_create_one_notification(self):
        from datetime import datetime
        from unittest.mock import Mock
        from panic_monitor import watch
        now = datetime.fromisoformat('2026-11-25T18:05:00+00:00')
        event = dict(heat=19.9, as_of='2026-11-25T18:00:00+00:00', checked_at=now.isoformat(),
                     session='2026-11-25', previous_session='2026-11-24', previous_close=None,
                     close='2026-11-25T21:00:00+00:00', components=4, breadth_count=100,
                     source='https://example.test/quote', method='https://example.test/method')
        ranks = {k:dict(as_of='2026-11-24', source='https://example.test/weights', rows=[])
                 for k in ('SPX','NDX')}
        state = {'weights':ranks, 'dashboard':{}}
        watch.advance(state, event)
        watch.advance(state['dashboard'], {**event, 'indicator':'market-pulse-v1', 'heat':18.4})
        feed = object.__new__(watch.Feed)
        feed.api, feed.root, feed.save = Mock(), 'https://example.test', Mock()
        res = feed.api.get.return_value
        res.links, res.json.return_value = {}, []
        feed.api.post.return_value.json.return_value = {'html_url':'https://example.test/comment'}
        feed.deliver(state, lambda: now)
        body = feed.api.post.call_args.kwargs['json']['body']
        for token in ('Market Thermometer', 'Index-Leader', '18.400', '19.900', '5 min', 'verzögert', 'EST', 'CET'):
            self.assertIn(token, body)
        feed.deliver(state, lambda: now)
        feed.api.post.assert_called_once()
        self.assertEqual(state['last_alert'], state['dashboard']['last_alert'])
