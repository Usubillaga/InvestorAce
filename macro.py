#!/usr/bin/env python3
"""
macro.py &middot; what regime are we ACTUALLY in
=========================================
The engine's regime_scores() answers "which regime does this STOCK suit".
It never answered "which regime are we IN". That gap made the whole column
abstract. This closes it, and the good idea comes from the Streamlit macro
dashboard: read the regime off market data instead of guessing.

  GROWTH impulse    = 6-month rate of change of  SPY (earnings expectations)
                      and copper (global industrial demand), averaged
  INFLATION impulse = 6-month rate of change of  crude oil (cost push)
                      and the US 10-year yield (market expectations), averaged

     growth+  inflation+   REFLATION
     growth+  inflation-   GOLDILOCKS
     growth-  inflation+   STAGFLATION
     growth-  inflation-   RECESSION

Plus a recession score from four independent, checkable series:
  yield curve (^TNX - ^FVX)   banking credit stress
  RHI vs its 200d             staffing leads hiring and firing
  IYT vs its 200d             transports are physical GDP, not sentiment
  XLY / XLP vs its 50d        discretionary over staples is consumer nerve

And VIX, which matters directly: the tranche rule uses VIX > 25.

No inputs, no opinions. Everything here is a number off a price series.

The market quadrant alone cannot see the economy: a rising stock market reads
as "growth" even while hiring stalls, and the INFLATION regime was unreachable.
The live regime therefore also uses dated official US data from FRED (CPI,
unemployment, payrolls). Each input becomes a signal in [-1, 1]; a growth
score and an inflation score are their averages, and all five regimes are
reachable. Without economic data the legacy market quadrant is used and the
reading is marked MARKET_ONLY.
"""
import csv
import io
import json
import math
import urllib.request
from datetime import datetime, timezone
from path_features import diagnostics as path_diagnostics

try:
    import yfinance as yf
except ImportError:
    yf = None

SERIES = ['SPY', 'HG=F', 'CL=F', '^TNX', '^VIX', '^FVX', 'RSP', 'IYT', 'RHI', 'XLY', 'XLP']

def _closes(period='2y'):
    if yf is None: return {}
    out = {}
    for s in SERIES:
        try:
            h = yf.Ticker(s).history(period=period, auto_adjust=False)
            if h is None or h.empty: continue
            c = h['Close'].dropna()
            if len(c): out[s] = c
        except Exception:
            continue
    return out

def _roc(ser, days=126, back=0):
    """6-month rate of change as it stood `back` trading days ago.
       back=0 is today; back=63 is the same reading a quarter ago."""
    if ser is None or len(ser) < days + back + 1: return None
    a = float(ser.iloc[-1 - back]); b = float(ser.iloc[-days - back - 1])
    return None if not b else (a / b - 1)

def _vs_ma(ser, n=200):
    if ser is None or len(ser) < n: return None
    return float(ser.iloc[-1]) > float(ser.rolling(n).mean().iloc[-1])


def _point(c, back):
    gs = [x for x in (_roc(c.get('SPY'), back=back), _roc(c.get('HG=F'), back=back)) if x is not None]
    is_ = [x for x in (_roc(c.get('CL=F'), back=back), _roc(c.get('^TNX'), back=back)) if x is not None]
    if not gs or not is_: return None
    return (round(100*sum(gs)/len(gs), 2), round(100*sum(is_)/len(is_), 2))

def quadrant_of(g, i):
    return ('REFLATION'   if g >= 0 and i >= 0 else
            'GOLDILOCKS'  if g >= 0 and i <  0 else
            'STAGFLATION' if g <  0 and i >= 0 else 'RECESSION')

def trail(c=None):
    """Where the economy has been, as a path through the growth/inflation grid.
       Each point is the SAME 6-month impulse calculation evaluated at an earlier
       endpoint. The path is not a model and not a forecast -- it is one statistic
       read at six moments, which is the only honest way to show direction."""
    if c is None: c = _closes()
    if not c: return []
    out = []
    for back, label in ((252,'12m'), (189,'9m'), (126,'6m'), (63,'3m'), (21,'1m'), (0,'now')):
        p = _point(c, back)
        if p: out.append(dict(label=label, back=back, g=p[0], i=p[1],
                              quadrant=quadrant_of(p[0], p[1])))
    return out

def heading(tr):
    """Direction of travel from three readings ago to now. A DESCRIPTION of the
       path, not an extrapolation of it."""
    if len(tr) < 3: return None
    now, prev = tr[-1], tr[-3]
    dg, di = now['g'] - prev['g'], now['i'] - prev['i']
    if abs(dg) < 0.5 and abs(di) < 0.5:
        return dict(dg=round(dg,2), di=round(di,2), toward=now['quadrant'], note='stalled')
    tg = quadrant_of(now['g'] + dg, now['i'] + di)
    return dict(dg=round(dg,2), di=round(di,2), toward=tg,
                note=('holding' if tg == now['quadrant'] else 'crossing'))


# ---------------- official economic data ----------------
FRED_SERIES = {'cpi': 'CPIAUCSL', 'unemployment': 'UNRATE', 'payrolls': 'PAYEMS'}
FRED_URL = 'https://fred.stlouisfed.org/graph/fredgraph.csv?id={}'
REGIME_BASIS = 'MARKET_AND_ECONOMIC_DATA'


def _fred(series_id, timeout=20):
    """Monthly observations [(YYYY-MM-DD, value)], oldest first; '.' rows skipped."""
    request = urllib.request.Request(FRED_URL.format(series_id),
                                     headers={'User-Agent': 'Mozilla/5.0 (InvestorAce macro research)',
                                              'Accept': 'text/csv,*/*'})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        text = response.read().decode('utf-8')
    rows = []
    for row in csv.reader(io.StringIO(text)):
        if len(row) != 2:
            continue
        try:
            value = float(row[1])
            datetime.strptime(row[0], '%Y-%m-%d')
        except ValueError:
            continue
        if math.isfinite(value):
            rows.append((row[0], value))
    return rows


# The same three BLS series, read from the BLS public API when FRED refuses.
BLS_SERIES = {'cpi': 'CUSR0000SA0', 'unemployment': 'LNS14000000', 'payrolls': 'CES0000000001'}
BLS_URL = 'https://api.bls.gov/publicAPI/v1/timeseries/data/{}'


def _bls(series_id, timeout=20):
    """Monthly observations [(YYYY-MM-01, value)], oldest first, from BLS API v1."""
    request = urllib.request.Request(BLS_URL.format(series_id),
                                     headers={'User-Agent': 'InvestorAce macro (research)'})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode('utf-8'))
    if payload.get('status') != 'REQUEST_SUCCEEDED':
        raise ValueError('BLS status ' + str(payload.get('status')))
    rows = []
    for series in (payload.get('Results') or {}).get('series') or []:
        for item in series.get('data') or []:
            period = str(item.get('period', ''))
            if not period.startswith('M') or period == 'M13':
                continue
            try:
                value = float(str(item.get('value')).replace(',', ''))
                stamp = f"{int(item['year']):04d}-{int(period[1:]):02d}-01"
            except (KeyError, TypeError, ValueError):
                continue
            if math.isfinite(value):
                rows.append((stamp, value))
    return sorted(rows)


ECONOMIC_LOG = []


def economic_data(fetch=_fred, fallback=_bls, log=None):
    """Last 40 monthly observations per series; FRED first, BLS as fallback.

    A series both sources fail on is simply absent. Each outcome is logged so
    a build shows why the regime fell back to market data only."""
    out, notes = {}, []
    for key, series_id in FRED_SERIES.items():
        rows, source = [], 'FRED'
        try:
            rows = fetch(series_id)
        except Exception as exc:
            notes.append(f'{key}: FRED failed ({type(exc).__name__}: {str(exc)[:80]})')
        if not rows and fallback is not None:
            source = 'BLS'
            try:
                rows = fallback(BLS_SERIES[key])
            except Exception as exc:
                notes.append(f'{key}: BLS failed ({type(exc).__name__}: {str(exc)[:80]})')
        if rows:
            out[key] = [{'date': d, 'value': v} for d, v in rows[-40:]]
            notes.append(f'{key}: {source} ok, {len(rows)} rows, last {rows[-1][0]}')
    ECONOMIC_LOG[:] = notes
    (log or print)('Economic data: ' + '; '.join(notes))
    return out


def _month(date_text):
    year, month = int(date_text[:4]), int(date_text[5:7])
    return year * 12 + month - 1


def _by_month(rows):
    """{month index: value}; a month the agency never published simply is absent."""
    out = {}
    for row in rows or []:
        try:
            out[_month(row['date'])] = float(row['value'])
        except (KeyError, TypeError, ValueError):
            continue
    return out


def economic_signals(data):
    """Dated readings derived from official monthly data; short series are omitted.

    Every comparison is by calendar month, never by list position: BLS did
    not publish October 2025 (government shutdown), and a positional lookup
    then compared September 2026 with August 2025.
    """
    out = {}
    data = data or {}
    cpi = _by_month(data.get('cpi'))
    if cpi:
        last = max(cpi)
        def yoy(m):
            return 100 * (cpi[m] / cpi[m - 12] - 1) if m in cpi and m - 12 in cpi and cpi[m - 12] > 0 else None
        now, before = yoy(last), yoy(last - 3)
        if now is not None and before is not None:
            out.update(cpi_yoy=round(now, 2), cpi_yoy_3m_change=round(now - before, 2),
                       cpi_date=data['cpi'][-1]['date'])
    unemployment = _by_month(data.get('unemployment'))
    if unemployment:
        last = max(unemployment)
        def avg3(m):
            values = [unemployment.get(m - k) for k in range(3)]
            known = [v for v in values if v is not None]
            return sum(known) / len(known) if len(known) >= 2 else None
        prior = [avg3(m) for m in range(last - 12, last)]
        prior = [v for v in prior if v is not None]
        current = avg3(last)
        if current is not None and len(prior) >= 10:
            # Sahm-type gap: 3-month average versus its low over the prior 12 months.
            out.update(unemployment=unemployment[last], unemployment_gap=round(current - min(prior), 2),
                       unemployment_date=data['unemployment'][-1]['date'])
    payrolls = _by_month(data.get('payrolls'))
    if payrolls:
        last = max(payrolls)
        if last - 3 in payrolls:
            out.update(payrolls_3m_avg_thousands=round((payrolls[last] - payrolls[last - 3]) / 3, 1),
                       payrolls_date=data['payrolls'][-1]['date'])
    return out


def _clip(x):
    return max(-1.0, min(1.0, x))


def classify(growth, inflation, signals=None):
    """Five-regime reading from market impulses (percent) and economic signals.

    growth score    = mean(market growth/10, labour (0.3 - gap)/0.3,
                           payrolls (avg - 75k)/75k)
    inflation score = mean(market inflation/20, CPI (yoy - 2.5)/1.5,
                           CPI trend change/0.5)
    growth >= 0: INFLATION if inflation >= 0.5, REFLATION if >= 0, else GOLDILOCKS
    growth <  0: STAGFLATION if inflation >= 0, else RECESSION
    """
    signals = signals or {}
    g = {'market': _clip(growth / 10)}
    i = {'market': _clip(inflation / 20)}
    if signals.get('unemployment_gap') is not None:
        g['labour'] = _clip((0.3 - signals['unemployment_gap']) / 0.3)
    if signals.get('payrolls_3m_avg_thousands') is not None:
        g['payrolls'] = _clip((signals['payrolls_3m_avg_thousands'] - 75) / 75)
    if signals.get('cpi_yoy') is not None:
        i['cpi_level'] = _clip((signals['cpi_yoy'] - 2.5) / 1.5)
    if signals.get('cpi_yoy_3m_change') is not None:
        i['cpi_trend'] = _clip(signals['cpi_yoy_3m_change'] / 0.5)
    economic = len(g) + len(i) > 2
    if not economic:
        return dict(regime=quadrant_of(growth, inflation), basis='MARKET_ONLY',
                    growth_score=None, inflation_score=None, components=None)
    gs, is_ = sum(g.values()) / len(g), sum(i.values()) / len(i)
    regime = (('INFLATION' if is_ >= 0.5 else 'REFLATION' if is_ >= 0 else 'GOLDILOCKS')
              if gs >= 0 else ('STAGFLATION' if is_ >= 0 else 'RECESSION'))
    return dict(regime=regime, basis=REGIME_BASIS, growth_score=round(gs, 2),
                inflation_score=round(is_, 2),
                components={'growth': {k: round(v, 2) for k, v in g.items()},
                            'inflation': {k: round(v, 2) for k, v in i.items()}})


def read_macro():
    """Returns the live regime, the two impulses, a recession score and VIX."""
    c = _closes()
    if not c:
        return dict(ok=False, note='no market data')

    g_eq, g_cu = _roc(c.get('SPY')), _roc(c.get('HG=F'))
    i_oil, i_ty = _roc(c.get('CL=F')), _roc(c.get('^TNX'))
    gs = [x for x in (g_eq, g_cu) if x is not None]
    is_ = [x for x in (i_oil, i_ty) if x is not None]
    if not gs or not is_:
        return dict(ok=False, note='insufficient history for the impulses')

    growth = 100 * sum(gs) / len(gs)
    infl   = 100 * sum(is_) / len(is_)
    market_regime = quadrant_of(growth, infl)
    economy = economic_data()
    signals = economic_signals(economy)
    reading = classify(growth, infl, signals)
    regime = reading['regime']

    # recession score, 0-100, four independent legs
    score, legs = 0, []
    tnx, fvx = c.get('^TNX'), c.get('^FVX')
    if tnx is not None and fvx is not None:
        curve = float(tnx.iloc[-1]) - float(fvx.iloc[-1])
        if curve < 0:
            score += 35; legs.append(f'yield curve inverted ({curve:+.2f}pp) &mdash; banks lend less')
    if _vs_ma(c.get('RHI')) is False:
        score += 25; legs.append('staffing stocks below their 200-day &mdash; temp hiring slowing')
    if _vs_ma(c.get('IYT')) is False:
        score += 25; legs.append('transports below their 200-day &mdash; physical goods volume falling')
    xly, xlp = c.get('XLY'), c.get('XLP')
    if xly is not None and xlp is not None and len(xly) > 50 and len(xlp) > 50:
        ratio = (xly / xlp).dropna()
        if len(ratio) > 50 and float(ratio.iloc[-1]) < float(ratio.rolling(50).mean().iloc[-1]):
            score += 15; legs.append('staples beating discretionary &mdash; consumer defensive')

    vix = float(c['^VIX'].iloc[-1]) if '^VIX' in c else None
    vix_state = (None if vix is None else
                 'CRASH'        if vix > 28 else
                 'STRESSED'     if vix > 20 else
                 'COMPLACENT'   if vix < 12 else 'CALM')

    breadth = None
    if 'RSP' in c and 'SPY' in c and len(c['RSP']) > 50:
        r = (c['RSP'] / c['SPY']).dropna()
        if len(r) > 50:
            breadth = 'broadening' if float(r.iloc[-1]) > float(r.rolling(50).mean().iloc[-1]) else 'narrowing'

    tr = trail(c)
    # Preserve the legacy classifier above. Research observations require all
    # four proxy series on exactly the same dates, never positional alignment.
    points = aligned_path(c)
    raw = {sym: [{'date': idx.isoformat(), 'close': float(value)}
                  for idx, value in series.items()]
           for sym, series in c.items()}
    return dict(ok=True, regime=regime, market_regime=market_regime,
                regime_basis=reading['basis'], growth_score=reading['growth_score'],
                inflation_score=reading['inflation_score'], regime_components=reading['components'],
                economic=signals, economic_series=economy,
                economic_source='FRED or BLS API (CPI-U, unemployment rate, nonfarm payrolls); monthly, latest vintage',
                economic_log=list(ECONOMIC_LOG),
                trail=tr, heading=heading(tr), growth=round(growth, 1), inflation=round(infl, 1),
                path_points=points, path_diagnostics=path_diagnostics(points),
                input_series=raw, source='Yahoo market-price proxies; unadjusted closes',
                source_vintage='retrieved-now; historical closes may be revised',
                recession_score=score, recession_legs=legs, vix=vix, vix_state=vix_state,
                breadth=breadth,
                detail={'SPY 6m': None if g_eq is None else round(100*g_eq,1),
                        'Copper 6m': None if g_cu is None else round(100*g_cu,1),
                        'Oil 6m': None if i_oil is None else round(100*i_oil,1),
                        '10Y 6m': None if i_ty is None else round(100*i_ty,1)},
                ts=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'))

def aligned_path(closes, lookback=126, window=126):
    """Common-date proxy path, with no forward filling or future interpolation."""
    keys = ('SPY', 'HG=F', 'CL=F', '^TNX')
    if any(k not in closes for k in keys):
        return []
    series = {k: {idx.date().isoformat(): float(v) for idx, v in closes[k].items()
                  if math.isfinite(float(v))} for k in keys}
    dates = sorted(set.intersection(*(set(s) for s in series.values())))
    points = []
    for j in range(max(lookback, len(dates) - window), len(dates)):
        now, prev = dates[j], dates[j - lookback]
        if any(series[k][prev] == 0 for k in keys):
            continue
        roc = {k: 100 * (series[k][now] / series[k][prev] - 1) for k in keys}
        points.append({'date': now, 'g': (roc['SPY'] + roc['HG=F']) / 2,
                       'i': (roc['CL=F'] + roc['^TNX']) / 2,
                       'spy_close': series['SPY'][now]})
    return points


if __name__ == '__main__':
    print(json.dumps(read_macro(), indent=1))


# =====================================================================
# SECTOR PERFORMANCE
#
# The eleven SPDR sector ETFs, rebased and measured over 1/3/5/10 years.
# The point is not the league table. It is that the ordering IS a regime
# reading: a decade in which technology triples and energy goes nowhere
# is a decade of falling discount rates, and the framework's REFLATION
# affinities are a bet that the ordering inverts. Putting the two side
# by side is the only way to see whether that bet is contrarian or late.
# =====================================================================
SECTOR_ETF = {
    'XLK':  'Technology',      'XLV': 'Health Care',    'XLE': 'Energy',
    'XLF':  'Financials',      'XLP': 'Cons. Staples',  'XLY': 'Cons. Discretionary',
    'XLI':  'Industrials',     'XLB': 'Materials',      'XLU': 'Utilities',
    'XLRE': 'Real Estate',     'XLC': 'Comm. Services', 'SPY': 'S&P 500',
}
# how each maps onto the engine's affinity tables, so the two can be compared
SECTOR_TO_ENGINE = {
    'XLK':'Technology','XLV':'Healthcare','XLE':'Energy','XLF':'Info Svcs',
    'XLP':'Consumer Defensive','XLY':'Consumer Cyclical','XLI':'Industrials',
    'XLB':'Materials','XLU':'Utilities','XLRE':'REIT','XLC':'Communication Services',
}

def sector_performance(years=10):
    """Annualised total return over several windows, plus a rebased path."""
    if yf is None: return {}
    out, paths, dates = {}, {}, None
    for sym, name in SECTOR_ETF.items():
        try:
            h = yf.Ticker(sym).history(period=f'{years}y', auto_adjust=True)
            if h is None or h.empty: continue
            c = h['Close'].dropna()
            if len(c) < 260: continue
            row = {'name': name, 'sym': sym}
            for w, lbl in ((252,'1y'), (756,'3y'), (1260,'5y'), (2520,'10y')):
                if len(c) > w:
                    tot = float(c.iloc[-1]) / float(c.iloc[-w-1]) - 1
                    row[lbl] = round(100 * ((1 + tot) ** (252.0/w) - 1), 2)
                else:
                    row[lbl] = None
            out[sym] = row
            m = c.resample('ME').last().dropna()
            paths[sym] = [round(100 * float(x) / float(m.iloc[0]), 1) for x in m]
            if dates is None or len(m) > len(dates):
                dates = [str(i)[:7] for i in m.index]
        except Exception:
            continue
    n = min((len(v) for v in paths.values()), default=0)
    paths = {k: v[-n:] for k, v in paths.items()}
    return dict(rows=out, paths=paths, dates=(dates[-n:] if dates else []), years=years)
