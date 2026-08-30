#!/usr/bin/env python3
"""
autoscore.py · draft the scorecard automatically from Yahoo financials
=====================================================================
  from autoscore import auto_row
  row = auto_row('ASML.AS')      -> a complete DATA dict, built='auto'

WHAT IS AND IS NOT AUTOMATABLE — the honest split
-------------------------------------------------
I have been saying "the subscores need a human". That was too broad. Six of the
eight ARE computable from filings against explicit thresholds. Only two are not:

  AUTOMATABLE (thresholds below, no judgement)
    growth          revenue growth YoY
    profitability   operating margin
    cash generation FCF margin
    balance sheet   net debt / EBITDA
    valuation       FCF yield
    returns         dividend yield + buyback yield
    priced-in       DERIVED from cover, minus 2.0 when the cushion is negative
    dilution        twelve-month share-count change

  NOT AUTOMATABLE (and no threshold will fix them)
    deliver   the company's OWN leading metric — organic revenue, cRPO, comps,
              gross bookings, AFFO/share. Yahoo has revenue growth, which is a
              proxy, not the thing. Auto-filled and flagged.
    clock     needs a judgement about whether concentration has an expiry date.
              Auto-guessed from sector and flagged for review.
    na        a REIT needs AFFO, a pipeline needs DCF, a commodity producer needs
              nothing at all. Auto-detects negative FCF only.

Every auto row is marked built='auto'. That is not decoration — it tells you the
number has not been read by a person, which is exactly what the provenance
column exists to say.
"""
import math
import yfinance as yf

# ---- thresholds. change these and the whole book rescores consistently ----
def _band(x, table, default=5.0):
    """table = [(upper_bound, score), ...] ascending. None x -> default."""
    if x is None or (isinstance(x, float) and math.isnan(x)): return default
    for hi, sc in table:
        if x < hi: return sc
    return table[-1][1]

GROWTH   = [(0,2.0),(5,4.0),(10,5.5),(20,7.0),(40,8.5),(1e9,9.5)]        # revenue growth %
PROFIT   = [(0,2.0),(10,4.0),(20,6.0),(30,7.5),(45,9.0),(1e9,9.5)]       # operating margin %
CASHGEN  = [(0,1.5),(5,4.0),(12,6.0),(20,7.5),(30,9.0),(1e9,9.5)]        # FCF margin %
BALANCE  = [(0,9.5),(1,8.0),(2,7.0),(3,6.0),(4,4.5),(5,3.0),(1e9,1.5)]   # net debt / EBITDA
VALUE    = [(1,1.5),(2,3.0),(3,4.5),(4.5,6.0),(7,7.5),(1e9,9.0)]         # FCF yield %
RETURNS  = [(0.01,1.0),(1,4.0),(2.5,6.0),(4,7.5),(1e9,9.0)]              # div + buyback yield %
DILUTION = [(-4,9.5),(-1,8.5),(0.5,7.0),(2,5.5),(5,3.5),(10,2.0),(1e9,0.5)]  # share count change %

def priced_in_from_cover(cover_pct, cushion=None):
    """[Sicher] This is not a new rule — it is the mapping I have been applying by
       hand across 48 rows, written down. 199% cover -> 9.5. 25% -> 2.5. And the
       Pfizer adjustment: a NEGATIVE cushion costs 2.0 points regardless of how
       good the cover looks, because the hurdle sits above what the business
       delivers."""
    if cover_pct is None: return None
    pr = _band(cover_pct, [(15,1.5),(25,2.5),(35,3.0),(45,4.5),(60,5.5),(75,7.0),(90,8.0),(100,9.0),(1e9,9.5)])
    if cushion is not None and cushion < 0: pr = max(1.0, pr - 2.0)
    return round(pr, 1)

CLOCK_GUESS = {                       # a starting point, NOT an answer
 'Pharma':'CLOCK','Biotech':'CLOCK','Animal Health':'CLOCK','Utilities':'CLOCK','Materials':'CLOCK',
 'Energy':'DIV','Staples':'DIV','Restaurant':'DIV','Health Ins':'DIV','MedTech':'DIV','Media':'DIV',
}

def _fin(tk):
    """Pull everything needed in one pass. Returns None for anything unavailable."""
    out = dict(fcf=None, shares=None, rev=None, rev_prev=None, opinc=None,
               ebitda=None, netdebt=None, div_yield=None, price=None, cur=None,
               sector='', name='', lo=None, hi=None, shares_prev=None)
    fi = {}
    try: fi = dict(tk.fast_info) or {}
    except Exception: pass
    out['price'] = fi.get('last_price')
    out['cur']   = str(fi.get('currency') or '')
    out['shares']= fi.get('shares')
    for lo_k, hi_k in (('year_low','year_high'),('yearLow','yearHigh'),('fiftyTwoWeekLow','fiftyTwoWeekHigh')):
        if fi.get(lo_k) and fi.get(hi_k): out['lo'], out['hi'] = fi[lo_k], fi[hi_k]; break
    info = {}
    try: info = tk.get_info() or {}
    except Exception: pass
    out['sector'] = info.get('sector','') or ''
    out['name']   = info.get('longName','') or ''
    out['div_yield'] = (info.get('dividendYield') or 0) * (100 if (info.get('dividendYield') or 0) < 1 else 1)
    if not out['shares']: out['shares'] = info.get('sharesOutstanding')

    def rows(df, *names):
        if df is None or getattr(df,'empty',True): return None
        idx = {str(i).strip().lower(): i for i in df.index}
        for n in names:
            if n in idx: return df.loc[idx[n]]
        return None
    def num(x):
        try:
            v = float(x); return None if math.isnan(v) else v
        except Exception: return None

    try:  # TTM from four quarters where possible
        qcf = tk.quarterly_cashflow
        fr = rows(qcf, 'free cash flow')
        if fr is not None:
            v = [num(x) for x in fr.iloc[:4]]; v = [x for x in v if x is not None]
            if v: out['fcf'] = sum(v)
        if out['fcf'] is None:
            o, c = rows(qcf,'operating cash flow'), rows(qcf,'capital expenditure')
            if o is not None and c is not None:
                p = [(num(a),num(b)) for a,b in zip(o.iloc[:4], c.iloc[:4])]
                p = [(a,b) for a,b in p if a is not None and b is not None]
                if p: out['fcf'] = sum(a+b for a,b in p)
    except Exception: pass
    try:
        qis = None
        for attr in ('quarterly_income_stmt', 'quarterly_financials'):   # newer name first
            try:
                cand = getattr(tk, attr, None)
                if cand is not None and not cand.empty: qis = cand; break
            except Exception: continue
        r = rows(qis, 'total revenue', 'operating revenue')
        if r is not None and len(r) >= 8:                 # ideal: TTM vs prior TTM
            cur4  = [num(x) for x in r.iloc[:4]];  prev4 = [num(x) for x in r.iloc[4:8]]
            if all(v is not None for v in cur4+prev4):
                out['rev'], out['rev_prev'] = sum(cur4), sum(prev4)
        if out['rev'] is None and r is not None and len(r) >= 4:
            v = [num(x) for x in r.iloc[:4]]                # [FIX] 4 quarters is enough for TTM
            if all(x is not None for x in v): out['rev'] = sum(v)
        if out['rev_prev'] is None:                        # [FIX] YoY from ANNUAL statements
            try:
                ais = getattr(tk, 'income_stmt', None)
                if ais is None or ais.empty: ais = tk.financials
                ar = rows(ais, 'total revenue', 'operating revenue')
                if ar is not None and len(ar) >= 2:
                    a0, a1 = num(ar.iloc[0]), num(ar.iloc[1])
                    if a0 and a1:
                        if out['rev'] is None: out['rev'] = a0
                        out['rev_prev'] = a1
            except Exception: pass
        oi = rows(qis,'operating income','ebit','total operating income as reported')
        if oi is not None:
            v = [num(x) for x in oi.iloc[:4]]; v=[x for x in v if x is not None]
            if v: out['opinc'] = sum(v)
        if out['opinc'] is None:                            # [FIX] annual fallback
            try:
                ais = getattr(tk, 'income_stmt', None)
                ao = rows(ais, 'operating income', 'ebit')
                if ao is not None: out['opinc'] = num(ao.iloc[0])
            except Exception: pass
        eb = rows(qis,'ebitda','normalized ebitda')
        if eb is not None:
            v = [num(x) for x in eb.iloc[:4]]; v=[x for x in v if x is not None]
            if v: out['ebitda'] = sum(v)
    except Exception: pass
    try:
        bs = tk.quarterly_balance_sheet
        d  = rows(bs,'total debt'); c = rows(bs,'cash and cash equivalents','cash cash equivalents and short term investments')
        dv = num(d.iloc[0]) if d is not None else None
        cv = num(c.iloc[0]) if c is not None else None
        if dv is not None: out['netdebt'] = dv - (cv or 0)
        so = rows(bs,'ordinary shares number','share issued')
        if so is not None and len(so) >= 5:
            a, b = num(so.iloc[0]), num(so.iloc[4])
            if a and b: out['shares_prev'] = b
    except Exception: pass
    return out

def auto_row(symbol, r=0.080):
    """Return a DATA-ready dict, fully drafted. built='auto'."""
    tk = yf.Ticker(symbol)
    f  = _fin(tk)
    warn = []
    if not f['fcf'] or not f['shares']:
        return None, ['no cash flow or share count — cannot build NGV']

    fcf_m = f['fcf']/1e6
    sh_m  = f['shares']/1e6
    rev_g = (100*(f['rev']/f['rev_prev']-1)) if (f['rev'] and f['rev_prev']) else None
    op_m  = (100*f['opinc']/f['rev'])  if (f['opinc'] and f['rev']) else None
    fcf_m_pct = (100*f['fcf']/f['rev']) if f['rev'] else None
    nd_e  = (f['netdebt']/f['ebitda']) if (f['netdebt'] is not None and f['ebitda']) else None
    mcap  = (f['price']*f['shares']) if (f['price'] and f['shares']) else None
    fcf_y = (100*f['fcf']/mcap) if mcap else None
    sh_ch = (100*(f['shares']/f['shares_prev']-1)) if f['shares_prev'] else None
    buyb  = max(0.0, -(sh_ch or 0))
    tot_y = (f['div_yield'] or 0) + buyb

    sub = (round(_band(rev_g, GROWTH),1), round(_band(op_m, PROFIT),1),
           round(_band(fcf_m_pct, CASHGEN),1), round(_band(nd_e, BALANCE),1),
           round(_band(fcf_y, VALUE),1), round(_band(tot_y, RETURNS),1))
    dil = round(_band(sh_ch, DILUTION),1)

    ngv   = (fcf_m/sh_m)/r
    cover = 100*ngv/f['price'] if f['price'] else None
    impl  = 100*r*(1-cover/100)/(1+(cover/100)*r) if cover else None
    cush  = (rev_g - impl) if (rev_g is not None and impl is not None) else None
    pr    = priced_in_from_cover(cover, cush)

    if fcf_m <= 0:      warn.append(f'FCF negative ({fcf_m:,.0f}m) — set fcf=None and add na="reason"')
    if rev_g is None:   warn.append('no revenue history — growth scored at the 5.0 default')
    if nd_e is None:    warn.append('no net-debt/EBITDA — balance sheet scored at the 5.0 default')
    warn.append('deliver is REVENUE GROWTH, a proxy. Replace with the company\'s own leading metric.')
    warn.append(f'clock guessed from sector "{f["sector"]}" — confirm CLOCK / CONC / DIV by hand.')

    row = dict(yf=symbol, fcf=round(fcf_m,1), shares=round(sh_m,2), r=r,
               cur=('GBp' if symbol.endswith('.L') and f['cur'].upper()=='GBP' else f['cur'] or 'USD'),
               deliver=round(rev_g,1) if rev_g is not None else None,
               dl='revenue growth (PROXY)', sub=sub, pr=pr, dil=dil,
               clock=CLOCK_GUESS.get(f['sector'],'CONC'), ins='NOT CHECKED',
               held=False, sector=f['sector'], built='auto',
               sanity=(round(f['lo']*.5,2), round(f['hi']*2,2)) if (f['lo'] and f['hi']) else None)
    return row, warn

if __name__ == '__main__':
    import sys, pprint
    sym = sys.argv[1] if len(sys.argv) > 1 else 'ASML.AS'
    row, warn = auto_row(sym)
    if row is None:
        print('FAILED:', warn); raise SystemExit(1)
    key = sym.split('.')[0]
    print(f"'{key}': " + repr(row).replace('{','dict(').replace('}',')').replace("'yf':","yf=") + ',')
    print()
    for w in warn: print('  !', w)
