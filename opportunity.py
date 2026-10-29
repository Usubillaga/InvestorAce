"""Versioned, automatic discounted-quality signal; analyst approval is separate.

All calculations consume dated input packets. Missing contributions retain
their attainable intervals; no midpoint or neutral category is invented.
"""
import copy
from datetime import date, timedelta, timezone

import assessment
import autoscore
from integrity import finite_number, positive_number


VERSION = 'opportunity-v17.1'
PRICE_METRICS = ('valuation_pe','reported_pe','fcf_yield_pct','market_cap','cover_pct',
                 'earnings_yield_pct','shareholder_yield_pct')
WEIGHTS = dict(p=.12, c=.105, b=.075, fcfy=.15, pe=.10, expectations=.15,
               g=.10, r=.03, d=.02, macro=.15)
LABELS = dict(p='Operating profitability', c='Cash generation', b='Balance sheet',
    fcfy='Free cash flow yield', pe='Earnings valuation', expectations='Priced-in growth',
    g='Revenue growth', r='Shareholder returns', d='Dilution', macro='Current regime fit')
REGIMES = ('GOLDILOCKS', 'REFLATION', 'INFLATION', 'STAGFLATION', 'RECESSION')
FINANCIAL_MAX_AGE_DAYS = 550
DEFENSIVE = {'Info Svcs','Animal Health','Healthcare','Health Ins','Pharma','Staples',
             'Consumer Defensive','Utilities','MedTech','Health Data'}
GROWTH = {'Software','Technology','Semis','AI Infra','Platform','Space','Biotech',
          'Ad Tech','AdTech','Health Data'}
CYCLICAL = {'Consumer Cyclical','Industrials','Automotive','Aerospace','Luxury',
            'Apparel','Restaurant','Media','Real Estate','REIT','Banks','Materials','Energy'}


def label(score):
    score = finite_number(score)
    if score is None or not 0 <= score <= 10:
        return None
    for ceiling, name in ((3.5,'Sell'),(5.5,'Hold Negative'),(7.,'Hold Positive'),
                          (8.5,'Buy'),(float('inf'),'Strong Buy')):
        if score < ceiling:
            return name


def curve(value, knots):
    value = finite_number(value)
    if value is None:
        return None
    if value <= knots[0][0]:
        return knots[0][1]
    for (x0,y0),(x1,y1) in zip(knots,knots[1:]):
        if value <= x1:
            return y0 + (y1-y0)*(value-x0)/(x1-x0)
    return knots[-1][1]


def financial_current(period, as_of):
    try:
        age = (as_of.astimezone(timezone.utc).date()-date.fromisoformat(period)).days
        return 0 <= age <= FINANCIAL_MAX_AGE_DAYS
    except (TypeError,ValueError):
        return False


def profile(row, values, metrics):
    sector = row.get('sector')
    tags = []
    if sector in DEFENSIVE:
        tags.append('DEFENSIVE')
    if row.get('midcycle') or sector in ('Energy','Materials'):
        tags += ['CYCLICAL','COMMODITY']
    elif sector in CYCLICAL:
        tags.append('CYCLICAL')
    if sector in GROWTH or ('COMMODITY' not in tags and (finite_number(metrics.get('revenue_growth_pct')) or 0) >= 10):
        tags.append('GROWTH')
    if sector in ('REIT','Utilities','Midstream'):
        tags.append('INCOME')
    if all(values.get(k) is not None and values[k] >= limit
           for k,limit in (('p',7),('c',7),('b',5))):
        tags.append('QUALITY')
    if (finite_number(metrics.get('fcf_yield_pct')) or -1) >= 6:
        tags.append('VALUE')
    return dict(tags=tags or ['UNCLASSIFIED'], basis='SECTOR_AND_REPORTED_METRICS',
                confidence='HEURISTIC', sector=sector)


def fits(row, ranges, cover, spec):
    """The frozen regime formula, with bounds replacing missing balance/payout."""
    if cover is None or row.get('sector') not in set().union(*(
            set(x) for x in spec['affinity'].values())):
        return {}, {}
    duration = max(-spec['clamp'], min(spec['clamp'], (cover-.60)*100))
    exact, bounds = {}, {}
    for regime in REGIMES:
        common = (50 + spec['multiplier']*spec['affinity'][regime].get(row.get('sector'),0)
                  + spec['duration'][regime]*duration)
        parts = [spec['balance'][regime]*(x-6) for x in ranges['b']]
        payouts = [spec['payout'][regime]*(x-6) for x in ranges['r']]
        lower = round(max(0.,min(100.,common+min(parts)+min(payouts))),1)
        upper = round(max(0.,min(100.,common+max(parts)+max(payouts))),1)
        bounds[regime] = [lower,upper]
        exact[regime] = lower if lower == upper else None
    return exact, bounds


def assess(row, *, regime, spec, as_of=None):
    as_of = assessment._now(as_of)
    dynamic = row.get('dynamic_analysis') or {}
    metrics = dict(dynamic.get('metrics') or {})
    inputs = dynamic.get('inputs') or {}
    source_values = dynamic.get('components') or {}
    values = {key: finite_number(source_values.get(key)) for key in ('p','c','b','g','r','d')}
    values = {k:v if v is not None and 0 <= v <= 10 else None for k,v in values.items()}
    values['fcfy'] = curve(metrics.get('fcf_yield_pct'),[(0,0),(2,2),(4,5),(6,7.5),(8,9),(10,10)])
    pe = finite_number(metrics.get('valuation_pe'))
    net_income = finite_number(inputs.get('net_income'))
    values['pe'] = (curve(pe,[(8,10),(12,9),(15,8),(20,6.5),(25,5),(35,3),(50,1),(100,0)])
                    if pe is not None and pe > 0 else 0. if net_income is not None and net_income <= 0
                    and not row.get('midcycle') else None)
    values['expectations'] = curve((dynamic.get('valuation') or {}).get('reverse_dcf_growth_pct'),
                                  [(-5,10),(0,9),(3,8),(6,6.5),(10,5),(15,3),(25,1)])
    ranges = {key:[value,value] if value is not None else [0.,10.] for key,value in values.items()}
    flags, caps = [], []
    debt, cash = finite_number(inputs.get('debt')), finite_number(inputs.get('cash'))
    ebitda = positive_number(inputs.get('ebitda'))
    balance_supported = values['b'] is not None
    if values['b'] is None and debt is not None and debt >= 0 and cash is None and ebitda:
        minimum = autoscore._band(debt/ebitda,autoscore.BALANCE,default=None)
        ranges['b'] = [minimum,9.5]
        balance_supported = True
        flags.append('BALANCE_LOWER_BOUND')
    if row.get('midcycle'):
        flags.append('MIDCYCLE_PROXY')
        if (dynamic.get('parameters') or {}).get('cash_flow_policy') != 'MIDCYCLE_MEAN_PROXY':
            values['fcfy'] = values['expectations'] = None
            ranges['fcfy'] = ranges['expectations'] = [0.,10.]
        if row.get('normalization_status') != 'VERIFIED':
            caps.append(dict(maximum=8.49,reason='Commodity cycle averages still require economic normalization.'))
    business = profile(row,values,metrics)
    qstatus = assessment.quote_status(row,as_of)
    period = dynamic.get('financial_period')
    fetched = assessment.timestamp(dynamic.get('fetched_at'))
    source_current = dynamic.get('schema') == 'dynamic-analysis-v1' and fetched is not None and fetched <= as_of
    source_current = source_current and financial_current(period,as_of)
    if not source_current:
        flags.append('FINANCIAL_PACKET_UNAVAILABLE')
    price_current = qstatus == 'DATED' and source_current
    if not price_current:
        business['tags'] = [x for x in business['tags'] if x != 'VALUE'] or ['UNCLASSIFIED']
        for key in ('fcfy','pe','expectations'):
            values[key],ranges[key] = None,[0.,10.]
    ngv = positive_number((dynamic.get('valuation') or {}).get('ngv_per_share'))
    cover = ngv/row['price'] if price_current and ngv else None
    regime_fit, fit_bounds = fits(row,ranges,cover,spec)
    current = fit_bounds.get(regime)
    values['macro'] = current[0]/10 if current and current[0] == current[1] else None
    ranges['macro'] = [x/10 for x in current] if current else [0.,10.]
    if not current:
        flags.append('CURRENT_REGIME_UNAVAILABLE')
    quality_bounds = [sum(ranges[k][i]*WEIGHTS[k] for k in ('p','c','b'))/.30 for i in (0,1)]
    valuation_bounds = [sum(ranges[k][i]*WEIGHTS[k] for k in ('fcfy','pe','expectations'))/.40 for i in (0,1)]
    quality,valuation = quality_bounds[0],valuation_bounds[0]
    fcf = finite_number(inputs.get('fcf'))
    margin = finite_number(metrics.get('operating_margin_pct'))
    if (fcf is not None and fcf <= 0) or (margin is not None and margin <= 0):
        caps.append(dict(maximum=5.49,reason='Negative cash/operating profit or excessive leverage: value-trap guard.'))
    if net_income is not None and net_income <= 0:
        caps.append(dict(maximum=6.99,reason='Reported earnings are not positive.'))
    maximums = [min([10.] + [item['maximum'] for item in caps])]*2
    for i in (0,1):
        conditional=[]
        if ranges['b'][i] < 3:
            conditional.append(dict(maximum=5.49,reason='Negative cash/operating profit or excessive leverage: value-trap guard.'))
        if quality_bounds[i] < 6 or valuation_bounds[i] < 6 or ranges['b'][i] < 4.5 or not current or current[i] < 35:
            conditional.append(dict(maximum=6.99,reason='Buy requires quality >=6, valuation >=6, balance >=4.5 and current fit >=35.'))
        if quality_bounds[i] < 7 or valuation_bounds[i] < 8 or ranges['b'][i] < 5 or not current or current[i] < 50:
            conditional.append(dict(maximum=8.49,reason='Strong Buy requires quality >=7, valuation >=8, balance >=5 and current fit >=50.'))
        maximums[i]=min([maximums[i]]+[item['maximum'] for item in conditional])
        for item in conditional:
            item['applies_to']='LOWER_BOUND' if i==0 else 'UPPER_BOUND'
        caps.extend(conditional)
    lower = sum(WEIGHTS[k]*ranges[k][0] for k in WEIGHTS)
    upper = sum(WEIGHTS[k]*ranges[k][1] for k in WEIGHTS)
    missing = [k for k in WEIGHTS if values[k] is None]
    core = all(values[k] is not None for k in ('p','c','fcfy','expectations')) and balance_supported
    available = price_current and current is not None and core
    point = lower if not missing and available else None
    result_lower,result_upper = min(maximums[0],lower),min(maximums[1],upper)
    signal = label(result_lower) if available and label(result_lower) == label(result_upper) else None
    fundamentals = [k for k in WEIGHTS if k != 'macro']
    fundamental = (sum(WEIGHTS[k]*values[k] for k in fundamentals)/.85
                   if all(values[k] is not None for k in fundamentals) else None)
    deadline = assessment.timestamp(row.get('quote_observed_at'))
    explanation = [dict(key=k,label=LABELS[k],value=values[k],weight=WEIGHTS[k],
        contribution=WEIGHTS[k]*values[k] if values[k] is not None else None,
        lower_contribution=WEIGHTS[k]*ranges[k][0],upper_contribution=WEIGHTS[k]*ranges[k][1]) for k in WEIGHTS]
    return dict(schema=VERSION,as_of=as_of.isoformat(),price=row.get('price'),
        quote_observed_at=row.get('quote_observed_at'),quote_status=qstatus,
        expires_at=(deadline+timedelta(hours=96)).isoformat() if deadline else None,
        score=min(maximums[0],point) if point is not None else None,label=signal,
        score_lower=result_lower if price_current else None,score_upper=result_upper if price_current else None,
        uncapped_score=point,score_cap=maximums[0] if maximums[0]==maximums[1] else None,
        score_cap_bounds=maximums,caps=caps,withdrawn=not price_current,
        status='COMPLETE' if point is not None else 'BOUNDED' if signal else 'PARTIAL',
        signal_basis='AUTOMATIC_MODEL',review_status='REVIEW_REQUIRED',
        fundamental_score=fundamental,
        quality_score=quality if all(values[k] is not None for k in ('p','c','b')) else None,
        quality_bounds=quality_bounds,
        valuation_score=valuation if price_current and all(values[k] is not None for k in ('fcfy','pe','expectations')) else None,
        valuation_bounds=valuation_bounds if price_current else None,
        profile=business,current_regime=regime,regime_fit=regime_fit,regime_fit_bounds=fit_bounds,
        current_fit=current[0] if current and current[0] == current[1] else None,
        current_fit_bounds=current,regime_model=spec['version'],
        metrics=metrics if price_current else {k:v for k,v in metrics.items() if k not in PRICE_METRICS},
        financial_period=period,financial_fetched_at=dynamic.get('fetched_at'),
        cash_flow_policy=(dynamic.get('parameters') or {}).get('cash_flow_policy'),
        implied_growth_pct=(dynamic.get('valuation') or {}).get('reverse_dcf_growth_pct') if price_current else None,
        components=explanation,missing_components=missing,flags=flags)


def project(stored, *, as_of=None):
    """Withdraw expired frozen signals without recalculating a historical model."""
    if not isinstance(stored,dict) or stored.get('schema') != VERSION:
        return None
    result = copy.deepcopy(stored)
    as_of = assessment._now(as_of)
    captured = assessment.timestamp(result.get('as_of'))
    qstatus = assessment.quote_status(result,as_of)
    if captured is None or captured > as_of or qstatus != 'DATED' or not financial_current(result.get('financial_period'),as_of):
        result.update(score=None,label=None,score_lower=None,score_upper=None,uncapped_score=None,
            fundamental_score=None,valuation_score=None,current_fit=None,current_fit_bounds=None,
            regime_fit={},regime_fit_bounds={},implied_growth_pct=None,quote_status=qstatus,status='PARTIAL',withdrawn=True)
        result['metrics'] = {k:v for k,v in result.get('metrics',{}).items() if k not in PRICE_METRICS}
        result['profile']['tags'] = [x for x in result['profile']['tags'] if x != 'VALUE']
        for component in result['components']:
            if component['key'] in ('fcfy','pe','expectations','macro','r'):
                component.update(value=None,contribution=None,lower_contribution=0.,
                                 upper_contribution=10*component['weight'])
    return result
