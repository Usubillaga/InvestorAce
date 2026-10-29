# InvestorAce opportunity score v17

The user wants profitable, cash-generating businesses that the market discounts,
classified by business type and suitability for the current economic regime.
Restore five visible automatic labels: Strong Buy, Buy, Hold Positive,
Hold Negative, Sell. Manual review remains a separate status. Preserve prior
scores, financial analyses, sources, objections and the five-regime formula.

Use the existing Python/yfinance pipeline. The new decision layer uses 30%
financial quality (profitability 12%, cash generation 10.5%, balance 7.5%),
40% valuation (FCF yield 15%, earnings multiple 10%, reverse-DCF expectations
15%), 10% revenue growth, 5% shareholder returns/dilution (3%/2%) and 15%
current regime fit. The previous eight-category calculation stays available
for historical reproduction. These weights are a design choice, not
backtested evidence or weights selected to force particular tickers to Buy.

Use the existing 8.5/7/5.5/3.5 label boundaries, before rounding. Reject
unprofitable/negative-cash/debt traps through visible score caps. Strong Buy
needs quality >=7, valuation >=8 and current fit >=50; Buy needs quality >=6,
valuation >=6, balance >=4.5 and current fit >=35. Negative operating income,
negative free cash flow or balance <3 cap at Hold Negative. Negative earnings
cap at Hold Positive. Unverified commodity-cycle proxies cap at Buy.

Business profiles are sector-based heuristics, with separate growth/quality/
value tags derived from actual metrics. Show all five regime fits and highlight
the current one. Current macro regime comes from the dated engine snapshot;
it is a market-signal classifier, not an official economic diagnosis.

Missing inputs retain bounds, never neutral fabricated points. A label may
be shown for a partial score only if the entire attainable score interval
lies in one band and core quality, valuation and macro inputs are supported.
Known nonnegative gross debt / positive EBITDA provides a conservative lower
balance-score bound when cash is missing; it does not manufacture cash.
No point score is assigned to an interval. Missing prices or expired quotes
remove price-dependent signals in Python and in an already-open browser.

P/E is market capitalization / corresponding reported net income, explicitly
a proxy using current outstanding shares. Commodity valuation uses >=3
consecutive annual FCF observations, and corresponding annual earnings when
available. Reported peak P/E remains diagnostic and cannot score as normalized
earnings. DCF scenarios and heuristic macro fits are assumptions, not forecasts.

Implementation: new pure opportunity.py + reusable opportunity_view.py;
integrate into engine snapshot/report, universe scanner, review packets/PDF.
Keep the SEC-wide prescreen as a separately labelled preliminary calculation.
The front page ranks the new opportunity signal. Existing analysis remains
accessible. Rejected approaches: merely restoring old labels leaves growth
weights and manual gating unchanged; replacing archived formulas destroys
historical comparability. A versioned new decision layer addresses both.

Validation: behavioral regression fixtures for discounted quality, expensive
quality, cash/debt traps, commodity normalization, missing inputs, changing
regimes, stale quotes, label boundaries and frontend expiry; then full Python,
JavaScript, lint and desktop/mobile checks. Publish through a tested PR.
