#!/usr/bin/env python3
"""
epv.py * Earnings Power Value, per Greenwald
============================================
Transcribed from the EPV sheet of the ValueInvesting.io template.

WHY THIS REPLACES NGV RATHER THAN SITTING BESIDE IT
---------------------------------------------------
NGV is (FCF / shares) / r. EPV is the same idea done properly, and the
three differences are exactly the three things I have been patching by
hand all session:

1. NORMALISATION.  NGV capitalises the LATEST free cash flow. EPV
   capitalises a three-year average of revenue and margin, minus a
   three-year average of operating expense. Every cycle_pos flag, every
   "mid-cycle" override for AR/DVN/OXY/CNX, and every argument about
   Lululemon's one-off tariff refund or Planet Labs swinging from
   +$52.9m to -$2.5m in two quarters exists because NGV has no
   normalisation. EPV has it structurally.

2. NET DEBT.  EPV divides normalised earnings by WACC to get ENTERPRISE
   value, then subtracts net debt to reach equity. NGV divides by shares
   immediately, which is only correct if the FCF is already post-interest
   equity cash flow. For VST with ~$19.9bn of net debt, or ENB at 5.1x
   leverage, that assumption is doing violent work.

3. MAINTENANCE vs GROWTH CAPEX.  EPV subtracts the five-year average of
   (capex - D&A): the amount by which capex exceeds depreciation is
   growth spending, not maintenance. NGV cannot separate them, which is
   why American Water Works came out `na` -- $3.13bn of capex against
   $2.06bn of operating cash flow reads as "no free cash flow" when the
   truth is "a regulated utility investing its rate base".

THE CHAIN, EXACTLY AS THE TEMPLATE COMPUTES IT
-----------------------------------------------
    sustainable revenue       3y average
    sustainable gross margin  3y average
    sustainable gross profit  = revenue * margin
  - maintenance opex          3y average of (R&D + SG&A)
  = normalised EBIT
  * (1 - tax rate)
  = after-tax normalised EBIT
  - 5y average of (capex - D&A)
  = NORMALISED EARNINGS
  / WACC
  = enterprise value
  - net debt
  = equity value
  / shares
  = EPV per share

WHAT EPV DELIBERATELY DOES NOT DO
----------------------------------
No growth. No terminal value. No projection. Like NGV it answers "what
is this worth on today's earning power, forever" -- it just measures
today's earning power far more carefully. The FMP DCF workbooks put 82-85%
of their value in a terminal-value perpetuity; EPV has nowhere to hide.
"""
import math

FIELDS = ('revenue', 'gross_profit', 'rd', 'sga', 'capex', 'dep_amort',
          'tax_rate', 'net_debt', 'shares')


def _avg(xs, n=None):
    xs = [x for x in xs if x is not None]
    if n: xs = xs[:n]
    return sum(xs) / len(xs) if xs else None


def compute(revenue, gross_profit, rd, sga, capex, dep_amort,
            tax_rate, net_debt, shares, wacc, years_norm=3, years_capex=5):
    """All series newest-first. Amounts in the same unit; shares in the same
       unit as the amounts (so millions of currency, millions of shares).
       Returns a dict with the full chain, or None if inputs are unusable."""
    rev = _avg(revenue, years_norm)
    if not rev or not shares or not wacc:
        return None
    gm = _avg([g / r for g, r in zip(gross_profit, revenue) if r], years_norm)
    if gm is None:
        return None
    sgp = rev * gm
    opex = _avg([(x or 0) + (y or 0) for x, y in zip(rd or [], sga or [])], years_norm)
    if opex is None:
        opex = _avg(sga, years_norm) or 0.0
    ebit = sgp - opex
    tx = (tax_rate if tax_rate is not None else 0.21)
    if tx > 1: tx /= 100.0
    after_tax = ebit * (1 - tx)
    growth_capex = _avg([(c or 0) - (d or 0) for c, d in zip(capex or [], dep_amort or [])],
                        years_capex) or 0.0
    normalised = after_tax - growth_capex
    ev = normalised / wacc
    eq = ev - (net_debt or 0.0)
    return dict(
        sustainable_revenue=rev, sustainable_gross_margin=gm,
        sustainable_gross_profit=sgp, maintenance_opex=opex,
        normalised_ebit=ebit, tax_rate=tx, after_tax_ebit=after_tax,
        growth_capex=growth_capex, normalised_earnings=normalised,
        wacc=wacc, enterprise_value=ev, net_debt=net_debt or 0.0,
        equity_value=eq, shares=shares,
        epv_per_share=(eq / shares if shares else None))


def fetch(symbol, yf=None, wacc=None):
    """Pull the nine inputs from Yahoo annual statements. Returns None when a
       required series is missing -- a partial EPV is worse than no EPV."""
    if yf is None:
        try: import yfinance as yf
        except ImportError: return None
    try:
        tk = yf.Ticker(symbol)
        ist, cf, bs = tk.income_stmt, tk.cashflow, tk.balance_sheet
        if ist is None or ist.empty: return None
        def row(df, *names):
            if df is None or df.empty: return None
            idx = {str(i).strip().lower(): i for i in df.index}
            for n in names:
                k = idx.get(n.lower())
                if k is not None:
                    return [None if (v != v) else float(v) for v in df.loc[k].values]
            return None
        rev = row(ist, 'Total Revenue', 'Operating Revenue')
        gp  = row(ist, 'Gross Profit')
        rd  = row(ist, 'Research And Development') or [0] * len(rev or [])
        sga = row(ist, 'Selling General And Administration',
                       'Selling General And Administrative')
        cap = row(cf, 'Capital Expenditure')
        cap = [abs(x) if x is not None else None for x in (cap or [])]
        da  = row(cf, 'Depreciation And Amortization',
                      'Depreciation Amortization Depletion')
        pre = row(ist, 'Pretax Income'); tax = row(ist, 'Tax Provision')
        tr  = None
        if pre and tax and pre[0]:
            tr = max(0.0, min(0.40, tax[0] / pre[0]))
        debt = row(bs, 'Total Debt'); cash = row(bs, 'Cash And Cash Equivalents',
                                                 'Cash Cash Equivalents And Short Term Investments')
        nd = ((debt[0] if debt else 0) or 0) - ((cash[0] if cash else 0) or 0)
        sh = row(bs, 'Ordinary Shares Number', 'Share Issued')
        if not (rev and gp and sga and sh): return None
        return dict(revenue=rev, gross_profit=gp, rd=rd, sga=sga, capex=cap,
                    dep_amort=da, tax_rate=tr, net_debt=nd, shares=sh[0])
    except Exception:
        return None


if __name__ == '__main__':
    # Apple, from the figures in the uploaded FMP DCF workbook (USD millions)
    r = compute(revenue=[391035, 383285, 394328, 365817, 274515],
                gross_profit=[180683, 169148, 170782, 152836, 104956],
                rd=[31370, 29915, 26251, 21914, 18752],
                sga=[26097, 24932, 25094, 21973, 19916],
                capex=[9447, 10959, 10708, 11085, 7309],
                dep_amort=[11445, 11519, 11104, 11284, 11056],
                tax_rate=0.2409, net_debt=89100, shares=15408.1, wacc=0.0867)
    for k, v in r.items():
        print(f'{k:26}{v:>16,.2f}' if isinstance(v, float) else f'{k:26}{v}')
