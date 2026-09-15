#!/usr/bin/env python3
"""
INVESTORACE &middot; SCORECARD ENGINE &middot; v15.2-framework  (producer cushion withdrawn: volume growth is not a cash-flow rate)  (sanity-band fix, self-healing ranges)  (regime classifier + score fallback + bootstrap diagnostics)
Corrected build. Fixes marked [FIX n].

RUN:  python engine.py          -> writes index.html + history/YYYY-MM-DD.json
DEPLOY: GitHub Actions cron -> commit index.html -> GitHub Pages.
"""
import warnings as _w
_w.filterwarnings('ignore')          # [FIX] yfinance emits a Pandas4Warning per
import json, os, sys, math, hashlib  # fetch; 200 lines of them buried the real
                                     # traceback and made the failure unreadable
from datetime import datetime, timezone
from pathlib import Path
import evidence as EVIDENCE
from integrity import atomic_text
from framework_view import framework_panel
from portfolio import construct as construct_portfolio
import yfinance as yf
try:
    import wacc as WACC
except Exception:
    WACC = None
try:
    import epv as EPV
except Exception:
    EPV = None
try:
    from forward import run as forward_run, freeze_cohorts
except Exception:
    forward_run = lambda: {'ok': False, 'note': 'forward.py not present'}
    freeze_cohorts = lambda *a, **k: None
try:
    from macro import sector_performance, SECTOR_TO_ENGINE
except Exception:
    sector_performance = lambda years=10: {}
    SECTOR_TO_ENGINE = {}
try:
    from macro import read_macro
except Exception:
    read_macro = lambda: {'ok': False, 'note': 'macro.py not present'}

CASH_PCT = 7.8      # uninvested, so weights should sum to 100 - this

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
'SPGI': dict(yf='SPGI',   fcf=5200,   shares=293.3,  r=.075, cur='USD', deliver=7.0,  dl='organic cc',       sub=(8,9.5,9,6.5,4.5,9),     pr=6.0, dil=9.0, clock='CONC', ins='BUYING&middot;LILA', held=True, sector='Info Svcs',     built='exact', sanity=(200,700), weight=1.4),
'SAN' : dict(yf='SAN.PA', fcf=6900,   shares=1215.0, r=.080, cur='EUR', deliver=10.0, dl='sales cc',         sub=(8,7,7,7,8,8),           pr=9.0, dil=8.0, clock='CLOCK',ins='AWARDS',      held=True,  sector='Pharma',        built='exact', sanity=(50,140), weight=5.7),
'APP' : dict(yf='APP',    fcf=4000,   shares=335.29, r=.100, cur='USD', deliver=53.0, dl='revenue',          sub=(9,9.5,8,8.5,3.5,7.5),   pr=5.0, dil=8.0, clock='CONC', ins='SELLING',     held=False, sector='Ad Tech',       built='exact', sanity=(100,700)),
'ABT' : dict(yf='ABT',    fcf=7824,   shares=1746.0, r=.075, cur='USD', deliver=7.0,  dl='comparable sales', sub=(7,7.5,7,7.5,7.5,8.5),   pr=7.5, dil=7.0, clock='DIV',  ins='MIXED',       held=True,  sector='MedTech',       built='exact', sanity=(50,200), weight=1.8),
'WKL' : dict(yf='WKL.AS', fcf=1250,   shares=232.52, r=.080, cur='EUR', deliver=5.0,  dl='organic revenue',  sub=(6,9,8,6,5,7),           pr=8.5, dil=7.5, clock='DIV',  ins='MIXED',       held=True,  sector='Info Svcs',     built='exact', sanity=(30,150), weight=23.2),
'LVMH': dict(yf='MC.PA',  fcf=13100,  shares=500.0,  r=.080, cur='EUR', deliver=2.0,  dl='organic revenue',  sub=(5,8,8,7.5,7.5,6.5),                    pr=None, dil=6.5, clock='CONC', ins='BUYING&middot;LILA', held=True,  sector='Luxury',        built='exact', sanity=(300,900), weight=27.4, boot_note='rebuilt 2026-09-03 from H1: organic +2% (Q2 +3%), jewellery +11%, op margin 22.5%, recurring op profit EUR8.69bn -4%, FCF EUR13.1bn. Named risk not scored: France extending the corporate surcharge takes the FY27 effective tax rate to ~33% (Bernstein cut FY27 EPS 6.1%).'),
'UBER': dict(yf='UBER',   fcf=10000,  shares=2100.0, r=.080, cur='USD', deliver=24.0, dl='gross bookings',   sub=(6,7,8,6,8,6),           pr=7.5, dil=9.0, clock='DIV',  ins='AWARDS',      held=True,  sector='Platform',      built='exact', sanity=(40,150), weight=3.8),
'AVGO': dict(yf='AVGO',   fcf=35000,  shares=4757.0, r=.100, cur='USD', deliver=48.0, dl='revenue',          sub=(9.5,9.5,9.5,7.5,2.5,7), pr=2.0, dil=6.0, clock='CONC', ins='NOT CHECKED', held=False, sector='Semis',         built='exact', sanity=(100,1000)),
'ONON': dict(yf='ONON',   fcf=437,    shares=416.0,  r=.090, cur='USD', deliver=21.6, dl='revenue cc',       sub=(8.5,8.5,7,9,3.5,1.5),   pr=6.0, dil=6.0, clock='CONC', ins='NOT CHECKED', held=True, sector='Apparel',       built='est',   sanity=(10,120), weight=4.5),
'VICI': dict(yf='VICI',   fcf=2480,   shares=1000.0, r=.075, cur='USD', deliver=3.3,  dl='AFFO/share',       sub=None,                    pr=8.0, dil=3.5, clock='CONC', ins='AWARDS',      held=True,  sector='REIT',          built='back-solved', sanity=(15,60), score_fixed=6.8, weight=1.9),
'ENB' : dict(yf='ENB.TO', fcf=12900,  shares=2184.0, r=.075, cur='CAD', deliver=5.0,  dl='DCF/share CAGR',   sub=(5,6,5,3.5,6,8.5),       pr=8.5, dil=6.0, clock='CONC', ins='NOT CHECKED', held=True,  sector='Midstream',     built='exact', sanity=(30,120), weight=4.1),
'PFE' : dict(yf='PFE',    fcf=9480,   shares=5700.0, r=.080, cur='USD', deliver=-1.8, dl='FY guide vs FY25', sub=(4,6.5,5.5,4,8.5,7),     pr=6.5, dil=5.5, clock='CLOCK',ins='BUYING',      held=False,  sector='Pharma',        built='exact', sanity=(10,60)),
# [FIX 5] NGV inputs restored -- these were computed and then dropped back to None
'ROL' : dict(yf='ROL',    fcf=502,    shares=475.3,  r=.075, cur='USD', deliver=5.7,  dl='organic revenue',  sub=None,                    pr=4.5, dil=6.0, clock='CONC', ins='SELLING',     held=False, sector='Services',      built='exact', sanity=(15,80), score_fixed=6.47),
'LULU': dict(yf='LULU',   fcf=850,   shares=112.0,  r=.090, cur='USD', deliver=-6.0, dl='FY revenue guide',         sub=(1.5,7,6,9,8.5,5),         pr=None, dil=7.5, clock='CONC', ins='NOT CHECKED', held=False, sector='Apparel',       built='exact',   sanity=(80,500), boot_note='Q2 FY2026 reported 3 Sep 2026. Revenue $2.42bn -4% and MISSED. Comps -9%, Americas comps -12%, womens leggings -20%. FY guide cut to $10.35-10.5bn and EPS to $9.48-9.73. The $2.92 EPS beat is $0.86 of TARIFF REFUND; ex-refund it missed both lines. FCF normalised to $850m excluding the one-off $134.5m refund.'),
'PL'  : dict(yf='PL',     fcf=52.9,   shares=356.0,  r=.100, cur='USD', deliver=58.0, dl='revenue growth',          sub=(9.5,4,5,8.5,1.5,1),       pr=None, dil=2.5, clock='CONC', ins='SELLING',     held=True, sector='Space',         built='exact', sanity=(2,80), boot_note='Q2 FY2027 reported 3 Sep 2026: revenue $116.1m beat the $102-107m guide, +58% YoY accelerating from +42%, backlog ~$1bn +72%, first adjusted-profitable quarter, FY27 guide raised to $430-441m, cash $730.8m. FCF is the problem: +$52.9m FY26 then -$2.5m in Q1 FY27, so the NGV rests on a lumpy prepayment-driven number.', weight=1.7),
# --- NGV N/A by judgement. reason recorded; these will never take a price. -------
'MSFT': dict(yf='MSFT', fcf=66987.0, shares=7425.55, r=0.08, cur='USD', deliver=None, dl='revenue growth (PROXY)', sub=(5.0,5.0,5.0,8.0,5.0,9.0), pr=None, dil=7.0, clock='CONC', ins='NOT CHECKED', held=False, sector='Technology', built='auto', sanity=(174.6,1107.44)),
'AAPL': dict(yf='AAPL', fcf=136683.0, shares=14594.18, r=0.08, cur='USD', deliver=None, dl='revenue growth (PROXY)', sub=(5.0,5.0,5.0,8.0,5.0,9.0), pr=None, dil=8.5, clock='CONC', ins='NOT CHECKED', held=False, sector='Technology', built='auto', sanity=(112.97,689.14)),
'KO': dict(yf='KO', fcf=14297.0, shares=4302.55, r=0.08, cur='USD', deliver=None, dl='revenue growth (PROXY)', sub=(5.0,5.0,5.0,7.0,5.0,6.0), pr=None, dil=7.0, clock='CONC', ins='NOT CHECKED', held=False, sector='Consumer Defensive', built='auto', sanity=(32.67,184.98)),
'CVX': dict(yf='CVX', fcf=27012.0, shares=1961.6, r=0.08, cur='USD', deliver=None, dl='revenue growth (PROXY)', sub=(5.0,5.0,5.0,8.0,5.0,7.5), pr=None, dil=0.5, clock='DIV', ins='NOT CHECKED', held=False, sector='Energy', built='auto', sanity=(73.25,429.42)),
'AMAT': dict(yf='AMAT', fcf=5343.0, shares=793.6, r=0.08, cur='USD', deliver=None, dl='revenue growth (PROXY)', sub=(5.0,5.0,5.0,8.0,5.0,9.0), pr=None, dil=8.5, clock='CONC', ins='NOT CHECKED', held=False, sector='Technology', built='auto', sanity=(77.24,1479.34)),
'PHR': dict(yf='PHR', fcf=63.3, shares=61.77, r=0.08, cur='USD', deliver=None, dl='revenue growth (PROXY)', sub=(5.0,5.0,5.0,8.0,5.0,1.0), pr=None, dil=3.5, clock='CONC', ins='NOT CHECKED', held=False, sector='Healthcare', built='auto', sanity=(3.88,63.66)),
'RCAT': dict(yf='RCAT', fcf=None, shares=152.71, r=0.08, cur='USD', deliver=None, dl='', sub=(5.0,5.0,5.0,6.0,5.0,1.0), pr=None, dil=0.5, clock='CONC', ins='NOT CHECKED', held=False, sector='Industrials', built='auto', sanity=(2.88,37.56), na='free cash flow -157.7m -- a NEGATIVE fcf was written straight into the row, which makes NGV negative'),
'ADSK': dict(yf='ADSK', fcf=2694.0, shares=211.15, r=0.08, cur='USD', deliver=22.4, dl='revenue growth (PROXY)', sub=(8.5,7.5,9.5,8.0,5.0,6.0), pr=None, dil=8.5, clock='CONC', ins='NOT CHECKED', held=False, sector='Technology', built='auto', sanity=(92.75,658.18)),
'GOOG': dict(yf='GOOG', fcf=53273.0, shares=12229.93, r=0.08, cur='USD', deliver=27.4, dl='revenue growth (PROXY)', sub=(8.5,9.0,6.0,8.0,5.0,9.0), pr=None, dil=5.5, clock='CONC', ins='NOT CHECKED', held=False, sector='Communication Services', built='auto', sanity=(103.48,808.94)),
'GILD': dict(yf='GILD', fcf=12943.0, shares=1239.96, r=0.08, cur='USD', deliver=5.9, dl='revenue growth (PROXY)', sub=(5.5,9.0,9.5,5.0,5.0,6.0), pr=None, dil=7.0, clock='CLOCK', ins='NOT CHECKED', held=False, sector='Healthcare', built='auto', sanity=(54.23,314.58), boot_note='balance sheet auto-scored 1.5 (net debt/EBITDA >5x); Gilead runs nearer 1.5-2x -- reset to 5.0 until EBITDA is verified'),
'AG'  : dict(yf='AG', fcf=180, fcf_ttm=614, shares=492.91, r=.11, cur='USD', deliver=None, dl='n/a - see note', sub=(9,8,7,9,5,7), pr=None, dil=6.0, clock='DIV', ins='SELLING', held=False, sector='Materials', built='mid-cycle', midcycle=True, sanity=(3,300), boot_note='silver; the most cyclical row in the table | deliver blanked: production growth ignores the price half of a producer cash flow, so the cushion read negative by construction'),
'BABA': dict(yf='BABA', fcf=None, shares=2485.62, r=0.08, cur='USD', deliver=2.7, dl='revenue growth (PROXY)', sub=(4.0,4.0,1.5,7.0,5.0,9.0), pr=None, dil=9.5, clock='CONC', ins='NOT CHECKED', held=False, sector='Consumer Cyclical', built='auto', sanity=(45.99,385.34), na='Yahoo returned FCF of -50,724m, not credible for Alibaba. Treated as a bad pull, NOT as evidence of cash burn.'),
'BYRN': dict(yf='BYRN', fcf=None, shares=22.8, r=0.08, cur='USD', deliver=26.9, dl='revenue growth (PROXY)', sub=(8.5,2.0,1.5,6.0,5.0,1.0), pr=None, dil=5.5, clock='CONC', ins='NOT CHECKED', held=False, sector='Industrials', built='auto', sanity=(1.59,61.24), na='free cash flow non-positive (-0.5m)'),
'FSLR': dict(yf='FSLR', fcf=None, shares=107.0, r=.090, cur='USD', deliver=-4.0,
    dl='net sales YoY', sub=(4,8.5,1,7.5,7.5,1), pr=None, dil=6.5, clock='CLOCK',
    ins='NOT CHECKED', held=False, sector='Semis', built='exact', sanity=(60,600),
    na='H1 2026 free cash flow -$640m (OCF -$360m, capex -$280m). And the margin is policy: Section 45X credits decline after 2029.'),
'SITE': dict(yf='SITE', fcf=250.2, shares=43.66, r=.080, cur='USD', deliver=5.2, dl='revenue growth (PROXY)', sub=(5.5,4.0,6.0,6.0,5.0,6.0), pr=None, dil=8.5, clock='CONC', ins='NOT CHECKED', held=True, sector='Industrials', built='auto', sanity=(45.03,337.12), weight=2.0),
'TSLA': dict(yf='TSLA', fcf=5755.0, shares=3949.55, r=0.08, cur='USD', deliver=6.1, dl='revenue growth (PROXY)', sub=(5.5,4.0,6.0,8.0,5.0,1.0), pr=None, dil=0.5, clock='CONC', ins='NOT CHECKED', held=False, sector='Consumer Cyclical', built='auto', sanity=(148.69,997.66)),
'PG'  : dict(yf='PG', fcf=15147.0, shares=2324.43, r=0.08, cur='USD', deliver=3.3, dl='revenue growth (PROXY)', sub=(4.0,7.5,7.5,7.0,5.0,7.5), pr=None, dil=7.0, clock='CONC', ins='NOT CHECKED', held=False, sector='Consumer Defensive', built='auto', sanity=(68.81,334.5)),
'CSGP': dict(yf='CSGP', fcf=227.0, shares=405.2, r=0.08, cur='USD', deliver=30.0, dl='revenue growth (PROXY)', sub=(8.5,4.0,6.0,9.5,5.0,9.0), pr=None, dil=9.5, clock='CONC', ins='NOT CHECKED', held=False, sector='Real Estate', built='auto', sanity=(12.94,183.78)),
'OXY' : dict(yf='OXY', fcf=3900, fcf_ttm=4793, shares=999.64, r=.105, cur='USD', deliver=None, dl='n/a - see note', sub=(2,7.5,7,6,6,6), pr=None, dil=6.0, clock='DIV', ins='SELLING', held=False, sector='Energy', built='mid-cycle', midcycle=True, sanity=(3,300), boot_note='oil and gas; heavy post-CrownRock leverage | deliver blanked: production growth ignores the price half of a producer cash flow, so the cushion read negative by construction'),
'SPCX': dict(yf='SPCX', fcf=None, shares=13181.78, r=0.08, cur='USD', deliver=47.3, dl='revenue growth (PROXY)', sub=(9.5,2.0,1.5,9.5,5.0,1.0), pr=None, dil=5.0, clock='CONC', ins='NOT CHECKED', held=False, sector='Industrials', built='auto', sanity=(52.42,451.28), na='Yahoo returned FCF of -32,522m on 13.2bn shares. Not credible -- a bad pull, not evidence of cash burn. Verify what this symbol actually is before trusting any of it.'),
'JEQE': dict(yf='JEQE.DE', fcf=None, shares=None, r=.080, cur='EUR', deliver=None,
    dl='', sub=None, pr=None, dil=6.0, clock='CONC', ins='N/A - FUND', held=True,
    sector='Technology', built='fund', sanity=(8,60), weight=2.1,
    na='fund, not a company. No single free cash flow to capitalise, so no NGV. '
       'A covered-call overlay on the Nasdaq-100: 109 holdings, top 10 = 49.4%. '
       'The framework cannot score it and should not pretend to.'),
'REP' : dict(yf='REP.MC', fcf=1800, fcf_ttm=2604, shares=1150.0, r=.105, cur='EUR',
    deliver=None, dl='n/a - see note', sub=(5.5,6.5,7,6.5,7,9), pr=None, dil=8.5,
    clock='DIV', ins='NOT CHECKED', held=False, sector='Energy', built='mid-cycle',
    midcycle=True, sanity=(4,60),
    boot_note='mid-cycle FCF EUR1.8bn against H1-2026 annualised EUR2.6bn. Brent averaged $104 in Q2, up 53% YoY, and adjusted net income rose 135% on production up 4% q/q -- a price event, not a business event. Spanish withholding 19% on a 4.8% yield = 0.91%/yr unrecoverable, on top of ENG.'),
'AWK' : dict(yf='AWK', fcf=None, shares=194.0, r=.070, cur='USD', deliver=7.6,
    dl='adj. EPS guide vs FY25', sub=(6.5,6,2,4.5,5.5,6.5), pr=None, dil=3.5,
    clock='DIV', ins='NOT CHECKED', held=False, sector='Utilities', built='exact',
    sanity=(40,320),
    na='regulated water utility. 2025 operating cash flow $2.06bn against $3.13bn capex, so free cash flow is negative and stays negative BY PLAN: $19-20bn of investment 2026-2030. NGV cannot be built from a cash line the business is designed not to produce. Value here is rate base times allowed return, which this framework does not compute. Same structural problem as ENG.'),
'MRVL': dict(yf='MRVL', fcf=2100, shares=921.0, r=.100, cur='USD', deliver=37.0,
    dl='revenue growth', sub=(9.5,5.5,7.5,6.5,1.5,2), pr=None, dil=3.0, clock='CONC',
    ins='NOT CHECKED', held=False, sector='Semis', built='est', sanity=(40,500),
    boot_note='Q2 FY2027 reported 27 Aug 2026. Revenue $2.739bn +37%, Data Center +46% and 79% of the mix, guidance raised twice for FY27 AND FY28. GAAP net income $308m vs non-GAAP $866m -- a $558m gap, mostly stock comp and amortisation. Google warrant for up to 7% of shares is the dilution risk. $120bn Google deal produces material revenue only from FY2029.'),
'AR'  : dict(yf='AR', fcf=520, fcf_ttm=340, shares=310.0, r=.105, cur='USD', deliver=None, dl='n/a - see note', sub=(8,8,6.5,6,6,4), pr=None, dil=6.0, clock='DIV', ins='SELLING', held=True, sector='Energy', built='mid-cycle', midcycle=True, sanity=(3,300), boot_note='mid-cycle FCF across four reported years; natural gas | deliver blanked: production growth ignores the price half of a producer cash flow, so the cushion read negative by construction', weight=2.5),
'DVN' : dict(yf='DVN', fcf=2600, fcf_ttm=2150, shares=1290.0, r=.105, cur='USD', deliver=None, dl='n/a - see note', sub=(6,7,6.5,5,7,7), pr=None, dil=5.0, clock='DIV', ins='SELLING', held=False, sector='Energy', built='mid-cycle', midcycle=True, sanity=(3,300), boot_note='post-Coterra share count; oil and gas | deliver blanked: production growth ignores the price half of a producer cash flow, so the cushion read negative by construction'),
'CNX' : dict(yf='CNX', fcf=440, fcf_ttm=525, shares=145.0, r=.1, cur='USD', deliver=None, dl='n/a - see note', sub=(3.5,6.5,7,6,7.5,8), pr=None, dil=6.0, clock='DIV', ins='SELLING', held=True, sector='Energy', built='mid-cycle', midcycle=True, sanity=(3,300), boot_note='26 consecutive positive-FCF quarters; gas | deliver blanked: production growth ignores the price half of a producer cash flow, so the cushion read negative by construction', weight=2.3),
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
'VST' : dict(yf='VST',    fcf=None, shares=None, r=.080, cur='USD', deliver=None, dl='', sub=None, pr=6.0, dil=8.5, clock='DIV',  ins='MIXED',   held=True, sector='Utilities',  built='back-solved', score_fixed=6.58, weight=4.8),
'SE'  : dict(yf='SE',     fcf=None, shares=None, r=.080, cur='USD', deliver=None, dl='', sub=None, pr=5.5, dil=4.5, clock='CONC', ins='SELLING', held=False, sector='Platform',   built='back-solved', score_fixed=6.47),
'UNH' : dict(yf='UNH',    fcf=None, shares=None, r=.080, cur='USD', deliver=None, dl='', sub=None, pr=5.5, dil=8.5, clock='DIV',  ins='SELLING', held=False, sector='Health Ins', built='back-solved', score_fixed=6.35),
'CMCSA':dict(yf='CMCSA',  fcf=None, shares=None, r=.080, cur='USD', deliver=None, dl='', sub=None, pr=9.5, dil=6.0, clock='CLOCK',ins='SELLING', held=False, sector='Media',      built='back-solved', score_fixed=6.25),
'NVO' : dict(yf='NVO',    fcf=None, shares=None, r=.080, cur='USD', deliver=None, dl='', sub=None, pr=6.0, dil=6.0, clock='CLOCK',ins='REGIME',  held=False, sector='Pharma',     built='back-solved', score_fixed=6.15),
'ENG' : dict(yf='ENG.MC', fcf=None, shares=None, r=.075, cur='EUR', deliver=-8.6,dl='recurring net profit', sub=None, pr=8.0, dil=6.0, clock='CLOCK', ins='BUYING', held=True, sector='Utilities', built='back-solved', sanity=(5,40), score_fixed=6.0, na='regulated network: total-capex FCF is the wrong line, needs FFO or DCF per share like ENB', weight=2.8),
'META': dict(yf='META',   fcf=None, shares=None, r=.080, cur='USD', deliver=None, dl='', sub=None, pr=3.0, dil=8.0, clock='CONC', ins='SELLING', held=False, sector='AdTech',     built='back-solved', score_fixed=5.83),
'DIS' : dict(yf='DIS',    fcf=None, shares=None, r=.080, cur='USD', deliver=None, dl='', sub=None, pr=4.0, dil=9.0, clock='DIV',  ins='AWARDS',  held=False, sector='Media',      built='back-solved', score_fixed=5.62),
'PEP' : dict(yf='PEP',    fcf=None, shares=None, r=.080, cur='USD', deliver=None, dl='', sub=None, pr=5.0, dil=7.0, clock='DIV',  ins='SELLING', held=False, sector='Staples',    built='back-solved', score_fixed=5.5),
'BSX' : dict(yf='BSX',    fcf=None, shares=None, r=.080, cur='USD', deliver=None, dl='', sub=None, pr=4.0, dil=6.0, clock='DIV',  ins='BUYING&middot;LILA', held=True, sector='MedTech',built='exact', score_fixed=5.4, weight=0.2),
'WIX' : dict(yf='WIX',    fcf=None, shares=None, r=.080, cur='USD', deliver=None, dl='', sub=(6,3,4,2,8,5), pr=9.5, dil=8.5, clock='CONC', ins='AWARDS', held=False, sector='Software', built='exact'),
'GRAB': dict(yf='GRAB',   fcf=None, shares=None, r=.080, cur='USD', deliver=None, dl='', sub=None, pr=2.5, dil=5.5, clock='CONC', ins='SELLING', held=False, sector='Platform',   built='back-solved', score_fixed=5.23, na='TTM IFRS free cash flow negative (-186m)'),
'NOW' : dict(yf='NOW',    fcf=None, shares=None, r=.080, cur='USD', deliver=None, dl='', sub=None, pr=2.0, dil=6.0, clock='CONC', ins='SELLING', held=False, sector='Software',   built='exact', score_fixed=5.22),
'MCD' : dict(yf='MCD',    fcf=None, shares=None, r=.080, cur='USD', deliver=None, dl='', sub=None, pr=2.5, dil=7.0, clock='DIV',  ins='SELLING', held=False, sector='Restaurant', built='back-solved', score_fixed=5.2),
'TTD' : dict(yf='TTD',    fcf=None, shares=None, r=.080, cur='USD', deliver=None, dl='', sub=None, pr=2.5, dil=9.0, clock='CONC', ins='BUYING',  held=False, sector='Ad Tech',    built='back-solved', score_fixed=4.7),
'NKE' : dict(yf='NKE',    fcf=None, shares=None, r=.080, cur='USD', deliver=None, dl='', sub=None, pr=4.5, dil=7.0, clock='DIV',  ins='BUYING',  held=False, sector='Apparel',    built='exact', score_fixed=4.6),
'ZTS' : dict(yf='ZTS',    fcf=None, shares=None, r=.080, cur='USD', deliver=None, dl='', sub=None, pr=4.5, dil=6.0, clock='CLOCK',ins='BUYING',  held=False, sector='Animal Health', built='exact', score_fixed=4.55),
'IBST': dict(yf='IBST.L', fcf=None, shares=None, r=.080, cur='GBp', deliver=None, dl='', sub=None, pr=2.5, dil=6.0, clock='CLOCK',ins='REGIME',  held=False, sector='Materials',  built='exact', sanity=(50,400), score_fixed=3.7, na='free cash flow negative (-7m) in a UK housing downturn'),
}

# ---------------- engine ----------------
def ngv(d):
    """[CHANGE] r is now COMPUTED where possible, not assigned.

       The hand-set rates (0.075 to 0.105) were judgements doing enormous
       unexamined work. Worked from the FMP Advanced DCF for JNJ and AAPL at
       the same FCF per share: under a flat 8% the two read 65% and 52% cover,
       nearly identical. Under their real WACCs -- 5.36% and 8.67% -- they are
       49 cover-points apart. A beta-0.39 pharma and a beta-1.09 consumer-tech
       company cannot share a discount rate.

       r_wacc is filled during the price fetch. A row whose beta fetch fails
       keeps its hand-set r, so nothing breaks."""
    f, s = d.get('fcf'), d.get('shares')
    r = d.get('r_wacc') or d.get('r', .08)
    return None if (f is None or s is None or not r) else (f/s)/r

def rate_used(d):
    """Which discount rate this row is actually valued on, and where it came from."""
    return (d['r_wacc'], 'wacc') if d.get('r_wacc') else (d.get('r', .08), 'manual')

def cover(d):
    n, p = ngv(d), d.get('price')
    return None if (n is None or not p) else n/p

def implied_growth(d):
    c = cover(d)
    r = d.get('r_wacc') or d.get('r', .08)   # must match ngv(), or cushion lies
    return None if c is None else r*(1-c)/(1+c*r)

def cushion(d):
    """[FIX] A mid-cycle producer row carries deliver = PRODUCTION growth, which
       is a VOLUME rate. implied_growth is a CASH FLOW rate. A gas producer can
       grow volume 3% while cash flow doubles on price, so subtracting one from
       the other is a category error -- it was manufacturing negative cushions
       for AR, DVN, OXY and CNX out of nothing. NGV and cover are unaffected and
       stay; only the comparison is withdrawn."""
    if d.get('midcycle'): return None
    g, dv = implied_growth(d), d.get('deliver')
    return None if (g is None or dv is None) else dv - 100*g

CUSHION_TOL = 0.5     # percentage points

def cushion_neg(d):
    """[FIX] A cushion of -0.2 is arithmetic noise, not evidence that the price
       demands more than the business delivers. It fired DO NOT ADD on LVMH for
       weeks while I called it a rounding artefact in prose and left the code
       alone. Anything inside +/-0.5pp now counts as flat."""
    cu = cushion(d)
    return cu is not None and cu < -CUSHION_TOL

def entry_price(d, target=.60):
    n = ngv(d);  return None if n is None else n/target

def entry_gap(d, target=.60):
    c = cover(d);  return None if c is None else c/target - 1

def epv(d):
    """EPV per share, populated by populate_epv(). Separate from NGV by design."""
    return d.get('epv_value')


def epv_cover(d):
    """EPV / price. Diagnostic only; never enters score(), risk() or regime fit."""
    e, p = epv(d), d.get('price')
    return None if (e is None or not p) else e / p


def valuation_gap(d):
    """EPV relative to NGV. -0.49 means EPV is 49% below NGV."""
    n, e = ngv(d), epv(d)
    if n is None or e is None or n <= 0:
        return None
    return e / n - 1.0


def valuation_read(d):
    """Describe agreement/divergence without manufacturing a composite valuation score."""
    n, e = ngv(d), epv(d)
    if n is None and e is None: return 'NO VALUE'
    if n is None: return 'EPV ONLY'
    if e is None: return 'NGV ONLY'
    if n <= 0 or e <= 0: return 'CHECK'
    g = abs(e / n - 1.0)
    if g <= .15: return 'AGREE'
    if g <= .35: return 'DIVERGE'
    return 'WIDE GAP'

def valuation_gap_class(d):
    g = valuation_gap(d)
    if g is None: return 'pr na'
    a = abs(g)
    return 'pr pos' if a <= .15 else ('pr mid' if a <= .35 else 'pr neg')


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
    if cushion_neg(d): pr = max(1.0, pr - 2.0)
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
    if cushion_neg(d): x += .6
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
    if cushion_neg(d):
        return ('DO NOT ADD','v-avoid') if s < 7.00 else ('BUY &middot; CUSHION NEG','v-avoid')
    if s >= 7.00:
        return ('BUY &middot; LOW RISK','v-buy') if rk <= 2.4 else \
               (('BUY &middot; MOD','v-buymod') if rk <= 3.2 else ('BUY &middot; HIGH RISK','v-buyhi'))
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
'GOLDILOCKS': {'Real Estate':0,'Consumer Cyclical':2,'Communication Services':1,'Technology':2,'Consumer Defensive':-1,'Healthcare':0,'Semis':2,'Software':2,'AI Infra':2,'Ad Tech':2,'AdTech':2,'Platform':2,'Space':2,
    'MedTech':1,'Luxury':1,'Apparel':1,'Info Svcs':1,'Health Data':1,'Biotech':1,
    'Services':0,'Industrials':0,'Automotive':1,'Media':0,'Restaurant':0,'Animal Health':0,'Aerospace':0,
    'Staples':-1,'Utilities':-1,'REIT':-1,'Health Ins':-1,'Pharma':-1,
    'Energy':-2,'Midstream':-2,'Materials':-2},
'REFLATION': {'Real Estate':-1,'Consumer Cyclical':1,'Communication Services':1,'Technology':1,'Consumer Defensive':-1,'Healthcare':-1,'Energy':2,'Materials':2,'Aerospace':2,'Midstream':2,
    'Semis':1,'Luxury':1,'Apparel':1,'Platform':1,'Media':1,'Restaurant':1,
    'Software':0,'Industrials':2,'Automotive':2,'Info Svcs':0,'Services':0,'MedTech':0,'Space':0,'Health Data':0,'Ad Tech':0,'AdTech':0,'Animal Health':0,
    'Staples':-1,'Utilities':-1,'Pharma':-1,'Health Ins':-1,'REIT':-2,'Biotech':-2,'AI Infra':0},
'INFLATION': {'Real Estate':2,'Consumer Cyclical':-1,'Communication Services':-1,'Technology':-1,'Consumer Defensive':1,'Healthcare':0,'Energy':2,'Midstream':2,'Materials':2,'REIT':2,'Utilities':2,
    'Staples':1,'Restaurant':1,'Info Svcs':1,'Luxury':1,
    'MedTech':0,'Industrials':1,'Automotive':-1,'Pharma':0,'Services':0,'Health Ins':0,'Aerospace':0,'Animal Health':0,
    'Software':-1,'Platform':-1,'Apparel':-1,'Media':-1,
    'Semis':-2,'AI Infra':-2,'Space':-2,'Biotech':-2,'Ad Tech':-2,'AdTech':-2,'Health Data':-2},
'STAGFLATION': {'Real Estate':1,'Consumer Cyclical':-1,'Communication Services':-1,'Technology':-2,'Consumer Defensive':1,'Healthcare':0,'Energy':2,'Midstream':2,'Materials':2,
    'Utilities':1,'REIT':1,'Staples':1,'Info Svcs':1,
    'Pharma':0,'Industrials':-1,'Automotive':-2,'MedTech':0,'Health Ins':0,'Restaurant':0,'Services':0,'Animal Health':0,
    'Luxury':-1,'Apparel':-1,'Media':-1,'Platform':-1,'Aerospace':-1,
    'Semis':-2,'Software':-2,'AI Infra':-2,'Space':-2,'Biotech':-2,'Ad Tech':-2,'AdTech':-2,'Health Data':-2},
'RECESSION': {'Real Estate':1,'Consumer Cyclical':-1,'Communication Services':0,'Technology':0,'Consumer Defensive':2,'Healthcare':2,'Staples':2,'Pharma':2,'Utilities':2,'Health Ins':2,
    'MedTech':1,'Info Svcs':1,'Services':1,'Animal Health':1,'REIT':1,
    'Software':0,'Industrials':-1,'Automotive':-2,'Media':0,'Restaurant':0,'Midstream':0,
    'Luxury':-1,'Apparel':-1,'Platform':-1,'Semis':-1,'Materials':-1,'Aerospace':-1,'Energy':-1,
    'AI Infra':-2,'Space':-2,'Biotech':-2,'Ad Tech':-2,'AdTech':-2,'Health Data':-2},
}
# how hard duration, balance sheet and payout bite in each regime
DUR_W = {'GOLDILOCKS':-0.35,'REFLATION':0.00,'INFLATION':0.45,'STAGFLATION':0.55,'RECESSION':0.45}
BS_W  = {'GOLDILOCKS':0.5,'REFLATION':0.5,'INFLATION':1.5,'STAGFLATION':2.5,'RECESSION':3.0}
PAY_W = {'GOLDILOCKS':0.5,'REFLATION':0.5,'INFLATION':1.5,'STAGFLATION':1.5,'RECESSION':1.5}

REGIME_MODEL_VERSION = 'v15.1-golden-2026-09-13'
REGIME_SECTOR_MULT = 12.0
REGIME_DURATION_CLAMP = 40.0
REGIME_SPEC_EXPECTED_SHA256 = '78c4c1681fe507136a77e06e02f5ffcadcc86a165a3376366744a815c6b1121d'


def regime_spec_sha256():
    payload = dict(AFF=AFF, DUR_W=DUR_W, BS_W=BS_W, PAY_W=PAY_W,
                   sector_mult=REGIME_SECTOR_MULT, duration_clamp=REGIME_DURATION_CLAMP)
    raw = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def regime_fit_components(d):
    """Return the exact live regime formula as auditable components.

    This is deliberately boring: the coefficients below are the pre-v2 model.
    Changing one is a MODEL CHANGE and must update the golden-master fixtures.
    Portfolio weight, score, risk, momentum and valuation never enter this function.
    """
    c = cover(d)
    if c is None: return {}
    sec = d.get('sector','')
    sub = d.get('sub')
    bs  = sub[3] if (sub and len(sub)==6) else 6.0
    pay = sub[5] if (sub and len(sub)==6) else 6.0
    dur = max(-REGIME_DURATION_CLAMP, min(REGIME_DURATION_CLAMP, (c - 0.60) * 100))
    out = {}
    for r in REGIMES:
        base = 50.0
        sector = REGIME_SECTOR_MULT * AFF[r].get(sec, 0)
        duration = DUR_W[r] * dur
        balance = BS_W[r] * (bs - 6)
        payout = PAY_W[r] * (pay - 6)
        raw = base + sector + duration + balance + payout
        out[r] = dict(base=base, sector=sector, duration=duration,
                      balance=balance, payout=payout, duration_input=dur,
                      raw=raw, total=round(max(0.0, min(100.0, raw)), 1))
    return out


def regime_scores(d):
    """0-100 per regime, preserving the v15.1 formula exactly."""
    comp = regime_fit_components(d)
    return {r: comp[r]['total'] for r in REGIMES} if comp else {}


# Frozen fixtures catch coefficient/clamp drift. These examples intentionally include
# the three names that exposed the v2 regression plus explicit clamp boundaries.
REGIME_GOLDEN = (
    ('NVDA', 'Semis', 0.21714285714285714, 9.0, 6.0,
     {'GOLDILOCKS':88.9,'REFLATION':63.5,'INFLATION':13.3,'STAGFLATION':12.4,'RECESSION':29.8}),
    ('ROAD', 'Industrials', 0.21636363636363637, 4.5, 1.5,
     {'GOLDILOCKS':60.4,'REFLATION':71.0,'INFLATION':35.7,'STAGFLATION':6.4,'RECESSION':9.5}),
    ('SAN', 'Pharma', 0.7466666666666667, 7.0, 8.0,
     {'GOLDILOCKS':34.4,'REFLATION':39.5,'INFLATION':61.1,'STAGFLATION':63.6,'RECESSION':86.6}),
    ('CLAMP_HIGH', 'Energy', 1.50, 6.0, 6.0,
     {'GOLDILOCKS':12.0,'REFLATION':74.0,'INFLATION':92.0,'STAGFLATION':96.0,'RECESSION':56.0}),
    ('CLAMP_LOW', 'Technology', 0.01, 6.0, 6.0,
     {'GOLDILOCKS':88.0,'REFLATION':62.0,'INFLATION':20.0,'STAGFLATION':4.0,'RECESSION':32.0}),
)


def _regime_fixture(sec, cv, bs, pay):
    """Build a stock with NGV=100 and price chosen to produce the frozen cover."""
    return dict(fcf=8.0, shares=1.0, r=.08, price=100.0/cv,
                sector=sec, sub=(6,6,6,bs,6,pay), dil=6.0, pr=6.0)


def regime_regression_errors():
    """True regression test: compare outputs to a frozen previous-model oracle."""
    errors = []
    for name, sec, cv, bs, pay, expected in REGIME_GOLDEN:
        got = regime_scores(_regime_fixture(sec, cv, bs, pay))
        if got != expected:
            errors.append(f'{name}: regime model drift: expected {expected}, got {got}')
    return errors


def regime_book(regime, size=30):
    """Pure regime ranking. No score/risk/cover/portfolio-weight tie-breaks.

    Ticker is used only to make exact-fit ties deterministic.
    """
    if regime not in REGIMES: return []
    rows = []
    for t, d in DATA.items():
        f = fit_now(d, regime)
        if f is not None:
            rows.append((t, d, f))
    rows.sort(key=lambda x: (-x[2], x[0]))
    return rows[:size]


def fit_now(d, macro_regime):
    """The number that makes the regime column actionable: how well THIS row
       suits the regime we are ACTUALLY in, rather than the one it likes best."""
    sc = regime_scores(d)
    return sc.get(macro_regime) if (sc and macro_regime) else None

def best_regime(d):
    s = regime_scores(d)
    if not s: return (None, None)
    r = max(s, key=s.get)
    return (r, s[r])


# =====================================================================
# MID-CYCLE NGV  --  commodity producers get a number, not a refusal
#
# The old rule marked AR, DVN, CNX, AG and OXY as na because "implied
# growth is really a price deck". That was true and it was also a
# cop-out: the framework ALREADY normalises the cash line for REITs
# (AFFO) and pipelines (distributable cash flow). Refusing to do the
# same work for a producer is inconsistent.
#
# The fix is what energy analysts actually do: capitalise MID-CYCLE
# free cash flow -- the average across a full price cycle -- instead of
# whatever this year happens to be. Then report where in the cycle the
# CURRENT year sits, so the flattery is visible rather than hidden.
#
#   NGV_midcycle = (mean annual FCF over ~4 years / shares) / r
#   cycle_pos    = TTM FCF / mid-cycle FCF
#                  > 1.5  cyclical PEAK  -- cover looks better than it is
#                  < 0.7  cyclical TROUGH -- cover looks worse than it is
#
# Producers also carry a higher discount rate (10-11%) because the cash
# flow is a price bet, not an annuity.
# =====================================================================
def cycle_pos(d):
    """TTM FCF divided by mid-cycle FCF. None when either is missing."""
    ttm, mid = d.get('fcf_ttm'), d.get('fcf')
    if ttm is None or not mid: return None
    return round(ttm / mid, 2)

def cycle_note(d):
    cp = cycle_pos(d)
    if cp is None: return ''
    if cp >= 1.5: return f'PEAK {cp:.2f}x mid-cycle &mdash; cover flatters'
    if cp <= 0.7: return f'TROUGH {cp:.2f}x mid-cycle &mdash; cover understates'
    return f'{cp:.2f}x mid-cycle'

def midcycle_from_yahoo(tk, years=4):
    """Mean annual free cash flow across `years` reported years."""
    try:
        cf = tk.cashflow
        if cf is None or cf.empty: return None, None
        idx = {str(i).strip().lower(): i for i in cf.index}
        def row(*n):
            for x in n:
                if x in idx: return cf.loc[idx[x]]
            return None
        fr = row('free cash flow')
        vals = None
        if fr is not None:
            vals = [float(v) for v in fr.iloc[:years] if v == v and v is not None]
        if not vals:
            o, c = row('operating cash flow'), row('capital expenditure')
            if o is not None and c is not None:
                vals = [float(a) + float(b) for a, b in zip(o.iloc[:years], c.iloc[:years])
                        if a == a and b == b]
        if not vals: return None, None
        return sum(vals) / len(vals), vals[0]      # (mid-cycle, most recent year)
    except Exception:
        return None, None


# =====================================================================
# PROXIMITY ALERT  --  which rows are near a price that matters
#
# Two thresholds, both derived from NGV so neither goes stale:
#   AT NGV      price <= NGV. You are paying nothing for growth at all.
#   NEAR ENTRY  within 5% of entry@60%, the GOOD-cover threshold.
#   APPROACHING within 12% of it.
# =====================================================================
def proximity(d):
    """[FIX] the first version had this inverted. A NEGATIVE gap means the price
       is already BELOW the entry level, i.e. cover already exceeds 60% -- that
       is 'clears', not 'approaching'. Approaching means falling toward it from
       above, so the gap must be positive and small."""
    n, p = ngv(d), d.get('price')
    if n is None or not p: return (None, None)
    e = n / 0.60
    gap = 100 * (p/e - 1)            # >0 price above entry, <0 already through it
    if p <= n:   return ('AT NGV',      round(100*(p/n - 1), 1))   # cover >= 100%
    if gap <= 0: return ('CLEARS',      round(gap, 1))             # cover >= 60%
    if gap <= 5: return ('NEAR ENTRY',  round(gap, 1))
    if gap <= 12:return ('APPROACHING', round(gap, 1))
    return (None, round(gap, 1))

PROX_CSS = {'AT NGV':'x-atngv', 'CLEARS':'x-clear', 'NEAR ENTRY':'x-near', 'APPROACHING':'x-appr'}


# =====================================================================
# MOMENTUM -- reported, never scored
#
# The scorecard excludes technicals by design, so momentum enters as a
# column with the same standing as the insider column: informative,
# displayed, outside the weighting.
#
# It earns its place because of a specific defect in cover. Cover is
# NGV/price, so it RISES WHEN THE PRICE FALLS. A collapsing business and
# a bargain look identical in that column, and the framework has no way
# to tell them apart. Momentum is the standard diagnostic for exactly
# that confusion.
#
#   mom_12_1   twelve-month return excluding the most recent month.
#              The academic definition (Jegadeesh-Titman); the last month
#              is dropped because short-horizon returns mean-revert and
#              would work against the signal.
#   from_high  how far below the 52-week high, which is the number that
#              says how much has already been conceded.
#   DIVERGENCE cover >= 60% AND mom_12_1 <= -20%: the business standing
#              still covers most of the price AND the market is still
#              selling. That is either the best entry in the table or a
#              value trap, and the framework alone cannot say which.
# =====================================================================
def momentum(d):
    return d.get('mom_12_1')

def from_high(d):
    return d.get('from_high')

def divergence(d):
    c, mm = cover(d), d.get('mom_12_1')
    if c is None or mm is None: return False
    return c >= 0.60 and mm <= -20.0

def _fetch_momentum(tk, d):
    """12-1 return and distance from the 52-week high, from one history pull."""
    try:
        h = tk.history(period='13mo', auto_adjust=True)
        if h is None or h.empty or 'Close' not in h: return
        c = h['Close'].dropna()
        if len(c) < 60: return
        last = float(c.iloc[-1])
        d['momentum_observed_at'] = c.index[-1].isoformat()
        d['momentum_history_start'] = c.index[0].isoformat()
        skip = 21                                    # one month of trading days
        if len(c) > skip + 200:
            start = float(c.iloc[0]); end = float(c.iloc[-skip])
            if start: d['mom_12_1'] = round(100 * (end / start - 1), 1)
        hi = float(c.max())
        if hi: d['from_high'] = round(100 * (last / hi - 1), 1)
    except Exception:
        pass

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
        if d.get('midcycle'):              # producers: mean annual FCF, not TTM
            try:
                tk = yf.Ticker(d.get('yf', t))
                mid, last = midcycle_from_yahoo(tk)
                if mid and mid > 0:
                    d['fcf'] = round(mid / 1e6, 1)
                    d['fcf_ttm'] = round(last / 1e6, 1) if last else None
                    d['built'] = 'mid-cycle'
                    if not d.get('shares'):
                        fi = {}
                        try: fi = dict(tk.fast_info) or {}
                        except Exception: pass
                        sh = fi.get('shares')
                        if sh: d['shares'] = round(sh / 1e6, 2)
                else:
                    d['boot_note'] = 'mid-cycle FCF not positive across the cycle'
            except Exception as ex:
                d['boot_note'] = f'mid-cycle fetch failed: {type(ex).__name__}'
            continue
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
        # [FIX] history/ now also holds _cohort.json, which is NOT a daily
        # snapshot. Reading it as one crashes on its string-valued keys.
        # Any leading-underscore file is metadata, not a day.
        if os.path.basename(fp).startswith('_'):
            continue
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
        ser = None
        d['quote_observed_at'], d['quote_time_status'] = None, 'UNKNOWN'
        for field in ('mom_12_1', 'from_high', 'r_wacc', 'beta', 'wacc_inputs', 'wacc_details',
                      'momentum_observed_at', 'momentum_history_start'):
            d.pop(field, None)
        if d.get('na') and not d.get('midcycle'):
            # `na` means NGV is structurally unavailable, not that the security has no price.
            # Keep the reason separate so EPV can value rows such as AWK without suppressing
            # price/momentum data for the whole row.
            d['ngv_note'] = 'N/A: ' + d['na']
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
            # Retrieval time is not necessarily the quote's exchange timestamp.
            d['quote_observed_at'] = None
            d['quote_time_status'] = 'UNKNOWN'
            if ser is not None and len(ser):
                d['quote_observed_at'] = ser.index[-1].isoformat()
                d['quote_time_status'] = 'DAILY_CLOSE'
            _fetch_momentum(tk, d)
            if WACC is not None and d.get('shares'):
                try:
                    inp = WACC.fetch(d.get('yf', t), yf=yf)
                    if inp and inp.get('beta'):
                        mc = d['price'] * d['shares'] * 1e6
                        rw, _det = WACC.compute(
                            beta=inp['beta'], market_cap=mc or inp.get('market_cap'),
                            total_debt=inp.get('total_debt'), tax_rate=inp.get('tax_rate'))
                        d['r_wacc'], d['beta'] = rw, inp['beta']
                        d['wacc_inputs'], d['wacc_details'] = inp, _det
                except Exception:
                    pass
        except Exception as e:
            d['price_note'] = f'fetch failed: {type(e).__name__}'

EPV_CACHE_FILE = os.path.join('history', '_epv_cache.json')
EPV_CACHE_DAYS = 7


def _epv_cache_load():
    try:
        with open(EPV_CACHE_FILE, encoding='utf-8') as f:
            x = json.load(f)
            return x if isinstance(x, dict) else {}
    except Exception:
        return {}


def _epv_cache_fresh(rec):
    try:
        then = datetime.fromisoformat(rec.get('asof')).replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - then).days < EPV_CACHE_DAYS
    except Exception:
        return False


def _epv_cache_write(cache):
    os.makedirs('history', exist_ok=True)
    tmp = EPV_CACHE_FILE + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(cache, f, indent=1, default=str)
    os.replace(tmp, EPV_CACHE_FILE)


def populate_epv(force=False):
    """Populate a second, normalised valuation lens without touching NGV or score.

    Annual statement inputs are cached for seven days; EPV itself is recomputed every run
    with the current WACC/manual fallback, so a changing discount rate still flows through.
    """
    if EPV is None:
        for d in DATA.values(): d['epv_note'] = 'epv.py not present'
        return
    cache = _epv_cache_load()
    dirty = False
    today = datetime.now(timezone.utc).date().isoformat()
    for t, d in DATA.items():
        d['epv_value'] = None
        for field in ('epv_inputs', 'epv_inputs_retrieved_on', 'epv_normalised_earnings',
                      'epv_net_debt', 'epv_wacc', 'epv_rate_source', 'epv_tax_source'):
            d.pop(field, None)
        d['epv_confidence'] = 'NONE'
        d['epv_confidence_score'] = 0.0
        d['epv_note'] = ''
        if d.get('built') == 'fund':
            d['epv_note'] = 'fund: company EPV not applicable'
            continue
        sym = d.get('yf', t)
        rec = cache.get(sym) if isinstance(cache.get(sym), dict) else None
        inputs = rec.get('inputs') if (rec and not force and _epv_cache_fresh(rec)) else None
        if not inputs:
            try: inputs = EPV.fetch(sym, yf=yf)
            except Exception: inputs = None
            if inputs:
                cache[sym] = {'asof': today, 'inputs': inputs}
                dirty = True
        if not inputs:
            d['epv_note'] = 'annual statement inputs unavailable'
            continue
        inp = dict(inputs)
        d['epv_inputs'] = inp
        d['epv_inputs_retrieved_on'] = (cache.get(sym) or {}).get('asof')
        tax_override = d.get('epv_tax_rate')
        if tax_override is not None:
            inp['tax_rate'] = tax_override
            inp['tax_source'] = 'manual-epv-tax-rate'
        rr, rsrc = rate_used(d)
        try:
            ans = EPV.compute(wacc=rr, **{k: inp.get(k) for k in EPV.FIELDS})
        except Exception as ex:
            ans = None
            d['epv_note'] = f'EPV compute failed: {type(ex).__name__}'
        if not ans or not math.isfinite(ans.get('epv_per_share', float('nan'))):
            if not d.get('epv_note'): d['epv_note'] = 'EPV not computable from fetched inputs'
            continue
        d['epv_value'] = ans['epv_per_share']
        d['epv_normalised_earnings'] = ans['normalised_earnings']
        d['epv_net_debt'] = ans['net_debt']
        d['epv_wacc'] = rr
        d['epv_rate_source'] = rsrc
        d['epv_tax_source'] = inp.get('tax_source', 'unknown')
        cf = EPV.confidence(inp, tax_overridden=(tax_override is not None))
        d['epv_confidence'] = cf['level']
        d['epv_confidence_score'] = cf['score']
        d['epv_note'] = '; '.join(cf.get('reasons') or [])
    if dirty:
        _epv_cache_write(cache)


def observation(macro, bundle, captured_at=None):
    """Prepare a validated, detached observation without writing anything."""
    errors, _ = validate_full()
    if errors:
        raise ValueError('VALIDATION FAILED: ' + '; '.join(errors))
    rec = {t: dict(price=d.get('price'), ngv=ngv(d), cover=cover(d), cushion=cushion(d),
                   score=score(d), risk=risk(d), verdict=verdict(t,d)[0],
                   regime=regime_scores(d), weight=d.get('weight'),
                   momentum=d.get('mom_12_1'), from_high=d.get('from_high'),
                   epv=epv(d), epv_cover=epv_cover(d), valuation_gap=valuation_gap(d),
                   valuation_read=valuation_read(d), epv_confidence=d.get('epv_confidence'),
                    ts=d.get('price_ts'), note=d.get('price_note'),
                    diagnostics=EVIDENCE.row_diagnostics(d, W)) for t,d in DATA.items()}
    rec['_portfolio'] = portfolio_regime()
    regime = macro.get('regime') if macro.get('ok') else None
    rec['_portfolio_proposal'] = (portfolio_proposal(regime)
                                  if regime in REGIMES else None)
    rec['_models'] = dict(engine='v15.3-evidence', regime=REGIME_MODEL_VERSION,
                          regime_spec_sha256=regime_spec_sha256(),
                          ngv='fcf-per-share-capitalised', epv='greenwald-template-lens-v1')
    return EVIDENCE.create_record(DATA, rec, macro, rec['_models'], bundle['sha256'], captured_at)


def portfolio_proposal(regime):
    """Ten-slot planning book; the legacy raw regime book remains unchanged."""
    return construct_portfolio(regime_book(regime, len(DATA)),
                               entry_limits={t: entry_price(d) for t, d in DATA.items()})


def snapshot(macro=None, captured_at=None):
    """Compatibility API: archive a validated observation; never overwrite a day."""
    bundle = EVIDENCE.model_bundle(Path(__file__).parent)
    macro = read_macro() if macro is None else macro
    record = observation(macro, bundle, captured_at)
    return EVIDENCE.publish_record(record, bundle)['day']


def run_build():
    """One macro reading shared by the report and immutable observation."""
    with EVIDENCE.build_lock():
        bootstrap_fundamentals()
        fetch_prices()
        populate_epv()
        macro = read_macro()
        bundle = EVIDENCE.model_bundle(Path(__file__).parent)
        record = observation(macro, bundle)
        # Rendering can fail without publishing an observation or changing index.html.
        html = build_html(macro=macro, write=False)
        published = EVIDENCE.publish_record(record, bundle)
        atomic_text('index.html', html)
        # The report's forward panel consumes prior frozen evidence. New cohorts
        # become visible next run, after this validated observation is published.
        freeze_cohorts()
        return published


# =====================================================================
# VALIDATE  --  runs on every build and REFUSES to write index.html
#
# Almost every bug in this engine has been the same shape: something
# derived was presented without checking what it meant, or one thing
# changed and a dependant was not re-checked. Examples that shipped:
#   sanity=(0,0) rejected 16 correct prices as out of range
#   proximity bands were inverted, calling "already through entry" "near"
#   regime_history read _cohort.json as a daily snapshot and crashed
#   a new sector arrived unmapped and silently scored 0 affinity
#   an unguarded canvas lookup killed every later line of JavaScript
# None of those needed more care. They needed an assertion.
# =====================================================================
def validate(strict=True):
    """Back-compat wrapper: blocking problems only."""
    return validate_full()[0]


def validate_full():
    """[FIX] Returns (errors, warnings).

       v25.0 shipped with ONE list and build_html() exiting on any entry.
       The WACC-gap check was described as informational and was in fact
       build-blocking, so the first live run with real betas killed the
       deploy. A check that reports a FACT ('this beta looks odd') must not
       stop a build; only a check that proves the OUTPUT is wrong may."""
    p, warn = [], []
    secs = {d.get('sector') for d in DATA.values() if d.get('sector')}
    for r in REGIMES:
        miss = sorted(x for x in secs if x not in AFF[r])
        if miss: p.append(f'{r}: sectors unmapped -> {miss} (they would score 0 affinity silently)')
    for t, d in DATA.items():
        n = ngv(d)
        if n is not None and n < 0:
            p.append(f'{t}: NEGATIVE NGV {n:.2f} -- a negative FCF was written into the row')
        if d.get('na') and d.get('fcf') is not None and not d.get('midcycle'):
            p.append(f'{t}: flagged na but still carries fcf={d["fcf"]} -- one of them is wrong')
        if d.get('weight') and not d.get('held'):
            p.append(f'{t}: has weight={d["weight"]} but held=False')
        if d.get('held') and not d.get('weight'):
            p.append(f'{t}: held=True with no weight -- it will vanish from the portfolio panel')
        b = d.get('sanity')
        if b is not None and not _valid_band(b):
            p.append(f'{t}: sanity={b} is not a usable interval; every price will be rejected')
        if d.get('fcf') is not None and not d.get('shares'):
            p.append(f'{t}: fcf without shares -- NGV cannot be built')
    # Model regression is build-blocking: explainability is not regression testing.
    spec_hash = regime_spec_sha256()
    if spec_hash != REGIME_SPEC_EXPECTED_SHA256:
        p.append(f'regime spec changed: expected {REGIME_SPEC_EXPECTED_SHA256}, got {spec_hash}')
    p.extend(regime_regression_errors())
    for t, d in DATA.items():
        rg0 = regime_scores(d)
        if rg0:
            probe = dict(d); probe['weight'] = 999999.0
            if regime_scores(probe) != rg0:
                p.append(f'{t}: portfolio weight changes regime fit -- forbidden')
            comp = regime_fit_components(d)
            if any(comp[r]['total'] != rg0[r] for r in REGIMES):
                p.append(f'{t}: regime components do not reconcile to reported fit')
        e = epv(d)
        if e is not None and not math.isfinite(e):
            p.append(f'{t}: non-finite EPV {e}')
        if e is not None and e <= 0:
            warn.append(f'{t}: EPV <= 0 ({e:.2f}); normalised earning power/net debt needs review')
        vg = valuation_gap(d)
        if vg is not None and abs(vg) >= 1.0:
            warn.append(f'{t}: EPV/NGV divergence {vg:+.0%}; inspect normalisation and net debt')

    for t, d in DATA.items():
        if d.get('r_wacc') and abs(d['r_wacc'] - d.get('r', .08)) > 0.025:
            warn.append(f'{t}: WACC {100*d["r_wacc"]:.1f}% vs manual r {100*d.get("r",.08):.1f}% '
                     f'-- a {100*abs(d["r_wacc"]-d.get("r",.08)):.1f}pp gap. Check the beta '
                     f'({d.get("beta")}) before trusting the NGV.')
    w = sum(d['weight'] for d in DATA.values() if d.get('weight'))
    tgt = 100.0 - CASH_PCT          # [FIX] the first validate() run flagged this:
    if w and abs(w - tgt) > 3:      # weights cover INVESTED positions, cash is the rest
        warn.append(f'weights sum to {w:.1f}%, expected ~{tgt:.1f}% with CASH_PCT={CASH_PCT}')
    dup = {}
    for t, d in DATA.items(): dup.setdefault(d['yf'], []).append(t)
    for y, ts in dup.items():
        if len(ts) > 1: p.append(f'duplicate Yahoo symbol {y} on {ts}')
    return p, warn


# =====================================================================
# SCREEN  --  quality and regime are DIFFERENT QUESTIONS
#
# I once produced a regime screen, sorted it by cover inside each
# affinity tier, and called the top row "the strongest name on the
# list". It was the strongest on SCORE and thirteen points weaker on
# REGIME FIT than the rows below it. The tool made that easy to do,
# so the tool is what changes: a screen now requires an explicit
# purpose and ranks ONLY by that purpose. The other dimension is
# reported beside it and never used for ordering.
# =====================================================================
def screen(purpose, regime=None, min_score=5.50, min_cover=None, exclude_verdicts=
           ('DO NOT ADD', 'SELL', 'AVOID', 'NO SCORE'), held_only=False, limit=15):
    """purpose='quality'  -> rank by score. Regime fit shown, not ranked on.
       purpose='regime'   -> rank by fit to `regime`. Score shown, not ranked on.
       purpose='duration' -> rank by cover, for a rates-up view."""
    if purpose not in ('quality', 'regime', 'duration'):
        raise ValueError("purpose must be 'quality', 'regime' or 'duration'")
    if purpose == 'regime' and regime not in REGIMES:
        raise ValueError('purpose="regime" needs regime=one of ' + str(REGIMES))
    out = []
    for t, d in DATA.items():
        s, c, v = score(d), cover(d), verdict(t, d)[0]
        if s is None or s < min_score or v in exclude_verdicts: continue
        if min_cover is not None and (c is None or c < min_cover): continue
        if held_only and not d.get('weight'): continue
        fit = fit_now(d, regime) if regime else None
        aff = AFF[regime].get(d.get('sector', '')) if regime else None
        out.append(dict(t=t, score=s, cover=c, cushion=cushion(d), risk=risk(d),
                        verdict=v, sector=d.get('sector', ''), fit=fit, aff=aff,
                        best=best_regime(d)[0], held=bool(d.get('weight')),
                        cycle=cycle_pos(d), mom=d.get('mom_12_1')))
    key = {'quality':  lambda r: -r['score'],
           'regime':   lambda r: -(r['fit'] if r['fit'] is not None else -1),
           'duration': lambda r: -(r['cover'] or 0)}[purpose]
    out.sort(key=key)
    return out[:limit]

# ---------------- render ----------------
def fmt(x, spec, dash='&mdash;'):  return dash if x is None else format(x, spec)

def cls(x, good, bad, invert=False):
    if x is None: return 'pr na'
    if invert: return 'pr pos' if x <= good else ('pr neg' if x >= bad else 'pr mid')
    return 'pr pos' if x >= good else ('pr neg' if x <= bad else 'pr mid')

CLOCK_CSS = {'CLOCK':'s-clock','CONC':'s-conc','DIV':'s-diverse'}
REG_CSS = {'GOLDILOCKS':'g-gold','REFLATION':'g-refl','INFLATION':'g-infl',
           'STAGFLATION':'g-stag','RECESSION':'g-rec'}

CSS = """
:root{--bg:#0c0d12;--panel:#13151d;--line:#232634;--tx:#e7e9f0;--mu:#9aa0b3;
--green:#4ecb8a;--red:#f06a6a;--amber:#e5b45c;--cyan:#5cc8d8;
--sans:'Inter','SF Pro Text',system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;
--mono:'JetBrains Mono','SF Mono',ui-monospace,'Roboto Mono',Menlo,Consolas,monospace;}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{background:var(--bg);color:var(--tx);margin:0;padding:24px 14px 44px;
font-family:var(--sans);font-size:15px;line-height:1.55;
-webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale;
text-rendering:optimizeLegibility;font-feature-settings:'cv05','ss01'}
.kicker{font-family:var(--mono);font-size:11px;letter-spacing:.16em;color:var(--cyan);
text-transform:uppercase;margin-bottom:10px}
h1{font-weight:700;font-size:32px;line-height:1.15;letter-spacing:-.02em;margin:0 0 12px}
h2{font-size:18px;font-weight:650;letter-spacing:-.01em;margin:0 0 10px}
.lede{color:#c8ccd8;max-width:68ch;margin:0 0 16px;font-size:14px;line-height:1.6}
.box{border:1px solid var(--line);border-radius:12px;padding:16px 17px;background:var(--panel);margin-bottom:16px}
.tw{overflow-x:auto;-webkit-overflow-scrolling:touch;border-radius:10px;
border:1px solid var(--line);background:var(--panel)}
table{width:100%;border-collapse:collapse;font-size:12.5px;font-variant-numeric:tabular-nums}
th{text-align:left;color:var(--mu);font-weight:600;font-size:10px;letter-spacing:.07em;
text-transform:uppercase;border-bottom:1px solid var(--line);padding:11px 7px;white-space:nowrap;
position:sticky;top:0;background:var(--panel);z-index:2}
td{border-bottom:1px solid #1a1d27;padding:9px 7px;vertical-align:middle}
tr.held{background:#141826}
tr.hit td:first-child{box-shadow:inset 3px 0 0 var(--green)}
.rk{color:var(--mu);font-family:var(--mono);font-size:11px}
.tk{font-weight:700;font-size:13.5px;letter-spacing:-.01em;white-space:nowrap;
position:sticky;left:0;background:inherit;z-index:1}
tr.held .tk{background:#141826}
thead .tk,th:nth-child(2){z-index:3}
.se{color:#868da0;font-size:11px;white-space:nowrap}
.sc{font-family:var(--mono);font-weight:600;font-size:13.5px;color:var(--green)}
.pr{font-family:var(--mono);font-size:12px;white-space:nowrap}
.pr.pos{color:var(--green)}.pr.mid{color:var(--amber)}.pr.neg{color:var(--red)}.pr.na{color:#6b7183}
.in{font-family:var(--mono);font-size:10.5px;color:var(--mu);white-space:nowrap}
.pv{font-family:var(--mono);font-size:10.5px;white-space:nowrap}
.pv.exact{color:#4a5165}.pv.back-solved{color:#a07f45}.pv.est{color:#b96565}
.pv.auto{color:#5f7fa8}.pv.fund{color:#8a6ab0}.pv.mid-cycle{color:#c08a4a}
.mono{font-family:var(--mono);font-size:12px;color:#c8ccd8;white-space:nowrap}
.pill{display:inline-block;padding:3px 8px;border-radius:5px;font-size:9.5px;font-weight:700;
font-family:var(--mono);letter-spacing:.02em;white-space:nowrap}
.p-sbuy{background:#123a26;color:#66e39c;border:1px solid #1e5c3c}
.p-buy{background:#12331f;color:var(--green);border:1px solid #1d5433}
.p-hpos{background:#13202e;color:#7fb6d8;border:1px solid #23405c}
.p-hneg{background:#2b2210;color:var(--amber);border:1px solid #574318}
.p-sell{background:#331414;color:var(--red);border:1px solid #5c2020}
.empty{background:#181a22;color:#7b8195;border:1px solid #272b38}
.v-buy{background:#0f3d24;color:#5fe39a;border:1px solid #1e6b40}
.v-buymod{background:#12331f;color:var(--green);border:1px solid #1d5433}
.v-buyhi{background:#2b2210;color:var(--amber);border:1px solid #574318}
.v-trap{background:#2c1440;color:#d6a8ff;border:1px solid #543072}
.v-acc{background:#13202e;color:#7fb6d8;border:1px solid #23405c}
.v-hold{background:#181a22;color:var(--mu);border:1px solid #272b38}
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
.x-atngv{background:#0f3d24;color:#5fe39a;border:1px solid #1e6b40}
.x-clear{background:#13202e;color:#7fb6d8;border:1px solid #23405c}
.x-near{background:#123a26;color:#66e39c;border:1px solid #1e5c3c}
.x-appr{background:#2b2210;color:var(--amber);border:1px solid #574318}
.lock{border:1px dashed #2a7a4a;border-radius:12px;padding:16px;background:#0e1712;margin-bottom:16px}
input,select,textarea{background:#0a0b10;color:var(--tx);border:1px solid #2a2e3c;border-radius:7px;
padding:9px 11px;font-family:var(--mono);font-size:14px}
button{background:#1d5433;color:var(--green);border:1px solid #2a7a4a;border-radius:8px;
padding:10px 16px;font-weight:700;font-size:14px;font-family:var(--sans);cursor:pointer}
.foot{color:#6b7183;font-family:var(--mono);font-size:11px;line-height:1.7;
border-top:1px solid var(--line);padding-top:14px;margin-top:26px}
@media (max-width:640px){
  body{padding:18px 10px 40px;font-size:14.5px}
  h1{font-size:27px}
  h2{font-size:16.5px}
  .lede{font-size:13.5px}
  table{font-size:12px}
}
"""

# [FIX 1] THE BUG THAT SHOULD HAVE KILLED THE SCRIPT.
# In the previous version this JavaScript sat inside an f-string. Python reads a
# bare "{" in an f-string as the start of an expression, so `function f() {`
# raises SyntaxError at import time. The CSS was escaped with {{ }} but the JS
# was not. Keeping CSS and JS as PLAIN strings and concatenating is the fix --
# it also means you never have to double-brace anything again.
JS = """
const KNOWN = __TICKERS__;
const REPO = 'usubillaga/InvestorAce';

function addTicker(){
  const input  = document.getElementById('newTicker');
  const out    = document.getElementById('out');
  const link   = document.getElementById('gh');
  const button = document.getElementById('addTickerButton');
  if (!input || !out || !link) { console.error('add-ticker controls missing'); return false; }

  const t = input.value.trim().toUpperCase();
  if (!t) { out.value = 'Enter a Yahoo ticker first, e.g. ROAD or ASML.AS.'; input.focus(); return false; }
  const key = t.split('.')[0];
  if (KNOWN.includes(key)) { out.value = key + ' is already in the model.'; return false; }

  const body = [
    'Auto-add ' + t + '.', '',
    'Do not edit the title -- the workflow reads the ticker from it.', '',
    'It fetches price, shares and TTM free cash flow from Yahoo, drafts the',
    'mechanical fields, commits and redeploys. Two fields still need a human:',
    '  deliver : the company own leading metric (revenue growth fills as a proxy)',
    '  clock   : CLOCK / CONC / DIV', '',
    'Negative free cash flow is written as na= with no NGV, by design.'
  ].join('\\n');

  const url = 'https://github.com/' + REPO + '/issues/new'
    + '?title=' + encodeURIComponent('add-ticker: ' + t)
    + '&body='  + encodeURIComponent(body);

  link.href = url;
  link.textContent = 'Open GitHub issue for ' + t + ' \\u2192';
  link.hidden = false;
  link.style.display = 'inline-block';
  out.value = 'Opening GitHub...\\n\\nIf it does not open, use the green link below.\\n\\n' + url;
  if (button) button.disabled = true;
  window.location.assign(url);   // not window.open -- mobile blocks popups
  return true;
}

function initTickerAdder(){
  const button = document.getElementById('addTickerButton');
  const input  = document.getElementById('newTicker');
  if (!button || !input) return;
  button.addEventListener('click', addTicker);
  input.addEventListener('keydown', function(e){
    if (e.key === 'Enter') { e.preventDefault(); addTicker(); }
  });
}
if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initTickerAdder);
else initTickerAdder();
"""
FIT_JS = """
const FL = __FITLAB__, FV = __FITVAL__, FC = __FITCOL__;
const fitEl = document.getElementById('fitChart');
if (FL.length && window.Chart && fitEl) {
  new Chart(fitEl.getContext('2d'), {
    type: 'bar',
    data: { labels: FL, datasets: [{ data: FV, backgroundColor: FC, borderWidth: 0 }] },
    options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { x: { min: 0, max: 100, ticks: { color: '#5e6373', font: { size: 9 } }, grid: { color: '#1a1d27' } },
                y: { ticks: { color: '#8f95a8', font: { size: 10 } }, grid: { display: false } } } }
  });
}
"""


SCAT_JS = """
const PTS = __PTS__;
window.drawPortfolioCharts = function(){
  if (window.drawRegimeHistory) window.drawRegimeHistory();
  if (window.drawSectors) window.drawSectors();
  const rwEl = document.getElementById('rwChart');
  if (PTS.length && window.Chart && rwEl && rwEl.dataset.drawn !== '1') {
  rwEl.dataset.drawn = '1';
  new Chart(rwEl.getContext('2d'), {
    type: 'scatter',
    data: { datasets: [{ data: PTS, pointRadius: 7, pointHoverRadius: 10,
      backgroundColor: PTS.map(p => p.c), borderColor: '#0c0d12', borderWidth: 1 }]},
    options: { responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false },
        tooltip: { callbacks: { label: c => c.raw.t + '  rank ' + c.raw.x + '  ' + c.raw.y.toFixed(1) + '%' } } },
      scales: {
        x: { title:{display:true,text:'rank (1 = best)',color:'#8f95a8',font:{size:10}}, min:0,
             ticks:{color:'#5e6373',font:{size:9}}, grid:{color:'#1a1d27'} },
        y: { title:{display:true,text:'weight %',color:'#8f95a8',font:{size:10}}, min:0,
             ticks:{color:'#5e6373',font:{size:9}}, grid:{color:'#1a1d27'} } } }
  });
}
};
"""


ZIEL_JS = """
const ZP = "__ZIELPAYLOAD__";
function b64utf8(s){
  return decodeURIComponent(Array.prototype.map.call(atob(s),
    c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)).join(''));
}
function revealZiel(){
  const box = document.getElementById('zielBox');
  if (!box || box.dataset.open === '1') return;
  box.innerHTML = b64utf8(ZP);
  box.dataset.open = '1';
  if (window.drawPortfolioCharts) window.drawPortfolioCharts();
}
function tryZiel(){
  const el = document.getElementById('zielIn');
  const v = (el && el.value || '').trim().toLowerCase();
  if (v === 'ziel' || v === 'ziele') { if (el) el.value = ''; revealZiel(); }
}
function initZiel(){
  const b = document.getElementById('zielBtn'), i = document.getElementById('zielIn');
  if (b) b.addEventListener('click', tryZiel);
  if (i) i.addEventListener('keydown', function(e){
    if (e.key === 'Enter') { e.preventDefault(); tryZiel(); }
  });
  if ((location.hash || '').toLowerCase() === '#ziel') revealZiel();
  let buf = '';
  document.addEventListener('keydown', function(e){
    const tag = (e.target && e.target.tagName || '').toLowerCase();
    if (tag === 'input' || tag === 'textarea') return;      // do not eat the ticker box
    if (e.key && e.key.length === 1) {
      buf = (buf + e.key.toLowerCase()).slice(-8);
      if (buf.endsWith('ziel')) { buf = ''; revealZiel(); }
    }
  });
}
if (window.drawSectors) window.drawSectors();
if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initZiel);
else initZiel();
"""


QUAD_JS = """
const QT = __TRAIL__, QH = __HEADING__;
if (QT.length && window.Chart) {
  const el = document.getElementById('quadChart');
  if (el) {
    const pts = QT.map((p,k) => ({x:p.g, y:p.i, l:p.label, q:p.quadrant, last:k===QT.length-1}));
    const lim = Math.max(6, Math.ceil(Math.max(...pts.flatMap(p=>[Math.abs(p.x),Math.abs(p.y)]))*1.35));
    // four quadrants painted behind the path, so the position reads at a glance
    const quads = {
      id:'quads',
      beforeDatasetsDraw(c){
        const {ctx, chartArea:a, scales:{x,y}} = c;
        const zx = x.getPixelForValue(0), zy = y.getPixelForValue(0);
        const fill = (x0,y0,x1,y1,col) => { ctx.save(); ctx.fillStyle=col;
          ctx.fillRect(x0, y0, x1-x0, y1-y0); ctx.restore(); };
        fill(zx, a.top, a.right, zy, 'rgba(99,198,240,.10)');   // g+ i+  reflation
        fill(zx, zy, a.right, a.bottom, 'rgba(102,227,156,.10)'); // g+ i-  goldilocks
        fill(a.left, a.top, zx, zy, 'rgba(240,106,106,.11)');   // g- i+  stagflation
        fill(a.left, zy, zx, a.bottom, 'rgba(214,168,255,.10)'); // g- i-  recession
        ctx.save();
        ctx.strokeStyle='#2a2e3c'; ctx.lineWidth=1;
        ctx.beginPath(); ctx.moveTo(a.left,zy); ctx.lineTo(a.right,zy);
        ctx.moveTo(zx,a.top); ctx.lineTo(zx,a.bottom); ctx.stroke();
        ctx.font='600 11px Inter, sans-serif'; ctx.textAlign='center';
        ctx.fillStyle='#63c6f0'; ctx.fillText('REFLATION',  (zx+a.right)/2, a.top+18);
        ctx.fillStyle='#f06a6a'; ctx.fillText('STAGFLATION',(a.left+zx)/2,  a.top+18);
        ctx.fillStyle='#66e39c'; ctx.fillText('GOLDILOCKS', (zx+a.right)/2, a.bottom-10);
        ctx.fillStyle='#d6a8ff'; ctx.fillText('RECESSION',  (a.left+zx)/2,  a.bottom-10);
        ctx.restore();
      }
    };
    new Chart(el.getContext('2d'), {
      type:'scatter',
      data:{ datasets:[{
        data: pts, showLine:true, borderColor:'#e7e9f0', borderWidth:2,
        pointBackgroundColor: pts.map(p => p.last ? '#ffffff' : 'rgba(231,233,240,.55)'),
        pointBorderColor: pts.map(p => p.last ? '#0c0d12' : 'transparent'),
        pointBorderWidth: pts.map(p => p.last ? 3 : 0),
        pointRadius: pts.map((p,k) => p.last ? 9 : 3 + k*0.8),
        pointHoverRadius: 11, tension:.25
      }]},
      options:{ responsive:true, maintainAspectRatio:false, animation:false,
        plugins:{ legend:{display:false},
          tooltip:{ callbacks:{ label: c =>
            c.raw.l + ' &middot; growth ' + c.raw.x.toFixed(1) + '% &middot; inflation ' +
            c.raw.y.toFixed(1) + '% &middot; ' + c.raw.q }}},
        scales:{
          x:{ min:-lim, max:lim, title:{display:true,text:'growth impulse  (S&P + copper, 6m)',
              color:'#9aa0b3',font:{size:11}}, ticks:{color:'#6b7183',font:{size:10}},
              grid:{color:'#171a23'} },
          y:{ min:-lim, max:lim, title:{display:true,text:'inflation impulse  (oil + 10y, 6m)',
              color:'#9aa0b3',font:{size:11}}, ticks:{color:'#6b7183',font:{size:10}},
              grid:{color:'#171a23'} } }
      },
      plugins:[quads]
    });
  }
}
"""


SEC_JS = """
const SD = __SECDATES__, SP = __SECPATHS__, SC = __SECCOLS__;
window.drawSectors = function(){
  const el = document.getElementById('secChart');
  if (!el || !window.Chart || !SD.length || el.dataset.drawn === '1') return;
  el.dataset.drawn = '1';
  new Chart(el.getContext('2d'), {
    type: 'line',
    data: { labels: SD, datasets: Object.keys(SP).map(k => ({
      label: k, data: SP[k], borderColor: SC[k], backgroundColor: 'transparent',
      borderWidth: k === 'SPY' ? 3 : 1.6, borderDash: k === 'SPY' ? [] : [],
      pointRadius: 0, tension: .2 })) },
    options: { responsive: true, maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: { legend: { labels: { color: '#9aa0b3', font: { size: 10 },
                 boxWidth: 11, usePointStyle: true } } },
      scales: { x: { ticks: { color: '#5e6373', font: { size: 9 }, maxTicksLimit: 8 },
                     grid: { color: '#171a23' } },
                y: { type: 'logarithmic', ticks: { color: '#5e6373', font: { size: 9 } },
                     grid: { color: '#171a23' },
                     title: { display: true, text: 'rebased to 100', color: '#9aa0b3',
                              font: { size: 10 } } } } }
  });
};
"""

CHART_JS = """
const RD = __DATES__, RS = __SERIES__;
window.drawRegimeHistory = function(){
  const el = document.getElementById('regimeChart');
  if (!el || !window.Chart || el.dataset.drawn === '1') return;
  el.dataset.drawn = '1';
  if (!RD.length) {
    const n = document.getElementById('chartNote');
    if (n) n.textContent = 'No history yet. The line appears once history/ has two or more daily snapshots.';
    return;
  }
  new Chart(el.getContext('2d'), {
    type: 'line',
    data: { labels: RD, datasets: [
      {label:'Goldilocks', data:RS.GOLDILOCKS,  borderColor:'#66e39c', backgroundColor:'transparent', tension:.3, borderWidth:2},
      {label:'Reflation',  data:RS.REFLATION,   borderColor:'#63c6f0', backgroundColor:'transparent', tension:.3, borderWidth:2},
      {label:'Inflation',  data:RS.INFLATION,   borderColor:'#e5b45c', backgroundColor:'transparent', tension:.3, borderWidth:2},
      {label:'Stagflation',data:RS.STAGFLATION, borderColor:'#f06a6a', backgroundColor:'transparent', tension:.3, borderWidth:2},
      {label:'Recession',  data:RS.RECESSION,   borderColor:'#d6a8ff', backgroundColor:'transparent', tension:.3, borderWidth:2}
    ]},
    options: { responsive:true, maintainAspectRatio:false,
      plugins:{ legend:{ labels:{ color:'#8f95a8', font:{size:10}, boxWidth:12 } } },
      scales:{ x:{ ticks:{color:'#5e6373', font:{size:9}}, grid:{color:'#1a1d27'} },
               y:{ min:0, max:100, ticks:{color:'#5e6373', font:{size:9}}, grid:{color:'#1a1d27'} } } }
  });
};
"""

def build_html(macro=None, write=True):
    errors, warnings = validate_full()
    for w_ in warnings:
        print('   ~ ' + w_, file=sys.stderr)
    if errors:
        print('VALIDATION FAILED - index.html NOT written:', file=sys.stderr)
        for p_ in errors: print('   ! ' + p_, file=sys.stderr)
        raise SystemExit(1)
    rows = []
    ranked = sorted(DATA.items(), key=lambda kv: (-(score(kv[1]) if score(kv[1]) is not None else -1), kv[0]))
    for i,(t,d) in enumerate(ranked, 1):
        s, rk, c, cu, eg = score(d), risk(d), cover(d), cushion(d), entry_gap(d)
        bn, bc = band(s); vn, vc = verdict(t, d)
        note = d.get('price_note','')
        rows.append(
          '<tr%s>' % (' class="hit"' if proximity(d)[0] else '')
          + f'<td class="rk">{i}</td>'
          + f'<td class="tk">{t}</td>'
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
          + (lambda mm, fh: '<td class="mono">'
             + (f'<span class="{cls(mm,10,-15)}">{mm:+.0f}%</span>' if mm is not None else '<span class="pr na">&mdash;</span>')
             + (f'<br><span style="font-size:10px;color:#7b8195">{fh:+.0f}% off high</span>' if fh is not None else '')
             + ('<br><span class="pill x-appr">DIVERGENCE</span>' if divergence(d) else '')
             + '</td>')(momentum(d), from_high(d))
          + (lambda rg, sc: f'<td><span class="pill {REG_CSS.get(rg,"empty")}">{rg or "&mdash;"}</span>'
                            f'{f"<br><span style=font-size:10px;color:#7b8195>{sc:.0f}</span>" if sc else ""}</td>'
            )(*best_regime(d))
          + f'<td class="mono">{fmt(ngv(d),",.2f")}</td>'
          + (lambda ev, ec: f'<td class="mono">{fmt(ev,",.2f")}'
             + (f'<br><span style="font-size:10px;color:#7b8195">{ec}</span>' if ev is not None else '')
             + '</td>')(epv(d), d.get('epv_confidence',''))
          + (lambda vg, vr: '<td class="mono">'
             + ((f'<span class="{valuation_gap_class(d)}">{vg:+.0%}</span>') if vg is not None else '&mdash;')
             + (f'<br><span style="font-size:10px;color:#7b8195">{vr}</span>' if vr else '')
             + '</td>')(valuation_gap(d), valuation_read(d))
          + f'<td class="mono">{fmt(entry_price(d),",.2f")}</td>'
          + (lambda pf, gp: f'<td class="mono">{fmt(d.get("price"),",.2f")}'
             + (f'<br><span class="pill {PROX_CSS[pf]}">{pf} {gp:+.1f}%</span>' if pf else ''))(*proximity(d))
          + f'{""}'
          + (f'<br><span style="color:#f06a6a;font-size:10px">{note}</span>' if note else '')
          + '</td>'
          + f'<td class="mono" style="font-size:10px;color:#7b8195">{d.get("price_ts") or ""}</td>'
          + (lambda rr, src: f'<td class="pv {d.get("built","exact")}">{d.get("built","exact")}'
             + f'<br><span style="font-size:10px;color:'
             + ('#5cc8d8' if src == 'wacc' else '#7b8195')
             + f'">r {100*rr:.2f}% {src}</span>')(*rate_used(d))
          + (f'<br><span style="color:#e5b45c;font-size:10px">{cycle_note(d)}</span>' if cycle_note(d) else '')
          + '</td></tr>')

    stamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    priced = sum(1 for d in DATA.values() if d.get('price') is not None)
    withngv = sum(1 for d in DATA.values() if ngv(d) is not None)
    na = sum(1 for d in DATA.values() if d.get('na'))
    issues = {t: d['price_note'] for t,d in DATA.items() if d.get('price_note') and not d.get('na')}
    for t,d in DATA.items():
        if d.get('boot_note'): issues[t] = 'NGV: ' + d['boot_note']

    js = JS.replace('__TICKERS__', json.dumps(sorted(DATA.keys())))
    M = read_macro() if macro is None else macro
    cur_reg = M.get('regime') if M.get('ok') else None
    fits = sorted(((t, fit_now(d, cur_reg)) for t, d in DATA.items()), key=lambda kv: -(kv[1] or -1))
    fits = [(t, v) for t, v in fits if v is not None][:15]
    FIT_COL = {'GOLDILOCKS':'#66e39c','REFLATION':'#63c6f0','INFLATION':'#e5b45c',
               'STAGFLATION':'#f06a6a','RECESSION':'#d6a8ff'}
    bar = FIT_COL.get(cur_reg, '#5cc8d8')
    js += (QUAD_JS.replace('__TRAIL__', json.dumps(M.get('trail') or []))
                  .replace('__HEADING__', json.dumps(M.get('heading') or {})))
    SEC = sector_performance(10)
    SECCOL = {'XLK':'#63c6f0','XLV':'#66e39c','XLE':'#e5b45c','XLF':'#8f9bd6','XLP':'#c88a5c',
              'XLY':'#d6a8ff','XLI':'#8ad6c0','XLB':'#c0a86a','XLU':'#7fb6d8','XLRE':'#f06a6a',
              'XLC':'#a0d67f','SPY':'#e7e9f0'}
    js += (SEC_JS.replace('__SECDATES__', json.dumps(SEC.get('dates', [])))
                 .replace('__SECPATHS__', json.dumps(SEC.get('paths', {})))
                 .replace('__SECCOLS__', json.dumps(SECCOL)))
    rdates, rser = regime_history()
    js += CHART_JS.replace('__DATES__', json.dumps(rdates)).replace('__SERIES__', json.dumps(rser))
    ranked_all = sorted(DATA.items(), key=lambda kv: (-(score(kv[1]) if score(kv[1]) is not None else -1), kv[0]))
    rank_of = {t: i for i, (t, _) in enumerate(ranked_all, 1)}
    pts = sorted([dict(x=rank_of[t], y=d['weight'], t=t,
                 c=('#4ecb8a' if rank_of[t] <= 6 else '#e5b45c' if rank_of[t] <= 15 else '#f06a6a'))
                 for t, d in DATA.items() if d.get('weight')], key=lambda p: p['x'])
    js += SCAT_JS.replace('__PTS__', json.dumps(pts))
    js += (FIT_JS.replace('__FITLAB__', json.dumps([t for t, _ in fits]))
                 .replace('__FITVAL__', json.dumps([v for _, v in fits]))
                 .replace('__FITCOL__', json.dumps([bar]*len(fits))))
    pf = portfolio_regime()
    pf_txt = ' &middot; '.join(f'<b>{r.title()}</b> {v:.0f}' for r, v in
                        sorted(pf.items(), key=lambda kv: -kv[1])) if pf else 'no cover yet'
    FW = forward_run()
    if FW.get('ok') and FW.get('signals'):
        pick = 'score' if 'score' in FW['signals'] else list(FW['signals'])[0]
        P = FW['signals'][pick]
        head_fw = (f'<div class="lede" style="margin-bottom:8px">Cohorts frozen '
                   f'<b>{FW["frozen_on"]}</b> &middot; <b>{FW["obs"]}</b> observations against a '
                   f'<b>{FW["floor"]}</b>-day floor. Top quintile minus bottom, equal-weighted. '
                    f'{FW.get("n_tests", 4)} signals are tested, so the threshold is Bonferroni-adjusted to '
                    f'|t| &ge; {FW.get("z_crit", 2.50):.2f}.</div>')
        srows = ''.join(
            f'<tr><td class="tk">{k}</td>'
            f'<td class="{cls(v["spread_pct"],0.0001,-0.0001)}">{v["spread_pct"]:+.1f}%</td>'
            f'<td class="{cls(v.get("annualised_pct"),0.0001,-0.0001)}">'
            f'{(("%+.1f%%" % v["annualised_pct"]) if v.get("annualised_pct") is not None else "&mdash;")}</td>'
            f'<td class="mono">{v["daily_bp"]:+.2f}bp</td><td class="mono">{v["t"]:+.2f}</td>'
            f'<td class="mono">{(str(v["years_needed"]) + "y") if v["years_needed"] else "&mdash;"}</td>'
            f'<td><span class="pill {"v-buy" if v["verdict"]=="RANKS" else "v-sell" if v["verdict"]=="RANKS INVERSELY" else "v-hold"}">{v["verdict"]}</span></td></tr>'
            for k, v in FW['signals'].items())

        mrows = ''.join(
            f'<tr><td class="mono">{m["period"]}</td><td class="mono">{m["top"]:+.2f}%</td>'
            f'<td class="mono">{m["bot"]:+.2f}%</td>'
            f'<td class="{cls(m["spread"],0.0001,-0.0001)}">{m["spread"]:+.2f}%</td>'
            f'<td class="mono" style="color:#5e6373">{m["obs"]}</td></tr>'
            for m in reversed(P.get('monthly', [])))
        yrows = ''.join(
            f'<tr><td class="mono"><b>{y["period"]}</b></td><td class="mono">{y["top"]:+.2f}%</td>'
            f'<td class="mono">{y["bot"]:+.2f}%</td>'
            f'<td class="{cls(y["spread"],0.0001,-0.0001)}"><b>{y["spread"]:+.2f}%</b></td>'
            f'<td class="mono" style="color:#5e6373">{y["obs"]}</td></tr>'
            for y in reversed(P.get('yearly', [])))
        SB = P.get('stability')
        sb_txt = ('' if not SB else
            f'<div class="lede" style="margin-top:10px;margin-bottom:0"><b>Stability {SB["rho"]:.3f}</b> '
            f'&mdash; {SB["pct_positive"]:.0f}% of {SB["months"]} months positive, dispersion '
            f'{SB["dispersion"]:.2f}pp, worst month {SB["worst"]:+.2f}%. Reads as '
            f'<b>{SB["reads"]}</b>. This is the paper&rsquo;s regime gate applied to the monthly '
            f'spreads: a result that comes from one lucky month scores low here even when the '
            f'cumulative number looks strong.</div>')
        per = ('' if not (mrows or yrows) else
            f'<h2 style="margin-top:16px">Month by month &mdash; <span class="mono">{pick}</span></h2>'
            '<div class="lede" style="margin-bottom:8px">Reading twelve monthly cells is twelve '
            'more looks at the same data. <b>One good month is noise.</b> Read the stability line '
            'under the table, not the best row in it.</div>'
            '<table><thead><tr><th>Period</th><th>Top</th><th>Bottom</th><th>Spread</th>'
            f'<th>Days</th></tr></thead><tbody>{yrows}{mrows}</tbody></table>{sb_txt}')

        fw_box = ('<div class="box"><h2>Does the scorecard actually rank?</h2>' + head_fw +
                  '<table><thead><tr><th>Signal</th><th>Cumulative</th><th>Annualised</th>'
                  '<th>Per day</th><th>t</th><th>Years to sig.</th><th>Verdict</th></tr></thead>'
                  f'<tbody>{srows}</tbody></table>' + per +
                  '<div class="lede" style="font-size:12px;margin-top:10px">Forward test, not a '
                  'backtest. Cohorts were fixed before any of these prices existed. '
                  '<b>Re-freezing them after reading this destroys the test.</b></div></div>')
    else:
        fw_box = ('<div class="box"><h2>Does the scorecard actually rank?</h2>'
                  f'<div class="lede">{FW.get("note","")} &mdash; cohorts freeze on the first run '
                  'and the test accumulates from there.</div></div>')

    if M.get('ok'):
        legs = ''.join(f'<div class="mono" style="font-size:10px">&middot; {x}</div>' for x in M['recession_legs'])
        det = ' &middot; '.join(f'{k} {v:+.1f}%' for k, v in M['detail'].items() if v is not None)
        macro_box = (
          f'<div class="box" style="border-color:#4a3566;background:#15111d">'
          f'<h2>Regime now: <span class="pill {REG_CSS.get(cur_reg,"empty")}">{cur_reg}</span></h2>'
          f'<div class="lede" style="margin-bottom:8px">Read off market data, not opinion. '
          f'<b>Growth impulse {M["growth"]:+.1f}%</b> (S&amp;P + copper, 6-month) &middot; '
          f'<b>Inflation impulse {M["inflation"]:+.1f}%</b> (oil + 10-year, 6-month).<br>'
          f'<span class="mono" style="font-size:10px">{det}</span></div>'
          f'<div class="lede" style="margin-bottom:6px">'
           f'VIX <b>{fmt(M.get("vix"), ".1f")} &mdash; {M.get("vix_state") or "unavailable"}</b>'
          + (f' &middot; tranche rule fires above 25' if (M["vix"] or 0) > 25 else '')
          + (f' &middot; breadth {M["breadth"]}' if M.get('breadth') else '')
          + f' &middot; recession score <b>{M["recession_score"]}/100</b></div>{legs}'
          + (lambda H, T: '' if not (H and T) else
             f'<div class="lede" style="margin-top:12px;margin-bottom:6px">Path over the last '
             f'twelve months, each dot the same statistic read at an earlier date. Growth impulse '
             f'moved <b>{H["dg"]:+.1f}pp</b> and inflation <b>{H["di"]:+.1f}pp</b> across the last '
             f'two readings &mdash; ' +
             (f'<b>{H["note"]}</b> inside {H["toward"]}.' if H['note'] in ('holding','stalled')
              else f'<b>crossing toward {H["toward"]}</b>.') +
             ' The path is data. Extending it is not.</div>'
             '<div style="height:340px"><canvas id="quadChart"></canvas></div>'
            )(M.get('heading'), M.get('trail'))
          + '</div>')
    else:
        macro_box = f'<div class="box"><h2>Regime now</h2><div class="lede">unavailable: {M.get("note","")}</div></div>'

    tw  = sum(d['weight'] for d in DATA.values() if d.get('weight')) or 1
    wsc = sum(d['weight']*(score(d) or 0) for d in DATA.values() if d.get('weight'))/tw
    cw  = sum(d['weight'] for d in DATA.values() if d.get('weight') and cover(d))
    wcv = (sum(d['weight']*cover(d)*100 for d in DATA.values() if d.get('weight') and cover(d))/cw) if cw else None
    wrk = sum(d['weight']*rank_of[t] for t, d in DATA.items() if d.get('weight'))/tw
    eqr = (sum(rank_of[t] for t, d in DATA.items() if d.get('weight'))/len(pts)) if pts else 0
    uns = [(t, d['weight']) for t, d in DATA.items() if d.get('weight') and score(d) is None]
    unscored = sum(w for _, w in uns)
    unscored_names = ', '.join(f'{t} {w:.1f}%' for t, w in sorted(uns, key=lambda kv: -kv[1]))
    port_box = ('<div class="box" style="border-color:#1d5433;background:#0e1712">'
        '<h2>Your book as one line</h2>'
        f'<div class="lede" style="margin-bottom:8px">{len(pts)} positions &middot; weighted score '
        f'<b>{wsc:.2f}</b> &middot; weighted cover <b>{("%.0f%%" % wcv) if wcv else "n/a"}</b> &middot; '
        f'<b>weight-weighted rank {wrk:.1f}</b> against <b>{eqr:.1f}</b> if held equally.</div>'
        + (f'<div class="lede" style="margin-bottom:8px;color:#e5b45c"><b>{unscored:.1f}% of the '
           f'book carries no score</b> &mdash; {unscored_names}. The weighted figures above exclude it, '
           f'so they describe {100-unscored:.1f}% of what you own.</div>' if unscored else '')
        + '<div class="lede" style="margin-bottom:8px">Every dot should sit on a line falling left to '
        'right: best ideas biggest. <b>Dots high and to the right are the problem</b> &mdash; size with no '
        'rank to justify it.</div>'
        '<div style="height:280px"><canvas id="rwChart"></canvas></div></div>')

    fit_box = ('<div class="box"><h2>Best fit for the regime we are actually in</h2>'
               f'<div class="lede" style="margin-bottom:8px">Each row scored against <b>{cur_reg or "&mdash;"}</b>, '
               'not against the regime it happens to like best. This is what makes the regime column '
               'actionable rather than descriptive.</div>'
               '<div style="height:330px"><canvas id="fitChart"></canvas></div></div>') if cur_reg else ''

    if cur_reg:
        rb = regime_book(cur_reg, 30)
        rb_rows = ''.join(
            f'<tr><td class="rk">{i}</td><td class="tk">{t}</td><td class="se">{d.get("sector","")}</td>'
            f'<td class="mono"><b>{f:.1f}</b></td><td class="mono">{fmt(score(d),".2f")}</td>'
            f'<td class="mono">{fmt(None if cover(d) is None else cover(d)*100,".0f")}%</td>'
            f'<td class="mono">{valuation_read(d)}</td></tr>'
            for i, (t, d, f) in enumerate(rb, 1))
        regime_book_box = ('<div class="box"><h2>30-name regime book</h2>'
            f'<div class="lede">Ranked <b>only</b> by {cur_reg} fit. Score, risk, valuation and existing portfolio weight '
            'are shown only as diagnostics and never break a fit tie. Ticker alphabetically breaks exact ties.</div>'
            '<div class="tw"><table><thead><tr><th>#</th><th>Ticker</th><th>Sector</th><th>Fit</th>'
            '<th>Score</th><th>NGV cover</th><th>Valuation</th></tr></thead><tbody>' + rb_rows + '</tbody></table></div></div>')
    else:
        regime_book_box = ''

    if SEC.get('rows'):
        rr = sorted(SEC['rows'].values(), key=lambda x: -(x.get('10y') if x.get('10y') is not None else -99))
        srows = ''
        for x in rr:
            eng = SECTOR_TO_ENGINE.get(x['sym'])
            aff = AFF['REFLATION'].get(eng) if eng else None
            ac = 'pos' if (aff or 0) > 0 else ('neg' if (aff or 0) < 0 else 'na')
            spy = x['sym'] == 'SPY'
            srows += ('<tr%s>' % (' style="background:#141826"' if spy else '')
                + f'<td class="tk">{x["sym"]}<div class="se">{x["name"]}</div></td>'
                + ''.join(f'<td class="pr {cls(x.get(w),8,0)}">'
                          f'{("%+.1f%%" % x[w]) if x.get(w) is not None else "&mdash;"}</td>'
                          for w in ('1y','3y','5y','10y'))
                + f'<td class="pr {ac}">{("%+d" % aff) if aff is not None else "&mdash;"}</td></tr>')
        sec_box = ('<div class="box"><h2>Eleven sectors, ten years</h2>'
          '<div class="lede" style="margin-bottom:10px">Annualised total return. The right-hand '
          'column is the same sector&rsquo;s <b>reflation affinity</b> from the engine&rsquo;s own '
          'table. <b>Read them together</b>: a decade where technology compounds and energy does '
          'not is a decade of falling discount rates, and a reflation tilt is a bet that the '
          'ordering inverts. Whether that is contrarian or late is the only question the table '
          'answers.</div>'
          '<div class="tw"><table><thead><tr><th>Sector</th><th>1y</th><th>3y</th><th>5y</th>'
          '<th>10y</th><th>Refl</th></tr></thead><tbody>' + srows + '</tbody></table></div>'
          '<div style="height:300px;margin-top:14px"><canvas id="secChart"></canvas></div></div>')
    else:
        sec_box = ''

    chart_box = ('<div class="box"><h2>Where the book sits on the growth / inflation grid</h2>'
                 '<div class="lede" style="margin-bottom:8px">Position-weighted, not a cross-sectional '
                 'average &mdash; averaging all 51 rows is dominated by the sector mix and barely moves. '
                 'Today: ' + pf_txt + '</div>'
                 '<div style="height:220px"><canvas id="regimeChart"></canvas></div>'
                 '<div id="chartNote" class="lede" style="font-size:12px;margin-top:6px"></div></div>')
    head = ('<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>InvestorAce &middot; Master Scoreboard</title>'
            '<link rel="preconnect" href="https://fonts.googleapis.com">'
            '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
            'family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap">'
            '<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>'
            '<style>' + CSS + '</style></head><body>')
    hdr = (f'<div class="kicker">InvestorAce &middot; Live &middot; {stamp}</div>'
           f'<h1>Master Scoreboard</h1>'
           f'<div class="lede">{len(DATA)} tickers &middot; <b>{withngv}</b> with NGV &middot; <b>{sum(1 for d in DATA.values() if epv(d) is not None)}</b> with EPV &middot; <b>{priced}</b> priced this run &middot; '
           f'<b>{na}</b> NGV-N/A. <b>NGV and EPV are separate valuation lenses.</b> The gap is diagnostic and is never fed into score or regime fit.</div>')
    issue_box = ''
    if issues:
        li = ''.join(f'<div class="mono">{t}: {v}</div>' for t,v in sorted(issues.items()))
        issue_box = f'<div class="box"><h2 style="color:#f06a6a">Price issues this run ({len(issues)})</h2>{li}</div>'
    adder = ('<div class="box"><h2>Add a ticker</h2>'
             '<div class="lede" style="margin-bottom:10px">Yahoo can supply the mechanical half &mdash; price, shares, '
             'cash flow, currency. It cannot supply subscores, the delivering metric or the clock classification. '
             'This opens a pre-filled GitHub issue; the workflow does the rest and comments back with the result.</div>'
             '<input id="newTicker" placeholder="e.g. ASML.AS" style="width:220px">&nbsp;'
             '<button id="addTickerButton" type="button">Add via GitHub</button>&nbsp;'
             '<a id="gh" target="_blank" rel="noopener" style="display:none;background:#1d5433;color:#4ecb8a;border:1px solid #2a7a4a;border-radius:6px;padding:8px 14px;font-weight:700;text-decoration:none"></a>'
             '<textarea id="out" style="width:100%;height:150px;margin-top:10px" readonly></textarea></div>')
    tbl = ('<div class="tw"><table><thead><tr><th>#</th><th>Ticker</th><th>Sector</th><th>Legacy Score</th><th>Band</th><th>Risk</th>'
           '<th>Verdict</th><th>Cover</th><th>Cushion</th><th>Entry gap</th><th>Clock</th><th>Insider</th><th>Mom 12-1</th><th>Regime</th>'
           '<th>NGV</th><th>EPV</th><th>EPV vs NGV</th><th>Entry@60%</th><th>Price</th><th>Fetched</th><th>Built</th></tr></thead><tbody>'
           + '\n'.join(rows) + '</tbody></table></div>')
    zin = ('<div style="margin-top:18px;text-align:right">'
           '<input id="zielIn" type="password" autocomplete="off" placeholder="&#8942;" '
           'style="width:96px;text-align:center;opacity:.55" aria-label="">'
           '&nbsp;<button id="zielBtn" type="button" '
           'style="padding:6px 11px;font-size:11px;opacity:.55">&#8594;</button></div>')

    foot = (f'<div class="foot">Snapshot written to history/. NGV capitalises the row FCF; EPV normalises operating earning power and subtracts net debt. '
            f'Neither valuation gap nor EPV confidence changes Score or Regime Fit. Regime model {REGIME_MODEL_VERSION}. '
            f'Negative cushion forces DO NOT ADD at every band. Last pull {stamp}.<br>Not financial advice</div>')
    import base64
    ziel_payload = base64.b64encode((port_box + chart_box).encode('utf-8')).decode('ascii')
    js_z = ZIEL_JS.replace('__ZIELPAYLOAD__', ziel_payload)
    gate = '<div id="zielBox" data-open="0"></div>'
    # [FROM V2] atomic write. A build that dies mid-write used to leave
    # index.html truncated and the live site broken until the next cron run.
    proposal = portfolio_proposal(cur_reg) if cur_reg in REGIMES else None
    html = (head + hdr + macro_box + framework_panel(DATA, W, M, proposal) + sec_box + fw_box + gate + zin + fit_box
            + regime_book_box + issue_box + adder + tbl + foot
            + '<script>' + js + js_z + '</script></body></html>')
    if write:
        atomic_text('index.html', html)
    return html

if __name__ == '__main__':
    published = run_build()
    day = published['day']
    bad = {t: d['price_note'] for t,d in DATA.items() if d.get('price_note') and not d.get('na')}
    print(f'{len(DATA)} tickers &middot; snapshot history/{day}.json &middot; index.html written')
    if bad: print('PRICE ISSUES:', json.dumps(bad, indent=1), file=sys.stderr)
