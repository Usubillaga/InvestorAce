"""Daily trading round run by GitHub Actions (active-round.yml)."""
import unittest
from datetime import date
from pathlib import Path

import active_round as ar


class Calendar(unittest.TestCase):
    def test_weekends_holidays_and_uncovered_years_are_skipped(self):
        self.assertEqual(ar.skip_reason(date(2026, 11, 21)), 'weekend')
        self.assertEqual(ar.skip_reason(date(2026, 11, 26)), 'NYSE holiday')          # Thanksgiving
        self.assertEqual(ar.skip_reason(date(2026, 12, 25)), 'NYSE holiday')
        self.assertIsNone(ar.skip_reason(date(2026, 11, 23)))
        self.assertIsNone(ar.skip_reason(date(2026, 11, 27)))                         # half day, open
        self.assertIn('calendar', ar.skip_reason(date(2028, 1, 4)))
        self.assertTrue(all(date.fromisoformat(d).weekday() < 5 for d in ar.NYSE_HOLIDAYS))


class Workflow(unittest.TestCase):
    def test_orders_go_through_intake_once_per_day_and_never_through_paper_order(self):
        text = (Path(__file__).parent / '.github/workflows/active-round.yml').read_text(encoding='utf-8')
        self.assertIn("cron: '43 12 * * 1-5'", text)
        self.assertIn('python active_round.py plan', text)
        self.assertIn('python active_trading.py intake', text)
        self.assertIn('created:>=$today', text)                                       # duplicate guard
        self.assertNotIn('secrets.', text)                                            # GITHUB_TOKEN only
        paper = (Path(__file__).parent / '.github/workflows/paper-order.yml').read_text(encoding='utf-8')
        self.assertIn("author_association == 'OWNER'", paper)                         # bot issues not re-recorded


if __name__ == '__main__':
    unittest.main()
