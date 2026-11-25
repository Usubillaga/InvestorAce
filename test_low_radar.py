from datetime import datetime, timedelta, timezone
import unittest

from low_radar_data import quote_fields, snapshot


class LowRadarTests(unittest.TestCase):
    now = datetime(2026, 11, 25, 22, tzinfo=timezone.utc)

    def info(self, **changes):
        quote = dict(symbol='VIS.MC', currency='EUR', quoteType='EQUITY', regularMarketPrice=53.3,
                     fiftyTwoWeekLow=52.1, regularMarketTime=self.now.timestamp()-3600,
                     regularMarketPreviousClose=53.4)
        return quote | changes

    def record(self, prices):
        inputs, record = {}, {}
        for symbol, quote in prices.items():
            inputs[symbol] = dict(low_radar_quote=quote_fields(quote | dict(symbol=symbol), symbol, 'EUR'),
                                  dynamic_analysis=dict(financial_currency='EUR'))
            record[symbol] = dict(opportunity=dict(quote_observed_at=self.now.isoformat(),
                                                  metrics=dict(market_cap=2e9, reported_pe=15)))
        record['_evidence'] = dict(inputs=inputs, captured_at=self.now.isoformat())
        return record

    def test_math_and_missing_optional_values(self):
        record = self.record({'VIS.MC': self.info(), 'FLAT': self.info(regularMarketPrice=52.1, regularMarketPreviousClose=None)})
        record['FLAT']['opportunity']['quote_observed_at'] = '2025-01-01'
        flat, vis = snapshot(record)['rows']
        self.assertEqual(flat['distance'], 0)
        self.assertIsNone(flat['change'])
        self.assertIsNone(flat['pe'])
        self.assertAlmostEqual(vis['distance'], 2.303262955854124)
        self.assertAlmostEqual(vis['change'], -0.1872659176029967)
        self.assertEqual(vis['market_cap'], 2e9)

    def test_eligibility_sort_before_rounding_and_ties(self):
        quotes = {f'S{i:02}': self.info(regularMarketPrice=53+i/100000) for i in reversed(range(35))}
        quotes['A'] = quotes['S00']
        for field in [dict(currency='USD'),dict(quoteType='ETF'),dict(fiftyTwoWeekLow=60),
                      dict(fiftyTwoWeekLow=None),dict(fiftyTwoWeekLow=float('nan')),
                      dict(regularMarketTime=(self.now-timedelta(days=6)).timestamp()),
                      dict(regularMarketTime=self.now.timestamp()+100)]:
            quotes['bad'+str(len(quotes))] = self.info(**field)
        self.assertIsNone(quote_fields(self.info(symbol='OTHER'), 'VIS.MC', 'EUR'))
        result = snapshot(self.record(quotes))
        self.assertEqual((result['universe'], result['eligible']), (43, 36))
        self.assertEqual([r['symbol'] for r in result['rows']], ['A']+[f'S{i:02}' for i in range(29)])
