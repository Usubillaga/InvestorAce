"""Offline full-report checks for presentation-only translations."""
import copy
import io
import re
import unittest
from contextlib import redirect_stderr
from html.parser import HTMLParser
from unittest.mock import patch

import i18n
import timing
from test_framework_contract import engine
from test_decision_view import row
from test_timing import AS_OF, history


class FinancialCells(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_cell = False
        self.values = []
        self.tickers = []
        self.ticker_cell = False

    def handle_starttag(self, tag, attrs):
        if tag == 'td':
            self.in_cell = True
            self.ticker_cell = 'tk' in dict(attrs).get('class', '').split()

    def handle_endtag(self, tag):
        if tag == 'td':
            self.in_cell = False
            self.ticker_cell = False

    def handle_data(self, data):
        text = data.strip()
        if self.in_cell and re.fullmatch(r'[+−$€£(-]?\d[\d.,%+−/() $€£-]*', text):
            self.values.append(text)
        if self.ticker_cell and text in {'BUY', 'SELL', 'HOLD'}:
            self.tickers.append(text)


class FullReportLanguages(unittest.TestCase):
    def report(self):
        rows = {}
        for ticker, close in [('BUY', 120.0), ('SELL', 80.0), ('HOLD', 100.0)]:
            bars = history()
            bars.iloc[-1] = [close + 1, close - 1, close]
            rows[ticker] = row(timing=timing.calculate(bars, AS_OF))
        before = copy.deepcopy(rows)
        with patch.object(engine, 'DATA', rows), \
             patch.object(engine, 'sector_performance', return_value={'ok': False}), \
             patch.object(engine, 'forward_run', return_value={}), \
             patch.object(engine, 'regime_history', return_value=([], {})), redirect_stderr(io.StringIO()):
            financials = {t: (engine.score(d), engine.verdict(t, d), engine.regime_scores(d),
                              engine.entry_price(d), engine.ngv(d), engine.risk(d))
                          for t, d in rows.items()}
            html = engine.build_html(macro={'ok': False}, write=False)
            variants = {language: i18n.localize(html, language) for language in ('en', 'de', 'es')}
            self.assertEqual(financials,
                             {t: (engine.score(d), engine.verdict(t, d), engine.regime_scores(d),
                                   engine.entry_price(d), engine.ngv(d), engine.risk(d))
                              for t, d in rows.items()})
        self.assertEqual(rows, before)
        return html, variants

    def test_translated_full_reports_preserve_financial_cells_and_tickers(self):
        html, variants = self.report()
        source = FinancialCells()
        source.feed(html)
        self.assertTrue(source.values)
        self.assertEqual(set(source.tickers), {'BUY', 'SELL', 'HOLD'})
        for language, page in variants.items():
            parsed = FinancialCells()
            parsed.feed(page)
            with self.subTest(language=language):
                self.assertEqual(parsed.values, source.values)
                self.assertEqual(parsed.tickers, source.tickers)
                self.assertIn(f'<html lang="{language}">', page)
                self.assertEqual(page.count('id="investorace-language-nav"'), 1)
                self.assertIn('id="decision-observations"', page)
                self.assertTrue(page.endswith('</body></html>'))
                self.assertNotIn('NaN', page)
                self.assertNotIn('Infinity', page)

    def test_engine_renders_the_language_control_before_publication(self):
        html, _ = self.report()
        self.assertEqual(html.count('id="investorace-language-nav"'), 1)
        for language in ('en', 'de', 'es'):
            self.assertIn(f'href="{i18n.homepage(language)}"', html)


if __name__ == '__main__':
    unittest.main()
