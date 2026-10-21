"""Render the new diagnostics separately from legacy actions and rankings."""
from html import escape
from evidence import row_diagnostics
from assessment import LABELS


def assessment_panel(assessments):
    """Readable arithmetic coverage; bounds are not confidence intervals."""
    rows = []
    for ticker, item in sorted(assessments.items()):
        model = '&mdash;' if item['model_score'] is None else f"{item['model_score']:.2f}"
        missing = ', '.join(LABELS[key] for key in item['missing_components']) or '&mdash;'
        cells = [escape(ticker), f"{item['coverage_weight']:.0%}",
                 f"{item['score_lower']:.2f}&ndash;{item['score_upper']:.2f}", model,
                 escape(item['rating'] or 'Pending'), missing]
        fields = (None, 'coverage', 'bounds', 'model_score', 'rating', 'missing')
        rows.append('<tr data-assessment="' + escape(ticker) + '">' + ''.join(
            '<td' + (f' data-assessment-field="{field}"' if field else '') + '>' + value + '</td>'
            for field, value in zip(fields, cells)) + '</tr>')
    return ('<section class="box"><h2>Score completeness and review</h2>'
        '<p>Model scores require all eight contributions at their original weights. '
        'Coverage measures numeric availability, not source verification. '
        'Arithmetic bounds assign missing categories zero to ten; they are not forecasts or confidence intervals.</p>'
        '<p>No approved rating does not mean Sell. Existing holdings are unchanged.</p>'
        '<p>Approval is withdrawn when recorded validity or quote age expires. New research requires rebuilding the report.</p>'
        '<details><summary>Inspect score completeness</summary><div class="tw"><table><thead><tr>'
        '<th>Ticker</th><th>Category coverage</th><th>Arithmetic bounds</th><th>Model Score</th>'
        '<th>Current rating</th><th>Missing categories</th></tr></thead><tbody>'
        + ''.join(rows) + '</tbody></table></div></details></section>')


def framework_panel(rows, weights, macro, proposal=None):
    path = macro.get('path_diagnostics') or {}
    if path.get('status') == 'DESCRIPTIVE':
        persistence = str(path['persistence_observations']) + ('+' if path['persistence_censored'] else '')
        path_text = (f"{escape(path['regime'])}: {persistence} consecutive sampled sessions. "
                     f"Growth change {path['growth_change_pp']:+.1f} pp; "
                     f"inflation change {path['inflation_change_pp']:+.1f} pp "
                     f"from {escape(path['start'])} to {escape(path['end'])}. "
                     f"{path['transitions']} observed quadrant changes. "
                     'All four proxies use common dates; this can differ from the legacy current reading. '
                     'Historical market-proxy readings; descriptive, with no forecast probability.')
    else:
        path_text = 'Path diagnostics unavailable: insufficient aligned market history.'
    body = []
    for ticker, row in sorted(rows.items()):
        d = row_diagnostics(row, weights)
        quality = '&mdash;' if d['business_quality'] is None else f"{d['business_quality']:.2f}"
        vals = [escape(ticker), quality, d['score_basis'], d['price'], d['fundamentals'],
                d['ngv'], d['epv'], d['momentum'], d['valuation_contract']['status'],
                escape(str(d['growth_contract']['basis'])), d['growth_contract']['status']]
        body.append('<tr>' + ''.join('<td>' + v + '</td>' for v in vals) + '</tr>')
    book = ''
    if proposal:
        positions = ''
        for p in proposal['positions']:
            plan = p['trade_plan']
            def money(value):
                return '&mdash;' if value is None else f"{value:,.4f} {escape(str(plan.get('currency') or ''))}"
            status = {'WITHIN_ENTRY_CEILING': 'Within entry ceiling',
                      'WAIT_FOR_PULLBACK': 'Wait for pullback', 'UNAVAILABLE': 'Entry plan unavailable'}[plan['status']]
            positions += ('<tr data-entry-assessment="' + escape(p['ticker'])
                          + '" data-entry-expires="' + escape(plan['entry_valid_until'])
                          + f'" data-entry-weight="{p["weight"]}"><td>' + escape(p['ticker']) + '</td><td>' + escape(p['sector'])
                          + f"</td><td>{p['fit']:.1f}</td><td data-entry-action=\"weight\">{p['weight']:.1%}</td>"
                          + '<td>' + money(plan['quote']) + '</td><td data-entry-action="limit">' + money(plan['entry_limit'])
                          + '</td><td data-entry-action="stop">' + money(plan['initial_stop']) + '</td>'
                          + f"<td>{plan['holding_min_days']}&ndash;{plan['holding_max_days']} days after fill"
                          + f"<br>Review every {plan['review_every_days']} days</td>"
                          + '<td><span data-entry-action="status">' + status + '</span><br>Refresh by ' + escape(plan['entry_valid_until']) + '</td></tr>')
        book = ('<details><summary>Constrained portfolio proposal</summary>'
                f'<p><span data-proposal-current="filled">{len(proposal["positions"])}</span> of {proposal["target_size"]} slots filled; '
                f'unallocated capacity <span data-proposal-current="capacity">{proposal["cash_weight"]:.1%}</span>. Maximum {proposal["max_per_sector"]} names per sector. '
                'Equal planned allocations among reviewed eligible candidates in regime order. '
                'Unfilled proposal slots are unallocated capacity, not a recommendation to sell holdings.</p>'
                '<div class="tw"><table><thead><tr><th>Ticker</th><th>Sector</th><th>Fit</th>'
                '<th>Planned weight</th><th>Reference quote</th><th>Buy limit</th><th>Initial stop</th>'
                '<th>Holding / review</th><th>Entry status</th></tr></thead><tbody>' + positions + '</tbody></table></div>'
                '<p>Buy limit = the lower of the reference quote and NGV / 0.60. This is the existing '
                '60% cover rule, not a 60% discount. Prices use each listing\'s currency or quote unit (including GBp). '
                'Displayed prices are planning levels; confirm a fresh quote and the broker\'s permitted price increment.</p>'
                '<p>The initial stop is a configurable percentage below the proposed entry (default 10%). '
                'Set it from the actual fill; never lower an existing stop just because this table refreshes. '
                'The default 90&ndash;180-day horizon is a planning assumption, not a predicted profitable exit date. '
                'Review sooner if the macro regime or investment thesis changes; a stop can trigger before that horizon.</p>'
                '<p>These are new-entry scenarios, not instructions to replace stops on existing holdings. '
                'No orders are placed. Stops do not guarantee execution at the displayed price. '
                '<a href="https://www.investor.gov/introduction-investing/investing-basics/glossary/stop-order" '
                'target="_blank" rel="noopener">How stop orders work</a>.</p></details>')
    return ('<section class="box"><h2>Evidence and path diagnostics</h2><p>' + path_text + '</p>'
            '<p>Legacy Score includes valuation. Regime Fit includes a cover-based duration proxy. '
            'Business Quality uses growth, profitability, cash conversion, balance sheet and dilution; '
            'it is a separate heuristic and does not change existing actions or rankings.</p>'
            '<details><summary>Inspect data availability and valuation assumptions</summary>'
            '<p>UNVERIFIED means the cash-flow basis, dated source information, or a matching '
            'cash-flow/discount-rate contract is unestablished. '
            'MISMATCH means the declared cash-flow and discount-rate bases disagree. '
            'AVAILABLE describes presence, not accuracy or freshness. Missing subscores retain '
            'the legacy neutral balance/payout assumptions; Business Quality remains unavailable. '
            'Cushion compares only explicitly declared cash-flow growth. Revenue, earnings, '
            'bookings and production proxies remain descriptive and cannot impose a cushion penalty.</p>'
            '<div class="tw"><table><thead><tr><th>Ticker</th><th>Business Quality</th>'
            '<th>Legacy Score basis</th><th>Price</th><th>Fundamentals</th><th>NGV</th>'
            '<th>EPV</th><th>Momentum</th><th>Valuation basis</th><th>Growth basis</th>'
            '<th>Growth comparison</th></tr></thead><tbody>'
            + ''.join(body) + '</tbody></table></div></details>' + book + '</section>')
