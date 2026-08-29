#!/usr/bin/env python3
"""
add_ticker.py · v2 · safe draft-only ticker adder

  python add_ticker.py ASML.AS

WHAT THIS DOES AND DELIBERATELY DOES NOT DO
-------------------------------------------
Yahoo can supply the MECHANICAL half honestly: price, share count, a cash-flow
figure, currency, sector. It cannot supply the JUDGEMENT half: the eight
subscores, the delivering metric, the clock classification.

So a new ticker is written as a DRAFT: built='yahoo-draft', sub=None, pr=None.
It gets NGV and cover — which are real and useful immediately — and NO SCORE,
which is the honest state until a human fills the rest in.

Gemini is right that raw Yahoo FCF will not run this model unattended. It is
wrong that this makes automation useless. Automating the mechanical half and
refusing to automate the judgement half is the correct split.
"""
import sys, math, json, re, os
import yfinance as yf

TARGET = 'engine.py'          # file containing the DATA = { ... } block

# Yahoo quirks worth encoding once
LONDON_PENCE = ('.L',)        # London quotes GBp (pence), not GBP
KNOWN_FIX = {                 # tickers where the obvious guess is a different company
    'ENG':  ('ENG.MC',  'Enagas — ENGI.PA is ENGIE, a different company'),
    'SAN':  ('SAN.PA',  'Sanofi — SAN.MC is Banco Santander'),
    'ENB':  ('ENB.TO',  'use .TO for the CAD line; plain ENB quotes USD'),
    'MUV2': ('MUV2.DE', 'Munich Re — MUVG.DE does not exist'),
    'NVO':  ('NVO',     'NYSE ADR quotes USD; NOVO-B.CO quotes DKK'),
}

def clean(x):
    """None for anything that is not a finite number. [FIX] NaN is truthy in
       Python, so `if x else None` lets nan through and writes fcf=nan, which
       raises NameError the next time the module imports."""
    try:
        v = float(x)
        return None if (math.isnan(v) or math.isinf(v)) else v
    except (TypeError, ValueError):
        return None

def ttm_fcf(tk):
    """TTM = last four quarters of (operating cash flow − capex), in millions.
       [FIX] Gemini's version took cashflow.iloc[0], which is the last ANNUAL
       figure — up to twelve months stale for a company mid-year."""
    for getter, label, n in ((lambda: tk.quarterly_cashflow, 'TTM q', 4),
                             (lambda: tk.cashflow,           'FY',    1)):
        try:
            cf = getter()
            if cf is None or cf.empty: continue
            idx = {str(i).strip().lower(): i for i in cf.index}
            def row(*names):
                for nm in names:
                    if nm in idx: return cf.loc[idx[nm]]
                return None
            fcf = row('free cash flow')
            if fcf is not None:
                vals = [clean(v) for v in fcf.iloc[:n]]
                vals = [v for v in vals if v is not None]
                if vals: return sum(vals)/1e6, f'{label} FreeCashFlow'
            ocf = row('operating cash flow', 'total cash from operating activities')
            cap = row('capital expenditure', 'capital expenditures')
            if ocf is not None and cap is not None:
                o = [clean(v) for v in ocf.iloc[:n]]; c = [clean(v) for v in cap.iloc[:n]]
                pairs = [(a,b) for a,b in zip(o,c) if a is not None and b is not None]
                if pairs: return sum(a+b for a,b in pairs)/1e6, f'{label} OCF-capex'
        except Exception:
            continue
    return None, 'unavailable'

def main():
    if len(sys.argv) < 2:
        print('usage: python add_ticker.py <YAHOO_TICKER>'); return 1
    yft = sys.argv[1].strip().upper()
    key = yft.split('.')[0]

    src = open(TARGET, encoding='utf-8').read()
    if re.search(rf"^\s*'{re.escape(key)}'\s*:", src, re.M):
        print(f'{key} is already in DATA. Nothing written.'); return 1   # [FIX] duplicate guard

    tk = yf.Ticker(yft)
    fi = {}
    try: fi = dict(tk.fast_info) or {}
    except Exception: pass

    px  = clean(fi.get('last_price'))
    cur = str(fi.get('currency') or '').strip() or 'USD'
    sh  = clean(fi.get('shares'))                       # [FIX] fast_info, not info['sharesOutstanding']
    if sh is None:
        try: sh = clean((tk.get_info() or {}).get('sharesOutstanding'))
        except Exception: pass
    sh = round(sh/1e6, 2) if sh else None

    fcf, fcf_src = ttm_fcf(tk)
    fcf = round(fcf, 1) if fcf is not None else None

    sector = ''
    try: sector = (tk.get_info() or {}).get('sector', '') or ''
    except Exception: pass

    # sanity band from the 52-week range, widened. A quote outside it is rejected
    # at fetch time rather than silently producing a plausible wrong cover.
    lo = clean(fi.get('year_low')); hi = clean(fi.get('year_high'))
    sanity = (round(lo*0.5), round(hi*2)) if (lo and hi) else (0, 0)

    warn = []
    if yft.endswith(LONDON_PENCE) and cur.upper() == 'GBP':
        cur = 'GBp'; warn.append('London quotes pence — currency forced to GBp')
    if key in KNOWN_FIX and KNOWN_FIX[key][0] != yft:
        warn.append(f'expected {KNOWN_FIX[key][0]}: {KNOWN_FIX[key][1]}')
    if fcf is not None and fcf <= 0:
        warn.append('FCF is negative or zero — set fcf=None and add na="reason"')
    if sanity == (0, 0):
        warn.append('no 52-week range — set sanity manually before trusting the price')

    entry = (f"'{key}': dict(yf='{yft}', fcf={fcf}, shares={sh}, r=.080, cur='{cur}',\n"
             f"    deliver=None, dl='', sub=None, pr=None, dil=6.0, clock='CONC',\n"
             f"    ins='NOT CHECKED', held=False, sector='{sector}', built='yahoo-draft',\n"
             f"    sanity={sanity}),\n")

    # [FIX] plain splice, not re.sub. A backslash or a \1 in a sector name makes
    # re.sub either corrupt the file or raise. String surgery on the anchor is safe.
    m = re.search(r'^DATA\s*=\s*\{', src, re.M)
    if not m: print(f'could not find "DATA = {{" in {TARGET}'); return 1
    close = src.index('\n}', m.end())
    out = src[:close+1] + entry + src[close+1:]
    open(TARGET, 'w', encoding='utf-8').write(out)

    print(f'ADDED {key}  ({yft})')
    print(f'  price {px}  {cur} | shares {sh}m | fcf {fcf}m from {fcf_src} | sanity {sanity}')
    print(f'  built=yahoo-draft -> NGV and cover will compute, SCORE WILL NOT.')
    for w in warn: print(f'  ! {w}')
    print('\nSTILL OWED BY A HUMAN — Yahoo cannot supply these:')
    print('  sub=(growth, profitability, cash gen, balance sheet, valuation, returns)')
    print('  pr, dil   priced-in and dilution subscores')
    print('  deliver   the company\'s own leading growth metric, in %')
    print('  clock     CLOCK / CONC / DIV')
    print('  REIT? use AFFO per share.  Pipeline? use distributable cash flow.')
    print('  Commodity producer or negative FCF? set fcf=None and na="reason".')
    return 0

if __name__ == '__main__':
    sys.exit(main())
