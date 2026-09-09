#!/usr/bin/env python3
"""
wacc.py - compute the discount rate instead of assigning it
===========================================================
Built from the mathematics in the FMP Advanced DCF workbooks (JNJ, AAPL).

WHY THIS MATTERS MORE THAN ANY OTHER CHANGE TO THE FRAMEWORK
------------------------------------------------------------
The engine's NGV is (FCF / shares) / r, and r has been assigned by hand:
0.075 for SPGI, 0.08 for most rows, 0.09 for LULU, 0.10 for NVDA, 0.105
for producers. Those numbers were judgements, and they were doing an
enormous amount of unexamined work.

Worked from the two uploaded files, at the same FCF per share:

                 flat r = 8%          computed WACC
    JNJ    NGV $121.24, cover 65%    NGV $180.96, cover 97%   (WACC 5.36%)
    AAPL   NGV $133.95, cover 52%    NGV $123.59, cover 48%   (WACC 8.67%)

Under a flat rate the two look like similar propositions. Under the real
rate they are 49 cover-points apart. A beta-0.39 pharma and a beta-1.09
consumer-tech company cannot share a discount rate, and the hand-set r
was erasing the largest single difference between them.

THE CAPM BUILD, EXACTLY AS THE WORKBOOKS DO IT
----------------------------------------------
    cost of equity    = risk_free + beta * market_risk_premium
    after-tax cost of debt = cost_of_debt * (1 - tax_rate)
    WACC = equity_weight * cost_of_equity + debt_weight * after_tax_cost_of_debt

where the weights are market values: equity = market cap, debt = total debt.

THE PROPERTY THAT ANSWERS THE BURNS QUESTION
--------------------------------------------
RISK_FREE is a single module-level input. Change it once and every NGV,
cover, cushion and entry price in the book reprices, correctly and
company-specifically: high-beta rows move more than low-beta rows,
because that is what beta means. The stress test stops being a manual
"+300bp to everything" and becomes the model doing its job.

WHAT THIS DELIBERATELY DOES NOT COPY FROM THE DCF
-------------------------------------------------
The workbooks put 85% (JNJ) and 82% (AAPL) of enterprise value in the
TERMINAL VALUE -- a perpetuity on a five-year projection, with a
long-term growth rate FMP set at 2.0% for JNJ and 4.0% for AAPL. Four
percent forever for a $2.8tn company is not a forecast, it is an
assumption carrying four fifths of the answer.

NGV assumes ZERO growth on purpose. That is not a cruder DCF; it is a
different question -- what is this worth if it never grows again -- and
it has no terminal value to hide in. Take the WACC from the DCF. Leave
the terminal value where it is.
"""
import math

# ---- the three market-wide inputs. Change RISK_FREE and the book reprices ----
RISK_FREE = 3.67          # % -- US 10y in the source workbooks
MARKET_RISK_PREMIUM = 4.72  # % -- FMP's global equity risk premium
DEFAULT_BETA = 1.00
FLOOR, CEILING = 0.045, 0.140   # sanity band on the output


def cost_of_equity(beta, risk_free=None, mrp=None):
    rf = RISK_FREE if risk_free is None else risk_free
    p = MARKET_RISK_PREMIUM if mrp is None else mrp
    return (rf + (DEFAULT_BETA if beta is None else beta) * p) / 100.0


def compute(beta=None, market_cap=None, total_debt=None, tax_rate=None,
            cost_of_debt=None, risk_free=None, mrp=None):
    """Returns (wacc, detail). wacc is a fraction; detail explains it.
       Missing debt data collapses to cost of equity, which is correct for
       a debt-free company and conservative for one whose debt we cannot see."""
    rf = RISK_FREE if risk_free is None else risk_free
    ke = cost_of_equity(beta, rf, mrp)
    kd = (rf if cost_of_debt is None else cost_of_debt) / 100.0
    tx = 0.21 if tax_rate is None else tax_rate / 100.0
    kd_after = kd * (1 - tx)

    e = market_cap or 0.0
    d = total_debt or 0.0
    tot = e + d
    if tot <= 0:
        w = ke
        detail = dict(beta=beta, ke=ke, kd_after=kd_after, we=1.0, wd=0.0,
                      note='no capital structure data; cost of equity used')
    else:
        we, wd = e / tot, d / tot
        w = we * ke + wd * kd_after
        detail = dict(beta=beta, ke=ke, kd_after=kd_after, we=we, wd=wd, note='')
    capped = max(FLOOR, min(CEILING, w))
    if capped != w:
        detail['note'] = (detail['note'] + f' | clamped from {100*w:.2f}%').strip(' |')
    detail['wacc'] = capped
    return capped, detail


def fetch(symbol, yf=None):
    """Pull beta, market cap, total debt and tax rate from Yahoo for one ticker."""
    if yf is None:
        try: import yfinance as yf
        except ImportError: return None
    try:
        tk = yf.Ticker(symbol)
        info = {}
        try: info = tk.get_info() or {}
        except Exception: pass
        fi = {}
        try: fi = dict(tk.fast_info) or {}
        except Exception: pass
        beta = info.get('beta')
        mcap = fi.get('market_cap') or info.get('marketCap')
        debt = info.get('totalDebt')
        if debt is None:
            try:
                bs = tk.quarterly_balance_sheet
                idx = {str(i).strip().lower(): i for i in bs.index}
                if 'total debt' in idx: debt = float(bs.loc[idx['total debt']].iloc[0])
            except Exception: pass
        eff_tax = None
        try:
            ist = tk.income_stmt
            idx = {str(i).strip().lower(): i for i in ist.index}
            pre = idx.get('pretax income'); tex = idx.get('tax provision')
            if pre and tex:
                p, t = float(ist.loc[pre].iloc[0]), float(ist.loc[tex].iloc[0])
                if p: eff_tax = max(0.0, min(40.0, 100.0 * t / p))
        except Exception: pass
        return dict(beta=beta, market_cap=mcap, total_debt=debt, tax_rate=eff_tax)
    except Exception:
        return None


if __name__ == '__main__':
    # reproduce the two workbooks from their own inputs
    for name, beta, mcap, debt, tax, expected in (
        ('JNJ',  0.392, 185.98 * 2_429_400_000,  0.075/0.925 * 185.98*2_429_400_000, 15.71, 5.36),
        ('AAPL', 1.094, 257.13 * 15_408_095_000, 0.0292/0.9708 * 257.13*15_408_095_000, 24.09, 8.67)):
        w, d = compute(beta=beta, market_cap=mcap, total_debt=debt, tax_rate=tax)
        print(f'{name:5} computed {100*w:.2f}%   workbook {expected:.2f}%   '
              f'ke {100*d["ke"]:.2f}%  kd_at {100*d["kd_after"]:.2f}%  '
              f'we {100*d["we"]:.1f}%')
