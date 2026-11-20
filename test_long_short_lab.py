import json
from datetime import datetime
from pathlib import Path
import tempfile
import unittest

import long_short_lab as lab
import timing


def tech(day, close=97, swap=False):
    return dict(schema=timing.VERSION, status='AVAILABLE', close=close, sma36=100,
                sma50=105 if swap else 98, sma200=100 if swap else 102, atr14=2,
                last_bar=f'{day}T00:00:00-05:00', source_timezone='America/New_York')


def verified_opportunity(score, quality):
    return dict(schema=lab.opportunity.VERSION, as_of='2026-11-17T12:00:00+00:00',
                quote_observed_at='2026-11-17T12:00:00+00:00', financial_period='2026-09-30',
                profile={'tags': []}, components=[], price=100, fundamental_score=score, quality_score=quality)


def snapshot(day, captured, close, score=4., quality=5.):
    at = datetime.fromisoformat(captured).replace(tzinfo=lab.NY)
    return dict(rows={'T': ('T', tech(day, close), verified_opportunity(score, quality))},
                day=day, captured=at, build=day)


def build(run, captured, last_bar, returns):
    return dict(manifest={'run_id': run}, record={'_evidence': {'captured_at': captured,
        'inputs': {'T': {'cur': 'USD', 'timing': tech(last_bar)}}, 'macro': {'pulse': {
            'tracked': {'^GSPC': [[day, 100] for day, *_ in returns]},
            'paper_returns': {'T': returns},
        }}}})


class LabTest(unittest.TestCase):
    DAYS = ['2026-11-16', '2026-11-17', '2026-11-18', '2026-11-19', '2026-11-20']

    def test_sma36_crossing_and_trend_confirmation(self):
        day = self.DAYS[0]
        self.assertEqual(lab.entry_side(tech(day, 97), tech(day, 101)), 'SHORT')
        self.assertEqual(lab.entry_side(tech(day, 106, swap=True), tech(day, 99)), 'LONG')
        self.assertIsNone(lab.entry_side(tech(day, 97), tech(day, 99)))
        self.assertIsNone(lab.entry_side(tech(day, 90), tech(day, 101)))
        self.assertFalse(lab.confirmed('SHORT', 5, None))
        self.assertFalse(lab.confirmed('SHORT', 5, 7))
        self.assertTrue(lab.confirmed('SHORT', 5, 6))
        self.assertTrue(lab.confirmed('LONG', 7, 6))

    def test_first_completed_close_and_forward_deadline(self):
        day = self.DAYS[-1]
        prev = self.DAYS[-2]
        builds = [
            build('partial', '2026-11-20T19:00:00+00:00', prev, [[day, prev, 1, 100]]),
            build('completed', '2026-11-20T22:00:00+00:00', prev, [[day, prev, .9, 90]]),
            build('revision', '2026-11-21T20:00:00+00:00', day, [[day, prev, .8, 80]]),
            build('late', '2026-11-25T17:30:00+00:00', '2026-11-23',
                  [['2026-11-23', day, 1, 90]]),
        ]
        days, _, bars, forward = lab.collect(builds)
        self.assertEqual(days, [day, '2026-11-23'])
        self.assertEqual(bars[day]['T']['build'], 'completed')
        self.assertEqual(forward[day]['T']['close'], 90)
        self.assertNotIn('2026-11-23', forward)

    def test_short_cashflow_next_session_and_sma_exit(self):
        a,b,c,d,e = self.DAYS
        observations = {
            a: snapshot(a, b + 'T08:45', 102),
            b: snapshot(b, c + 'T08:45', 97),
            c: snapshot(c, d + 'T08:45', 96),
            d: snapshot(d, e + 'T08:45', 101),
        }
        bars = {
            c: {'T': dict(previous=b, relative=1, close=97, build='open')},
            d: {'T': dict(previous=c, relative=.8, close=77.6, build='mark')},
            e: {'T': dict(previous=d, relative=1, close=77.6, build='exit')},
        }
        as_of = datetime.fromisoformat(e + 'T17:00').replace(tzinfo=lab.NY)
        result = lab.book_results(self.DAYS, observations, bars, require_fundamentals=True, as_of=as_of)
        self.assertFalse(result['positions'])
        self.assertEqual([(o['action'], o['signal_session'], o['execution_session']) for o in result['orders']],
                         [('OPEN', b, c), ('CLOSE', d, e)])
        self.assertEqual(result['by_side']['SHORT']['entries'], 1)
        self.assertAlmostEqual(result['execution_fees'], .9)
        self.assertAlmostEqual(result['borrow_cost'], (500 + 400) * .02 / 365)
        self.assertAlmostEqual(result['final_equity'], 10_099.1 - result['borrow_cost'])

        observations[b] = snapshot(b, c + 'T08:45', 97, score=7.)
        confirmed = lab.book_results(self.DAYS, observations, bars, require_fundamentals=True, as_of=as_of)
        control = lab.book_results(self.DAYS, observations, bars, require_fundamentals=False, as_of=as_of)
        self.assertEqual(confirmed['orders'], [])
        self.assertEqual(control['by_side']['SHORT']['entries'], 1)

    def test_missing_price_and_one_session_delay(self):
        a,b,c,d,e = self.DAYS
        observations = {a: snapshot(a, b + 'T08:45', 102), b: snapshot(b, c + 'T08:45', 97)}
        bars = {c: {'T': dict(previous=b, relative=1, close=97, build='open')}}
        as_of = datetime.fromisoformat(e + 'T17:00').replace(tzinfo=lab.NY)
        result = lab.book_results([a,b,c,d], observations, bars, require_fundamentals=True, as_of=as_of)
        self.assertIsNone(result['final_equity'])
        self.assertEqual(result['gap_sessions'], 1)
        later = {**bars, e: {'T': dict(previous=d, relative=1, close=90, build='next')}}
        late_mark = {d: {'T': dict(day=d, previous=c, relative=.9,
                                  known_at=as_of, close=90, build='late')}}
        recovered = lab.book_results(self.DAYS, observations, later, require_fundamentals=True,
                                     as_of=as_of, catchup_bars=late_mark)
        self.assertEqual(recovered['gap_sessions'], 1)
        self.assertEqual(recovered['positions']['T']['marked_on'], e)
        self.assertAlmostEqual(recovered['positions']['T']['marked_notional'], 450)
        missed = lab.book_results([a,b,c], observations, {}, require_fundamentals=True, as_of=as_of)
        self.assertEqual(missed['orders'][0]['status'], 'MISSED_PRICE')
        self.assertIsNone(missed['return_pct'])

        observations[b] = snapshot(b, c + 'T12:30', 97)
        bars[d] = {'T': dict(previous=c, relative=1, close=99, build='next')}
        result = lab.book_results(self.DAYS, observations, bars, require_fundamentals=True, as_of=as_of)
        self.assertEqual([(o['execution_session'], o['status']) for o in result['orders']], [(d, 'FILLED')])
        self.assertEqual(result['gap_sessions'], 1)

        observations[b] = snapshot(b, d + 'T12:30', 97)
        result = lab.book_results(self.DAYS, observations, bars, require_fundamentals=True, as_of=as_of)
        self.assertEqual(result['orders'], [])

    def test_long_entry_exit_and_forward_book_starts_empty(self):
        a, b, c, d, e = self.DAYS
        observations = {}
        for day, capture, close in [(a,b,99), (b,c,106), (c,d,108), (d,e,99)]:
            obs = snapshot(day, capture + 'T08:45', close, score=8, quality=7)
            obs['rows']['T'] = ('T', tech(day, close, swap=True), obs['rows']['T'][2])
            observations[day] = obs
        bars = {
            c: {'T': dict(previous=b, relative=1., close=106, build='open')},
            d: {'T': dict(previous=c, relative=1.1, close=116.6, build='mark')},
            e: {'T': dict(previous=d, relative=1., close=116.6, build='exit')},
        }
        as_of = datetime.fromisoformat(e + 'T17:00').replace(tzinfo=lab.NY)
        result = lab.book_results(self.DAYS, observations, bars, require_fundamentals=True, as_of=as_of)
        self.assertEqual(result['by_side']['LONG']['entries'], 1)
        self.assertEqual(result['by_side']['LONG']['exits'], 1)
        self.assertAlmostEqual(result['final_equity'], 10048.95)
        self.assertEqual(result['borrow_cost'], 0)
        forward = lab.book_results(self.DAYS, observations, bars, require_fundamentals=True,
                                   first=e, as_of=as_of)
        self.assertEqual(forward['orders'], [])
        self.assertIsNone(forward['return_pct'])

    def test_unpaired_report_is_not_published(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / lab.REPORT
            path.parent.mkdir()
            path.write_text(json.dumps({'schema': lab.SCHEMA, 'archive_build': 'other'}))
            self.assertEqual(lab.site_pages(folder, {'manifest': {'run_id': 'verified'}}), [])


if __name__ == '__main__':
    unittest.main()
