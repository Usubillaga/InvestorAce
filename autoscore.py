#!/usr/bin/env python3
"""autoscore.py · automatic mechanical score draft for InvestorAce."""
from __future__ import annotations

import math
import sys
import yfinance as yf

def _band(x, table, default=5.0):
    if x is None:
        return default
    try:
        x = float(x)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(x):
        return default
    for hi, score in table:
        if x < hi:
            return score
    return table[-1][1]

GROWTH = [(0,2.0),(5,4.0),(10,5.5),(20,7.0),(40,8.5),(1e9,9.5)]
PROFIT = [(0,2.0),(10,4.0),(20,6.0),(30,7.5),(45,9.0),(1e9,9.5)]
CASHGEN = [(0,1.5),(5,4.0),(12,6.0),(20,7.5),(30,9.0),(1e9,9.5)]
BALANCE = [(0,9.5),(1,8.0),(2,7.0),(3,6.0),(4,4.5),(5,3.0),(1e9,1.5)]
VALUE = [(1,1.5),(2,3.0),(3,4.5),(4.5,6.0),(7,7.5),(1e9,9.0)]
RETURNS = [(0.01,1.0),(1,4.0),(2.5,6.0),(4,7.5),(1e9,9.0)]
DILUTION = [(-4,9.5),(-1,8.5),(0.5,7.0),(2,5.5),(5,3.5),(10,2.0),(1e9,0.5)]

def priced_in_from_cover(cover_pct, cushion=None):
    if cover_pct is None:
        return None
    pr = _band(cover_pct, [(15,1.5),(25,2.5),(35,3.0),(45,4.5),(60,5.5),
                           (75,7.0),(90,8.0),(100,9.0),(1e9,9.5)])
    if cushion is not None and cushion < 0:
        pr = max(1.0, pr - 2.0)
    return round(pr, 1)

CLOCK_GUESS = {
    "Pharma":"CLOCK","Biotech":"CLOCK","Animal Health":"CLOCK","Utilities":"CLOCK",
    "Materials":"CLOCK","Energy":"DIV","Staples":"DIV","Restaurant":"DIV",
    "Health Ins":"DIV","MedTech":"DIV","Media":"DIV",
}

def _finite(x):
    if isinstance(x, bool):
        return None
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None

def _fin(tk):
    out = dict(
        fcf=None, shares=None, rev=None, rev_prev=None, opinc=None, ebitda=None,
        netdebt=None, div_yield=None, price=None, cur=None, sector="", name="",
        lo=None, hi=None, shares_prev=None, periods={}
    )

    fi = {}
    try:
        fi = dict(tk.fast_info) or {}
    except Exception:
        pass

    out["price"] = _finite(fi.get("last_price"))
    out["cur"] = str(fi.get("currency") or "")
    out["shares"] = _finite(fi.get("shares"))

    for lo_k, hi_k in (("year_low","year_high"),("yearLow","yearHigh"),
                       ("fiftyTwoWeekLow","fiftyTwoWeekHigh")):
        lo, hi = _finite(fi.get(lo_k)), _finite(fi.get(hi_k))
        if lo is not None and hi is not None:
            out["lo"], out["hi"] = lo, hi
            break

    info = {}
    try:
        info = tk.get_info() or {}
    except Exception:
        pass

    out["sector"] = info.get("sector","") or ""
    out["name"] = info.get("longName","") or ""
    dy = _finite(info.get("dividendYield"))
    # A missing distribution is unknown, and a positive untagged yield has
    # ambiguous fraction/percentage units. Do not invent zero or multiply it.
    out["div_yield"] = 0.0 if dy == 0 else None
    annual_dividend = _finite(info.get('dividendRate'))
    if (annual_dividend is not None and annual_dividend >= 0 and out['price']
            and out['cur'] == info.get('currency') and out['cur'] not in ('GBp', 'GBP')):
        out['div_yield'] = 100 * annual_dividend / out['price']

    if out["shares"] is None:
        out["shares"] = _finite(info.get("sharesOutstanding"))

    def rows(df, *names):
        if df is None or getattr(df, "empty", True):
            return None
        idx = {str(i).strip().lower(): i for i in df.index}
        for n in names:
            if n in idx:
                return df.loc[idx[n]].sort_index(ascending=False)
        return None

    def window(row, n=4, start=0, basis='TTM'):
        if row is None or len(row) < start + n:
            return None, None
        part = row.iloc[start:start+n]
        vals = [_finite(x) for x in part]
        try:
            dates = [x.date() for x in part.index]
            gaps = [(a-b).days for a, b in zip(dates, dates[1:])]
        except (AttributeError, TypeError):
            return None, None
        if any(x is None for x in vals) or any(not 60 <= gap <= 120 for gap in gaps):
            return None, None
        return sum(vals), [basis, *[day.isoformat() for day in dates]]

    def save(key, pair):
        out[key], out['periods'][key] = pair

    # Cash flow: TTM from four quarterly observations.
    try:
        qcf = tk.quarterly_cashflow
        f = rows(qcf, "free cash flow")
        if f is not None:
            save('fcf', window(f))
        if out["fcf"] is None:
            o = rows(qcf, "operating cash flow", "total cash from operating activities")
            c = rows(qcf, "capital expenditure", "capital expenditures")
            if o is not None and c is not None:
                ov, op = window(o)
                cv, cp = window(c.abs())
                if ov is not None and cv is not None and op == cp:
                    save('fcf', (ov-cv, op))
    except Exception:
        pass

    try:
        qis = None
        for attr in ("quarterly_income_stmt", "quarterly_financials"):
            try:
                cand = getattr(tk, attr, None)
                if cand is not None and not cand.empty:
                    qis = cand
                    break
            except Exception:
                continue

        r = rows(qis, "total revenue", "operating revenue")
        save('rev', window(r))
        whole, _ = window(r, n=8)
        if whole is not None:
            save('rev_prev', window(r, start=4))
        ais = getattr(tk, 'income_stmt', None)
        if ais is None or ais.empty:
            ais = getattr(tk, 'financials', None)
        if out['rev'] is None:
            ar = rows(ais, 'total revenue', 'operating revenue')
            save('rev', window(ar, n=1, basis='FY'))
            if ar is not None and len(ar) >= 2 and 300 <= (ar.index[0]-ar.index[1]).days <= 400:
                save('rev_prev', window(ar, n=1, start=1, basis='FY'))

        oi = rows(qis, "operating income", "ebit", "total operating income as reported")
        save('opinc', window(oi))
        if (out['periods'].get('rev') or [None])[0] == 'FY':
            save('opinc', window(rows(ais, 'operating income', 'ebit'), n=1, basis='FY'))

        eb = rows(qis, "ebitda", "normalized ebitda")
        save('ebitda', window(eb))
    except Exception:
        pass

    try:
        bs = tk.quarterly_balance_sheet
        debt = rows(bs, "total debt")
        cash = rows(bs, "cash and cash equivalents",
                    "cash cash equivalents and short term investments")
        debt_v = _finite(debt.iloc[0]) if debt is not None else None
        cash_v = _finite(cash.iloc[0]) if cash is not None else None
        if debt_v is not None and cash_v is not None:
            out["netdebt"] = debt_v - cash_v
            out['periods']['netdebt'] = debt.index[0].date().isoformat()

        shares_row = rows(bs, "ordinary shares number", "share issued")
        if shares_row is not None and len(shares_row) >= 5:
            a, b = _finite(shares_row.iloc[0]), _finite(shares_row.iloc[4])
            if a is not None and b is not None and b != 0:
                out["shares_prev"] = b
    except Exception:
        pass

    return out


def auto_row(symbol, r=0.080):
    """Return a DATA-ready automatic row."""
    tk = yf.Ticker(symbol)
    f = _fin(tk)
    warn = []

    if f["fcf"] is None or f["shares"] is None or f["shares"] <= 0:
        return None, ["no usable cash flow or share count — cannot build NGV"]

    fcf_m = f["fcf"] / 1e6
    sh_m = f["shares"] / 1e6
    rev_g = 100 * (f["rev"] / f["rev_prev"] - 1) if f["rev"] is not None and f["rev_prev"] else None
    periods = f.get('periods', {})
    def same_period(a, b):
        return periods.get(a) is not None and periods.get(a) == periods.get(b)
    op_m = 100 * f["opinc"] / f["rev"] if f["opinc"] is not None and f["rev"] and same_period('opinc', 'rev') else None
    fcf_m_pct = 100 * f["fcf"] / f["rev"] if f["rev"] and same_period('fcf', 'rev') else None
    balance_aligned = periods.get('netdebt') is not None and periods['netdebt'] == (periods.get('ebitda') or [None, None])[1]
    nd_e = f["netdebt"] / f["ebitda"] if f["netdebt"] is not None and f["ebitda"] is not None and f['ebitda'] > 0 and balance_aligned else None
    mcap = f["price"] * f["shares"] if f["price"] and f["shares"] else None
    fcf_y = 100 * f["fcf"] / mcap if mcap else None
    sh_ch = 100 * (f["shares"] / f["shares_prev"] - 1) if f["shares_prev"] else None
    buyb = max(0.0, -sh_ch) if sh_ch is not None else None
    tot_y = f['div_yield'] + buyb if f['div_yield'] is not None and buyb is not None else None

    def category(value, table):
        result = _band(value, table, default=None)
        return round(result, 1) if result is not None else None

    sub = (
        category(rev_g, GROWTH),
        category(op_m, PROFIT),
        category(fcf_m_pct, CASHGEN),
        category(nd_e, BALANCE),
        category(fcf_y, VALUE),
        category(tot_y, RETURNS),
    )
    dil = category(sh_ch, DILUTION)
    draft_components = dict(zip(('g', 'p', 'c', 'b', 'v', 'r'), sub))
    if any(value is None for value in sub) or dil is None:
        sub = None

    ngv = (fcf_m / sh_m) / r
    cover = 100 * ngv / f["price"] if f["price"] else None
    # Revenue growth is descriptive, not a cash-flow-growth forecast. Do not
    # persist a proxy-derived penalty that could survive a missing live quote.
    pr = priced_in_from_cover(cover)

    if fcf_m <= 0:
        warn.append(
            f"FCF non-positive ({fcf_m:,.1f}m) — NGV must be disabled and a model-specific na= reason used"
        )
        row_fcf = None
        na_reason = (
            f"FCF non-positive ({fcf_m:,.1f}m from Yahoo); "
            "NGV intentionally disabled until a model-appropriate metric is supplied"
        )
    else:
        row_fcf = round(fcf_m, 1)
        na_reason = None

    if rev_g is None:
        warn.append("no comparable revenue history — growth remains unknown")
    if nd_e is None:
        warn.append("no usable net-debt/EBITDA — balance sheet remains unknown")
    warn.append("deliver is a REVENUE_PROXY; no cash-flow cushion is computed. "
                "Declare CASH_FLOW only for a sourced cash-flow-growth measure.")
    warn.append(f'clock guessed from sector "{f["sector"]}" — confirm CLOCK / CONC / DIV by hand.')

    row = dict(
        yf=symbol,
        fcf=row_fcf,
        shares=round(sh_m, 2),
        r=r,
        cur=("GBp" if symbol.endswith(".L") and f["cur"].upper() == "GBP" else f["cur"] or "USD"),
        deliver=round(rev_g, 1) if rev_g is not None else None,
        deliver_basis='REVENUE_PROXY',
        dl="revenue growth (PROXY)",
        sub=sub,
        draft_components=draft_components,
        draft_periods=periods,
        pr=pr,
        dil=dil,
        clock=CLOCK_GUESS.get(f["sector"], "CONC"),
        ins="NOT CHECKED",
        held=False,
        sector=f["sector"],
        built="auto",
        normalization_status='REVIEW_REQUIRED',
        sanity=(round(f["lo"] * .5, 2), round(f["hi"] * 2, 2)) if f["lo"] is not None and f["hi"] is not None else None,
    )
    if na_reason:
        row["na"] = na_reason
    return row, warn


if __name__ == "__main__":
    sym = sys.argv[1] if len(sys.argv) > 1 else "ASML.AS"
    row, warn = auto_row(sym)
    if row is None:
        print("FAILED:", warn)
        raise SystemExit(1)
    print(repr(row))
    for w in warn:
        print("!", w)

