"""War scenarios: producer war case from the TTM, stagflation stress, page."""
import copy
import importlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import market_pulse
import war_scenario as war
import weekly_research
from test_live_analysis import ASOF, ticker_fixture


def fake_assess(row, *, regime, as_of=None, weights=None):
    fcf = ((row.get('dynamic_analysis') or {}).get('inputs') or {}).get('valuation_fcf') or 0
    score = 6.0 + fcf / 1e9 + (0.5 if regime == 'STAGFLATION' else 0)
    return dict(score=score, label='Buy' if score >= 7 else 'Hold Positive', price=50.,
                price_thresholds=dict(buy=fcf / 1e7, strong_buy=None))


class WarCase(unittest.TestCase):
    def row(self, midcycle=True):
        cycle = dict(inputs=dict(valuation_fcf=1e9, valuation_net_income=.8e9), financial_period='2026-06-30')
        spot = dict(inputs=dict(valuation_fcf=3e9, valuation_net_income=2.5e9), financial_period='2026-06-30',
                    overlay=dict(fcf=3000.))
        row = dict(midcycle=True, fcf=1000., dynamic_analysis=cycle, spot_analysis=spot)
        if not midcycle:
            row.pop('midcycle')
        return row

    def test_producer_war_case_values_the_reported_twelve_months(self):
        out = war.case(self.row(), fake_assess, regime='INFLATION')
        self.assertEqual(out['spot']['valuation_fcf'], 3e9)
        self.assertEqual(out['spot']['cycle_fcf'], 1e9)
        self.assertEqual(out['spot']['label'], 'Buy')
        self.assertEqual(out['spot']['buy'], 300.)
        self.assertEqual(out['stagflation']['score'], 6 + 1 + .5)   # label row, cycle cash flow

    def test_the_label_row_is_never_changed_and_non_producers_get_only_the_stress(self):
        row = self.row()
        before = copy.deepcopy(row)
        war.case(row, fake_assess, regime='INFLATION')
        self.assertEqual(row, before)
        self.assertNotIn('spot', war.case(self.row(midcycle=False), fake_assess, regime='INFLATION'))

    def test_page_shows_both_cases_and_skips_unvalued_producers(self):
        record = {'OXY': dict(price=56.38, opportunity=dict(label='Hold Positive', score=6.67, price=56.38,
                              current_regime='INFLATION', price_thresholds=dict(buy=46.27)),
                              war=dict(spot=dict(label='Buy', score=7.29, buy=73.55, valuation_fcf=4.4e9,
                                                 cycle_fcf=3.3e9, financial_period='2026-06-30'),
                                       stagflation=dict(label='Buy', score=7.01, buy=56.69))),
                  'CTVA': dict(price=11.9, opportunity=dict(label=None, score=None),
                               war=dict(spot=dict(label=None), stagflation=dict(label=None))),
                  '_evidence': dict(captured_at='2026-11-09T23:30:00+00:00', inputs={'OXY': dict(cur='USD')},
                                    macro=dict(pulse=dict(oil=dict(last=101.2, date='2026-11-09',
                                                                   avg_63=97.5, avg_252=84.1))))}
        pages = war.site_pages('.', dict(record=record))
        self.assertEqual([str(p) for p, _ in pages], ['war-scenarios.html'])
        html = pages[0][1]
        self.assertIn('73.55', html)
        self.assertIn('46.27', html)
        self.assertIn('12-month average 84.10', html)
        self.assertIn('No valuation in this build', html)
        self.assertIn('CTVA', html)
        self.assertEqual(war.site_pages('.', dict(record={'OXY': dict(price=1.)})), [])


class BuildIntegration(unittest.TestCase):
    def test_build_stores_a_ttm_case_for_producers_only(self):
        e = importlib.import_module('engine')
        m = importlib.import_module('live_analysis')
        facts = m.extract(ticker_fixture(fcf=300e6), 'DVN', as_of=ASOF)
        facts['annual_fcf_series'] = [dict(period=f'{y}-12-31', value=v)
                                      for y, v in [(2025, 100e6), (2024, 100e6), (2023, 100e6)]]
        rows = {}
        for key, midcycle in (('DVN', True), ('ZTS', False)):
            row = copy.deepcopy(e.DATA[key])
            row.update(price=100., quote_observed_at='2026-10-24T20:00:00Z', midcycle=midcycle)
            rows[key] = row
        with tempfile.TemporaryDirectory() as tmp, patch.object(e, 'DATA', rows), \
                patch.object(e.WACC, 'resolve_risk_free', return_value=5.):
            path = Path(tmp) / 'facts.json'
            path.write_text(json.dumps(dict(schema=m.VERSION, entries={
                'DVN': dict(facts, symbol='DVN'), 'ZTS': dict(facts, symbol='ZTS')})))
            def offline(symbol):
                raise RuntimeError('offline')
            e.refresh_dynamic_analysis(cache_path=path, as_of=ASOF, ticker_factory=offline)
        producer = rows['DVN']
        self.assertEqual(producer['dynamic_analysis']['inputs']['valuation_fcf'], 100e6)
        self.assertEqual(producer['spot_analysis']['inputs']['valuation_fcf'],
                         producer['spot_analysis']['inputs']['fcf'])
        self.assertNotEqual(producer['spot_analysis']['inputs']['valuation_fcf'], 100e6)
        self.assertNotIn('spot_analysis', rows['ZTS'])
        out = war.case(producer, e.opportunity, regime='INFLATION', as_of=ASOF)
        self.assertEqual(out['spot']['valuation_fcf'], producer['spot_analysis']['inputs']['valuation_fcf'])
        self.assertTrue(producer['midcycle'])          # the label row keeps the cycle basis


class Navigation(unittest.TestCase):
    def test_oil_context_from_wti_closes(self):
        closes = {'CL=F': [(f'd{i:03d}', 80. + i / 10) for i in range(260)]}
        oil = market_pulse.summarize(closes, {})['oil']
        self.assertEqual(oil['last'], 105.9)
        self.assertAlmostEqual(oil['avg_63'], sum(80 + i / 10 for i in range(197, 260)) / 63, places=2)
        self.assertIsNone(market_pulse.summarize({}, {})['oil'])

    def test_links_and_labels(self):
        html = '<html><body><p>x</p></body></html>'
        linked = weekly_research.add_research_link(html, include_paper=True, include_war=True)
        self.assertIn('href="paper-test.html"', linked)
        self.assertIn('href="war-scenarios.html"', linked)
        self.assertNotIn('paper-test.html', weekly_research.add_research_link(html))
        import i18n
        for language, paper, scen in [('de', 'Papiertest ↗', 'Kriegsszenarien ↗'),
                                      ('es', 'Prueba en papel ↗', 'Escenarios de guerra ↗')]:
            out = i18n.localize(linked, language)
            self.assertIn(paper, out)
            self.assertIn(scen, out)


if __name__ == '__main__':
    unittest.main()
