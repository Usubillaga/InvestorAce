"""Claude's trading rules v1: entries, sizing, exits, market filter."""
import unittest
from datetime import date

import active_rules as ar
import active_trading as at

TODAY = date(2026, 12, 1)


def stock(label='Buy', score=7.5, price=100., trend='ABOVE_SMA200', ext=1.0, next_report=None, last_report=None,
          sector=None):
    events = {'earnings': {'date': next_report}, 'last_reported': last_report}
    return (dict(opportunity=dict(label=label, score=score, price=price)),
            dict(yf=None, cur='USD', sector=sector, timing=dict(status='AVAILABLE', trend=trend, extension_atr=ext),
                 dynamic_analysis=dict(events=events)))


def record(sp_vs_200=3.0, captured='2026-11-30', **stocks):
    rec, inputs = {}, {}
    for ticker, (row, inp) in stocks.items():
        rec[ticker] = row
        inputs[ticker] = dict(inp, yf=ticker)
    rec['_evidence'] = dict(captured_at=captured + 'T23:30:00+00:00', inputs=inputs, macro=dict(pulse=dict(components=dict(sp500_ma200=dict(value=sp_vs_200)))))
    return rec


def account(*orders):
    doc = at.new_account('2026-11-12')
    for i, (title, when) in enumerate(orders, 1):
        at.intake(doc, title, issue=i, created_at=when, universe={t: dict(yf=t, cur='USD') for t in 'ABCDEFGHIJ'})
    return doc


def days(start, closes):
    """Consecutive weekday sessions from `start` (a Monday)."""
    out, d = [], date.fromisoformat(start)
    for c in closes:
        while d.weekday() >= 5:
            d = date.fromordinal(d.toordinal() + 1)
        out.append((d.isoformat(), float(c)))
        d = date.fromordinal(d.toordinal() + 1)
    return out


class Entries(unittest.TestCase):
    def test_only_buy_labels_in_an_uptrend_not_extended_and_away_from_reports(self):
        rec = record(A=stock(score=8.0), B=stock(label='Hold Positive'), C=stock(trend='BELOW_SMA200'),
                     D=stock(ext=4.5), E=stock(next_report='2026-12-03'), F=stock(ext=-0.5))
        p = ar.plan(account(), rec, {}, TODAY)
        self.assertEqual([o['ticker'] for o in p['orders']], ['A'])

    def test_post_earnings_drift_ranks_first_then_score(self):
        rec = record(A=stock(score=8.5), B=stock(score=7.1, last_report='2026-11-26'), C=stock(score=7.9),
                     D=stock(score=9.0, last_report='2026-11-26'), E=stock(score=9.5, last_report='2026-11-26'))
        series = {'B': [('2026-11-25', 100.), ('2026-11-27', 104.)],      # rose on the report
                  'D': [('2026-11-25', 100.), ('2026-11-27', 95.)]}       # fell on it; E: reaction unknown
        p = ar.plan(account(), rec, series, TODAY)
        self.assertEqual([o['ticker'] for o in p['orders']], ['B', 'E', 'A', 'C'])
        self.assertIn('rose on its report', p['orders'][0]['reason'])
        self.assertNotIn('rose on its report', p['orders'][1]['reason'])
        self.assertTrue(any(n.startswith('D: skipped, fell') for n in p['notes']))

    def test_at_most_two_positions_per_sector(self):
        rec = record(A=stock(score=8.5, sector='Tech'), B=stock(score=8.4, sector='Tech'),
                     C=stock(score=8.3, sector='Tech'), D=stock(score=7.1, sector='Energy'))
        p = ar.plan(account(), rec, {}, TODAY)
        self.assertEqual([o['ticker'] for o in p['orders']], ['A', 'B', 'D'])

    def test_no_orders_from_a_stale_build(self):
        p = ar.plan(account(), record(captured='2026-11-25', A=stock()), {}, TODAY)
        self.assertEqual(p['orders'], [])
        self.assertIn('days old', p['notes'][0])
        self.assertEqual(len(ar.plan(account(), record(captured='2026-11-27', A=stock()), {}, TODAY)['orders']), 1)

    def test_risk_based_size_one_percent_of_equity_at_an_eight_percent_stop(self):
        p = ar.plan(account(), record(A=stock(price=100.)), {}, TODAY)
        unit = 100 * 0.89063
        self.assertEqual(p['orders'][0]['shares'], int(10000 * 0.01 / (0.08 * unit)))

    def test_every_fill_pays_the_trading_cost(self):
        doc = account(('paper-order: BUY 10 A', '2026-11-16T12:00:00Z'), ('paper-order: SELL 10 A', '2026-11-17T12:00:00Z'))
        r = at.replay(doc, {'A': [('2026-11-16', 100.), ('2026-11-17', 100.)]}, '2026-11-17')
        self.assertAlmostEqual(r['fees'], 2 * 1000 * 0.89063 * 0.001)
        self.assertAlmostEqual(r['cash'], 10000 - r['fees'])
        self.assertAlmostEqual(r['realized'], -r['fees'])

    def test_no_buys_in_a_correction(self):
        p = ar.plan(account(), record(sp_vs_200=-1.0, A=stock()), {}, TODAY)
        self.assertEqual(p['orders'], [])
        self.assertEqual(p['market'], 'CORRECTION')

    def test_at_most_eight_positions(self):
        rec = record(**{t: stock(score=7 + i / 10) for i, t in enumerate('ABCDEFGHIJ')})
        self.assertEqual(len(ar.plan(account(), rec, {}, TODAY)['orders']), ar.MAX_POSITIONS)


class Exits(unittest.TestCase):
    def held(self, closes, **kw):
        doc = account(('paper-order: BUY 10 A', '2026-11-16T12:00:00Z'))
        series = {'A': days('2026-11-16', closes), '^GSPC': days('2026-11-16', [1] * len(closes))}
        today = date.fromisoformat(series['A'][-1][0])
        return ar.plan(doc, record(captured=today.isoformat(), A=stock(**kw)), series, today)

    def only(self, plan):
        sells = [o for o in plan['orders'] if o['side'] == 'SELL']
        return sells[0]['rule'] if sells else None

    def test_stop_loss_at_eight_percent(self):
        self.assertEqual(self.only(self.held([100, 97, 93])), None)
        self.assertEqual(self.only(self.held([100, 97, 92])), 'STOP')

    def test_breakeven_after_ten_percent_and_trailing_after_twenty(self):
        self.assertEqual(self.only(self.held([100, 111, 100])), 'STOP')        # back to entry
        self.assertEqual(self.only(self.held([100] * 16 + [112, 124, 131, 118])), None)   # above 131 x 0.9
        self.assertEqual(self.only(self.held([100] * 16 + [112, 124, 131, 117])), 'STOP')

    def test_take_half_profit_once_at_twenty_five_percent(self):
        plan = self.held([100] * 17 + [104, 110, 118, 126])
        sell = [o for o in plan['orders'] if o['side'] == 'SELL'][0]
        self.assertEqual((sell['rule'], sell['shares']), ('TAKE_PROFIT', 5))

    def test_eight_week_hold_overrides_trailing_and_profit_taking(self):
        plan = self.held([100, 110, 121, 126, 140, 128])
        self.assertEqual(self.only(plan), None)
        self.assertEqual(self.only(self.held([100, 110, 121, 126, 140, 128], label='Sell')), None)   # label waits too
        self.assertEqual(self.only(self.held([100, 110, 121, 126, 140, 100])), 'STOP')               # the stop does not
        self.assertTrue(any('8-week hold' in n for n in plan['notes']))

    def test_sell_before_a_report_without_a_cushion(self):
        self.assertEqual(self.only(self.held([100, 103], next_report='2026-11-19')), 'EARNINGS')
        self.assertEqual(self.only(self.held([100, 111], next_report='2026-11-19')), None)

    def test_label_trend_and_time_stops(self):
        self.assertEqual(self.only(self.held([100, 101], label='Hold Negative')), 'LABEL')
        self.assertEqual(self.only(self.held([100, 101], trend='BELOW_SMA200')), 'TREND')
        self.assertEqual(self.only(self.held([100] * 16)), 'TIME_STOP')
        self.assertEqual(self.only(self.held([100] * 10)), None)

    def test_correction_tightens_the_stop_to_five_percent(self):
        doc = account(('paper-order: BUY 10 A', '2026-11-16T12:00:00Z'))
        series = {'A': days('2026-11-16', [100, 95])}
        plan = ar.plan(doc, record(sp_vs_200=-2, captured='2026-11-17', A=stock()), series, date(2026, 11, 17))
        self.assertEqual(self.only(plan), 'STOP')

    def test_titles_match_the_order_workflow(self):
        self.assertEqual(at.parse(ar.title(dict(side='BUY', shares=3, ticker='MU'))), ('BUY', 3, 'MU'))


if __name__ == '__main__':
    unittest.main()
