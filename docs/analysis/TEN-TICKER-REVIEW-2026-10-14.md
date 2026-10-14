# Ten-ticker source and insider review — 14 October 2026

The first batch covers ASML, ENB, LULU, LVMH, NFLX, NVDA, PFE, SAN (Sanofi),
UNH and WKL. The remaining 66 tickers are **not reviewed**. A source inspection
does not certify a sustainable valuation. Dated source URLs, periods,
reconciliations, limitations and individual public disclosures are frozen in
`source_reviews.json`, the archived model bundle and the paired observation.

## Financial changes and limits

| Ticker | Implemented input or explanation | Still required |
| --- | --- | --- |
| ASML | Retain EUR10,000m sustainable assumption; issuer TTM EUR20,999.4m remains a separate reported observation. | Working capital/advances, sustainable capex, point-in-time shares, EUR rate and equity bridge. |
| ENB | Identify CAD12,900m as a DCF-based assumption, not OCF less total capex; record September's 44.735m new shares. | Post-offering shares/acquisition bridge and CAD equity-DCF/rate matching. |
| LULU | Replace 112m shares with 110.710025m common plus exchangeable shares at August28; special voting shares are not counted twice. Correct the unsupported normalization claim. | Reconcile the selected USD850m assumption with reported TTM USD1,354.336m, tariff refund, interest and cash taxes. |
| LVMH | Correct H1 operating FCF to EUR4,100m; EUR13,100m remains a selected model assumption. Record reported TTM EUR11,401m separately. | Sustainable FCF, treasury/dilution and equity/rate bridge. |
| NFLX | Date/reconcile rounded USD11,152m reported TTM OCF-minus-PPE; keep rounded4,163.94m shares consistent with the June30 cover. | WBD USD2,800m receipt, Brazil non-income taxes and net cash-tax normalization. |
| NVDA | Replace rounded USD126,900m with issuer-defined reported TTM USD126,886m; replace EPS diluted-weighted24,285m with July26 outstanding24,147m, preserving million-share source precision. | Sustainable FCF and matching cash-flow/rate contract. |
| PFE | Replace undated USD9,480m with reported TTM OCF-minus-PPE USD10,985m; date5,699.673589m outstanding shares to July29. | Sustainable normalization and cash-flow/rate contract. |
| SAN | Record H1 issuer-adjusted FCF EUR3,724m and the source-table OCF inconsistency; retain the undated EUR6,900m assumption. | Consistent normalized FCF, share/debt definitions and EUR rate. |
| UNH | Existing USD22,826m reported TTM and July31 outstanding897.594847m shares tie to issuer sources. | Timing, subsidiary capital restrictions and normalized equity-cash-flow/rate match. |
| WKL | Replace232.52m with222.439643m dated September18:224.716153m issued less2.276510m treasury. Retain EUR1,250m FCF assumption. | Later repurchases/issuance and dilution; sustainable adjusted-FCF bridge. The dated count is not an exact October14 count. |

No reported cash flow is called normalized, FCFE or FCFF merely to clear a
warning. No debt is subtracted twice from a levered cash-flow measure. The
existing NGV, reverse-DCF, score, risk and regime formulas are unchanged.
Valuation diagnostics now also reject a claimed cost-of-equity label when
the calculation actually uses WACC, and expose the absent FCFF equity bridge.

## Public insider-disclosure review

Publication/filing and transaction dates are distinct. The window is July16
through October14,2026, inclusive, as observable on the review date. Later or
undisclosed filings cannot be certified. P/S include open-market **or private**
transactions. Awards, option exercises, withholding, gifts and employee fund
subscriptions are separate, with no inferred motive or net buying signal.
Derivative and non-derivative rows are not netted against each other.

| Ticker | Native-source coverage | Result |
| --- | --- | --- |
| UNH | SEC27/27 Forms4/4A parsed |28 retained transaction rows. |
| NFLX | SEC40/40 parsed |95 retained rows. |
| NVDA | SEC17/17 parsed |37 retained rows; superseded Parker award excluded. |
| PFE | SEC16/16 parsed |15 retained rows, including purchases and a sale. |
| LULU | SEC2/2 parsed |4 award rows; no P/S row in the checked window. |
| SAN | AMF exact issuer/type/window7/7 documents parsed |6 employee FCPE subscriptions and1 disposal of prior award shares. FCPE quantities are units, not direct ordinary-share purchases. |
| LVMH | AMF exact issuer/type/window returned0; historical positive control404 records |No manager declaration publicly listed in that window; this does not establish no actual trading. |
| ASML | AFM first listing accessible; issuer/window filter/export not completed |PARTIAL, no no-activity assertion. |
| WKL | Same native AFM limitation |PARTIAL, no no-activity assertion. |
| ENB | Native SEDI query unavailable |UNAVAILABLE, no no-activity assertion. |

The review contains186 transaction rows from109 inspected disclosures:
102 SEC Forms4/4A plus7 AMF documents. A row is not a separate economic
trade: one filing may contain several tables, instruments or transaction legs.
The old undated insider strings remain historical inputs but are no longer
presented as current evidence. Unreviewed rows show NOT REVIEWED.

## Controlled comparison and verification

Reference: main2ad1269, verified build
`20261014T092738126538-b7eacfc4b2c646e08a87d041eea3d5ba`.
All76 archived quotes, used rates, EPV data, subjective categories and weights
were fixed. Only this batch's input corrections and diagnostic metadata were
overlaid. These are model calculations at frozen inputs, not live prices or
certified fair values.

| Ticker | Legacy NGV before | After | Score before → after |
| --- | ---: | ---: | --- |
| WKL, EUR |95.47499 |99.80165 |unchanged |
| NVDA, USD |35.65155 |35.85134 |unchanged |
| PFE, USD |27.03228 |31.32559 |6.150 →6.225 |
| LULU, USD |88.48903 |89.52009 |unchanged |

Only those four tickers' numerical outputs change. PFE and LULU regime fits
move through the existing Cover/Duration term; coefficients and weight
independence do not change. The Inflation, Stagflation and Recession books
change order; Goldilocks and Reflation books do not. The complete Reflation
proposal is identical. Other proposal entry plans can change with NGV.
All three screens were recomputed; differences include updated numerical
fields and must not be described as membership changes without that comparison.

Validation executed:133 tests pass, including11 source-review regressions;
pyflakes, actionlint and `git diff --check` pass. Controlled offline HTML
rendering succeeds with exactly10 reviewed and66 unreviewed tickers.
Independent code review found no Critical or Important issue. Existing
generation archives and the production pointer are not edited by this change;
the normal paired build/deployment publishes after integration.
