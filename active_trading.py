"""Active paper trading: the user's own orders, kept apart from the model's paper tests.

Orders arrive as GitHub issues titled ``paper-order: BUY 10 MU`` (repository owner
only, see .github/workflows/paper-order.yml) and are appended to
``paper_trades/active-account.json``. Nothing is filled when the order arrives:
every fill is replayed from committed closes, at the close of the first session
whose cut-off lies after the submission time. Same-day fills therefore need the
order before the cut-off, and no order can pick a price it has already seen.

Paper only. No broker is connected and no real order is ever sent.
"""
import json
import re
from datetime import date, datetime, timedelta, timezone
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FILE = ROOT / 'paper_trades' / 'active-account.json'
SCHEMA = 'active-account-v1'
PAGE = 'trade.html'
REPO = 'Usubillaga/InvestorAce'
BENCHMARK = '^GSPC'
EU_SUFFIXES = ('.MC', '.AS', '.PA', '.DE', '.MI', '.BR', '.LS', '.CO', '.ST', '.HE', '.SW', '.L')
US_CUTOFF = '19:30'      # NYSE closes 20:00 UTC in summer, 21:00 in winter
EU_CUTOFF = '15:00'      # European cash markets close about 16:30 UTC
ORDER = re.compile(r'^\s*paper-order:\s*(BUY|SELL)\s+(\d{1,6})\s+([A-Za-z0-9.\-^=]{1,15})\s*$', re.I)
CANCEL = re.compile(r'^\s*paper-order:\s*CANCEL\s+#?(\d{1,7})\s*$', re.I)


def new_account(opened):
    return dict(schema=SCHEMA, name="Active trading · Claude's trading rules v1", capital=10000.,
                account_currency='EUR', fx={'USD': 0.89063}, opened=opened,
                fx_note='Fixed rate 1 EUR = 1.1228 USD, the same as the model paper tests; '
                        'currency moves are not part of the result.',
                orders=[])


def load(path=FILE):
    path = Path(path)
    if not path.exists():
        return None
    doc = json.loads(path.read_text(encoding='utf-8'))
    return doc if doc.get('schema') == SCHEMA else None


def save(doc, path=FILE):
    Path(path).write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def parse(title):
    """('BUY'|'SELL', shares, symbol) or ('CANCEL', order_id, None); ValueError otherwise."""
    match = ORDER.match(title or '')
    if match:
        shares = int(match.group(2))
        if shares <= 0:
            raise ValueError('shares must be a positive whole number')
        return match.group(1).upper(), shares, match.group(3).upper()
    match = CANCEL.match(title or '')
    if match:
        return 'CANCEL', int(match.group(1)), None
    raise ValueError('title must look like "paper-order: BUY 10 MU", "paper-order: SELL 5 MU" '
                     'or "paper-order: CANCEL 123"')


def resolve(symbol, universe):
    """Universe key and its row for a ticker or Yahoo symbol; None when unknown."""
    symbol = symbol.upper()
    for key, row in universe.items():
        if symbol in (key.upper(), str(row.get('yf') or '').upper()):
            return key, row
    return None, None


def intake(doc, title, *, issue, created_at, universe):
    """Append one order (or a cancel) and return (accepted, message). Never fills."""
    try:
        side, amount, symbol = parse(title)
    except ValueError as exc:
        return False, str(exc)
    orders = doc.setdefault('orders', [])
    if any(o.get('id') == issue for o in orders):
        return False, f'issue #{issue} is already recorded'
    if side == 'CANCEL':
        target = next((o for o in orders if o.get('id') == amount and o.get('side') in ('BUY', 'SELL')), None)
        if target is None:
            return False, f'no order #{amount} to cancel'
        if target.get('cancelled_at'):
            return False, f'order #{amount} is already cancelled'
        target['cancelled_at'] = created_at
        target['cancelled_by'] = issue
        return True, (f'cancel recorded for order #{amount}; it takes effect only if it arrived '
                      'before that order\'s fill cut-off')
    key, row = resolve(symbol, universe)
    if key is None:
        return False, f'{symbol} is not in the InvestorAce universe; add it first'
    currency = row.get('cur') or 'USD'
    if currency != doc.get('account_currency') and currency not in (doc.get('fx') or {}):
        return False, f'{key} is listed in {currency}; only EUR and USD listings can be traded for now'
    orders.append(dict(id=issue, side=side, ticker=key, yahoo=row.get('yf') or key, currency=currency,
                       shares=amount, submitted_at=created_at))
    return True, (f'{side} {amount} {key} recorded; it fills at the close of the first session whose '
                  f'cut-off is after {created_at} (see trade.html)')


def _when(value):
    return datetime.fromisoformat(str(value).replace('Z', '+00:00')).astimezone(timezone.utc)


def cutoff(day, yahoo):
    clock = EU_CUTOFF if str(yahoo).upper().endswith(EU_SUFFIXES) else US_CUTOFF
    return datetime.fromisoformat(f'{day}T{clock}:00+00:00')


def fill(order, series):
    """(date, close) of the session that fills the order, or None while none exists yet."""
    submitted = _when(order['submitted_at'])
    for day, close in series.get(order['yahoo']) or []:
        if day >= submitted.date().isoformat() and submitted < cutoff(day, order['yahoo']):
            return day, close
    return None


def _rate(doc, currency):
    return 1. if currency == doc.get('account_currency') else (doc.get('fx') or {}).get(currency)


def _last(series, symbol, as_of):
    rows = [r for r in series.get(symbol) or [] if r[0] <= as_of]
    return rows[-1] if rows else None


def replay(doc, series, as_of):
    """Fill, reject or keep pending every order in time order; value the positions."""
    as_of = as_of.isoformat() if isinstance(as_of, date) else str(as_of)
    events, out = [], []
    for order in doc.get('orders', []):
        o = dict(order)
        hit = fill(o, series)
        if hit and hit[0] > as_of:
            hit = None
        if o.get('cancelled_at') and (hit is None or _when(o['cancelled_at']) < cutoff(hit[0], o['yahoo'])):
            o.update(status='CANCELLED')
        elif hit is None:
            o.update(status='PENDING')
        else:
            o.update(fill_date=hit[0], fill_price=hit[1])
            events.append(o)
        out.append(o)
    cash, held, realized = float(doc['capital']), {}, 0.
    for o in sorted(events, key=lambda e: (e['fill_date'], cutoff(e['fill_date'], e['yahoo']), e['id'])):
        rate = _rate(doc, o['currency'])
        amount = o['shares'] * o['fill_price'] * rate
        position = held.setdefault(o['ticker'], dict(ticker=o['ticker'], yahoo=o['yahoo'], currency=o['currency'],
                                                     shares=0, cost=0.))
        if o['side'] == 'BUY':
            if amount > cash + 1e-9:
                o.update(status='REJECTED', reason=f'not enough cash ({cash:,.2f} EUR for {amount:,.2f} EUR)')
                continue
            cash -= amount
            position['shares'] += o['shares']
            position['cost'] += amount
        else:
            if o['shares'] > position['shares']:
                o.update(status='REJECTED', reason=f'only {position["shares"]} shares held')
                continue
            basis = position['cost'] * o['shares'] / position['shares']
            cash += amount
            realized += amount - basis
            o['realized'] = amount - basis
            position['shares'] -= o['shares']
            position['cost'] -= basis
        o.update(status='FILLED', amount=amount)
    positions = []
    for p in held.values():
        if not p['shares']:
            continue
        last = _last(series, p['yahoo'], as_of)
        rate = _rate(doc, p['currency'])
        value = p['shares'] * last[1] * rate if last else None
        positions.append(dict(p, last_date=last[0] if last else None, last_close=last[1] if last else None,
                              value=value, pnl=None if value is None else value - p['cost'],
                              pnl_pct=None if value is None or not p['cost'] else 100 * (value / p['cost'] - 1)))
    priced = all(p['value'] is not None for p in positions)
    value = cash + sum(p['value'] for p in positions) if priced else None
    bench = None
    start, end = _first_on_or_after(series, BENCHMARK, doc['opened']), _last(series, BENCHMARK, as_of)
    if start and end and end[0] >= start[0]:
        bench = 100 * (end[1] / start[1] - 1)
    return dict(as_of=as_of, capital=float(doc['capital']), cash=cash, positions=positions, orders=out,
                realized=realized, value=value, pnl=None if value is None else value - float(doc['capital']),
                return_pct=None if value is None else 100 * (value / float(doc['capital']) - 1),
                benchmark_pct=bench, priced=priced)


def _first_on_or_after(series, symbol, day):
    rows = [r for r in series.get(symbol) or [] if r[0] >= day]
    return rows[0] if rows else None


def tracked_symbols(path=FILE):
    """Symbols whose closes the nightly build must record: held, pending, and the benchmark."""
    doc = load(path)
    if doc is None:
        return []
    return sorted({o['yahoo'] for o in doc.get('orders', []) if o.get('yahoo')} | {BENCHMARK})


def _money(value, digits=0):
    return '—' if value is None else '€' + format(value, f',.{digits}f')


def _signed(value, pct=False):
    if value is None:
        return '—'
    css = 'up' if value > 0.005 else 'down' if value < -0.005 else ''
    text = (format(value, '+.2f') + '%') if pct else (('+' if value >= 0 else '−') + '€' + format(abs(value), ',.0f'))
    return f'<span class="{css}">{text}</span>'


def _universe(record):
    inputs = ((record.get('_evidence') or {}).get('inputs') or {})
    rows = []
    for t in sorted(k for k in record if not k.startswith('_') and isinstance(record[k], dict)):
        opp = record[t].get('opportunity') or {}
        cur = (inputs.get(t) or {}).get('cur') or ''
        rows.append(dict(t=t, yf=(inputs.get(t) or {}).get('yf') or t, cur=cur,
                         label=opp.get('label'), score=opp.get('score'),
                         price=opp.get('price', record[t].get('price')),
                         buy=(opp.get('price_thresholds') or {}).get('buy')))
    return rows


RULES_HTML = (
    '<details class="note" open><summary><b>Trading rules v1 (Claude), fixed 2026-11-12</b></summary><ul>'
    '<li><b>Buy</b> only InvestorAce Buy or Strong Buy, above the 200-day average, at or above the 21-day average and '
    'at most 3 ATR above it, no report in the next 5 days, and only while the S&amp;P 500 is above its 200-day '
    'average. A report in the last 10 days ranks first (post-earnings drift), then the model score.</li>'
    '<li><b>Size</b>: risk 1% of equity per trade at the stop, at most 20% per position, at most 8 positions, '
    '3% cash kept.</li>'
    '<li><b>Sell</b>: stop at −8% (−5% in a correction); stop to the entry price after +10%; after +20% the stop '
    'trails 10% under the highest close; half sold at +25% (once); sold before a report without a +10% cushion; '
    'sold below the 200-day average, when the label falls to Hold Negative or Sell, or after 15 sessions with '
    'less than +2%.</li>'
    '<li><b>8-week rule</b> (O\'Neil): a position up 20% within 15 sessions is held 40 sessions; only the stop at '
    'the entry price applies.</li>'
    '<li>Decided each weekday from the last committed build (the previous close); orders fill at that day\'s close. '
    'Sources: O\'Neil, Minervini, Elder/Van Tharp position sizing, Bernard &amp; Thomas (1989).</li></ul></details>')

TRADE_CSS = """
.form{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;background:var(--panel);
border:1px solid var(--line);border-radius:10px;padding:16px;margin:16px 0}
.form label{display:flex;flex-direction:column;gap:6px;color:var(--muted);font-size:13px}
.form select,.form input{background:#0d0f14;color:var(--text);border:1px solid var(--line);border-radius:8px;
padding:9px 10px;font:inherit}.form button{grid-column:1/-1;padding:12px;border-radius:8px;border:0;
background:var(--accent);color:#10140a;font-weight:700;font-size:16px;cursor:pointer}
.form .est{grid-column:1/-1;color:var(--muted)}.side{display:flex;gap:8px}.side label{flex-direction:row;
align-items:center;gap:6px;color:var(--text)}
"""

TRADE_JS = r"""
(function(){
  const data=JSON.parse(document.getElementById('trade-universe').textContent);
  const fx=JSON.parse(document.getElementById('trade-fx').textContent);
  const pick=document.getElementById('trade-ticker'), qty=document.getElementById('trade-shares');
  const est=document.getElementById('trade-estimate'), go=document.getElementById('trade-send');
  data.forEach(r=>{const o=document.createElement('option');o.value=r.t;
    o.textContent=r.t+(r.label?' · '+r.label+(r.score!=null?' '+r.score.toFixed(2):''):' · no label');pick.appendChild(o);});
  function side(){return document.querySelector('input[name="trade-side"]:checked').value;}
  function update(){
    const r=data.find(x=>x.t===pick.value), n=parseInt(qty.value,10);
    if(!r||!(n>0)){est.textContent='Choose a ticker and a whole number of shares.';return;}
    const rate=r.cur==='EUR'?1:fx[r.cur];
    if(!rate){est.textContent=r.t+' is listed in '+r.cur+'; only EUR and USD listings can be traded for now.';return;}
    const value=r.price!=null?n*r.price*rate:null;
    est.textContent=side()+' '+n+' '+r.t+' · last build price '+(r.price!=null?r.price.toFixed(2)+' '+r.cur:'—')
      +(value!=null?' · about €'+value.toLocaleString('en',{maximumFractionDigits:0}):'')
      +(r.buy!=null?' · model Buy up to '+r.buy.toFixed(2):'')
      +'. The fill price is the close of the fill session, not this estimate.';
  }
  [pick,qty].forEach(x=>x.addEventListener('input',update));
  document.querySelectorAll('input[name="trade-side"]').forEach(x=>x.addEventListener('change',update));
  go.addEventListener('click',()=>{
    const n=parseInt(qty.value,10);if(!(n>0)||!pick.value){update();return;}
    const title='paper-order: '+side()+' '+n+' '+pick.value;
    const body='Paper order from trade.html. Filled at the close of the first session after the cut-off; '
      +'no real order is sent. Submit this issue unchanged to place it.';
    window.open('https://github.com/'+go.dataset.repo+'/issues/new?title='+encodeURIComponent(title)
      +'&body='+encodeURIComponent(body),'_blank','noopener');
  });
  update();
})();
"""


def render(doc, result, record, *, now):
    from war_scenario import shell
    universe = _universe(record)
    tiles = ''.join(f'<div class="tile"><span>{k}</span><b>{v}</b></div>' for k, v in [
        ('Capital', _money(result['capital'])), ('Cash', _money(result['cash'])),
        ('Value now', _money(result['value'])), ('Gain/loss', _signed(result['pnl'])),
        ('Return', _signed(result['return_pct'], pct=True)),
        ('S&amp;P 500 since opening', _signed(result['benchmark_pct'], pct=True))])
    labels = {r['t']: r for r in universe}
    rows = ''.join(
        f'<tr><td><b>{escape(p["ticker"])}</b></td><td class="l">{escape(str((labels.get(p["ticker"]) or {}).get("label") or "—"))}</td>'
        f'<td>{p["shares"]}</td><td>{_money(p["cost"])}</td><td>{"—" if p["last_close"] is None else format(p["last_close"], ",.2f")} '
        f'{escape(p["currency"])}</td><td>{escape(str(p["last_date"] or "—"))}</td><td>{_money(p["value"])}</td>'
        f'<td>{_signed(p["pnl"])}</td><td>{_signed(p["pnl_pct"], pct=True)}</td></tr>'
        for p in sorted(result['positions'], key=lambda p: -(p['value'] or 0)))
    orders = ''.join(
        f'<tr><td>#{o["id"]}</td><td class="l">{escape(o["side"])} {o["shares"]} <b>{escape(o["ticker"])}</b></td>'
        f'<td>{escape(str(o["submitted_at"])[:16].replace("T", " "))}</td><td class="l">{escape(o["status"])}'
        f'{" · " + escape(o["reason"]) if o.get("reason") else ""}</td><td>{escape(str(o.get("fill_date") or "—"))}</td>'
        f'<td>{"—" if o.get("fill_price") is None else format(o["fill_price"], ",.2f")}</td>'
        f'<td>{_money(o.get("amount"))}</td><td>{_signed(o.get("realized")) if "realized" in o else "—"}</td></tr>'
        for o in sorted(result['orders'], key=lambda o: -o['id']))
    body = (f'<h1>Active trading</h1><p class="lead">{escape(doc.get("name") or "")}. A paper account separate from '
            f'the model\'s paper tests, so trading rules can be compared with the model. Opened {escape(doc["opened"])} with '
            f'{_money(doc["capital"])}. Valued at the closes up to {escape(result["as_of"])}; built '
            f'{escape(now.strftime("%Y-%m-%d %H:%M"))} UTC.</p>'
            f'<div class="tiles">{tiles}</div>'
            + ('' if result['priced'] else '<p class="muted">A position has no close yet; the total is withheld '
               'instead of being shown without it.</p>')
            + RULES_HTML + '<h2>Place an order</h2><div class="form">'
            '<label>Ticker<select id="trade-ticker"></select></label>'
            '<label>Shares<input id="trade-shares" type="number" min="1" step="1" value="10"></label>'
            '<div class="side"><label><input type="radio" name="trade-side" value="BUY" checked> Buy</label>'
            '<label><input type="radio" name="trade-side" value="SELL"> Sell</label></div>'
            '<p class="est" id="trade-estimate"></p>'
            f'<button type="button" id="trade-send" data-repo="{escape(REPO, quote=True)}">Send order via GitHub</button></div>'
            '<div class="note">The button opens a prepared GitHub issue; submit it to place the order (repository owner '
            'only). A workflow records it within a minute. It fills at the <b>close</b> of the first session whose '
            f'cut-off is after you submitted: {US_CUTOFF} UTC for US and Canadian listings, {EU_CUTOFF} UTC for '
            'European ones, otherwise the next session. Whole shares, no short selling, no leverage; a buy larger than '
            'the cash at the fill is rejected. To cancel, open an issue "paper-order: CANCEL &lt;order number&gt;" '
            'before the cut-off. Paper only: no broker is connected and no real order is sent. '
            f'{escape(doc.get("fx_note") or "")}</div>'
            '<h2>Positions</h2><div class="tw"><table><thead><tr><th>Ticker</th><th class="l">Model label</th>'
            '<th>Shares</th><th>Cost</th><th>Last close</th><th>Date</th><th>Value</th><th>Gain/loss</th><th>%</th>'
            '</tr></thead><tbody>' + (rows or '<tr><td colspan="9" class="l muted">No positions yet.</td></tr>')
            + '</tbody></table></div><h2>Orders</h2><div class="tw"><table><thead><tr><th>#</th><th class="l">Order</th>'
            '<th>Submitted (UTC)</th><th class="l">Status</th><th>Fill date</th><th>Fill price</th><th>Amount</th>'
            '<th>Realized</th></tr></thead><tbody>'
            + (orders or '<tr><td colspan="8" class="l muted">No orders yet.</td></tr>') + '</tbody></table></div>'
            '<script type="application/json" id="trade-universe">'
            + json.dumps(universe).replace('</', '<\\/') + '</script>'
            '<script type="application/json" id="trade-fx">'
            + json.dumps(doc.get('fx') or {}).replace('</', '<\\/') + f'</script><script>{TRADE_JS}</script>')
    return shell('Active trading', body).replace('</style>', TRADE_CSS + '</style>', 1)


def site_pages(root, build, *, now=None):
    from paper_portfolio import merge_series
    now = now or datetime.now(timezone.utc)
    doc = load(Path(root) / 'paper_trades' / 'active-account.json')
    if doc is None:
        return []
    start = date.fromisoformat(doc['opened']) - timedelta(days=7)
    snapshots = []
    for path in sorted((Path(root) / 'history' / 'runs').glob('*.json')):
        try:
            stamp = datetime.strptime(path.name[:8], '%Y%m%d').date()
        except ValueError:
            continue
        if stamp >= start:
            snapshots.append(json.loads(path.read_text(encoding='utf-8')))
    snapshots.append(build['record'])
    result = replay(doc, merge_series(snapshots), now.date())
    return [(Path(PAGE), render(doc, result, build['record'], now=now))]


def main(argv=None):
    import argparse
    import os
    parser = argparse.ArgumentParser(description='Record one paper order from a GitHub issue.')
    parser.add_argument('command', choices=['intake'])
    parser.parse_args(argv)
    import engine
    doc = load() or new_account(datetime.now(timezone.utc).date().isoformat())
    accepted, message = intake(doc, os.environ.get('ORDER_TITLE', ''), issue=int(os.environ['ORDER_ISSUE']),
                               created_at=os.environ['ORDER_CREATED_AT'], universe=engine.DATA)
    if accepted:
        save(doc)
    print(('ACCEPTED: ' if accepted else 'REJECTED: ') + message)
    output = os.environ.get('GITHUB_OUTPUT')
    if output:
        with open(output, 'a', encoding='utf-8') as handle:
            handle.write(f'accepted={"true" if accepted else "false"}\n')
            handle.write(f'message={message}\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
