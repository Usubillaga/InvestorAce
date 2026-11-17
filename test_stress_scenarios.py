"""Stress scenarios: fixed price shocks, information only."""
import unittest

import stress_scenarios as ss


def record():
    inputs = {
        'NVDA': dict(yf='NVDA', cur='USD', sector='Semis'),
        'GEN': dict(yf='GEN', cur='USD', sector='Technology'),
        'MO': dict(yf='MO', cur='USD', sector='Consumer Defensive'),
        'LVMH': dict(yf='MC.PA', cur='EUR', sector='Luxury'),
        'WKL': dict(yf='WKL.AS', cur='EUR', sector='Info Svcs'),
        'IBST': dict(yf='IBST.L', cur='GBp', sector='Materials'),
    }
    opp = lambda label, price, buy: dict(opportunity=dict(label=label, score=7.0, price=price,
                                                          price_thresholds=dict(buy=buy)))
    return {'_evidence': dict(inputs=inputs), 'NVDA': opp('Hold Positive', 150., 91.), 'GEN': opp('Buy', 30., 43.),
            'MO': opp('Buy', 78., 100.), 'LVMH': opp('Hold Positive', 600., 520.), 'WKL': opp('Buy', 90., 113.),
            'IBST': opp('Hold Positive', 300., 250.)}


class Shocks(unittest.TestCase):
    def test_ai_backlash_groups(self):
        rec = record()
        _, by = ss._universe(rec)
        self.assertEqual(ss.shock('AI_BACKLASH', 'NVDA', rec['_evidence']['inputs']['NVDA'])[:2], ('Chips', -0.30))
        self.assertEqual(ss.shock('AI_BACKLASH', 'GEN', rec['_evidence']['inputs']['GEN'])[:2],
                         ('Other technology', -0.10))
        self.assertEqual(ss.shock('AI_BACKLASH', 'MO', rec['_evidence']['inputs']['MO'])[1], 0.)
        result = ss.account_impact('AI_BACKLASH', [('NVDA', 1000.), ('MO', 1000.)], by)
        self.assertAlmostEqual(result['change'], -300.)
        self.assertAlmostEqual(result['change_pct'], -15.)

    def test_france_moves_euro_shares_and_the_dollar(self):
        rec = record()
        _, by = ss._universe(rec)
        result = ss.account_impact('FRANCE_2027', [('MC.PA', 1000.), ('WKL.AS', 1000.), ('MO', 950.),
                                                    ('IBST.L', 500.)], by)
        moves = {m['ticker']: m['change'] for m in result['moves']}
        self.assertAlmostEqual(moves['LVMH'], -150.)
        self.assertAlmostEqual(moves['WKL'], -100.)
        self.assertAlmostEqual(moves['MO'], 50.)          # a USD asset is worth 1/0.95 more in euros
        self.assertNotIn('IBST', moves)                   # no assumption for sterling

    def test_stock_rows_compare_the_shocked_price_with_buy_up_to(self):
        rows = {r['ticker']: r for r in ss.stock_rows('AI_BACKLASH', record())}
        self.assertAlmostEqual(rows['NVDA']['shocked'], 105.)
        self.assertIsNone(rows['NVDA']['at_shocked_price'])     # 105 is still above 91
        france = {r['ticker']: r for r in ss.stock_rows('FRANCE_2027', record())}
        self.assertEqual(france['LVMH']['at_shocked_price'], 'Buy')   # 510 <= 520
        self.assertNotIn('IBST', france)

    def test_page_lists_both_scenarios_and_never_writes_labels(self):
        rec = record()
        result = ss.build(rec, [('Test', [('NVDA', 1000.), ('MC.PA', 500.)])])
        html = ss.render(result, captured='2026-11-17T05:00:00+00:00')
        for text in ('AI backlash', 'France 2027', 'never change a score', 'Test', 'LVMH'):
            self.assertIn(text, html)
        self.assertEqual(rec['NVDA']['opportunity']['label'], 'Hold Positive')


if __name__ == '__main__':
    unittest.main()
