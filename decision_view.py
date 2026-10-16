"""Explain existing financial decisions beside separate timing observations."""
from html import escape

from evidence import number
import timing as TIMING

CSS = """
#decision-observations .decision-guide{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:14px 0}
#decision-observations .decision-guide>div{background:#10121a;border:1px solid var(--line);border-radius:8px;padding:12px}
#decision-observations .decision-guide strong{display:block;color:var(--cyan);font-size:15px}
#decision-observations .decision-guide small{display:block;color:var(--mu);margin-top:4px}
#decision-observations .decision-stock{border-top:1px solid var(--line);padding:11px 0}
#decision-observations .decision-stock>summary{line-height:1.8}
#decision-observations .decision-stock>summary b{display:inline-block;min-width:64px}
#decision-observations .decision-meta{color:var(--mu);font-size:12px;overflow-wrap:anywhere}
#decision-observations .decision-summary{color:#c8ccd8;font-size:12px;margin-left:8px;display:inline-block}
#decision-observations h3{font-size:14px;color:var(--cyan);margin:18px 0 8px}
#decision-observations .decision-facts{display:flex;flex-wrap:wrap;gap:8px 24px;margin:12px 0}
#decision-observations .decision-facts>span{font-size:12px}
#decision-observations .decision-flag{color:var(--amber);font-family:var(--mono);font-size:11px}
#decision-observations .decision-current{background:#14202a}
#decision-observations .decision-alerts{border:1px solid var(--amber);border-radius:8px;padding:12px;margin:14px 0}
#decision-observations .decision-alert{display:inline-block;font-family:var(--mono);font-size:12px;margin:8px 18px 0 0}
#decision-observations .decision-buy{color:#86efac}
#decision-observations .decision-sell{color:#fca5a5}
#decision-observations .tw{margin-bottom:10px}
@media(max-width:600px){#decision-observations .decision-guide{grid-template-columns:1fr}
#decision-observations .decision-summary{display:block;margin-left:17px}
#decision-observations .decision-guide>div{padding:10px}}
"""


def text(value):
    return escape(str(value)) if value is not None else '&mdash;'


def numeric(value, spec='.4f', scale=1):
    parsed = number(value)
    return '&mdash;' if parsed is None else format(parsed * scale, spec)


def table(headers, rows):
    return ('<div class="tw"><table><thead><tr>'
            + ''.join('<th>' + text(h) + '</th>' for h in headers)
            + '</tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div>')


def score_table(explanation):
    status = explanation['status']
    version = '<p class="decision-meta">Score explanation contract: ' + text(explanation.get('schema')) + '</p>'
    if status != 'DECOMPOSED':
        return (version + '<p>' + ('Published total only: ' + numeric(explanation['total'], '.2f')
                        if status == 'PUBLISHED_TOTAL' else 'Score unavailable.')
                + '. Category breakdown unavailable; no category scores are inferred.</p>')
    rows = []
    for component in explanation['components']:
        rows.append('<tr><td>' + text(component['label']) + '<br><small class="decision-meta">'
                    + text(component['source']) + '</small></td><td>' + numeric(component['value'], '.2f')
                    + '</td><td>' + numeric(component['nominal_weight'], '.1%', 1)
                    + '</td><td>' + numeric(component['effective_weight'], '.4%')
                    + '</td><td>' + numeric(component['contribution']) + '</td></tr>')
    note = ('Missing Priced-In Expectations: the existing score divides the remaining weighted '
            'sum by 0.85. Effective weights below expose that renormalisation.'
            if explanation['denominator'] != 1 else 'Effective weights equal the existing nominal weights.')
    return (version + '<p class="decision-meta">Category assessments are stored heuristics, not independently '
            'verified financial measurements. ' + note + '</p>'
            + table(['Category assessment (0–10)', 'Value', 'Nominal weight', 'Effective weight', 'Contribution'], rows)
            + '<p>Contribution sum: <b>' + numeric(explanation['sum_contributions'])
            + '</b> · Existing score: <b>' + numeric(explanation['total'], '.4f')
            + '</b> · Reconciles: ' + ('yes' if explanation['reconciles'] else 'NO — inspect model') + '</p>')


def regime_table(components, regime):
    if not components:
        return '<p>Regime components unavailable: no usable Cover.</p>'
    rows = []
    for name, component in components.items():
        cells = [text(name)] + [numeric(component[key])
                               for key in ('base', 'sector', 'duration', 'balance', 'payout', 'raw')]
        cells.append(numeric(component['total'], '.1f'))
        rows.append(('<tr class="decision-current">' if name == regime else '<tr>')
                    + ''.join('<td>' + cell + '</td>' for cell in cells) + '</tr>')
    first = next(iter(components.values()))
    return ('<p class="decision-meta">Current regime: ' + text(regime or 'unavailable')
            + '. Each raw fit is the sum of the five displayed contributions, clamped to 0–100 '
            'and rounded to one decimal. The existing clamped duration input is '
            + numeric(first['duration_input'], '.2f') + ' Cover percentage points relative to 60%. '
            'Fit is a heuristic, not a forecast probability. Portfolio weights do not enter it.</p>'
            + table(['Regime', 'Base', 'Sector', 'Duration', 'Balance sheet', 'Payout', 'Raw sum', 'Reported fit'], rows))


def _signal_record(observed):
    signal = observed.get('signal')
    return (signal if observed.get('schema') == TIMING.VERSION and isinstance(signal, dict)
            and signal.get('schema') == TIMING.SIGNAL_VERSION else None)


def _current_signal(observed):
    signal = _signal_record(observed)
    return (signal if signal and observed.get('status') == 'AVAILABLE'
            and signal.get('status') == 'AVAILABLE' and signal.get('date')
            and signal.get('event') in ('BUY', 'SELL', 'NO_NEW_SIGNAL') else None)


def signal_labels(observed):
    """Use archived signal contracts; never infer events from metric snapshots."""
    signal = _signal_record(observed)
    current = _current_signal(observed)
    if current:
        event = current['event']
        label = ('EXPERIMENTAL ' + event) if event in ('BUY', 'SELL') else event
        current_label = 'Current signal: ' + label + ' · ' + str(current['date'])
    else:
        if signal is None:
            reason = 'No signal contract archived; no signal is inferred.'
        elif observed.get('status') != 'AVAILABLE':
            reason = 'Current signal suppressed because timing is ' + str(observed.get('status')) + '.'
        else:
            reason = signal.get('reason') or 'No signal contract archived; no signal is inferred.'
        current_label = 'Current signal: UNAVAILABLE · ' + reason
    prefix = 'Latest historical event (last 20 completed sessions): '
    if (signal is None or observed.get('status') == 'UNAVAILABLE'
            or (number(observed.get('bars')) or 0) < TIMING.SIGNAL_MIN_BARS):
        return current_label, prefix + 'UNAVAILABLE.'
    event = signal.get('latest_event')
    if not isinstance(event, dict):
        return current_label, prefix + 'none.'
    age = event.get('age_sessions')
    if (event.get('event') not in ('BUY', 'SELL') or not event.get('date')
            or type(age) is not int or not 0 <= age < TIMING.SIGNAL_LOOKBACK_SESSIONS):
        return current_label, prefix + 'UNAVAILABLE.'
    age_label = str(age) + (' completed session ago' if age == 1 else ' completed sessions ago')
    return (current_label, prefix + 'EXPERIMENTAL ' + event['event'] + ' · '
            + str(event['date']) + ' · ' + age_label)


def timing_detail(observed, currency):
    status = observed.get('status', 'UNAVAILABLE')
    reason = observed.get('reason') or ''
    current_label, historical_label = signal_labels(observed)
    facts = [('Adjusted close', numeric(observed.get('close')) + ' ' + text(currency)),
             ('SMA 200', numeric(observed.get('sma200'))),
             ('Distance from SMA 200', numeric(observed.get('distance_sma_pct'), '+.2f') + '%'),
             ('EMA 21 reference', numeric(observed.get('ema21'))),
             ('ATR 14', numeric(observed.get('atr14'))),
             ('Extension', numeric(observed.get('extension_atr'), '+.2f') + ' ATR')]
    return ('<p><span class="decision-flag">Experimental · ' + text(status) + '</span> '
            + text(reason) + '</p><p>' + text(current_label) + '</p><p class="decision-meta">'
            + text(historical_label) + '</p><div class="decision-facts">'
            + ''.join('<span>' + text(label) + ': <b>' + value + '</b></span>' for label, value in facts)
            + '</div><p class="decision-meta">Last eligible bar: ' + text(observed.get('last_bar'))
            + ' · Calculated: ' + text(observed.get('calculated_at'))
            + ' · Source timezone: ' + text(observed.get('source_timezone'))
            + ' · Eligible bars: ' + text(observed.get('bars'))
            + '<br>Source: ' + text(observed.get('source') or 'No history captured')
            + ' · Timing contract: ' + text(observed.get('schema'))
            + ' · Signal rule contract: ' + text((observed.get('signal') or {}).get('schema') or 'unavailable')
            + ' · Price basis: ' + text(observed.get('price_basis') or 'unavailable')
            + '<br>Input window: ' + text(observed.get('history_start')) + ' → ' + text(observed.get('last_bar'))
            + '<br>Input SHA-256: ' + text(observed.get('input_sha256')) + '</p>')


def panel(rows, explanations, regime):
    """All strings are escaped; input rows and explanations are never mutated."""
    stocks, alerts = [], []
    available = sum((d.get('timing') or {}).get('status') == 'AVAILABLE' for d in rows.values())
    ranked = sorted(rows, key=lambda t: (-(explanations[t]['score']['total']
                                          if explanations[t]['score']['total'] is not None else -1), t))
    for ticker in ranked:
        row, explained = rows[ticker], explanations[ticker]
        observed = row.get('timing') or {'status': 'UNAVAILABLE', 'reason': 'No timing history captured.'}
        state = {'ABOVE_SMA200': 'above SMA 200', 'BELOW_SMA200': 'below SMA 200',
                 'AT_SMA200': 'at SMA 200'}.get(observed.get('trend'), 'trend unavailable')
        current_label, historical_label = signal_labels(observed)
        current = _current_signal(observed)
        if current and current['event'] in ('BUY', 'SELL'):
            alerts.append('<span class="decision-alert decision-' + current['event'].lower() + '">'
                          + text('EXPERIMENTAL ' + current['event'] + ' · ' + ticker + ' · '
                                 + str(current['date'])) + '</span>')
        fit = explained['regimes'].get(regime, {}).get('total')
        facts = [('NGV', numeric(explained['ngv'])),
                 ('Cover', numeric(explained['cover'], '.1%', 1)),
                 ('Implied cash-flow growth', numeric(explained['implied_growth'], '.2%', 1)),
                 ('Comparable cash-flow cushion (pp)', numeric(explained['cushion'], '+.2f'))]
        stocks.append('<details class="decision-stock"><summary><b>' + text(ticker)
                      + '</b><span class="decision-summary">Score '
                      + numeric(explained['score']['total'], '.2f') + ' · Current fit '
                      + numeric(fit, '.1f') + ' · ' + text(state) + ' · '
                      + text(observed['status']) + '<br>' + text(current_label) + '<br>'
                      + text(historical_label) + '</span></summary>'
                      + '<h3>Existing fundamental score</h3>' + score_table(explained['score'])
                      + '<div class="decision-facts">'
                      + ''.join('<span>' + text(label) + ': <b>' + value + '</b></span>' for label, value in facts)
                      + '</div><h3>Existing regime fit contributions</h3>'
                      + regime_table(explained['regimes'], regime)
                      + '<h3>Entry observation — separate from score and fit</h3>'
                      + timing_detail(observed, row.get('cur')) + '</details>')
    return ('<section class="box" id="decision-observations">'
            '<h2>Score explanations and entry observations</h2>'
            '<p><span class="decision-flag">Experimental timing · observation only</span><br>'
            'No automatic trades, entry gates, technical score points or allocation changes. '
            'Existing scores, regime fit and portfolio rules retain their own meanings.</p>'
            '<div class="decision-alerts"><strong>Current experimental BUY/SELL alerts</strong><p>'
            + (''.join(alerts) if alerts else 'No current BUY/SELL alerts.')
            + '</p><small class="decision-meta">Only latest completed-bar events appear here. '
            'Historical events are listed separately.</small></div>'
            '<div class="decision-guide"><div><strong>SMA 200 · slow trend</strong>'
            '<small>Describes the adjusted close relative to its 200-session average.</small></div>'
            '<div><strong>Extension · ATR units</strong>'
            '<small>(Adjusted close − EMA 21) / ATR 14. Signed distance, with no buy/sell threshold.</small></div>'
            '<div><strong>' + str(available) + ' / ' + str(len(rows)) + ' observations available</strong>'
            '<small>Missing, partial and stale observations remain explicit.</small></div></div>'
            '<details><summary>Inspect ' + str(len(rows)) + ' stock explanations and observations</summary>'
            + ''.join(stocks) + '</details>'
            '<p class="decision-meta">Only dates strictly before the current exchange-local date are used, '
            'even after today’s close. This conservative policy can lag one completed session. '
            'At least 200 valid bars are required for metrics. '
            'Signal comparisons need at least 201 valid completed bars. '
            'BUY: previous close ≤ previous EMA 21, latest close &gt; EMA 21 and SMA 200. '
            'SELL: previous close ≥ previous SMA 200, latest close &lt; SMA 200. '
            'Events are labels for review; existing verdicts and actions are unchanged. '
            'EMA 21 uses an initial 21-close mean; ATR 14 uses '
            'a 14-true-range mean followed by Wilder smoothing (first TR = High − Low). '
            'More than 7 calendar days of lag is flagged STALE. The adjusted historical close can differ '
            'from the current quote. Values and an input-window hash are archived as observed; raw OHLC '
            'is not archived and provider adjustments can change on refetch. Performance advantage '
            'has not been established.</p></section>')
