#!/usr/bin/env python3
"""
epv.py · Earnings Power Value (Greenwald-style) for InvestorAce
===============================================================

This module is a SECOND valuation lens beside NGV, not a replacement for it.
The disagreement is information:

    NGV = latest / hand-normalised equity FCF capitalised at r
    EPV = normalised operating earning power capitalised at WACC, then net debt

The computation follows the uploaded ValueInvesting.io EPV sheet's chain:
3y sustainable revenue and gross margin, 3y operating expense, tax, 5y average
(capex - D&A), enterprise value, net debt, equity value, per-share value.

Important fidelity note
-----------------------
The spreadsheet has a separately selected tax-rate input. Yahoo does not expose
that human selection, so fetch_ticker() reports a latest effective tax rate and
marks its provenance. InvestorAce may override it with d['epv_tax_rate'].
No automatic tax smoothing is invented here.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional
import math
from integrity import finite_number, positive_number

INPUT_SCHEMA = 'epv-inputs-v2-aligned-known-debt'


FIELDS = (
    "revenue", "gross_profit", "rd", "sga", "capex", "dep_amort",
    "tax_rate", "net_debt", "shares",
)


def _clean(xs: Optional[Iterable[Any]]) -> List[float]:
    out: List[float] = []
    for x in xs or []:
        v = finite_number(x)
        if v is not None:
            out.append(v)
    return out


def _avg(xs: Optional[Iterable[Any]], n: Optional[int] = None) -> Optional[float]:
    vals = _clean(list(xs or [])[:n] if n is not None else xs)
    return (sum(vals) / len(vals)) if vals else None


def _paired(a: Optional[Iterable[Any]], b: Optional[Iterable[Any]]) -> List[tuple[float, float]]:
    out: List[tuple[float, float]] = []
    for x, y in zip(a or [], b or []):
        xx, yy = finite_number(x), finite_number(y)
        if xx is not None and yy is not None:
            out.append((xx, yy))
    return out


def _income_rows(revenue, gross_profit, rd, sga, years):
    """Use one common mask inside the requested newest-first fiscal window."""
    rows = zip(revenue or [], gross_profit or [], rd or [], sga or [])
    result = []
    for raw in list(rows)[:years]:
        values = tuple(finite_number(x) for x in raw)
        if all(x is not None for x in values) and values[0] > 0:
            result.append(values)
    return result


def compute(
    revenue,
    gross_profit,
    rd,
    sga,
    capex,
    dep_amort,
    tax_rate,
    net_debt,
    shares,
    wacc,
    years_norm: int = 3,
    years_capex: int = 5,
) -> Optional[Dict[str, Any]]:
    """Compute EPV from newest-first annual series.

    Amounts and shares must use compatible units. Returns None rather than a
    partial valuation when the core operating inputs are not usable.
    """
    shares, wacc, net_debt = positive_number(shares), positive_number(wacc), finite_number(net_debt)
    if (shares is None or wacc is None or net_debt is None
            or type(years_norm) is not int or years_norm < 1
            or type(years_capex) is not int or years_capex < 1):
        return None
    income = _income_rows(revenue, gross_profit, rd, sga, years_norm)
    if not income:
        return None
    rev = sum(x[0] for x in income) / len(income)
    gm = sum(x[1] / x[0] for x in income) / len(income)
    sustainable_gp = rev * gm

    # The sheet treats R&D + SG&A as operating expense. If R&D is unavailable,
    # fetch_ticker supplies zeroes, matching the original transcription.
    opex = sum(x[2] + x[3] for x in income) / len(income)

    ebit = sustainable_gp - opex
    tx = 0.21 if tax_rate is None else finite_number(tax_rate)
    if tx is None:
        return None
    if tx > 1:
        tx /= 100.0
    tx = max(0.0, min(0.60, tx))
    after_tax = ebit * (1.0 - tx)

    cap_pairs = [(c - d) for c, d in _paired(list(capex or [])[:years_capex],
                                           list(dep_amort or [])[:years_capex])]
    growth_capex = _avg(cap_pairs)
    if growth_capex is None:
        # A missing capex/D&A history means we do not have template-faithful EPV.
        return None

    normalised = after_tax - growth_capex
    enterprise_value = normalised / float(wacc)
    net_debt_value = net_debt
    equity_value = enterprise_value - net_debt_value
    per_share = equity_value / float(shares)

    if not all(math.isfinite(x) for x in (rev, gm, opex, normalised, enterprise_value, equity_value, per_share)):
        return None
    return {
        "sustainable_revenue": rev,
        "sustainable_gross_margin": gm,
        "sustainable_gross_profit": sustainable_gp,
        "maintenance_opex": opex,
        "normalised_ebit": ebit,
        "tax_rate": tx,
        "after_tax_ebit": after_tax,
        "growth_capex": growth_capex,
        "normalised_earnings": normalised,
        "wacc": float(wacc),
        "enterprise_value": enterprise_value,
        "net_debt": net_debt_value,
        "equity_value": equity_value,
        "shares": float(shares),
        "epv_per_share": per_share,
        "years_norm": years_norm,
        "years_capex": years_capex,
        "income_years_used": len(income),
        "capex_years_used": len(cap_pairs),
    }


def _row(df, *names):
    if df is None or getattr(df, "empty", True):
        return None
    idx = {str(i).strip().lower(): i for i in df.index}
    for name in names:
        k = idx.get(name.lower())
        if k is not None:
            out = []
            for v in df.loc[k].values:
                out.append(finite_number(v))
            return out
    return None


def fetch_ticker(tk) -> Optional[Dict[str, Any]]:
    """Fetch EPV inputs from an already-created yfinance Ticker.

    Returns inputs plus provenance. This function deliberately does not compute
    EPV because InvestorAce owns the WACC decision and may use a manual fallback.
    """
    try:
        ist, cf, bs = tk.income_stmt, tk.cashflow, tk.balance_sheet
        if ist is None or ist.empty:
            return None
        ist = ist.reindex(columns=sorted(ist.columns, reverse=True))
        if cf is not None:
            cf = cf.reindex(columns=sorted(cf.columns, reverse=True))
        if bs is not None:
            bs = bs.reindex(columns=sorted(bs.columns, reverse=True))

        rev = _row(ist, "Total Revenue", "Operating Revenue")
        gp = _row(ist, "Gross Profit")
        rd = _row(ist, "Research And Development")
        sga = _row(
            ist,
            "Selling General And Administration",
            "Selling General And Administrative",
        )
        cap = _row(cf, "Capital Expenditure")
        if cap:
            cap = [abs(x) if x is not None else None for x in cap]
        da = _row(
            cf,
            "Depreciation And Amortization",
            "Depreciation Amortization Depletion",
            "Depreciation",
        )

        pre = _row(ist, "Pretax Income", "Income Before Tax")
        tax = _row(ist, "Tax Provision", "Income Tax Expense")
        effective_tax = None
        if pre and tax and pre[0] and tax[0] is not None:
            effective_tax = max(0.0, min(0.60, float(tax[0]) / float(pre[0])))

        debt = _row(bs, "Total Debt")
        cash = _row(
            bs,
            "Cash And Cash Equivalents",
            "Cash Cash Equivalents And Short Term Investments",
            "Cash And Short Term Investments",
        )
        net_debt = (debt[0] - cash[0] if debt and cash
                    and debt[0] is not None and cash[0] is not None else None)

        shares = _row(bs, "Ordinary Shares Number", "Share Issued")
        if not (rev and gp and sga and cap and da and shares and positive_number(shares[0])):
            return None
        rd_source = 'reported'
        if rd is None:
            rd = [0.0] * len(rev)
            rd_source = 'assumed-zero-unavailable'

        # Coverage metadata makes confidence auditable without entering the value.
        norm_years = len(_income_rows(rev, gp, rd, sga, 3))
        capex_years = len(_paired(cap[:5], da[:5]))
        return {
            "input_schema": INPUT_SCHEMA,
            "revenue": rev,
            "gross_profit": gp,
            "rd": rd,
            "rd_source": rd_source,
            "sga": sga,
            "capex": cap,
            "dep_amort": da,
            "tax_rate": effective_tax,
            "tax_source": "yahoo-latest-effective" if effective_tax is not None else "default-21%",
            "net_debt": net_debt,
            "shares": float(shares[0]),
            "norm_years_available": norm_years,
            "capex_years_available": capex_years,
        }
    except Exception:
        return None


def fetch(symbol, yf=None) -> Optional[Dict[str, Any]]:
    """Fetch EPV inputs for a symbol. Prefer fetch_ticker() when a Ticker exists."""
    if yf is None:
        try:
            import yfinance as yf  # type: ignore
        except ImportError:
            return None
    try:
        return fetch_ticker(yf.Ticker(symbol))
    except Exception:
        return None


def confidence(inputs: Optional[Dict[str, Any]], tax_overridden: bool = False) -> Dict[str, Any]:
    """Evidence quality only. Never multiply a valuation or score by this."""
    if not inputs:
        return {"level": "NONE", "score": 0.0, "reasons": ["no EPV inputs"]}
    reasons: List[str] = []
    score = 1.0
    ny = int(inputs.get("norm_years_available") or 0)
    cy = int(inputs.get("capex_years_available") or 0)
    if ny < 3:
        score -= 0.25
        reasons.append(f"only {ny} normalisation years")
    if cy < 5:
        score -= 0.20
        reasons.append(f"only {cy} capex/D&A years")
    if not tax_overridden:
        score -= 0.10
        reasons.append("tax rate assumes 21%" if inputs.get('tax_source') == 'default-21%'
                       else "tax rate is Yahoo latest, not template-selected")
    if inputs.get('rd_source') == 'assumed-zero-unavailable':
        score -= 0.10
        reasons.append('R&D unavailable; zero is an assumption')
    if inputs.get("net_debt") is None:
        score -= 0.20
        reasons.append("net debt missing")
    score = max(0.0, min(1.0, score))
    level = "HIGH" if score >= 0.80 else "MEDIUM" if score >= 0.55 else "LOW"
    return {"level": level, "score": round(score, 2), "reasons": reasons}


if __name__ == "__main__":
    # Deterministic Apple fixture from the uploaded epv.py example.
    r = compute(
        revenue=[391035, 383285, 394328, 365817, 274515],
        gross_profit=[180683, 169148, 170782, 152836, 104956],
        rd=[31370, 29915, 26251, 21914, 18752],
        sga=[26097, 24932, 25094, 21973, 19916],
        capex=[9447, 10959, 10708, 11085, 7309],
        dep_amort=[11445, 11519, 11104, 11284, 11056],
        tax_rate=0.2409,
        net_debt=89100,
        shares=15408.1,
        wacc=0.0867,
    )
    print(f"Apple EPV fixture: {r['epv_per_share']:.2f}" if r else "fixture failed")

