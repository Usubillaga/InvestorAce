"""Panic and the index leaders: the market thermometer next to the largest companies of the S&P 500 and the
Nasdaq-100, and a paper account that buys those leaders when the thermometer panics (asked for on 23 Nov 2026).

Rule (the same as panic_backtest.weights_study tests):
* Signal: the thermometer closes under 20 (market_pulse.py's four scores: VIX, S&P 500 against its 50- and
  200-day averages, the share of the universe above its own 200-day average; CNN Fear & Greed is left out so the
  signal can be rebuilt from closes). Only the first panic close of an episode counts, at least 63 sessions after
  the previous one.
* Buy: the ten largest S&P 500 holdings of SPY (Yahoo's top holdings), each in proportion to its index weight,
  10,000 USD, at a close after the signal, but only if the thermometer is still in panic shortly before that close
  (the user's rule of 23 Nov 2026: check intraday before buying; no buy once the panic is over). At 20:40 UTC
  (about 20 minutes before the US close) decide() rebuilds the thermometer with intraday prices and leaves a
  pending order; the run after the close fills it at the close. Without panic before the close there is no
  order, and the next sessions are checked again while the episode lasts (63 sessions after its first panic
  close). 0.1% per side.
* Sell: everything at the close after the first euphoria close (thermometer at or above 80), and at the latest
  252 sessions (about a year) after the buy. Until 23 Nov 2026 the rule sold after 63 sessions; the user asked to
  sell in extreme euphoria instead, and the backtest's exit comparison found no reason against it.
Paper only. Weights are read on the day the order is filled, not on the signal day (Yahoo publishes only the
current list). The live thermometer on the scoreboard can differ slightly when Fear & Greed is available.
"""
import argparse
import json
from datetime import datetime, timezone
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATE = ROOT / 'paper_trades' / 'index-leaders.json'
LATEST = ROOT / 'index-leaders' / 'latest.json'
PAGE = 'index-leaders.html'
CAPITAL, COST, HOLD, TOP = 10000., 0.001, 252, 10
EUPHORIA = 80.
FUNDS = (('SPY', 'S&P 500'), ('QQQ', 'Nasdaq-100'))


# ------------------------------------------------------------------ account


def fresh(start):
    """A new account that never fills before `start` (the last completed session when it is first run)."""
    return dict(schema='index-leaders-v1', start=start, capital=CAPITAL, cash=CAPITAL, cost=COST, hold=HOLD,
                top=TOP, positions={}, bought=None, signal=None, done_signals=[], trades=[], marks=[])


def value(state, prices, day):
    """Cash plus positions at the closes of `day` (last known close when a stock has none that day)."""
    total = state['cash']
    for symbol, p in state['positions'].items():
        series = prices.get(symbol) or {}
        known = [d for d in series if d <= day]
        total += p['shares'] * (series[max(known)] if known else p['entry'])
    return total


def advance(state, sessions, heat, prices, holdings, today_signal=None):
    """Move the account through every completed session not yet marked.

    sessions: ordered completed session dates (ISO); heat: {date: thermometer}; prices: {symbol: {date: close}};
    holdings: callable returning [(symbol, weight)] for the buy (only called when a buy is due).
    Returns the list of events (BUY/SELL) applied."""
    events = []
    last_mark = state['marks'][-1]['date'] if state['marks'] else None
    for i, day in enumerate(sessions):
        if day < state.get('start', '') or (last_mark is not None and day <= last_mark):
            continue
        prev = sessions[i - 1] if i else None
        pending = state.get('pending')
        # Fill the order decided intraday (thermometer still in panic before this close) at this close.
        if pending and pending['date'] == day and not state['positions']:
            picks = [(s, w) for s, w in holdings() if w and w > 0 and (prices.get(s) or {}).get(day)][:TOP]
            total_w = sum(w for _, w in picks)
            if picks and total_w > 0:
                cash = state['cash']
                for symbol, w in picks:
                    px = prices[symbol][day]
                    shares = cash * (w / total_w) / (px * (1 + COST))
                    state['positions'][symbol] = dict(shares=round(shares, 6), entry=px, weight=round(w, 6))
                    state['cash'] -= shares * px * (1 + COST)
                state['cash'] = round(state['cash'], 6)
                state.update(bought=day, signal=pending['signal'], sessions_held=0, pending=None)
                state['done_signals'].append(pending['signal'])
                events.append(dict(type='BUY', date=day, signal=pending['signal'], heat=pending['heat'],
                                   heat_close=heat.get(day), symbols=[s for s, _ in picks]))
        elif state['positions']:
            state['sessions_held'] = state.get('sessions_held', 0) + 1
            euphoric = prev is not None and (heat.get(prev) or 0) >= EUPHORIA and prev > state['bought']
            if state['sessions_held'] >= HOLD or euphoric or state.get('selling'):
                # The decision holds until every position has a close to sell at.
                state['selling'] = state.get('selling') or ('EUPHORIA' if euphoric else 'MAX_HOLD')
                proceeds = 0.
                for symbol, p in state['positions'].items():
                    px = (prices.get(symbol) or {}).get(day)
                    if px is None:                       # no close today: keep it and try tomorrow
                        break
                    proceeds += p['shares'] * px * (1 - COST)
                else:
                    why = state['selling']
                    start_value = sum(p['shares'] * p['entry'] * (1 + COST) for p in state['positions'].values())
                    state['trades'].append(dict(signal=state['signal'], bought=state['bought'], sold=day, why=why,
                                                symbols=sorted(state['positions']), cost=round(start_value, 2),
                                                proceeds=round(proceeds, 2),
                                                ret=round(proceeds / start_value - 1, 6) if start_value else None))
                    state['cash'] = round(state['cash'] + proceeds, 6)
                    state['positions'] = {}
                    state.update(bought=None, signal=None, sessions_held=0, selling=None)
                    events.append(dict(type='SELL', date=day, why=why))
        if pending and pending['date'] <= day and state.get('pending'):
            state['pending'] = None                 # unfilled (a missing close): decided again on the next day
        state['marks'].append(dict(date=day, equity=round(value(state, prices, day), 2), heat=heat.get(day)))
    return events


def decide(state, sessions, heat, today, heat_now):
    """Before the close of `today`: leave a buy order for today's close if the thermometer is still in panic
    now (heat_now < 20, from intraday prices) and the current episode has not bought yet.

    sessions/heat are completed closes before today. The episode is the last first-panic close (one per 63
    sessions, panic_backtest.signals) within the last 63 sessions. Returns the order or None."""
    import panic_backtest as pb
    import pandas as pd
    if (state.get('pending') or {}).get('date') == today:
        state['pending'] = None               # the last check before the close decides; an earlier one is replaced
    if state['positions'] or heat_now is None or heat_now >= pb.PANIC:
        return None
    series = pd.Series({pd.Timestamp(d): heat[d] for d in sessions if heat.get(d) is not None}, dtype=float)
    entries = [str(d.date()) for d in pb.signals(series)[0]] if len(series) else []
    recent = [d for d in entries if d in sessions[-pb.GAP:] and d >= state.get('start', '')]
    if not recent or recent[-1] in state['done_signals'] or recent[-1] >= today:
        return None
    state['pending'] = dict(date=today, signal=recent[-1], heat=round(float(heat_now), 2),
                            decided_at=datetime.now(timezone.utc).isoformat(timespec='minutes'))
    return state['pending']


# ------------------------------------------------------------------ data (network; GitHub Actions)
def top_holdings(fund):
    """[(symbol, weight)] from Yahoo's fund data, largest first."""
    import yfinance as yf
    frame = yf.Ticker(fund).funds_data.top_holdings
    out = []
    for symbol, row in frame.iterrows():
        weight = row.get('Holding Percent')
        if weight is not None and weight == weight:
            out.append((str(symbol).replace('.', '-'), float(weight), str(row.get('Name') or symbol)))
    return sorted(out, key=lambda x: -x[1])


def session_cutoff(now=None, intraday=False):
    """First date NOT to read. Today's bar counts once the US close is done (16:15 New York) or, intraday,
    as the latest quote; otherwise it is a partial bar and is left out."""
    import pandas as pd
    now = now or pd.Timestamp.now(tz='America/New_York')
    day = now.normalize().tz_localize(None) if now.tz is not None else now.normalize()
    done = intraday or (now.hour, now.minute) >= (16, 15)
    return day + pd.Timedelta(days=1) if done else day


def collect(today=None, intraday=False):
    """Closes for the thermometer, the holdings and the account; returns (sessions, heat, prices, holdings).

    intraday=True keeps today's partial bar (the latest quote), so the last session is today and its heat is the
    thermometer right now."""
    import yfinance as yf
    import engine
    import panic_backtest as pb
    holdings = {fund: top_holdings(fund) for fund, _ in FUNDS}
    universe = sorted({row.get('yf') or key for key, row in engine.DATA.items()})
    state = load(start='')
    held = sorted(set(state['positions']) | {s for s, _, _ in holdings['SPY'][:TOP]})
    raw = yf.download(sorted(set(universe) | set(held) | {'^GSPC', '^VIX'}), period='2y', auto_adjust=False,
                      progress=False, threads=True, group_by='column')['Close']
    raw.index = raw.index.tz_localize(None) if raw.index.tz is not None else raw.index
    raw = raw[raw.index < session_cutoff(today, intraday)].round(4)
    spx = raw['^GSPC'].dropna()
    heat = pb.heat(spx, raw['^VIX'], raw[[s for s in universe if s in raw.columns]])
    sessions = [str(d.date()) for d in spx.index]
    heat_map = {str(d.date()): round(float(v), 2) for d, v in heat.dropna().items()}
    prices = {s: {str(d.date()): float(v) for d, v in raw[s].dropna().items()} for s in held if s in raw.columns}
    return sessions, heat_map, prices, holdings


def load(path=STATE, start=None):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return fresh(start)


def run(path=STATE, latest=LATEST):
    sessions, heat, prices, holdings = collect()
    state = load(path, start=sessions[-1])
    events = advance(state, sessions[-130:], heat, prices,
                     lambda: [(s, w) for s, w, _ in holdings['SPY'][:TOP]])
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(state, indent=1) + '\n', encoding='utf-8')
    last = sessions[-1]
    snapshot = dict(schema='index-leaders-latest-v1', as_of=datetime.now(timezone.utc).isoformat(timespec='minutes'),
                    session=last, heat=heat.get(last), heat_recent=[[d, heat[d]] for d in sessions[-30:] if d in heat],
                    holdings={fund: [dict(symbol=s, weight=w, name=n) for s, w, n in rows]
                              for fund, rows in holdings.items()},
                    events=events)
    Path(latest).parent.mkdir(parents=True, exist_ok=True)
    Path(latest).write_text(json.dumps(snapshot, indent=1) + '\n', encoding='utf-8')
    print(json.dumps(dict(session=last, heat=heat.get(last), events=events), indent=1))


def decide_run(path=STATE, latest=LATEST):
    """20:40 UTC: the intraday thermometer decides whether today's close buys."""
    import pandas as pd
    now = pd.Timestamp.now(tz='America/New_York')
    minutes = now.hour * 60 + now.minute
    if not 15 * 60 + 10 <= minutes <= 15 * 60 + 55:          # only shortly before a regular 16:00 close
        print(json.dumps(dict(now=now.isoformat(timespec='minutes'), decision='outside the pre-close window')))
        return None
    sessions, heat, _, _ = collect(intraday=True)
    today = str(now.date())
    if not sessions or sessions[-1] != today:
        print(json.dumps(dict(today=today, decision='no session today')))
        return None
    state = load(path, start=sessions[-2])
    heat_now = heat.get(today)
    order = decide(state, sessions[:-1][-130:], heat, today, heat_now)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(state, indent=1) + '\n', encoding='utf-8')
    try:
        snapshot = json.loads(Path(latest).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        snapshot = {}
    snapshot['intraday'] = dict(date=today, heat=heat_now, order=bool(order),
                                checked_at=datetime.now(timezone.utc).isoformat(timespec='minutes'))
    Path(latest).parent.mkdir(parents=True, exist_ok=True)
    Path(latest).write_text(json.dumps(snapshot, indent=1) + '\n', encoding='utf-8')
    print(json.dumps(dict(today=today, heat_now=heat_now, order=order), indent=1))
    return order


# ------------------------------------------------------------------ page
YELLOW = '#f5d000'
BAND_COLOURS = (('Panic', '#0b6b2b'), ('Fear', '#7fb07f'), ('Neutral', '#c8c6b8'), ('Greed', '#7a4a0a'),
                ('Euphoria', '#8f2525'))


def _pct(x, digits=2):
    return '—' if x is None else f'{100 * x:.{digits}f}%'


def render(snapshot, state, backtest=None):
    import market_pulse
    from war_scenario import shell
    h = snapshot.get('heat')
    band = market_pulse.band(h)
    colour = dict(BAND_COLOURS).get(band, '#c8c6b8')
    bar = ''.join(f'<span style="background:{c}"></span>' for _, c in BAND_COLOURS)
    buy = h is not None and h < 20
    intraday = snapshot.get('intraday') or {}
    status = (f'<b style="color:{YELLOW}">PANIC · buy signal</b>: the account buys the S&amp;P 500 leaders at a '
              'following close if the thermometer is still under 20 about 20 minutes before that close.' if buy else
              'No panic: the account does not buy. After a panic close (thermometer under 20) it buys the S&amp;P 500 '
              'leaders at a following close, only if the thermometer is still under 20 shortly before it, and sells them at the close after the first '
              'euphoria close (80 or more), at the latest after 252 sessions.')
    recent = ''.join(f'<span title="{escape(d)}: {v:.1f}" style="display:inline-block;width:8px;height:{max(3, v)}px;'
                     f'margin-right:2px;vertical-align:bottom;background:'
                     f'{dict(BAND_COLOURS).get(market_pulse.band(v), "#888")}"></span>'
                     for d, v in snapshot.get('heat_recent', []))
    parts = [f'<style>{market_pulse.CSS}</style>', f'<h1 style="color:{YELLOW}">Panic &amp; index leaders</h1>',
             '<div class="note">The market thermometer (the scoreboard\'s crash and panic gauge) next to the '
             'largest companies of the S&amp;P 500 and the Nasdaq-100 by index weight. When the thermometer '
             'closes under 20 (panic), a paper account buys the ten largest S&amp;P 500 holdings, weighted as in '
             'the index, and sells them after the first close in extreme euphoria (80 or more), at the latest a year '
             'later. Paper only; not advice.</div>',
             '<div class="box pulse-thermo"><h2>Thermometer</h2>'
             f'<span class="pulse-big" style="color:{colour}">{"—" if h is None else format(h, ".1f")}</span> /100 · '
             f'<b>{escape(band or "—")}</b> · close of {escape(snapshot.get("session") or "—")}'
             f'<div class="pulse-bar">{bar}<i class="pulse-marker" style="left:{0 if h is None else h:.1f}%"></i></div>'
             '<small>Panic · buy — Fear — Neutral — Greed — Euphoria · sell</small>'
             f'<p>{status}</p>'
             + (f'<p>Intraday check {escape(intraday["date"])} ({escape(intraday.get("checked_at", ""))} UTC): '
                f'thermometer {"—" if intraday.get("heat") is None else format(intraday["heat"], ".1f")} → '
                f'{"<b>buy order for the close</b>" if intraday.get("order") else "no buy order"}</p>'
                if intraday.get('date') else '')
             + f'<div style="margin-top:8px">Last 30 sessions: {recent}</div>'
             '<p class="muted">Rebuilt from closes without CNN Fear &amp; Greed, so it can differ slightly from the '
             'scoreboard\'s gauge. The industry bubble monitor is on the <a href="crash-monitor.html">crash '
             'monitor</a> page.</p></div>']
    for fund, name in FUNDS:
        rows = snapshot.get('holdings', {}).get(fund) or []
        body = ''.join(f'<tr><td>{i}</td><td class="mono"><b>{escape(r["symbol"])}</b></td><td>{escape(r["name"])}</td>'
                       f'<td class="mono">{_pct(r["weight"])}</td><td style="width:40%"><span style="display:block;'
                       f'height:10px;width:{min(100, 400 * r["weight"]):.0f}%;background:{YELLOW}"></span></td></tr>'
                       for i, r in enumerate(rows, 1))
        parts.append(f'<h2>{escape(name)} leaders by index weight ({escape(fund)})</h2>'
                     + ('<div class="tw"><table><thead><tr><th>#</th><th>Symbol</th><th>Company</th><th>Weight</th>'
                        f'<th></th></tr></thead><tbody>{body}</tbody></table></div>' if body
                        else '<p class="muted">Holdings not available.</p>'))
    equity = state['marks'][-1]['equity'] if state.get('marks') else state.get('capital')
    pos = ''.join(f'<tr><td class="mono">{escape(s)}</td><td class="mono">{p["shares"]:.4f}</td>'
                  f'<td class="mono">{p["entry"]:.2f}</td><td class="mono">{_pct(p.get("weight"))}</td></tr>'
                  for s, p in sorted(state.get('positions', {}).items()))
    trades = ''.join(f'<tr><td>{escape(t["signal"])}</td><td>{escape(t["bought"])}</td><td>{escape(t["sold"])}</td>'
                     f'<td class="mono">{_pct(t["ret"], 1)}</td></tr>' for t in state.get('trades', []))
    parts.append('<h2>Paper account</h2>'
                 f'<p>Equity <b>{equity:,.2f} USD</b> (start {state.get("capital", CAPITAL):,.0f}) · cash '
                 f'{state.get("cash", 0):,.2f} · '
                 + (f'holding since {escape(state["bought"])} (signal {escape(state["signal"])}), session '
                    f'{state.get("sessions_held", 0)} of {HOLD}' if state.get('positions') else 'flat') + '</p>'
                 + (f'<div class="tw"><table><thead><tr><th>Symbol</th><th>Shares</th><th>Entry</th><th>Index weight'
                    f'</th></tr></thead><tbody>{pos}</tbody></table></div>' if pos else '')
                 + (f'<div class="tw"><table><thead><tr><th>Signal</th><th>Bought</th><th>Sold</th><th>Return</th>'
                    f'</tr></thead><tbody>{trades}</tbody></table></div>' if trades else ''))
    if backtest:
        parts.append('<h2>Backtest</h2><div class="note">From the last backtest run (backtest.html, section '
                     '"Thermometer Panic · buy"); six panic episodes since 2015, so treat it as a hint, not proof.'
                     '</div>' + backtest)
    return shell('Panic & index leaders', ''.join(parts))


def backtest_html(root):
    """The weight-based leader table from backtests/latest.json, if present."""
    try:
        result = json.loads((Path(root) / 'backtests' / 'latest.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return ''
    block = ((result.get('panic') or {}).get('panic_entry') or {}).get('weights')
    if not block or not block.get('summary'):
        return ''
    rows = ''.join(f'<tr><td>{h}</td><td>{c["n"]}</td><td class="mono">{_pct(c["leaders"]["mean"], 1)}</td>'
                   f'<td class="mono">{_pct(c["spx"]["mean"], 1)}</td><td>{c["beats_spx"]}/{c["n"]}</td></tr>'
                   for h, c in block['summary'].items() if c.get('n'))
    return ('<div class="tw"><table><thead><tr><th>Sessions held</th><th>Signals</th><th>Top 10 by weight</th>'
            f'<th>S&amp;P 500</th><th>Beats S&amp;P</th></tr></thead><tbody>{rows}</tbody></table></div>')


def site_pages(root):
    try:
        snapshot = json.loads((Path(root) / 'index-leaders' / 'latest.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return []
    return [(Path(PAGE), render(snapshot, load(Path(root) / 'paper_trades' / 'index-leaders.json', start=''),
                                backtest_html(root)))]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--decide', action='store_true', help='before the close: intraday thermometer, buy order')
    if parser.parse_args().decide:
        decide_run()
    else:
        run()
