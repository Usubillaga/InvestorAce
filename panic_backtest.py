"""The market thermometer's "Panic · buy" signal, and buying the leaders when it fires (asked for on 23 Nov 2026).

On Friday 20 Nov 2026 the thermometer (market_pulse.py) read 15.4: VIX 35.89 (score 13.7), S&P 500 5.96% under
its 200-day average (20.2) and 9.37% under its 50-day (0.0), 27.6% of the universe above its own 200-day (27.6).
Under 20 the band is Panic, which the page labels "buy". CNN's Fear & Greed was not available that day, so the
thermometer is the mean of those four scores, each rebuilt here exactly as market_pulse.summarize scores it.

Signals:
* panic_entry: the first close under 20 after at least GAP sessions without one (one signal per panic episode).
* panic_exit: the first close back at or above 20 after such an episode (waits for confirmation).

At each signal, bought at the next close and held 21/63/126/252 sessions:
* leader: the universe stock with the highest 21-day / 200-day average ratio (v1.6's ranking) on the signal day.
* top5: the five highest, equal weight.
* universe: every stock with a price, equal weight.
* spx: the S&P 500.
Costs 0.1% per side. Caveats: today's universe (survivorship flatters every stock basket, the leader most of all,
since a leader that later collapsed may be gone); signals overlap in time across horizons; few episodes. The test
compares the leader with the S&P 500 and the universe on the same dates. Research only; nothing is traded.
"""
import statistics

import numpy as np
import pandas as pd

PANIC = 20.
EUPHORIA = 80.            # market_pulse's Euphoria band
GAP = 63
HORIZONS = (21, 63, 126, 252)
COST = 0.001


def _clip(x):
    return x.clip(lower=0, upper=100)


def heat(spx, vix, close):
    """Daily thermometer from closes: the mean of the four market_pulse scores (no Fear & Greed)."""
    ma200, ma50 = spx.rolling(200).mean(), spx.rolling(50).mean()
    s200 = _clip(50 + 5 * 100 * (spx / ma200 - 1))
    s50 = _clip(50 + 10 * 100 * (spx / ma50 - 1))
    svix = _clip((40 - vix.reindex(spx.index).ffill()) / 30 * 100)
    sma = close.rolling(200).mean()
    valid = sma.notna() & close.notna()
    share = 100 * ((close > sma) & valid).sum(axis=1) / valid.sum(axis=1).where(valid.sum(axis=1) >= 20)
    frame = pd.concat([s200, s50, svix, share.reindex(spx.index)], axis=1)
    return frame.mean(axis=1).where(frame.notna().sum(axis=1) >= 3)   # as live: a mean of at least 3 scores


def signals(h, panic=PANIC, gap=GAP):
    """(entries, exits): dates of the first panic close per episode and of the first close back above."""
    entries, exits, last_panic, open_episode = [], [], None, False
    for i, (day, v) in enumerate(h.items()):
        if np.isnan(v):
            continue
        if v < panic:
            if last_panic is None or i - last_panic > gap:
                entries.append(day)
                open_episode = True
            last_panic = i
        elif open_episode:
            exits.append(day)
            open_episode = False
    return entries, exits


def _ret(series, i, h):
    if i + h >= len(series):
        return None
    a, b = series.iloc[i], series.iloc[i + h]
    if not (np.isfinite(a) and np.isfinite(b)) or a <= 0:
        return None
    return float(b / a * (1 - COST) / (1 + COST) - 1)


def outcomes(day, close, mad, spx, horizons=HORIZONS):
    """Returns after buying at the close after `day`."""
    pos = close.index.get_loc(day)
    if pos + 1 >= len(close.index):
        return None
    ranked = mad.loc[day].dropna().sort_values(ascending=False)
    if ranked.empty:
        return None
    leader, top5 = ranked.index[0], list(ranked.index[:5])
    out = dict(date=str(day.date()), leader=leader, top5=top5, returns={})
    i = pos + 1
    spx_i = spx.index.get_loc(close.index[i])
    for h in horizons:
        r = dict(leader=_ret(close[leader], i, h),
                 top5=_mean([_ret(close[s], i, h) for s in top5]),
                 universe=_mean([_ret(close[s], i, h) for s in close.columns]),
                 spx=_ret(spx, spx_i, h))
        out['returns'][str(h)] = r
    return out


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return float(np.mean(xs)) if xs else None


def summary(events, horizons=HORIZONS):
    out = {}
    for h in horizons:
        rows = [e['returns'][str(h)] for e in events if e and all(e['returns'][str(h)][k] is not None
                                                                   for k in ('leader', 'top5', 'universe', 'spx'))]
        if not rows:
            out[str(h)] = dict(n=0)
            continue
        cell = dict(n=len(rows))
        for k in ('leader', 'top5', 'universe', 'spx'):
            xs = [r[k] for r in rows]
            cell[k] = dict(mean=statistics.fmean(xs), median=statistics.median(xs),
                           positive=sum(x > 0 for x in xs), worst=min(xs))
        cell['leader_beats_spx'] = sum(r['leader'] > r['spx'] for r in rows)
        cell['top5_beats_spx'] = sum(r['top5'] > r['spx'] for r in rows)
        out[str(h)] = cell
    return out


def study(frames, spx, vix):
    close = pd.DataFrame({s: f['close'] for s, f in frames.items()}).reindex(spx.index)
    mad = pd.DataFrame({s: f['mad'] for s, f in frames.items()}).reindex(spx.index)
    h = heat(spx, vix, close)
    entries, exits = signals(h)
    result = dict(last_heat=dict(date=str(h.dropna().index[-1].date()), value=round(float(h.dropna().iloc[-1]), 1))
                  if h.notna().any() else None,
                  euphoria_days=[str(d.date()) for d in h.index[(h >= EUPHORIA).to_numpy()]])
    last = h.dropna()
    if len(last) and last.iloc[-1] < PANIC:
        result['panic_today'] = str(last.index[-1].date())
    for name, days in (('panic_entry', entries), ('panic_exit', exits)):
        events = [e for e in (outcomes(d, close, mad, spx) for d in days) if e]
        for e in events:
            e['heat'] = round(float(h.loc[pd.Timestamp(e['date'])]), 1)
        result[name] = dict(events=events, summary=summary(events))
    return result


def _pct(x):
    return '—' if x is None else f'{100 * x:+.1f}%'


def report(result):
    lines = ['', '## Thermometer "Panic · buy": buy the leader', '',
             f'Signal: the thermometer (market_pulse.py, rebuilt without Fear & Greed) closes under {PANIC:g}; one '
             f'signal per episode ({GAP} sessions apart). Bought at the next close; 0.1% per side. Leader: highest '
             '21/200-day average ratio in the universe on the signal day; top5: the five highest. Today\'s universe, '
             'so stock baskets are flattered by survivorship.', '']
    if result.get('last_heat'):
        lines.append(f"Rebuilt thermometer on {result['last_heat']['date']}: {result['last_heat']['value']}.")
    for name, title in (('panic_entry', 'First panic close'), ('panic_exit', 'First close back above 20')):
        block = result.get(name) or {}
        lines += ['', f'### {title}', '',
                  '| Sessions | Signals | Leader mean / median | Top 5 mean / median | Universe mean | S&P 500 mean / median | '
                  'Leader beats S&P | Leader worst |', '|---:|---:|---|---|---:|---|---:|---:|']
        for h, c in (block.get('summary') or {}).items():
            if not c.get('n'):
                lines.append(f'| {h} | 0 | — | — | — | — | — | — |')
                continue
            lines.append(f"| {h} | {c['n']} | {_pct(c['leader']['mean'])} / {_pct(c['leader']['median'])} | "
                         f"{_pct(c['top5']['mean'])} / {_pct(c['top5']['median'])} | {_pct(c['universe']['mean'])} | "
                         f"{_pct(c['spx']['mean'])} / {_pct(c['spx']['median'])} | {c['leader_beats_spx']}/{c['n']} | "
                         f"{_pct(c['leader']['worst'])} |")
        lines += ['', 'Signals: ' + '; '.join(
            f"{e['date']} (heat {e['heat']}, leader {e['leader']}: 63 sessions {_pct(e['returns']['63']['leader'])}, "
            f"S&P {_pct(e['returns']['63']['spx'])})" for e in block.get('events', []))]
    return '\n'.join(lines) + '\n' + index_report(result)


def download_vix(period):
    import yfinance as yf
    raw = yf.download(['^VIX'], period=period, auto_adjust=False, progress=False, threads=False, group_by='column')
    s = raw['Close']['^VIX'].dropna().round(4)
    s.index = s.index.tz_localize(None) if s.index.tz is not None else s.index
    return s


# ------------------------------------------------------------------ index leaders, point in time
MEMBERS_URL = ('https://raw.githubusercontent.com/fja05680/sp500/master/'
               'S%26P%20500%20Historical%20Components%20%26%20Changes%20(Updated).csv')


def parse_members(text):
    """[(date, [tickers])] from the fja05680/sp500 file: S&P 500 members on each change date since 1996."""
    import csv
    import io
    rows = []
    for row in csv.DictReader(io.StringIO(text)):
        rows.append((pd.Timestamp(row['date']), [t.strip() for t in row['tickers'].split(',') if t.strip()]))
    return sorted(rows)


def members_on(rows, day):
    """Members on `day`: the last list dated on or before it (None when the file ends before `day`)."""
    last = None
    for date, tickers in rows:
        if date > day:
            break
        last = tickers
    if rows and day > rows[-1][0] + pd.Timedelta(days=120):
        return None                      # the file is too old to know the members on that day
    return last


def yahoo(ticker):
    return ticker.replace('.', '-')


def index_leaders(days, rows, close, spx, horizons=HORIZONS, top=(1, 5, 10)):
    """Point-in-time S&P 500 leaders at each signal day.

    close: daily closes for every ticker that was a member on any signal day (Yahoo symbols). Members without
    a price on the day (mostly delisted or acquired later) are counted, not guessed."""
    events = []
    for day in days:
        members = members_on(rows, day)
        if not members or day not in close.index:
            continue
        cols = [yahoo(t) for t in members if yahoo(t) in close.columns]
        hist = close.loc[:day, cols]
        sma21, sma200 = hist.iloc[-21:].mean(), hist.iloc[-200:].mean()
        ok = hist.iloc[-1].notna() & (hist.count() >= 200)
        strength = (sma21 / sma200)[ok].dropna().sort_values(ascending=False)
        if strength.empty:
            continue
        pos = close.index.get_loc(day)
        spx_pos = spx.index.get_loc(day) if day in spx.index else None
        event = dict(date=str(day.date()), members=len(members), priced=int(ok.sum()),
                     leaders=list(strength.index[:max(top)]), returns={})
        for h in horizons:
            cell = {}
            for n in top:
                rets = [_ret(close[s], pos + 1, h) for s in strength.index[:n]]
                cell[f'top{n}'] = _mean(rets)
            cell['all_members'] = _mean([_ret(close[s], pos + 1, h) for s in strength.index])
            cell['spx'] = _ret(spx, spx_pos + 1, h) if spx_pos is not None else None
            event['returns'][str(h)] = cell
        events.append(event)
    return events


def leader_summary(events, horizons=HORIZONS):
    out = {}
    for h in horizons:
        rows = [e['returns'][str(h)] for e in events if all(v is not None for v in e['returns'][str(h)].values())]
        cell = dict(n=len(rows))
        for k in (rows[0].keys() if rows else ()):
            xs = [r[k] for r in rows]
            cell[k] = dict(mean=statistics.fmean(xs), median=statistics.median(xs), positive=sum(x > 0 for x in xs),
                           worst=min(xs))
        if rows:
            cell['top1_beats_spx'] = sum(r['top1'] > r['spx'] for r in rows)
        out[str(h)] = cell
    return out


def index_study(result, rows, download, spx, shares=None):
    """Adds the point-in-time index leaders for the panic signals already in `result`."""
    for name in ('panic_entry', 'panic_exit'):
        days = [pd.Timestamp(e['date']) for e in result[name]['events']]
        tickers = sorted({yahoo(t) for d in days for t in (members_on(rows, d) or [])})
        if not tickers:
            continue
        panel = download(tickers)
        close = panel['Close'].reindex(spx.index)
        events = index_leaders(days, rows, close, spx)
        result[name]['index'] = dict(events=events, summary=leader_summary(events))
        if name == 'panic_entry' and shares is not None:
            volume = panel['Volume'].reindex(spx.index)
            wevents = weight_leaders(days, rows, close, volume, spx, shares)
            euphoria = [pd.Timestamp(d) for d in result.get('euphoria_days', [])]
            exits = exit_rules(wevents, close, spx, euphoria)
            result[name]['weights'] = dict(events=wevents, summary=weight_summary(wevents),
                                           exits=exits, exit_summary=exit_summary(exits))
    if result.get('panic_today'):
        day = pd.Timestamp(result['panic_today'])
        members = members_on(rows, day) or []
        close = download(sorted({yahoo(t) for t in members}))['Close'].reindex(spx.index)
        hist = close.loc[:day]
        ok = hist.iloc[-1].notna() & (hist.count() >= 200)
        strength = (hist.iloc[-21:].mean() / hist.iloc[-200:].mean())[ok].dropna().sort_values(ascending=False)
        result['leaders_today'] = dict(date=str(day.date()), members=len(members), priced=int(ok.sum()),
                                       leaders=[[s, round(float(v), 3)] for s, v in strength.iloc[:10].items()])
    return result


def download_closes(tickers, period):
    """{'Close', 'Volume'} panels (dividend-adjusted closes)."""
    import yfinance as yf
    raw = yf.download(tickers, period=period, auto_adjust=True, progress=False, threads=True, group_by='column')
    out = {}
    for field in ('Close', 'Volume'):
        frame = raw[field].round(4) if field == 'Close' else raw[field]
        frame.index = frame.index.tz_localize(None) if frame.index.tz is not None else frame.index
        out[field] = frame
    return out


# ------------------------------------------------------------------ leaders by index weight
CANDIDATES = 40           # the most traded members (63-day average dollar volume) whose market cap is looked up


def weight_leaders(days, rows, close, volume, spx, shares, horizons=HORIZONS, top=10, candidates=CANDIDATES):
    """The ten largest S&P 500 members by market cap on each signal day, bought in proportion to their cap.

    Market cap = close x shares outstanding reported on or before the day (shares(ticker, day) -> float or None).
    Only the most traded members are looked up (the largest companies are always among them); members whose
    shares are unknown are counted and left out."""
    events = []
    for day in days:
        members = members_on(rows, day)
        if not members or day not in close.index:
            continue
        cols = [yahoo(t) for t in members if yahoo(t) in close.columns]
        dollar = (close.loc[:day, cols].iloc[-63:] * volume.loc[:day, cols].iloc[-63:]).mean().dropna()
        pool = list(dollar.sort_values(ascending=False).index[:candidates])
        caps, missing = {}, []
        for t in pool:
            n = shares(t, day)
            px = close.at[day, t]
            if n and np.isfinite(px):
                caps[t] = float(px) * float(n)
            else:
                missing.append(t)
        ranked = sorted(caps.items(), key=lambda kv: -kv[1])[:top]
        if not ranked:
            continue
        total = sum(c for _, c in ranked)
        weights = {t: c / total for t, c in ranked}
        pos = close.index.get_loc(day)
        spx_pos = spx.index.get_loc(day) if day in spx.index else None
        event = dict(date=str(day.date()), leaders=[[t, round(w, 4)] for t, w in weights.items()],
                     looked_up=len(pool), missing_shares=missing, returns={})
        for h in horizons:
            parts = [(w, _ret(close[t], pos + 1, h)) for t, w in weights.items()]
            known = [(w, r) for w, r in parts if r is not None]
            wsum = sum(w for w, _ in known)
            event['returns'][str(h)] = dict(
                leaders=sum(w * r for w, r in known) / wsum if wsum > 0.8 else None,   # needs 80% of the weight
                spx=_ret(spx, spx_pos + 1, h) if spx_pos is not None else None)
        events.append(event)
    return events


EXIT_RULES = ('hold_63', 'euphoria', 'euphoria_after_63', 'euphoria_or_252')


def exit_rules(events, close, spx, euphoria, rules=EXIT_RULES):
    """The same cap-weighted buy with different exits, each against the S&P 500 over the same sessions.

    hold_63: 63 sessions. euphoria: the first close with the thermometer at or above 80 after the buy, however
    long that takes (still open at the end of the data = marked at the last close, flagged open).
    euphoria_after_63: the first such close at least 63 sessions after the buy. euphoria_or_252: the first such
    close, at most 252 sessions."""
    filled = close.ffill()
    idx = close.index
    eu = np.array(sorted(idx.get_indexer([d for d in euphoria if d in idx])))
    out = []
    for e in events:
        start = idx.get_loc(pd.Timestamp(e['date'])) + 1
        if start >= len(idx):
            continue
        weights = dict(e['leaders'])
        row = dict(date=e['date'], rules={})
        for rule in rules:
            after = eu[eu > start] if len(eu) else eu
            if rule == 'hold_63':
                end, open_ = start + 63, False
            elif rule == 'euphoria':
                end, open_ = (int(after[0]), False) if len(after) else (len(idx) - 1, True)
            elif rule == 'euphoria_after_63':
                later = after[after >= start + 63] if len(after) else after
                end, open_ = (int(later[0]), False) if len(later) else (len(idx) - 1, True)
            else:
                end, open_ = (int(after[0]), False) if len(after) and after[0] <= start + 252 else (start + 252, False)
            if end >= len(idx):
                end, open_ = len(idx) - 1, True
            parts = [(w, filled[t].iloc[end] / filled[t].iloc[start] * (1 - COST) / (1 + COST) - 1)
                     for t, w in weights.items() if np.isfinite(filled[t].iloc[start]) and np.isfinite(filled[t].iloc[end])]
            wsum = sum(w for w, _ in parts)
            spx_f = spx.reindex(idx).ffill()
            years = max((idx[end] - idx[start]).days / 365.25, 1 / 252)
            ret = sum(w * r for w, r in parts) / wsum if wsum > 0.8 else None
            spx_ret = float(spx_f.iloc[end] / spx_f.iloc[start] - 1)
            row['rules'][rule] = dict(exit=str(idx[end].date()), sessions=int(end - start), open=open_,
                                      ret=ret, spx=spx_ret,
                                      annual=(1 + ret) ** (1 / years) - 1 if ret is not None else None,
                                      spx_annual=(1 + spx_ret) ** (1 / years) - 1)
        out.append(row)
    return out


def exit_summary(rows, rules=EXIT_RULES):
    out = {}
    for rule in rules:
        cells = [r['rules'][rule] for r in rows if r['rules'].get(rule, {}).get('ret') is not None]
        if not cells:
            out[rule] = dict(n=0)
            continue
        out[rule] = dict(n=len(cells), open=sum(c['open'] for c in cells),
                         mean=statistics.fmean(c['ret'] for c in cells),
                         median=statistics.median(c['ret'] for c in cells),
                         spx_mean=statistics.fmean(c['spx'] for c in cells),
                         beats_spx=sum(c['ret'] > c['spx'] for c in cells),
                         sessions=statistics.median(c['sessions'] for c in cells),
                         worst=min(c['ret'] for c in cells))
    return out


def weight_summary(events, horizons=HORIZONS):
    out = {}
    for h in horizons:
        rows = [e['returns'][str(h)] for e in events if None not in e['returns'][str(h)].values()]
        if not rows:
            out[str(h)] = dict(n=0)
            continue
        out[str(h)] = dict(n=len(rows), beats_spx=sum(r['leaders'] > r['spx'] for r in rows),
                           **{k: dict(mean=statistics.fmean(r[k] for r in rows),
                                      median=statistics.median(r[k] for r in rows),
                                      worst=min(r[k] for r in rows)) for k in ('leaders', 'spx')})
    return out


def yahoo_shares(ticker, day):
    """Shares outstanding reported on or before `day` (Yahoo's share history), or None."""
    import yfinance as yf
    try:
        s = yf.Ticker(ticker).get_shares_full(start=(day - pd.Timedelta(days=550)).date(),
                                              end=(day + pd.Timedelta(days=1)).date())
    except Exception:
        return None
    if s is None or len(s) == 0:
        return None
    s.index = s.index.tz_localize(None) if getattr(s.index, 'tz', None) is not None else s.index
    s = s[s.index <= day + pd.Timedelta(days=1)]
    return float(s.iloc[-1]) if len(s) else None


def fetch_members(url=MEMBERS_URL):
    import urllib.request
    request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (InvestorAce backtest)'})
    with urllib.request.urlopen(request, timeout=60) as response:
        return parse_members(response.read().decode('utf-8'))


def index_report(result):
    if result.get('index_error'):
        return '\n### S&P 500 leaders, point in time\n\nNot computed: ' + result['index_error'] + '\n'
    lines = ['', '### S&P 500 leaders, point in time', '',
             'Members on the signal day from the fja05680/sp500 history (including companies that later left the '
             'index); leader = highest 21/200-day average ratio among members with 200 sessions of prices. Members '
             'without Yahoo prices (mostly delisted later) are counted and left out, so a little survivorship remains.']
    for name, title in (('panic_entry', 'First panic close'), ('panic_exit', 'First close back above 20')):
        block = (result.get(name) or {}).get('index')
        if not block:
            continue
        lines += ['', f'#### {title}', '',
                  '| Sessions | Signals | Leader mean / median | Top 5 mean | Top 10 mean | All members mean | S&P 500 mean | '
                  'Leader beats S&P | Leader worst |', '|---:|---:|---|---:|---:|---:|---:|---:|---:|']
        for h, c in block['summary'].items():
            if not c.get('n'):
                lines.append(f'| {h} | 0 | — | — | — | — | — | — | — |')
                continue
            lines.append(f"| {h} | {c['n']} | {_pct(c['top1']['mean'])} / {_pct(c['top1']['median'])} | "
                         f"{_pct(c['top5']['mean'])} | {_pct(c['top10']['mean'])} | {_pct(c['all_members']['mean'])} | "
                         f"{_pct(c['spx']['mean'])} | {c['top1_beats_spx']}/{c['n']} | {_pct(c['top1']['worst'])} |")
        lines += ['', 'Signals: ' + '; '.join(
            f"{e['date']} ({e['priced']}/{e['members']} members priced; leader {e['leaders'][0]}, 63 sessions "
            f"{_pct(e['returns']['63']['top1'])}; top 5 {', '.join(e['leaders'][:5])})" for e in block['events'])]
    w = (result.get('panic_entry') or {}).get('weights')
    if w:
        lines += ['', '#### Ten largest S&P 500 members by market cap, cap-weighted (first panic close)', '',
                  'Market cap = close x Yahoo shares outstanding on the day; looked up for the 40 most traded members. '
                  'This is the rule of the index-leaders paper account (index_leaders.py).', '',
                  '| Sessions | Signals | Top 10 by weight mean / median | S&P 500 mean / median | Beats S&P | Worst |',
                  '|---:|---:|---|---|---:|---:|']
        for h, c in w['summary'].items():
            if not c.get('n'):
                lines.append(f'| {h} | 0 | — | — | — | — |')
                continue
            lines.append(f"| {h} | {c['n']} | {_pct(c['leaders']['mean'])} / {_pct(c['leaders']['median'])} | "
                         f"{_pct(c['spx']['mean'])} / {_pct(c['spx']['median'])} | {c['beats_spx']}/{c['n']} | "
                         f"{_pct(c['leaders']['worst'])} |")
        lines += ['', 'Signals: ' + '; '.join(
            f"{e['date']} ({', '.join(f'{t} {100 * x:.0f}%' for t, x in e['leaders'][:5])}…; 63 sessions "
            f"{_pct(e['returns']['63']['leaders'])} vs S&P {_pct(e['returns']['63']['spx'])}"
            + (f"; no shares for {', '.join(e['missing_shares'])}" if e['missing_shares'] else '') + ')'
            for e in w['events'])]
    ex = ((result.get('panic_entry') or {}).get('weights') or {}).get('exit_summary')
    if ex:
        lines += ['', '#### Exit rules for the same buy (ten largest by weight)', '',
                  'hold_63 sells after 63 sessions; euphoria at the first thermometer close at or above 80 (however '
                  'long); euphoria_after_63 at the first such close after at least 63 sessions; euphoria_or_252 at the '
                  'first such close, at most 252 sessions. Open = no euphoria yet, marked at the last close.', '',
                  '| Exit | Signals | Still open | Median sessions held | Mean / median return | S&P 500 same span | '
                  'Beats S&P | Worst |', '|---|---:|---:|---:|---|---:|---:|---:|']
        for rule, c in ex.items():
            if not c.get('n'):
                lines.append(f'| {rule} | 0 | — | — | — | — | — | — |')
                continue
            lines.append(f"| {rule} | {c['n']} | {c['open']} | {c['sessions']:.0f} | {_pct(c['mean'])} / "
                         f"{_pct(c['median'])} | {_pct(c['spx_mean'])} | {c['beats_spx']}/{c['n']} | {_pct(c['worst'])} |")
        rows = ((result.get('panic_entry') or {}).get('weights') or {}).get('exits') or []
        lines += ['', 'Per signal (euphoria exit): ' + '; '.join(
            f"{r['date']} → {r['rules']['euphoria']['exit']} ({r['rules']['euphoria']['sessions']} sessions"
            f"{', open' if r['rules']['euphoria']['open'] else ''}): {_pct(r['rules']['euphoria']['ret'])} vs S&P "
            f"{_pct(r['rules']['euphoria']['spx'])}" for r in rows)]
    today = result.get('leaders_today')
    if today:
        lines += ['', f"Panic today ({today['date']}): S&P 500 leaders by the same ranking, members as of the latest "
                  f"list ({today['priced']}/{today['members']} priced): "
                  + ', '.join(f'{s} {v:.2f}' for s, v in today['leaders'])]
    return '\n'.join(lines) + '\n'
