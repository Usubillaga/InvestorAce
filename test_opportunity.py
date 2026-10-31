"""Behavioral checks for discounted quality and regime-aware automatic signals."""
import copy
import importlib
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from test_framework_contract import engine


ASOF = datetime(2026, 10, 28, 12, tzinfo=timezone.utc)


def row():
    return dict(sector='Info Svcs', cur='EUR', price=60.,
        quote_observed_at='2026-10-27T16:35:03+00:00',
        dynamic_analysis=dict(schema='dynamic-analysis-v1',
            fetched_at='2026-10-28T02:00:00+00:00', financial_period='2026-06-30',
            inputs=dict(debt=200., cash=20., ebitda=100., fcf=80., valuation_fcf=80., net_income=100.),
            components=dict(p=9.,c=9.,b=7.,g=4.,r=9.,d=8.5),
            metrics=dict(operating_margin_pct=35.,fcf_margin_pct=24.,
                         fcf_yield_pct=8.,valuation_pe=12.,reported_pe=12.,
                         net_debt_ebitda=1.8,revenue_growth_pct=3.),
            parameters=dict(cash_flow_policy='REPORTED_FCF_PROXY'),
            valuation=dict(reverse_dcf_growth_pct=-5.,ngv_per_share=60.)))


def spec():
    return dict(affinity=engine.AFF, duration=engine.DUR_W, balance=engine.BS_W,
                payout=engine.PAY_W, multiplier=12., clamp=40., version=engine.REGIME_MODEL_VERSION)


class OpportunityTests(unittest.TestCase):
    def assess(self, value=None, regime='REFLATION'):
        try:
            module = importlib.import_module('opportunity')
        except ImportError:
            self.fail('The current report has no regime-aware opportunity assessment')
        return module.assess(value or row(), regime=regime, spec=spec(), as_of=ASOF)

    def test_discounted_quality_has_a_buy_signal_without_manual_approval(self):
        result = self.assess()
        self.assertEqual(result['label'], 'Buy')
        self.assertGreater(result['score'], 7.)
        self.assertEqual(result['review_status'], 'REVIEW_REQUIRED')
        self.assertIn('DEFENSIVE', result['profile']['tags'])
        self.assertIn('QUALITY', result['profile']['tags'])
        self.assertEqual(result['metrics']['valuation_pe'], 12.)
        self.assertEqual(len(result['regime_fit']), 5)

    def test_expensive_quality_is_not_given_the_discounted_label(self):
        value = row(); dynamic = value['dynamic_analysis']
        dynamic['metrics'].update(fcf_yield_pct=2.,valuation_pe=45.,reported_pe=45.)
        dynamic['valuation'].update(reverse_dcf_growth_pct=20.,ngv_per_share=15.)
        self.assertEqual(self.assess(value)['label'], 'Hold Negative')

    def test_negative_cash_flow_cannot_buy_its_way_out_with_a_cheap_pe(self):
        value = row();value['dynamic_analysis']['inputs']['fcf']=-10.
        value['dynamic_analysis']['metrics']['fcf_margin_pct']=-3.
        self.assertEqual(self.assess(value)['label'], 'Hold Negative')

    def test_heavy_leverage_caps_even_high_margin_discounted_equity(self):
        value=row();value['dynamic_analysis']['components']['b']=1.5
        self.assertEqual(self.assess(value)['label'], 'Hold Negative')

    def test_unknown_cash_is_a_conservative_range_not_zero_cash(self):
        value=row();dynamic=value['dynamic_analysis'];dynamic['components']['b']=None
        dynamic['inputs']['cash']=None;dynamic['metrics']['net_debt_ebitda']=None
        result=self.assess(value)
        self.assertIsNone(result['score'])
        self.assertIsNone(result['quality_score'])
        self.assertEqual(result['label'], 'Buy')
        self.assertLess(result['score_lower'],result['score_upper'])
        self.assertIsNone(dynamic['inputs']['cash'])
        self.assertIn('BALANCE_LOWER_BOUND',result['flags'])

    def test_uncertain_quality_gate_does_not_truncate_an_attainable_strong_buy(self):
        value=row();dynamic=value['dynamic_analysis']
        dynamic['components'].update(p=7.,c=7.,b=None,g=7.,r=10.,d=10.)
        dynamic['inputs']['cash']=None
        dynamic['metrics']['valuation_pe']=8.
        partial=self.assess(value,regime='RECESSION')
        complete=copy.deepcopy(value)
        complete['dynamic_analysis']['components']['b']=9.5
        complete['dynamic_analysis']['inputs']['cash']=250.
        completed=self.assess(complete,regime='RECESSION')
        self.assertEqual(completed['label'],'Strong Buy')
        self.assertGreaterEqual(partial['score_upper'],completed['score'])
        self.assertIsNone(partial['label'])

    def test_fiscal_age_expiry_is_enforced_without_rebuilding_frozen_scores(self):
        module=importlib.import_module('opportunity');value=row()
        value['dynamic_analysis']['financial_period']=(ASOF.date()-timedelta(days=550)).isoformat()
        fresh=self.assess(value);later=ASOF+timedelta(days=1)
        self.assertEqual(fresh['label'],'Buy')
        self.assertIsNone(module.project(fresh,as_of=later)['label'])

    def test_direct_stale_assessment_withdraws_the_price_based_value_tag(self):
        value=row();value['quote_observed_at']='2026-10-01T20:00:00Z'
        self.assertNotIn('VALUE',self.assess(value)['profile']['tags'])

    def test_a_missing_major_input_does_not_become_sell_or_a_neutral_score(self):
        value=row();value['dynamic_analysis']['components']['c']=None
        result=self.assess(value)
        self.assertIsNone(result['score']);self.assertIsNone(result['label'])
        self.assertIn('c',result['missing_components'])

    def test_five_labels_use_the_unrounded_thresholds(self):
        module=importlib.import_module('opportunity')
        for score,label in [(8.5,'Strong Buy'),(8.4999,'Buy'),(7.,'Buy'),
                            (6.9999,'Hold Positive'),(5.5,'Hold Positive'),
                            (5.4999,'Hold Negative'),(3.5,'Hold Negative'),(3.4999,'Sell')]:
            self.assertEqual(module.label(score),label)

    def test_current_regime_changes_score_without_changing_fundamentals(self):
        a=self.assess(regime='REFLATION');b=self.assess(regime='RECESSION')
        self.assertGreater(b['score'],a['score'])
        self.assertEqual(a['fundamental_score'],b['fundamental_score'])
        self.assertEqual(a['profile'],b['profile'])

    def test_expired_quote_withdraws_signal_and_preserves_business_profile(self):
        value=row();value['quote_observed_at']='2026-10-01T20:00:00Z'
        result=self.assess(value)
        self.assertIsNone(result['label']);self.assertIsNone(result['score'])
        self.assertIn('DEFENSIVE',result['profile']['tags'])
        self.assertEqual(result['quote_status'],'STALE')

    def test_commodity_reported_pe_is_not_scored_as_midcycle_earnings(self):
        value=row();value.update(sector='Energy',midcycle=True)
        value['dynamic_analysis']['metrics']['valuation_pe']=None
        value['dynamic_analysis']['parameters']['cash_flow_policy']='MIDCYCLE_MEAN_PROXY'
        result=self.assess(value)
        self.assertIn('CYCLICAL',result['profile']['tags'])
        self.assertIn('COMMODITY',result['profile']['tags'])
        self.assertIn('pe',result['missing_components'])
        self.assertIn('MIDCYCLE_PROXY',result['flags'])
        value['dynamic_analysis']['metrics']['revenue_growth_pct']=30.
        self.assertNotIn('GROWTH',self.assess(value)['profile']['tags'])

    def test_input_packet_is_immutable(self):
        value=row();before=copy.deepcopy(value);self.assess(value)
        self.assertEqual(value,before)

    def test_missing_current_regime_keeps_fundamentals_but_no_composite(self):
        result=self.assess(regime=None)
        self.assertIsNone(result['label']);self.assertIsNone(result['score'])
        self.assertIsNotNone(result['fundamental_score'])

    def test_engine_exposes_the_new_signal_without_replacing_legacy_score(self):
        value=row();value['dynamic_analysis'].update(model_score=4.55)
        self.assertTrue(callable(getattr(engine,'opportunity',None)),
                        'The report still only exposes the manually gated legacy score')
        result=engine.opportunity(value,regime='REFLATION',as_of=ASOF)
        self.assertEqual(result['label'],'Buy')
        self.assertEqual(engine.score(value),4.55)

    def test_scanner_and_review_packet_keep_the_signal_separate_from_approval(self):
        import market_scanner
        from test_market_scanner import observation
        record=observation();value=row()
        idea=self.assess(value)
        record['_evidence'].update(captured_at='2026-10-28T10:00:00Z',inputs={'EX':value})
        record['EX']['opportunity']=idea
        result=market_scanner.build_scan(record,as_of=ASOF)
        current=result['rows'][0]
        self.assertEqual(current['opportunity']['label'],'Buy')
        self.assertIsNone(current['rating'])
        self.assertEqual(result['review_packets']['universe']['EX']['snapshot']['model_output']
                         ['opportunity_at_cutoff']['label'],'Buy')
        self.assertIn('REFLATION',current['opportunity_html'])

    def test_frozen_projection_withdraws_price_dependent_contributions(self):
        module=importlib.import_module('opportunity')
        value=self.assess();expired=module.project(value,as_of=datetime(2026,11,1,tzinfo=timezone.utc))
        self.assertIsNone(expired['label']);self.assertIsNone(expired['score_lower'])
        self.assertNotIn('valuation_pe',expired['metrics'])
        self.assertEqual(expired['regime_fit'],{})
        self.assertEqual(value['label'],'Buy')

    def test_snapshot_persists_opportunity_and_preserves_legacy_channel(self):
        import evidence
        value=row();value.update(dynamic_analysis=dict(value['dynamic_analysis'],model_score=4.55,
            score_explanation=dict(schema='score-explanation-v1',status='DECOMPOSED',
                total=4.55,components=[],reconciles=True)))
        with patch.object(engine,'DATA',{'EX':value}),patch.object(engine,'validate_full',return_value=([],[])):
            record=engine.observation(dict(ok=True,regime='REFLATION'),
                evidence.model_bundle(engine.Path(engine.__file__).parent),captured_at=ASOF.isoformat())
        self.assertEqual(record['EX']['score'],4.55)
        self.assertEqual(record['EX']['opportunity']['label'],'Buy')
        self.assertEqual(record['_models']['opportunity'],'opportunity-v17.1')


def priced_row():
    value = row(); dynamic = value['dynamic_analysis']
    dynamic['parameters'].update(discount_rate_pct=9., terminal_growth_pct=2., currency_factor=1.)
    dynamic['metrics']['market_cap'] = 960.
    return value


class BuyPriceTests(unittest.TestCase):
    def thresholds(self, value, regime='REFLATION'):
        module = importlib.import_module('opportunity')
        return module, module.price_thresholds(value, regime=regime, spec=spec(), as_of=ASOF)

    def test_buy_threshold_is_where_the_label_flips(self):
        module, result = self.thresholds(priced_row())
        self.assertEqual(result['basis'], 'PRICE_ONLY_RESCORE')
        self.assertIsNotNone(result['buy'])
        at = module.assess(module._at_price(priced_row(), result['buy'] * .999),
                           regime='REFLATION', spec=spec(), as_of=ASOF)
        above = module.assess(module._at_price(priced_row(), result['buy'] * 1.01),
                              regime='REFLATION', spec=spec(), as_of=ASOF)
        self.assertIn(at['label'], ('Buy', 'Strong Buy'))
        self.assertNotIn(above['label'], ('Buy', 'Strong Buy'))
        if result['strong_buy'] is not None:
            self.assertLess(result['strong_buy'], result['buy'])

    def test_repricing_moves_only_price_dependent_inputs(self):
        module = importlib.import_module('opportunity'); value = priced_row()
        half = module._at_price(value, 30.)['dynamic_analysis']
        self.assertAlmostEqual(half['metrics']['valuation_pe'], 6.)
        self.assertAlmostEqual(half['metrics']['fcf_yield_pct'], 16.)
        self.assertEqual(half['components'], value['dynamic_analysis']['components'])
        self.assertLess(half['valuation']['reverse_dcf_growth_pct'], -5.)

    def test_weak_balance_sheet_names_the_blocker_instead_of_a_price(self):
        value = priced_row(); value['dynamic_analysis']['components']['b'] = 1.5
        _, result = self.thresholds(value)
        self.assertIsNone(result['buy'])
        self.assertIn('balance sheet', result['blocker'])

    def test_stale_quote_or_missing_rate_gives_no_price(self):
        value = priced_row(); value['quote_observed_at'] = '2026-10-01T20:00:00Z'
        self.assertIsNone(self.thresholds(value)[1]['basis'])
        value = priced_row(); del value['dynamic_analysis']['parameters']['discount_rate_pct']
        self.assertEqual(self.thresholds(value)[1]['blocker'], 'PRICE_MODEL_UNAVAILABLE')

    def test_engine_attaches_thresholds_and_view_renders_them(self):
        import opportunity_view
        result = engine.opportunity(priced_row(), regime='REFLATION', as_of=ASOF)
        self.assertIsNotNone(result['price_thresholds']['buy'])
        self.assertIn('Buy ≤', opportunity_view.entry(result))
        stale = priced_row(); stale['quote_observed_at'] = '2026-10-01T20:00:00Z'
        withdrawn = engine.opportunity(stale, regime='REFLATION', as_of=ASOF)
        self.assertIsNone(withdrawn['price_thresholds'])
        self.assertIn('Buy price unavailable', opportunity_view.entry(withdrawn))

    def test_negative_cash_flow_is_a_named_blocker_not_a_missing_model(self):
        value = priced_row(); value['dynamic_analysis']['inputs']['valuation_fcf'] = -5.
        _, result = self.thresholds(value)
        self.assertIsNone(result['buy'])
        self.assertEqual(result['basis'], 'NO_POSITIVE_CASH_FLOW')
        import opportunity_view
        self.assertIn('No price reaches Buy', opportunity_view.entry(dict(price_thresholds=result)))

    def test_unknown_regime_fit_is_named_as_the_blocker(self):
        value = priced_row(); value['sector'] = 'Unmapped Sector'
        _, result = self.thresholds(value)
        self.assertIsNone(result['buy'])
        self.assertIn('current regime fit unknown', result['blocker'])


class ShortInterestTests(unittest.TestCase):
    def test_yahoo_fields_become_dated_positioning_and_never_zero(self):
        import live_analysis
        packet = live_analysis.short_interest(dict(sharesShort=3_000_000, sharesShortPriorMonth=2_500_000,
            shortPercentOfFloat=.25, shortRatio=8.9, dateShortInterest=1760486400))
        self.assertAlmostEqual(packet['pct_float'], 25.)
        self.assertAlmostEqual(packet['change_pct'], 20.)
        self.assertEqual(packet['settlement_date'], '2025-10-15')
        self.assertIsNone(live_analysis.short_interest({}))

    def test_short_interest_is_shown_but_does_not_move_the_score(self):
        import opportunity_view
        plain = engine.opportunity(priced_row(), regime='REFLATION', as_of=ASOF)
        value = priced_row(); value['dynamic_analysis']['positioning'] = dict(short_interest=dict(
            pct_float=25., days_to_cover=8.9, change_pct=20., settlement_date='2026-10-15'))
        shorted = engine.opportunity(value, regime='REFLATION', as_of=ASOF)
        self.assertEqual(plain['score'], shorted['score'])
        self.assertIn('25.0% of float', opportunity_view.short(shorted))
        self.assertIn('not reported', opportunity_view.short(plain))
