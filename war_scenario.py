"""War scenarios for the universe: information next to the model label, never a label.

Two questions, each answered with the same model that sets the label:

1. Commodity producers: what if war-level prices persist? The label values a
   producer on its multi-year cash-flow mean (AGENTS.md: commodity peak
   multiples do not substitute for multi-year inputs). The war case values the
   latest reported twelve months instead, earned at the current prices.
2. Everyone: what if the war turns the macro regime into STAGFLATION? The
   macro fit is scored on that single regime; cash flows stay as they are.

Both are scenarios. They never change a score, a label or a portfolio.
"""
import json
from datetime import datetime, timezone
from html import escape
from pathlib import Path

SCHEMA = 'war-scenario-v1'
STRESS_REGIME = 'STAGFLATION'
PAGE = 'war-scenarios.html'


def _compact(result):
    thresholds = result.get('price_thresholds') or {}
    return dict(score=result.get('score'), label=result.get('label'),
                withdrawn=bool(result.get('withdrawn')), buy=thresholds.get('buy'),
                strong_buy=thresholds.get('strong_buy'), blocker=thresholds.get('blocker'),
                implied_growth_pct=result.get('implied_growth_pct'))


def spot_row(row):
    """The row as the model would see it if the reported TTM were sustainable."""
    spot = row.get('spot_analysis')
    if not row.get('midcycle') or not isinstance(spot, dict):
        return None
    out = {k: v for k, v in row.items() if k not in ('midcycle', 'spot_analysis')}
    out.update(spot.get('overlay') or {})
    out['dynamic_analysis'] = spot
    return out


def case(row, assess, *, regime, as_of=None, weights=None):
    """War cases of one row; `assess` is engine.opportunity."""
    out = dict(schema=SCHEMA, stress_regime=STRESS_REGIME,
               stagflation=_compact(assess(row, regime=STRESS_REGIME, as_of=as_of)))
    spot = spot_row(row)
    if spot is not None:
        inputs = lambda r: ((r.get('dynamic_analysis') or {}).get('inputs') or {})
        out['spot'] = dict(_compact(assess(spot, regime=regime, as_of=as_of, weights=weights)),
                           valuation_fcf=inputs(spot).get('valuation_fcf'),
                           cycle_fcf=inputs(row).get('valuation_fcf'),
                           valuation_net_income=inputs(spot).get('valuation_net_income'),
                           cycle_net_income=inputs(row).get('valuation_net_income'),
                           financial_period=(spot.get('dynamic_analysis') or {}).get('financial_period'),
                           cycle_periods=((row.get('dynamic_analysis') or {}).get('parameters') or {})
                           .get('cash_cycle_periods'))
    return out


CSS = """
:root{color-scheme:dark;--bg:#0d0f14;--panel:#141821;--line:#2a3040;--text:#edf0f7;--muted:#a0aabe;
--accent:#c1d98b;--up:#66e39c;--down:#f06a6a}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);
font:15px/1.55 Inter,system-ui,-apple-system,sans-serif}a{color:var(--accent)}
main{max-width:1180px;margin:auto;padding:24px 16px 64px}nav{display:flex;gap:18px;flex-wrap:wrap;
padding-bottom:16px;border-bottom:1px solid var(--line)}nav strong{margin-right:auto}
h1{font-size:clamp(28px,5vw,44px);letter-spacing:-1px;margin:24px 0 8px}h2{margin:32px 0 8px}
.lead{color:var(--muted);max-width:820px}.tiles{display:flex;flex-wrap:wrap;gap:12px;margin:18px 0}
.tile{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px 16px;min-width:170px}
.tile b{display:block;font-size:24px;font-variant-numeric:tabular-nums}.tile span{color:var(--muted);font-size:13px}
.tw{overflow-x:auto;border:1px solid var(--line);border-radius:10px}table{border-collapse:collapse;width:100%;
font-variant-numeric:tabular-nums}th,td{padding:7px 10px;border-bottom:1px solid var(--line);text-align:right;
white-space:nowrap}th:first-child,td:first-child,th.l,td.l{text-align:left}th{background:#10141c;color:var(--muted);
font-weight:600;font-size:13px}tr:last-child td{border-bottom:0}.up{color:var(--up)}.down{color:var(--down)}
.muted{color:var(--muted)}.note{background:var(--panel);border:1px solid var(--line);border-radius:10px;
padding:12px 16px;color:var(--muted);margin:16px 0}.lbl{font-weight:650}
.lbl-Strong-Buy,.lbl-Buy{color:var(--up)}.lbl-Sell,.lbl-Hold-Negative{color:var(--down)}
tr.crash td{background:#3d1418}tr.risk td{background:#2a1518}tr.near td{background:#112619}
.key{padding:1px 8px;border-radius:6px;color:var(--text)}.key.crash{background:#5a1c22}.key.near{background:#1c4a2c}
"""


def shell(title, body):
    return ('<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>InvestorAce · {escape(title)}</title><style>{CSS}</style></head><body><main>'
            '<nav><strong>InvestorAce</strong><a href="index.html">Scoreboard</a>'
            '<a href="paper-test.html">Paper test</a><a href="trade.html">Active trading</a><a href="backtest.html">Backtest</a><a href="war-scenarios.html">War scenarios</a>'
            '<a href="crash-monitor.html">Crash monitor</a>'
            '<a href="scanner.html">Stock scanner</a></nav>' + body + '</main></body></html>')


def money(value, digits=2):
    return '—' if value is None else format(value, f',.{digits}f')


def label(value, score=None):
    if not value:
        return '<span class="muted">—</span>'
    text = escape(value) + ('' if score is None else ' ' + format(score, '.2f'))
    return f'<span class="lbl lbl-{escape(value.replace(" ", "-"))}">{text}</span>'


def _bn(value):
    return '—' if value is None else format(value / 1e9, ',.1f') + 'bn'


def _oil_note(oil):
    if not oil:
        return 'WTI history was not available in this build.'
    parts = [f"WTI {money(oil.get('last'))} USD on {escape(str(oil.get('date')))}"]
    if oil.get('avg_63') is not None:
        parts.append(f"3-month average {money(oil['avg_63'])}")
    if oil.get('avg_252') is not None:
        parts.append(f"12-month average {money(oil['avg_252'])}")
    return ' · '.join(parts) + '.'


def render(record, *, now=None):
    now = now or datetime.now(timezone.utc)
    evidence = record.get('_evidence') or {}
    macro = evidence.get('macro') or {}
    oil = (macro.get('pulse') or {}).get('oil')
    inputs = evidence.get('inputs') or {}
    tickers = sorted(t for t in record if not t.startswith('_') and isinstance(record[t], dict))
    regime = None
    producers, universe, unvalued = [], [], []
    for t in tickers:
        out = record[t]
        opp = out.get('opportunity') or {}
        regime = regime or opp.get('current_regime')
        war = out.get('war') or {}
        thresholds = opp.get('price_thresholds') or {}
        price = opp.get('price', out.get('price'))
        currency = (inputs.get(t) or {}).get('cur') or ''
        if war.get('spot') and (war['spot'].get('label') or opp.get('label')):
            producers.append((t, price, currency, opp, thresholds, war['spot']))
        elif war.get('spot'):
            unvalued.append(t)
        if war.get('stagflation'):
            universe.append((t, price, currency, opp, thresholds, war['stagflation']))
    captured = escape(str(evidence.get('captured_at') or now.isoformat())[:16].replace('T', ' '))
    body = [f'<h1>War scenarios</h1><p class="lead">What the InvestorAce model says if the war keeps '
            f'oil and metals at today\'s prices, and if it turns the economy into stagflation. These are '
            f'scenarios next to the model label, not labels: the scoreboard keeps valuing producers on '
            f'their multi-year cash-flow average. Build {captured} UTC, current regime '
            f'<b>{escape(regime or "unknown")}</b>.</p>',
            f'<div class="note">{_oil_note(oil)} The war case uses each producer\'s latest reported twelve '
            'months; compare its period with the oil averages above. If the twelve months were earned below '
            'today\'s prices, the war case is conservative; if prices fall back, the cycle case applies.</div>',
            '<h2>1 · Commodity producers: if war-level prices persist</h2>',
            '<p class="lead">"Buy up to" is the highest price at which the model would label the stock Buy, '
            'all else equal. Model = multi-year cash-flow mean (the label). War case = latest twelve months '
            'sustained.</p>']
    rows = []
    for t, price, cur, opp, thr, spot in sorted(producers, key=lambda x: -(x[5].get('score') or 0)):
        rows.append(f'<tr><td><b>{escape(t)}</b></td><td>{money(price)} {escape(cur)}</td>'
                    f'<td class="l">{label(opp.get("label"), opp.get("score"))}</td><td>{money(thr.get("buy"))}</td>'
                    f'<td class="l">{label(spot.get("label"), spot.get("score"))}</td><td><b>{money(spot.get("buy"))}</b></td>'
                    f'<td>{money(spot.get("strong_buy"))}</td><td>{_bn(spot.get("cycle_fcf"))}</td>'
                    f'<td>{_bn(spot.get("valuation_fcf"))}</td><td>{escape(str(spot.get("financial_period") or "—"))}</td></tr>')
    body.append('<div class="tw"><table><thead><tr><th>Ticker</th><th>Price</th><th class="l">Model label</th>'
                '<th>Model: Buy up to</th><th class="l">War case</th><th>War case: Buy up to</th>'
                '<th>War: Strong Buy up to</th><th>FCF cycle mean</th><th>FCF last 12 m</th><th>12 m to</th>'
                '</tr></thead><tbody>' + (''.join(rows) or
                '<tr><td colspan="10" class="l muted">No producer war case in this build.</td></tr>')
                + '</tbody></table></div>')
    if unvalued:
        body.append('<p class="muted">No valuation in this build (inputs blocked or partial, e.g. after a '
                    'spin-off): ' + escape(', '.join(unvalued)) + '.</p>')
    body.append(f'<h2>2 · Whole universe: if the war turns into {STRESS_REGIME.lower()}</h2>'
                f'<p class="lead">Same cash flows, macro fit scored on {STRESS_REGIME} only (oil shock with '
                'weak growth). Shows which labels survive a stagflation shock. Sorted by the stress score.</p>')
    rows = []
    for t, price, cur, opp, thr, st in sorted(universe, key=lambda x: -(x[5].get('score') or -1)):
        delta = (st.get('score') - opp.get('score')) if None not in (st.get('score'), opp.get('score')) else None
        css = '' if delta is None or abs(delta) < .005 else ('up' if delta > 0 else 'down')
        rows.append(f'<tr><td><b>{escape(t)}</b></td><td>{money(price)} {escape(cur)}</td>'
                    f'<td class="l">{label(opp.get("label"), opp.get("score"))}</td><td>{money(thr.get("buy"))}</td>'
                    f'<td class="l">{label(st.get("label"), st.get("score"))}</td><td>{money(st.get("buy"))}</td>'
                    f'<td class="{css}">{"—" if delta is None else format(delta, "+.2f")}</td></tr>')
    body.append('<div class="tw"><table><thead><tr><th>Ticker</th><th>Price</th><th class="l">Label now</th>'
                f'<th>Buy up to now</th><th class="l">Label in {STRESS_REGIME.lower()}</th><th>Buy up to</th>'
                '<th>Score change</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div>')
    body.append('<div class="note">Both scenarios hold quality, balance sheet, growth and shareholder returns at '
                'today\'s values. A dash means no price between 30% and 300% of today reaches that label. '
                'Research, not an approved purchase recommendation.</div>')
    return shell('War scenarios', ''.join(body))


def site_pages(root, build, *, now=None):
    record = build['record']
    if not any(isinstance(v, dict) and v.get('war') for k, v in record.items() if not k.startswith('_')):
        return []
    return [(Path(PAGE), render(record, now=now))]


if __name__ == '__main__':
    from evidence import current_build
    print(json.dumps([str(p) for p, _ in site_pages('.', current_build('history'))]))
