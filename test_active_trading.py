"""Active paper trading: order intake, replayed fills at the next close, the page."""
import json
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

import active_trading as at

UNIVERSE = {'MU': dict(yf='MU', cur='USD'), 'ELE': dict(yf='ELE.MC', cur='EUR'),
            'GIB': dict(yf='GIB-A.TO', cur='CAD')}


def account(**kw):
    doc = dict(at.new_account('2026-11-12'), cost_rate=0.)     # costs are tested in test_active_rules
    doc.update(kw)
    return doc


def place(doc, title, issue, when):
    return at.intake(doc, title, issue=issue, created_at=when, universe=UNIVERSE)


class Intake(unittest.TestCase):
    def test_parses_orders_and_rejects_anything_else(self):
        self.assertEqual(at.parse('paper-order: buy 10 mu'), ('BUY', 10, 'MU'))
        self.assertEqual(at.parse('paper-order: SELL 3 ELE.MC'), ('SELL', 3, 'ELE.MC'))
        self.assertEqual(at.parse('paper-order: CANCEL #12'), ('CANCEL', 12, None))
        for bad in ('paper-order: BUY 0 MU', 'paper-order: BUY 1.5 MU', 'paper-order: SHORT 5 MU',
                    'paper-order: BUY 5 MU; rm -rf /', 'buy 5 MU'):
            with self.assertRaises(ValueError):
                at.parse(bad)

    def test_only_universe_members_in_supported_currencies(self):
        doc = account()
        self.assertTrue(place(doc, 'paper-order: BUY 2 MU', 1, '2026-11-12T15:00:00Z')[0])
        self.assertTrue(place(doc, 'paper-order: BUY 5 ELE.MC', 2, '2026-11-12T10:00:00Z')[0])
        ok, why = place(doc, 'paper-order: BUY 5 AAPLX', 3, '2026-11-12T10:00:00Z')
        self.assertFalse(ok)
        self.assertIn('not in the InvestorAce universe', why)
        ok, why = place(doc, 'paper-order: BUY 5 GIB', 4, '2026-11-12T10:00:00Z')
        self.assertFalse(ok)
        self.assertIn('CAD', why)
        self.assertFalse(place(doc, 'paper-order: BUY 2 MU', 1, '2026-11-12T15:00:00Z')[0])   # same issue twice
        self.assertEqual([o['ticker'] for o in doc['orders']], ['MU', 'ELE'])
        self.assertNotIn('fill_price', doc['orders'][0])          # intake never fills


class Replay(unittest.TestCase):
    series = {'MU': [('2026-11-12', 100.), ('2026-11-13', 110.), ('2026-11-16', 120.)],
              'ELE.MC': [('2026-11-12', 40.), ('2026-11-13', 41.)],
              '^GSPC': [('2026-11-12', 7000.), ('2026-11-16', 7070.)]}

    def test_fill_at_the_first_close_after_the_cut_off(self):
        doc = account()
        place(doc, 'paper-order: BUY 10 MU', 1, '2026-11-12T19:00:00Z')    # before the US cut-off
        place(doc, 'paper-order: BUY 10 MU', 2, '2026-11-12T20:30:00Z')    # after it: next session
        place(doc, 'paper-order: BUY 10 ELE', 3, '2026-11-12T15:30:00Z')   # after the EU cut-off
        out = {o['id']: o for o in at.replay(doc, self.series, date(2026, 11, 16))['orders']}
        self.assertEqual((out[1]['fill_date'], out[1]['fill_price']), ('2026-11-12', 100.))
        self.assertEqual((out[2]['fill_date'], out[2]['fill_price']), ('2026-11-13', 110.))
        self.assertEqual(out[3]['fill_date'], '2026-11-13')

    def test_no_close_yet_stays_pending_and_never_uses_a_later_price(self):
        doc = account()
        place(doc, 'paper-order: BUY 10 MU', 1, '2026-11-12T20:30:00Z')
        result = at.replay(doc, self.series, date(2026, 11, 12))
        self.assertEqual(result['orders'][0]['status'], 'PENDING')
        self.assertEqual(result['cash'], 10000.)

    def test_account_value_cost_basis_and_realized_gain_in_euros(self):
        doc = account()
        place(doc, 'paper-order: BUY 10 MU', 1, '2026-11-12T19:00:00Z')
        place(doc, 'paper-order: SELL 4 MU', 2, '2026-11-13T10:00:00Z')
        r = at.replay(doc, self.series, date(2026, 11, 16))
        rate = 0.89063
        self.assertAlmostEqual(r['cash'], 10000 - 1000 * rate + 440 * rate)
        (p,) = r['positions']
        self.assertEqual(p['shares'], 6)
        self.assertAlmostEqual(p['cost'], 600 * rate)
        self.assertAlmostEqual(p['value'], 720 * rate)
        self.assertAlmostEqual(r['realized'], 40 * rate)
        self.assertAlmostEqual(r['pnl'], (40 + 120) * rate)
        self.assertAlmostEqual(r['benchmark_pct'], 1.0)

    def test_rejects_buys_beyond_cash_and_sells_beyond_holdings(self):
        doc = account(capital=1000.)
        place(doc, 'paper-order: BUY 20 MU', 1, '2026-11-12T19:00:00Z')    # 2000 USD > 1000 EUR
        place(doc, 'paper-order: SELL 1 ELE', 2, '2026-11-12T10:00:00Z')
        out = {o['id']: o for o in at.replay(doc, self.series, date(2026, 11, 16))['orders']}
        self.assertEqual(out[1]['status'], 'REJECTED')
        self.assertIn('not enough cash', out[1]['reason'])
        self.assertEqual(out[2]['status'], 'REJECTED')

    def test_cancel_counts_only_before_the_cut_off(self):
        doc = account()
        place(doc, 'paper-order: BUY 10 MU', 1, '2026-11-12T12:00:00Z')
        place(doc, 'paper-order: CANCEL 1', 2, '2026-11-12T13:00:00Z')
        place(doc, 'paper-order: BUY 10 MU', 3, '2026-11-12T12:00:00Z')
        place(doc, 'paper-order: CANCEL 3', 4, '2026-11-12T20:00:00Z')     # too late: already filled
        out = {o['id']: o for o in at.replay(doc, self.series, date(2026, 11, 16))['orders']}
        self.assertEqual(out[1]['status'], 'CANCELLED')
        self.assertEqual(out[3]['status'], 'FILLED')


class Page(unittest.TestCase):
    def record(self):
        return {'MU': dict(price=120., opportunity=dict(label='Buy', score=7.9, price=120.,
                                                        price_thresholds=dict(buy=130.))),
                'ELE': dict(price=41., opportunity=dict(label='Hold Positive', score=5.98, price=41.)),
                '_evidence': dict(inputs={'MU': dict(yf='MU', cur='USD'), 'ELE': dict(yf='ELE.MC', cur='EUR')})}

    def test_page_shows_account_form_positions_and_orders(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'paper_trades').mkdir()
            (root / 'history' / 'runs').mkdir(parents=True)
            doc = account()
            place(doc, 'paper-order: BUY 10 MU', 1, '2026-11-12T19:00:00Z')
            at.save(doc, root / 'paper_trades' / 'active-account.json')
            record = dict(self.record())
            record['_evidence'] = dict(record['_evidence'], captured_at='2026-11-16T22:00:00+00:00',
                                       macro=dict(pulse=dict(tracked=Replay.series)))
            pages = at.site_pages(root, dict(record=record), now=datetime(2026, 11, 16, 22, tzinfo=timezone.utc))
        self.assertEqual([str(p) for p, _ in pages], ['trade.html'])
        html = pages[0][1]
        for text in ('Active trading', 'Send order via GitHub', 'id="trade-universe"', 'FILLED',
                     'Usubillaga/InvestorAce', 'no broker is connected'):
            self.assertIn(text, html)
        universe = json.loads(html.split('id="trade-universe">')[1].split('</script>')[0])
        self.assertEqual({r['t'] for r in universe}, {'MU', 'ELE'})
        self.assertEqual(at.site_pages(root, dict(record=record)), [])     # temp dir gone: no account

    def test_tracked_symbols_cover_orders_and_the_benchmark(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'a.json'
            self.assertEqual(at.tracked_symbols(path), [])
            doc = account()
            place(doc, 'paper-order: BUY 10 ELE', 1, '2026-11-12T10:00:00Z')
            at.save(doc, path)
            self.assertEqual(at.tracked_symbols(path), ['ELE.MC', '^GSPC'])

    def test_workflow_only_accepts_the_owner_and_passes_the_title_via_env(self):
        text = (Path(__file__).parent / '.github' / 'workflows' / 'paper-order.yml').read_text()
        self.assertIn("github.event.issue.author_association == 'OWNER'", text)
        self.assertIn('ORDER_TITLE: ${{ github.event.issue.title }}', text)
        self.assertNotIn('run: python active_trading.py intake "${{', text)
        self.assertNotIn('concurrency:', text)   # a group cancels all but one pending order
        self.assertIn('git reset -q --hard "origin/$BRANCH"', text)   # parallel orders re-record on the new main

    def test_committed_account_has_ten_thousand_euros(self):
        doc = at.load()
        self.assertEqual((doc['capital'], doc['account_currency'], doc['opened']), (10000., 'EUR', '2026-11-12'))
        self.assertEqual(doc['cost_rate'], 0.001)


if __name__ == '__main__':
    unittest.main()
