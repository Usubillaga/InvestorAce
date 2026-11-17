"""Stress scenarios: price shocks applied to the paper accounts. Information only.

Two scenarios from The Economist's "The World Ahead 2027" themes (asked for on
17 Nov 2026). Each one is a fixed, written-down set of price moves, not a
forecast:

* AI_BACKLASH: spending on AI is cut. Shocks by group: chips and AI cloud fall
  most, software and the big platforms less, the rest of technology and the
  power producers tied to data centres a little. Size: [Wahrscheinlich] about
  two thirds of the 2022 fall of the Philadelphia semiconductor index (-46% from
  December 2021 to October 2022); an assumption, not a measurement.
* FRANCE_2027: a far-right win in the 2027 French presidential election.
  France-listed shares -15%, other euro-area shares -10%, EUR/USD -5% (so a
  USD asset is worth 1/0.95 more in euros). Other currencies are left unchanged
  because no rate move is assumed for them.

The shocked price is set against the model's own Buy-up-to price, so the page
shows which names the model would rate Buy at the shocked price. No score,
label, rule or order changes.
"""
import json
from datetime import date, datetime, timezone
from html import escape
from pathlib import Path

PAGE = 'stress-scenarios.html'
SCHEMA = 'stress-scenarios-v1'

AI_GROUPS = [
    ('AI cloud', -0.40, {'CRWV', 'NBIS'}),
    ('Chips', -0.30, {'NVDA', 'AVGO', 'AMD', 'INTC', 'MRVL', 'MU', 'AMAT', 'ASML', 'SMCI'}),
    ('Software and ad tech', -0.20, {'ADBE', 'CRM', 'NOW', 'WIX', 'ADSK', 'MNDY', 'TEAM', 'PTC', 'INTU', 'APP',
                                     'TTD'}),
    ('Big platforms', -0.20, {'MSFT', 'GOOGL', 'META'}),
    ('Data-centre power', -0.15, {'VST', 'CEG', 'NRG', 'OKLO'}),
]
OTHER_TECH = ('Other technology', -0.10)

SCENARIOS = {
    'AI_BACKLASH': dict(title='AI backlash', note=(
        'AI spending is cut: AI cloud -40%, chips -30%, software, ad tech and the big platforms -20%, '
        'data-centre power producers -15%, the rest of technology -10%. Everything else and all currencies '
        'unchanged.')),
    'FRANCE_2027': dict(title='France 2027', note=(
        'A far-right win in the 2027 French presidential election: France-listed shares -15%, other euro-area '
        'shares -10%, EUR/USD -5% (USD assets gain about 5.3% in euros). US shares unchanged in dollars; GBP '
        'and CAD unchanged.')),
}


def shock(scenario, ticker, row):
    """(group, local price move, currency factor into EUR) for one universe row."""
    cur = row.get('cur') or 'USD'
    if scenario == 'AI_BACKLASH':
        for name, move, members in AI_GROUPS:
            if ticker in members:
                return name, move, 1.
        if row.get('sector') == 'Technology':
            return OTHER_TECH[0], OTHER_TECH[1], 1.
        return None, 0., 1.
    if scenario == 'FRANCE_2027':
        symbol = str(row.get('yf') or ticker)
        if cur == 'EUR' and symbol.endswith('.PA'):
            return 'France-listed', -0.15, 1.
        if cur == 'EUR':
            return 'Other euro area', -0.10, 1.
        if cur == 'USD':
            return 'USD asset', 0., 1 / 0.95
        return None, 0., 1.
    raise ValueError(f'unknown scenario {scenario}')


def _universe(record):
    inputs = (record.get('_evidence') or {}).get('inputs') or {}
    by_symbol = {}
    for ticker, row in inputs.items():
        if isinstance(row, dict):
            by_symbol[ticker] = (ticker, row)
            by_symbol[str(row.get('yf') or ticker)] = (ticker, row)
    return inputs, by_symbol


def account_impact(scenario, positions, by_symbol):
    """Positions: [(symbol, value in EUR)]. Returns before, after, change and the per-position moves."""
    before = after = 0.
    moves = []
    for symbol, value in positions:
        ticker, row = by_symbol.get(symbol, (symbol, {}))
        group, move, factor = shock(scenario, ticker, row)
        new = value * (1 + move) * factor
        before, after = before + value, after + new
        if new != value:
            moves.append(dict(ticker=ticker, group=group, value=value, change=new - value))
    return dict(before=before, after=after, change=after - before,
                change_pct=100 * (after / before - 1) if before else None,
                moves=sorted(moves, key=lambda m: m['change']))


def stock_rows(scenario, record):
    """Every universe member the scenario moves, with the shocked price against the model's Buy-up-to."""
    inputs, _ = _universe(record)
    out = []
    for ticker, row in sorted(inputs.items()):
        if not isinstance(row, dict):
            continue
        group, move, _ = shock(scenario, ticker, row)
        if not move:
            continue
        opp = (record.get(ticker) or {}).get('opportunity') or {}
        price = opp.get('price') or (record.get(ticker) or {}).get('price')
        th = opp.get('price_thresholds') or {}
        shocked = price * (1 + move) if price else None
        buy, strong = th.get('buy'), th.get('strong_buy')
        state = None
        if shocked is not None and strong is not None and shocked <= strong:
            state = 'Strong Buy'
        elif shocked is not None and buy is not None and shocked <= buy:
            state = 'Buy'
        out.append(dict(ticker=ticker, group=group, move=move, label=opp.get('label'), score=opp.get('score'),
                        price=price, shocked=shocked, buy=buy, at_shocked_price=state, cur=row.get('cur'),
                        blocker=th.get('blocker')))
    return out


def paper_positions(root, record, today):
    """Current EUR values of every paper account, from the committed files and closes."""
    import active_trading as at
    import paper_portfolio as pp
    root = Path(root)
    snapshots = []
    for path in sorted((root / 'history' / 'runs').glob('*.json')):
        try:
            stamp = datetime.strptime(path.name[:8], '%Y%m%d').date()
        except ValueError:
            continue
        if (today - stamp).days <= 60:
            snapshots.append(json.loads(path.read_text(encoding='utf-8')))
    series = pp.merge_series(snapshots + [record])
    accounts = []
    for doc in pp.load(root / 'paper_trades'):
        result = pp.evaluate(doc, series, today)
        rows = [h for h in result['holdings'] + (result.get('discretionary') or []) if h.get('value_now')]
        if rows:
            accounts.append((doc.get('short_name') or doc['name'],
                             [(h.get('yahoo') or h['ticker'], h['value_now']) for h in rows]))
    path = root / 'paper_trades' / 'active-account.json'
    if path.exists():
        state = at.replay(at.load(path), series, today.isoformat())
        rows = [(p['yahoo'], p['value']) for p in state['positions'] if p.get('value')]
        if rows:
            accounts.append(('Active trading', rows))
    return accounts


def build(record, accounts):
    _, by_symbol = _universe(record)
    return dict(schema=SCHEMA, scenarios={
        key: dict(spec, accounts=[dict(name=name, **account_impact(key, positions, by_symbol))
                                  for name, positions in accounts],
                  stocks=stock_rows(key, record))
        for key, spec in SCENARIOS.items()})


def _eur(value):
    return '—' if value is None else ('−' if value < 0 else '+') + '€' + format(abs(value), ',.0f')


def _pct(value):
    return '—' if value is None else ('−' if value < 0 else '+') + format(abs(value), '.1f') + '%'


def render(result, *, captured=None):
    from war_scenario import label, money, shell
    parts = ['<h1>Stress scenarios</h1><p class="lead">Fixed price shocks applied to the paper accounts and the '
             'universe. They are assumptions, not forecasts, and they never change a score, a label, a rule or an '
             'order.' + (f' Prices from the build of {escape(captured[:10])}.' if captured else '') + '</p>']
    for key, sc in result['scenarios'].items():
        parts.append(f'<h2>{escape(sc["title"])}</h2><div class="note">{escape(sc["note"])}</div>')
        rows = ''.join(
            f'<tr><td>{escape(a["name"])}</td><td>€{money(a["before"], 0)}</td><td>€{money(a["after"], 0)}</td>'
            f'<td class="{"down" if a["change"] < 0 else "up"}">{_eur(a["change"])}</td>'
            f'<td class="{"down" if (a["change_pct"] or 0) < 0 else "up"}">{_pct(a["change_pct"])}</td>'
            f'<td class="l">{escape(", ".join(m["ticker"] + " " + _eur(m["change"]) for m in a["moves"][:4]) or "—")}'
            '</td></tr>' for a in sc['accounts'])
        parts.append('<div class="tw"><table><thead><tr><th>Account</th><th>Positions now</th><th>After shock</th>'
                     '<th>Change</th><th>%</th><th class="l">Largest moves</th></tr></thead><tbody>'
                     + (rows or '<tr><td colspan="6" class="muted">No open paper positions.</td></tr>')
                     + '</tbody></table></div>')
        cheap = [s for s in sc['stocks'] if s['at_shocked_price'] and s['label'] not in ('Buy', 'Strong Buy')]
        lines = ''.join(
            f'<tr><td>{escape(s["ticker"])}</td><td class="l">{escape(s["group"] or "")}</td><td>{_pct(100 * s["move"])}</td>'
            f'<td>{label(s["label"], s["score"])}</td><td>{money(s["price"])}</td><td>{money(s["shocked"])}</td>'
            f'<td>{money(s["buy"])}</td><td>{escape(s["at_shocked_price"] or "—")}</td></tr>' for s in sc['stocks'])
        parts.append(f'<p class="lead">Universe members the scenario moves ({len(sc["stocks"])}). '
                     f'Not Buy today but at or below the Buy-up-to price after the shock: '
                     f'<b>{escape(", ".join(s["ticker"] for s in cheap) or "none")}</b>.</p>'
                     '<div class="tw"><table><thead><tr><th>Ticker</th><th class="l">Group</th><th>Shock</th>'
                     '<th>Label today</th><th>Price</th><th>After shock</th><th>Buy up to</th>'
                     '<th>At shocked price</th></tr></thead><tbody>' + lines + '</tbody></table></div>')
    return shell('Stress scenarios', ''.join(parts))


def site_pages(root, committed_build, *, now=None):
    record = committed_build['record']
    today = (now or datetime.now(timezone.utc)).date()
    accounts = paper_positions(root, record, today)
    result = build(record, accounts)
    captured = str((record.get('_evidence') or {}).get('captured_at') or '')
    return [(Path(PAGE), render(result, captured=captured))]


if __name__ == '__main__':
    from evidence import current_build
    build_ = current_build(Path('history'))
    record_ = build_['record']
    out = build(record_, paper_positions('.', record_, date.today()))
    for k, sc in out['scenarios'].items():
        print(k)
        for a in sc['accounts']:
            print(f"  {a['name']}: {a['before']:,.0f} -> {a['after']:,.0f} ({a['change_pct']:+.1f}%)")
        print('  newly at Buy:', [s['ticker'] for s in sc['stocks']
                                  if s['at_shocked_price'] and s['label'] not in ('Buy', 'Strong Buy')])
