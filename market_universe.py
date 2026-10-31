#!/usr/bin/env python3
"""Market-wide idea scan: every US-GAAP filer listed on NYSE or Nasdaq.

The existing scanner ranks only the tickers already in engine.py. This module
looks at the whole US listing and proposes companies that are NOT yet there.

Two stages keep the load polite (SEC asks for at most 10 requests/second):

1. SEC XBRL frames. One request per concept and period returns that concept for
   every filer, so ~60 requests cover ~5,000 companies. Revenue >= 1 bn USD,
   no known nonpositive operating profit/FCF, and a recent dated Yahoo daily
   close give a supported-contribution subtotal. Missing inputs remain open.
2. Down the pre-score ranking, SEC submissions give the SIC code (-> sector).
   Banks, insurers and REITs are skipped until the shortlist is full, because
   FCF and net debt do not describe them. 20-F/40-F filers are flagged (ADS).
3. For the shortlist only: SEC companyfacts (every reported fact). Trailing
   twelve months are rebuilt per company as last fiscal year + current
   year-to-date - prior year-to-date, all on identical reporting windows.

The SEC agent comes from the SEC_USER_AGENT secret and must carry a real
contact address; without one the scan stops before the first request.

The score reuses autoscore's bands and the engine's eight weights (Growth 15,
Profitability 20, Cash Generation 15, Balance Sheet 15, Valuation 10,
Priced-in 15, Shareholder Returns 5, Dilution 5). It is a mechanical screening
draft: revenue growth is a proxy and the flat 8 % discount rate is a scenario.
Producer valuation needs explicitly sourced normalized FCF. Missing categories
have no composite score. It never enters engine.py, never changes an InvestorAce score and
never places a trade. A candidate becomes a model row only through add-ticker.

Run:   SEC_USER_AGENT="InvestorAce Name name@domain" python market_universe.py --output market-scan
Test:  python -m unittest test_market_universe -v      (offline)
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

VERSION = 'market-scan-v1'
SCORING_VERSION = 'market-screen-evidence-gates-v2'
SEC_DATA = 'https://data.sec.gov'
TICKERS_URL = 'https://www.sec.gov/files/company_tickers_exchange.json'
# SEC fair access needs a declared agent with a reachable contact address. On
# 2026-10-18 every agent with a users.noreply.github.com address got 403 from
# GitHub runners while a plain company-style agent got 200, so there is no
# default: the repository secret SEC_USER_AGENT must name the owner.
AGENT_HELP = ('Lege in GitHub unter Settings → Secrets and variables → Actions das Secret '
              'SEC_USER_AGENT an, z. B. "InvestorAce Vorname Nachname name@beispiel.de". '
              'Die SEC verlangt eine echte Kontaktadresse; noreply-Adressen lehnt sie mit 403 ab.')
EXCHANGES = ('NYSE', 'Nasdaq')
MIN_REVENUE = 1e9
SHORTLIST = 300
KEEP = 150
DISCOUNT = 0.08            # autoscore's draft rate; a real WACC comes after add-ticker
REQUESTS_PER_SECOND = 5    # half of the SEC fair-access ceiling
MAX_SCAN_AGE_DAYS = 14     # older scans are shown as stale on the page

# Same eight categories and weights as engine.W, kept here so the page builder
# never has to import engine.py (and yfinance) just to read this file.
WEIGHTS = {'g': .15, 'p': .20, 'c': .15, 'b': .15, 'v': .10, 'pr': .15, 'r': .05, 'd': .05}
LABELS = {'g': 'Growth', 'p': 'Profitability', 'c': 'Cash Generation', 'b': 'Balance Sheet',
          'v': 'Valuation', 'pr': 'Priced-In Expectations', 'r': 'Shareholder Returns',
          'd': 'Dilution'}
BANDS = [(3.5, 'Sell'), (5.5, 'Hold negativ'), (7, 'Hold positiv'), (8.5, 'Buy'), (11, 'Strong Buy')]

# us-gaap tags, most specific first. Companies switch tags over the years.
REVENUE = ('Revenues', 'RevenueFromContractWithCustomerExcludingAssessedTax',
           'RevenueFromContractWithCustomerIncludingAssessedTax', 'SalesRevenueNet')
OPERATING_INCOME = ('OperatingIncomeLoss',)
PRETAX_INCOME = ('IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest',
                 'IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments')
OPERATING_CASH = ('NetCashProvidedByUsedInOperatingActivities',
                  'NetCashProvidedByUsedInOperatingActivitiesContinuingOperations')
# Capex: the LARGEST tagged figure per window is used, so a small corporate PP&E
# line never stands in for an oil producer's well spending (first live scan:
# EOG, COP, FANG and others reported none of the first two tags).
CAPEX = ('PaymentsToAcquirePropertyPlantAndEquipment', 'PaymentsToAcquireProductiveAssets',
         'PaymentsToAcquireOilAndGasPropertyAndEquipment', 'PaymentsToAcquireOilAndGasProperty',
         'PaymentsToExploreAndDevelopOilAndGasProperties', 'PaymentsToAcquireEquipmentOnLease',
         'PaymentsToAcquireOtherPropertyPlantAndEquipment')
DEPRECIATION = ('DepreciationDepletionAndAmortization', 'DepreciationAndAmortization',
                'DepreciationAmortizationAndAccretionNet', 'Depreciation')
DIVIDENDS = ('PaymentsOfDividends', 'PaymentsOfDividendsCommonStock')
DILUTED_SHARES = ('WeightedAverageNumberOfDilutedSharesOutstanding',)
DEBT_TOTAL = ('LongTermDebt',)                      # includes current maturities
DEBT_NONCURRENT = ('LongTermDebtNoncurrent', 'LongTermDebtAndCapitalLeaseObligations',
                   'LongTermNotesPayable')
DEBT_CURRENT = ('LongTermDebtCurrent', 'DebtCurrent')
DEBT_SHORT = ('ShortTermBorrowings', 'CommercialPaper')
CASH = ('CashAndCashEquivalentsAtCarryingValue',
        'CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents')
SECURITIES = ('ShortTermInvestments', 'MarketableSecuritiesCurrent',
              'AvailableForSaleSecuritiesDebtSecuritiesCurrent')

FLAG_TEXT = {
    'CAPEX_NOT_TAGGED': 'Keine Investitionsausgaben getaggt; ersatzweise die Abschreibungen als '
                        'Erhaltungsinvestition abgezogen (prüfen).',
    'CAPEX_AND_DA_MISSING': 'Weder Investitionen noch Abschreibungen getaggt; FCF und betroffene Kategorien ausgesetzt.',
    'SHARES_SCALE_FIXED': 'Verwässerte Aktienzahl in den XBRL-Daten um Faktor 1.000/1.000.000 falsch skaliert; '
                          'Deckblattangabe verwendet.',
    'GROWTH_OUTLIER': 'Umsatzsprung über +100 % oder unter −50 %: Übernahme, Abspaltung, aufgegebene '
                      'Geschäftsbereiche oder echter Boom? Wachstumskategorie prüfen.',
    'SHARES_JUMP': 'Aktienzahl um mehr als 25 % verändert (Übernahme, Spin-off oder Split prüfen).',
    'DEBT_NOT_TAGGED': 'Keine vollständigen Finanzschulden getaggt; Bilanzkategorie ausgesetzt.',
    'DEBT_PARTIAL': 'Nur Teile der Finanzschulden getaggt; kein vollständiger Schuldenstand und keine Bilanzwertung.',
    'CASH_NOT_TAGGED': 'Keine Zahlungsmittel getaggt; Nettoverschuldung und Bilanzwertung ausgesetzt.',
    'NO_DEPRECIATION': 'Keine Abschreibungen getaggt; EBITDA und Bilanzkategorie nicht berechenbar.',
    'OPERATING_INCOME_PROXY': 'Kein operatives Ergebnis getaggt; Vorsteuerergebnis als Ersatz.',
    'GROWTH_DEFAULT': 'Kein Vorjahreswert; Wachstumskategorie ausgesetzt.',
    'BALANCE_DEFAULT': 'Nettoverschuldung/EBITDA nicht berechenbar; Bilanzkategorie ausgesetzt.',
    'FISCAL_YEAR_ONLY': 'Kein passendes Quartals-YTD; Kennzahlen auf Basis des letzten Geschäftsjahres.',
    'FRAMES_ONLY': 'Companyfacts nicht nutzbar; Werte aus den SEC-Jahresframes.',
    'SHARES_DILUTED_AVG': 'Aktienzahl = verwässerter Durchschnitt (keine Deckblattangabe nutzbar).',
    'NO_PRICE': 'Kein datierter Schlusskurs; Bewertung und Rang ausgesetzt.',
    'CLASSIFICATION_MISSING': 'Keine belastbare SIC-Klassifikation; Bewertungs- und Gesamtscore ausgesetzt.',
    'COMMODITY_MIDCYCLE_REQUIRED': 'Rohstoffproduzent: Bewertung erst mit belegtem normalisiertem Mid-Cycle-FCF.',
    'DENOMINATOR_UNVERIFIED': 'Aktien-/ADS-Basis nicht datiert übergeleitet; Bewertung und Aktionärsrendite ausgesetzt.',
    'DILUTION_MISSING': 'Kein vergleichbarer Vorjahres-Aktienstand; Verwässerung und Rückkaufrendite ausgesetzt.',
    'DIVIDENDS_NOT_TAGGED': 'Keine belegte Dividendenzahlung; Aktionärsrendite unvollständig.',
    'DIVIDENDS_INVALID': 'Negative Dividendenzahlung nicht als Ausschüttung verwendbar; Quellenprüfung erforderlich.',
    'FCF_INCOMPLETE': 'FCF nicht vollständig belegt; betroffene Kategorien bleiben offen.',
    'OPERATING_INCOME_MISSING': 'Kein operatives Ergebnis verfügbar; betroffene Kategorien bleiben offen.',
    'REPORTED_FCF_SCENARIO': 'Gemeldeter FCF zum Szenario-Diskontsatz; kein verifizierter nachhaltiger Fair Value.',
    'NORMALIZED_FCF_VERIFIED': 'Normalisierter FCF mit Quellenstatus VERIFIED; Diskontsatz bleibt eine Annahme.',
    'FOREIGN_FILER': 'Auslandsemittent (Jahresbericht 20-F/40-F): Die SEC-Aktienzahl zählt Stammaktien, '
                     'gehandelt werden oft ADS in anderem Verhältnis. Marktwert und FCF-Rendite prüfen.',
}

SIC_SECTORS = (
    # specific ranges first; first match wins
    (1311, 1311, 'Energy'), (1381, 1389, 'Energy'), (1220, 1241, 'Energy'), (2911, 2999, 'Energy'),
    (1000, 1099, 'Materials'), (1400, 1499, 'Materials'), (1500, 1799, 'Industrials'),
    (2000, 2199, 'Staples'), (2200, 2399, 'Apparel'), (2400, 2499, 'Materials'),
    (2500, 2599, 'Consumer Cyclical'), (2600, 2699, 'Materials'), (2700, 2799, 'Media'),
    (2833, 2834, 'Pharma'), (2835, 2835, 'MedTech'), (2836, 2836, 'Biotech'),
    (2840, 2844, 'Staples'), (2800, 2899, 'Materials'), (3021, 3021, 'Apparel'),   # rubber footwear
    (3000, 3099, 'Materials'),
    (3100, 3199, 'Apparel'), (3200, 3399, 'Materials'), (3400, 3499, 'Industrials'),
    (3570, 3579, 'Technology'), (3500, 3599, 'Industrials'), (3674, 3674, 'Semis'),
    (3661, 3679, 'Technology'), (3630, 3639, 'Consumer Cyclical'), (3651, 3652, 'Consumer Cyclical'),
    (3600, 3699, 'Industrials'), (3711, 3716, 'Automotive'), (3751, 3751, 'Automotive'),
    (3720, 3729, 'Aerospace'), (3760, 3769, 'Aerospace'), (3700, 3799, 'Industrials'),
    (3812, 3812, 'Aerospace'), (3841, 3851, 'MedTech'), (3800, 3899, 'Industrials'),
    (3911, 3915, 'Luxury'), (3900, 3999, 'Consumer Cyclical'), (4000, 4799, 'Industrials'),
    (4812, 4813, 'Communication Services'), (4830, 4841, 'Media'),
    (4800, 4899, 'Communication Services'), (4922, 4925, 'Midstream'),
    (4950, 4959, 'Industrials'), (4900, 4999, 'Utilities'), (5122, 5122, 'Healthcare'),
    (5140, 5149, 'Staples'), (5000, 5199, 'Industrials'), (5400, 5499, 'Staples'),
    (5912, 5912, 'Staples'), (5812, 5813, 'Restaurant'), (5600, 5699, 'Apparel'),
    (5944, 5944, 'Luxury'), (5200, 5999, 'Consumer Cyclical'), (7370, 7373, 'Software'),
    (7374, 7374, 'Info Svcs'), (7375, 7379, 'Software'), (7320, 7323, 'Info Svcs'),
    (7310, 7319, 'Media'), (7810, 7841, 'Media'), (7011, 7011, 'Consumer Cyclical'),
    (7900, 7999, 'Consumer Cyclical'), (7000, 7999, 'Services'), (8000, 8099, 'Healthcare'),
    (8731, 8734, 'Healthcare'), (8000, 8999, 'Services'),
)
FINANCIAL_SIC = (6000, 6799)   # banks, insurers (incl. health insurers), REITs, holding cos.

# autoscore's bands, duplicated only as a fallback for the page builder; the
# scan itself imports autoscore so a band change there cannot drift silently.
_FALLBACK_BANDS = dict(
    GROWTH=[(0, 2.0), (5, 4.0), (10, 5.5), (20, 7.0), (40, 8.5), (1e9, 9.5)],
    PROFIT=[(0, 2.0), (10, 4.0), (20, 6.0), (30, 7.5), (45, 9.0), (1e9, 9.5)],
    CASHGEN=[(0, 1.5), (5, 4.0), (12, 6.0), (20, 7.5), (30, 9.0), (1e9, 9.5)],
    BALANCE=[(0, 9.5), (1, 8.0), (2, 7.0), (3, 6.0), (4, 4.5), (5, 3.0), (1e9, 1.5)],
    VALUE=[(1, 1.5), (2, 3.0), (3, 4.5), (4.5, 6.0), (7, 7.5), (1e9, 9.0)],
    RETURNS=[(0.01, 1.0), (1, 4.0), (2.5, 6.0), (4, 7.5), (1e9, 9.0)],
    DILUTION=[(-4, 9.5), (-1, 8.5), (0.5, 7.0), (2, 5.5), (5, 3.5), (10, 2.0), (1e9, 0.5)],
)
_COVER = [(15, 1.5), (25, 2.5), (35, 3.0), (45, 4.5), (60, 5.5), (75, 7.0), (90, 8.0), (100, 9.0), (1e9, 9.5)]


def _bands():
    """autoscore owns the band tables; import them when yfinance is installed."""
    try:
        import autoscore
        return {k: getattr(autoscore, k) for k in _FALLBACK_BANDS}
    except Exception:   # pragma: no cover - only without yfinance
        return dict(_FALLBACK_BANDS)


# ---------------------------------------------------------------- helpers
def _num(value):
    if isinstance(value, bool):
        return None
    try:
        value = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return value if math.isfinite(value) else None


def _date(value):
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def _band(value, table, default=None):
    value = _num(value)
    if value is None:
        return default
    for ceiling, score in table:
        if value < ceiling:
            return score
    return table[-1][1]


def priced_in(cover_pct):
    """Engine/autoscore mapping of NGV cover to the priced-in category."""
    if cover_pct is None:
        return None
    return round(_band(cover_pct, _COVER), 1)


def model_band(score):
    score = _num(score)
    if score is None or not 0 <= score <= 10:
        return None
    return next(label for ceiling, label in BANDS if score < ceiling)


def sector_from_sic(sic):
    sic = _num(sic)
    if sic is None:
        return 'Unbekannt'
    sic = int(sic)
    if FINANCIAL_SIC[0] <= sic <= FINANCIAL_SIC[1]:
        return 'Financials'
    return next((label for lo, hi, label in SIC_SECTORS if lo <= sic <= hi), 'Unbekannt')


def is_financial(sic):
    sic = _num(sic)
    return sic is not None and FINANCIAL_SIC[0] <= int(sic) <= FINANCIAL_SIC[1]


def is_commodity_producer(sic):
    """Raw mining, upstream/refining and fertilizer, rather than all Materials."""
    sic = _num(sic)
    return sic is not None and any(lo <= int(sic) <= hi for lo, hi in (
        (1000, 1299), (1300, 1379), (1400, 1499), (2910, 2919), (2870, 2879)))


def yahoo_symbol(ticker):
    return ticker.replace('.', '-').upper()


def recent_quarter_ends(today, lag_days=45, count=2):
    """Latest calendar quarter ends with enough time for 10-Q filings."""
    ends, year, month = [], today.year, today.month
    while len(ends) < count:
        quarter_month = ((month - 1) // 3) * 3          # 0,3,6,9 -> previous quarter end
        if quarter_month == 0:
            year, month = year - 1, 12
        else:
            month = quarter_month
        end = date(year, month, 31 if month in (3, 12) else 30)
        if (today - end).days >= lag_days:
            ends.append(end)
    return ends


def quarter_label(end):
    return f'CY{end.year}Q{(end.month - 1) // 3 + 1}I'


# ---------------------------------------------------------------- SEC client
_EMAIL = re.compile(r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)+')
_PLACEHOLDERS = ('noreply', 'no-reply', 'donotreply', 'do-not-reply', '@example.', '@beispiel.',
                 '@samplecompany.')


def sec_agent(value):
    """The declared SEC agent: a real contact address, never a placeholder or noreply."""
    agent = ' '.join(str(value or '').split())
    if not agent:
        raise RuntimeError('SEC_USER_AGENT ist in diesem Lauf leer: Das Secret fehlt oder ist kein '
                           'Repository-Secret unter "Actions" (Environment-, Codespaces- und '
                           'Dependabot-Secrets sieht dieser Job nicht). ' + AGENT_HELP)
    match = _EMAIL.search(agent)
    if not match:
        # Length and '@' count only: the value itself never reaches the public log.
        raise RuntimeError(f'SEC_USER_AGENT ist gesetzt ({len(agent)} Zeichen, {agent.count("@")}× "@"), '
                           'enthält aber keine gültige E-Mail-Adresse. ' + AGENT_HELP)
    address = match.group(0).lower()
    if any(marker in address for marker in _PLACEHOLDERS):
        raise RuntimeError('SEC_USER_AGENT nutzt eine Platzhalter- oder noreply-Adresse. ' + AGENT_HELP)
    return agent


class SecClient:
    """Small SEC client: declared agent, rate limit, bounded retries."""

    def __init__(self, agent, rate=REQUESTS_PER_SECOND, session=None, log=print):
        import requests
        self.session = session or requests.Session()
        self.session.headers.update({'User-Agent': sec_agent(agent),
                                     'Accept-Encoding': 'gzip, deflate'})
        self.interval = 1.0 / rate
        self.last = 0.0
        self.calls = 0
        self.failures = 0
        self.log = log

    def get_json(self, url, tries=4):
        response = self._get(url, tries)
        return response.json() if response is not None else None

    def get_text(self, url, tries=4):
        response = self._get(url, tries)
        return response.text if response is not None else None

    def _get(self, url, tries=4):
        for attempt in range(tries):
            wait = self.interval - (time.monotonic() - self.last)
            if wait > 0:
                time.sleep(wait)
            self.last = time.monotonic()
            self.calls += 1
            try:
                response = self.session.get(url, timeout=60)
            except Exception as exc:   # network errors are retried
                status, error = None, exc
            else:
                status, error = response.status_code, None
                if status == 200:
                    return response
                if status == 404:
                    return None
                if status == 403:
                    # SEC answers 403 for a rejected agent or a rate breach;
                    # retrying only extends the block. The agent is never logged.
                    title = re.search(r'<title>(.*?)</title>', str(getattr(response, 'text', '')), re.S)
                    reason = ' '.join(title.group(1).split()) if title else 'ohne Begründung'
                    raise RuntimeError(f'SEC lehnt {url} ab (403: {reason}) nach {self.calls} Anfragen. '
                                       'Meist ist die Kontaktadresse in SEC_USER_AGENT nicht akzeptiert '
                                       'oder das Limit von 10 Anfragen/s überschritten. ' + AGENT_HELP)
            if attempt + 1 < tries:
                time.sleep(2 ** (attempt + 1))
        self.failures += 1
        self.log(f'SEC request failed ({status or type(error).__name__}): {url}')
        return None


def frame_url(tag, unit, period, taxonomy='us-gaap'):
    return f'{SEC_DATA}/api/xbrl/frames/{taxonomy}/{tag}/{unit}/{period}.json'


def submissions_url(cik):
    return f'{SEC_DATA}/submissions/CIK{int(cik):010d}.json'


def companyfacts_url(cik):
    return f'{SEC_DATA}/api/xbrl/companyfacts/CIK{int(cik):010d}.json'


def filing_url(cik, accn):
    return f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{str(accn).replace("-", "")}/'


def company_url(cik):
    return ('https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany'
            f'&CIK={int(cik):010d}&type=10-&dateb=&owner=include&count=40')


# ---------------------------------------------------------------- parsing
def parse_universe(payload, exchanges=EXCHANGES):
    """company_tickers_exchange.json -> one primary listing per CIK."""
    if not isinstance(payload, dict):
        raise ValueError('SEC ticker list unavailable')
    fields = payload.get('fields') or []
    try:
        ix = {name: fields.index(name) for name in ('cik', 'name', 'ticker', 'exchange')}
    except ValueError:
        raise ValueError('SEC ticker list has unexpected fields') from None
    seen, rows = set(), []
    for item in payload.get('data') or []:
        try:
            cik, name, ticker, exchange = (item[ix['cik']], item[ix['name']],
                                           item[ix['ticker']], item[ix['exchange']])
        except (IndexError, TypeError):
            continue
        if exchange not in exchanges or not isinstance(ticker, str) or cik in seen:
            continue
        ticker = ticker.strip().upper()
        if not re.fullmatch(r'[A-Z0-9][A-Z0-9.\-]{0,9}', ticker):
            continue
        seen.add(cik)   # the first ticker per CIK is the primary common line
        rows.append(dict(cik=int(cik), ticker=ticker, yahoo=yahoo_symbol(ticker),
                         name=str(name or ticker), exchange=exchange))
    return rows


def parse_frame(payload):
    """SEC frame -> {cik: fact}. Missing or malformed frames are empty."""
    result = {}
    if not isinstance(payload, dict):
        return result
    for item in payload.get('data') or []:
        try:
            cik, value = int(item['cik']), _num(item['val'])
        except (KeyError, TypeError, ValueError):
            continue
        if value is not None:
            result[cik] = dict(val=value, start=item.get('start'), end=item.get('end'),
                               accn=item.get('accn'))
    return result


ANNUAL_FORMS = ('10-K', '20-F', '40-F')


def parse_submission(payload):
    if not isinstance(payload, dict):
        return None
    sic = _num(payload.get('sic'))
    try:
        forms = [str(f).split('/')[0] for f in payload['filings']['recent']['form']]
    except (KeyError, TypeError):
        forms = []
    # Most recent annual report decides: a 20-F/40-F filer usually trades as ADS.
    annual = next((f for f in forms if f in ANNUAL_FORMS), None)
    return dict(sic=int(sic) if sic is not None else None,
                sic_description=str(payload.get('sicDescription') or ''),
                name=str(payload.get('name') or ''),
                fiscal_year_end=str(payload.get('fiscalYearEnd') or ''),
                tickers=[str(t).upper() for t in payload.get('tickers') or []],
                annual_form=annual)


# ---------------------------------------------------------------- stage 1: frames
def frame_plan(today):
    """Every frame stage one needs: (tag, unit, period)."""
    year = today.year
    plan = [(tag, 'USD', f'CY{y}') for tag in REVENUE for y in (year, year - 1, year - 2)]
    for tags in (OPERATING_INCOME, PRETAX_INCOME, OPERATING_CASH, CAPEX, DEPRECIATION[:2], DIVIDENDS):
        plan += [(tag, 'USD', f'CY{y}') for tag in tags for y in (year, year - 1)]
    plan += [(tag, 'shares', f'CY{y}') for tag in DILUTED_SHARES for y in (year, year - 1, year - 2)]
    for end in recent_quarter_ends(today):
        plan += [(tag, 'USD', quarter_label(end)) for tag in
                 DEBT_TOTAL + DEBT_NONCURRENT + DEBT_CURRENT + DEBT_SHORT + CASH + SECURITIES]
    return plan


def _frame_value(frames, tags, unit, period, cik):
    for tag in tags:
        fact = frames.get((tag, unit, period), {}).get(cik)
        if fact is not None:
            return fact['val']
    return None


def _max_frame_fact(frames, tags, unit, period, cik):
    facts = [frames.get((tag, unit, period), {}).get(cik) for tag in tags]
    facts = [f for f in facts if f is not None]
    return max(facts, key=lambda f: f['val']) if facts else None


def _max_frame_value(frames, tags, unit, period, cik):
    fact = _max_frame_fact(frames, tags, unit, period, cik)
    return None if fact is None else fact['val']


def net_debt_from(get):
    """Require a complete debt bridge; an absent component is not zero debt."""
    flags = []
    total = get(DEBT_TOTAL)
    current_total = get(('DebtCurrent',))
    noncurrent, long_current = get(DEBT_NONCURRENT), get(('LongTermDebtCurrent',))
    short = [x for x in (get(('ShortTermBorrowings',)), get(('CommercialPaper',))) if x is not None]
    any_debt = total is not None or noncurrent is not None or current_total is not None \
        or long_current is not None or bool(short)
    if noncurrent is not None and current_total is not None:
        total = noncurrent + current_total  # DebtCurrent already includes short borrowings.
    elif total is not None and current_total is not None:
        # LongTermDebt includes its current maturities. Without that bridge,
        # adding all DebtCurrent could count the same debt twice.
        total = total + current_total - long_current if long_current is not None else None
    elif total is not None:
        total += sum(short)
    elif noncurrent is not None and long_current is not None:
        total = noncurrent + long_current + sum(short)
    if total is None:
        flags.append('DEBT_PARTIAL' if any_debt else 'DEBT_NOT_TAGGED')
    cash = get(CASH)
    if cash is None:
        flags.append('CASH_NOT_TAGGED')
    else:
        cash += get(SECURITIES) or 0.0
    net = total - cash if total is not None and cash is not None else None
    return net, total, cash, flags


def stage_one(listing, frames, today):
    """Annual SEC frame metrics + hard filters for every listed company."""
    year = today.year
    rows = []
    for company in listing:
        cik = company['cik']
        flags = []
        latest = next((y for y in (year, year - 1) if _max_frame_value(
            frames, REVENUE, 'USD', f'CY{y}', cik) is not None), None)
        row = dict(company, flags=flags, rejected=None, basis='FY', source='frames')
        rows.append(row)
        if latest is None:
            row['rejected'] = 'NO_REVENUE'
            continue
        period = f'CY{latest}'
        revenue_fact = _max_frame_fact(frames, REVENUE, 'USD', period, cik)
        revenue = revenue_fact['val']
        revenue_prior = _max_frame_value(frames, REVENUE, 'USD', f'CY{latest - 1}', cik)
        operating = _frame_value(frames, OPERATING_INCOME, 'USD', period, cik)
        if operating is None:
            operating = _frame_value(frames, PRETAX_INCOME, 'USD', period, cik)
            if operating is not None:
                flags.append('OPERATING_INCOME_PROXY')
        cash_flow = _frame_value(frames, OPERATING_CASH, 'USD', period, cik)
        depreciation = _frame_value(frames, DEPRECIATION[:2], 'USD', period, cik)
        capex = _max_frame_value(frames, CAPEX, 'USD', period, cik)
        capex_basis = 'REPORTED'
        if capex is None:
            capex = abs(depreciation) if depreciation is not None else None
            capex_basis = 'DEPRECIATION_PROXY' if depreciation is not None else None
            flags.append('CAPEX_NOT_TAGGED' if depreciation is not None else 'CAPEX_AND_DA_MISSING')
        dividends = _frame_value(frames, DIVIDENDS, 'USD', period, cik)
        if dividends is None:
            flags.append('DIVIDENDS_NOT_TAGGED')
        shares = _frame_value(frames, DILUTED_SHARES, 'shares', period, cik)
        shares_prior = _frame_value(frames, DILUTED_SHARES, 'shares', f'CY{latest - 1}', cik)
        balance = None
        for end in recent_quarter_ends(today):
            label = quarter_label(end)
            if _frame_value(frames, CASH, 'USD', label, cik) is not None:
                balance = (label, end)
                break
        if balance:
            net_debt, debt, cash, debt_flags = net_debt_from(
                lambda tags: _frame_value(frames, tags, 'USD', balance[0], cik))
            flags.extend(debt_flags)
        else:
            net_debt = debt = cash = None
        row.update(period_label=period, accns=[revenue_fact['accn']] if revenue_fact.get('accn') else [],
                   period_start=revenue_fact.get('start'),
                   period_end=revenue_fact.get('end'), revenue=revenue, revenue_prior=revenue_prior,
                   growth_basis='FY' if revenue_prior else None,
                   operating_income=operating, operating_cash_flow=cash_flow,
                   capex=abs(capex) if capex is not None else None, capex_basis=capex_basis,
                   fcf=None if cash_flow is None or capex is None else cash_flow - abs(capex),
                   depreciation=depreciation, dividends=dividends,
                   dividends_verified=dividends is not None and dividends >= 0,
                   shares=shares, shares_prior=shares_prior, shares_basis='DILUTED_AVG_FY',
                   net_debt=net_debt, debt=debt, cash=cash,
                   balance_date=balance[1].isoformat() if balance else None)
        if revenue < MIN_REVENUE:
            row['rejected'] = 'REVENUE_BELOW_1BN'
        elif operating is not None and operating <= 0:
            row['rejected'] = 'NO_OPERATING_PROFIT'
        elif row['fcf'] is not None and row['fcf'] <= 0:
            row['rejected'] = 'NO_POSITIVE_FCF'
        if operating is None:
            flags.append('OPERATING_INCOME_MISSING')
        if row['fcf'] is None:
            flags.append('FCF_INCOMPLETE')
    return rows


# ---------------------------------------------------------------- stage 2: companyfacts
def _clean(facts, today):
    """Dedupe by (start, end) keeping the most recently filed (restated) value."""
    best = {}
    for fact in facts or []:
        end, start, value = _date(fact.get('end')), _date(fact.get('start')), _num(fact.get('val'))
        filed = _date(fact.get('filed'))
        if end is None or value is None or end > today or filed is None or filed > today:
            continue
        key = (start, end)
        if key not in best or filed >= best[key]['filed']:
            best[key] = dict(start=start, end=end, val=value, filed=filed,
                             accn=fact.get('accn'), form=fact.get('form'))
    return list(best.values())


def _units(companyfacts, tag, unit, taxonomy='us-gaap'):
    try:
        return companyfacts['facts'][taxonomy][tag]['units'][unit]
    except (KeyError, TypeError):
        return []


def _durations(companyfacts, tags, unit, today, largest=False):
    """Merged duration facts: per window the first tag that reports it, or the largest value."""
    merged = {}
    for tag in tags:
        for fact in _clean(_units(companyfacts, tag, unit), today):
            if fact['start'] is None:
                continue
            key = (fact['start'], fact['end'])
            if key not in merged or (largest and abs(fact['val']) > abs(merged[key]['val'])):
                merged[key] = dict(fact, tag=tag)
    return list(merged.values())


def _instants(companyfacts, tags, unit, today, taxonomy='us-gaap'):
    merged = {}
    for tag in tags:
        for fact in _clean(_units(companyfacts, tag, unit, taxonomy), today):
            if fact['start'] is None:
                merged.setdefault(fact['end'], dict(fact, tag=tag))
    return merged


def _days(fact):
    return (fact['end'] - fact['start']).days


def _at(facts, start, end, tolerance=7):
    matches = [f for f in facts if abs((f['start'] - start).days) <= tolerance
               and abs((f['end'] - end).days) <= tolerance]
    return min(matches, key=lambda f: abs((f['end'] - end).days) + abs((f['start'] - start).days),
               default=None)


def windows(revenue_facts):
    """Reporting windows anchored on revenue: FY, current YTD, prior YTD."""
    annual = [f for f in revenue_facts if 330 <= _days(f) <= 400]
    if not annual:
        return None
    fy = max(annual, key=lambda f: f['end'])
    result = dict(fy=(fy['start'], fy['end']))
    previous = _at(annual, fy['start'] - timedelta(days=365), fy['end'] - timedelta(days=365), 20)
    if previous:
        result['fy_prior'] = (previous['start'], previous['end'])
    year_start = fy['end'] + timedelta(days=1)
    ytd = [f for f in revenue_facts if f['end'] > fy['end'] and 60 <= _days(f) < 330
           and abs((f['start'] - year_start).days) <= 20]
    if ytd:
        current = max(ytd, key=lambda f: f['end'])
        prior = _at(revenue_facts, current['start'] - timedelta(days=365),
                    current['end'] - timedelta(days=365), 20)
        if prior:
            result.update(ytd=(current['start'], current['end']), ytd_prior=(prior['start'], prior['end']))
            before = _at(revenue_facts, prior['start'] - timedelta(days=365),
                         prior['end'] - timedelta(days=365), 20)
            if before:
                result['ytd_prior2'] = (before['start'], before['end'])
    return result


def ttm(facts, w):
    """TTM on the anchored windows; FY only when no matching year-to-date pair exists."""
    fy = _at(facts, *w['fy'])
    if fy is None:
        return None
    if 'ytd' in w:
        current, prior = _at(facts, *w['ytd']), _at(facts, *w['ytd_prior'])
        if current is not None and prior is not None:
            return dict(value=fy['val'] + current['val'] - prior['val'], basis='TTM',
                        start=w['ytd'][1] - timedelta(days=364), end=w['ytd'][1],
                        accns=[fy['accn'], current['accn'], prior['accn']])
    return dict(value=fy['val'], basis='FY', start=w['fy'][0], end=w['fy'][1], accns=[fy['accn']])


def prior_ttm(facts, w, basis):
    """Same construction one year earlier, for growth."""
    if 'fy_prior' not in w:
        return None
    fy = _at(facts, *w['fy_prior'])
    if fy is None:
        return None
    if basis == 'TTM' and 'ytd_prior2' in w:
        prior, before = _at(facts, *w['ytd_prior']), _at(facts, *w['ytd_prior2'])
        if prior is not None and before is not None:
            return fy['val'] + prior['val'] - before['val']
        return None
    return fy['val'] if basis == 'FY' else None


def _flows(companyfacts, revenue_facts, w, today):
    """Every flow measure on one set of windows; None if a core measure is missing."""
    flags = []
    revenue = ttm(revenue_facts, w)
    basis = revenue['basis']

    def measure(tags):
        value = ttm(_durations(companyfacts, tags, 'USD', today), w)
        return value if value is not None and value['basis'] == basis else None

    operating = measure(OPERATING_INCOME)
    if operating is None:
        operating = measure(PRETAX_INCOME)
        if operating is not None:
            flags.append('OPERATING_INCOME_PROXY')
    cash_flow = measure(OPERATING_CASH)
    capex_facts = _durations(companyfacts, CAPEX, 'USD', today, largest=True)
    capex = ttm(capex_facts, w)
    capex = capex if capex is not None and capex['basis'] == basis else None
    if operating is None or cash_flow is None or (capex is None and capex_facts):
        return None
    depreciation = measure(DEPRECIATION)
    if depreciation is None:
        flags.append('NO_DEPRECIATION')
    if capex is None:
        # Untagged capex is not zero capex: depreciation stands in as maintenance spend.
        capex = depreciation
        flags.append('CAPEX_NOT_TAGGED' if depreciation is not None else 'CAPEX_AND_DA_MISSING')
    return dict(revenue=revenue, basis=basis, operating=operating, cash_flow=cash_flow,
                capex=capex, depreciation=depreciation, dividends=measure(DIVIDENDS), flags=flags)


def company_metrics(companyfacts, today):
    """TTM metrics from one companyfacts document, all on the revenue windows.

    If any core measure lacks the year-to-date pair, every measure falls back
    to the last fiscal year together, so margins never mix reporting windows.
    """
    revenue_tags = []
    for tag in REVENUE:
        facts = [f for f in _clean(_units(companyfacts, tag, 'USD'), today) if f['start']]
        annual = [f for f in facts if 330 <= _days(f) <= 400]
        if annual:
            latest = max(annual, key=lambda f: f['end'])
            revenue_tags.append((latest['end'], latest['val'], tag, facts))
    if not revenue_tags:
        return None
    _, _, revenue_tag, revenue_facts = max(revenue_tags, key=lambda x: (x[0], x[1]))
    w = windows(revenue_facts)
    if w is None:
        return None
    flows = _flows(companyfacts, revenue_facts, w, today)
    if flows is None or flows['basis'] != 'TTM':
        w = {k: v for k, v in w.items() if k in ('fy', 'fy_prior')}
        flows = _flows(companyfacts, revenue_facts, w, today)
    if flows is None:
        return None
    flags = list(flows['flags'])
    revenue, basis = flows['revenue'], flows['basis']
    operating, cash_flow, capex = flows['operating'], flows['cash_flow'], flows['capex']
    depreciation, dividends = flows['depreciation'], flows['dividends']
    if dividends is None:
        flags.append('DIVIDENDS_NOT_TAGGED')
    revenue_prior = prior_ttm(revenue_facts, w, basis)
    growth_basis = basis if revenue_prior else None
    if revenue_prior is None and basis == 'TTM':
        current, prior = _at(revenue_facts, *w['ytd']), _at(revenue_facts, *w['ytd_prior'])
        if current and prior and prior['val'] > 0 and current['val'] > 0:
            revenue_prior, growth_basis = prior['val'] * revenue['value'] / current['val'], 'YTD'
    if basis == 'FY' and any(f['end'] > w['fy'][1] for f in revenue_facts):
        # A newer quarter exists but could not be used on identical windows.
        # Right after a 10-K the fiscal year simply is the latest twelve months.
        flags.append('FISCAL_YEAR_ONLY')

    # Shares: cover-page count if consistent with the latest diluted average.
    diluted = [f for f in _durations(companyfacts, DILUTED_SHARES, 'shares', today)
               if 60 <= _days(f) <= 120 or 330 <= _days(f) <= 400]
    latest_diluted = max(diluted, key=lambda f: (f['end'], -_days(f)), default=None)
    prior_diluted = None
    if latest_diluted is not None:
        same_length = [f for f in diluted if abs(_days(f) - _days(latest_diluted)) <= 20]
        prior_diluted = _at(same_length, latest_diluted['start'] - timedelta(days=365),
                            latest_diluted['end'] - timedelta(days=365), 20)
    cover = _instants(companyfacts, ('EntityCommonStockSharesOutstanding',), 'shares', today, 'dei')
    cover_latest = cover[max(cover)] if cover else None
    shares, shares_basis = None, None
    ratio = (cover_latest['val'] / latest_diluted['val']
             if cover_latest is not None and latest_diluted is not None and latest_diluted['val'] > 0 else None)
    if ratio is not None and 0.7 <= ratio <= 1.4:
        shares, shares_basis = cover_latest['val'], 'COVER_PAGE'
    elif ratio is not None and any(0.7 <= ratio / scale <= 1.4 for scale in (1e3, 1e6)):
        # First live scan: McDonald's tagged 711.1 diluted shares (millions meant).
        shares, shares_basis = cover_latest['val'], 'COVER_PAGE'
        flags.append('SHARES_SCALE_FIXED')
    elif latest_diluted is not None:
        shares, shares_basis = latest_diluted['val'], 'DILUTED_AVG'
        flags.append('SHARES_DILUTED_AVG')
    if not shares or shares <= 0:
        return None
    change = None
    if prior_diluted is not None and prior_diluted['val'] > 0:
        step = latest_diluted['val'] / prior_diluted['val']
        # A thousandfold jump between two diluted averages is a tagging scale error, not dilution.
        if 1e-2 < step < 1e2:
            change = 100 * (step - 1)

    # Balance sheet: every tag on the latest cash date only.
    cash_dates = _instants(companyfacts, CASH, 'USD', today)
    balance_date = max(cash_dates) if cash_dates else None
    net_debt = debt = cash = None
    if balance_date is not None:
        def get(tags):
            values = _instants(companyfacts, tags, 'USD', today)
            hit = next((values[d] for d in values if abs((d - balance_date).days) <= 5), None)
            return None if hit is None else hit['val']
        net_debt, debt, cash, debt_flags = net_debt_from(get)
        flags.extend(debt_flags)

    accns = [a for a in dict.fromkeys(revenue['accns'][:2]) if a]   # annual report, latest 10-Q
    return dict(basis=basis, period_start=revenue['start'].isoformat(),
                period_end=revenue['end'].isoformat(), revenue_tag=revenue_tag,
                revenue=revenue['value'], revenue_prior=revenue_prior, growth_basis=growth_basis,
                operating_income=operating['value'], operating_cash_flow=cash_flow['value'],
                capex=abs(capex['value']) if capex else None,
                capex_basis='DEPRECIATION_PROXY' if 'CAPEX_NOT_TAGGED' in flags else 'REPORTED' if capex else None,
                fcf=cash_flow['value'] - abs(capex['value']) if capex else None,
                depreciation=depreciation['value'] if depreciation else None,
                dividends=dividends['value'] if dividends else None,
                dividends_verified=dividends is not None and dividends['value'] >= 0,
                shares=shares, shares_basis=shares_basis, share_change_pct=change,
                shares_date=(cover_latest['end'].isoformat() if shares_basis == 'COVER_PAGE'
                             else latest_diluted['end'].isoformat()),
                net_debt=net_debt, debt=debt, cash=cash,
                balance_date=balance_date.isoformat() if balance_date else None,
                accns=accns, flags=flags, source='companyfacts')


# ---------------------------------------------------------------- scoring
INPUT_METADATA_KEYS = (
    'sic', 'flags', 'basis', 'period_start', 'period_end', 'growth_basis', 'balance_date',
    'shares_basis', 'shares_date', 'capex_basis', 'dividends_verified', 'source', 'normalization_status',
    'normalization_sources', 'normalization_date', 'normalized_fcf', 'denominator_status',
    'denominator_date', 'denominator_sources', 'valuation_shares', 'ads_status', 'ads_ratio',
    'ads_sources', 'as_of',
)


def _sourced(sources):
    """Require usable evidence locators, not a placeholder or a status alone.

    VERIFIED is a reviewer assertion, not something a URL can authenticate.
    The input ledger retains those assertions and locators for source review.
    """
    if not isinstance(sources, (list, tuple)) or not sources:
        return False
    return all(isinstance(url := s.get('url') if isinstance(s, dict) else s, str)
               and url.startswith('https://') and len(url.split('/')) > 3
               and not any(p in url.lower() for p in ('example.', 'placeholder', 'todo'))
               for s in sources)


def score_metrics(m, price, bands=None, discount=DISCOUNT):
    """The existing eight curves, with unsupported categories left unavailable.

    Partial selection uses known fixed-weight contributions; it never rescales
    them into a composite. Reported FCF/rate valuation is a scenario. A producer
    needs a separately sourced VERIFIED normalized_fcf (zero is valid), while
    Cash Generation continues to describe supported reported FCF.
    """
    bands = bands or _bands()
    flags = list(dict.fromkeys(m.get('flags') or []))
    revenue, fcf, shares = (_num(m.get(k)) for k in ('revenue', 'fcf', 'shares'))
    operating, depreciation = (_num(m.get(k)) for k in ('operating_income', 'depreciation'))
    price, discount = _num(price), _num(discount)
    price = price if price is not None and price > 0 else None
    shares = shares if shares is not None and shares > 0 else None

    def ratio(numerator, denominator, scale=1):
        return _num(scale * numerator / denominator) if numerator is not None and denominator else None

    prior = _num(m.get('revenue_prior'))
    growth = 100 * (revenue / prior - 1) if revenue is not None and prior is not None and prior > 0 else None
    if growth is None or 'GROWTH_DEFAULT' in flags:
        growth = None
        flags.append('GROWTH_DEFAULT')
    op_margin = ratio(operating, revenue, 100) if revenue is not None and revenue > 0 else None
    fcf_margin = ratio(fcf, revenue, 100) if revenue is not None and revenue > 0 else None
    ebitda = operating + depreciation if operating is not None and depreciation is not None else None
    if depreciation is None or 'NO_DEPRECIATION' in flags:
        ebitda = None
        flags.append('NO_DEPRECIATION')
    if 'OPERATING_INCOME_PROXY' in flags:
        ebitda = None
    nd_ebitda = ratio(_num(m.get('net_debt')), ebitda) if ebitda is not None and ebitda > 0 else None
    if any(f in flags for f in ('DEBT_NOT_TAGGED', 'DEBT_PARTIAL', 'CASH_NOT_TAGGED', 'BALANCE_DEFAULT')):
        nd_ebitda = None
    if nd_ebitda is None:
        flags.append('BALANCE_DEFAULT')
    change, shares_prior = _num(m.get('share_change_pct')), _num(m.get('shares_prior'))
    if change is None and shares is not None and shares_prior is not None and shares_prior > 0 \
            and 1e-2 < shares / shares_prior < 1e2:
        change = 100 * (shares / shares_prior - 1)
    if change is None:
        flags.append('DILUTION_MISSING')
    if growth is not None and not -50 <= growth <= 100:
        flags.append('GROWTH_OUTLIER')
    if change is not None and abs(change) > 25:
        flags.append('SHARES_JUMP')

    # Diluted averages and foreign ordinary-share counts require a dated bridge
    # to the units actually priced. ads_ratio is ordinary shares per traded ADS.
    average = 'SHARES_DILUTED_AVG' in flags or str(m.get('shares_basis', '')).startswith('DILUTED_AVG')
    foreign = 'FOREIGN_FILER' in flags
    bridge_date = _date(m.get('denominator_date'))
    cutoff = _date(m.get('as_of'))
    bridge = (m.get('denominator_status') == 'VERIFIED' and bridge_date is not None
              and (cutoff is None or bridge_date <= cutoff) and _sourced(m.get('denominator_sources')))
    valuation_shares = shares
    if average and not bridge:
        valuation_shares = None
    elif average:
        valuation_shares = _num(m.get('valuation_shares'))
        valuation_shares = valuation_shares if valuation_shares is not None and valuation_shares > 0 else None
    if foreign:
        ads_ratio = _num(m.get('ads_ratio'))
        if not bridge or m.get('ads_status') != 'VERIFIED' or not _sourced(m.get('ads_sources')) \
                or ads_ratio is None or ads_ratio <= 0:
            valuation_shares = None
        elif valuation_shares is not None:
            valuation_shares /= ads_ratio
    denominator_ok = valuation_shares is not None
    if not denominator_ok:
        flags.append('DENOMINATOR_UNVERIFIED')

    sic = _num(m.get('sic'))
    classified = sic is not None and 100 <= sic <= 9999 and sic.is_integer()
    if not classified:
        flags.append('CLASSIFICATION_MISSING')
    producer = is_commodity_producer(sic)
    normalized = _num(m.get('normalized_fcf'))
    normalized_ok = (normalized is not None and normalized >= 0
                     and m.get('normalization_status') == 'VERIFIED'
                     and _sourced(m.get('normalization_sources')))
    capex_unknown = any(f in flags for f in ('CAPEX_NOT_TAGGED', 'CAPEX_AND_DA_MISSING'))
    reported_ok = fcf is not None and not capex_unknown
    valuation_fcf = normalized if normalized_ok else fcf if reported_ok and not producer else None
    valuation_issues = []
    if not classified:
        valuation_issues.append('CLASSIFICATION_MISSING')
    if producer and not normalized_ok:
        valuation_issues.append('COMMODITY_MIDCYCLE_REQUIRED')
        flags.append('COMMODITY_MIDCYCLE_REQUIRED')
    if not denominator_ok:
        valuation_issues.append('DENOMINATOR_UNVERIFIED')
    if valuation_fcf is None:
        valuation_issues.append('FCF_INCOMPLETE')
    if price is None:
        flags.append('NO_PRICE')
        valuation_issues.append('NO_PRICE')
    if discount is None or discount <= 0:
        valuation_issues.append('DISCOUNT_INVALID')
    valuation_ok = not valuation_issues
    raw_market_cap = price * shares if price is not None and shares is not None else None
    market_cap = price * valuation_shares if price is not None and denominator_ok else None
    fcf_yield = ratio(valuation_fcf, market_cap, 100) if valuation_ok else None
    ngv = ratio(ratio(valuation_fcf, valuation_shares), discount) if valuation_ok else None
    cover_pct = ratio(ngv, price, 100)
    raw_dividends = _num(m.get('dividends'))
    invalid_dividends = raw_dividends is not None and raw_dividends < 0
    dividends = raw_dividends
    if invalid_dividends or (raw_dividends == 0 and m.get('dividends_verified') is not True):
        dividends = None
    if invalid_dividends:
        flags.append('DIVIDENDS_INVALID')
    elif dividends is None:
        flags.append('DIVIDENDS_NOT_TAGGED')
    dividend_yield = ratio(dividends, market_cap, 100)
    buyback_yield = max(0.0, -change) if change is not None else None
    shareholder_yield = dividend_yield + buyback_yield \
        if dividend_yield is not None and buyback_yield is not None else None
    saturated_returns = (not invalid_dividends and shareholder_yield is None and market_cap is not None
                         and buyback_yield is not None
                         and _band(buyback_yield, bands['RETURNS']) == bands['RETURNS'][-1][1])
    if saturated_returns:
        # Every possible nonnegative dividend leaves the category at its top
        # band. This proves a category bound without inventing a zero payout.
        shareholder_yield = buyback_yield
    inputs = dict(g=growth, p=op_margin, c=fcf_margin, b=nd_ebitda, v=fcf_yield,
                  r=shareholder_yield, pr=cover_pct, d=change)
    values = dict(g=_band(growth, bands['GROWTH']), p=_band(op_margin, bands['PROFIT']),
                  c=_band(fcf_margin, bands['CASHGEN']), b=_band(nd_ebitda, bands['BALANCE']),
                  d=_band(change, bands['DILUTION']), v=_band(fcf_yield, bands['VALUE']),
                  r=_band(shareholder_yield, bands['RETURNS']), pr=priced_in(cover_pct))
    if 'OPERATING_INCOME_PROXY' in flags:
        values['p'] = values['b'] = None
    if not reported_ok:
        values['c'] = None
        flags.append('FCF_INCOMPLETE')
    values = {k: round(v, 1) if v is not None else None for k, v in values.items()}
    if not classified:
        valuation_status = 'BLOCKED_CLASSIFICATION'
    elif producer and not normalized_ok:
        valuation_status = 'PENDING_MIDCYCLE'
    elif not denominator_ok:
        valuation_status = 'BLOCKED_DENOMINATOR'
    elif not valuation_ok:
        valuation_status = 'BLOCKED_DATA'
    else:
        valuation_status = 'VERIFIED_NORMALIZED_FCF' if normalized_ok else 'SCENARIO_REPORTED_FCF'
        flags.append('NORMALIZED_FCF_VERIFIED' if normalized_ok else 'REPORTED_FCF_SCENARIO')
    metrics = dict(growth_pct=growth, operating_margin_pct=op_margin, fcf_margin_pct=fcf_margin,
                   ebitda=ebitda, nd_ebitda=nd_ebitda, share_change_pct=change, market_cap=market_cap,
                   fcf_yield_pct=fcf_yield, dividend_yield_pct=dividend_yield,
                   buyback_yield_pct=buyback_yield if market_cap is not None else None,
                   ngv_per_share=ngv, cover_pct=cover_pct, valuation_fcf=valuation_fcf,
                   valuation_shares=valuation_shares, discount_rate=discount,
                   raw_market_cap=raw_market_cap, raw_fcf_yield_pct=ratio(fcf, raw_market_cap, 100))
    reasons = dict(g='GROWTH_DEFAULT', p='OPERATING_INCOME_MISSING', c='FCF_INCOMPLETE',
                   b='BALANCE_DEFAULT', v=valuation_status, pr=valuation_status,
                   r='DENOMINATOR_OR_RETURNS_INCOMPLETE', d='DILUTION_MISSING')
    components = [dict(key=k, label=LABELS[k], value=values[k], weight=w,
                       contribution=values[k] * w if values[k] is not None else None,
                       input=inputs[k], supported=values[k] is not None,
                       input_basis='SATURATED_LOWER_BOUND' if k == 'r' and saturated_returns else 'MEASURED_INPUT',
                       reason=('DIVIDEND_UNVERIFIED_SATURATED_BY_BUYBACK_PROXY' if k == 'r' and saturated_returns
                               else None if values[k] is not None else reasons[k])) for k, w in WEIGHTS.items()]
    coverage = round(sum(c['weight'] for c in components if c['supported']), 12)
    selection = sum(c['contribution'] for c in components if c['supported'])
    complete = all(c['supported'] for c in components)
    total = selection if complete else None
    sub = tuple(values[k] for k in ('g', 'p', 'c', 'b', 'v', 'r'))
    return dict(score=total, band=model_band(total), components=components, metrics=metrics,
                flags=list(dict.fromkeys(flags)), sub=sub if all(v is not None for v in sub) else None,
                coverage_weight=coverage, selection_score=selection,
                score_bounds=dict(lower=selection, upper=selection + 10 * (1 - coverage)),
                status='COMPLETE' if complete else 'PARTIAL', valuation_status=valuation_status,
                valuation_issues=valuation_issues)


MAX_FCF_YIELD = 50.0     # % of market value
MIN_PRICE_TO_SALES = 0.05


def implausible(row, metrics):
    """Reasons a scored row cannot be a real operating company's numbers.

    First live scan: McDonald's and Nutanix showed FCF yields above 4,000 %
    (share counts tagged in millions/thousands), Wise and Royalty Pharma
    showed free cash flow above revenue (customer funds and royalty receipts
    in operating cash flow). Such rows leave the ranking and are listed apart.
    """
    reasons = []
    revenue, fcf = row.get('revenue'), row.get('fcf')
    market_cap = metrics.get('market_cap') or metrics.get('raw_market_cap')
    if market_cap and revenue and market_cap / revenue < MIN_PRICE_TO_SALES:
        reasons.append('Marktwert unter 5 % des Umsatzes: Aktienzahl vermutlich falsch skaliert')
    if fcf is not None and revenue and fcf > revenue:
        reasons.append('Free Cashflow über dem Umsatz: Kundengelder oder Sonderzahlungen im operativen Cashflow')
    if (metrics.get('fcf_yield_pct') or metrics.get('raw_fcf_yield_pct') or 0) > MAX_FCF_YIELD:
        reasons.append(f'FCF-Rendite über {MAX_FCF_YIELD:.0f} % des Marktwerts')
    return reasons


def regime_fit(row, sub):
    """The engine's unchanged regime formula on this draft row (SIC-derived sector)."""
    try:
        from engine import regime_scores
    except Exception:   # pragma: no cover - engine import needs yfinance
        return {}
    if sub is None:
        return {}
    scored = score_metrics(row, row.get('price'))
    m = scored['metrics']
    if m['cover_pct'] is None:
        return {}
    draft = dict(fcf=m['valuation_fcf'] / 1e6, shares=m['valuation_shares'] / 1e6, r=DISCOUNT,
                 price=row.get('price'), sector=row.get('sector', ''), sub=sub)
    return regime_scores(draft) if draft['price'] else {}


def universe_tickers():
    """US tickers already modelled in engine.py (exchange-suffixed listings excluded)."""
    try:
        from engine import DATA
    except Exception:   # pragma: no cover
        return set()
    tickers = set()
    for key, row in DATA.items():
        symbol = str(row.get('yf') or key).upper()
        if '.' not in symbol:
            tickers.update({symbol, key.upper()})
    return tickers


# ---------------------------------------------------------------- prices
def _close(frame, symbol):
    try:
        columns = frame.columns
        if getattr(columns, 'nlevels', 1) > 1:
            if symbol in columns.get_level_values(0):
                return frame[symbol]['Close']
            if symbol in columns.get_level_values(1):
                return frame.xs(symbol, axis=1, level=1)['Close']
            return None
        return frame['Close']
    except (KeyError, TypeError, AttributeError):
        return None


def fetch_prices(symbols, chunk=80, pause=2.0, log=print):
    """Dated Yahoo daily closes: {symbol: {'price': x, 'date': 'YYYY-MM-DD'}}."""
    import yfinance as yf
    found = {}
    pending = list(dict.fromkeys(symbols))
    for size in (chunk, 15):
        missing = []
        for i in range(0, len(pending), size):
            part = pending[i:i + size]
            frame = None
            for attempt in range(3):
                try:
                    frame = yf.download(part, period='10d', interval='1d', auto_adjust=False,
                                        actions=False, progress=False, group_by='ticker', threads=True)
                    break
                except Exception as exc:
                    log(f'Yahoo batch failed ({type(exc).__name__}); retry {attempt + 1}')
                    time.sleep(5 * (attempt + 1))
            for symbol in part:
                series = None if frame is None or frame.empty else _close(frame, symbol)
                series = None if series is None else series.dropna()
                if series is None or series.empty:
                    missing.append(symbol)
                    continue
                price = _num(series.iloc[-1])
                if price is None or price <= 0:
                    missing.append(symbol)
                    continue
                found[symbol] = dict(price=price, date=series.index[-1].date().isoformat())
            time.sleep(pause)
        pending = missing
        if not pending:
            break
    return found


# ---------------------------------------------------------------- orchestration
def _finite_or_none(value):
    value = _num(value)
    return None if value is None else value


def _candidate(row, scored, info, universe):
    metrics = {k: _finite_or_none(row.get(k)) for k in (
        'revenue', 'revenue_prior', 'operating_income', 'operating_cash_flow', 'capex', 'fcf',
        'depreciation', 'dividends', 'shares', 'net_debt', 'debt', 'cash')}
    metrics.update({k: _finite_or_none(v) for k, v in scored['metrics'].items()})
    flags = list(dict.fromkeys(row.get('flags', []) + scored['flags']))
    sources = [dict(title='SEC companyfacts (XBRL, alle gemeldeten Werte)', url=companyfacts_url(row['cik'])),
               dict(title='SEC EDGAR: 10-K/10-Q-Einreichungen', url=company_url(row['cik']))]
    for accn in (row.get('accns') or [])[:2]:
        sources.append(dict(title=f'SEC-Einreichung {accn}', url=filing_url(row['cik'], accn)))
    return dict(
        ticker=row['ticker'], yahoo=row['yahoo'], cik=row['cik'], name=info.get('name') or row['name'],
        exchange=row['exchange'], sic=info.get('sic'), sic_description=info.get('sic_description', ''),
        sector=row.get('sector', 'Unbekannt'), in_universe=row['ticker'] in universe or row['yahoo'] in universe,
        price=_finite_or_none(row.get('price')), price_date=row.get('price_date'), currency='USD',
        basis=row.get('basis'), period_start=row.get('period_start'), period_end=row.get('period_end'),
        growth_basis=row.get('growth_basis'), shares_basis=row.get('shares_basis'),
        balance_date=row.get('balance_date'), source=row.get('source'),
        input_metadata={k: row[k] for k in INPUT_METADATA_KEYS if k in row},
        normalization_status=row.get('normalization_status') or 'UNREVIEWED',
        metrics=metrics, score=_finite_or_none(scored['score']), band=model_band(scored['score']),
        coverage_weight=scored['coverage_weight'], selection_score=scored['selection_score'],
        score_bounds=scored['score_bounds'], status=scored['status'],
        valuation_status=scored['valuation_status'], valuation_issues=scored['valuation_issues'],
        components=[dict(c, input=_finite_or_none(c['input'])) for c in scored['components']],
        regime_fit=row.get('regime_fit') or {}, flags=flags,
        flag_text={f: FLAG_TEXT.get(f, f) for f in flags}, sources=sources)


def run(sec=None, prices=None, universe=None, today=None, now=None, shortlist=SHORTLIST,
        keep=KEEP, log=print):
    now = now or datetime.now(timezone.utc)
    today = today or now.date()
    sec = sec or SecClient(os.environ.get('SEC_USER_AGENT'), log=log)
    prices = prices or (lambda symbols: fetch_prices(symbols, log=log))
    universe = universe_tickers() if universe is None else set(universe)
    bands = _bands()

    listing = parse_universe(sec.get_json(TICKERS_URL))
    log(f'Universe: {len(listing)} NYSE/Nasdaq companies')
    plan = frame_plan(today)
    frames = {key: parse_frame(sec.get_json(frame_url(*key))) for key in plan}
    empty = sum(1 for v in frames.values() if not v)
    if empty > len(plan) // 2:
        raise RuntimeError(f'{empty} of {len(plan)} SEC frames empty; refusing to publish a thin scan')
    rows = stage_one(listing, frames, today)
    rejected = {}
    for row in rows:
        if row['rejected']:
            rejected[row['rejected']] = rejected.get(row['rejected'], 0) + 1
    passed = [r for r in rows if not r['rejected']]
    log(f'Stage 1: {len(passed)} pass the hard filters')

    quotes = prices([r['yahoo'] for r in passed])
    priced = []
    for row in passed:
        quote = quotes.get(row['yahoo'])
        if quote:
            price, stamp = _num(quote.get('price')), _date(quote.get('date'))
            # Daily dates only: never future-dated, and at most four calendar
            # days old (weekends/holidays included). The page has its own gate.
            if price is None or price <= 0 or stamp is None or not 0 <= (today - stamp).days <= 4:
                continue
            row.update(price=price, price_date=stamp.isoformat(), as_of=today.isoformat())
            row['pre_selection_score'] = score_metrics(row, row['price'], bands)['selection_score']
            priced.append(row)
    priced.sort(key=lambda r: (-r['pre_selection_score'], -r['revenue'], r['ticker']))

    # Banks, insurers and REITs report cash flows that FCF does not describe;
    # their frame "FCF" yields look spectacular and would crowd the shortlist.
    # Walk the pre-score ranking and skip them until the shortlist is full.
    short, infos, excluded_financial = [], {}, 0
    for row in priced:
        if len(short) >= shortlist:
            break
        info = parse_submission(sec.get_json(submissions_url(row['cik']))) or {}
        if is_financial(info.get('sic')):
            excluded_financial += 1
            continue
        infos[row['cik']] = info
        row.update(sic=info.get('sic'), sector=sector_from_sic(info.get('sic')))
        if info.get('annual_form') in ('20-F', '40-F'):
            row['flags'] = list(dict.fromkeys(row['flags'] + ['FOREIGN_FILER']))
        short.append(row)
    log(f'Stage 1: {len(priced)} priced, {excluded_financial} financials skipped, {len(short)} shortlisted')

    refined, candidates, set_aside = 0, [], []
    for row in short:
        info = infos[row['cik']]
        facts = sec.get_json(companyfacts_url(row['cik']))
        metrics = company_metrics(facts, today) if facts else None
        if metrics:
            refined += 1
            # Replace every frame figure; the frame-based prior share count would
            # otherwise mix an annual average with the cover-page count. Flags
            # about the filer itself survive the replacement.
            keep_flags = [f for f in row['flags'] if f == 'FOREIGN_FILER']
            row.update(metrics, shares_prior=None)
            row['flags'] = list(dict.fromkeys(keep_flags + row['flags']))
        else:
            row['flags'] = list(dict.fromkeys(row['flags'] + ['FRAMES_ONLY']))
        scored = score_metrics(row, row['price'], bands)
        if (row.get('fcf') is not None and row['fcf'] <= 0) \
                or (row.get('operating_income') is not None and row['operating_income'] <= 0):
            continue
        reasons = implausible(row, scored['metrics'])
        if reasons:
            set_aside.append(dict(ticker=row['ticker'], name=info.get('name') or row['name'],
                                  reasons=reasons, source_url=companyfacts_url(row['cik'])))
            continue
        row['regime_fit'] = regime_fit(row, scored['sub'])
        candidates.append(_candidate(row, scored, info, universe))
    candidates.sort(key=lambda c: (c['score'] is None,
                                   -(c['score'] if c['score'] is not None else c['selection_score']), c['ticker']))
    kept = candidates[:keep]
    log(f'Stage 2: {refined} with TTM, {len(set_aside)} implausible set aside, '
        f'{len(candidates)} still positive, {len(kept)} kept')

    payload = dict(
        schema=VERSION, generated_at=now.isoformat(), as_of=today.isoformat(),
        coverage='USA: an NYSE oder Nasdaq notierte US-GAAP-Berichterstatter mit SEC-XBRL-Daten. '
                 'Ohne Banken, Versicherer und REITs. Europa ist noch nicht abgedeckt.',
        funnel=[dict(stage='NYSE/Nasdaq-Unternehmen in der SEC-Liste', count=len(listing)),
                dict(stage='Umsatz ≥ 1 Mrd. USD; kein belegter negativer Gewinn/FCF (offene Daten bleiben sichtbar)',
                     count=len(passed)),
                dict(stage='Mit datiertem Schlusskurs', count=len(priced)),
                dict(stage=f'Vorauswahl nach vorläufigem Score, ohne Banken, Versicherer und REITs '
                           f'(SIC 6000–6799; {excluded_financial} übersprungen)', count=len(short)),
                dict(stage=f'Nach Prüfung der Einreichungen plausibel, offene Kategorien separat ({refined} mit '
                           f'TTM-Werten, {len(set_aside)} unplausibel beiseitegelegt)', count=len(candidates)),
                dict(stage='Gespeicherte Kandidaten (vollständige Scores, dann fixe Teilbeiträge)', count=len(kept))],
        excluded_financials=excluded_financial,
        implausible=set_aside,
        rejected=rejected,
        method=dict(scoring_version=SCORING_VERSION, weights=WEIGHTS, discount_rate=DISCOUNT, min_revenue_usd=MIN_REVENUE,
                    score_contract='fixed-weight-coverage-v2',
                    quote_date_policy='Datumsgranularität: kein Zukunftskurs, höchstens 4 Kalendertage alt.',
                    shortlist=shortlist, keep=keep, bands=[dict(upper_exclusive=c, label=l) for c, l in BANDS],
                    ttm='Letztes Geschäftsjahr + laufendes YTD − Vorjahres-YTD, alle Werte auf identischen Berichtsfenstern.',
                    note='Mechanischer Vorscore wie autoscore: Umsatzwachstum als Proxy, pauschal 8 % als '
                         'Szenario-Diskontsatz. Unbelegte Kategorien bleiben offen; Produzentenbewertung '
                         'erfordert belegten Mid-Cycle-FCF. Kein InvestorAce-Modellscore und keine Kaufempfehlung.'),
        sources=dict(universe=TICKERS_URL, frames=f'{SEC_DATA}/api/xbrl/frames/',
                     companyfacts=f'{SEC_DATA}/api/xbrl/companyfacts/',
                     prices='Yahoo Finance, Tagesschlusskurs mit Datum'),
        requests=dict(sec=getattr(sec, 'calls', None), sec_failures=getattr(sec, 'failures', None)),
        candidates=kept)
    errors = validate_payload(payload, now=now)
    if errors:
        raise ValueError('Invalid market scan: ' + '; '.join(errors[:10]))
    return payload


# ---------------------------------------------------------------- validation
def _guarded_errors(c, *, allow_quote_gaps=False):
    """Validate the new partial-score contract without rejecting old snapshots."""
    ticker, errors = c.get('ticker'), []
    components = c.get('components')
    if not isinstance(components, list) or len(components) != len(WEIGHTS) \
            or not all(isinstance(x, dict) for x in components) \
            or [x.get('key') for x in components] != list(WEIGHTS):
        return [f'{ticker}: guarded score needs all eight fixed-weight components']
    coverage, subtotal, complete = 0.0, 0.0, True
    for component in components:
        key = component['key']
        weight, value, contribution = (_num(component.get(k)) for k in ('weight', 'value', 'contribution'))
        if weight is None or not math.isclose(weight, WEIGHTS[key], abs_tol=1e-12):
            errors.append(f'{ticker}: {key} weight differs from the fixed framework')
        if component.get('value') is None:
            complete = False
            if component.get('contribution') is not None:
                errors.append(f'{ticker}: {key} unavailable value has a contribution')
        elif value is None or not 0 <= value <= 10 or contribution is None \
                or not math.isclose(contribution, value * WEIGHTS[key], abs_tol=1e-9):
            errors.append(f'{ticker}: {key} invalid value or fixed-weight contribution')
        else:
            coverage += WEIGHTS[key]
            subtotal += contribution
    declared_coverage, declared_subtotal = _num(c.get('coverage_weight')), _num(c.get('selection_score'))
    if declared_coverage is None or not math.isclose(declared_coverage, coverage, abs_tol=1e-9):
        errors.append(f'{ticker}: coverage_weight does not match supported categories')
    if declared_subtotal is None or not math.isclose(declared_subtotal, subtotal, abs_tol=1e-9):
        errors.append(f'{ticker}: selection_score must be the fixed-weight subtotal')
    bounds = c.get('score_bounds') or {}
    for key, expected in (('lower', subtotal), ('upper', subtotal + 10 * (1 - coverage))):
        value = _num(bounds.get(key)) if isinstance(bounds, dict) else None
        if value is None or not math.isclose(value, expected, abs_tol=1e-9):
            errors.append(f'{ticker}: score_bounds.{key} does not match coverage')
    if c.get('status') != ('COMPLETE' if complete else 'PARTIAL'):
        errors.append(f'{ticker}: score status does not match category coverage')
    score = _num(c.get('score'))
    if not complete and c.get('score') is not None:
        errors.append(f'{ticker}: incomplete categories cannot have a composite score')
    elif complete and (score is None or not math.isclose(score, subtotal, abs_tol=1e-9)):
        errors.append(f'{ticker}: complete score does not match fixed-weight contributions')
    # New rows retain enough inputs to detect flags that would otherwise be
    # ignored by a coherent-looking but fabricated complete score. Legacy rows
    # are intentionally left structurally loadable for guarded replay.
    metadata = c.get('input_metadata')
    if isinstance(metadata, dict):
        inputs = dict(c.get('metrics') or {})
        inputs.update(metadata)
        inputs.update(sic=c.get('sic'), flags=c.get('flags') or [])
        expected = score_metrics(inputs, c.get('price'), discount=inputs.get('discount_rate', DISCOUNT))
        price = _num(c.get('price'))
        quote_gap = price is None or price <= 0 or _date(c.get('price_date')) is None
        for actual, recomputed in zip(components, expected['components']):
            if allow_quote_gaps and quote_gap and actual['key'] in ('v', 'pr', 'r'):
                # The page withdraws these outputs per issuer after loading.
                # All fixed weights, ties and nonquote inputs remain checked.
                continue
            actual_value, expected_value = _num(actual.get('value')), recomputed['value']
            if (actual_value is None) != (expected_value is None) or (actual_value is not None
                    and not math.isclose(actual_value, expected_value, abs_tol=1e-9)):
                errors.append(f'{ticker}: {actual["key"]} does not match guarded inputs')
    return errors


def validate_payload(payload, now=None, max_age_days=None, *, allow_quote_gaps=False):
    """Validate structure; the page may quarantine quote gaps per issuer.

    Writers use strict validation. The loader's explicit opt-in permits quote
    gaps only so its mandatory per-name audit can withdraw those outputs.
    """
    errors = []
    if not isinstance(payload, dict) or payload.get('schema') != VERSION:
        return ['schema must be ' + VERSION]
    try:
        generated = datetime.fromisoformat(str(payload.get('generated_at')).replace('Z', '+00:00'))
        if generated.tzinfo is None:
            errors.append('generated_at needs a timezone')
        elif now is not None and generated > now + timedelta(minutes=5):
            errors.append('generated_at lies in the future')
        elif now is not None and max_age_days is not None and now - generated > timedelta(days=max_age_days):
            errors.append('scan is stale')
    except ValueError:
        errors.append('generated_at is not ISO 8601')
    candidates = payload.get('candidates')
    if not isinstance(candidates, list):
        return errors + ['candidates must be a list']
    seen = set()
    for c in candidates:
        if not isinstance(c, dict):
            errors.append('candidate must be an object')
            continue
        ticker = c.get('ticker')
        if not isinstance(ticker, str) or not re.fullmatch(r'[A-Z0-9][A-Z0-9.\-]{0,9}', ticker):
            errors.append(f'bad ticker {ticker!r}')
            continue
        if ticker in seen:
            errors.append(f'{ticker}: duplicate')
        seen.add(ticker)
        score = c.get('score')
        if score is not None and (_num(score) is None or not 0 <= score <= 10):
            errors.append(f'{ticker}: score out of range')
        if c.get('band') != model_band(score):
            errors.append(f'{ticker}: band does not match score')
        price = c.get('price')
        if not allow_quote_gaps and price is not None and (_num(price) is None or price <= 0):
            errors.append(f'{ticker}: price must be positive')
        if not allow_quote_gaps and price is not None and _date(c.get('price_date')) is None:
            errors.append(f'{ticker}: price without date')
        for key, value in (c.get('metrics') or {}).items():
            if value is not None and _num(value) is None:
                errors.append(f'{ticker}: metric {key} not finite')
        total = sum(_num(x.get('contribution')) or 0 for x in c.get('components') or [] if isinstance(x, dict))
        if score is not None and c.get('components') and not math.isclose(total, score, abs_tol=1e-9):
            errors.append(f'{ticker}: components do not add up to the score')
        if any(k in c for k in ('coverage_weight', 'selection_score', 'score_bounds', 'status')):
            errors.extend(_guarded_errors(c, allow_quote_gaps=allow_quote_gaps))
        for source in c.get('sources') or []:
            if not str(source.get('url', '')).startswith('https://'):
                errors.append(f'{ticker}: non-https source')
    for item in payload.get('implausible') or []:
        if not isinstance(item, dict) or not isinstance(item.get('reasons'), list) or not item['reasons'] \
                or not str(item.get('source_url', '')).startswith('https://'):
            errors.append('implausible entries need reasons and an https source')
        elif item.get('ticker') in seen:
            errors.append(f'{item.get("ticker")}: both ranked and set aside')
    try:
        json.dumps(payload, allow_nan=False)
    except ValueError:
        errors.append('payload contains NaN or infinity')
    return errors


def _fmt(value, digits=1, suffix=''):
    value = _num(value)
    return '—' if value is None else f'{value:,.{digits}f}{suffix}'.replace(',', ' ')


def report_markdown(payload_path, log_path=None, outcome='success', rows=40):
    """Pull-request summary: funnel, new ideas, overlaps and the log tail."""
    lines = [f'### Marktscan · Live-Lauf: `{outcome}`', '']
    payload = None
    # After a failed run the file on disk is the previous scan; never present it as this one.
    if payload_path and outcome == 'success' and Path(payload_path).exists():
        try:
            payload = json.loads(Path(payload_path).read_text(encoding='utf-8'))
        except ValueError:
            payload = None
    if payload:
        errors = validate_payload(payload)
        lines += [f'Stand {payload.get("as_of")} · SEC-Anfragen {payload.get("requests", {}).get("sec")} '
                  f'(fehlgeschlagen {payload.get("requests", {}).get("sec_failures")}) · '
                  f'Validierung: {"ok" if not errors else "; ".join(errors[:3])}', '',
                  '| Stufe | Anzahl |', '|---|---:|']
        lines += [f'| {s["stage"]} | {s["count"]} |' for s in payload.get('funnel', [])]
        rejected = payload.get('rejected') or {}
        if rejected:
            lines += ['', 'Ausgeschieden: ' + ', '.join(f'{k} {v}' for k, v in sorted(rejected.items()))]
        fresh = [c for c in payload.get('candidates', []) if not c.get('in_universe')]
        held = [c for c in payload.get('candidates', []) if c.get('in_universe')]
        lines += ['', f'**Neue Ideen (Top {min(rows, len(fresh))} von {len(fresh)})**', '',
                  '| # | Ticker | Unternehmen | Sektor | Score | Band | Umsatzwachstum | Op.-Marge | FCF-Rendite '
                  '| NGV-Deckung | Basis | Kurs | Hinweise |',
                  '|---:|---|---|---|---:|---|---:|---:|---:|---:|---|---|---|']
        for i, c in enumerate(fresh[:rows], 1):
            m = c.get('metrics') or {}
            lines.append(f'| {i} | {c["ticker"]} | {c.get("name", "")[:28]} | {c.get("sector")} | '
                         f'{_fmt(c.get("score"), 2)} | {c.get("band")} | {_fmt(m.get("growth_pct"), 1, " %")} | '
                         f'{_fmt(m.get("operating_margin_pct"), 1, " %")} | {_fmt(m.get("fcf_yield_pct"), 1, " %")} | '
                         f'{_fmt(m.get("cover_pct"), 0, " %")} | {c.get("basis")} bis {c.get("period_end")} | '
                         f'{_fmt(c.get("price"), 2)} ({c.get("price_date")}) | {", ".join(c.get("flags") or [])} |')
        if held:
            lines += ['', 'Schon im Universum: ' + ', '.join(f'{c["ticker"]} {_fmt(c.get("score"), 2)}' for c in held)]
        aside = payload.get('implausible') or []
        if aside:
            lines += ['', 'Beiseitegelegt (unplausibel): ' + '; '.join(
                f'{x.get("ticker")} – {" / ".join(x.get("reasons") or [])}' for x in aside)]
    else:
        lines.append('Kein gültiges Ergebnis geschrieben.')
    if log_path and Path(log_path).exists():
        text = Path(log_path).read_text(encoding='utf-8', errors='replace')
        if outcome != 'success' and 'SEC_USER_AGENT' in text:
            lines += ['', '**Aktion nötig:** ' + AGENT_HELP]
        tail = text.splitlines()[-(60 if outcome != 'success' else 12):]
        lines += ['', '<details><summary>Log (Ende)</summary>', '', '```', *tail, '```', '</details>']
    return '\n'.join(lines) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--output', type=Path, default=Path('market-scan'))
    parser.add_argument('--shortlist', type=int, default=SHORTLIST)
    parser.add_argument('--keep', type=int, default=KEEP)
    parser.add_argument('--report', type=Path, help='print a Markdown summary of this scan file and exit')
    parser.add_argument('--log', type=Path, help='log file whose tail the report includes')
    parser.add_argument('--outcome', default='success')
    args = parser.parse_args(argv)
    if args.report:
        sys.stdout.write(report_markdown(args.report, args.log, args.outcome))
        return 0
    from integrity import atomic_text
    try:
        payload = run(shortlist=args.shortlist, keep=args.keep)
    except RuntimeError as exc:      # deliberate stops: agent, SEC refusal, thin frames
        print(f'Marktscan abgebrochen: {exc}', file=sys.stderr)
        return 1
    args.output.mkdir(parents=True, exist_ok=True)
    atomic_text(args.output / 'latest.json',
                json.dumps(payload, ensure_ascii=False, indent=1, allow_nan=False) + '\n')
    print(f'Market scan: {len(payload["candidates"])} candidates -> {args.output / "latest.json"}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
