import copy
import unittest
from unittest.mock import patch

import portfolio
from framework_view import framework_panel
from test_framework_contract import engine


class PortfolioPlanTests(unittest.TestCase):
    def candidates(self):
        return [(f'T{i:02}', dict(price=100, cur='USD', sector=f'S{i // 4}'), 100-i)
                for i in range(24)]

    def test_ten_positions_two_per_sector_ten_percent(self):
        ranked = self.candidates()
        original = copy.deepcopy(ranked)
        book = portfolio.construct(ranked)
        self.assertEqual(len(book['positions']), 10)
        self.assertEqual(book['target_size'], 10)
        self.assertAlmostEqual(book['cash_weight'], 0)
        for sector in {p['sector'] for p in book['positions']}:
            self.assertLessEqual(sum(p['sector'] == sector for p in book['positions']), 2)
        self.assertTrue(all(p['weight'] == .1 for p in book['positions']))
        self.assertEqual(ranked, original)

    def test_pullback_entry_and_stop_use_entry_not_current_price(self):
        plan = portfolio.trade_plan(dict(price=100, cur='EUR'), 80, as_of='2026-09-15')
        self.assertEqual(plan['entry_limit'], 80)
        self.assertEqual(plan['initial_stop'], 72)
        self.assertEqual(plan['status'], 'WAIT_FOR_PULLBACK')
        self.assertEqual(plan['entry_valid_until'], '2026-09-22')

    def test_lower_market_quote_caps_limit(self):
        plan = portfolio.trade_plan(dict(price=70, cur='GBp'), 80, as_of='2026-09-15')
        self.assertEqual(plan['entry_limit'], 70)
        self.assertEqual(plan['initial_stop'], 63)
        self.assertEqual(plan['currency'], 'GBp')

    def test_missing_valuation_does_not_invent_entry(self):
        plan = portfolio.trade_plan(dict(price=70, cur='USD'), None)
        self.assertIsNone(plan['entry_limit'])
        self.assertIsNone(plan['initial_stop'])
        self.assertEqual(plan['status'], 'UNAVAILABLE')

    def test_fill_anchors_stop_and_review_clock(self):
        plan = portfolio.trade_plan(dict(price=100, cur='USD'), 80, as_of='2026-09-15')
        filled = portfolio.filled_plan(plan, 78, '2026-09-16')
        self.assertAlmostEqual(filled['initial_stop'], 70.2)
        self.assertEqual(filled['next_review'], '2026-10-16')
        self.assertEqual(filled['holding_review_from'], '2026-12-15')
        self.assertEqual(filled['mandatory_reassessment_on'], '2027-03-15')
        self.assertEqual(plan['status'], 'WAIT_FOR_PULLBACK')
        with self.assertRaises(ValueError):
            portfolio.filled_plan(plan, 81, '2026-09-16')
        with self.assertRaises(ValueError):
            portfolio.filled_plan(plan, 78, '2026-09-23')

    def test_engine_uses_its_existing_entry_formula(self):
        d = engine._regime_fixture('Pharma', .30, 7, 8)
        d.update(cur='USD', yf='AAA')
        with patch.object(engine, 'DATA', {'AAA': d}):
            book = engine.portfolio_proposal('REFLATION')
        plan = book['positions'][0]['trade_plan']
        self.assertEqual(plan['entry_ceiling'], engine.entry_price(d))
        self.assertEqual(plan['entry_limit'], min(d['price'], engine.entry_price(d)))

    def test_table_displays_entry_stop_currency_and_horizon(self):
        ranked = self.candidates()
        book = portfolio.construct(ranked, entry_limits={t: 80 for t, _, _ in ranked})
        html = framework_panel({t: d for t, d, _ in ranked}, engine.W, {}, book)
        self.assertIn('10 of 10 slots', html)
        self.assertIn('80.0000 USD', html)
        self.assertIn('72.0000 USD', html)
        self.assertIn('90&ndash;180 days after fill', html)
        self.assertIn('Review every 30 days', html)


if __name__ == '__main__':
    unittest.main()
