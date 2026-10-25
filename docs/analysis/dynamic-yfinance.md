# Dynamic company calculations

`engine.run_build()` now refreshes supported company financial inputs with
yfinance after fetching quotes and before calculating the report, observation,
and scanner. `live_analysis.py` owns extraction and numerical calculations.
The weekday build uses the existing 23:00 UTC schedule. GitHub Pages displays
the latest successful Python calculation; opening a page does not fetch prices.

## Facts and assumptions

| Input | Treatment |
| --- | --- |
| Revenue, earnings, operating cash flow and capex | Sum four actual matching quarters, otherwise use a matching fiscal year. Never annualize incomplete quarters. |
| Debt and cash | Balance sheet at the selected cash-flow period end. |
| Shares | Current Yahoo outstanding-share snapshot, explicitly undated; dated balance-sheet shares are a fallback. |
| Price | Dated quote, maximum age 96 calendar hours for price-dependent outputs. |
| Revenue growth and share change | Comparable annual periods; each metric retains its own period labels. |
| Risk-free rate | Existing shared USD Treasury curve and its source/date. |
| Cost of equity | `risk_free + beta * market_risk_premium`. |
| Five-year FCF growth | Comparable annual FCF growth, bounded to -10% to +15%; zero when unavailable. An assumption, not a forecast. |
| Terminal growth | Lower of 2% and cost of equity minus one percentage point, floored at zero. |
| Bear/bull growth | Base growth minus/plus five percentage points. |

Financial period, retrieval time and quote time are separate. Yahoo does not
establish filing publication dates or resolve restatements. An undated current
share count does not complete the share/corporate-action review. Non-USD cash
flows disclose the shared USD-rate assumption. Incompatible quote and financial
currencies suspend valuation; the GBP to GBp unit conversion is explicit.

## Python formulas

The ordinary-company cash-flow proxy is operating cash flow minus absolute cash
capex. If that bridge is unavailable, Yahoo's reported Free Cash Flow is labelled
as the fallback. This reported leveraged proxy is not certified sustainable FCFE.
The no-growth scenario is `FCF / shares / cost_of_equity`. The DCF discounts five
annual cash flows and a perpetuity terminal value, then divides by shares.
Reverse DCF solves the five-year growth rate consistent with the current quote
and declared terminal assumption. These equity scenarios do not subtract net
debt again. Enterprise EPV retains its existing WACC and net-debt bridge.

Commodity rows use a mean of at least three contiguous annual reported cash
flows, with zero base growth, as a disclosed preliminary scenario. Funds, REITs,
midstream distributable-cash-flow models, reported-FFO models, banks and insurers
retain their specialized models. Ordinary Yahoo FCF cannot stand in for AFFO,
issuer distributable cash flow or normalized FFO.

All eight original score curves/weights and the regime coefficients remain the
existing framework. Missing inputs remain null; refreshed companies never fall
back to a fixed total or an invented neutral category. Source review and analyst
approval remain separate from visible, reproducible model arithmetic.

## Persistence and access

`history/_dynamic_cache.json` contains versioned last-good **input facts**.
When a financial refresh fails, the build retains their original retrieval date
and recalculates against this run's quote and rates. Cache packets from after
the calculation cutoff are rejected. With no valid facts, output is unavailable.
The history publisher already commits the entire history directory.

The original primary-analysis row is copied into `primary_analysis_archive` in
the evidence generation. Dated research, sources and objections remain in their
existing source registers. Existing immutable observations remain reproducible.

Every scoreboard row links to `scanner.html?view=universe&ticker=SYMBOL`.
This link opens the requested company independently of default Buy/new filters.
The selected company's JSON review packet is available below its heading and
in the navigation, and remains associated with that company when filters or tabs
change. It contains the dated inputs, Python outputs, assumptions, primary
research and unresolved objections.

## Zoetis correction

Zoetis research was present in `scanner_notes.json`, `source_reviews.json`, and
`docs/analysis/DVN-ZTS-2026-10-23.md`. A prior primary-review hold set the valuation
cash flow to null because the normalization/recast bridge was unresolved. Default
scanner filters also hid the row and its export action. The correction restores
a visible *current reported-cash scenario* alongside the retained primary
analysis and outstanding objections; it does not certify the unresolved bridge.
