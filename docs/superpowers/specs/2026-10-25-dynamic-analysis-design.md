# Dynamic financial analysis without losing research

The user rejected static research exports as the substantive improvement and
explicitly requested Python formulas recalculated with yfinance data. Zoetis
research still exists in production; the primary-review hold removed current
valuation inputs. PR76 was merged and its packets are online, but ZTS is hidden
by the default Buy/new filters.

## Design decision

Refresh supported ordinary-company inputs on every build from one yfinance
financial snapshot per issuer. Recompute ratios, original-category curves,
reported-FCF no-growth scenarios, five-year DCF scenarios and inverse DCF in
Python. Keep primary-source research, objections and historical values. Current
model arithmetic is visible even while normalization/analyst approval is open.

Use reported OCF minus cash capex as a LEVERED_FCF_PROXY, with cost of equity
for its equity valuation; do not subtract net debt again. This is a disclosed
reported-cash scenario, not a claim of normalized FCFE. EPV continues using WACC
and its existing enterprise/equity bridge. Explicit growth/terminal/horizon
assumptions remain distinct from fetched facts. Existing category weights and
regime coefficients do not change. Funds, REITs and other bespoke cash metrics
retain their explicitly identified existing models rather than misusing Yahoo
FCF as AFFO. A common USD risk-free curve remains a disclosed assumption for
other currencies; it never earns source/normalization approval.

## Boundaries

- `live_analysis.py` owns statement extraction, pure calculations and a small
  supported-row refresh adapter. `analyze(ticker, symbol, *, quote, risk_free,
  mrp, as_of)` returns the JSON-safe interface below.
- Snapshot fields: status, as_of, fetched_at, financial_period, basis, currency;
  inputs (absolute amounts, shares, quote_price); metrics; parameters
  (discount_rate_pct, growth_rate_pct, terminal_growth_pct, horizon_years);
  valuation (ngv_per_share, dcf_per_share, reverse_dcf_growth_pct, scenarios with
  name/growth_pct/value_per_share); overlay with million-unit engine inputs.
- Use a complete four-quarter window or a full fiscal year; never capitalize a
  half year as annual cash. Ratios retain their own matched fiscal windows.
- Missing inputs stay null. No fixed total/neutral category fallback for a
  refreshed corporate row. A failed fetch keeps research and dated last-good
  financial inputs; calculations rerun against the current quote and rate.
- Engine observes refreshed values, but the source/normalization/approval gates
  remain separate. A cache/retrieval timestamp is not a publication date.
- Scanner exposes direct ticker links and an obvious selected packet download;
  optional dynamic-analysis fields are display only. Browser never computes DCF.
- Existing weekday workflow runs refresh and computation automatically. Static
  hosting presents these server-generated results; no credentials enter HTML.

## Verification

Known-value formulas, changed price/cash/shares/rates, missing inputs, mismatched
periods/currencies, failure retention, and ZTS primary-research preservation get
regression coverage. Exercise ZTS with live yfinance, run the complete suite,
browser checks and one fresh whole-change review. Publish an unmerged PR.
