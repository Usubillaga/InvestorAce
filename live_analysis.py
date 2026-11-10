"""Current Yahoo facts and reproducible Python valuation scenarios.

Reported OCF minus cash capex is a leveraged cash-flow proxy, not certified
normalized FCFE. Its equity scenarios use cost of equity; no debt is deducted
again. Sources, dates and assumptions travel with every result.
"""
from __future__ import annotations

import copy
from datetime import datetime, timezone
from urllib.parse import quote as urlquote

import assessment
import autoscore
import equity_basis
from integrity import finite_number, positive_number


VERSION = 'dynamic-analysis-v1'
ALIASES = {
    'revenue': ('Total Revenue', 'Operating Revenue'),
    'operating_income': ('Operating Income', 'EBIT'),
    'net_income': ('Net Income', 'Net Income Common Stockholders'),
    'ebitda': ('EBITDA', 'Normalized EBITDA'),
    'depreciation': ('Depreciation And Amortization', 'Depreciation Amortization Depletion'),
    'diluted_shares': ('Diluted Average Shares',),
    'operating_cash_flow': ('Operating Cash Flow', 'Total Cash From Operating Activities'),
    'capex': ('Capital Expenditure', 'Capital Expenditures'),
    'fcf': ('Free Cash Flow',),
    'dividends': ('Cash Dividends Paid', 'Common Stock Dividend Paid'),
    'debt': ('Total Debt',),
    # Yahoo omits 'Total Debt' for companies without borrowings. Debt is part
    # of total liabilities, so that total is a sourced upper bound for it.
    'liabilities': ('Total Liabilities Net Minority Interest', 'Total Liabilities'),
    'cash': ('Cash And Cash Equivalents', 'Cash Cash Equivalents And Short Term Investments'),
    'shares': ('Ordinary Shares Number',),
    # Row names as yfinance 0.2.66 serves them (const.py keys through
    # utils.camel2title). Yahoo has no separate continuing-operations capex
    # row; the earlier names 'Cash Flow From Discontinued Operating
    # Activities' and 'Capital Expenditure From Continuing Operations' never
    # occur, so every discontinued line left the whole valuation unresolved.
    'net_income_common': ('Net Income Common Stockholders',),
    'preferred_earnings': ('Preferred Stock Dividends',),
    'preferred_paid': ('Preferred Stock Dividend Paid',),
    'preferred_outstanding': ('Preferred Stock', 'Preferred Stock Equity'),
    'common_dividends': ('Common Stock Dividend Paid',),
    'continuing_ocf': ('Cash Flow From Continuing Operating Activities',),
    'continuing_income': ('Net Income From Continuing Operation Net Minority Interest',),
    'discontinued_ocf': ('Cash From Discontinued Operating Activities',),
    'discontinued_investing': ('Cash From Discontinued Investing Activities',),
    'discontinued_cash': ('Cash Flow From Discontinued Operation',),
    'discontinued_income': ('Net Income Discontinuous Operations',),
}
# Discontinued amounts at or below this share of the window's net income and
# operating cash stay in the reported figures. Pfizer's legacy line was
# USD -5m over the nine months to September 2026 against USD 5,710m of net
# income, yet it withdrew Pfizer's signal from 6 November 2026.
DISCONTINUED_MATERIALITY = .05
DISCONTINUED_CASH = ('discontinued_ocf', 'discontinued_investing', 'discontinued_cash')
TABLES = {'g': autoscore.GROWTH, 'p': autoscore.PROFIT, 'c': autoscore.CASHGEN,
          'b': autoscore.BALANCE, 'v': autoscore.VALUE, 'r': autoscore.RETURNS,
          'd': autoscore.DILUTION}


def dcf_value(cash_flow, shares, discount_rate, growth, terminal_growth, years=5):
    """Equity cash-flow scenario, all amount/share units must match."""
    f, s, r = positive_number(cash_flow), positive_number(shares), positive_number(discount_rate)
    g, t = finite_number(growth), finite_number(terminal_growth)
    if (f is None or s is None or r is None or g is None or t is None or
            g <= -1 or t <= -1 or t >= r or type(years) is not int or not 1 <= years <= 30):
        return None
    try:
        cash = [f * (1 + g) ** year for year in range(1, years + 1)]
        value = sum(x / (1 + r) ** year for year, x in enumerate(cash, 1))
        value += cash[-1] * (1 + t) / (r - t) / (1 + r) ** years
        return finite_number(value / s)
    except (OverflowError, ZeroDivisionError):
        return None


def reverse_dcf(price, cash_flow, shares, discount_rate, terminal_growth, years=5):
    """Growth required by price under the stated scenario, not a forecast."""
    price = positive_number(price)
    if price is None:
        return None
    low, high = -.95, 1.
    a = dcf_value(cash_flow, shares, discount_rate, low, terminal_growth, years)
    b = dcf_value(cash_flow, shares, discount_rate, high, terminal_growth, years)
    if a is None or b is None or not a <= price <= b:
        return None
    for _ in range(100):
        mid = (low + high) / 2
        value = dcf_value(cash_flow, shares, discount_rate, mid, terminal_growth, years)
        if value is None:
            return None
        if value < price:
            low = mid
        else:
            high = mid
    return (low + high) / 2


def _frame(ticker, name, cutoff):
    try:
        frame = getattr(ticker, name)
        if frame is None or frame.empty:
            return None
        frame = frame.copy()
        keep = [c for c in frame.columns if c.date() <= cutoff.date()]
        return frame[sorted(keep, reverse=True)]
    except Exception:
        return None


def _value(frame, key, column):
    if frame is None or column not in frame.columns:
        return None
    index = {str(x).lower(): x for x in frame.index}
    for name in ALIASES[key]:
        if name.lower() in index:
            return finite_number(frame.loc[index[name.lower()], column])
    return None


def _total(frame, key, columns):
    vals = [_value(frame, key, c) for c in columns]
    return sum(vals) if vals and all(v is not None for v in vals) else None


def _cash(frame, columns):
    ocf = _total(frame, 'operating_cash_flow', columns)
    capex = [_value(frame, 'capex', c) for c in columns]
    capex = sum(abs(x) for x in capex) if capex and all(x is not None for x in capex) else None
    reported = _total(frame, 'fcf', columns)
    fcf = ocf - capex if ocf is not None and capex is not None else reported
    return ocf, capex, fcf


def _event_total(frame, key, columns):
    """Sum of an event row (discontinued operations); None when no period reports it.

    Yahoo leaves the row empty in periods without such an event, so an empty
    period counts as zero once any period of the window reports the row."""
    values = [_value(frame, key, c) for c in columns]
    return None if all(v is None for v in values) else sum(v or 0. for v in values)


def _material_discontinued(amounts, net_income, operating_cash):
    """Discontinued earnings or cash above 5% of the window's total, or with no total."""
    def large(amount, total):
        return amount not in (None, 0.) and (total in (None, 0.) or
                                             abs(amount) > DISCONTINUED_MATERIALITY * abs(total))
    cash = max((abs(amounts[k]) for k in DISCONTINUED_CASH if amounts[k] is not None), default=None)
    return large(amounts['discontinued_income'], net_income) or large(cash, operating_cash)


def _equity_row(cf, income, balance, dates, basis):
    """Only create metadata when the provider actually discloses a claim/scope row.

    A material discontinued business moves the window to continuing operations
    only when the provider separates its cash flows (a discontinued operating,
    investing or combined cash row) and reports continuing operating cash; the
    remaining investing rows, capex included, then belong to the continuing
    business. Without that separation the scope stays unresolved."""
    if not dates:
        return None
    paid = _total(cf, 'preferred_paid', dates)
    deduction = _total(income, 'preferred_earnings', dates)
    common = _total(income, 'net_income_common', dates)
    outstanding = _value(balance, 'preferred_outstanding', dates[0])
    amounts = {key: _event_total(income if key == 'discontinued_income' else cf, key, dates)
               for key in ('discontinued_income',) + DISCONTINUED_CASH}
    discontinued = any(v not in (None, 0.) for v in amounts.values())
    if all(x is None for x in (paid, deduction, common, outstanding)) and not discontinued:
        return None
    ocf, capex, reported = _cash(cf, dates)
    net_income, revenue = _total(income, 'net_income', dates), _total(income, 'revenue', dates)
    material = discontinued and _material_discontinued(amounts, net_income, ocf)
    scope = earnings_scope = 'REPORTED'
    if material:
        scope = earnings_scope = 'UNRESOLVED'
        separated = any(amounts[k] not in (None, 0.) for k in DISCONTINUED_CASH)
        continuing = _total(cf, 'continuing_ocf', dates)
        if continuing is None and amounts['discontinued_ocf'] is not None and ocf is not None:
            continuing = ocf - amounts['discontinued_ocf']
        if separated and continuing is not None and capex is not None:
            ocf, scope = continuing, 'CONTINUING'
        # A consolidated common-income row is not continuing common income;
        # the continuing parent income row is, before preferred deductions.
        common = None
        continuing_income = _total(income, 'continuing_income', dates)
        if continuing_income is not None:
            net_income, earnings_scope = continuing_income, 'CONTINUING'
    return dict(period=dates[0].date().isoformat(), basis=basis, scope=scope,
        earnings_scope=earnings_scope,
        # Reported revenue excludes discontinued operations (ASC 205-20, IFRS 5).
        revenue_scope=scope,
        operating_cash_flow=ocf, capex=capex, net_income=net_income,
        reported_fcf=reported,
        net_income_common=common, revenue=revenue,
        preferred_cash_paid=paid, preferred_earnings_deduction=deduction,
        preferred_outstanding=outstanding, has_discontinued_operations=discontinued,
        discontinued_material=material,
        discontinued_net_income=amounts['discontinued_income'],
        discontinued_operating_cash_flow=amounts['discontinued_ocf'],
        discontinued_investing_cash_flow=amounts['discontinued_investing'],
        discontinued_cash_flow=amounts['discontinued_cash'],
        common_dividends_paid=_total(cf, 'common_dividends', dates),
        dividends_total=_total(cf, 'dividends', dates), source='YAHOO_STATEMENT_ROWS')


def _annual_growth(frame, key):
    if frame is None or len(frame.columns) < 2:
        return None
    a, b = frame.columns[:2]
    av, bv = _value(frame, key, a), _value(frame, key, b)
    if av is None or bv is None or bv <= 0 or not 300 <= (a-b).days <= 400:
        return None
    return 100 * (av / bv - 1)


# Yahoo's sharesOutstanding counts only the quoted class of a multi-class
# company: GOOGL reads 5,888m, the Class A line of Alphabet's 10-Q cover
# (5,888m A + 827m B + 5,579m C = 12,294m on 21 Oct 2026), so its market
# value, P/E and FCF yield were computed on 48% of the company. META, NKE
# and TTD show smaller gaps of the same kind.
SHARE_CLASS_GAP = (1.05, 2.5)


def all_class_shares(listed, implied, diluted):
    """Whole-company share count when the listed class is only part of it.

    Two independent provider counts must both exceed the listed class by
    5-150%: the market-value-implied count (all classes at the quote) and
    the latest diluted average (EPS denominator, all classes). The smaller is
    used, so a stale or inflated source cannot overstate the count. A split
    after the latest quarter moves only the diluted average and is ignored,
    as is an ordinary-share count for an ADR (outside the band). None means
    keep the listed count."""
    listed, implied, diluted = (positive_number(x) for x in (listed, implied, diluted))
    if None in (listed, implied, diluted):
        return None
    low, high = SHARE_CLASS_GAP
    if low < implied / listed <= high and low < diluted / listed <= high:
        return min(implied, diluted)
    return None


def short_interest(info):
    """Exchange-reported short interest as Yahoo carries it; positioning, not scored.

    Yahoo reports US-listed short interest (FINRA settlement dates, twice a
    month). Venues without such reports return None, never zero."""
    shares = positive_number(info.get('sharesShort'))
    pct = finite_number(info.get('shortPercentOfFloat'))
    if shares is None and pct is None:
        return None
    stamp = positive_number(info.get('dateShortInterest'))
    try:
        date = datetime.fromtimestamp(stamp, timezone.utc).date().isoformat() if stamp else None
    except (ValueError, OverflowError, OSError):
        date = None
    prior = positive_number(info.get('sharesShortPriorMonth'))
    return dict(pct_float=100 * pct if pct is not None else None,
                days_to_cover=finite_number(info.get('shortRatio')), shares=shares,
                prior_month_shares=prior, settlement_date=date,
                change_pct=100 * (shares / prior - 1) if shares and prior else None,
                source='YAHOO_EXCHANGE_REPORTED')


# Minimum equity beta for the cost of equity. Tested on the 2026-11-01
# universe: only NVO (Buy -> Hold Positive) and SAN changed; the calibration
# cases WKL and OXY keep their labels.
BETA_FLOOR = 0.6


def earnings_event(info):
    """Next or latest earnings date as Yahoo carries it; estimates stay flagged."""
    def day(key):
        stamp = positive_number(info.get(key))
        try:
            return datetime.fromtimestamp(stamp, timezone.utc).date().isoformat() if stamp else None
        except (ValueError, OverflowError, OSError):
            return None
    start = day('earningsTimestampStart') or day('earningsTimestamp')
    if start is None:
        return None
    end = day('earningsTimestampEnd')
    return dict(date=start, date_end=end if end and end != start else None,
                estimated=bool(info.get('isEarningsDateEstimate')), source='YAHOO')


def last_earnings(fresh, previous, today):
    """Latest report date already past, remembered across nights.

    Yahoo replaces a past date with the next one soon after a report, so the
    cache keeps the last reported date to tell whether the data caught up."""
    dates = [(previous or {}).get('last_earnings')]
    for packet in (previous, fresh):
        dates.append(((packet or {}).get('earnings') or {}).get('date'))
    past = [d for d in dates if isinstance(d, str) and d <= today.isoformat()]
    return max(past) if past else None


def no_dividend(info):
    """True only when the provider explicitly reports a zero trailing dividend."""
    rate = finite_number(info.get('trailingAnnualDividendRate'))
    paid = finite_number(info.get('dividendRate'))
    return rate == 0 and not paid


def extract(ticker, symbol, *, as_of):
    """Collect an atomic financial packet; fiscal dates are not publication dates."""
    try:
        info = ticker.get_info() or {}
    except Exception:
        info = {}
    frames = {key: _frame(ticker, name, as_of) for key, name in (
        ('cf', 'cashflow'), ('income', 'income_stmt'), ('balance', 'balance_sheet'),
        ('qcf', 'quarterly_cashflow'), ('qincome', 'quarterly_income_stmt'),
        ('qbalance', 'quarterly_balance_sheet'))}
    cf, income = frames['cf'], frames['income']
    qcf, qi = frames['qcf'], frames['qincome']
    quarterly = sorted(set(qcf.columns).intersection(qi.columns), reverse=True) if qcf is not None and qi is not None else []
    quarter_dates = quarterly[:4]
    complete = len(quarter_dates) == 4 and all(60 <= (a-b).days <= 120
                                                for a, b in zip(quarter_dates, quarter_dates[1:]))
    if complete and _cash(qcf, quarter_dates)[2] is not None:
        selected_cf, selected_income, dates, basis = qcf, qi, quarter_dates, 'TTM'
    else:
        annual = sorted(set(cf.columns).intersection(income.columns), reverse=True) if cf is not None and income is not None else []
        selected_cf, selected_income, dates, basis = cf, income, annual[:1], 'FY'
    end = dates[0] if dates else None
    ocf, capex, fcf = _cash(selected_cf, dates)
    values = {key: _total(selected_income, key, dates) for key in
              ('revenue', 'operating_income', 'net_income', 'ebitda')}
    values.update(operating_cash_flow=ocf, capex=capex, fcf=fcf,
                  dividends=_total(selected_cf, 'dividends', dates),
                  depreciation=_total(selected_cf, 'depreciation', dates))
    dividends_basis = 'CASH_FLOW_STATEMENT' if values['dividends'] is not None else None
    if values['dividends'] is None and no_dividend(info):
        # The statement simply has no dividend row for non-payers; the provider
        # states a zero trailing dividend, so this is a sourced zero, not a guess.
        values['dividends'] = 0.
        dividends_basis = 'PROVIDER_ZERO_TRAILING_DIVIDEND'
    balance = next((b for b in (frames['qbalance'], frames['balance'])
                    if b is not None and end is not None and end in b.columns), None)
    values.update({key: _value(balance, key, end) for key in ('debt', 'cash', 'liabilities')})
    equity_rows = []
    current_equity = _equity_row(selected_cf, selected_income, balance, dates, basis)
    if current_equity:
        if dividends_basis == 'PROVIDER_ZERO_TRAILING_DIVIDEND':
            # This is a sourced common-share zero, independent of preferred cash.
            current_equity['common_dividends_paid'] = 0.
        equity_rows.append(current_equity)
    if cf is not None:
        for c in cf.columns[:5]:
            row = _equity_row(cf, income, frames['balance'], [c], 'FY')
            if row and (row['period'], row['basis']) != ((current_equity or {}).get('period'), basis):
                equity_rows.append(row)
    shares = positive_number(info.get('sharesOutstanding'))
    share_basis, shares_asof = 'YAHOO_CURRENT_SNAPSHOT_UNDATED', None
    if shares is None:
        for table in (frames['qbalance'], frames['balance']):
            if table is not None and len(table.columns):
                shares = positive_number(_value(table, 'shares', table.columns[0]))
                if shares is not None:
                    share_basis, shares_asof = 'BALANCE_SHEET_OUTSTANDING', table.columns[0].date().isoformat()
                    break
    listed_shares = shares
    implied = positive_number(info.get('impliedSharesOutstanding'))
    if implied is None:
        cap, quote_px = positive_number(info.get('marketCap')), positive_number(info.get('regularMarketPrice'))
        implied = cap / quote_px if cap and quote_px else None
    diluted = positive_number(_value(selected_income, 'diluted_shares', end)) if end is not None else None
    whole = all_class_shares(listed_shares, implied, diluted)
    if whole is not None and share_basis == 'YAHOO_CURRENT_SNAPSHOT_UNDATED':
        shares, share_basis = whole, 'ALL_CLASSES_MIN_IMPLIED_DILUTED'
    values['shares'] = shares
    previous_cf = _cash(cf, [cf.columns[1]])[2] if cf is not None and len(cf.columns) > 1 else None
    latest_cf = _cash(cf, [cf.columns[0]])[2] if cf is not None and len(cf.columns) else None
    annual_dates = list(cf.columns[:2]) if cf is not None else []
    comparable_fcf = (len(annual_dates) == 2 and 300 <= (annual_dates[0]-annual_dates[1]).days <= 400
                      and latest_cf is not None and previous_cf is not None and previous_cf > 0)
    cash_growth = 100 * (latest_cf / previous_cf - 1) if comparable_fcf else None
    stamp = positive_number(info.get('regularMarketTime'))
    try:
        quote_time = datetime.fromtimestamp(stamp, timezone.utc).isoformat() if stamp else None
    except (ValueError, OverflowError, OSError):
        quote_time = None
    return dict(schema=VERSION, fetched_at=as_of.isoformat(), symbol=symbol,
        financial_period=end.date().isoformat() if end is not None else None,
        period_ends=[c.date().isoformat() for c in dates], basis=basis, inputs=values,
        equity_periods=equity_rows,
        financial_currency=info.get('financialCurrency'), currency=info.get('currency'),
        beta=finite_number(info.get('beta')), quote_price=positive_number(info.get('regularMarketPrice')),
        quote_observed_at=quote_time, quote_type=info.get('quoteType'),
        short_interest=short_interest(info),
        dividends_basis=dividends_basis,
        earnings=earnings_event(info),
        shares_basis=share_basis, shares_asof=shares_asof,
        revenue_growth_pct=_annual_growth(income, 'revenue'),
        share_change_pct=_annual_growth(frames['balance'], 'shares'),
        annual_fcf_growth_pct=cash_growth,
        revenue_growth_periods=[c.date().isoformat() for c in list(income.columns[:2])] if income is not None else [],
        share_change_periods=[c.date().isoformat() for c in list(frames['balance'].columns[:2])]
            if frames['balance'] is not None else [],
        cash_flow_calculation='OCF_MINUS_ABS_CAPEX' if ocf is not None and capex is not None else 'YAHOO_REPORTED_FCF',
        annual_fcf_series=[dict(period=c.date().isoformat(), value=_cash(cf, [c])[2])
                           for c in list(cf.columns[:5])] if cf is not None else [],
        annual_net_income_series=[dict(period=c.date().isoformat(), value=_value(income, 'net_income', c))
                           for c in list(income.columns[:5])] if income is not None else [],
        annual_revenue_series=[dict(period=c.date().isoformat(), value=_value(income, 'revenue', c))
                           for c in list(income.columns[:5])] if income is not None else [],
        listed_class_shares=listed_shares, implied_shares=implied, diluted_average_shares=diluted,
        cash_growth_periods=[c.date().isoformat() for c in annual_dates],
        source_urls=[f'https://finance.yahoo.com/quote/{urlquote(symbol, safe="")}/{part}/'
                     for part in ('cash-flow', 'financials', 'balance-sheet', 'key-statistics')])


def prefer_primary(provider, primary, *, as_of):
    """Use a dated issuer packet, retaining live market data and later periods.

    Exact-year corrections remain authoritative when a provider advances to a
    later financial period. Neither source narrative nor analyst approval is
    treated as a numeric input.
    """
    if not primary:
        return provider
    published = assessment.timestamp(primary.get('published_at'))
    retrieved = assessment.timestamp(primary.get('fetched_at'))
    if not published or not retrieved or not published <= retrieved <= as_of:
        return provider
    if (primary.get('symbol') != provider.get('symbol') or
            primary.get('schema') != VERSION or not primary.get('source_urls') or
            primary.get('financial_currency') != primary.get('currency') or
            provider.get('currency') not in (None, primary.get('currency')) or
            provider.get('financial_currency') not in (None, primary.get('financial_currency'))):
        raise ValueError('Primary financial identity/currency/source mismatch')
    try:
        period = datetime.fromisoformat(primary['financial_period']).date()
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError('Invalid primary financial period') from exc
    if period > published.date():
        raise ValueError('Primary period postdates publication')
    inputs = primary.get('inputs') or {}
    ocf, capex, fcf = (finite_number(inputs.get(k)) for k in
                       ('operating_cash_flow', 'capex', 'fcf'))
    if (None in (ocf, capex, fcf) or capex < 0 or abs(ocf-capex-fcf) > 1. or
            positive_number(inputs.get('shares')) is None):
        raise ValueError('Invalid primary OCF/capex/share bridge')
    result = copy.deepcopy(provider)
    if (provider.get('financial_period') or '') <= primary['financial_period']:
        market = {k: provider[k] for k in
                  ('beta', 'quote_price', 'quote_observed_at', 'quote_type', 'short_interest', 'earnings') if k in provider}
        result.update(copy.deepcopy(primary))
        result.update(market)
        result['primary_current'] = True
    for key in ('annual_fcf_series', 'annual_net_income_series', 'annual_revenue_series'):
        series = {item['period']: copy.deepcopy(item) for item in provider.get(key, [])}
        for item in primary.get(key, []):
            series[item['period']] = copy.deepcopy(item)
        result[key] = sorted(series.values(), key=lambda x: x['period'], reverse=True)
    annual = result.get('annual_fcf_series', [])
    if len(annual) >= 2:
        a, b = annual[:2]
        av, bv = finite_number(a.get('value')), positive_number(b.get('value'))
        gap = (datetime.fromisoformat(a['period'])-datetime.fromisoformat(b['period'])).days
        result['annual_fcf_growth_pct'] = 100*(av/bv-1) if av is not None and bv and 300 <= gap <= 400 else None
        result['cash_growth_periods'] = [a['period'], b['period']]
    result['source_urls'] = list(dict.fromkeys(provider.get('source_urls', []) + primary['source_urls']))
    result['primary_source_published_at'] = primary['published_at']
    result['primary_warnings'] = primary.get('primary_warnings', [])
    if provider.get('equity_periods'):
        # Primary corrections win over optional Yahoo rows for the same periods.
        # Never rebuild corrected FCF from a superseded OCF/capex pair.
        rows = {(r['period'], r['basis']): copy.deepcopy(r) for r in provider['equity_periods']}
        for key, field in (('annual_fcf_series', 'reported_fcf'),
                           ('annual_net_income_series', 'net_income'),
                           ('annual_revenue_series', 'revenue')):
            for item in primary.get(key, []):
                identity = (item['period'], 'FY')
                row = rows.setdefault(identity, dict(period=item['period'], basis='FY', scope='REPORTED'))
                row[field] = item.get('value')
                row['source'] = 'PRIMARY_FINANCIAL_PACKET'
                if field == 'reported_fcf':
                    row.update(operating_cash_flow=None, capex=None)
                if field == 'net_income':
                    row['net_income_common'] = None
                if equity_basis.material_discontinued(row) or row.get('scope') == 'CONTINUING':
                    row['scope'] = primary.get('operating_scope', 'UNRESOLVED')
        if (provider.get('financial_period') or '') <= primary['financial_period']:
            identity = (primary['financial_period'], primary['basis'])
            row = rows.setdefault(identity, dict(period=identity[0], basis=identity[1], scope='REPORTED'))
            row.update({k: inputs.get(k) for k in ('operating_cash_flow', 'capex', 'net_income', 'revenue')})
            row.update(net_income_common=inputs.get('net_income_common'), reported_fcf=inputs.get('fcf'),
                       dividends_total=inputs.get('dividends'), common_dividends_paid=inputs.get('common_dividends_paid'),
                       source='PRIMARY_FINANCIAL_PACKET')
        result['equity_periods'] = list(rows.values())
    return result


def leverage_ebitda(inputs):
    """EBITDA for net debt / EBITDA, and its basis.

    EBITDA can never be below EBIT on one basis (D&A >= 0). Yahoo's EBITDA row
    is built from pre-tax income and carries unusual items that its Operating
    Income row excludes: Gilead's TTM to 2026-09-30 reads EBITDA 1.29bn against
    operating income 11.70bn, turning ~1.7x leverage into 15.3x, a balance score
    of 1.5 and a value-trap cap. When the row is below operating income, use
    operating income plus D&A from the same cash-flow periods, or operating
    income alone as a conservative floor (it understates EBITDA, never inflates
    it). A consistent provider EBITDA is used unchanged."""
    reported = finite_number(inputs.get('ebitda'))
    opinc = finite_number(inputs.get('operating_income'))
    # A missing row is treated like an inconsistent one: Salesforce's quarterly
    # EBITDA row came and went between builds on 1-4 Nov 2026 while operating
    # income stayed, so its balance score, macro fit and Buy label vanished
    # and returned. Operating income plus D&A is EBITDA by definition.
    if opinc is not None and opinc > 0 and (reported is None or reported < opinc):
        da = finite_number(inputs.get('depreciation'))
        if da is not None and da != 0:
            return opinc + abs(da), 'OPERATING_INCOME_PLUS_DA'
        return opinc, 'OPERATING_INCOME_FLOOR'
    value = positive_number(reported)
    return value, 'REPORTED_EBITDA' if value is not None else None


def calculate(facts, *, quote=None, risk_free, mrp, as_of, cushion_tolerance=.5):
    """Reprice frozen facts with current parameters; no network or stored scores."""
    facts = equity_basis.apply(facts, as_of=as_of)
    common_basis = facts.get('common_equity_basis') or {}
    current_common = common_basis.get('current')
    inputs = dict(facts.get('inputs') or {})
    warnings = ['Reported leveraged FCF proxy; sustainable cash flow has not been normalized.',
                'Five-year growth and terminal growth are scenario assumptions, not forecasts.']
    warnings.extend(facts.get('primary_warnings', []))
    if facts.get('shares_basis') == 'ALL_CLASSES_MIN_IMPLIED_DILUTED':
        warnings.append('The quoted line is one share class of several; valuation uses the whole-company count '
                        '(smaller of the market-value-implied and diluted average counts).')
    if facts.get('cash_flow_calculation') == 'YAHOO_REPORTED_FCF':
        warnings.append('OCF/capex bridge unavailable; cash flow uses Yahoo reported Free Cash Flow.')
    currency, financial_currency = facts.get('currency'), facts.get('financial_currency')
    factor = 1. if currency and financial_currency and currency == financial_currency else None
    if currency == 'GBp' and financial_currency == 'GBP':
        factor = 100.
    fx = facts.get('fx') or {}
    if factor is None and positive_number(fx.get('rate')) and fx.get('pair') == f'{financial_currency}{currency}':
        # A US-listed ADR quoted in USD on statements in DKK/EUR/CHF/CNY:
        # one statement-currency unit is worth `rate` quote-currency units.
        factor = positive_number(fx['rate'])
        warnings.append(f"Quote converted with the {fx['pair']} rate {factor:.6g} ({str(fx.get('observed_at'))[:10]}); "
                        'the reported share count is assumed to match the listed shares.')
    if factor is None:
        warnings.append('Quote and financial currencies are missing or incompatible; valuation suspended.')
    if financial_currency and financial_currency != 'USD':
        warnings.append('USD risk-free curve is a shared model assumption for this non-USD cash flow.')
    q = quote or dict(price=facts.get('quote_price'), observed_at=facts.get('quote_observed_at'))
    price = positive_number(q.get('price'))
    observed = assessment.timestamp(q.get('observed_at'))
    if observed is None or not 0 <= (as_of-observed).total_seconds() <= 96*3600:
        price = None
        warnings.append('No sufficiently recent dated quote; price-dependent outputs suspended.')
    inputs['quote_price'] = price
    beta, rf, premium = (finite_number(x) for x in (facts.get('beta'), risk_free, mrp))
    reported_beta = beta
    if beta is not None and beta < BETA_FLOOR:
        # A provider beta near zero (NVO 0.38, WKL 0.18) would value equity
        # almost at the risk-free rate; equity risk is never that low.
        beta = BETA_FLOOR
        warnings.append(f'Reported beta {reported_beta:.2f} is below the {BETA_FLOOR:.1f} floor; '
                        'the cost of equity uses the floor.')
    rate = rf + beta * premium if None not in (rf, beta, premium) else None
    if rate is None or not 0 < rate < 1:
        rate = None
        warnings.append('Valid cost-of-equity inputs unavailable; valuation suspended.')
    fcf, shares = finite_number(inputs.get('fcf')), positive_number(inputs.get('shares'))
    if current_common is not None:
        fcf = current_common['common_fcf']
        inputs['common_fcf'] = fcf
        inputs['common_net_income'] = current_common['common_net_income']
        warnings.append('Common-equity bridge uses period-matched preferred cash payments and earnings deductions; raw inputs are retained.')
        bridged = [current_common] + list(common_basis.get('annual') or [])[:5]
        if any(r.get('preferred_cash_basis') == 'DECLARED_STABLE_BALANCE' for r in bridged):
            warnings.append('Preferred cash dividends are not reported separately; the same-window declared '
                            'dividend on an unchanged preferred balance is deducted.')
        if any(r.get('has_discontinued_operations') and r.get('discontinued_material') is False for r in bridged):
            warnings.append('Discontinued operations at or below 5% of net income and operating cash '
                            'stay in the reported figures.')
        if current_common.get('scope') == 'CONTINUING':
            warnings.append('Cash flow and earnings use continuing operations; the disposed business is excluded.')
        if common_basis.get('current_window_open'):
            warnings.append('The current window lacks a matched common-equity bridge; current cash ratios are '
                            'unknown and the cycle valuation uses the bridged years.')
    valuation_fcf = fcf
    policy = 'REPORTED_FCF_PROXY'
    cash_cycle_periods = []
    if facts.get('midcycle'):
        # Yahoo often includes an empty oldest column. Use the contiguous
        # complete prefix; never jump across a missing intervening year.
        annual = []
        for item in (common_basis.get('annual_fcf_series', facts.get('annual_fcf_series')) or [])[:5]:
            if finite_number(item.get('value')) is None:
                break
            annual.append(item)
        values = [finite_number(item.get('value')) for item in annual]
        dates = [item.get('period') for item in annual]
        aligned = len(values) >= 3 and all(x is not None for x in values)
        try:
            stamps = [datetime.fromisoformat(x) for x in dates]
            aligned = aligned and all(300 <= (a-b).days <= 400 for a,b in zip(stamps,stamps[1:]))
        except (TypeError, ValueError):
            aligned = False
        valuation_fcf = sum(values)/len(values) if aligned else None
        cash_cycle_periods = dates if aligned else []
        policy = 'MIDCYCLE_MEAN_PROXY'
        warnings.append('Commodity value uses a multi-year reported cash-flow mean; acquisitions and normalization still require review.')
    conflicts = copy.deepcopy(facts.get('valuation_input_conflicts') or [])
    if conflicts:
        # A known invalid perimeter/senior-claim bridge is not a pending
        # approval. Keep raw reported facts, but do not capitalise them as
        # common-equity cash flow or silently replace them with an estimate.
        inputs['rejected_valuation_fcf'] = valuation_fcf
        valuation_fcf, policy = None, 'BLOCKED_INPUT_CONFLICT'
        warnings.extend('Valuation blocked: ' + item['reason'] for item in conflicts)
    inputs['valuation_fcf'] = valuation_fcf
    usable = valuation_fcf is not None and valuation_fcf > 0 and shares is not None and rate is not None and factor is not None
    ngv = valuation_fcf / shares / rate * factor if usable else None
    historical = finite_number(facts.get('annual_fcf_growth_pct'))
    if common_basis:
        annual = common_basis['annual_fcf_series']
        historical = None
        # Growth never compares two business perimeters (a continuing year
        # against a year that still holds the sold business).
        scopes = {r.get('scope', 'REPORTED') for r in (common_basis.get('annual') or [])[:2]}
        if len(annual) >= 2 and len(scopes) == 1:
            a, b = annual[:2]
            av, bv = finite_number(a['value']), positive_number(b['value'])
            gap = (datetime.fromisoformat(a['period'])-datetime.fromisoformat(b['period'])).days
            historical = 100*(av/bv-1) if av is not None and bv and 300 <= gap <= 400 else None
    growth = max(-.10, min(.15, historical / 100)) if historical is not None else 0.
    if facts.get('midcycle'):
        growth = 0.
    if historical is None:
        warnings.append('No comparable positive annual FCF growth; base growth assumes zero.')
    terminal = min(.02, rate - .01) if rate is not None else None
    terminal = max(0., terminal) if terminal is not None else None
    scenarios = []
    for name, g in [('bear', max(-.20, growth-.05)), ('base', growth), ('bull', min(.20, growth+.05))]:
        value = dcf_value(valuation_fcf, shares, rate, g, terminal, 5) if usable else None
        scenarios.append(dict(name=name, growth_pct=100*g,
                              value_per_share=value * factor if value is not None else None))
    reverse = reverse_dcf(price/factor, valuation_fcf, shares, rate, terminal, 5) if usable and price else None
    reverse_bound = None
    if reverse is None and usable and price:
        # Outside the solver's -95%..+100% bracket the required growth is still
        # known to lie beyond that edge; keep the edge as a flagged bound.
        floor = dcf_value(valuation_fcf, shares, rate, -.95, terminal, 5)
        ceiling = dcf_value(valuation_fcf, shares, rate, 1., terminal, 5)
        if ceiling is not None and price/factor > ceiling:
            reverse, reverse_bound = 1., 'ABOVE_100_PCT'
        elif floor is not None and price/factor < floor:
            reverse, reverse_bound = -.95, 'BELOW_MINUS_95_PCT'
        if reverse_bound:
            warnings.append('Price implies growth beyond the reverse-DCF range ('+reverse_bound
                            +'); the range edge is used as a bound.')
    rev = positive_number(inputs.get('revenue'))
    cash_revenue = positive_number(current_common.get('comparable_revenue')) if current_common else rev
    opinc = finite_number(inputs.get('operating_income'))
    ebitda, leverage_basis = leverage_ebitda(inputs)
    if leverage_basis in ('OPERATING_INCOME_PLUS_DA', 'OPERATING_INCOME_FLOOR'):
        warnings.append(('Provider EBITDA is missing; ' if finite_number(inputs.get('ebitda')) is None else
                         'Provider EBITDA is below operating income, so it includes non-operating or unusual items; ')
                        + ('leverage uses operating income plus depreciation and amortization.'
                           if leverage_basis == 'OPERATING_INCOME_PLUS_DA' else
                           'leverage uses operating income as a conservative floor.'))
    inputs['leverage_ebitda'] = ebitda
    debt, cash = finite_number(inputs.get('debt')), finite_number(inputs.get('cash'))
    market_cap = price * shares / factor if price and shares and factor else None
    earnings = finite_number(inputs.get('net_income'))
    common_earnings = current_common['common_net_income'] if current_common else earnings
    valuation_earnings = common_earnings
    if facts.get('midcycle'):
        years = []
        for item in (common_basis.get('annual_net_income_series', facts.get('annual_net_income_series')) or [])[:5]:
            if finite_number(item.get('value')) is None:
                break
            years.append(item)
        by_period = {item.get('period'):finite_number(item.get('value')) for item in years}
        corresponding = [by_period.get(period) for period in cash_cycle_periods]
        aligned = len(corresponding) >= 3 and all(value is not None for value in corresponding)
        valuation_earnings = sum(corresponding)/len(corresponding) if aligned else None
        if not aligned:
            warnings.append('Commodity earnings multiple unavailable: earnings and cash cycle periods do not align.')
    earnings_basis = 'CYCLE_MEAN' if facts.get('midcycle') else 'REPORTED_NET_INCOME'
    if (not facts.get('midcycle') and valuation_earnings is not None and valuation_earnings > 0
            and opinc is not None and valuation_earnings > opinc):
        # Net income above pre-tax operating income needs non-operating gains
        # or tax benefits: Alphabet's TTM reads 235.7bn against 157.0bn, from
        # marks on private stakes, and scored P/E 7.0 = 10 points. The multiple
        # uses operating income instead; it never raises a P/E score.
        valuation_earnings, earnings_basis = opinc, 'CAPPED_AT_OPERATING_INCOME'
        warnings.append('Net income exceeds operating income (non-operating gains or tax benefits); '
                        'the earnings multiple uses operating income.')
    if conflicts:
        inputs['rejected_valuation_net_income'] = valuation_earnings
        valuation_earnings, earnings_basis = None, 'BLOCKED_INPUT_CONFLICT'
    inputs['valuation_net_income'] = valuation_earnings
    cycle_growth = None
    if facts.get('midcycle') and cash_cycle_periods:
        # A producer's one-year revenue change is mostly the commodity price
        # (CNX +49%, AG +124% in FY2025). Growth uses the same years as the
        # cash-flow and earnings averages, newest first.
        # Yahoo's cash-flow table can hold one more year than its income
        # statement; the newest contiguous run of at least three years is used.
        revenue = {item.get('period'): positive_number(item.get('value'))
                   for item in common_basis.get('annual_revenue_series', facts.get('annual_revenue_series')) or []}
        path = []
        for period in cash_cycle_periods:
            if revenue.get(period) is None:
                break
            path.append(revenue[period])
        if len(path) >= 3:
            cycle_growth = 100 * ((path[0] / path[-1]) ** (1 / (len(path) - 1)) - 1)
    dividends = finite_number(inputs.get('dividends'))
    if current_common is not None:
        dividends = current_common['common_dividends_paid']
    share_change = finite_number(facts.get('share_change_pct'))
    div_yield = abs(dividends) / market_cap * 100 if dividends is not None and market_cap else None
    buybacks = max(0., -share_change) if share_change is not None else None
    returns = div_yield + buybacks if div_yield is not None and buybacks is not None else None
    metrics = dict(revenue_growth_pct=facts.get('revenue_growth_pct'),
        operating_margin_pct=100*opinc/rev if opinc is not None and rev else None,
        fcf_margin_pct=100*fcf/cash_revenue if fcf is not None and cash_revenue else None,
        net_debt=debt-cash if debt is not None and cash is not None else None,
        net_debt_ebitda=(debt-cash)/ebitda if None not in (debt,cash) and ebitda else None,
        fcf_yield_pct=100*valuation_fcf/market_cap if valuation_fcf is not None and market_cap else None,
        shareholder_yield_pct=returns, share_change_pct=share_change,
        fcf_growth_pct=historical, market_cap=market_cap,
        reported_pe=market_cap/earnings if market_cap and earnings is not None and earnings > 0 else None,
        valuation_pe=market_cap/valuation_earnings if market_cap and valuation_earnings is not None and valuation_earnings > 0 else None,
        earnings_yield_pct=100*valuation_earnings/market_cap if market_cap and valuation_earnings is not None else None,
        cash_conversion_pct=100*fcf/common_earnings if fcf is not None and common_earnings is not None and common_earnings > 0 else None,
        cycle_revenue_growth_pct=cycle_growth,
        cover_pct=100*ngv/price if ngv is not None and price else None)
    raw = dict(zip(('g','p','c','b','v','r','d'), (metrics[k] for k in (
        'revenue_growth_pct','operating_margin_pct','fcf_margin_pct','net_debt_ebitda',
        'fcf_yield_pct','shareholder_yield_pct','share_change_pct'))))
    components = {key: autoscore._band(value, TABLES[key], default=None) for key,value in raw.items()}
    cover = ngv/price if ngv is not None and price else None
    implied = rate*(1-cover)/(1+cover*rate) if cover is not None and rate else None
    # Annual historical cash growth is descriptive; use the original metric
    # type guard and retain a source-period label in the overlay.
    cushion = (historical - 100*implied if historical is not None and implied is not None
               and not facts.get('midcycle') else None)
    # Preserve the engine's original rounding tolerance: a small negative
    # cushion is flat, while autoscore's generic helper penalizes below zero.
    penalty_cushion = cushion if cushion is not None and cushion < -cushion_tolerance else None
    components['pr'] = autoscore.priced_in_from_cover(metrics['cover_pct'], penalty_cushion)
    complete = all(components.get(key) is not None for key in assessment.WEIGHTS)
    score = sum(components[key]*weight for key,weight in assessment.WEIGHTS.items()) if complete else None
    explanation = [dict(key=key, label=assessment.LABELS[key], value=components[key],
        nominal_weight=weight, effective_weight=weight if components[key] is not None else 0.,
        contribution=components[key]*weight if components[key] is not None else None,
        source='Calculated from reported financial inputs and a dated primary common-equity bridge' if common_basis.get('source_urls') else
            'Calculated from dated primary financial inputs' if facts.get('primary_current') else
            'Calculated from dated yfinance financial inputs') for key,weight in assessment.WEIGHTS.items()]
    overlay = dict(fcf=valuation_fcf/1e6 if valuation_fcf is not None and valuation_fcf > 0 and factor else None,
        fcf_ttm=fcf/1e6 if fcf is not None and facts.get('basis')=='TTM' else None,
        shares=shares/1e6 if shares else None, sub=tuple(components[k] for k in ('g','p','c','b','v','r'))
            if all(components[k] is not None for k in ('g','p','c','b','v','r')) else None,
        draft_components={k:components[k] for k in ('g','p','c','b','v','r')},
        dil=components['d'], pr=components['pr'], deliver=historical, deliver_basis='CASH_FLOW',
        dl='reported annual FCF growth', built='primary-dynamic' if facts.get('primary_current') else 'yfinance-dynamic',
        normalization_status='REVIEW_REQUIRED', cash_flow_basis='LEVERED_FCF_PROXY',
        discount_rate_basis='COST_OF_EQUITY', financial_period=facts.get('financial_period'),
        financial_published_at=facts.get('published_at'), financial_retrieved_at=facts.get('fetched_at'),
        shares_asof=facts.get('shares_asof'), shares_basis=facts.get('shares_basis'),
        score_fixed=None, fundamentals_refresh='PRIMARY_DYNAMIC' if facts.get('primary_current') else 'YFINANCE_DYNAMIC')
    return dict(schema=VERSION, status='COMPLETE' if complete else 'PARTIAL', as_of=as_of.isoformat(),
        fetched_at=facts.get('fetched_at'), financial_period=facts.get('financial_period'),
        basis=facts.get('basis'), currency=currency, financial_currency=financial_currency,
        inputs=inputs, metrics=metrics, components=components, model_score=score,
        metric_periods=dict(cash_flow=facts.get('period_ends', []),
            fcf_growth=facts.get('cash_growth_periods', []),
            revenue_growth=facts.get('revenue_growth_periods', []),
            share_change=facts.get('share_change_periods', [])),
        annual_fcf_series=facts.get('annual_fcf_series', []),
        common_equity_basis=common_basis or None,
        positioning=dict(short_interest=facts.get('short_interest')),
        events=dict(earnings=facts.get('earnings'), last_reported=facts.get('last_earnings')),
        quote_observed_at=q.get('observed_at'), warnings=warnings, source_urls=facts.get('source_urls',[]),
        parameters=dict(discount_rate_pct=100*rate if rate else None, beta=beta,
            reported_beta=reported_beta, beta_floor=BETA_FLOOR,
            currency_factor=factor,
            cash_flow_policy=policy,
            cash_flow_calculation=facts.get('cash_flow_calculation'),
            leverage_ebitda_basis=leverage_basis, earnings_basis=earnings_basis,
            shares_basis=facts.get('shares_basis'),
            common_equity_scope=current_common.get('scope') if current_common else None,
            preferred_cash_basis=current_common.get('preferred_cash_basis') if current_common else None,
            cushion_tolerance_pp=cushion_tolerance,
            risk_free_pct=100*rf if rf is not None else None, market_premium_pct=100*premium if premium is not None else None,
            discount_rate_basis='COST_OF_EQUITY', cash_flow_basis='LEVERED_FCF_PROXY',
            growth_rate_pct=100*growth, terminal_growth_pct=100*terminal if terminal is not None else None,
            horizon_years=5),
        valuation=dict(ngv_per_share=ngv, dcf_per_share=scenarios[1]['value_per_share'],
            reverse_dcf_growth_pct=100*reverse if reverse is not None else None,
            reverse_dcf_bound=reverse_bound, scenarios=scenarios),
        overlay=overlay, score_explanation=dict(schema='score-explanation-v1', status='DECOMPOSED',
            total=score, components=explanation, denominator=1.,
            sum_contributions=score, reconciles=True if complete else None),
        valuation_input_conflicts=conflicts,
        review_status='REVIEW_REQUIRED', can_approve=False)


def analyze(ticker, symbol, *, quote=None, risk_free, mrp, as_of=None):
    as_of = as_of or datetime.now(timezone.utc)
    if as_of.tzinfo is None:
        raise ValueError('Analysis cutoff requires a timezone')
    facts = extract(ticker, symbol, as_of=as_of)
    return calculate(facts, quote=quote, risk_free=risk_free, mrp=mrp, as_of=as_of)
