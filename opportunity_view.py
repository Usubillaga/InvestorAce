"""Compact, reusable rendering for the versioned opportunity signal."""
from html import escape

CSS = """
.opportunity-label{display:inline-block;border:1px solid currentColor;border-radius:5px;padding:4px 7px;font-size:11px;white-space:nowrap}
.opportunity-label.p-buy,.opportunity-label.p-sbuy{color:#66e39c}.opportunity-label.p-hpos{color:#63c6f0}.opportunity-label.p-hneg{color:#e5b45c}.opportunity-label.p-sell{color:#f06a6a}
.opportunity-tags{display:flex;flex-wrap:wrap;gap:4px;margin-top:7px;max-width:210px}
.opportunity-tag{border:1px solid #304457;border-radius:4px;padding:2px 5px;color:#b7cee2;font-size:10px}
.opportunity-metrics,.opportunity-legacy{display:block;font-size:11px;color:var(--mu);font-weight:400;line-height:1.65}
.opportunity-legacy{max-width:230px;margin-top:5px}.opportunity-legacy summary{font-size:10px}
.opportunity-score{font-size:20px;font-variant-numeric:tabular-nums;font-weight:700}
.opportunity-guide{border-left:3px solid var(--cyan);padding:10px 14px;margin:12px 0;font-size:12px;line-height:1.65;background:#101e29}
.opportunity-stock{border-top:1px solid var(--line);padding:12px 0}.opportunity-stock summary{font-size:14px}
.opportunity-stock .tw{margin:12px 0;max-width:100%;overflow:auto}.opportunity-stock table{min-width:600px}
.opportunity-fit-now{background:#172f38}.opportunity-caps{color:var(--amber);font-size:12px}
"""


def number(value, digits=2):
    return format(value,f'.{digits}f') if isinstance(value,(int,float)) else '—'


def interval(value, lower, upper, digits=2):
    if value is not None:
        return number(value,digits)
    return number(lower,digits)+'–'+number(upper,digits) if lower is not None and upper is not None else '—'


def tags(item):
    return '<div class="opportunity-tags">'+''.join(
        '<span class="opportunity-tag">'+escape(tag.title())+'</span>'
        for tag in item['profile']['tags'])+'</div>'


def score(item):
    return '<span class="opportunity-score" data-opportunity-field="score">'+interval(
        item['score'],item['score_lower'],item['score_upper'])+'</span>'


def signal(item):
    css = {'Strong Buy':'p-sbuy','Buy':'p-buy','Hold Positive':'p-hpos',
           'Hold Negative':'p-hneg','Sell':'p-sell'}.get(item['label'],'empty')
    return ('<span data-opportunity-field="label" class="pill opportunity-label '+css+'">'
            +escape(item['label'] or 'Data incomplete')+'</span>'
            '<small class="opportunity-metrics">Automatic model signal</small>')


def metrics(item):
    values = item['metrics']
    return ('<span class="opportunity-metrics" data-opportunity-field="metrics">P/E '
            +number(values.get('valuation_pe'),1)+' · FCF '+number(values.get('fcf_yield_pct'),1)
            +'%<br>Operating margin '+number(values.get('operating_margin_pct'),1)+'%</span><br>'+entry(item))


def entry(item):
    """Price at which the automatic label becomes Buy / Strong Buy, vs today's quote."""
    t = item.get('price_thresholds') or {}
    price = t.get('price')
    def level(name, value):
        if value is None or not price:
            return ''
        limit = (t.get('scan') or [None, None])[1]
        edge = ', scan limit' if limit and value >= price*limit*(1-1e-9) else ''
        return name+' ≤ '+number(value)+' ('+('%+.0f' % (100*(value/price-1)))+'% vs price'+edge+')'
    if not t or t.get('basis') is None:
        return '<span class="opportunity-metrics" data-opportunity-field="entry">Buy price unavailable</span>'
    parts = [x for x in (level('Buy', t.get('buy')), level('Strong Buy', t.get('strong_buy'))) if x]
    if not parts:
        return ('<span class="opportunity-metrics" data-opportunity-field="entry">No price reaches Buy: '
                +escape(t.get('blocker') or '')+'</span>')
    return '<span class="opportunity-metrics" data-opportunity-field="entry">'+escape(' · '.join(parts))+'</span>'


def fit(item):
    bounds = item.get('current_fit_bounds') or [None,None]
    return ('<b data-opportunity-field="fit">'+interval(item.get('current_fit'),*bounds,1)
            +'</b><small class="opportunity-metrics">/100 · '
            +escape(item.get('current_regime') or 'Unavailable')+'</small>')


def guide(regime):
    return ('<div class="opportunity-guide"><b>Discounted quality · Current regime: '
            +escape(regime or 'Unavailable')+'</b><br>Valuation & expectations 40% · Financial quality 30% '
            '· Current regime 15% · Growth 10% · Shareholder returns & dilution 5%. '
            'Strong Buy ≥8.50 · Buy ≥7.00 · Hold Positive ≥5.50 · Hold Negative ≥3.50 · Sell &lt;3.50. '
            'A range is missing-data uncertainty, not a point estimate. Labels use unrounded scores '
            'and value-trap caps. Automatic signals and analyst review are separate. '
            'Macro fit is a heuristic, not a forecast probability.</div>')


def detail(ticker,item):
    rows = []
    for regime,bounds in item['regime_fit_bounds'].items():
        rows.append(('<tr class="opportunity-fit-now">' if regime == item['current_regime'] else '<tr>')
            +'<td>'+escape(regime)+'</td><td>'+interval(item['regime_fit'].get(regime),*bounds,1)+'/100</td></tr>')
    components = ''.join('<tr><td>'+escape(c['label'])+'</td><td>'+number(c['value'])
        +'</td><td>'+number(c['weight']*100,1)+'%</td><td>'+interval(c['contribution'],
            c['lower_contribution'],c['upper_contribution'],3)+'</td></tr>' for c in item['components'])
    return ('<details class="opportunity-stock decision-stock" id="opportunity-'+escape(ticker,quote=True)
        +'" data-opportunity="'+escape(ticker,quote=True)+'"><summary><b class="tk">'+escape(ticker)+'</b> '
        +signal(item)+' · '+score(item)+'</summary>'+tags(item)+metrics(item)
        +'<p class="opportunity-metrics">P/E proxy = market capitalization / corresponding net income. '
        'Commodity valuation uses cycle averages where available. Financial period: '
        +escape(item.get('financial_period') or 'Unavailable')+' · '+escape(item.get('cash_flow_policy') or '')
        +'. Required growth (reverse DCF): <span data-opportunity-field="growth">'
        +number(item.get('implied_growth_pct'))+'%</span>.</p>'
        +'<p>'+entry(item)+' <small class="opportunity-metrics">Re-scored at each price; quality, '
        'balance sheet, growth and regime affinity held at today\'s values.</small></p>'
        +'<div class="tw"><table><thead><tr><th>Regime</th><th>Fit /100</th></tr></thead><tbody data-opportunity-field="regimes">'
        +''.join(rows)+'</tbody></table></div>'
        +'<div class="tw"><table><thead><tr><th>Component</th><th>Value /10</th><th>Weight</th><th>Contribution</th></tr></thead>'
        +'<tbody data-opportunity-field="components">'+components+'</tbody></table></div>'
        +'<p class="opportunity-caps">'+escape(' '.join(c['reason'] for c in item['caps']))+'</p>'
        +'<p class="opportunity-metrics">'+escape(', '.join(item['flags']))
        +'. Historical scores and unresolved analyst objections remain in the research below.</p></details>')


def panel(items):
    return '<div class="box" id="opportunity-analysis"><h2>Opportunity score & regime matrix</h2>'+''.join(
        detail(ticker,item) for ticker,item in items.items())+'</div>'
