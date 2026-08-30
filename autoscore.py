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
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None

def _fin(tk):
    out = dict(
        fcf=None, shares=None, rev=None, rev_prev=None, opinc=None, ebitda=None,
        netdebt=None, div_yield=None, price=None, cur=None, sector="", name="",
        lo=None, hi=None, shares_prev=None
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
    if dy is None:
        out["div_yield"] = 0.0
    else:
        out["div_yield"] = dy * (100 if dy < 1 else 1)

    if out["shares"] is None:
        out["shares"] = _finite(info.get("sharesOutstanding"))

    def rows(df, *names):
        if df is None or getattr(df, "empty", True):
            return None
        idx = {str(i).strip().lower(): i for i in df.index}
        for n in names:
            if n in idx:
                return df.loc[idx[n]]
        return None

    def series_values(row, n):
        if row is None:
            return []
        vals = []
        for x in row.iloc[:n]:
            v = _finite(x)
            if v is not None:
                vals.append(v)
        return vals

    # Cash flow: TTM from four quarterly observations.
    try:
        qcf = tk.quarterly_cashflow
        f = rows(qcf, "free cash flow")
        if f is not None:
            vals = series_values(f, 4)
            if len(vals) >= 4:
                out["fcf"] = sum(vals[:4])
        if out["fcf"] is None:
            o = rows(qcf, "operating cash flow", "total cash from operating activities")
            c = rows(qcf, "capital expenditure", "capital expenditures")
            if o is not None and c is not None:
                pairs = []
                for a, b in zip(o.iloc[:4], c.iloc[:4]):
                    a, b = _finite(a), _finite(b)
                    if a is not None and b is not None:
                        pairs.append((a,b))
                if len(pairs) >= 4:
                    out["fcf"] = sum(a+b for a,b in pairs[:4])
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
        if r is not None and len(r) >= 8:
            cur4 = [_finite(x) for x in r.iloc[:4]]
            prev4 = [_finite(x) for x in r.iloc[4:8]]
            if all(x is not None for x in cur4 + prev4):
                out["rev"], out["rev_prev"] = sum(cur4), sum(prev4)

        if out["rev"] is None and r is not None and len(r) >= 4:
            vals = [_finite(x) for x in r.iloc[:4]]
            if all(x is not None for x in vals):
                out["rev"] = sum(vals)

        if out["rev_prev"] is None:
            try:
                ais = getattr(tk, "income_stmt", None)
                if ais is None or ais.empty:
                    ais = getattr(tk, "financials", None)
                ar = rows(ais, "total revenue", "operating revenue")
                if ar is not None and len(ar) >= 2:
                    a0, a1 = _finite(ar.iloc[0]), _finite(ar.iloc[1])
                    if a0 is not None and a1 is not None and a1 != 0:
                        if out["rev"] is None:
                            out["rev"] = a0
                        out["rev_prev"] = a1
            except Exception:
                pass

        oi = rows(qis, "operating income", "ebit", "total operating income as reported")
        if oi is not None:
            vals = series_values(oi, 4)
            if vals:
                out["opinc"] = sum(vals)

        if out["opinc"] is None:
            try:
                ais = getattr(tk, "income_stmt", None)
                ao = rows(ais, "operating income", "ebit")
                if ao is not None:
                    out["opinc"] = _finite(ao.iloc[0])
            except Exception:
                pass

        eb = rows(qis, "ebitda", "normalized ebitda")
        if eb is not None:
            vals = series_values(eb, 4)
            if vals:
                out["ebitda"] = sum(vals)
    except Exception:
        pass

    try:
        bs = tk.quarterly_balance_sheet
        debt = rows(bs, "total debt")
        cash = rows(bs, "cash and cash equivalents",
                    "cash cash equivalents and short term investments")
        debt_v = _finite(debt.iloc[0]) if debt is not None else None
        cash_v = _finite(cash.iloc[0]) if cash is not None else None
        if debt_v is not None:
            out["netdebt"] = debt_v - (cash_v or 0)

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
    op_m = 100 * f["opinc"] / f["rev"] if f["opinc"] is not None and f["rev"] else None
    fcf_m_pct = 100 * f["fcf"] / f["rev"] if f["rev"] else None
    nd_e = f["netdebt"] / f["ebitda"] if f["netdebt"] is not None and f["ebitda"] not in (None, 0) else None
    mcap = f["price"] * f["shares"] if f["price"] and f["shares"] else None
    fcf_y = 100 * f["fcf"] / mcap if mcap else None
    sh_ch = 100 * (f["shares"] / f["shares_prev"] - 1) if f["shares_prev"] else None
    buyb = max(0.0, -(sh_ch or 0))
    tot_y = (f["div_yield"] or 0) + buyb

    sub = (
        round(_band(rev_g, GROWTH), 1),
        round(_band(op_m, PROFIT), 1),
        round(_band(fcf_m_pct, CASHGEN), 1),
        round(_band(nd_e, BALANCE), 1),
        round(_band(fcf_y, VALUE), 1),
        round(_band(tot_y, RETURNS), 1),
    )
    dil = round(_band(sh_ch, DILUTION), 1)

    ngv = (fcf_m / sh_m) / r
    cover = 100 * ngv / f["price"] if f["price"] else None
    impl = (
        100 * r * (1 - cover / 100) / (1 + (cover / 100) * r)
        if cover is not None and (1 + (cover / 100) * r) != 0
        else None
    )
    cush = rev_g - impl if rev_g is not None and impl is not None else None
    pr = priced_in_from_cover(cover, cush)

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
        warn.append("no revenue history — growth scored at the 5.0 default")
    if nd_e is None:
        warn.append("no net-debt/EBITDA — balance sheet scored at the 5.0 default")
    warn.append("deliver is REVENUE GROWTH, a proxy. Replace with the company's own leading metric.")
    warn.append(f'clock guessed from sector "{f["sector"]}" — confirm CLOCK / CONC / DIV by hand.')

    row = dict(
        yf=symbol,
        fcf=row_fcf,
        shares=round(sh_m, 2),
        r=r,
        cur=("GBp" if symbol.endswith(".L") and f["cur"].upper() == "GBP" else f["cur"] or "USD"),
        deliver=round(rev_g, 1) if rev_g is not None else None,
        dl="revenue growth (PROXY)",
        sub=sub,
        pr=pr,
        dil=dil,
        clock=CLOCK_GUESS.get(f["sector"], "CONC"),
        ins="NOT CHECKED",
        held=False,
        sector=f["sector"],
        built="auto",
        sanity=(round(f["lo"] * .5, 2), round(f["hi"] * 2, 2)) if f["lo"] is not None and f["hi"] is not None else None,
    )
    if na_reason:
        row["na"] = na_reason
    return row, warn


if __name__ == "__main__":
    import pprint
    sym = sys.argv[1] if len(sys.argv) > 1 else "ASML.AS"
    row, warn = auto_row(sym)
    if row is None:
        print("FAILED:", warn)
        raise SystemExit(1)
    print(repr(row))
    for w in warn:
        print("!", w)
