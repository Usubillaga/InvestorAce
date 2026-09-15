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

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional


FIELDS = (
    "revenue", "gross_profit", "rd", "sga", "capex", "dep_amort",
    "tax_rate", "net_debt", "shares",
)


def _clean(xs: Optional[Iterable[Any]]) -> List[float]:
    out: List[float] = []
    for x in xs or []:
        if x is None:
            continue
        try:
            v = float(x)
        except (TypeError, ValueError):
            continue
        if v != v:  # NaN
            continue
        out.append(v)
    return out


def _avg(xs: Optional[Iterable[Any]], n: Optional[int] = None) -> Optional[float]:
    vals = _clean(xs)
    if n is not None:
        vals = vals[:n]
    return (sum(vals) / len(vals)) if vals else None


def _paired(a: Optional[Iterable[Any]], b: Optional[Iterable[Any]]) -> List[tuple[float, float]]:
    out: List[tuple[float, float]] = []
    for x, y in zip(a or [], b or []):
        if x is None or y is None:
            continue
        try:
            xx, yy = float(x), float(y)
        except (TypeError, ValueError):
            continue
        if xx != xx or yy != yy:
            continue
        out.append((xx, yy))
    return out


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
    rev = _avg(revenue, years_norm)
    if not rev or not shares or not wacc or wacc <= 0:
        return None

    gm_pairs = [(g / r) for g, r in _paired(gross_profit, revenue) if r]
    gm = _avg(gm_pairs, years_norm)
    if gm is None:
        return None
    sustainable_gp = rev * gm

    # The sheet treats R&D + SG&A as operating expense. If R&D is unavailable,
    # fetch_ticker supplies zeroes, matching the original transcription.
    opex_pairs = [(x + y) for x, y in _paired(rd or [], sga or [])]
    opex = _avg(opex_pairs, years_norm)
    if opex is None:
        opex = _avg(sga, years_norm)
    if opex is None:
        return None

    ebit = sustainable_gp - opex
    tx = 0.21 if tax_rate is None else float(tax_rate)
    if tx > 1:
        tx /= 100.0
    tx = max(0.0, min(0.60, tx))
    after_tax = ebit * (1.0 - tx)

    cap_pairs = [(c - d) for c, d in _paired(capex or [], dep_amort or [])]
    growth_capex = _avg(cap_pairs, years_capex)
    if growth_capex is None:
        # A missing capex/D&A history means we do not have template-faithful EPV.
        return None

    normalised = after_tax - growth_capex
    enterprise_value = normalised / float(wacc)
    net_debt_value = float(net_debt or 0.0)
    equity_value = enterprise_value - net_debt_value
    per_share = equity_value / float(shares)

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
                try:
                    out.append(None if v != v else float(v))
                except Exception:
                    out.append(None)
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
        if pre and tax and pre[0]:
            effective_tax = max(0.0, min(0.60, float(tax[0]) / float(pre[0])))

        debt = _row(bs, "Total Debt")
        cash = _row(
            bs,
            "Cash And Cash Equivalents",
            "Cash Cash Equivalents And Short Term Investments",
            "Cash And Short Term Investments",
        )
        net_debt = ((debt[0] if debt else 0.0) or 0.0) - ((cash[0] if cash else 0.0) or 0.0)

        shares = _row(bs, "Ordinary Shares Number", "Share Issued")
        if not (rev and gp and sga and cap and da and shares and shares[0]):
            return None
        if rd is None:
            rd = [0.0] * len(rev)

        # Coverage metadata makes confidence auditable without entering the value.
        norm_years = min(len(_clean(rev)), len(_clean(gp)), len(_clean(sga)))
        capex_years = min(len(_clean(cap)), len(_clean(da)))
        return {
            "revenue": rev,
            "gross_profit": gp,
            "rd": rd,
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
        reasons.append("tax rate is Yahoo latest, not template-selected")
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

