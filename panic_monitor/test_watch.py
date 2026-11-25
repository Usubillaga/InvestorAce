import unittest
from datetime import datetime
from unittest.mock import Mock, patch

import pandas as pd

from . import market, watch
from .weights import sp_weights


def dt(stamp):
    return datetime.fromisoformat('2026-11-' + stamp + '+00:00')


def reading(value, time='25T18:00', baseline=32):
    return dict(heat=value, as_of=dt(time).isoformat(), session='2026-11-' + time[:2],
                close=dt(time[:2]+'T21:00').isoformat(), previous_close=baseline)


class PanicWatchTests(unittest.TestCase):
    def test_calendar_including_black_friday(self):
        for stamp in ('26T15:00', '27T14:29', '27T18:00', '28T15:00'):
            self.assertIsNone(market.session(dt(stamp)))
        self.assertEqual(market.session(dt('27T17:42'))[1], dt('27T18:00'))

    def test_threshold_rearming_and_cross_day_dedup(self):
        state = {}
        for v, t in [(20, '25T16:00'), (19.999, '25T16:30')]:
            watch.advance(state, reading(v, t))
        self.assertEqual(state.pop('pending')['heat'], 19.999)
        watch.advance(state, reading(17, '25T17:00'))
        watch.advance(state, reading(16, '27T15:00', baseline=18))
        self.assertNotIn('pending', state)
        watch.advance(state, reading(20, '27T15:30', baseline=18))
        watch.advance(state, reading(19, '27T16:00', baseline=18))
        self.assertEqual(state['pending']['prior'], 20)

    def test_partial_delivery_resumes_once_and_ignores_out_of_order(self):
        state = {}
        watch.advance(state, reading(18, '25T17:00'))
        key = state['pending']['as_of']
        watch.advance(state, reading(19, '25T17:30'))
        watch.advance(state, reading(30, '25T17:15'))
        self.assertEqual(state['pending']['as_of'], key)
        feed = object.__new__(watch.Feed)
        feed.api, feed.root, feed.save = Mock(), 'https://example.test', Mock()
        res = feed.api.get.return_value
        res.links = {}
        res.json.return_value = [dict(body='<!-- panic-crossing '+key+' -->',
                                     user={'login':'github-actions[bot]'}, html_url='url')]
        feed.deliver(state, lambda: dt('25T17:32'))
        self.assertNotIn('pending', state)
        feed.api.post.assert_not_called()

    def test_expired_signal_never_delivered(self):
        feed = object.__new__(watch.Feed)
        feed.api, feed.root = Mock(), 'https://example.test'
        res = feed.api.get.return_value
        res.links, res.json.return_value = {}, []
        state = {}
        watch.advance(state, reading(18))
        for t in ('25T19:00', '25T21:01', '27T16:00'):
            feed.deliver(state, lambda: dt(t))
        feed.api.post.assert_not_called()

    def test_stale_vix_and_premarket_prices_are_rejected(self):
        for t in ('25T16:20', '25T14:29'):
            now = dt('25T17:00' if t.endswith('16:20') else '25T14:31')
            meta = {'regularMarketTime': dt(t).timestamp(), 'regularMarketPrice': 20,
                    'currentTradingPeriod': {'regular': {'end':dt('25T21:00').timestamp()}}}
            with patch.object(market, 'chart', return_value=(pd.Series(dtype=float),meta)):
                with self.assertRaises(ValueError):
                    market.usable_series('^VIX', now)

    def test_read_only_market_reconstruction_and_missing_breadth(self):
        day = pd.Timestamp('2026-11-25')
        days = pd.bdate_range(end=day, periods=252)
        now = dt('25T18:00')
        symbols = {f'S{i}' for i in range(25)}
        def sample(symbol):
            history = pd.Series(100., index=days)
            history.iloc[-1] = 90.
            if symbol == '^VIX':
                history[:] = 35.
            if sparse and symbol in symbols:
                history.iloc[-40] = float('nan')
            return history, now
        for sparse, parts in [(False, 4), (True, 3)]:
            with patch.object(market, 'usable_series', side_effect=sample):
                r = market.observe(now, symbols)
            self.assertEqual(r['components'], parts)
            self.assertLess(r['heat'], 20)
        def outage(symbol):
            hist, stamp = sample(symbol)
            if symbol in symbols:
                hist.iloc[-1] = float('nan')
            return hist, stamp
        with patch.object(market, 'usable_series', side_effect=outage):
            with self.assertRaises(ValueError):
                market.observe(now, symbols)

    def test_notify_in_time_with_rankings_and_no_other_writes(self):
        feed = object.__new__(watch.Feed)
        feed.api, feed.root, feed.save = Mock(), 'https://example.test', Mock()
        res = feed.api.get.return_value
        res.links, res.json.return_value = {}, []
        feed.api.post.return_value.json.return_value = {'html_url':'https://example.test/alert'}
        weights = {k:dict(as_of='2026-11-02', source='https://example.test/weights',
                          rows=[dict(name='Apple',ticker='AAPL',pct=8.)]) for k in ('SPX','NDX')}
        state = {'weights':weights}
        r = reading(19)
        r.update(checked_at=r['as_of'], components=3, breadth_count=0, source=market.SOURCE+'%5EGSPC',
                 method=market.METHOD, previous_session='2026-11-24')
        watch.advance(state, r)
        feed.deliver(state, lambda: dt('25T18:04'))
        args, kwargs = feed.api.post.call_args
        self.assertTrue(args[0].endswith('/issues/241/comments'))
        body = kwargs['json']['body']
        for token in ['@Usubillaga', '19.000', 'CET', 'EST', 'veraltet', 'AAPL', 'Nasdaq-100', '3/4']:
            self.assertIn(token, body)
        self.assertNotIn('pending', state)
        feed.api.post.assert_called_once()

    def test_index_table_and_date_grade(self):
        rows = '<table><thead><tr><th>Name</th><th>Weight</th></tr></thead><tbody><tr><td>Apple Inc.</td><td>{}</td></tr></tbody></table>'
        html = '<h3>Fund Top Holdings</h3>'+rows.format('8.31%')+'<h3>Index Top Holdings <span class="date">as of Nov 24 2026</span></h3>'+rows.format('8.33%')
        stamp, data = sp_weights(html)
        self.assertEqual(str(stamp),'2026-11-24')
        self.assertEqual(data,[('Apple Inc.', 'AAPL', 8.33)])
        self.assertEqual(watch.grade('2026-11-02','2026-11-25','2026-11-24'),'veraltet')
