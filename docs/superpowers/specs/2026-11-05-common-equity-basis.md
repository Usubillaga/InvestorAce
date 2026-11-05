# General common-equity basis and EPV integrity

User authorized a new public PR for the source-verified corrections. Stack it on fix/oxy-input-conflicts (PR107), head1379b062144d1e151d59cece23fce59ea6bff5ad; do not merge it.

Required behavior: distinguish paid preferred cash dividends from accrued preferred earnings adjustments; prefer already-common earnings and avoid double subtraction. Match operating-cash and cash-capex per period and continuing/consolidated scope. Known preferred obligations with missing payments remain unknown, not zero. Add ordinary provider row detection and dated issuer bridges; preserve raw financials and unknowns. Select one common-equity scope for commodity history, never mix a pre-sale year into a continuing-operations mean. Keep revised history source dates, raw and adjusted values, and adjustment reasons. Derive OXY history from original filings, not a target valuation. Do not import AlphaSpread price targets as facts.

A conflict may be resolved only by sufficient matched data, not elapsed time or a manual status change. Retain remaining normalization/claims risks. Close the PR107 EPV bypass: active monetary input conflicts must suppress current EPV too, including cached values. Preserve eight-category/current v18 weights, raw regime coefficients, historical generations and generic pending-review independence.

Verification: RED then GREEN tests for double subtraction, mixed operating perimeter, signed/zero/missing preferred cash, annual cash versus NI premium differences, asof/publication identity checks, fresh/cached paths and EPV. Run project Python/Node/lint/WACC and replay actual frozen inputs; disclose all affected tickers. Review branch independently, publish the PR and observe CI.

Implementation
- Added provider disclosure detection, dated common-equity bridges and arithmetic/identity validation. Inputs remain raw; adjusted rows carry cash, earnings, revenue scope and sources separately.
- Original OXY filings reconcile FY2023-25; unconfirmed current paid preferred cash remains null. FY2022 is excluded from the continuing cycle.
- EPV access/population guard covers cached values and unsupported enterprise bridges. Existing primary packets and sourced zero dividends retain precedence.
- Independent review identified EPV scope, primary-packet precedence, zero-dividend and listing-alias defects; failing reproductions were added and fixes pass targeted tests. Final review rerun was unavailable after the review agent hit a usage limit; no final independent approval is claimed.
- Frozen 81-company replay changes only OXY. See docs/analysis/common-equity-bridge.md for evidence and limits. Final full checks and remote CI are recorded in the PR.
