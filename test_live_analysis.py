"""Current Yahoo facts must drive formulas without destroying dated research."""
import copy
import importlib
import json
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from pathlib import Path
import tempfile
from unittest.mock import patch

import pandas as pd


ASOF = datetime(2026, 10, 25, 12, tzinfo=timezone.utc)


def ticker_fixture(fcf=100e6, shares=10e6, price=100., debt=50e6):
    years = pd.to_datetime(['2025-12-31', '2024-12-31', '2023-12-31'])
    annual_cf = pd.DataFrame([[fcf+20e6]*3, [-20e6]*3, [fcf]*3, [-10e6]*3],
        index=['Operating Cash Flow', 'Capital Expenditure', 'Free Cash Flow', 'Cash Dividends Paid'], columns=years)
    annual_is = pd.DataFrame([[1000e6]*3, [200e6]*3, [150e6]*3, [250e6]*3],
        index=['Total Revenue', 'Operating Income', 'Net Income', 'EBITDA'], columns=years)
    annual_bs = pd.DataFrame([[debt]*3, [10e6]*3, [shares]*3],
        index=['Total Debt', 'Cash And Cash Equivalents', 'Ordinary Shares Number'], columns=years)
    info = dict(currency='USD', financialCurrency='USD', beta=1., sharesOutstanding=shares,
        regularMarketPrice=price, regularMarketTime=int(datetime(2026,10,23,20,tzinfo=timezone.utc).timestamp()),
        quoteType='EQUITY', sector='Healthcare', longName='Fixture')
    return SimpleNamespace(get_info=lambda: copy.deepcopy(info), info=info,
        cashflow=annual_cf, income_stmt=annual_is, balance_sheet=annual_bs,
        quarterly_cashflow=pd.DataFrame(), quarterly_income_stmt=pd.DataFrame(),
        quarterly_balance_sheet=pd.DataFrame())


class LiveAnalysisTests(unittest.TestCase):
    def test_earnings_multiple_and_cash_conversion_use_the_same_packet(self):
        result=self.analyze()
        self.assertAlmostEqual(result['metrics']['reported_pe'],1000e6/150e6)
        self.assertAlmostEqual(result['metrics']['valuation_pe'],1000e6/150e6)
        self.assertAlmostEqual(result['metrics']['cash_conversion_pct'],100e6/150e6*100)

    def test_commodity_pe_uses_several_years_not_the_latest_peak(self):
        m=self.module();facts=m.extract(ticker_fixture(), 'AR', as_of=ASOF)
        facts.update(midcycle=True, annual_fcf_series=[dict(period=f'{y}-12-31',value=100e6)
            for y in (2025,2024,2023)],annual_net_income_series=[dict(period=f'{y}-12-31',value=v)
            for y,v in [(2025,300e6),(2024,100e6),(2023,200e6)]])
        result=m.calculate(facts,risk_free=.05,mrp=.05,as_of=ASOF)
        self.assertAlmostEqual(result['metrics']['valuation_pe'],5.)
        self.assertAlmostEqual(result['metrics']['reported_pe'],1000e6/150e6)

    def test_absent_midcycle_earnings_do_not_reuse_reported_pe(self):
        m=self.module();facts=m.extract(ticker_fixture(), 'AR', as_of=ASOF)
        facts.update(midcycle=True,annual_net_income_series=[])
        result=m.calculate(facts,risk_free=.05,mrp=.05,as_of=ASOF)
        self.assertIsNone(result['metrics']['valuation_pe'])

    def test_commodity_earnings_and_cash_averages_must_cover_the_same_years(self):
        m=self.module();facts=m.extract(ticker_fixture(), 'AR', as_of=ASOF)
        facts.update(midcycle=True,annual_fcf_series=[dict(period=f'{y}-12-31',value=100e6)
            for y in (2025,2024,2023,2022,2021)],annual_net_income_series=[dict(period=f'{y}-12-31',value=200e6)
            for y in (2023,2022,2021)])
        result=m.calculate(facts,risk_free=.05,mrp=.05,as_of=ASOF)
        self.assertIsNone(result['metrics']['valuation_pe'])
        self.assertEqual(result['inputs']['valuation_fcf'],100e6)

    def module(self):
        try:
            return importlib.import_module('live_analysis')
        except ImportError:
            self.fail('The build needs live Python valuation formulas, not only an export packet')

    def analyze(self, ticker=None, **kwargs):
        m = self.module()
        return m.analyze(ticker or ticker_fixture(), 'ZTS', quote=None,
            risk_free=.05, mrp=.05, as_of=ASOF, **kwargs)

    def test_no_growth_equity_value_and_inverse_are_reproduced(self):
        m = self.module()
        self.assertAlmostEqual(m.dcf_value(100., 10., .10, 0., 0., 5), 100., places=9)
        self.assertAlmostEqual(m.reverse_dcf(100., 100., 10., .10, 0., 5), 0., places=8)

    def test_current_cash_shares_price_and_rate_change_outputs(self):
        a = self.analyze()
        b = self.analyze(ticker_fixture(fcf=200e6))
        c = self.analyze(ticker_fixture(shares=20e6))
        self.assertAlmostEqual(a['valuation']['ngv_per_share'], 100.)
        self.assertAlmostEqual(b['valuation']['ngv_per_share'], 200.)
        self.assertAlmostEqual(c['valuation']['ngv_per_share'], 50.)
        expensive = self.analyze(ticker_fixture(price=200.))
        self.assertGreater(expensive['valuation']['reverse_dcf_growth_pct'],
                           a['valuation']['reverse_dcf_growth_pct'])
        self.assertAlmostEqual(a['parameters']['discount_rate_pct'], 10.)
        self.assertEqual(a['inputs']['fcf'], 100e6)
        json.dumps(a, allow_nan=False)

    def test_unknown_debt_never_becomes_a_neutral_balance_score(self):
        t = ticker_fixture()
        t.balance_sheet = t.balance_sheet.drop('Total Debt')
        result = self.analyze(t)
        self.assertIsNone(result['components']['b'])
        self.assertIsNone(result['model_score'])
        self.assertIsNone(result['inputs']['debt'])

    def test_three_quarters_are_not_annualized_and_annual_data_remains_available(self):
        t = ticker_fixture()
        dates = pd.to_datetime(['2026-06-30','2026-03-31','2025-12-31'])
        t.quarterly_cashflow=pd.DataFrame([[1e6]*3,[-.1e6]*3],
            index=['Operating Cash Flow','Capital Expenditure'],columns=dates)
        t.quarterly_income_stmt=pd.DataFrame([[20e6]*3],index=['Total Revenue'],columns=dates)
        result=self.analyze(t)
        self.assertEqual(result['basis'],'FY')
        self.assertEqual(result['inputs']['fcf'],100e6)
        self.assertEqual(result['financial_period'],'2025-12-31')

    def test_equity_cash_flow_does_not_subtract_net_debt_again(self):
        a=self.analyze(ticker_fixture(debt=50e6))
        b=self.analyze(ticker_fixture(debt=500e6))
        self.assertAlmostEqual(a['valuation']['ngv_per_share'],b['valuation']['ngv_per_share'])
        self.assertAlmostEqual(a['valuation']['dcf_per_share'],b['valuation']['dcf_per_share'])

    def test_currency_mismatch_does_not_create_a_price_comparison(self):
        t=ticker_fixture()
        t.info['financialCurrency']='EUR'
        result=self.analyze(t)
        self.assertIsNone(result['valuation']['ngv_per_share'])
        self.assertIsNone(result['valuation']['dcf_per_share'])
        self.assertIsNone(result['components']['v'])

    def test_commodity_value_uses_a_multi_year_cash_proxy_instead_of_one_peak(self):
        m=self.module()
        facts=m.extract(ticker_fixture(), 'DVN', as_of=ASOF)
        facts.update(midcycle=True, annual_fcf_series=[dict(period=f'{year}-12-31',value=value)
            for year,value in [(2025,300e6),(2024,100e6),(2023,200e6)]])
        result=m.calculate(facts,risk_free=.05,mrp=.05,as_of=ASOF)
        self.assertAlmostEqual(result['valuation']['ngv_per_share'],200.)
        self.assertEqual(result['inputs']['valuation_fcf'],200e6)
        self.assertEqual(result['parameters']['cash_flow_policy'],'MIDCYCLE_MEAN_PROXY')

    def test_changed_rate_reprices_without_editing_a_stored_target(self):
        m=self.module();facts=m.extract(ticker_fixture(),'ZTS',as_of=ASOF)
        result=m.calculate(facts,risk_free=.07,mrp=.05,as_of=ASOF)
        self.assertAlmostEqual(result['valuation']['ngv_per_share'],100/.12/10)

    def test_empty_oldest_yahoo_column_does_not_discard_three_complete_years(self):
        m=self.module()
        facts=m.extract(ticker_fixture(), 'DVN', as_of=ASOF)
        facts.update(midcycle=True, annual_fcf_series=[dict(period=f'{year}-12-31',value=value)
            for year,value in [(2025,300e6),(2024,100e6),(2023,200e6),(2022,None)]])
        result=m.calculate(facts,risk_free=.05,mrp=.05,as_of=ASOF)
        self.assertAlmostEqual(result['valuation']['ngv_per_share'],200.)

    def test_pence_quote_and_pounds_statements_have_an_explicit_unit_bridge(self):
        t=ticker_fixture(price=10000.)
        t.info.update(currency='GBp',financialCurrency='GBP')
        result=self.analyze(t)
        self.assertAlmostEqual(result['valuation']['ngv_per_share'],10000.)
        self.assertEqual(result['parameters']['currency_factor'],100.)


class DynamicBuildIntegration(unittest.TestCase):
    def test_failed_live_quote_can_use_only_a_fresh_dated_same_currency_cached_quote(self):
        e=self.engine();m=importlib.import_module('live_analysis')
        facts=m.extract(ticker_fixture(), 'ZTS', as_of=ASOF)
        for changes,cutoff,expected in [({},ASOF,100.),
            ({},datetime(2026,11,1,tzinfo=timezone.utc),None),
            ({'currency':'EUR'},ASOF,None),({'quote_observed_at':None},ASOF,None)]:
            value=copy.deepcopy(e.DATA['ZTS']);value.update(price=None,quote_observed_at=None)
            packet=dict(facts,**changes)
            with tempfile.TemporaryDirectory() as tmp,patch.object(e,'DATA',{'ZTS':value}):
                path=Path(tmp)/'facts.json';path.write_text(json.dumps(dict(schema=m.VERSION,entries={'ZTS':packet})))
                def offline(symbol):raise RuntimeError('offline')
                e.refresh_dynamic_analysis(cache_path=path,as_of=cutoff,ticker_factory=offline)
            self.assertEqual(value.get('price'),expected)
            if expected:
                self.assertEqual(value['quote_observed_at'],facts['quote_observed_at'])
                self.assertEqual(value['quote_time_status'],'CACHED_DATED')

    def test_older_provider_period_never_overwrites_newer_stored_financials(self):
        e=self.engine();m=importlib.import_module('live_analysis')
        fresh=m.extract(ticker_fixture(), 'ZTS', as_of=ASOF)
        newer=copy.deepcopy(fresh)
        newer.update(financial_period='2026-06-30',period_ends=['2026-06-30'],beta=.4,quote_price=90.)
        newer['inputs']=dict(newer['inputs'],fcf=150e6,valuation_fcf=150e6)
        row=copy.deepcopy(e.DATA['ZTS']);row.update(price=100.,quote_observed_at='2026-10-24T20:00:00Z')
        with tempfile.TemporaryDirectory() as tmp,patch.object(e,'DATA',{'ZTS':row}), \
             patch.object(e.WACC,'resolve_risk_free',return_value=5.), \
             patch.object(e.WACC,'MARKET_RISK_PREMIUM',5.):
            path=Path(tmp)/'facts.json';path.write_text(json.dumps(dict(schema=m.VERSION,entries={'ZTS':newer})))
            counts=e.refresh_dynamic_analysis(cache_path=path,as_of=ASOF,
                                              ticker_factory=lambda symbol:ticker_fixture())
            stored=json.loads(path.read_text())['entries']['ZTS']
        analysis=row['dynamic_analysis']
        self.assertEqual(counts['retained_newer_period'],1)
        self.assertEqual(analysis['financial_period'],'2026-06-30')
        self.assertEqual(analysis['inputs']['fcf'],150e6)
        self.assertEqual(analysis['data_status'],'NEWER_PERIOD_RETAINED')
        self.assertEqual(stored['financial_period'],'2026-06-30')
        self.assertEqual(stored['quote_price'],fresh['quote_price'])
        self.assertEqual(stored['beta'],fresh['beta'])
        self.assertTrue(any('older financial period' in w for w in analysis['warnings']))

    def test_same_or_newer_provider_period_still_refreshes(self):
        e=self.engine();m=importlib.import_module('live_analysis')
        fresh=m.extract(ticker_fixture(fcf=120e6), 'ZTS', as_of=ASOF)
        older=m.extract(ticker_fixture(), 'ZTS', as_of=ASOF)
        older.update(financial_period='2025-09-30')
        row=copy.deepcopy(e.DATA['ZTS']);row.update(price=100.,quote_observed_at='2026-10-24T20:00:00Z')
        with tempfile.TemporaryDirectory() as tmp,patch.object(e,'DATA',{'ZTS':row}):
            path=Path(tmp)/'facts.json';path.write_text(json.dumps(dict(schema=m.VERSION,entries={'ZTS':older})))
            counts=e.refresh_dynamic_analysis(cache_path=path,as_of=ASOF,
                                              ticker_factory=lambda symbol:ticker_fixture(fcf=120e6))
        self.assertEqual(counts['refreshed'],1)
        self.assertEqual(row['dynamic_analysis']['inputs']['fcf'],fresh['inputs']['fcf'])

    def test_missing_beta_keeps_the_last_known_beta(self):
        e=self.engine();m=importlib.import_module('live_analysis')
        stored=m.extract(ticker_fixture(), 'ZTS', as_of=ASOF);stored['beta']=.9
        t=ticker_fixture();t.info.pop('beta',None)
        row=copy.deepcopy(e.DATA['ZTS']);row.update(price=100.,quote_observed_at='2026-10-24T20:00:00Z')
        with tempfile.TemporaryDirectory() as tmp,patch.object(e,'DATA',{'ZTS':row}):
            path=Path(tmp)/'facts.json';path.write_text(json.dumps(dict(schema=m.VERSION,entries={'ZTS':stored})))
            e.refresh_dynamic_analysis(cache_path=path,as_of=ASOF,ticker_factory=lambda symbol:t)
            self.assertEqual(json.loads(path.read_text())['entries']['ZTS']['beta_basis'],'CARRIED_FROM_PREVIOUS_FETCH')
        self.assertEqual(row['dynamic_analysis']['parameters']['beta'],.9)

    def engine(self):
        from test_framework_contract import engine
        self.assertTrue(callable(getattr(engine,'refresh_dynamic_analysis',None)),
                        'Every build must refresh financial inputs and recompute the model')
        return engine

    def test_zoetis_research_survives_while_current_formulas_replace_fixed_total(self):
        e=self.engine()
        row=copy.deepcopy(e.DATA['ZTS'])
        row.update(price=100.,quote_observed_at='2026-10-23T20:00:00Z')
        old_cash=copy.deepcopy(row['reported_cash_flow'])
        with tempfile.TemporaryDirectory() as tmp, patch.object(e,'DATA',{'ZTS':row}), \
             patch.object(e.WACC,'resolve_risk_free',return_value=5.), \
             patch.object(e.WACC,'MARKET_RISK_PREMIUM',5.):
            e.refresh_dynamic_analysis(cache_path=Path(tmp)/'facts.json',as_of=ASOF,
                                       ticker_factory=lambda symbol:ticker_fixture())
            self.assertEqual(row['reported_cash_flow'],old_cash)
            self.assertEqual(row['primary_analysis_archive']['score_fixed'],4.55)
            self.assertAlmostEqual(e.ngv(row),100.)
            self.assertNotEqual(e.score(row),4.55)
            self.assertEqual(row['dynamic_analysis']['review_status'],'REVIEW_REQUIRED')
            checked=e.assessment(row,ticker='ZTS',as_of=ASOF)
            self.assertIsNotNone(checked['model_score'])
            self.assertIsNone(checked['rating'])

    def test_failed_refresh_retains_last_good_facts_and_reprices_current_quote(self):
        e=self.engine()
        row=copy.deepcopy(e.DATA['ZTS'])
        row.update(price=100.,quote_observed_at='2026-10-23T20:00:00Z')
        with tempfile.TemporaryDirectory() as tmp, patch.object(e,'DATA',{'ZTS':row}), \
             patch.object(e.WACC,'resolve_risk_free',return_value=5.), \
             patch.object(e.WACC,'MARKET_RISK_PREMIUM',5.):
            path=Path(tmp)/'facts.json'
            e.refresh_dynamic_analysis(cache_path=path,as_of=ASOF,ticker_factory=lambda symbol:ticker_fixture())
            before=copy.deepcopy(row['dynamic_analysis'])
            row['price']=200.
            def offline(symbol):raise RuntimeError('offline')
            e.refresh_dynamic_analysis(cache_path=path,as_of=ASOF,ticker_factory=offline)
            after=row['dynamic_analysis']
            self.assertEqual(after['fetched_at'],before['fetched_at'])
            self.assertEqual(after['inputs']['fcf'],100e6)
            self.assertEqual(after['inputs']['quote_price'],200.)
            self.assertGreater(after['valuation']['reverse_dcf_growth_pct'],
                               before['valuation']['reverse_dcf_growth_pct'])
            self.assertEqual(after['data_status'],'CACHED_INPUTS')
            self.assertTrue(row['reported_cash_flow'])

    def test_distributable_cash_flow_models_are_not_replaced_by_ordinary_fcf(self):
        e=self.engine()
        row=copy.deepcopy(e.DATA['ENB'])
        before=copy.deepcopy(row)
        with tempfile.TemporaryDirectory() as tmp, patch.object(e,'DATA',{'ENB':row}):
            counts=e.refresh_dynamic_analysis(cache_path=Path(tmp)/'facts.json',as_of=ASOF,
                ticker_factory=lambda symbol:self.fail('Specialty cash flow needs its own model'))
        self.assertEqual(row,before)
        self.assertEqual(counts['specialized'],1)

    def test_small_negative_cushion_preserves_original_tolerance_and_score_tie_out(self):
        e=self.engine()
        row=copy.deepcopy(e.DATA['ZTS'])
        row.update(price=100.,quote_observed_at='2026-10-23T20:00:00Z')
        ticker=ticker_fixture()
        prior=ticker.cashflow.columns[1]
        ticker.cashflow.loc['Operating Cash Flow',prior]=100e6/.9975+20e6
        with tempfile.TemporaryDirectory() as tmp, patch.object(e,'DATA',{'ZTS':row}), \
             patch.object(e.WACC,'resolve_risk_free',return_value=5.), \
             patch.object(e.WACC,'MARKET_RISK_PREMIUM',5.):
            e.refresh_dynamic_analysis(cache_path=Path(tmp)/'facts.json',as_of=ASOF,
                                       ticker_factory=lambda symbol:ticker)
            checked=e.assessment(row,ticker='ZTS',as_of=ASOF)
            self.assertAlmostEqual(e.cushion(row),-.25)
            self.assertAlmostEqual(e.score(row),checked['model_score'])
            self.assertEqual(row['dynamic_analysis']['components']['pr'],e.priced_in_live(row))

    def test_future_cached_facts_are_not_backfilled_into_an_earlier_analysis(self):
        e=self.engine()
        m=importlib.import_module('live_analysis')
        facts=m.extract(ticker_fixture(),'ZTS',as_of=ASOF)
        facts['fetched_at']='2026-10-26T00:00:00Z'
        row=copy.deepcopy(e.DATA['ZTS'])
        with tempfile.TemporaryDirectory() as tmp, patch.object(e,'DATA',{'ZTS':row}):
            path=Path(tmp)/'facts.json'
            path.write_text(json.dumps(dict(schema=m.VERSION,entries={'ZTS':facts})))
            def offline(symbol):raise RuntimeError('offline')
            e.refresh_dynamic_analysis(cache_path=path,as_of=ASOF,ticker_factory=offline)
        self.assertEqual(row['dynamic_analysis']['data_status'],'UNAVAILABLE')
        self.assertIsNone(row['dynamic_analysis']['valuation']['ngv_per_share'])


if __name__=='__main__':
    unittest.main()


class DividendZeroTests(unittest.TestCase):
    def test_only_an_explicit_zero_trailing_dividend_counts_as_zero(self):
        import live_analysis as m
        self.assertTrue(m.no_dividend(dict(trailingAnnualDividendRate=0.0)))
        self.assertFalse(m.no_dividend({}))
        self.assertFalse(m.no_dividend(dict(trailingAnnualDividendRate=0.0, dividendRate=1.2)))
        self.assertFalse(m.no_dividend(dict(trailingAnnualDividendRate=2.0)))

    def test_non_payer_gets_shareholder_returns_from_buybacks(self):
        import live_analysis as m
        t = ticker_fixture()
        t.cashflow = t.cashflow.drop(index='Cash Dividends Paid')
        t.info.update(trailingAnnualDividendRate=0.0)
        facts = m.extract(t, 'ZTS', as_of=ASOF)
        self.assertEqual(facts['inputs']['dividends'], 0.)
        self.assertEqual(facts['dividends_basis'], 'PROVIDER_ZERO_TRAILING_DIVIDEND')
        t2 = ticker_fixture(); t2.cashflow = t2.cashflow.drop(index='Cash Dividends Paid')
        self.assertIsNone(m.extract(t2, 'ZTS', as_of=ASOF)['inputs']['dividends'])


class CrossCurrencyAndBoundTests(unittest.TestCase):
    def test_adr_quoted_in_usd_is_converted_with_a_dated_fx_rate(self):
        import live_analysis as m
        facts = m.extract(ticker_fixture(price=40.), 'NVO', as_of=ASOF)
        facts.update(currency='USD', financial_currency='DKK')
        suspended = m.calculate(facts, risk_free=.05, mrp=.05, as_of=ASOF)
        self.assertIsNone(suspended['valuation']['ngv_per_share'])
        facts['fx'] = dict(pair='DKKUSD', rate=.15, observed_at=ASOF.isoformat(), source='YAHOO_FX')
        result = m.calculate(facts, risk_free=.05, mrp=.05, as_of=ASOF)
        dkk = m.calculate(dict(facts, currency='DKK', fx=None), quote=dict(price=40/.15,
            observed_at=facts['quote_observed_at']), risk_free=.05, mrp=.05, as_of=ASOF)
        self.assertAlmostEqual(result['valuation']['ngv_per_share'], dkk['valuation']['ngv_per_share'] * .15)
        self.assertAlmostEqual(result['valuation']['reverse_dcf_growth_pct'], dkk['valuation']['reverse_dcf_growth_pct'])
        self.assertTrue(any('DKKUSD' in w for w in result['warnings']))
        facts['fx'] = dict(pair='EURUSD', rate=1.1)
        self.assertIsNone(m.calculate(facts, risk_free=.05, mrp=.05, as_of=ASOF)['valuation']['ngv_per_share'])

    def test_price_beyond_the_solver_range_keeps_a_flagged_edge(self):
        import live_analysis as m
        facts = m.extract(ticker_fixture(price=100000.), 'TSLA', as_of=ASOF)
        result = m.calculate(facts, risk_free=.05, mrp=.05, as_of=ASOF)
        self.assertEqual(result['valuation']['reverse_dcf_growth_pct'], 100.)
        self.assertEqual(result['valuation']['reverse_dcf_bound'], 'ABOVE_100_PCT')
        normal = m.calculate(m.extract(ticker_fixture(), 'ZTS', as_of=ASOF), risk_free=.05, mrp=.05, as_of=ASOF)
        self.assertIsNone(normal['valuation']['reverse_dcf_bound'])
