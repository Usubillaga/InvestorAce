#!/usr/bin/env python3
"""
INVESTORACE · SCORECARD ENGINE · v6.0  (merged: 58 tickers, chart, auto rows)  (sanity-band fix, self-healing ranges)  (regime classifier + score fallback + bootstrap diagnostics)
Corrected build. Fixes marked [FIX n].

RUN:  python engine.py          -> writes index.html + history/YYYY-MM-DD.json
DEPLOY: GitHub Actions cron -> commit index.html -> GitHub Pages.
"""
import json, os, sys
from datetime import datetime, timezone
import yfinance as yf

W = {'g':.15,'p':.20,'c':.15,'b':.15,'v':.10,'pr':.15,'r':.05,'d':.05}
BANDS = [(3.50,'SELL','p-sell'), (5.50,'HOLD NEG','p-hneg'), (7.00,'HOLD POS','p-hpos'),
         (8.50,'BUY','p-buy'), (999,'STRONG BUY','p-sbuy')]

# [FIX 2] ENGI.PA is ENGIE (French utility). Enagas is ENG.MC (Madrid).
#         Same class of error as SAN.MC/Banco Santander. A wrong ticker returns a
#         plausible price and nothing flags it -- which is why every priced row
#         now carries a sanity band.
# [FIX 3] ENB on NYSE quotes USD. The NGV of C$78.67 is CAD -> use ENB.TO.
# [FIX 4] IBST is IBST.L and London quotes pence (GBp), not GBP.
DATA = {
'ADBE': dict(yf='ADBE',   fcf=9100,   shares=425.0,  r=.080, cur='USD', deliver=10.5, dl='ARR organic',      sub=None,                    pr=8.5, dil=9.5, clock='CONC', ins='MIXED',       held=False, sector='Software',      built='back-solved', sanity=(150,900), score_fixed=7.88, trap=True),
'ASML': dict(yf='ASML.AS', fcf=10000, shares=383.0, r=.080, cur='EUR', deliver=35.0,
    dl='FY26 revenue guidance vs FY25', sub=(9.5,9.5,5.5,7.5,4.5,8.0), pr=4.5, dil=8.0,
    clock='CONC', ins='NOT CHECKED', held=False, sector='Semis', built='est',
    sanity=(300,1600)),
'RIVN': dict(yf='RIVN', fcf=None, shares=1415.0, r=.080, cur='USD', deliver=27.0,
    dl='revenue growth', sub=(7,2,0.5,5.5,6.5,0.5), pr=None, dil=2.0, clock='CONC',
    ins='NOT CHECKED', held=False, sector='Automotive', built='exact', sanity=(3,60),
    na='free cash flow -$1,924m in H1 2026; automotive gross profit still negative'),
'ROAD': dict(yf='ROAD', fcf=150, shares=56.1, r=.090, cur='USD', deliver=14.3,
    dl='backlog growth', sub=(8,6,4,4.5,4,1.5), pr=4.5, dil=5.5, clock='CONC',
    ins='NOT CHECKED', held=False, sector='Industrials', built='est',
    sanity=(25,250)),
'CRM' : dict(yf='CRM',    fcf=12700,  shares=950.0,  r=.080, cur='USD', deliver=14.0, dl='cRPO cc',          sub=(7,8,8,7.5,7.5,7),       pr=8.0, dil=9.0, clock='CONC', ins='AWARDS',      held=False, sector='Software',      built='exact', sanity=(120,450)),
'NVDA': dict(yf='NVDA',   fcf=126900, shares=24285., r=.100, cur='USD', deliver=106.0,dl='revenue',          sub=(10,10,8,9,6,6),         pr=2.5, dil=8.0, clock='CONC', ins='SELLING',     held=False, sector='Semis',         built='exact', sanity=(80,400), risk_floor=3.4),
'SPGI': dict(yf='SPGI',   fcf=5200,   shares=293.3,  r=.075, cur='USD', deliver=7.0,  dl='organic cc',       sub=(8,9.5,9,6.5,4.5,9),     pr=6.0, dil=9.0, clock='CONC', ins='BUYING·LILA', held=False, sector='Info Svcs',     built='exact', sanity=(200,700)),
'SAN' : dict(yf='SAN.PA', fcf=6900,   shares=1215.0, r=.080, cur='EUR', deliver=10.0, dl='sales cc',         sub=(8,7,7,7,8,8),           pr=9.0, dil=8.0, clock='CLOCK',ins='AWARDS',      held=True,  sector='Pharma',        built='exact', sanity=(50,140), weight=6.05),
'APP' : dict(yf='APP',    fcf=4000,   shares=335.29, r=.100, cur='USD', deliver=53.0, dl='revenue',          sub=(9,9.5,8,8.5,3.5,7.5),   pr=5.0, dil=8.0, clock='CONC', ins='SELLING',     held=False, sector='Ad Tech',       built='exact', sanity=(100,700)),
'ABT' : dict(yf='ABT',    fcf=7824,   shares=1746.0, r=.075, cur='USD', deliver=7.0,  dl='comparable sales', sub=(7,7.5,7,7.5,7.5,8.5),   pr=7.5, dil=7.0, clock='DIV',  ins='MIXED',       held=True,  sector='MedTech',       built='exact', sanity=(50,200), weight=1.94),
'WKL' : dict(yf='WKL.AS', fcf=1250,   shares=232.52, r=.080, cur='EUR', deliver=5.0,  dl='organic revenue',  sub=(6,9,8,6,5,7),           pr=8.5, dil=7.5, clock='DIV',  ins='MIXED',       held=True,  sector='Info Svcs',     built='exact', sanity=(30,150), weight=33.92),
'LVMH': dict(yf='MC.PA',  fcf=13100,  shares=500.0,  r=.080, cur='EUR', deliver=2.0,  dl='organic revenue',  sub=None,                    pr=8.0, dil=6.5, clock='CONC', ins='BUYING·LILA', held=True,  sector='Luxury',        built='back-solved', sanity=(300,900), score_fixed=7.16, weight=30.16),
'UBER': dict(yf='UBER',   fcf=10000,  shares=2100.0, r=.080, cur='USD', deliver=24.0, dl='gross bookings',   sub=(6,7,8,6,8,6),           pr=7.5, dil=9.0, clock='DIV',  ins='AWARDS',      held=True,  sector='Platform',      built='exact', sanity=(40,150), weight=16.04),
'AVGO': dict(yf='AVGO',   fcf=35000,  shares=4757.0, r=.100, cur='USD', deliver=48.0, dl='revenue',          sub=(9.5,9.5,9.5,7.5,2.5,7), pr=2.0, dil=6.0, clock='CONC', ins='NOT CHECKED', held=False, sector='Semis',         built='exact', sanity=(100,1000)),
'ONON': dict(yf='ONON',   fcf=437,    shares=416.0,  r=.090, cur='USD', deliver=21.6, dl='revenue cc',       sub=(8.5,8.5,7,9,3.5,1.5),   pr=6.0, dil=6.0, clock='CONC', ins='NOT CHECKED', held=False, sector='Apparel',       built='est',   sanity=(10,120)),
'VICI': dict(yf='VICI',   fcf=2480,   shares=1000.0, r=.075, cur='USD', deliver=3.3,  dl='AFFO/share',       sub=None,                    pr=8.0, dil=3.5, clock='CONC', ins='AWARDS',      held=True,  sector='REIT',          built='back-solved', sanity=(15,60), score_fixed=6.8, weight=2.04),
'ENB' : dict(yf='ENB.TO', fcf=12900,  shares=2184.0, r=.075, cur='CAD', deliver=5.0,  dl='DCF/share CAGR',   sub=(5,6,5,3.5,6,8.5),       pr=8.5, dil=6.0, clock='CONC', ins='NOT CHECKED', held=True,  sector='Midstream',     built='exact', sanity=(30,120), weight=1.65),
'PFE' : dict(yf='PFE',    fcf=9480,   shares=5700.0, r=.080, cur='USD', deliver=-1.8, dl='FY guide vs FY25', sub=(4,6.5,5.5,4,8.5,7),     pr=6.5, dil=5.5, clock='CLOCK',ins='BUYING',      held=True,  sector='Pharma',        built='exact', sanity=(10,60), weight=1.11),
# [FIX 5] NGV inputs restored -- these were computed and then dropped back to None
'ROL' : dict(yf='ROL',    fcf=502,    shares=475.3,  r=.075, cur='USD', deliver=5.7,  dl='organic revenue',  sub=None,                    pr=4.5, dil=6.0, clock='CONC', ins='SELLING',     held=False, sector='Services',      built='exact', sanity=(15,80), score_fixed=6.47),
'LULU': dict(yf='LULU',   fcf=1000,   shares=115.4,  r=.090, cur='USD', deliver=-2.0, dl='comps cc',         sub=(3,5,5.5,9,8,4),         pr=5.5, dil=6.5, clock='CONC', ins='NOT CHECKED', held=False, sector='Apparel',       built='est',   sanity=(80,500)),
'PL'  : dict(yf='PL',     fcf=52.9,   shares=356.0,  r=.100, cur='USD', deliver=42.0, dl='revenue',          sub=(9,4,5.5,7,1.5,1),       pr=2.0, dil=2.5, clock='CONC', ins='SELLING',     held=False, sector='Space',         built='exact', sanity=(2,80)),
# --- NGV N/A by judgement. reason recorded; these will never take a price. -------
'MSFT': dict(yf='MSFT', fcf=66987.0, shares=7425.55, r=0.08, cur='USD', deliver=None, dl='revenue growth (PROXY)', sub=(5.0,5.0,5.0,8.0,5.0,9.0), pr=None, dil=7.0, clock='CONC', ins='NOT CHECKED', held=False, sector='Technology', built='auto', sanity=(174.6,1107.44)),
'AAPL': dict(yf='AAPL', fcf=136683.0, shares=14594.18, r=0.08, cur='USD', deliver=None, dl='revenue growth (PROXY)', sub=(5.0,5.0,5.0,8.0,5.0,9.0), pr=None, dil=8.5, clock='CONC', ins='NOT CHECKED', held=False, sector='Technology', built='auto', sanity=(112.97,689.14)),
'KO': dict(yf='KO', fcf=14297.0, shares=4302.55, r=0.08, cur='USD', deliver=None, dl='revenue growth (PROXY)', sub=(5.0,5.0,5.0,7.0,5.0,6.0), pr=None, dil=7.0, clock='CONC', ins='NOT CHECKED', held=False, sector='Consumer Defensive', built='auto', sanity=(32.67,184.98)),
'CVX': dict(yf='CVX', fcf=27012.0, shares=1961.6, r=0.08, cur='USD', deliver=None, dl='revenue growth (PROXY)', sub=(5.0,5.0,5.0,8.0,5.0,7.5), pr=None, dil=0.5, clock='DIV', ins='NOT CHECKED', held=False, sector='Energy', built='auto', sanity=(73.25,429.42)),
'AMAT': dict(yf='AMAT', fcf=5343.0, shares=793.6, r=0.08, cur='USD', deliver=None, dl='revenue growth (PROXY)', sub=(5.0,5.0,5.0,8.0,5.0,9.0), pr=None, dil=8.5, clock='CONC', ins='NOT CHECKED', held=False, sector='Technology', built='auto', sanity=(77.24,1479.34)),
'PHR': dict(yf='PHR', fcf=63.3, shares=61.77, r=0.08, cur='USD', deliver=None, dl='revenue growth (PROXY)', sub=(5.0,5.0,5.0,8.0,5.0,1.0), pr=None, dil=3.5, clock='CONC', ins='NOT CHECKED', held=False, sector='Healthcare', built='auto', sanity=(3.88,63.66)),
'RCAT': dict(yf='RCAT', fcf=None, shares=152.71, r=0.08, cur='USD', deliver=None, dl='', sub=(5.0,5.0,5.0,6.0,5.0,1.0), pr=None, dil=0.5, clock='CONC', ins='NOT CHECKED', held=False, sector='Industrials', built='auto', sanity=(2.88,37.56), na='free cash flow -157.7m -- a NEGATIVE fcf was written straight into the row, which makes NGV negative'),
'AR'  : dict(yf='AR',     fcf=None, shares=None, r=.080, cur='USD', deliver=None, dl='', sub=(8,8,5,6,6,4),   pr=None, dil=6.0, clock='DIV',  ins='SELLING', held=True,  sector='Energy',      built='exact', na='commodity producer', weight=4.18),
'DVN' : dict(yf='DVN',    fcf=None, shares=None, r=.080, cur='USD', deliver=None, dl='', sub=(6,7,3,5,7,7),   pr=None, dil=5.0, clock='DIV',  ins='SELLING', held=False, sector='Energy',      built='exact', na='commodity producer'),
'CNX' : dict(yf='CNX',    fcf=None, shares=None, r=.080, cur='USD', deliver=None, dl='', sub=(3.5,6.5,7.5,6,7.5,8), pr=None, dil=6.5, clock='DIV', ins='AWARDS', held=False, sector='Energy', built='exact', na='commodity producer'),
'MRNA': dict(yf='MRNA',   fcf=None, shares=None, r=.080, cur='USD', deliver=None, dl='', sub=None, pr=None, dil=5.0, clock='CONC', ins='SELLING', held=False, sector='Biotech',  built='exact', na='FCF deeply negative', score_fixed=2.97),
'BNTX': dict(yf='BNTX',   fcf=None, shares=None, r=.080, cur='USD', deliver=None, dl='', sub=None, pr=None, dil=7.5, clock='CONC', ins='SELLING', held=False, sector='Biotech',  built='exact', na='FCF negative', score_fixed=4.29),
'INTC': dict(yf='INTC',   fcf=None, shares=None, r=.080, cur='USD', deliver=None, dl='', sub=None, pr=None, dil=1.0, clock='CONC', ins='BUYING',  held=False, sector='Semis',    built='exact', na='adj. FCF -$8.4bn in the quarter', score_fixed=4.15),
'CRWV': dict(yf='CRWV',   fcf=None, shares=None, r=.080, cur='USD', deliver=None, dl='', sub=None, pr=None, dil=0.5, clock='CLOCK',ins='SELLING', held=False, sector='AI Infra', built='exact', na='no steady-state FCF', score_fixed=3.41),
'NBIS': dict(yf='NBIS',   fcf=None, shares=None, r=.080, cur='USD', deliver=None, dl='', sub=None, pr=None, dil=1.5, clock='CONC', ins='SELLING', held=False, sector='AI Infra', built='exact', na='no steady-state FCF', score_fixed=4.29),
'OPEN': dict(yf='OPEN',   fcf=None, shares=None, r=.080, cur='USD', deliver=None, dl='', sub=None, pr=None, dil=6.0, clock='CONC', ins='BUYING',  held=False, sector='Platform', built='exact', na='FCF tracks the inventory cycle', score_fixed=3.44),
'BA'  : dict(yf='BA',     fcf=None, shares=None, r=.080, cur='USD', deliver=None, dl='', sub=(6.5,3,4.5,5,4,1.5), pr=None, dil=5.5, clock='CONC', ins='BUYING', held=False, sector='Aerospace', built='exact', na='trailing FCF negative; guide is a forecast'),
'TEM' : dict(yf='TEM',    fcf=None, shares=None, r=.080, cur='USD', deliver=None, dl='', sub=(8,3.5,4,6,4,0.5), pr=None, dil=2.5, clock='CONC', ins='SELLING', held=False, sector='Health Data', built='exact', na='operating cash flow negative'),
# --- awaiting FCF + shares. price will fetch; NGV stays None until filled. ------
'ISRG': dict(yf='ISRG',   fcf=None, shares=None, r=.080, cur='USD', deliver=None, dl='', sub=None, pr=2.5, dil=8.0, clock='CLOCK',ins='SELLING', held=False, sector='MedTech',    built='back-solved', score_fixed=6.65),
'VST' : dict(yf='VST',    fcf=None, shares=None, r=.080, cur='USD', deliver=None, dl='', sub=None, pr=6.0, dil=8.5, clock='DIV',  ins='MIXED',   held=False, sector='Utilities',  built='back-solved', score_fixed=6.58),
'SE'  : dict(yf='SE',     fcf=None, shares=None, r=.080, cur='USD', deliver=None, dl='', sub=None, pr=5.5, dil=4.5, clock='CONC', ins='SELLING', held=False, sector='Platform',   built='back-solved', score_fixed=6.47),
'UNH' : dict(yf='UNH',    fcf=None, shares=None, r=.080, cur='USD', deliver=None, dl='', sub=None, pr=5.5, dil=8.5, clock='DIV',  ins='SELLING', held=False, sector='Health Ins', built='back-solved', score_fixed=6.35),
'CMCSA':dict(yf='CMCSA',  fcf=None, shares=None, r=.080, cur='USD', deliver=None, dl='', sub=None, pr=9.5, dil=6.0, clock='CLOCK',ins='SELLING', held=False, sector='Media',      built='back-solved', score_fixed=6.25),
'NVO' : dict(yf='NVO',    fcf=None, shares=None, r=.080, cur='USD', deliver=None, dl='', sub=None, pr=6.0, dil=6.0, clock='CLOCK',ins='REGIME',  held=False, sector='Pharma',     built='back-solved', score_fixed=6.15),
'ENG' : dict(yf='ENG.MC', fcf=None, shares=None, r=.075, cur='EUR', deliver=-8.6,dl='recurring net profit', sub=None, pr=8.0, dil=6.0, clock='CLOCK', ins='BUYING', held=True, sector='Utilities', built='back-solved', sanity=(5,40), score_fixed=6.0, na='regulated network: total-capex FCF is the wrong line, needs FFO or DCF per share like ENB', weight=2.92),
'META': dict(yf='META',   fcf=None, shares=None, r=.080, cur='USD', deliver=None, dl='', sub=None, pr=3.0, dil=8.0, clock='CONC', ins='SELLING', held=False, sector='AdTech',     built='back-solved', score_fixed=5.83),
'DIS' : dict(yf='DIS',    fcf=None, shares=None, r=.080, cur='USD', deliver=None, dl='', sub=None, pr=4.0, dil=9.0, clock='DIV',  ins='AWARDS',  held=False, sector='Media',      built='back-solved', score_fixed=5.62),
'PEP' : dict(yf='PEP',    fcf=None, shares=None, r=.080, cur='USD', deliver=None, dl='', sub=None, pr=5.0, dil=7.0, clock='DIV',  ins='SELLING', held=False, sector='Staples',    built='back-solved', score_fixed=5.5),
'BSX' : dict(yf='BSX',    fcf=None, shares=None, r=.080, cur='USD', deliver=None, dl='', sub=None, pr=4.0, dil=6.0, clock='DIV',  ins='BUYING·LILA', held=False, sector='MedTech',built='exact', score_fixed=5.4),
'WIX' : dict(yf='WIX',    fcf=None, shares=None, r=.080, cur='USD', deliver=None, dl='', sub=(6,3,4,2,8,5), pr=9.5, dil=8.5, clock='CONC', ins='AWARDS', held=False, sector='Software', built='exact'),
'GRAB': dict(yf='GRAB',   fcf=None, shares=None, r=.080, cur='USD', deliver=None, dl='', sub=None, pr=2.5, dil=5.5, clock='CONC', ins='SELLING', held=False, sector='Platform',   built='back-solved', score_fixed=5.23, na='TTM IFRS free cash flow negative (-186m)'),
'NOW' : dict(yf='NOW',    fcf=None, shares=None, r=.080, cur='USD', deliver=None, dl='', sub=None, pr=2.0, dil=6.0, clock='CONC', ins='SELLING', held=False, sector='Software',   built='exact', score_fixed=5.22),
'MCD' : dict(yf='MCD',    fcf=None, shares=None, r=.080, cur='USD', deliver=None, dl='', sub=None, pr=2.5, dil=7.0, clock='DIV',  ins='SELLING', held=False, sector='Restaurant', built='back-solved', score_fixed=5.2),
'TTD' : dict(yf='TTD',    fcf=None, shares=None, r=.080, cur='USD', deliver=None, dl='', sub=None, pr=2.5, dil=9.0, clock='CONC', ins='BUYING',  held=False, sector='Ad Tech',    built='back-solved', score_fixed=4.7),
'NKE' : dict(yf='NKE',    fcf=None, shares=None, r=.080, cur='USD', deliver=None, dl='', sub=None, pr=4.5, dil=7.0, clock='DIV',  ins='BUYING',  held=False, sector='Apparel',    built='exact', score_fixed=4.6),
'ZTS' : dict(yf='ZTS',    fcf=None, shares=None, r=.080, cur='USD', deliver=None, dl='', sub=None, pr=4.5, dil=6.0, clock='CLOCK',ins='BUYING',  held=False, sector='Animal Health', built='exact', score_fixed=4.55),
'IBST': dict(yf='IBST.L', fcf=None, shares=None, r=.080, cur='GBp', deliver=None, dl='', sub=None, pr=2.5, dil=6.0, clock='CLOCK',ins='REGIME',  held=False, sector='Materials',  built='exact', sanity=(50,400), score_fixed=3.7, na='free cash flow negative (-7m) in a UK housing downturn'),
'ADSK': dict(yf='ADSK', fcf=2694.0, shares=211.15, r=0.08, cur='USD', deliver=22.4, dl='revenue growth (PROXY)', sub=(8.5, 7.5, 9.5, 8.0, 5.0, 6.0), pr=None, dil=8.5, clock='CONC', ins='NOT CHECKED', held=False, sector='Technology', built='auto', sanity=(92.75, 658.18)),
'GILD': dict(yf='GILD', fcf=12943.0, shares=1239.96, r=0.08, cur='USD', deliver=5.9, dl='revenue growth (PROXY)', sub=(5.5, 9.0, 9.5, 1.5, 5.0, 6.0), pr=None, dil=7.0, clock='CONC', ins='NOT CHECKED', held=False, sector='Healthcare', built='auto', sanity=(54.23, 314.58)),
'AG': dict(yf='AG', fcf=614.1, shares=492.91, r=0.08, cur='USD', deliver=192.7, dl='revenue growth (PROXY)', sub=(9.5, 9.0, 9.5, 9.5, 5.0, 9.0), pr=None, dil=5.5, clock='CONC', ins='NOT CHECKED', held=False, sector='Basic Materials', built='auto', sanity=(4.5, 64.08)),
'BABA': dict(yf='BABA', fcf=None, shares=2485.62, r=0.08, cur='USD', deliver=2.7, dl='revenue growth (PROXY)', sub=(4.0, 4.0, 1.5, 7.0, 5.0, 9.0), pr=None, dil=9.5, clock='CONC', ins='NOT CHECKED', held=False, sector='Consumer Cyclical', built='auto', sanity=(45.99, 385.34), na='FCF non-positive (-50,724.0m from Yahoo); NGV intentionally disabled until a model-appropriate metric is supplied'),
'BYRN': dict(yf='BYRN', fcf=None, shares=22.8, r=0.08, cur='USD', deliver=26.9, dl='revenue growth (PROXY)', sub=(8.5, 2.0, 1.5, 6.0, 5.0, 1.0), pr=None, dil=5.5, clock='CONC', ins='NOT CHECKED', held=False, sector='Industrials', built='auto', sanity=(1.59, 61.24), na='FCF non-positive (-0.5m from Yahoo); NGV intentionally disabled until a model-appropriate metric is supplied'),
}

# ---------------- engine ----------------
def ngv(d):
    f, s, r = d.get('fcf'), d.get('shares'), d.get('r', .08)
    return None if (f is None or s is None or not r) else (f/s)/r

def cover(d):
    n, p = ngv(d), d.get('price')
    return None if (n is None or not p) else n/p

def implied_growth(d):
    c, r = cover(d), d.get('r', .08)
    return None if c is None else r*(1-c)/(1+c*r)

def cushion(d):
    g, dv = implied_growth(d), d.get('deliver')
    return None if (g is None or dv is None) else dv - 100*g

def entry_price(d, target=.60):
    n = ngv(d);  return None if n is None else n/target

def entry_gap(d, target=.60):
    c = cover(d);  return None if c is None else c/target - 1

def priced_in_live(d):
    """[FIX] cover is live, pr was static. When the price moved, cover updated
       and the SCORE DID NOT -- the stale-cover bug one level up. Derive pr from
       cover on every run; fall back to the stored value when there is no price.
       Same mapping used by autoscore, including the Pfizer rule: a negative
       cushion costs 2.0 points however good the cover looks."""
    c = cover(d)
    if c is None: return d.get('pr')
    pct = c * 100
    for hi, v in ((15,1.5),(25,2.5),(35,3.0),(45,4.5),(60,5.5),(75,7.0),(90,8.0),(100,9.0),(1e9,9.5)):
        if pct < hi: pr = v; break
    cu = cushion(d)
    if cu is not None and cu < 0: pr = max(1.0, pr - 2.0)
    return round(pr, 1)

def score(d):
    """[FIX] 28 of 48 rows had sub=None, so score() returned None, so risk()
       returned None, so verdict() said NO SCORE -- four blank columns per row.
       Those rows DO have a published total from the master sheet; only the
       category splits are missing. Fall back to it and flag the provenance."""
    sub = d.get('sub')
    if not sub or len(sub) != 6: return d.get('score_fixed')
    g,p,c,b,v,r = sub
    core = g*W['g']+p*W['p']+c*W['c']+b*W['b']+v*W['v']+r*W['r']
    dil = d.get('dil', 6.0)
    pr = priced_in_live(d)                     # live, not the stored constant
    return (core + dil*W['d'])/(1-W['pr']) if pr is None else core + pr*W['pr'] + dil*W['d']

def risk(d):
    s = score(d)
    if s is None: return None
    sub = d.get('sub'); dil = d.get('dil', 6.0)
    bs = sub[3] if (sub and len(sub)==6) else 6.0
    x = 3.0 - .40*(bs-6)/2 - .40*(dil-6)/2
    if priced_in_live(d) is None: x += 1.0
    cu = cushion(d)
    if cu is not None and cu < 0: x += .6
    if s < 3.50: x += .5
    return max(1.0, min(5.0, round(max(x, d.get('risk_floor', 0)), 1)))

def band(s):
    if s is None: return ('NO SCORE','empty')
    for lim,name,css in BANDS:
        if s < lim: return (name,css)
    return ('STRONG BUY','p-sbuy')

def verdict(t, d):
    s, rk, cu = score(d), risk(d), cushion(d)
    if s is None: return ('NO SCORE','v-hold')
    if d.get('trap'): return ('TRAP BUY','v-trap')
    if cu is not None and cu < 0:
        return ('DO NOT ADD','v-avoid') if s < 7.00 else ('BUY · CUSHION NEG','v-avoid')
    if s >= 7.00:
        return ('BUY · LOW RISK','v-buy') if rk <= 2.4 else \
               (('BUY · MOD','v-buymod') if rk <= 3.2 else ('BUY · HIGH RISK','v-buyhi'))
    if s >= 5.50:
        return ('ACCUMULATE','v-acc') if rk <= 2.4 else ('HOLD','v-hold')
    return ('AVOID','v-avoid') if s >= 3.50 else ('SELL','v-sell')


# =====================================================================
# MACRO REGIME FIT
# Five regimes on the growth x inflation grid. Scored 0-100 per ticker,
# mechanically, from four inputs -- not from a feel for the sector.
#
# The key idea: COVER IS DURATION. A row with 25% cover holds three
# quarters of its value in far-future cash flows, so a rising discount
# rate destroys it. A row with 98% cover is short-duration -- its value
# is cash already produced. That is why NVDA and WKL sit at opposite
# ends of the stagflation column despite both being "good businesses".
# =====================================================================
REGIMES = ['GOLDILOCKS', 'REFLATION', 'INFLATION', 'STAGFLATION', 'RECESSION']
REGIME_CSS = {'GOLDILOCKS':'g-gold','REFLATION':'g-refl','INFLATION':'g-infl',
              'STAGFLATION':'g-stag','RECESSION':'g-rec'}

# sector affinity, -2 to +2
AFF = {
'GOLDILOCKS': {'Technology':2,'Consumer Defensive':-1,'Healthcare':0,'Semis':2,'Software':2,'AI Infra':2,'Ad Tech':2,'AdTech':2,'Platform':2,'Space':2,
    'MedTech':1,'Luxury':1,'Apparel':1,'Info Svcs':1,'Health Data':1,'Biotech':1,
    'Services':0,'Industrials':0,'Automotive':1,'Media':0,'Restaurant':0,'Animal Health':0,'Aerospace':0,
    'Staples':-1,'Utilities':-1,'REIT':-1,'Health Ins':-1,'Pharma':-1,
    'Energy':-2,'Midstream':-2,'Materials':-2},
'REFLATION': {'Technology':1,'Consumer Defensive':-1,'Healthcare':-1,'Energy':2,'Materials':2,'Aerospace':2,'Midstream':2,
    'Semis':1,'Luxury':1,'Apparel':1,'Platform':1,'Media':1,'Restaurant':1,
    'Software':0,'Industrials':2,'Automotive':2,'Info Svcs':0,'Services':0,'MedTech':0,'Space':0,'Health Data':0,'Ad Tech':0,'AdTech':0,'Animal Health':0,
    'Staples':-1,'Utilities':-1,'Pharma':-1,'Health Ins':-1,'REIT':-2,'Biotech':-2,'AI Infra':0},
'INFLATION': {'Technology':-1,'Consumer Defensive':1,'Healthcare':0,'Energy':2,'Midstream':2,'Materials':2,'REIT':2,'Utilities':2,
    'Staples':1,'Restaurant':1,'Info Svcs':1,'Luxury':1,
    'MedTech':0,'Industrials':1,'Automotive':-1,'Pharma':0,'Services':0,'Health Ins':0,'Aerospace':0,'Animal Health':0,
    'Software':-1,'Platform':-1,'Apparel':-1,'Media':-1,
    'Semis':-2,'AI Infra':-2,'Space':-2,'Biotech':-2,'Ad Tech':-2,'AdTech':-2,'Health Data':-2},
'STAGFLATION': {'Technology':-2,'Consumer Defensive':1,'Healthcare':0,'Energy':2,'Midstream':2,'Materials':2,
    'Utilities':1,'REIT':1,'Staples':1,'Info Svcs':1,
    'Pharma':0,'Industrials':-1,'Automotive':-2,'MedTech':0,'Health Ins':0,'Restaurant':0,'Services':0,'Animal Health':0,
    'Luxury':-1,'Apparel':-1,'Media':-1,'Platform':-1,'Aerospace':-1,
    'Semis':-2,'Software':-2,'AI Infra':-2,'Space':-2,'Biotech':-2,'Ad Tech':-2,'AdTech':-2,'Health Data':-2},
'RECESSION': {'Technology':0,'Consumer Defensive':2,'Healthcare':2,'Staples':2,'Pharma':2,'Utilities':2,'Health Ins':2,
    'MedTech':1,'Info Svcs':1,'Services':1,'Animal Health':1,'REIT':1,
    'Software':0,'Industrials':-1,'Automotive':-2,'Media':0,'Restaurant':0,'Midstream':0,
    'Luxury':-1,'Apparel':-1,'Platform':-1,'Semis':-1,'Materials':-1,'Aerospace':-1,'Energy':-1,
    'AI Infra':-2,'Space':-2,'Biotech':-2,'Ad Tech':-2,'AdTech':-2,'Health Data':-2},
}
# how hard duration, balance sheet and payout bite in each regime
DUR_W = {'GOLDILOCKS':-0.35,'REFLATION':0.00,'INFLATION':0.45,'STAGFLATION':0.55,'RECESSION':0.45}
BS_W  = {'GOLDILOCKS':0.5,'REFLATION':0.5,'INFLATION':1.5,'STAGFLATION':2.5,'RECESSION':3.0}
PAY_W = {'GOLDILOCKS':0.5,'REFLATION':0.5,'INFLATION':1.5,'STAGFLATION':1.5,'RECESSION':1.5}

def regime_scores(d):
    """0-100 per regime. Returns {} when there is no cover, because duration is
       the single largest term and without it the answer would be a sector guess."""
    c = cover(d)
    if c is None: return {}
    sec = d.get('sector','')
    sub = d.get('sub')
    bs  = sub[3] if (sub and len(sub)==6) else 6.0
    pay = sub[5] if (sub and len(sub)==6) else 6.0
    dur = max(-40.0, min(40.0, (c - 0.60) * 100))      # cover above/below the GOOD line
    out = {}
    for r in REGIMES:
        v = 50.0 + 12.0*AFF[r].get(sec, 0) + DUR_W[r]*dur + BS_W[r]*(bs-6) + PAY_W[r]*(pay-6)
        out[r] = round(max(0.0, min(100.0, v)), 1)
    return out

def best_regime(d):
    s = regime_scores(d)
    if not s: return (None, None)
    r = max(s, key=s.get)
    return (r, s[r])

# ---------------- prices ----------------


def _valid_band(b):
    """A band is usable only if it is a real interval. (0,0) is not a band --
       it is a missing one, and rejecting every price because the RANGE is
       absent confuses 'unknown' with 'wrong'."""
    try:
        lo, hi = b
        return hi > 0 and hi > lo and lo >= 0
    except Exception:
        return False

def _year_range(tk, fi):
    """fast_info key names vary by yfinance version. Try all of them, then fall
       back to a year of history."""
    for lo_k, hi_k in (('year_low','year_high'), ('yearLow','yearHigh'),
                       ('fiftyTwoWeekLow','fiftyTwoWeekHigh')):
        lo, hi = fi.get(lo_k), fi.get(hi_k)
        if lo and hi: return float(lo), float(hi)
    try:
        h = tk.history(period='1y', auto_adjust=False)
        if h is not None and not h.empty:
            return float(h['Low'].min()), float(h['High'].max())
    except Exception:
        pass
    return None, None

def bootstrap_fundamentals():
    """Fill fcf and shares from Yahoo ONLY where both are missing and the row is
       not flagged na. Marks built='yahoo-draft' so the table shows you which
       numbers are unverified. REITs (AFFO) and pipelines (DCF) already carry
       manual values and are left alone -- Yahoo's FCF line is wrong for them."""
    for t, d in DATA.items():
        if d.get('na') or (d.get('fcf') is not None and d.get('shares') is not None):
            continue                       # [FIX] was skipping rows where only ONE field was set
        why = []
        try:
            tk = yf.Ticker(d.get('yf', t))
            fi = {}
            try: fi = dict(tk.fast_info) or {}
            except Exception: pass
            sh = fi.get('shares')
            if not sh:
                try: sh = (tk.get_info() or {}).get('sharesOutstanding')
                except Exception: sh = None
            fcf = None
            for getter, n in ((lambda: tk.quarterly_cashflow, 4), (lambda: tk.cashflow, 1)):
                try:
                    cf = getter()
                    if cf is None or cf.empty: continue
                    idx = {str(i).strip().lower(): i for i in cf.index}
                    def row(*names):
                        for nm in names:
                            if nm in idx: return cf.loc[idx[nm]]
                        return None
                    fr = row('free cash flow')
                    if fr is not None:
                        v = [float(x) for x in fr.iloc[:n] if x == x and x is not None]
                        if v: fcf = sum(v); break
                    o, c = row('operating cash flow'), row('capital expenditure')
                    if o is not None and c is not None:
                        p = [(float(a), float(b)) for a, b in zip(o.iloc[:n], c.iloc[:n])
                             if a == a and b == b]
                        if p: fcf = sum(a + b for a, b in p); break
                except Exception:
                    continue
            if sh is None: why.append('no share count')
            if fcf is None: why.append('no cash-flow line')
            elif fcf <= 0: why.append(f'FCF negative ({fcf/1e6:,.0f}m) -> needs na="reason"')
            if why:
                d['boot_note'] = '; '.join(why)      # [FIX] surface it instead of silent continue
                continue
            d['fcf'] = round(fcf / 1e6, 1)
            d['shares'] = round(sh / 1e6, 2)
            d['built'] = 'yahoo-draft'
            if not _valid_band(d.get('sanity')):
                lo, hi = _year_range(tk, fi)
                if lo and hi: d['sanity'] = (round(lo * .5, 2), round(hi * 2, 2))
        except Exception as e:
            d['boot_note'] = f'bootstrap failed: {type(e).__name__}'


def portfolio_regime():
    """Regime fit of the BOOK, weighted by position size.

       Averaging regime scores across all 51 tickers is close to meaningless --
       the mean is set by the sector mix and barely moves. What actually changes
       as prices move is where YOUR MONEY sits on the growth/inflation grid.
       That is the line worth plotting."""
    tot = 0.0; acc = {r: 0.0 for r in REGIMES}
    for t, d in DATA.items():
        w = d.get('weight'); sc = regime_scores(d)
        if not w or not sc: continue
        tot += w
        for r in REGIMES: acc[r] += w * sc[r]
    if not tot: return {}
    return {r: round(acc[r]/tot, 1) for r in REGIMES}

def regime_history():
    """Read history/*.json and return (dates, {regime: [values]}) for the chart."""
    import glob
    dates, series = [], {r: [] for r in REGIMES}
    for fp in sorted(glob.glob('history/*.json')):
        try:
            with open(fp) as f: day = json.load(f)
        except Exception:
            continue
        pf = day.get('_portfolio')
        if not pf:                       # older snapshots: rebuild from the rows
            tot = 0.0; acc = {r: 0.0 for r in REGIMES}
            for t, m in day.items():
                if t.startswith('_'): continue
                w, rg = m.get('weight'), m.get('regime') or {}
                if not w or not rg: continue
                tot += w
                for r in REGIMES: acc[r] += w * float(rg.get(r, 0))
            if not tot: continue
            pf = {r: round(acc[r]/tot, 1) for r in REGIMES}
        dates.append(os.path.basename(fp)[:-5])
        for r in REGIMES: series[r].append(pf.get(r))
    return dates, series

def fetch_prices():
    stamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    for t, d in DATA.items():
        d['price'], d['price_ts'], d['price_note'] = None, None, ''
        if d.get('na'):
            d['price_note'] = 'N/A: ' + d['na']; continue          # never price an N/A row
        try:
            tk = yf.Ticker(d.get('yf', t))
            fi = {}
            try: fi = dict(tk.fast_info) or {}
            except Exception: fi = {}
            px = fi.get('last_price') or fi.get('lastPrice')
            if px is None:
                h = tk.history(period='5d', auto_adjust=False)
                if not h.empty and 'Close' in h:
                    ser = h['Close'].dropna()
                    if len(ser): px = float(ser.iloc[-1])
            if px is None:
                d['price_note'] = 'no quote'; continue
            cur = str(fi.get('currency') or '').strip()
            if cur and cur.upper() != d.get('cur','').upper():
                d['price_note'] = f'CURRENCY {cur} != {d.get("cur")}'; continue
            band = d.get('sanity')
            if not _valid_band(band):
                lo, hi = _year_range(tk, fi)          # self-heal: build one now
                if lo and hi:
                    band = (round(lo * .5, 2), round(hi * 2, 2)); d['sanity'] = band
            if _valid_band(band):
                lo, hi = band
                if not (lo <= px <= hi):
                    d['price_note'] = f'REJECTED {px:.2f} outside {lo}-{hi}'; continue
            else:
                d['price_note'] = f'accepted UNBOUNDED at {px:.2f} - no 52w range, set sanity by hand'
            d['price'], d['price_ts'] = float(px), stamp
        except Exception as e:
            d['price_note'] = f'fetch failed: {type(e).__name__}'

def snapshot():
    os.makedirs('history', exist_ok=True)
    day = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    rec = {t: dict(price=d.get('price'), ngv=ngv(d), cover=cover(d), cushion=cushion(d),
                   score=score(d), risk=risk(d), verdict=verdict(t,d)[0],
                   regime=regime_scores(d), weight=d.get('weight'),
                   ts=d.get('price_ts'), note=d.get('price_note')) for t,d in DATA.items()}
    rec['_portfolio'] = portfolio_regime()
    with open(f'history/{day}.json','w') as f: json.dump(rec, f, indent=1, default=str)
    return day

# ---------------- render ----------------
def fmt(x, spec, dash='—'):  return dash if x is None else format(x, spec)

def cls(x, good, bad, invert=False):
    if x is None: return 'pr na'
    if invert: return 'pr pos' if x <= good else ('pr neg' if x >= bad else 'pr mid')
    return 'pr pos' if x >= good else ('pr neg' if x <= bad else 'pr mid')

CLOCK_CSS = {'CLOCK':'s-clock','CONC':'s-conc','DIV':'s-diverse'}
REG_CSS = {'GOLDILOCKS':'g-gold','REFLATION':'g-refl','INFLATION':'g-infl',
           'STAGFLATION':'g-stag','RECESSION':'g-rec'}

CSS = """
:root{--bg:#0c0d12;--panel:#13151d;--line:#232634;--tx:#e7e9f0;--mu:#8f95a8;
--green:#4ecb8a;--red:#f06a6a;--amber:#e5b45c;--cyan:#5cc8d8;}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--tx);margin:0;padding:26px 14px 40px;
font-family:Inter,system-ui,sans-serif;font-size:12.2px;line-height:1.5}
.kicker{font-family:ui-monospace,monospace;font-size:10px;letter-spacing:.17em;color:var(--cyan);text-transform:uppercase;margin-bottom:8px}
h1{font-weight:800;font-size:30px;margin:0 0 10px}
h2{font-size:16px;margin:0 0 8px}
.lede{color:#c3c7d4;max-width:1030px;margin:0 0 16px;font-size:12.5px}
.box{border:1px solid var(--line);border-radius:10px;padding:14px 15px;background:var(--panel);margin-bottom:14px}
table{width:100%;border-collapse:collapse;font-size:10.4px}
th{text-align:left;color:var(--mu);font-weight:600;font-size:8.6px;letter-spacing:.06em;text-transform:uppercase;border-bottom:1px solid var(--line);padding:0 4px 7px}
td{border-bottom:1px solid #1a1d27;padding:6px 4px;vertical-align:middle}
tr.held{background:#141826}
.rk{color:var(--mu);font-family:ui-monospace,monospace;width:22px}
.tk{font-weight:700;font-size:11.6px;width:54px}.tk sup{color:var(--cyan);font-size:8px}
.se{color:#7d8395;font-size:9.2px;width:70px}
.sc{font-family:ui-monospace,monospace;font-weight:600;font-size:11.6px;color:var(--green);width:40px}
.pr{font-family:ui-monospace,monospace;font-size:10.4px;width:44px}
.pr.pos{color:var(--green)}.pr.mid{color:var(--amber)}.pr.neg{color:var(--red)}.pr.na{color:#5e6373}
.in{font-family:ui-monospace,monospace;font-size:8.6px;color:#8f95a8;width:58px}
.pv{font-family:ui-monospace,monospace;font-size:8.2px;width:58px}
.pv.exact{color:#3f4657}.pv.back-solved{color:#8a6a3a}.pv.est{color:#a05555}
.mono{font-family:ui-monospace,monospace;font-size:10.4px;color:#c3c7d4}
.pill{display:inline-block;padding:2px 7px;border-radius:4px;font-size:8.2px;font-weight:700;font-family:ui-monospace,monospace;white-space:nowrap}
.p-sbuy{background:#123a26;color:#66e39c;border:1px solid #1e5c3c}
.p-buy{background:#12331f;color:var(--green);border:1px solid #1d5433}
.p-hpos{background:#13202e;color:#7fb6d8;border:1px solid #23405c}
.p-hneg{background:#2b2210;color:var(--amber);border:1px solid #574318}
.p-sell{background:#331414;color:var(--red);border:1px solid #5c2020}
.empty{background:#181a22;color:#6b7183;border:1px solid #272b38}
.v-buy{background:#0f3d24;color:#5fe39a;border:1px solid #1e6b40}
.v-buymod{background:#12331f;color:var(--green);border:1px solid #1d5433}
.v-buyhi{background:#2b2210;color:var(--amber);border:1px solid #574318}
.v-trap{background:#2c1440;color:#d6a8ff;border:1px solid #543072}
.v-acc{background:#13202e;color:#7fb6d8;border:1px solid #23405c}
.v-hold{background:#181a22;color:#8f95a8;border:1px solid #272b38}
.v-avoid{background:#2b1a10;color:#d08a5c;border:1px solid #573018}
.v-sell{background:#331414;color:var(--red);border:1px solid #5c2020}
.s-clock{background:#331414;color:var(--red);border:1px solid #5c2020}
.s-conc{background:#2b2210;color:var(--amber);border:1px solid #574318}
.s-diverse{background:#12331f;color:var(--green);border:1px solid #1d5433}
.g-gold{background:#123a26;color:#66e39c;border:1px solid #1e5c3c}
.g-refl{background:#12283a;color:#63c6f0;border:1px solid #1d4a6b}
.g-infl{background:#3a2c10;color:#e5b45c;border:1px solid #6b5218}
.g-stag{background:#3a1414;color:#f06a6a;border:1px solid #6b2020}
.g-rec{background:#2c1440;color:#d6a8ff;border:1px solid #543072}
input,select,textarea{background:#0a0b10;color:var(--tx);border:1px solid #2a2e3c;border-radius:5px;padding:6px 8px;font-family:ui-monospace,monospace;font-size:11px}
button{background:#1d5433;color:var(--green);border:1px solid #2a7a4a;border-radius:6px;padding:8px 14px;font-weight:700;cursor:pointer}
.foot{color:#5e6373;font-family:ui-monospace,monospace;font-size:9.2px;border-top:1px solid var(--line);padding-top:11px;margin-top:22px}
"""

# [FIX 1] THE BUG THAT SHOULD HAVE KILLED THE SCRIPT.
# In the previous version this JavaScript sat inside an f-string. Python reads a
# bare "{" in an f-string as the start of an expression, so `function f() {`
# raises SyntaxError at import time. The CSS was escaped with {{ }} but the JS
# was not. Keeping CSS and JS as PLAIN strings and concatenating is the fix --
# it also means you never have to double-brace anything again.
JS = r"""
const KNOWN = __TICKERS__;
const REPO = 'usubillaga/InvestorAce';

function addTicker(){
  const input = document.getElementById('newTicker');
  const out = document.getElementById('out');
  const link = document.getElementById('gh');
  const button = document.getElementById('addTickerButton');

  if (!input || !out || !link) {
    console.error('InvestorAce: Add ticker controls are missing from the page.');
    return false;
  }

  const t = input.value.trim().toUpperCase();
  if (!t) {
    out.value = 'Enter a Yahoo ticker first, for example ROAD or ASML.AS.';
    input.focus();
    return false;
  }

  // Accept Yahoo symbols such as ASML.AS / SAN.PA / IBST.L.
  // The model key is the portion before the first dot.
  const key = t.split('.')[0];
  if (KNOWN.includes(key)) {
    out.value = key + ' is already in the model.';
    return false;
  }

  const title = 'add-ticker: ' + t;
  const body = [
    'Auto-add ' + t + '.',
    '',
    'Do not edit the title -- the workflow reads the ticker from it.',
    '',
    'It will fetch price, shares and TTM free cash flow from Yahoo, draft the',
    'mechanical fields, commit the change and redeploy. Human review is still',
    'required for the delivering metric and clock classification.',
    '',
    'If free cash flow is negative the row may be added with na= and no NGV, by design.'
  ].join('\n');

  const url = 'https://github.com/' + REPO + '/issues/new'
    + '?title=' + encodeURIComponent(title)
    + '&body=' + encodeURIComponent(body);

  link.href = url;
  link.textContent = 'Open GitHub issue for ' + t + ' →';
  link.hidden = false;
  link.style.display = 'inline-block';

  out.value = 'Opening GitHub…\n\nIf it does not open automatically, use the green link below.\n\n' + url;

  if (button) button.disabled = true;

  // Navigate in the same tab after a real user click. This avoids popup blockers
  // on Safari/iOS/Chrome that can make window.open() appear to do nothing.
  window.location.assign(url);
  return true;
}

function initTickerAdder(){
  const button = document.getElementById('addTickerButton');
  const input = document.getElementById('newTicker');
  if (!button || !input) return;

  button.addEventListener('click', addTicker);
  input.addEventListener('keydown', function(event){
    if (event.key === 'Enter') {
      event.preventDefault();
      addTicker();
    }
  });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initTickerAdder);
} else {
  initTickerAdder();
}
"""



CHART_JS = r"""
const RD = __DATES__, RS = __SERIES__;
if (RD.length && window.Chart) {
  new Chart(document.getElementById('regimeChart').getContext('2d'), {
    type: 'line',
    data: { labels: RD, datasets: [
      {label:'Goldilocks', data:RS.GOLDILOCKS,  borderColor:'#66e39c', backgroundColor:'transparent', tension:.3, borderWidth:2},
      {label:'Reflation',  data:RS.REFLATION,   borderColor:'#63c6f0', backgroundColor:'transparent', tension:.3, borderWidth:2},
      {label:'Inflation',  data:RS.INFLATION,   borderColor:'#e5b45c', backgroundColor:'transparent', tension:.3, borderWidth:2},
      {label:'Stagflation',data:RS.STAGFLATION, borderColor:'#f06a6a', backgroundColor:'transparent', tension:.3, borderWidth:2},
      {label:'Recession',  data:RS.RECESSION,   borderColor:'#d6a8ff', backgroundColor:'transparent', tension:.3, borderWidth:2}
    ]},
    options: {
      responsive:true, maintainAspectRatio:false,
      plugins:{ legend:{ labels:{ color:'#8f95a8', font:{size:10}, boxWidth:12 } } },
      scales:{
        x:{ ticks:{color:'#5e6373', font:{size:9}}, grid:{color:'#1a1d27'} },
        y:{ min:0, max:100, ticks:{color:'#5e6373', font:{size:9}}, grid:{color:'#1a1d27'} }
      }
    }
  });
} else {
  const el = document.getElementById('chartNote');
  if (el) el.textContent = RD.length ? 'Chart.js did not load.'
    : 'No history yet. The line appears once history/ has two or more daily snapshots.';
}
"""

def build_html():
    rows = []
    ranked = sorted(DATA.items(), key=lambda kv: (-(score(kv[1]) if score(kv[1]) is not None else -1), kv[0]))
    for i,(t,d) in enumerate(ranked, 1):
        s, rk, c, cu, eg = score(d), risk(d), cover(d), cushion(d), entry_gap(d)
        bn, bc = band(s); vn, vc = verdict(t, d)
        note = d.get('price_note','')
        rows.append(
          '<tr%s>' % (' class="held"' if d.get('held') else '')
          + f'<td class="rk">{i}</td>'
          + f'<td class="tk">{t}{"<sup>&#9679;</sup>" if d.get("held") else ""}</td>'
          + f'<td class="se">{d.get("sector","")}</td>'
          + f'<td class="sc">{fmt(s,".2f")}</td>'
          + f'<td><span class="pill {bc}">{bn}</span></td>'
          + f'<td class="{cls(rk,2.4,3.3,invert=True)}">{fmt(rk,".1f")}</td>'
          + f'<td><span class="pill {vc}">{vn}</span></td>'
          + f'<td class="{cls(None if c is None else c*100,60,35)}">{fmt(None if c is None else c*100,".0f")}%</td>'
          + f'<td class="{cls(cu,0.0001,-0.0001)}">{fmt(cu,"+.1f")}</td>'
          + f'<td class="{cls(None if eg is None else eg*100,0,-0.0001)}">{fmt(None if eg is None else eg*100,"+.0f")}%</td>'
          + f'<td><span class="pill {CLOCK_CSS.get(d.get("clock"),"s-conc")}">{d.get("clock","")}</span></td>'
          + f'<td class="in">{d.get("ins","")}</td>'
          + (lambda rg, sc: f'<td><span class="pill {REG_CSS.get(rg,"empty")}">{rg or "—"}</span>'
                            f'{f"<br><span style=font-size:8px;color:#5e6373>{sc:.0f}</span>" if sc else ""}</td>'
            )(*best_regime(d))
          + f'<td class="mono">{fmt(ngv(d),",.2f")}</td>'
          + f'<td class="mono">{fmt(entry_price(d),",.2f")}</td>'
          + f'<td class="mono">{fmt(d.get("price"),",.2f")}'
          + (f'<br><span style="color:#f06a6a;font-size:8px">{note}</span>' if note else '')
          + '</td>'
          + f'<td class="mono" style="font-size:8px;color:#5e6373">{d.get("price_ts") or ""}</td>'
          + f'<td class="pv {d.get("built","exact")}">{d.get("built","exact")}</td></tr>')

    stamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    priced = sum(1 for d in DATA.values() if d.get('price') is not None)
    withngv = sum(1 for d in DATA.values() if ngv(d) is not None)
    na = sum(1 for d in DATA.values() if d.get('na'))
    issues = {t: d['price_note'] for t,d in DATA.items() if d.get('price_note') and not d.get('na')}
    for t,d in DATA.items():
        if d.get('boot_note'): issues[t] = 'NGV: ' + d['boot_note']

    js = JS.replace('__TICKERS__', json.dumps(sorted(DATA.keys())))
    rdates, rser = regime_history()
    js += CHART_JS.replace('__DATES__', json.dumps(rdates)).replace('__SERIES__', json.dumps(rser))
    pf = portfolio_regime()
    pf_txt = ' · '.join(f'<b>{r.title()}</b> {v:.0f}' for r, v in
                        sorted(pf.items(), key=lambda kv: -kv[1])) if pf else 'no cover yet'
    chart_box = ('<div class="box"><h2>Where the book sits on the growth / inflation grid</h2>'
                 '<div class="lede" style="margin-bottom:8px">Position-weighted, not a cross-sectional '
                 'average — averaging all 51 rows is dominated by the sector mix and barely moves. '
                 'Today: ' + pf_txt + '</div>'
                 '<div style="height:220px"><canvas id="regimeChart"></canvas></div>'
                 '<div id="chartNote" class="lede" style="font-size:10.5px;margin-top:6px"></div></div>')
    head = ('<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>InvestorAce · Master Scoreboard</title>'
            '<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>'
            '<style>' + CSS + '</style></head><body>')
    hdr = (f'<div class="kicker">InvestorAce · Live · {stamp}</div>'
           f'<h1>Master Scoreboard</h1>'
           f'<div class="lede">{len(DATA)} tickers · <b>{withngv}</b> with NGV · <b>{priced}</b> priced this run · '
           f'<b>{na}</b> formally N/A. Prices from Yahoo; NGV, subscores and the delivering metric are static and '
           f'human-set. <b>NGV does not move with price — cover, cushion and entry gap all derive from it.</b></div>')
    issue_box = ''
    if issues:
        li = ''.join(f'<div class="mono">{t}: {v}</div>' for t,v in sorted(issues.items()))
        issue_box = f'<div class="box"><h2 style="color:#f06a6a">Price issues this run ({len(issues)})</h2>{li}</div>'
    adder = ('<div class="box"><h2>Add a ticker</h2>'
             '<div class="lede" style="margin-bottom:10px">Yahoo can supply the mechanical half — price, shares, '
             'cash flow, currency. It cannot supply subscores, the delivering metric or the clock classification. '
             'This opens a pre-filled GitHub issue; the workflow does the rest and comments back with the result.</div>'
             '<input id="newTicker" type="text" autocomplete="off" spellcheck="false" '
             'placeholder="e.g. ASML.AS" aria-label="Yahoo ticker" style="width:220px">&nbsp;'
             '<button id="addTickerButton" type="button">Add via GitHub</button>&nbsp;'
             '<a id="gh" target="_blank" rel="noopener noreferrer" hidden '
             'style="background:#1d5433;color:#4ecb8a;border:1px solid #2a7a4a;border-radius:6px;padding:8px 14px;font-weight:700;text-decoration:none"></a>'
             '<textarea id="out" aria-live="polite" style="width:100%;height:150px;margin-top:10px" readonly></textarea></div>')
    tbl = ('<table><thead><tr><th>#</th><th>Ticker</th><th>Sector</th><th>Score</th><th>Band</th><th>Risk</th>'
           '<th>Verdict</th><th>Cover</th><th>Cushion</th><th>Entry gap</th><th>Clock</th><th>Insider</th><th>Regime</th>'
           '<th>NGV</th><th>Entry@60%</th><th>Price</th><th>Fetched</th><th>Built</th></tr></thead><tbody>'
           + '\n'.join(rows) + '</tbody></table>')
    foot = (f'<div class="foot">Snapshot written to history/. NGV = (FCF ÷ shares) ÷ r and is price-independent. '
            f'Negative cushion forces DO NOT ADD at every band. NVDA carries a manual risk floor because the '
            f'formula has no concentration term. Last pull {stamp}.<br>Not financial advice</div>')
    with open('index.html','w',encoding='utf-8') as f:
        f.write(head + hdr + issue_box + chart_box + adder + tbl + foot + '<script>' + js + '</script></body></html>')

if __name__ == '__main__':
    bootstrap_fundamentals()
    fetch_prices()
    day = snapshot()
    build_html()
    bad = {t: d['price_note'] for t,d in DATA.items() if d.get('price_note') and not d.get('na')}
    print(f'{len(DATA)} tickers · snapshot history/{day}.json · index.html written')
    if bad: print('PRICE ISSUES:', json.dumps(bad, indent=1), file=sys.stderr)
