import importlib.util
import math
import os
import sys
import types
import unittest

HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)

# engine imports yfinance unconditionally; unit tests do not touch the network.
yf = types.ModuleType('yfinance')
yf.Ticker = lambda *a, **k: None
sys.modules['yfinance'] = yf

spec = importlib.util.spec_from_file_location('engine_v3', os.path.join(HERE, 'engine.py'))
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)

spec2 = importlib.util.spec_from_file_location('epv_v2', os.path.join(HERE, 'epv.py'))
epvmod = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(epvmod)


class RegimeContract(unittest.TestCase):
    def test_golden_master(self):
        self.assertEqual(engine.regime_spec_sha256(), engine.REGIME_SPEC_EXPECTED_SHA256)
        self.assertEqual(engine.regime_regression_errors(), [])

    def test_components_reconcile(self):
        for _, sec, cv, bs, pay, expected in engine.REGIME_GOLDEN:
            d = engine._regime_fixture(sec, cv, bs, pay)
            comp = engine.regime_fit_components(d)
            self.assertEqual({r: comp[r]['total'] for r in engine.REGIMES}, expected)
            for r in engine.REGIMES:
                raw = (comp[r]['base'] + comp[r]['sector'] + comp[r]['duration'] +
                       comp[r]['balance'] + comp[r]['payout'])
                self.assertAlmostEqual(raw, comp[r]['raw'], places=12)

    def test_weight_does_not_change_fit(self):
        d = engine._regime_fixture('Pharma', 0.7466666666666667, 7.0, 8.0)
        a = engine.regime_scores(d)
        d['weight'] = 99.9
        self.assertEqual(a, engine.regime_scores(d))

    def test_specific_regressions(self):
        fixtures = {x[0]: x for x in engine.REGIME_GOLDEN}
        for name, regime, expected in [
            ('NVDA', 'GOLDILOCKS', 88.9),
            ('ROAD', 'STAGFLATION', 6.4),
            ('SAN', 'RECESSION', 86.6),
        ]:
            _, sec, cv, bs, pay, _ = fixtures[name]
            got = engine.regime_scores(engine._regime_fixture(sec, cv, bs, pay))[regime]
            self.assertEqual(got, expected)


class EPVContract(unittest.TestCase):
    def apple(self):
        return epvmod.compute(
            revenue=[391035, 383285, 394328, 365817, 274515],
            gross_profit=[180683, 169148, 170782, 152836, 104956],
            rd=[31370, 29915, 26251, 21914, 18752],
            sga=[26097, 24932, 25094, 21973, 19916],
            capex=[9447, 10959, 10708, 11085, 7309],
            dep_amort=[11445, 11519, 11104, 11284, 11056],
            tax_rate=0.2409, net_debt=89100, shares=15408.1, wacc=0.0867)

    def test_apple_fixture(self):
        r = self.apple()
        self.assertIsNotNone(r)
        self.assertAlmostEqual(r['epv_per_share'], 62.86, places=2)

    def test_uploaded_template_fixture(self):
        # Historical Apple values read from the uploaded ValueInvesting.io EPV sheet.
        revenue = [365817, 274515, 260174, 265595, 229234]
        margins = [0.4177935962516778, 0.38233247727810865, 0.3781776810903472,
                   0.38343718820007905, 0.38469860491899105]
        gross_profit = [r*m for r, m in zip(revenue, margins)]
        rd = [21914, 18752, 16217, 14236, 11581]
        sga = [21973, 19916, 18245, 16705, 15261]
        capex = [11085, 7309, 10495, 13313, 12451]
        da = [11284, 11056, 12547, 10903, 10157]
        common = dict(revenue=revenue, gross_profit=gross_profit, rd=rd, sga=sga,
                      capex=capex, dep_amort=da, tax_rate=0.15943837,
                      net_debt=91883, shares=16185.2)
        low = epvmod.compute(wacc=0.08638773131987162, **common)
        high = epvmod.compute(wacc=0.06383396603296074, **common)
        self.assertAlmostEqual(low['epv_per_share'], 41.93522583072486, places=8)
        self.assertAlmostEqual(high['epv_per_share'], 58.75753067606372, places=8)

    def test_net_debt_is_equity_bridge(self):
        r = self.apple()
        self.assertAlmostEqual(r['enterprise_value'] - r['net_debt'], r['equity_value'], places=8)
        self.assertAlmostEqual(r['equity_value'] / r['shares'], r['epv_per_share'], places=8)

    def test_capex_da_required(self):
        r = epvmod.compute(
            revenue=[100,100,100], gross_profit=[50,50,50], rd=[1,1,1], sga=[10,10,10],
            capex=[], dep_amort=[], tax_rate=.2, net_debt=0, shares=10, wacc=.08)
        self.assertIsNone(r)

    def test_gap_is_diagnostic_only(self):
        d = dict(fcf=8, shares=1, r=.08, price=100, epv_value=50)
        before = engine.score(d)
        self.assertAlmostEqual(engine.valuation_gap(d), -0.5)
        self.assertEqual(engine.valuation_read(d), 'WIDE GAP')
        self.assertEqual(before, engine.score(d))


class RegimeBookContract(unittest.TestCase):
    def test_book_ignores_score_and_weight(self):
        original = engine.DATA
        try:
            def row(t, fit_cover, score_fixed, weight):
                # Same sector / factors, fit ordered only by cover in INFLATION.
                d = engine._regime_fixture('Technology', fit_cover, 6, 6)
                d.update(yf=t, score_fixed=score_fixed, weight=weight, held=bool(weight))
                d['sub'] = None  # score comes only from score_fixed
                return d
            engine.DATA = {
                'AAA': row('AAA', .80, 1.0, 99.0),
                'BBB': row('BBB', .90, 9.9, 0.1),
                'CCC': row('CCC', .70, 8.0, 50.0),
            }
            book = engine.regime_book('INFLATION', 3)
            fits = [x[2] for x in book]
            self.assertEqual(fits, sorted(fits, reverse=True))
            # Perturb score/weight; ranking must remain identical.
            names1 = [x[0] for x in book]
            engine.DATA['AAA']['score_fixed'] = 10
            engine.DATA['AAA']['weight'] = .01
            engine.DATA['BBB']['score_fixed'] = 0
            engine.DATA['BBB']['weight'] = 99
            names2 = [x[0] for x in engine.regime_book('INFLATION', 3)]
            self.assertEqual(names1, names2)
        finally:
            engine.DATA = original


if __name__ == '__main__':
    unittest.main(verbosity=2)
