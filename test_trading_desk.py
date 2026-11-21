"""Technical trend scan and the Claude vs Codex trading comparison (no network)."""
import json
import tempfile
import unittest
from pathlib import Path

import active_trading as at
import trading_desk as td


def timing(close, s36, s50, s200):
    return dict(status='AVAILABLE', close=close, sma36=s36, sma50=s50, sma200=s200, extension_atr=0.5)


RECORD = {
    '_evidence': {'captured_at': '2026-11-21T04:00:00+00:00', 'inputs': {
        'UP': dict(sector='Tech', cur='USD', timing=timing(120, 110, 108, 100)),
        'DOWN': dict(sector='Energy', cur='USD', timing=timing(80, 90, 95, 100)),
        'PULL': dict(sector='Tech', cur='USD', timing=timing(105, 110, 108, 100)),
        'REC': dict(sector='Tech', cur='USD', timing=timing(95, 92, 90, 100)),
        'NODATA': dict(sector='Tech', cur='USD', timing=dict(status='UNAVAILABLE')),
        'BROKEN': dict(sector='Tech', cur='USD', timing=dict(status='AVAILABLE', close=None))}},
    'UP': {'opportunity': {'label': 'Buy', 'score': 7.5}},
}


class Scan(unittest.TestCase):
    def test_groups_breadth_and_missing_data_stay_out(self):
        out = td.scan(RECORD)
        groups = {r['ticker']: r['group'] for r in out['rows']}
        self.assertEqual(groups, {'UP': 'UPTREND', 'DOWN': 'DOWNTREND', 'PULL': 'PULLBACK', 'REC': 'RECOVERING'})
        self.assertEqual(out['measured'], 4)
        self.assertAlmostEqual(out['breadth'], 50.)
        html = td.render_scan(out, market='CORRECTION', captured='2026-11-21')
        self.assertIn('Uptrend', html)
        self.assertIn('CORRECTION', html)
        self.assertLess(html.index('>UP<'), html.index('>DOWN<'))


class Compare(unittest.TestCase):
    def test_accounts_from_the_common_start_with_drawdown_and_exposure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'paper_trades').mkdir()
            (root / 'history').mkdir()
            doc = dict(at.new_account('2026-11-12'), cost_rate=0.)
            at.intake(doc, 'paper-order: SHORT 10 X', issue=1, created_at='2026-11-19T10:00:00Z',
                      universe={'X': dict(yf='X', cur='EUR')})
            at.save(doc, root / 'paper_trades' / 'active-account.json')
            series = {'X': [('2026-11-19', 100.), ('2026-11-20', 100.), ('2026-11-23', 110.), ('2026-11-24', 90.)],
                      '^GSPC': [('2026-11-19', 1.), ('2026-11-20', 100.), ('2026-11-23', 99.), ('2026-11-24', 98.)]}
            claude = td.claude_account(root, series, '2026-11-24')
            self.assertEqual((claude['shorts'], claude['longs'], claude['sessions']), (1, 0, 2))
            self.assertAlmostEqual(claude['ret'], 100 * (10100 / 10000 - 1))
            self.assertAlmostEqual(claude['dd'], 100 * (9900 / 10000 - 1))
            self.assertAlmostEqual(claude['exposure'], 100 * 900 / 10100)
            self.assertAlmostEqual(td.benchmark(series, '2026-11-24'), -2.)
            (root / 'history' / 'long_short_lab.json').write_text(json.dumps(dict(
                parameters=dict(capital_usd=10000., position_usd=500., slots_per_side=3),
                paper=dict(final_equity=10050., return_pct=0.5, drawdown_pct=-0.2, sessions=2,
                           daily_equity=[['2026-11-23', 10000.], ['2026-11-24', 10050.]], pending=[],
                           positions={'AVGO': dict(side='SHORT', marked_notional=480.)}))))
            codex = td.codex_long_short(root)
            self.assertEqual((codex['shorts'], codex['currency']), (1, 'USD'))
            html = td.render_compare([claude, codex], -2., today='2026-11-24')
            self.assertIn('Codex · long/short lab', html)
            self.assertIn('+3.00 pts', html)                    # Claude +1% vs S&P -2%

    def test_missing_ledgers_give_an_empty_but_valid_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(td.claude_account(tmp, {}, '2026-11-24'))
            self.assertIsNone(td.codex_long_short(tmp))
            self.assertIsNone(td.codex_active(tmp))
            self.assertIn('No account has a session', td.render_compare([], 0., today='2026-11-24'))


if __name__ == '__main__':
    unittest.main()
