"""Earnings calendar: dated Yahoo events, soonest first, estimates flagged."""
import unittest
from datetime import date

import earnings_view
import live_analysis


def row(day, estimated=False):
    return dict(dynamic_analysis=dict(events=dict(earnings=dict(date=day, estimated=estimated, date_end=None))))


class EarningsCalendarTests(unittest.TestCase):
    def test_yahoo_timestamps_become_dated_events(self):
        event = live_analysis.earnings_event(dict(earningsTimestampStart=1764720000, isEarningsDateEstimate=True))
        self.assertEqual(event['date'], '2025-12-03')
        self.assertTrue(event['estimated'])
        self.assertIsNone(live_analysis.earnings_event({}))

    def test_calendar_is_sorted_windowed_and_names_missing_dates(self):
        data = {'BBW': row('2026-12-03', True), 'ZTS': row('2026-11-04'), 'OLD': row('2026-09-01'),
                'FAR': row('2027-06-01'), 'NONE': {}}
        rows, missing = earnings_view.events(data, {'ZTS': dict(label='Buy')}, today=date(2026, 10, 31))
        self.assertEqual([r['ticker'] for r in rows], ['ZTS', 'BBW'])  # 2026-09-01 is older than 21 days
        self.assertEqual(rows[0]['label'], 'Buy')
        self.assertEqual(missing, ['NONE'])
        html = earnings_view.panel(data, {}, today=date(2026, 10, 31))
        self.assertIn('estimated', html)
        self.assertIn('+4', html)

    def test_calendar_has_no_translation_gaps(self):
        import i18n
        html = earnings_view.panel({'ZTS': row('2026-11-04'), 'BBW': row('2026-12-03', True), 'X': {}},
                                   {'ZTS': dict(label='Buy')}, today=date(2026, 10, 31))
        self.assertEqual(i18n.translation_gaps(html), [])


if __name__ == '__main__':
    unittest.main()


def packet(next_day=None, last=None, period='2026-09-30', estimated=False):
    events = dict(earnings=dict(date=next_day, estimated=estimated) if next_day else None, last_reported=last)
    return dict(dynamic_analysis=dict(financial_period=period, events=events))


class EarningsAlertTests(unittest.TestCase):
    today = date(2026, 11, 1)

    def test_reports_within_7_days_are_red_on_top_and_on_the_row(self):
        data = {'ZTS': packet('2026-11-05'), 'INTU': packet('2026-11-19')}
        html = earnings_view.alert(data, {'ZTS': dict(label='Buy')}, today=self.today)
        self.assertIn('Reporting in the next 7 days: ZTS 2026-11-05 (Buy)', html)
        self.assertNotIn('INTU', html)
        css = earnings_view.row_css(data, today=self.today)
        self.assertIn('tr[data-assessment="ZTS"]', css)
        self.assertNotIn('INTU', css)

    def test_after_a_report_the_alert_says_whether_the_data_caught_up(self):
        data = {'BSX': packet(None, last='2026-10-22', period='2026-03-31'),
                'AAPL': packet('2027-01-29', last='2026-10-30', period='2026-09-27')}
        html = earnings_view.alert(data, {}, today=self.today)
        self.assertIn('Reported, waiting for the new quarter in the data: BSX 2026-10-22', html)
        self.assertIn('Reported and updated with the new quarter: AAPL 2026-10-30', html)
        rows, _ = earnings_view.events(data, {}, today=self.today)
        self.assertEqual({r['ticker']: r['updated'] for r in rows if r['days'] <= 0}, {'BSX': False, 'AAPL': True})

    def test_nothing_to_report_renders_no_alert(self):
        self.assertEqual(earnings_view.alert({'X': packet('2027-02-01')}, {}, today=self.today), '')

    def test_last_report_is_remembered_after_yahoo_moves_to_the_next_date(self):
        previous = dict(earnings=dict(date='2026-10-22'))
        fresh = dict(earnings=dict(date='2027-01-28'))
        self.assertEqual(live_analysis.last_earnings(fresh, previous, self.today), '2026-10-22')
        self.assertEqual(live_analysis.last_earnings(fresh, dict(last_earnings='2026-10-22'), self.today), '2026-10-22')
        self.assertIsNone(live_analysis.last_earnings(fresh, None, self.today))

    def test_alert_has_no_translation_gaps(self):
        import i18n
        data = {'ZTS': packet('2026-11-05', estimated=True), 'BSX': packet(None, last='2026-10-22', period='2026-03-31'),
                'AAPL': packet(None, last='2026-10-30', period='2026-09-27')}
        html = earnings_view.alert(data, {'ZTS': dict(label='Buy')}, today=self.today) + earnings_view.panel(data, {}, today=self.today)
        self.assertEqual(i18n.translation_gaps(html), [])
        self.assertIn('Resultados en los próximos 7 días: ZTS ~2026-11-05 (Buy)', i18n.localize(html, 'es'))
