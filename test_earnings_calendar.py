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
        self.assertEqual([r['ticker'] for r in rows], ['ZTS', 'BBW'])
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
