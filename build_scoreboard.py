#!/usr/bin/env python3
import json, os, sys
from datetime import datetime, timezone
import yfinance as yf

W = {'g':.15,'p':.20,'c':.15,'b':.15,'v':.10,'pr':.15,'r':.05,'d':.05}
BANDS = [(3.50,'SELL','p-sell'), (5.50,'HOLD NEG','p-hneg'), (7.00,'HOLD POS','p-hpos'),
         (8.50,'BUY','p-buy'), (999,'STRONG BUY','p-sbuy')]

DATA = {
'ADBE': dict(yf='ADBE',   fcf=9100,   shares=425.0,  r=.080, cur='USD', deliver=10.5, dl='ARR organic', sub=None, pr=8.5, dil=9.5, clock='CONC', ins='MIXED', held=False, sector='Software', built='back-solved', sanity=(200,800)),
'CRM' : dict(yf='CRM',    fcf=12700,  shares=950.0,  r=.080, cur='USD', deliver=14.0, dl='cRPO cc', sub=(7,8,8,7.5,7.5,7), pr=8.0, dil=9.0, clock='CONC', ins='AWARDS', held=False, sector='Software', built='exact', sanity=(120,450)),
'NVDA': dict(yf='NVDA',   fcf=126900, shares=24285., r=.100, cur='USD', deliver=106.0, dl='revenue', sub=(10,10,8,9,6,6), pr=2.5, dil=8.0, clock='CONC', ins='SELLING', held=False, sector='Semis', built='exact', sanity=(80,400), risk_floor=3.4),
'SPGI': dict(yf='SPGI',   fcf=5200,   shares=293.3,  r=.075, cur='USD', deliver=7.0, dl='organic cc', sub=(8,9.5,9,6.5,4.5,9), pr=6.0, dil=9.0, clock='CONC', ins='BUYING', held=False, sector='Info Svcs', built='exact', sanity=(200,600)),
'SAN' : dict(yf='SAN.PA', fcf=6900,   shares=1215.0, r=.080, cur='EUR', deliver=10.0, dl='sales cc', sub=(8,7,7,7,8,8), pr=9.0, dil=8.0, clock='CLOCK', ins='AWARDS', held=True, sector='Pharma', built='exact', sanity=(50,140)),
'APP' : dict(yf='APP',    fcf=4000,   shares=335.29, r=.100, cur='USD', deliver=53.0, dl='revenue', sub=(9,9.5,8,8.5,3.5,7.5), pr=5.0, dil=8.0, clock='CONC', ins='SELLING', held=False, sector='Ad Tech', built='exact', sanity=(100,500)),
'ABT' : dict(yf='ABT',    fcf=7824,   shares=1746.0, r=.075, cur='USD', deliver=7.0, dl='comparable sales', sub=(7,7.5,7,7.5,7.5,8.5), pr=7.5, dil=7.0, clock='DIV', ins='MIXED', held=True, sector='MedTech', built='exact', sanity=(50,200)),
'WKL' : dict(yf='WKL.AS', fcf=1250,   shares=232.52, r=.080, cur='EUR', deliver=5.0, dl='organic revenue', sub=(6,9,8,6,5,7), pr=8.5, dil=7.5, clock='DIV', ins='MIXED', held=True, sector='Info Svcs', built='exact', sanity=(30,150)),
'LVMH': dict(yf='MC.PA',  fcf=13100,  shares=500.0,  r=.080, cur='EUR', deliver=2.0, dl='organic revenue', sub=None, pr=8.0, dil=6.5, clock='CONC', ins='BUYING', held=True, sector='Luxury', built='back-solved', sanity=(300,900)),
'UBER': dict(yf='UBER',   fcf=10000,  shares=2100.0, r=.080, cur='USD', deliver=24.0, dl='gross bookings', sub=(6,7,8,6,8,6), pr=7.5, dil=9.0, clock='DIV', ins='AWARDS', held=True, sector='Platform', built='exact', sanity=(40,150)),
'AVGO': dict(yf='AVGO',   fcf=35000,  shares=4757.0, r=.100, cur='USD', deliver=48.0, dl='revenue', sub=(9.5,9.5,9.5,7.5,2.5,7), pr=2.0, dil=6.0, clock='CONC', ins='', held=False, sector='Semis', built='exact', sanity=(100,1000)),
'ONON': dict(yf='ONON',   fcf=437,    shares=416.0,  r=.090, cur='USD', deliver=21.6, dl='revenue cc', sub=(8.5,8.5,7,9,3.5,1.5), pr=6.0, dil=6.0, clock='CONC', ins='', held=False, sector='Apparel', built='est', sanity=(10,100)),
'VICI': dict(yf='VICI',   fcf=2480,   shares=1000.0, r=.075, cur='USD', deliver=3.3, dl='AFFO/share', sub=None, pr=8.0, dil=3.5, clock='CONC', ins='AWARDS', held=True, sector='REIT', built='back-solved', sanity=(15,60)),
'ISRG': dict(yf='ISRG',   fcf=None,   shares=None,   r=.080, cur='USD', deliver=None, dl='', sub=None, pr=None, dil=6.0, clock='CLOCK', ins='SELLING', held=False, sector='MedTech', built='exact'),
'VST' : dict(yf='VST',    fcf=None,   shares=None,   r=.080, cur='USD', deliver=None, dl='', sub=None, pr=None, dil=6.0, clock='DIV', ins='MIXED', held=False, sector='Utilities', built='exact'),
'AR'  : dict(yf='AR',     fcf=None,   shares=None,   r=.080, cur='USD', deliver=None, dl='', sub=None, pr=None, dil=6.0, clock='DIV', ins='SELLING', held=True, sector='Energy', built='exact'),
'ROL' : dict(yf='ROL',    fcf=None,   shares=None,   r=.080, cur='USD', deliver=None, dl='', sub=None, pr=None, dil=6.0, clock='CONC', ins='SELLING', held=False, sector='Services', built='exact'),
'SE'  : dict(yf='SE',     fcf=None,   shares=None,   r=.080, cur='USD', deliver=None, dl='', sub=None, pr=None, dil=6.0, clock='CONC', ins='SELLING', held=False, sector='Platform', built='back-solved'),
'UNH' : dict(yf='UNH',    fcf=None,   shares=None,   r=.080, cur='USD', deliver=None, dl='', sub=None, pr=None, dil=6.0, clock='DIV', ins='SELLING', held=False, sector='Health Ins', built='back-solved'),
'CNX' : dict(yf='CNX',    fcf=None,   shares=None,   r=.080, cur='USD', deliver=None, dl='', sub=None, pr=None, dil=6.0, clock='DIV', ins='AWARDS', held=False, sector='Energy', built='exact'),
'CMCSA':dict(yf='CMCSA',  fcf=None,   shares=None,   r=.080, cur='USD', deliver=None, dl='', sub=None, pr=None, dil=6.0, clock='CLOCK', ins='SELLING', held=False, sector='Media', built='exact'),
'NVO' : dict(yf='NVO',    fcf=None,   shares=None,   r=.080, cur='USD', deliver=None, dl='', sub=None, pr=None, dil=6.0, clock='CLOCK', ins='REGIME', held=False, sector='Pharma', built='exact'),
'ENG' : dict(yf='ENGI.PA',fcf=None,   shares=None,   r=.075, cur='EUR', deliver=None, dl='', sub=None, pr=None, dil=6.0, clock='CLOCK', ins='BUYING', held=True, sector='Utilities', built='back-solved'),
'ENB' : dict(yf='ENB',    fcf=12900,  shares=2184.0, r=.075, cur='CAD', deliver=5.0, dl='DCF/share CAGR', sub=(5,6,5,3.5,6,8.5), pr=8.5, dil=6.0, clock='CONC', ins='', held=False, sector='Midstream', built='exact', sanity=(20,100)),
'META': dict(yf='META',   fcf=None,   shares=None,   r=.080, cur='USD', deliver=None, dl='', sub=None, pr=None, dil=6.0, clock='CONC', ins='SELLING', held=False, sector='AdTech', built='back-solved'),
'PFE' : dict(yf='PFE',    fcf=9480,   shares=5700.0, r=.080, cur='USD', deliver=-1.8, dl='FY guide', sub=(4,6.5,5.5,4,8.5,7), pr=6.5, dil=5.5, clock='CLOCK', ins='BUYING', held=True, sector='Pharma', built='exact', sanity=(10,60)),
'LULU': dict(yf='LULU',   fcf=None,   shares=None,   r=.080, cur='USD', deliver=None, dl='', sub=None, pr=None, dil=6.0, clock='CONC', ins='', held=False, sector='Apparel', built='est'),
'DVN' : dict(yf='DVN',    fcf=None,   shares=None,   r=.080, cur='USD', deliver=None, dl='', sub=None, pr=None, dil=6.0, clock='DIV', ins='SELLING', held=False, sector='Energy', built='exact'),
'DIS' : dict(yf='DIS',    fcf=None,   shares=None,   r=.080, cur='USD', deliver=None, dl='', sub=None, pr=None, dil=6.0, clock='DIV', ins='AWARDS', held=False, sector='Media', built='back-solved'),
'PEP' : dict(yf='PEP',    fcf=None,   shares=None,   r=.080, cur='USD', deliver=None, dl='', sub=None, pr=None, dil=6.0, clock='DIV', ins='SELLING', held=False, sector='Staples', built='back-solved'),
'BSX' : dict(yf='BSX',    fcf=None,   shares=None,   r=.080, cur='USD', deliver=None, dl='', sub=None, pr=None, dil=6.0, clock='DIV', ins='BUYING', held=False, sector='MedTech', built='exact'),
'WIX' : dict(yf='WIX',    fcf=None,   shares=None,   r=.080, cur='USD', deliver=None, dl='', sub=None, pr=None, dil=6.0, clock='CONC', ins='AWARDS', held=False, sector='Software', built='exact'),
'GRAB': dict(yf='GRAB',   fcf=None,   shares=None,   r=.080, cur='USD', deliver=None, dl='', sub=None, pr=None, dil=6.0, clock='CONC', ins='SELLING', held=False, sector='Platform', built='back-solved'),
'NOW' : dict(yf='NOW',    fcf=None,   shares=None,   r=.080, cur='USD', deliver=None, dl='', sub=None, pr=None, dil=6.0, clock='CONC', ins='SELLING', held=False, sector='Software', built='exact'),
'MCD' : dict(yf='MCD',    fcf=None,   shares=None,   r=.080, cur='USD', deliver=None, dl='', sub=None, pr=None, dil=6.0, clock='DIV', ins='SELLING', held=False, sector='Restaurant', built='back-solved'),
'TTD' : dict(yf='TTD',    fcf=None,   shares=None,   r=.080, cur='USD', deliver=None, dl='', sub=None, pr=None, dil=6.0, clock='CONC', ins='BUYING', held=False, sector='Ad Tech', built='back-solved'),
'PL'  : dict(yf='PL',     fcf=None,   shares=None,   r=.080, cur='USD', deliver=None, dl='', sub=None, pr=None, dil=6.0, clock='CONC', ins='SELLING', held=False, sector='Space', built='exact'),
'TEM' : dict(yf='TEM',    fcf=None,   shares=None,   r=.080, cur='USD', deliver=None, dl='', sub=None, pr=None, dil=6.0, clock='CONC', ins='SELLING', held=False, sector='Health Data', built='exact'),
'NKE' : dict(yf='NKE',    fcf=None,   shares=None,   r=.080, cur='USD', deliver=None, dl='', sub=None, pr=None, dil=6.0, clock='DIV', ins='BUYING', held=False, sector='Apparel', built='exact'),
'ZTS' : dict(yf='ZTS',    fcf=None,   shares=None,   r=.080, cur='USD', deliver=None, dl='', sub=None, pr=None, dil=6.0, clock='CLOCK', ins='BUYING', held=False, sector='Animal Health', built='exact'),
'BA'  : dict(yf='BA',     fcf=None,   shares=None,   r=.080, cur='USD', deliver=None, dl='', sub=None, pr=None, dil=6.0, clock='CONC', ins='BUYING', held=False, sector='Aerospace', built='exact'),
'NBIS': dict(yf='NBIS',   fcf=None,   shares=None,   r=.080, cur='USD', deliver=None, dl='', sub=None, pr=None, dil=6.0, clock='CONC', ins='SELLING', held=False, sector='AI Infra', built='exact'),
'BNTX': dict(yf='BNTX',   fcf=None,   shares=None,   r=.080, cur='USD', deliver=None, dl='', sub=None, pr=None, dil=6.0, clock='CONC', ins='SELLING', held=False, sector='Biotech', built='exact'),
'INTC': dict(yf='INTC',   fcf=None,   shares=None,   r=.080, cur='USD', deliver=None, dl='', sub=None, pr=None, dil=6.0, clock='CONC', ins='BUYING', held=False, sector='Semis', built='exact'),
'IBST': dict(yf='IBST',   fcf=None,   shares=None,   r=.080, cur='USD', deliver=None, dl='', sub=None, pr=None, dil=6.0, clock='CLOCK', ins='REGIME', held=False, sector='Materials', built='exact'),
'OPEN': dict(yf='OPEN',   fcf=None,   shares=None,   r=.080, cur='USD', deliver=None, dl='', sub=None, pr=None, dil=6.0, clock='CONC', ins='BUYING', held=False, sector='Platform', built='exact'),
'CRWV': dict(yf='CRWV',   fcf=None,   shares=None,   r=.080, cur='USD', deliver=None, dl='', sub=None, pr=None, dil=6.0, clock='CLOCK', ins='SELLING', held=False, sector='AI Infra', built='exact'),
'MRNA': dict(yf='MRNA',   fcf=None,   shares=None,   r=.080, cur='USD', deliver=None, dl='', sub=None, pr=None, dil=6.0, clock='CONC', ins='SELLING', held=False, sector='Biotech', built='exact'),
}

# ---------------- Fault-Tolerant Engine ----------------
def ngv(d):
    fcf = d.get('fcf')
    shares = d.get('shares')
    r = d.get('r', 0.08)
    if fcf is None or shares is None or r == 0: return None
    return (fcf / shares) / r

def cover(d):
    n, p = ngv(d), d.get('price')
    return None if (n is None or p is None or p == 0) else n / p

def implied_growth(d):
    c = cover(d)
    r = d.get('r', 0.08)
    return None if c is None else r * (1 - c) / (1 + c * r)

def cushion(d):
    g = implied_growth(d)
    deliver = d.get('deliver')
    return None if (g is None or deliver is None) else deliver - 100 * g

def entry_gap(d, target=.60):
    c = cover(d)
    return None if c is None else c / target - 1

def score(d):
    sub = d.get('sub')
    if not sub or len(sub) != 6: return None
    g, p, c, b, v, r = sub
    core = g*W['g'] + p*W['p'] + c*W['c'] + b*W['b'] + v*W['v'] + r*W['r']
    pr = d.get('pr')
    dil = d.get('dil', 6.0)
    if pr is None: return (core + dil*W['d']) / (1 - W['pr'])
    return core + pr*W['pr'] + dil*W['d']

def risk(d):
    s = score(d)
    if s is None: return None
    sub = d.get('sub')
    bs = sub[3] if (sub and len(sub) == 6) else 6.0
    dil = d.get('dil', 6.0)
    x = 3.0 - 0.40*(bs - 6)/2 - 0.40*(dil - 6)/2
    if d.get('pr') is None: x += 1.0
    cu = cushion(d)
    if cu is not None and cu < 0: x += 0.6
    if s < 3.50: x += 0.5
    x = max(x, d.get('risk_floor', 0))
    return max(1.0, min(5.0, round(x, 1)))

def band(s):
    if s is None: return ('NO SCORE', 'empty')
    for lim, name, css in BANDS:
        if s < lim: return (name, css)
    return ('STRONG BUY', 'p-sbuy')

def verdict(t, d):
    s, rk, cu = score(d), risk(d), cushion(d)
    if s is None: return ('NO SCORE', 'v-hold')
    if d.get('trap'): return ('TRAP BUY', 'v-trap')
    if cu is not None and cu < 0:
        return ('DO NOT ADD', 'v-avoid') if s < 7.00 else ('BUY · CUSHION NEG', 'v-avoid')
    if s >= 7.00:
        return ('BUY · LOW RISK', 'v-buy') if rk <= 2.4 else \
               (('BUY · MOD', 'v-buymod') if rk <= 3.2 else ('BUY · HIGH RISK', 'v-buyhi'))
    if s >= 5.50:
        return ('ACCUMULATE', 'v-acc') if rk <= 2.4 else ('HOLD', 'v-hold')
    return ('AVOID', 'v-avoid') if s >= 3.50 else ('SELL', 'v-sell')

# ---------------- Safe Prices ----------------
def fetch_prices():
    stamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    for t, d in DATA.items():
        d['price'], d['price_ts'], d['price_note'] = None, None, ''
        try:
            yf_ticker = d.get('yf', t)
            tk = yf.Ticker(yf_ticker)
            fi = getattr(tk, 'fast_info', {}) or {}
            px = fi.get('last_price')
            
            if px is None:
                h = tk.history(period='5d', auto_adjust=False)
                if not h.empty and 'Close' in h.columns:
                    px = float(h['Close'].dropna().iloc[-1])
            
            if px is None:
                d['price_note'] = 'no quote'; continue
                
            cur = (fi.get('currency') or '').upper()
            expected_cur = d.get('cur', '').upper()
            if cur and expected_cur and cur != expected_cur:
                d['price_note'] = f'CURRENCY MISMATCH {cur}!={expected_cur}'; continue
                
            lo, hi = d.get('sanity', (0, 1e9))
            if not (lo <= px <= hi):
                d['price_note'] = f'REJECTED {px:.2f} outside {lo}-{hi}'; continue
                
            d['price'], d['price_ts'] = float(px), stamp
        except Exception as e:
            d['price_note'] = f'fetch failed: {type(e).__name__}'

def snapshot():
    os.makedirs('history', exist_ok=True)
    day = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    rec = {t: dict(price=d.get('price'), ngv=ngv(d), cover=cover(d), cushion=cushion(d),
                   score=score(d), risk=risk(d), verdict=verdict(t,d)[0],
                   ts=d.get('price_ts'), note=d.get('price_note'))
           for t,d in DATA.items()}
    with open(f'history/{day}.json','w') as f: json.dump(rec, f, indent=1, default=str)

# ---------------- Safe HTML Render ----------------
def fmt(x, spec, dash='—'):
    return dash if x is None else format(x, spec)

def cls(x, good, bad, invert=False):
    if x is None: return 'pr na'
    if invert: return 'pr pos' if x <= good else ('pr neg' if x >= bad else 'pr mid')
    return 'pr pos' if x >= good else ('pr neg' if x <= bad else 'pr mid')

CLOCK_CSS = {'CLOCK':'s-clock', 'CONC':'s-conc', 'DIV':'s-diverse'}

def build_html():
    out = []
    for i,(t,d) in enumerate(sorted(DATA.items(), key=lambda kv: -(score(kv[1]) or 0)), 1):
        s, rk, c, cu, eg = score(d), risk(d), cover(d), cushion(d), entry_gap(d)
        bn, bc = band(s); vn, vc = verdict(t, d)
        note = d.get('price_note','')
        
        out.append(
          f'<tr{" class=held" if d.get("held") else ""}>'
          f'<td class="rk">{i}</td>'
          f'<td class="tk">{t}{"<sup>&#9679;</sup>" if d.get("held") else ""}</td>'
          f'<td class="hd"></td>'
          f'<td class="se">{d.get("sector","")}</td>'
          f'<td class="sc">{fmt(s,".2f")}</td>'
          f'<td><span class="pill {bc}">{bn}</span></td>'
          f'<td class="{cls(rk,2.4,3.3,invert=True)}">{fmt(rk,".1f")}</td>'
          f'<td><span class="pill {vc}">{vn}</span></td>'
          f'<td class="{cls(None if c is None else c*100,60,35)}">{fmt(None if c is None else c*100,".0f")}%</td>'
          f'<td class="{cls(cu,0.001,-0.001)}">{fmt(cu,"+.1f")}</td>'
          f'<td class="{cls(None if eg is None else eg*100,0,-0.001)}">{fmt(None if eg is None else eg*100,"+.0f")}%</td>'
          f'<td><span class="pill {CLOCK_CSS.get(d.get("clock"),"s-conc")}">{d.get("clock","")}</span></td>'
          f'<td class="in">{d.get("ins","")}</td>'
          f'<td class="li"></td><td class="pr na">—</td>'
          f'<td class="mono">{fmt(ngv(d),",.2f")}</td>'
          f'<td class="mono">{fmt(d.get("price"),",.2f")}'
          f'{f"<br><span style=color:#f06a6a;font-size:8px>{note}</span>" if note else ""}</td>'
          f'<td class="pv {d.get("built","exact")}">{d.get("built","exact")}</td></tr>')
    
    html_content = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>Master Scoreboard — Live</title><style>
:root{{--bg:#0c0d12;--panel:#13151d;--line:#232634;--tx:#e7e9f0;--mu:#8f95a8;--acc:#b98cf0;
--green:#4ecb8a;--red:#f06a6a;--amber:#e5b45c;--cyan:#5cc8d8;}}
*{{box-sizing:border-box}}
body{{background:var(--bg);color:var(--tx);margin:0;padding:30px 16px 40px;font-family:Inter,system-ui,sans-serif;font-size:12.2px;line-height:1.55}}
.kicker{{font-family:ui-monospace,monospace;font-size:10.2px;letter-spacing:.17em;color:var(--cyan);text-transform:uppercase;margin-bottom:8px}}
h1{{font-weight:800;font-size:34px;margin:0 0 12px;line-height:1.06}}
.lede{{color:#c3c7d4;max-width:1030px;margin:0 0 18px;font-size:12.8px}}
table{{width:100%;border-collapse:collapse;font-size:10.4px;margin:6px 0}}
th{{text-align:left;color:var(--mu);font-weight:600;font-size:8.6px;letter-spacing:.06em;text-transform:uppercase;border-bottom:1px solid var(--line);padding:0 4px 7px;vertical-align:bottom}}
td{{border-bottom:1px solid #1a1d27;padding:6px 4px;vertical-align:middle}}
tr.held{{background:#141826}}
.rk{{color:var(--mu);font-family:ui-monospace,monospace;width:22px}}
.tk{{font-weight:700;font-size:11.8px;width:54px}}.tk sup{{color:var(--cyan);font-size:8px}}
.se{{color:#7d8395;font-size:9.4px;width:70px}}
.sc{{font-family:ui-monospace,monospace;font-weight:600;font-size:11.8px;color:var(--green);width:40px}}
.pr{{font-family:ui-monospace,monospace;font-size:10.4px;width:44px}}
.pr.pos{{color:var(--green)}}.pr.mid{{color:var(--amber)}}.pr.neg{{color:var(--red)}}.pr.na{{color:#5e6373}}
.in{{font-family:ui-monospace,monospace;font-size:9px;color:#8f95a8;width:56px}}
.pv{{font-family:ui-monospace,monospace;font-size:8.2px;width:58px}}
.pv.exact{{color:#3f4657}}.pv.back-solved{{color:#8a6a3a}}.pv.est{{color:#a05555}}
.mono{{font-family:ui-monospace,monospace;font-size:10.6px;color:#c3c7d4}}
.pill{{display:inline-block;padding:2px 7px;border-radius:4px;font-size:8.2px;font-weight:700;letter-spacing:.03em;font-family:ui-monospace,monospace;white-space:nowrap}}
.p-sbuy{{background:#123a26;color:#66e39c;border:1px solid #1e5c3c}}
.p-buy{{background:#12331f;color:var(--green);border:1px solid #1d5433}}
.p-hpos{{background:#13202e;color:#7fb6d8;border:1px solid #23405c}}
.p-hneg{{background:#2b2210;color:var(--amber);border:1px solid #574318}}
.p-sell{{background:#331414;color:var(--red);border:1px solid #5c2020}}
.v-buy{{background:#0f3d24;color:#5fe39a;border:1px solid #1e6b40}}
.v-buymod{{background:#12331f;color:var(--green);border:1px solid #1d5433}}
.v-buyhi{{background:#2b2210;color:var(--amber);border:1px solid #574318}}
.v-trap{{background:#2c1440;color:#d6a8ff;border:1px solid #543072}}
.v-acc{{background:#13202e;color:#7fb6d8;border:1px solid #23405c}}
.v-hold{{background:#181a22;color:#8f95a8;border:1px solid #272b38}}
.v-avoid{{background:#2b1a10;color:#d08a5c;border:1px solid #573018}}
.v-sell{{background:#331414;color:var(--red);border:1px solid #5c2020}}
.s-clock{{background:#331414;color:var(--red);border:1px solid #5c2020}}
.s-conc{{background:#2b2210;color:var(--amber);border:1px solid #574318}}
.s-diverse{{background:#12331f;color:var(--green);border:1px solid #1d5433}}
.foot{{color:#5e6373;font-family:ui-monospace,monospace;font-size:9.2px;border-top:1px solid var(--line);padding-top:11px;margin-top:22px}}
</style></head><body>
<div class="kicker">Master Scoreboard · Live Update · {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</div>
<h1>Revision 4A — Automated Repricing</h1>
<div class="lede">GitHub Actions fetching end-of-day prices via Yahoo Finance. NGV logic strictly separated. {len(DATA)} Tickers Tracked.</div>
<!-- UI für den Ticker-Export -->
<div class="box" style="margin-bottom: 20px;">
    <h2>Add Ticker to Model (Export for Claude)</h2>
    <div style="margin-bottom: 10px;">
        <label>1. Wähle eine Gruppe: </label>
        <select id="groupSelect" onchange="filterTickers()" style="background:#1a1d27; color:#e7e9f0; padding:5px; border:1px solid #232634;">
            <option value="All">Alle anzeigen</option>
            <option value="Defensive">Defensive</option>
            <option value="Cyclical">Cyclical</option>
            <option value="Sensitive">Sensitive</option>
            <option value="Growth">Growth</option>
            <option value="High Yield">High Yield</option>
        </select>
    </div>
    <div style="margin-bottom: 10px;">
        <label>2. Wähle eine Aktie: </label>
        <select id="tickerSelect" style="background:#1a1d27; color:#e7e9f0; padding:5px; border:1px solid #232634; width: 300px;">
            <!-- Wird per JS gefüllt -->
        </select>
    </div>
    <button onclick="generateCode()" style="background:#4ecb8a; color:#0c0d12; font-weight:bold; border:none; padding:8px 15px; border-radius:4px; cursor:pointer;">Export Code</button>
    
    <div style="margin-top: 15px;">
        <label class="sub">Kopiere diesen Code für Claude oder deine DATA-Struktur:</label>
        <textarea id="codeOutput" style="width:100%; height:80px; background:#141826; color:#5cc8d8; font-family:monospace; border:1px solid #232634; padding:10px; margin-top:5px;" readonly></textarea>
    </div>
</div>

<!-- Logik zum Filtern und Code generieren -->
<script src="tickers.js"></script>
<script>
    function filterTickers() {
        const group = document.getElementById("groupSelect").value;
        const select = document.getElementById("tickerSelect");
        select.innerHTML = ""; // Leeren
        
        tickerLibrary.forEach(item => {
            if (group === "All" || item.group === group) {
                let option = document.createElement("option");
                option.value = JSON.stringify(item);
                option.text = `${item.yf} - ${item.name} (${item.index})`;
                select.appendChild(option);
            }
        });
    }

    function generateCode() {
        const select = document.getElementById("tickerSelect");
        if (select.selectedIndex === -1) return;
        
        const data = JSON.parse(select.value);
        const internalTicker = data.yf.split('.')[0]; // Entfernt .DE etc für den internen Key
        
        // Generiert die exakte Syntax für dein Python DATA dict
        const code = `'${internalTicker}': dict(yf='${data.yf}', fcf=None, shares=None, r=.080, cur='${data.cur}', deliver=None, dl='', sub=None, pr=None, dil=6.0, clock='CONC', ins='', held=False, sector='${data.sector}', built='exact'),`;
        
        const output = document.getElementById("codeOutput");
        output.value = "Claude, bitte fülle die FCF und Shares Daten für diesen Ticker aus Yahoo Finance ab und gib mir das aktualisierte Dictionary zurück:\n\n" + code;
        
        // Text markieren für einfaches Kopieren
        output.select();
    }

    // Beim Laden initialisieren
    window.onload = function() {
        filterTickers();
    };
</script>

<table><thead><tr><th>#</th><th>Ticker</th><th></th><th>Sector</th><th>Score</th><th>Band</th><th>Risk</th>
<th>Verdict</th><th>Cover</th><th>Cushion</th><th>Entry gap</th><th>Clock</th><th>Insider</th><th></th><th></th><th>NGV</th><th>Price</th><th>Built</th></tr></thead>
<tbody>
{chr(10).join(out)}
</tbody></table>
<div class="foot">Last API pull: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</div>
</body></html>
"""
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

if __name__ == '__main__':
    fetch_prices()
    snapshot()
    build_html()
