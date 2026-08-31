#!/usr/bin/env python3
"""
macro.py · what regime are we ACTUALLY in
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
"""
import math
from datetime import datetime, timezone

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

def _roc(ser, days=126):
    if ser is None or len(ser) < days + 1: return None
    a, b = float(ser.iloc[-1]), float(ser.iloc[-days-1])
    return None if not b else (a / b - 1)

def _vs_ma(ser, n=200):
    if ser is None or len(ser) < n: return None
    return float(ser.iloc[-1]) > float(ser.rolling(n).mean().iloc[-1])

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
    regime = ('REFLATION'   if growth >= 0 and infl >= 0 else
              'GOLDILOCKS'  if growth >= 0 and infl <  0 else
              'STAGFLATION' if growth <  0 and infl >= 0 else 'RECESSION')

    # recession score, 0-100, four independent legs
    score, legs = 0, []
    tnx, fvx = c.get('^TNX'), c.get('^FVX')
    if tnx is not None and fvx is not None:
        curve = float(tnx.iloc[-1]) - float(fvx.iloc[-1])
        if curve < 0:
            score += 35; legs.append(f'yield curve inverted ({curve:+.2f}pp) — banks lend less')
    if _vs_ma(c.get('RHI')) is False:
        score += 25; legs.append('staffing stocks below their 200-day — temp hiring slowing')
    if _vs_ma(c.get('IYT')) is False:
        score += 25; legs.append('transports below their 200-day — physical goods volume falling')
    xly, xlp = c.get('XLY'), c.get('XLP')
    if xly is not None and xlp is not None and len(xly) > 50 and len(xlp) > 50:
        ratio = (xly / xlp).dropna()
        if len(ratio) > 50 and float(ratio.iloc[-1]) < float(ratio.rolling(50).mean().iloc[-1]):
            score += 15; legs.append('staples beating discretionary — consumer defensive')

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

    return dict(ok=True, regime=regime, growth=round(growth, 1), inflation=round(infl, 1),
                recession_score=score, recession_legs=legs, vix=vix, vix_state=vix_state,
                breadth=breadth,
                detail={'SPY 6m': None if g_eq is None else round(100*g_eq,1),
                        'Copper 6m': None if g_cu is None else round(100*g_cu,1),
                        'Oil 6m': None if i_oil is None else round(100*i_oil,1),
                        '10Y 6m': None if i_ty is None else round(100*i_ty,1)},
                ts=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'))

if __name__ == '__main__':
    import json
    print(json.dumps(read_macro(), indent=1))

