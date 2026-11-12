"""Backtest of the technical trading rules on the InvestorAce universe.

What it can and cannot answer
-----------------------------
* It tests the TECHNICAL rules only. The InvestorAce label cannot be replayed:
  there is no history of labels, and using today's labels for past dates would
  look into the future. Every variant therefore trades the same universe without
  the label filter, so the variants differ only by the rule being tested.
* The universe is today's members, which were partly chosen for doing well
  (survivorship bias). This lifts all variants alike; compare variants with each
  other, not with the S&P 500.
* One five-year window is one market regime. Overlapping forward returns in the
  event study make naive t-statistics too optimistic, so none are reported.

Two parts:
1. Event study (the user's claims as stated): forward returns after a stock
   closes 30% or more above its 36-day average, and after breakouts above the
   prior high, split into breakouts that fail and those that hold.
2. Portfolio simulation: rules v1.5 (technical part) against variants that add
   the user's rules, with costs.

Runs in GitHub Actions (.github/workflows/backtest.yml), where Yahoo is reachable.
"""
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'backtests'
YEARS = 5
HISTORY_YEARS = 14
WINDOWS = (('2014-01-01', '2018-01-01'), ('2018-01-01', '2022-01-01'), ('2022-01-01', None))
WARMUP = 260
COST = 0.001
CAPITAL = 10000.
RESISTANCE_SESSIONS, BREAKOUT_GAP = 60, 5
EXT_LIMIT = 0.30            # the user's "more than 30% above the 36-day average"
BASE_SESSIONS, BASE_MAX_RANGE, BREAK_VOLUME, POP_VOLUME = 10, 0.12, 1.5, 1.2
FAIL_WINDOW = 10            # a breakout fails if it closes 3% under the old high within 10 sessions
HORIZONS = (5, 21, 63)


# ---------------------------------------------------------------- indicators
def indicators(close, high, low, volume=None):
    """Per-symbol frame of the levels the rules use; every value uses data up to that close only."""
    out = pd.DataFrame({'close': close})
    out['sma36'] = close.rolling(36).mean()
    out['sma50'] = close.rolling(50).mean()
    out['sma200'] = close.rolling(200).mean()
    out['sma21'] = close.rolling(21).mean()
    out['ema21'] = close.ewm(span=21, adjust=False).mean()
    out['ema10'] = close.ewm(span=10, adjust=False).mean()          # Oliver Kell's 10/20 EMAs
    out['ema20'] = close.ewm(span=20, adjust=False).mean()
    out['base_high'] = close.shift(1).rolling(BASE_SESSIONS).max()   # Kell's base: the prior 10 closes
    out['base_low'] = close.shift(1).rolling(BASE_SESSIONS).min()
    out['vol_ratio'] = (volume / volume.shift(1).rolling(50).mean()) if volume is not None else np.nan
    prev = close.shift(1)
    tr = pd.concat([high - low, (high - prev).abs(), (low - prev).abs()], axis=1).max(axis=1)
    out['atr'] = tr.ewm(alpha=1 / 14, adjust=False).mean()
    out['res'] = close.shift(BREAKOUT_GAP).rolling(RESISTANCE_SESSIONS).max()
    out['ext36'] = close / out['sma36'] - 1
    out['ext_atr'] = (close - out['ema21']) / out['atr']
    out['mad'] = out['sma21'] / out['sma200']
    above = close > out['res']
    out['prev_above'] = above.shift(1, fill_value=False)
    over = (close > out['ema10']) & (close > out['ema20'])
    out['ema_pop'] = over & ~over.shift(1, fill_value=False)        # Kell's wedge pop: back over both EMAs
    return out


# ---------------------------------------------------------------- event study
def _fwd(close, n):
    return close.shift(-n) / close - 1


def _drawdown_within(close, n):
    """Worst close in the next n sessions relative to today's close."""
    future = pd.concat([close.shift(-k) for k in range(1, n + 1)], axis=1)
    return future.min(axis=1) / close - 1


def event_study(frames, spx, start, end=None):
    rows = []
    spx_fwd = {n: _fwd(spx, n) for n in HORIZONS}
    for symbol, f in frames.items():
        d = f.loc[(f.index >= start) & ((f.index < end) if end is not None else True)].copy()
        if d.empty:
            continue
        for n in HORIZONS:
            d[f'fwd{n}'] = _fwd(f['close'], n).reindex(d.index)
            d[f'xs{n}'] = d[f'fwd{n}'] - spx_fwd[n].reindex(d.index)
        d['dd21'] = _drawdown_within(f['close'], 21).reindex(d.index)
        above = f['close'] > f['res']
        d['breakout'] = (above & ~above.shift(1, fill_value=False)).reindex(d.index)
        d['confirmed'] = (above & above.shift(1, fill_value=False)
                          & ~above.shift(2, fill_value=False)).reindex(d.index)
        lows = pd.concat([f['close'].shift(-k) for k in range(1, FAIL_WINDOW + 1)], axis=1).min(axis=1)
        d['failed'] = (lows < f['res'] * 0.97).reindex(d.index)
        d['near_res'] = ((f['close'] >= f['res'] * 0.97) & (f['close'] < f['res'])).reindex(d.index)
        d['uptrend'] = ((f['close'] > f['sma200']) & (f['close'] > f['sma50'])).reindex(d.index)
        d['symbol'] = symbol
        rows.append(d)
    data = pd.concat(rows).dropna(subset=['ext36', 'fwd63', 'sma200'])

    def summary(mask):
        s = data.loc[mask]
        out = dict(n=int(len(s)), stocks=int(s['symbol'].nunique()))
        for n in HORIZONS:
            out[f'fwd{n}_mean'] = _pct(s[f'fwd{n}'].mean())
            out[f'fwd{n}_median'] = _pct(s[f'fwd{n}'].median())
            out[f'xs{n}_mean'] = _pct(s[f'xs{n}'].mean())
        out['p_drop10_in_21'] = _pct((s['dd21'] <= -0.10).mean())
        out['p_negative_63'] = _pct((s['fwd63'] < 0).mean())
        return out

    bins = [(-1, 0), (0, .10), (.10, .20), (.20, .30), (.30, 10)]
    extension = {f'{int(lo * 100)}..{int(hi * 100) if hi < 10 else "+"}%': summary(
        (data['ext36'] > lo) & (data['ext36'] <= hi)) for lo, hi in bins}
    up = data['uptrend']
    breakouts = dict(
        all_uptrend_days=summary(up),
        breakout_day=summary(up & data['breakout']),
        breakout_failed=summary(up & data['breakout'] & data['failed']),
        breakout_held=summary(up & data['breakout'] & ~data['failed'].astype(bool)),
        confirmed_second_close=summary(up & data['confirmed']),
        just_under_resistance=summary(up & data['near_res']),
    )
    b = data.loc[up & data['breakout']]
    breakouts['failure_rate'] = _pct(b['failed'].mean()) if len(b) else None
    return dict(extension_36=extension, breakouts=breakouts)


def _pct(x):
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else round(100 * float(x), 2)


# ---------------------------------------------------------------- portfolio simulation
BASE = 'base_v1_6'
VARIANTS = {
    'base_v1_6': dict(sell_failed_breakout=True),
    'base_v1_5': dict(),
    'no_buy_above_30pct_36d': dict(skip_extended=True),
    'sell_above_30pct_36d': dict(sell_extended=True),
    'wait_under_resistance': dict(skip_near_res=True),
    'two_closes_above_resistance': dict(confirm_breakout=True),
    'sell_failed_breakout': dict(sell_failed_breakout=True),
    'wait_res_and_sell_failed': dict(skip_near_res=True, sell_failed_breakout=True),
    'kell_crossback_exit': dict(sell_failed_breakout=True, ema_crossback=True),
    'kell_base_n_break_entry': dict(sell_failed_breakout=True, base_break=True),
    'kell_wedge_pop_entry': dict(sell_failed_breakout=True, wedge_pop=True),
    'kell_full': dict(sell_failed_breakout=True, base_break=True, wedge_pop=True, ema_crossback=True),
}


def simulate(frames, spx, sectors, start, end=None, **rule):
    """Daily decisions on close t, fills at close t+1 (the live system: last night's build, today's close)."""
    dates = spx.index[(spx.index >= start) & ((spx.index < end) if end is not None else True)]
    spx_sma = spx.rolling(200).mean()
    cash, pos, trades, curve, cooldown = CAPITAL, {}, [], [], {}
    close = pd.DataFrame({s: f['close'] for s, f in frames.items()})
    for i, day in enumerate(dates[:-1]):
        nxt = dates[i + 1]
        px = close.loc[day]
        equity = cash + sum(p['shares'] * px.get(s, np.nan) for s, p in pos.items()
                            if not np.isnan(px.get(s, np.nan)))
        curve.append((day, equity))
        regime_up = spx.loc[day] > spx_sma.loc[day]
        stop = 0.08 if regime_up else 0.05
        sells = []
        for s, p in pos.items():
            f = frames[s].loc[day]
            c = f['close']
            if np.isnan(c):
                continue
            p['held'] += 1
            p['peak'] = max(p['peak'], c)
            e = p['entry']
            if p['held'] <= 15 and c >= e * 1.20:
                p['fast'] = True
            holding = p['fast'] and p['held'] <= 40
            floor = e * (1 - stop)
            if p['peak'] >= e * 1.10:
                floor = max(floor, e)
            if p['peak'] >= e * 1.20 and not holding:
                floor = max(floor, p['peak'] * 0.90)
            why = None
            if c <= floor:
                why = 'STOP'
            elif rule.get('sell_extended') and f['ext36'] > EXT_LIMIT:
                why = 'EXTENDED'
            elif holding:
                why = None
            elif (rule.get('sell_failed_breakout') and p.get('res') and p['held'] <= FAIL_WINDOW
                  and c < p['res'] * 0.97):
                why = 'FAILED_BREAKOUT'
            elif rule.get('ema_crossback') and c < f['ema10'] and c < f['ema20']:
                why = 'EMA_CROSSBACK'
            elif c < f['sma200']:
                why = 'TREND'
            elif c < f['sma50'] and c < e:
                why = 'SMA50'
            elif p['held'] >= 252:
                why = 'MAX_HOLD'
            if why:
                sells.append((s, why))
        for s, why in sells:
            fill = close.at[nxt, s]
            if np.isnan(fill):
                continue
            p = pos.pop(s)
            cash += p['shares'] * fill * (1 - COST)
            trades.append(dict(symbol=s, ret=fill * (1 - COST) / (p['entry'] * (1 + COST)) - 1,
                               held=p['held'], why=why))
            cooldown[s] = i
        if not regime_up or len(pos) >= 8:
            continue
        sector_count = {}
        for s in pos:
            sector_count[sectors.get(s)] = sector_count.get(sectors.get(s), 0) + 1
        cands = []
        for s, fr in frames.items():
            if s in pos or (s in cooldown and i - cooldown[s] <= 10) or day not in fr.index:
                continue
            f = fr.loc[day]
            if f[['close', 'sma36', 'sma50', 'sma200', 'ext_atr']].isna().any():
                continue
            c = f['close']
            if not (c > f['sma36'] and c > f['sma50'] and c > f['sma200'] and 0 <= f['ext_atr'] <= 3):
                continue
            if rule.get('skip_extended') and f['ext36'] > EXT_LIMIT:
                continue
            res = f['res']
            if rule.get('skip_near_res') and not np.isnan(res) and res * 0.97 <= c < res:
                continue
            if rule.get('confirm_breakout') and not np.isnan(res) and c > res and not f['prev_above']:
                continue                       # first close above the old high: wait for a second one
            if rule.get('base_break') or rule.get('wedge_pop'):
                above_emas = c > f['ema10'] and c > f['ema20']
                vol = f['vol_ratio']
                tight = f['base_high'] / f['base_low'] - 1 <= BASE_MAX_RANGE
                breaks = (rule.get('base_break') and above_emas and c > f['base_high'] and tight
                          and vol >= BREAK_VOLUME)
                pops = rule.get('wedge_pop') and f['ema_pop'] and vol >= POP_VOLUME
                if not (breaks or pops):
                    continue
            cands.append((-f['mad'], s, c, res))
        for _, s, c, res in sorted(cands):
            if len(pos) >= 8:
                break
            if sectors.get(s) and sector_count.get(sectors.get(s), 0) >= 2:
                continue
            fill = close.at[nxt, s]
            if np.isnan(fill):
                continue
            eq = equity
            shares = min(eq * 0.01 / (stop * fill), eq * 0.20 / fill, (cash - CAPITAL * 0.03) / (fill * (1 + COST)))
            if shares * fill < 50:
                continue
            cash -= shares * fill * (1 + COST)
            pos[s] = dict(shares=shares, entry=fill, peak=fill, held=0, fast=False,
                          res=res if c > res else None)
            sector_count[sectors.get(s)] = sector_count.get(sectors.get(s), 0) + 1
    curve = pd.Series(dict(curve)).sort_index()
    return _metrics(curve, trades)


def _metrics(curve, trades):
    rets = curve.pct_change().dropna()
    years = max((curve.index[-1] - curve.index[0]).days / 365.25, 1e-9)
    peak = curve.cummax()
    out = dict(final=round(float(curve.iloc[-1]), 0),
               cagr=_pct((curve.iloc[-1] / curve.iloc[0]) ** (1 / years) - 1),
               vol=_pct(rets.std() * math.sqrt(252)),
               sharpe=round(float(rets.mean() / rets.std() * math.sqrt(252)), 2) if rets.std() > 0 else None,
               max_drawdown=_pct((curve / peak - 1).min()),
               trades=len(trades))
    if trades:
        r = pd.Series([t['ret'] for t in trades])
        out.update(win_rate=_pct((r > 0).mean()), avg_trade=_pct(r.mean()),
                   avg_held=round(float(np.mean([t['held'] for t in trades])), 1),
                   exits={k: sum(t['why'] == k for t in trades) for k in sorted({t['why'] for t in trades})})
    return out


# ---------------------------------------------------------------- report
def windows(frames, spx, sectors):
    """The same variants in separate periods: a rule is only trusted if it helps in each of them."""
    out = []
    for lo, hi in WINDOWS:
        start, end = pd.Timestamp(lo), (pd.Timestamp(hi) if hi else None)
        sel = spx[(spx.index >= start) & ((spx.index < end) if end is not None else True)]
        if len(sel) < 250:
            continue
        active = sum(1 for f in frames.values() if f.loc[sel.index[0]:sel.index[-1], 'sma200'].notna().any())
        es = event_study(frames, spx, start, end)
        out.append(dict(window=f'{sel.index[0].date()} → {sel.index[-1].date()}', symbols=active,
                        spx=_metrics(sel / sel.iloc[0] * CAPITAL, []),
                        breakouts={k: es['breakouts'][k] for k in ('failure_rate', 'all_uptrend_days', 'breakout_failed',
                                                                    'just_under_resistance')},
                        extension_30=es['extension_36']['30..+%'],
                        portfolio={name: simulate(frames, spx, sectors, start, end, **rule)
                                   for name, rule in VARIANTS.items()}))
    return out


def robustness(wins):
    """Per variant: in how many windows it beat the base on return, drawdown and Sharpe."""
    out = {}
    for name in VARIANTS:
        if name in (BASE, 'base_v1_5'):
            continue
        better = dict(cagr=0, max_drawdown=0, sharpe=0)
        for w in wins:
            if name not in w['portfolio']:
                continue                       # results written by an older version
            base = w['portfolio'].get(BASE) or w['portfolio']['base_v1_5']
            var = w['portfolio'][name]
            for k in better:
                if None not in (base.get(k), var.get(k)) and var[k] > base[k]:
                    better[k] += 1
        out[name] = dict(better, windows=sum(name in w['portfolio'] for w in wins))
    return out


def report(result):
    lines = [f"# Backtest of the technical rules · {result['window']}", '',
             'Technical rules only (no InvestorAce label, which has no history); universe = today\'s members '
             '(survivorship bias lifts every variant alike). Decide on close t, fill at close t+1, 0.10% per fill. '
             'Compare the variants with each other.', '',
             '## 1 · After a close far above the 36-day average', '',
             '| Distance to 36-day avg | days | stocks | 21-day mean | 63-day mean | 63-day vs S&P | P(−10% within 21 d) | P(63 d < 0) |',
             '|---|---|---|---|---|---|---|---|']
    for k, v in result['event_study']['extension_36'].items():
        lines.append(f"| {k} | {v['n']} | {v['stocks']} | {v['fwd21_mean']}% | {v['fwd63_mean']}% | "
                     f"{v['xs63_mean']}% | {v['p_drop10_in_21']}% | {v['p_negative_63']}% |")
    b = result['event_study']['breakouts']
    lines += ['', f"## 2 · Breakouts above the prior 60-session high (in an uptrend) · failure rate {b['failure_rate']}%", '',
              '| Case | days | 5-day mean | 21-day mean | 63-day mean | 63-day vs S&P |', '|---|---|---|---|---|---|']
    for k in ('all_uptrend_days', 'breakout_day', 'breakout_failed', 'breakout_held', 'confirmed_second_close',
              'just_under_resistance'):
        v = b[k]
        lines.append(f"| {k} | {v['n']} | {v['fwd5_mean']}% | {v['fwd21_mean']}% | {v['fwd63_mean']}% | {v['xs63_mean']}% |")
    lines += ['', '"breakout_failed" and "breakout_held" use the next 10 sessions to sort the cases, so they are '
              'not tradable signals; they show how much a failure costs.', '',
              '## 3 · Portfolio simulation (10,000, max 8 positions)', '',
              '| Variant | CAGR | max drawdown | Sharpe | trades | win rate | avg trade | avg days |',
              '|---|---|---|---|---|---|---|---|']
    for k, v in result['portfolio'].items():
        lines.append(f"| {k} | {v['cagr']}% | {v['max_drawdown']}% | {v['sharpe']} | {v['trades']} | "
                     f"{v.get('win_rate')}% | {v.get('avg_trade')}% | {v.get('avg_held')} |")
    s = result['spx']
    lines += ['', f"S&P 500 buy and hold: CAGR {s['cagr']}%, max drawdown {s['max_drawdown']}%.", '']
    wins = result.get('windows') or []
    if wins:
        lines += ['## 4 · Separate periods (same variants)', '',
                  'Members enter a period once they have 200 days of prices, so early periods hold fewer stocks.', '']
        for w in wins:
            sp, b, x = w['spx'], w['breakouts'], w['extension_30']
            lines += [f"### {w['window']} · {w['symbols']} stocks · S&P CAGR {sp['cagr']}%, max drawdown {sp['max_drawdown']}%", '',
                      f"Breakout failure rate {b['failure_rate']}% · 63-day mean: uptrend days {b['all_uptrend_days']['fwd63_mean']}%, "
                      f"just under resistance {b['just_under_resistance']['fwd63_mean']}%, failed breakouts "
                      f"{b['breakout_failed']['fwd63_mean']}% · more than 30% above the 36-day average: n={x['n']}, "
                      f"63-day {x['fwd63_mean']}%, P(−10% in 21 d) {x['p_drop10_in_21']}%", '',
                      '| Variant | CAGR | max drawdown | Sharpe | trades |', '|---|---|---|---|---|']
            for k, v in w['portfolio'].items():
                lines.append(f"| {k} | {v['cagr']}% | {v['max_drawdown']}% | {v['sharpe']} | {v['trades']} |")
            lines.append('')
        lines += [f'### Robustness: windows in which a variant beat {BASE} (the current rules)', '',
                  '| Variant | CAGR | max drawdown (less deep) | Sharpe |', '|---|---|---|---|']
        for k, v in ((k, v) for k, v in robustness(wins).items() if v['windows']):
            lines.append(f"| {k} | {v['cagr']}/{v['windows']} | {v['max_drawdown']}/{v['windows']} | {v['sharpe']}/{v['windows']} |")
        lines.append('')
    lines += [
              f"Symbols: {result['symbols']} · generated {result['generated_at']}"]
    return '\n'.join(lines) + '\n'


PAGE = 'backtest.html'


def _md_to_html(md):
    """The report's own Markdown (headings, paragraphs, pipe tables) as HTML; nothing else is needed."""
    from html import escape
    out, table = [], []

    def flush():
        if table:
            head, *body = [r for r in table if not set(r.replace('|', '').strip()) <= set('-: ')]
            cells = lambda r: [c.strip() for c in r.strip().strip('|').split('|')]
            out.append('<div class="tw"><table><thead><tr>' + ''.join(f'<th>{escape(c)}</th>' for c in cells(head))
                       + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join(f'<td>{escape(c)}</td>' for c in cells(r))
                                                          + '</tr>' for r in body) + '</tbody></table></div>')
            table.clear()
    for line in md.splitlines():
        if line.startswith('|'):
            table.append(line)
            continue
        flush()
        if line.startswith('### '):
            out.append(f'<h3>{escape(line[4:])}</h3>')
        elif line.startswith('## '):
            out.append(f'<h2>{escape(line[3:])}</h2>')
        elif line.startswith('# '):
            out.append(f'<h1>{escape(line[2:])}</h1>')
        elif line.strip():
            out.append(f'<p class="lead">{escape(line)}</p>')
    flush()
    return ''.join(out)


def site_pages(root, build=None):
    """backtest.html from the committed results; empty until a backtest has run."""
    from war_scenario import shell
    path = Path(root) / 'backtests' / 'latest.json'
    if not path.exists():
        return []
    result = json.loads(path.read_text(encoding='utf-8'))
    intro = ('<div class="note">Updated by the backtest workflow on the first day of each month and whenever '
             'backtest.py changes. Only rules that help in every period are adopted into the trading rules '
             '(see Active trading).</div>')
    return [(Path(PAGE), shell('Backtest', intro + _md_to_html(report(result))))]


def main():
    import yfinance as yf
    import engine
    symbols = {key: row.get('yf') or key for key, row in engine.DATA.items()}
    sectors = {key: row.get('sector') for key, row in engine.DATA.items()}
    period = f'{HISTORY_YEARS}y'
    raw = yf.download(sorted(set(symbols.values())) + ['^GSPC'], period=period, auto_adjust=True,
                      progress=False, threads=True, group_by='column')
    spx = raw['Close']['^GSPC'].dropna()
    spx.index = spx.index.tz_localize(None) if spx.index.tz is not None else spx.index
    start = spx.index[-1] - pd.DateOffset(years=YEARS)
    frames = {}
    for key, sym in symbols.items():
        try:
            c, h, lo, v = (raw[k][sym] for k in ('Close', 'High', 'Low', 'Volume'))
        except KeyError:
            continue
        frame = pd.DataFrame({'c': c, 'h': h, 'l': lo, 'v': v}).dropna(subset=['c', 'h', 'l'])
        if len(frame) < WARMUP + 60:
            continue
        frame.index = frame.index.tz_localize(None) if frame.index.tz is not None else frame.index
        f = indicators(frame['c'], frame['h'], frame['l'], frame['v']).reindex(spx.index)
        frames[key] = f
    spx_curve = (spx[spx.index >= start] / spx[spx.index >= start].iloc[0]) * CAPITAL
    result = dict(schema='backtest-v2', windows=windows(frames, spx, sectors), generated_at=datetime.now(timezone.utc).isoformat(timespec='minutes'),
                  window=f'{start.date()} → {spx.index[-1].date()}', symbols=len(frames),
                  event_study=event_study(frames, spx, start),
                  portfolio={name: simulate(frames, spx, sectors, start, **rule) for name, rule in VARIANTS.items()},
                  spx=_metrics(spx_curve, []))
    OUT.mkdir(exist_ok=True)
    (OUT / 'latest.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    (OUT / 'latest.md').write_text(report(result), encoding='utf-8')
    print(report(result))


if __name__ == '__main__':
    main()
