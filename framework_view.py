"""Render the new diagnostics separately from legacy actions and rankings."""
from html import escape
from evidence import row_diagnostics


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
                d['ngv'], d['epv'], d['momentum'], d['valuation_contract']['status']]
        body.append('<tr>' + ''.join('<td>' + v + '</td>' for v in vals) + '</tr>')
    book = ''
    if proposal:
        positions = ''.join('<tr><td>' + escape(p['ticker']) + '</td><td>' + escape(p['sector'])
                            + f"</td><td>{p['fit']:.1f}</td><td>{p['weight']:.1%}</td></tr>"
                            for p in proposal['positions'])
        book = ('<details><summary>Constrained portfolio proposal</summary>'
                f"<p>{len(proposal['positions'])} of {proposal['target_size']} slots filled; "
                f"cash {proposal['cash_weight']:.1%}. Maximum {proposal['max_per_sector']} names per sector. "
                'Equal slots, selected from the raw regime ranking. No orders are placed.</p>'
                '<div class="tw"><table><thead><tr><th>Ticker</th><th>Sector</th><th>Fit</th>'
                '<th>Proposed weight</th></tr></thead><tbody>' + positions + '</tbody></table></div></details>')
    return ('<section class="box"><h2>Evidence and path diagnostics</h2><p>' + path_text + '</p>'
            '<p>Legacy Score includes valuation. Regime Fit includes a cover-based duration proxy. '
            'Business Quality uses growth, profitability, cash conversion, balance sheet and dilution; '
            'it is a separate heuristic and does not change existing actions or rankings.</p>'
            '<details><summary>Inspect data availability and valuation assumptions</summary>'
            '<p>UNVERIFIED means the cash-flow basis or dated source information is missing. '
            'MISMATCH means the declared cash-flow and discount-rate bases disagree. '
            'AVAILABLE describes presence, not accuracy or freshness. Missing subscores retain '
            'the legacy neutral balance/payout assumptions; Business Quality remains unavailable.</p>'
            '<div class="tw"><table><thead><tr><th>Ticker</th><th>Business Quality</th>'
            '<th>Legacy Score basis</th><th>Price</th><th>Fundamentals</th><th>NGV</th>'
            '<th>EPV</th><th>Momentum</th><th>Valuation basis</th></tr></thead><tbody>'
            + ''.join(body) + '</tbody></table></div></details>' + book + '</section>')
