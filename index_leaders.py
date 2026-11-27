"""Panic and the index leaders: the market thermometer next to the largest companies of the S&P 500 and the
Nasdaq-100, and a paper account that buys those leaders when the thermometer panics (asked for on 23 Nov 2026).

Rule (the same as panic_backtest.weights_study tests):
* Signal: the thermometer closes under 20 (market_pulse.py's four scores: VIX, S&P 500 against its 50- and
  200-day averages, the share of the universe above its own 200-day average; CNN Fear & Greed is left out so the
  signal can be rebuilt from closes). Only the first panic close of an episode counts, at least 63 sessions after
  the previous one.
* Buy: half the account in the ten largest S&P 500 holdings of SPY (Yahoo's top holdings), each in proportion
  to its index weight, and half in RSP (the equal-weight S&P 500 ETF), 10,000 USD, at a close after the signal, but only if the thermometer is still in panic shortly before that close
  (the user's rule of 23 Nov 2026: check intraday before buying; no buy once the panic is over). Between 50 and
  5 minutes before the close (16:00 New York, or 13:00 on early-close days) decide() rebuilds the thermometer
  with intraday prices and leaves a pending order (the last check wins); about one hour after the open the
  thermometer is only recorded (25 Nov 2026, the user's request), it places no order; the run after the close fills it at the close. Without panic before the close there is no
  order, and the next sessions are checked again while the episode lasts (63 sessions after its first panic
  close). 0.1% per side.
* Sell: hold at least 42 months (882 sessions); then everything at the close after the first euphoria close
  (thermometer at or above 80). No other exit, no stop.
* Two accounts with the same rules except the buy level (24 Nov 2026, after panic_history.py's study of every
  level from 20 to 10): paper_trades/index-leaders.json buys under 20, paper_trades/index-leaders-17.json under 17.
History of the rule: 23 Nov 2026 top 10 only, sold after 63 sessions, then at euphoria within 252 sessions; 24 Nov
2026 the mixed basket and the 42-month hold, which held up on every panic since 2000 (including 2001 and 2008) in
the backtest, at the cost of falls of up to 57% while held.
Paper only. Weights are read on the day the order is filled, not on the signal day (Yahoo publishes only the
current list). The live thermometer on the scoreboard can differ slightly when Fear & Greed is available.
"""
import argparse
import json
from datetime import datetime, timezone
from html import escape
from math import floor
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATE = ROOT / 'paper_trades' / 'index-leaders.json'
LATEST = ROOT / 'index-leaders' / 'latest.json'
PAGE = 'index-leaders.html'
CAPITAL, COST, TOP = 10000., 0.001, 10
MIN_HOLD = 882                  # 42 months
EQUAL_WEIGHT = 'RSP'            # the equal-weight half of the basket
EUPHORIA = 80.
ACCOUNTS = (('20', 20., STATE), ('17', 17., ROOT / 'paper_trades' / 'index-leaders-17.json'),
            ('17-spcx-ant', 17., ROOT / 'paper_trades' / 'index-leaders-17-spcx-ant.json'),
            ('20-move', 20., ROOT / 'paper_trades' / 'index-leaders-20-move.json'))
FX = 'EURUSD=X'                 # USD per EUR, for accounts kept in euros
MIX = (('top10', .5), (EQUAL_WEIGHT, .5))
# The third account (user's request, 24 Nov 2026): 25,000 EUR, level 17, 15% SpaceX and 15% Anthropic on top of the
# mixed basket. Neither has a backtest or a model label (Anthropic listed on 19 Nov 2026, SpaceX in June 2026).
SETUP = {'20': dict(capital=CAPITAL, currency='USD', basket_spec=MIX),
         '17': dict(capital=CAPITAL, currency='USD', basket_spec=MIX),
         '17-spcx-ant': dict(capital=25000., currency='EUR',
                             basket_spec=(('top10', .35), (EQUAL_WEIGHT, .35), ('SPCX', .15), ('ANT', .15)),
                             basket='35% the ten largest S&P 500 holdings by weight, 35% RSP, 15% SpaceX (SPCX), '
                                    '15% Anthropic (ANT)'),
         # The fourth account (user's request, 26 Nov 2026): buys under 20, but only while bond-market stress is not
         # high, the MOVE index at most 15 points above its three-year mean (3Fourteen's VIX & MOVE chart), and with
         # 15% SpaceX and 15% Anthropic like the third account (user's request the same day, before any buy).
         # Experimental: in the panic study the five buys with MOVE above +15 all beat the S&P 500 after 42 months
         # (+60% on average), so this filter would have skipped them; SpaceX and Anthropic have no backtest.
         '20-move': dict(capital=CAPITAL, currency='USD', move_max=15.,
                         basket_spec=(('top10', .35), (EQUAL_WEIGHT, .35), ('SPCX', .15), ('ANT', .15)),
                         basket='35% the ten largest S&P 500 holdings by weight, 35% RSP, 15% SpaceX (SPCX), '
                                '15% Anthropic (ANT)')}
MOVE_WINDOW = 756               # three years of sessions
FIRST_START = '2026-11-20'      # both accounts watch the panic that began on 20 Nov 2026 (buys only via decide())
RULES = dict(basket='half the ten largest S&P 500 holdings by weight, half RSP', min_hold=MIN_HOLD,
             exit='close after the first euphoria close (80+) once 42 months are held', stop=None)
FUNDS = (('SPY', 'S&P 500'), ('QQQ', 'Nasdaq-100'))


# ------------------------------------------------------------------ account


def fresh(start, level=20., name=None):
    """A new account that never fills before `start` and buys under `level` (setup of the account `name`)."""
    setup = dict(SETUP.get(name or f'{level:g}', SETUP['20']))
    rules = dict(RULES, **{k: v for k, v in setup.items() if k in ('basket', 'move_max')})
    return dict(schema='index-leaders-v2', start=start, level=level, capital=setup['capital'], cash=setup['capital'],
                currency=setup['currency'], basket_spec=[list(x) for x in setup['basket_spec']], cost=COST, top=TOP,
                positions={}, bought=None, signal=None, done_signals=[], trades=[], marks=[], **rules)


def _fx(prices, day):
    """USD per EUR at the last close on or before `day`, or None."""
    series = prices.get(FX) or {}
    known = [d for d in series if d <= day]
    return series[max(known)] if known else None


def upgrade(state, level, name=None):
    """Bring an account written under the earlier rule to the current one; only allowed while it holds nothing."""
    if state.get('schema') == 'index-leaders-v2':
        state.setdefault('currency', 'USD')                  # accounts written before the euro account existed
        state.setdefault('basket_spec', [list(x) for x in MIX])
        setup = SETUP.get(name) if name else None
        spec = [list(x) for x in setup['basket_spec']] if setup else None
        if spec and state['basket_spec'] != spec and not state['positions'] and not state.get('pending'):
            # a flat account follows a later change of its basket (26 Nov 2026: SpaceX and Anthropic in the MOVE
            # account); an account that holds or has an order keeps the basket it bought with
            state['basket_spec'] = spec
            if setup.get('basket'):
                state['basket'] = setup['basket']
            state.setdefault('rule_changes', []).append(dict(date=datetime.now(timezone.utc).date().isoformat(),
                                                             change='basket: ' + (setup.get('basket') or str(spec))))
        return state
    if state.get('positions'):
        raise ValueError('cannot change the rule of an account that holds positions')
    state.pop('hold', None)
    state.update(schema='index-leaders-v2', level=level, currency='USD', basket_spec=[list(x) for x in MIX], **RULES)
    state.setdefault('rule_changes', []).append(dict(date='2026-11-24', change='mixed basket (top 10 + RSP), '
                                                     'hold at least 42 months then sell in euphoria; no max hold'))
    return state


def value(state, prices, day):
    """Cash plus positions at the closes of `day` (last known close when a stock has none that day), in the
    account's currency: USD positions of a euro account are converted at that day's EUR/USD close."""
    usd = 0.
    for symbol, p in state['positions'].items():
        series = prices.get(symbol) or {}
        known = [d for d in series if d <= day]
        usd += p['shares'] * (series[max(known)] if known else p['entry'])
    if state.get('currency', 'USD') == 'EUR' and state['positions']:
        rate = _fx(prices, day) or state.get('fx_buy')
        usd /= rate
    return state['cash'] + usd


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
            spec = state.get('basket_spec') or [list(x) for x in MIX]
            picks = [(s_, w) for s_, w in holdings() if w and w > 0 and (prices.get(s_) or {}).get(day)][:TOP]
            total_w = sum(w for _, w in picks)
            fixed = [(sym, share) for sym, share in spec if sym != 'top10']
            top_share = sum(share for sym, share in spec if sym == 'top10')
            euro = state.get('currency', 'USD') == 'EUR'
            rate = (prices.get(FX) or {}).get(day) if euro else 1.
            ready = (picks and total_w > 0 and rate and all((prices.get(sym) or {}).get(day) for sym, _ in fixed))
            if ready:
                usd = state['cash'] * rate                     # a euro account converts at this close
                # The same symbol can be an index holding and a fixed allocation.
                index_weights = {}
                for symbol, weight in picks:
                    index_weights[symbol] = index_weights.get(symbol, 0.) + weight
                allocations = {s: top_share * w / total_w for s, w in index_weights.items()}
                for symbol, share in fixed:
                    allocations[symbol] = allocations.get(symbol, 0.) + share
                spent = 0.
                for symbol, share in allocations.items():
                    px = prices[symbol][day]
                    # Debit only the six-decimal quantity booked, including its buy fee.
                    shares = floor(usd * share / (px * (1 + COST)) * 1_000_000) / 1_000_000
                    index_weight = index_weights.get(symbol)
                    state['positions'][symbol] = dict(shares=shares, entry=px, account_share=round(share, 6),
                                                      index_weight=None if index_weight is None else round(index_weight, 6))
                    spent += shares * px * (1 + COST)
                state['cash'] = round((usd - spent) / rate, 6)
                state.update(bought=day, signal=pending['signal'], sessions_held=0, pending=None,
                             fx_buy=rate if euro else None)
                state['done_signals'].append(pending['signal'])
                events.append(dict(type='BUY', date=day, signal=pending['signal'], heat=pending['heat'],
                                   heat_close=heat.get(day), symbols=list(allocations),
                                   **({'eurusd': rate} if euro else {})))
        elif state['positions']:
            state['sessions_held'] = state.get('sessions_held', 0) + 1
            # Sell at this close when the previous close was euphoric and the account had then held 42 months.
            euphoric = (prev is not None and (heat.get(prev) or 0) >= EUPHORIA and prev > state['bought']
                        and state['sessions_held'] - 1 >= state.get('min_hold', MIN_HOLD))
            if euphoric or state.get('selling'):
                # The decision holds until every position has a close to sell at.
                state['selling'] = state.get('selling') or 'EUPHORIA_AFTER_42_MONTHS'
                proceeds = 0.
                euro = state.get('currency', 'USD') == 'EUR'
                rate = (prices.get(FX) or {}).get(day) if euro else 1.
                for symbol, p in state['positions'].items():
                    px = (prices.get(symbol) or {}).get(day)
                    if px is None or not rate:           # no close (or no EUR/USD) today: try tomorrow
                        break
                    proceeds += p['shares'] * px * (1 - COST)
                else:
                    why = state['selling']
                    proceeds /= rate                      # in the account's currency
                    start_value = (sum(p['shares'] * p['entry'] * (1 + COST) for p in state['positions'].values())
                                   / (state.get('fx_buy') or 1.))
                    state['trades'].append(dict(signal=state['signal'], bought=state['bought'], sold=day, why=why,
                                                symbols=sorted(state['positions']), cost=round(start_value, 2),
                                                proceeds=round(proceeds, 2),
                                                ret=round(proceeds / start_value - 1, 6) if start_value else None))
                    state['cash'] = round(state['cash'] + proceeds, 6)
                    state['positions'] = {}
                    state.update(bought=None, signal=None, sessions_held=0, selling=None, fx_buy=None)
                    events.append(dict(type='SELL', date=day, why=why))
        if pending and pending['date'] <= day and state.get('pending'):
            state['pending'] = None                 # unfilled (a missing close): decided again on the next day
        state['marks'].append(dict(date=day, equity=round(value(state, prices, day), 2), heat=heat.get(day)))
    return events


def decide(state, sessions, heat, today, heat_now, move_now=None):
    """Before the close of `today`: leave a buy order for today's close if the thermometer is still under the
    account's level now (heat_now, from intraday prices) and the current episode has not bought yet.

    sessions/heat are completed closes before today. The episode is the last first-panic close (one per 63
    sessions, panic_backtest.signals) within the last 63 sessions. An account with move_max buys only while the MOVE
    index is at most that many points above its three-year mean (move_now); unknown MOVE means no buy, and the
    episode stays open for a later session. Returns the order or None."""
    import panic_backtest as pb
    import pandas as pd
    if (state.get('pending') or {}).get('date') == today:
        state['pending'] = None               # the last check before the close decides; an earlier one is replaced
    level = state.get('level', pb.PANIC)
    if state['positions'] or heat_now is None or heat_now >= level:
        return None
    if state.get('move_max') is not None and (move_now is None or move_now > state['move_max']):
        return None
    series = pd.Series({pd.Timestamp(d): heat[d] for d in sessions if heat.get(d) is not None}, dtype=float)
    entries = [str(d.date()) for d in pb.signals(series, panic=level)[0]] if len(series) else []
    recent = [d for d in entries if d in sessions[-pb.GAP:] and d >= state.get('start', '')]
    if not recent or recent[-1] in state['done_signals'] or recent[-1] >= today:
        return None
    state['pending'] = dict(date=today, signal=recent[-1], heat=round(float(heat_now), 2),
                            **({'move_excess': round(float(move_now), 1)} if move_now is not None else {}),
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
    held = {s for s, _, _ in holdings['SPY'][:TOP]} | {EQUAL_WEIGHT, FX}
    for name, level, path in ACCOUNTS:
        state = load(path, start='', level=level, name=name)
        held |= set(state['positions']) | {sym for sym, _ in (state.get('basket_spec') or []) if sym != 'top10'}
    held = sorted(held)
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


def move_excess(today=None, intraday=False, download=None):
    """{date: MOVE points above its trailing three-year mean}; today's quote counts intraday."""
    import pandas as pd
    if download is None:
        import yfinance as yf
        raw = yf.download('^MOVE', period='6y', auto_adjust=False, progress=False, threads=False)['Close']
    else:
        raw = download()
    raw = raw.iloc[:, 0] if isinstance(raw, pd.DataFrame) else raw
    raw.index = raw.index.tz_localize(None) if raw.index.tz is not None else raw.index
    raw = raw[raw.index < session_cutoff(today, intraday)].dropna()
    ex = (raw - raw.rolling(MOVE_WINDOW, min_periods=MOVE_WINDOW // 2).mean()).dropna()
    return {str(d.date()): round(float(v), 2) for d, v in ex.items()}


def _move_now(day, intraday=False):
    try:
        return move_excess(intraday=intraday).get(day)
    except Exception as exc:                  # no MOVE: the MOVE account does not buy, the others are unaffected
        print(f'MOVE unavailable: {type(exc).__name__}')
        return None


def load(path=STATE, start=None, level=20., name=None):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return fresh(start, level, name)


def _accounts(start=FIRST_START):
    for name, level, path in ACCOUNTS:
        yield name, level, path, upgrade(load(path, start=start, level=level, name=name), level, name)


def run(latest=LATEST, collect_fn=None, move_fn=None):
    sessions, heat, prices, holdings = (collect_fn or collect)()
    events = {}
    for name, _, path, state in _accounts():
        events[name] = advance(state, sessions[-130:], heat, prices,
                               lambda: [(s, w) for s, w, _ in holdings['SPY'][:TOP]])
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(state, indent=1) + '\n', encoding='utf-8')
    last = sessions[-1]
    try:
        previous = json.loads(Path(latest).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        previous = {}
    snapshot = dict(schema='index-leaders-latest-v1', as_of=datetime.now(timezone.utc).isoformat(timespec='minutes'),
                    session=last, heat=heat.get(last), move_excess=(move_fn or _move_now)(last), heat_recent=[[d, heat[d]] for d in sessions[-30:] if d in heat],
                    holdings={fund: [dict(symbol=s, weight=w, name=n) for s, w, n in rows]
                              for fund, rows in holdings.items()},
                    events=events,
                    # latest closes of everything an account holds, and EUR/USD, so the page can value each position
                    prices={sym: [max(series), series[max(series)]] for sym, series in prices.items() if series})
    # the intraday readings are dated records of their own; the close run keeps them (it used to drop the morning
    # reading and the pre-close decision from the page, 27 Nov 2026)
    for key in ('morning', 'intraday'):
        if previous.get(key):
            snapshot[key] = previous[key]
    Path(latest).parent.mkdir(parents=True, exist_ok=True)
    Path(latest).write_text(json.dumps(snapshot, indent=1) + '\n', encoding='utf-8')
    print(json.dumps(dict(session=last, heat=heat.get(last), events=events), indent=1))


def _fourth_thursday_of_november(year):
    from datetime import date as _date
    first = _date(year, 11, 1)
    return first.toordinal() + (3 - first.weekday()) % 7 + 21


def close_minutes(day):
    """Regular NYSE close in New York minutes: 13:00 on the early-close days (the day after Thanksgiving,
    24 December and 3 July when they are weekdays), otherwise 16:00. Full holidays are found by the data:
    a day without a session never reaches a decision."""
    from datetime import date as _date
    day = _date.fromisoformat(str(day)[:10])
    early = (day.toordinal() == _fourth_thursday_of_november(day.year) + 1
             or (day.month, day.day) == (12, 24) or (day.month, day.day) == (7, 3))
    return 13 * 60 if early and day.weekday() < 5 else 16 * 60


OPEN_MINUTES = 9 * 60 + 30
MORNING = (55, 90)            # minutes after the open: the morning reading (about one hour into the session)
PRE_CLOSE = (50, 5)           # minutes before the close: the window in which the last check decides


def window(now):
    """'morning', 'pre-close' or None for a New York timestamp."""
    minutes = now.hour * 60 + now.minute
    close = close_minutes(now.date())
    if close - PRE_CLOSE[0] <= minutes <= close - PRE_CLOSE[1]:
        return 'pre-close'
    if OPEN_MINUTES + MORNING[0] <= minutes <= OPEN_MINUTES + MORNING[1]:
        return 'morning'
    return None


def decide_run(latest=LATEST, now=None, collect_fn=None, move_fn=None):
    """Intraday thermometer. About one hour after the open it is only recorded (the morning reading, no
    order: the rule buys on the reading shortly before the close). Shortly before the close, the regular
    16:00 or an early 13:00 close, it decides whether today's close buys."""
    import pandas as pd
    now = now or pd.Timestamp.now(tz='America/New_York')
    when = window(now)
    if when is None:
        print(json.dumps(dict(now=now.isoformat(timespec='minutes'), decision='outside the morning and pre-close windows')))
        return None
    sessions, heat, _, _ = (collect_fn or collect)(intraday=True)
    today = str(now.date())
    if not sessions or sessions[-1] != today:
        print(json.dumps(dict(today=today, decision='no session today')))
        return None
    heat_now = heat.get(today)
    move_now = (move_fn or (lambda d: _move_now(d, intraday=True)))(today)
    try:
        snapshot = json.loads(Path(latest).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        snapshot = {}
    checked_at = datetime.now(timezone.utc).isoformat(timespec='minutes')
    if when == 'morning':
        levels = {name: level for name, level, _ in ACCOUNTS}
        snapshot['morning'] = dict(date=today, heat=heat_now, move_excess=move_now, checked_at=checked_at,
                                   under={k: heat_now is not None and heat_now < v for k, v in levels.items()})
        order = None
    else:
        orders = {}
        for name, _, path, state in _accounts():
            orders[name] = decide(state, sessions[:-1][-130:], heat, today, heat_now, move_now)
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_text(json.dumps(state, indent=1) + '\n', encoding='utf-8')
        order = orders
        snapshot['intraday'] = dict(date=today, heat=heat_now, move_excess=move_now,
                                    orders={k: bool(v) for k, v in orders.items()},
                                    order=any(orders.values()), checked_at=checked_at)
    Path(latest).parent.mkdir(parents=True, exist_ok=True)
    Path(latest).write_text(json.dumps(snapshot, indent=1) + '\n', encoding='utf-8')
    print(json.dumps(dict(today=today, check=when, heat_now=heat_now, order=order), indent=1))
    return order


# ------------------------------------------------------------------ page
YELLOW = '#f5d000'
BAND_COLOURS = (('Panic', '#0b6b2b'), ('Fear', '#7fb07f'), ('Neutral', '#c8c6b8'), ('Greed', '#7a4a0a'),
                ('Euphoria', '#8f2525'))


def _pct(x, digits=2):
    return '—' if x is None else f'{100 * x:.{digits}f}%'


def render(snapshot, states, backtest=None):
    """states: [(name, level, state)] of the paper accounts."""
    import market_pulse
    from war_scenario import shell
    h = snapshot.get('heat')
    band = market_pulse.band(h)
    colour = dict(BAND_COLOURS).get(band, '#c8c6b8')
    bar = ''.join(f'<span style="background:{c}"></span>' for _, c in BAND_COLOURS)
    buy = h is not None and h < 20
    intraday = snapshot.get('intraday') or {}
    morning = snapshot.get('morning') or {}
    status = (f'<b style="color:{YELLOW}">PANIC · buy signal</b>: the accounts buy at a following close if the '
              'thermometer is still under their level (20 or 17) shortly before that close.' if buy else
              'No panic: the accounts do not buy. After a panic close they buy half the ten largest S&amp;P 500 '
              'companies by weight and half RSP (equal weight) at a following close, only if the thermometer is still '
              'under their level (20 or 17) shortly before it; they hold at least 42 months and then sell at the close '
              'after the first euphoria close (80 or more).')
    recent = ''.join(f'<span title="{escape(d)}: {v:.1f}" style="display:inline-block;width:8px;height:{max(3, v)}px;'
                     f'margin-right:2px;vertical-align:bottom;background:'
                     f'{dict(BAND_COLOURS).get(market_pulse.band(v), "#888")}"></span>'
                     for d, v in snapshot.get('heat_recent', []))
    parts = [f'<style>{market_pulse.CSS}</style>', f'<h1 style="color:{YELLOW}">Panic &amp; index leaders</h1>',
             '<div class="note">The market thermometer (the scoreboard\'s crash and panic gauge) next to the '
             'largest companies of the S&amp;P 500 and the Nasdaq-100 by index weight. Four paper accounts buy in a '
             'panic: under 20 and under 17 with half the ten largest S&amp;P 500 companies weighted as in the index '
             'and half RSP (equal weight), a third under 17 that adds 15% SpaceX and 15% Anthropic (25,000 EUR, '
             'no backtest), and a fourth under 20 that buys only while bond stress is not high (MOVE at most 15 '
             'points above its 3-year mean) with the same 15% SpaceX and 15% Anthropic (10,000 USD; experimental). All hold at least 42 months, then sell after the first close in extreme euphoria (80 or '
             'more). The backtest since 2000 found falls of up to 57% while held. Paper '
             'only; not advice.</div>',
             '<div class="box pulse-thermo"><h2>Thermometer</h2>'
             f'<span class="pulse-big" style="color:{colour}">{"—" if h is None else format(h, ".1f")}</span> /100 · '
             f'<b>{escape(band or "—")}</b> · close of {escape(snapshot.get("session") or "—")}'
             f'<div class="pulse-bar">{bar}<i class="pulse-marker" style="left:{0 if h is None else h:.1f}%"></i></div>'
             '<small>Panic · buy — Fear — Neutral — Greed — Euphoria · sell</small>'
             f'<p>{status}</p>'
             + (f'<p>Intraday check {escape(intraday["date"])} ({escape(intraday.get("checked_at", ""))} UTC): '
                f'thermometer {"—" if intraday.get("heat") is None else format(intraday["heat"], ".1f")} → '
                f'{"<b>buy order for the close</b>" if intraday.get("order") else "no buy order"}'
                + ''.join(f' · under {k}: {"order" if v else "none"}' for k, v in (intraday.get('orders') or {}).items())
                + '</p>'
                if intraday.get('date') else '')
             + (f'<p>Morning reading {escape(morning["date"])} ({escape(morning.get("checked_at", ""))} UTC, '
                'about one hour after the open; recorded only, no order): thermometer '
                f'{"—" if morning.get("heat") is None else format(morning["heat"], ".1f")}'
                + ''.join(f' · under {k}: {"yes" if v else "no"}' for k, v in (morning.get('under') or {}).items())
                + '</p>' if morning.get('date') else '')
             + _move_html(snapshot.get('move_excess'))
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
    parts.append(accounts_html(states, snapshot, intraday))
    if backtest:
        parts.append('<h2>Backtest</h2><div class="note">From the last backtest run (backtest.html, section '
                     '"Thermometer Panic · buy"); six panic episodes since 2015, so treat it as a hint, not proof.'
                     '</div>' + backtest)
    return shell('Panic & index leaders', ''.join(parts))


def _move_html(move):
    """Bond-market stress next to the thermometer (panic study, 26 Nov 2026)."""
    if move is None:
        return '<p>MOVE (bond volatility) vs its 3-year mean: —</p>'
    high = move > 15
    return (f'<p>MOVE (bond volatility): <b style="color:{"#ff6b6b" if high else "#66e39c"}">{move:+.1f}</b> points vs '
            'its 3-year mean. ' + ('<b>High bond stress</b>: in the panic study since 2002, buys with MOVE above +15 '
            '(2008, 2015, 2020, 2022) averaged −4% after 12 months and fell up to −57% while held, yet all beat the '
            'S&amp;P 500 after 42 months. The MOVE account waits.' if high else
            'Not high: in the panic study, buys with MOVE at or below +15 averaged +24% to +36% after 12 months.')
            + '</p>')


ACCOUNT_STYLE = {'20': ('#f5d000', 'Buys under 20', ''),
                 '17': ('#ff9d2e', 'Buys under 17', ''),
                 '17-spcx-ant': ('#b57bff', 'Buys under 17 · SpaceX + Anthropic',
                                 'No backtest · the user\'s conviction'),
                 '20-move': ('#2ec4b6', 'Buys under 20 · only if MOVE ≤ +15 · SpaceX + Anthropic',
                             'Experimental · backtest: the filter would have skipped 5 winners')}
CARD_CSS = '''
.acc-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px;margin:18px 0}
.acc{border:2px solid var(--acc);border-radius:12px;padding:14px 16px;background:#11161f}
.acc h3{margin:0 0 4px;color:var(--acc);font-size:18px}
.acc .tag{display:inline-block;margin:2px 0 8px;padding:2px 8px;border-radius:999px;background:var(--acc);color:#111;
  font-size:12px;font-weight:700}
.acc .state{font-size:22px;font-weight:800;margin:6px 0}
.acc .state.cash{color:#cfd6e4}.acc .state.inv{color:#66e39c}
.acc dl{display:grid;grid-template-columns:auto 1fr;gap:3px 12px;margin:8px 0 0;font-size:14px}
.acc dt{color:#9aa3b5}.acc dd{margin:0;font-variant-numeric:tabular-nums;font-weight:600}
.acc .gap{font-weight:700}.acc .gap.near{color:#ff6b6b}
.acc-detail{border-left:4px solid var(--acc);padding-left:12px;margin:18px 0}
.acc-detail h3{color:var(--acc)}
.up{color:#66e39c}.down{color:#f06a6a}
'''


def accounts_html(states, snapshot, intraday):
    """Three colour-coded cards side by side, then each account's positions and trades in its own colour."""
    h = snapshot.get('heat')
    prices = snapshot.get('prices') or {}
    fx = (prices.get(FX) or [None, None])[1]
    orders = intraday.get('orders') or {}
    cards, details = [], []
    for name, level, state in states:
        colour, title, tag = ACCOUNT_STYLE.get(name, ('#9aa3b5', f'Buys under {level:g}', ''))
        cur = state.get('currency', 'USD')
        euro = cur == 'EUR'
        equity = state['marks'][-1]['equity'] if state.get('marks') else state.get('capital')
        capital = state.get('capital', CAPITAL)
        invested = bool(state.get('positions'))
        gap = None if h is None else h - level
        rows = []
        for sym, p in sorted(state.get('positions', {}).items(), key=lambda kv: -kv[1].get('account_share', 0)):
            last = (prices.get(sym) or [None, None])[1]
            rate = (state.get('fx_buy') or 1.) if euro else 1.
            cost = p['shares'] * p['entry'] * (1 + COST) / rate
            now = None if last is None else p['shares'] * last / ((fx or rate) if euro else 1.)
            pnl = None if now is None else now - cost
            rows.append(f'<tr><td class="mono"><b>{escape(sym)}</b></td><td>{escape(state["bought"] or "")}</td>'
                        f'<td class="mono">{p["shares"]:,.4f}</td><td class="mono">{p["entry"]:,.2f} USD</td>'
                        f'<td class="mono">{cost:,.2f} {cur}</td>'
                        f'<td class="mono">{"—" if last is None else format(last, ",.2f") + " USD"}</td>'
                        f'<td class="mono">{"—" if now is None else format(now, ",.2f") + " " + cur}</td>'
                        f'<td class="mono {"up" if (pnl or 0) >= 0 else "down"}">'
                        f'{"—" if pnl is None else format(pnl, "+,.2f") + " " + cur}</td>'
                        f'<td class="mono">{_pct(p.get("account_share"), 1)}</td></tr>')
        result = equity / capital - 1 if capital else None
        cards.append(
            f'<div class="acc" style="--acc:{colour}"><h3>{escape(title)}</h3>'
            + (f'<span class="tag">{escape(tag)}</span>' if tag else '')
            + f'<div class="state {"inv" if invested else "cash"}">{"INVESTED" if invested else "IN CASH · waiting"}</div>'
            '<dl>'
            f'<dt>Value</dt><dd>{equity:,.2f} {cur} <span class="{"up" if (result or 0) >= 0 else "down"}">'
            f'({_pct(result, 1)})</span></dd>'
            f'<dt>Start capital</dt><dd>{capital:,.0f} {cur}</dd>'
            f'<dt>Cash</dt><dd>{state.get("cash", 0):,.2f} {cur}</dd>'
            f'<dt>Buys when</dt><dd>thermometer &lt; {level:g} shortly before the close</dd>'
            + ('' if invested else
               f'<dt>Thermometer now</dt><dd class="gap {"near" if gap is not None and gap < 5 else ""}">'
               f'{"—" if h is None else format(h, ".1f")}'
               f'{"" if gap is None else (" · " + format(gap, ".1f") + " points to go" if gap > 0 else " · in buy zone")}</dd>')
            + (f'<dt>Holding since</dt><dd>{escape(state["bought"])} · session {state.get("sessions_held", 0)} of ≥'
               f'{state.get("min_hold", MIN_HOLD)}</dd>' if invested else '')
            + (f'<dt>Last intraday check</dt><dd>{escape(intraday.get("date", ""))}: '
               f'{"BUY ORDER" if orders.get(name) else "no order"}</dd>' if name in orders else '')
            + f'<dt>Basket</dt><dd style="font-weight:400">{escape(state.get("basket") or "")}</dd>'
            + '</dl></div>')
        trades = ''.join(f'<tr><td>{escape(t["signal"])}</td><td>{escape(t["bought"])}</td><td>{escape(t["sold"])}</td>'
                         f'<td class="mono">{_pct(t["ret"], 1)}</td></tr>' for t in state.get('trades', []))
        details.append(
            f'<div class="acc-detail" style="--acc:{colour}"><h3>{escape(title)} · positions</h3>'
            + (f'<div class="tw"><table><thead><tr><th>Symbol</th><th>Bought</th><th>Units</th><th>Buy price</th>'
               f'<th>Cost</th><th>Last price</th><th>Value now</th><th>Gain / loss</th><th>Share at buy</th></tr></thead>'
               f'<tbody>{"".join(rows)}</tbody></table></div>' if rows else
               '<p class="muted">No positions yet: the account is in cash until the next panic.</p>')
            + (f'<div class="tw"><table><thead><tr><th>Signal</th><th>Bought</th><th>Sold</th><th>Return</th></tr>'
               f'</thead><tbody>{trades}</tbody></table></div>' if trades else '')
            + '</div>')
    return (f'<style>{CARD_CSS}</style><h2>The three paper accounts</h2><div class="acc-grid">' + ''.join(cards)
            + '</div>' + ''.join(details))


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


def history_html(root):
    """Twelve-month results of every basket after the panic signals since 2000 (backtests/panic_history.json)."""
    try:
        result = json.loads((Path(root) / 'backtests' / 'panic_history.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return ''
    names = dict(top10_weight='Top 10 by weight (this account)', leaders='Leaders (&lt;20% off their high)',
                 broken='Broken (20–40% off)', busted='Busted (&gt;40% off)', all_members='All members, equal weight',
                 mix='Half top 10, half all members', spx='S&amp;P 500')
    blocks = []
    for h, label in (('63', '3 months'), ('252', '12 months'), ('378', '18 months'), ('882', '42 months')):
        cells = (result.get('summary') or {}).get(h) or {}
        rows = ''.join(f'<tr><td>{names[k]}</td><td>{c["n"]}</td><td class="mono">{_pct(c["mean"], 1)}</td>'
                       f'<td class="mono">{_pct(c["median"], 1)}</td><td class="mono">{_pct(c["worst"], 1)}</td>'
                       f'<td>{"—" if k == "spx" else str(c["beats_spx"]) + "/" + str(c["n"])}</td></tr>'
                       for k, c in cells.items() if k in names)
        if rows:
            blocks.append(f'<h3>{label} after the buy</h3><div class="tw"><table><thead><tr><th>Basket</th>'
                          '<th>Signals</th><th>Mean</th><th>Median</th><th>Worst</th><th>Beats S&amp;P</th></tr></thead>'
                          f'<tbody>{rows}</tbody></table></div>')
    if not blocks:
        return ''
    events = ''.join(f'<tr><td>{escape(e["date"])}</td><td>{e["heat"]}</td>'
                     f'<td class="mono">{_pct((e["returns"].get("252") or {}).get("top10_weight"), 1)}</td>'
                     f'<td class="mono">{_pct((e["returns"].get("252") or {}).get("busted"), 1)}</td>'
                     f'<td class="mono">{_pct((e["returns"].get("252") or {}).get("spx"), 1)}</td>'
                     f'<td>{escape(e["basis"])}</td></tr>' for e in result.get('events', []))
    return ('<h2>Panic buys since 2000</h2><div class="note">Every first panic close since '
            f'{escape(result.get("start", ""))}, with the S&amp;P 500 members of that day (survivorship: members '
            'without Yahoo prices are left out, so early "busted" baskets look better than they were). '
            'Details in backtests/panic_history.md.</div>' + ''.join(blocks)
            + '<h3>Every signal (12 months)</h3><div class="tw"><table><thead><tr><th>Signal</th><th>Heat</th>'
            '<th>Top 10</th><th>Busted</th><th>S&amp;P 500</th><th>Weights</th></tr></thead>'
            f'<tbody>{events}</tbody></table></div>')


def site_pages(root):
    try:
        snapshot = json.loads((Path(root) / 'index-leaders' / 'latest.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return []
    states = [(name, level, load(Path(root) / 'paper_trades' / Path(path).name, start='', level=level, name=name))
              for name, level, path in ACCOUNTS]
    return [(Path(PAGE), render(snapshot, states, backtest_html(root) + history_html(root)))]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--decide', action='store_true', help='before the close: intraday thermometer, buy order')
    if parser.parse_args().decide:
        decide_run()
    else:
        run()
