# Corpay cash flow through 30 September 2026

Corpay uses “free cash flow” and “cash net income” as other names for adjusted net income attributable to Corpay. Management starts with earnings and adjusts for items including stock compensation, amortization, acquisition costs and related taxes. The cash statement instead records cash generated from operations, including changes in working capital. In Q3 alone, Corpay reported **$500.704m in adjusted net income** while operating cash less cash purchases of property and equipment was **negative $735.049m**. The latter is the nine-month amount less the first six months. [Q3 release, non-GAAP definitions and reconciliation](https://www.sec.gov/Archives/edgar/data/1175454/000117545426000054/ex991q3_2026.htm) · [Q2 Form 10-Q, cash flows](https://www.sec.gov/Archives/edgar/data/1175454/000117545426000050/cpay-20260630.htm)

Amounts below are USD millions. Cash capex is the positive amount spent on property and equipment in the cash statement. Corpay's segment capital expenditures also include noncash additions. TTM covers October 2025 through September 2026 and equals FY 2025 plus 9M 2026 less 9M 2025 for each row.

| Measure | FY 2025 | 9M 2025 | 9M 2026 | TTM |
| --- | ---: | ---: | ---: | ---: |
| Adjusted net income attributable to Corpay | 1,518.145 | 1,094.569 | 1,362.258 | 1,785.834 |
| Operating cash flow | 1,499.901 | 687.163 | 716.283 | 1,529.021 |
| Cash capex | 200.756 | 148.315 | 143.382 | 195.823 |
| Operating cash less cash capex | 1,299.145 | 538.848 | 572.901 | 1,333.198 |
| Stock-based compensation added back in operating cash | 102.637 | 74.826 | 92.928 | 120.739 |
| Cash proxy after InvestorAce's stock-compensation deduction | 1,196.508 | 464.022 | 479.973 | 1,212.459 |

The audited annual cash statement and the quarterly cash statement report in thousands. The earnings releases provide the adjusted-income reconciliation at the same precision. [FY 2025 Form 10-K, consolidated statements of cash flows](https://www.sec.gov/Archives/edgar/data/1175454/000117545426000018/flt-20251231.htm) · [FY 2025 release, adjusted-income reconciliation](https://www.sec.gov/Archives/edgar/data/1175454/000117545426000008/ex991q4_2025.htm) · [Q3 2026 Form 10-Q, cash flows and segment capex footnote](https://www.sec.gov/Archives/edgar/data/1175454/000117545426000059/cpay-20260930.htm)

## What InvestorAce priced

The 06:04 UTC build on 25 November recorded TTM operating cash of $1,529.021m and cash capex of $195.823m. The extraction path in `live_analysis._cash` calculates their difference. The valuation path in `live_analysis.calculate` deducts the same-window $120.739m stock compensation once. At the archived $447.91 quote and 63,971,827 common shares, the resulting $1,212.459m produced a 4.2314% valuation cash yield. The 10-Q cover confirms the same single-class share count on 30 October. Management's $1,785.834m adjusted earnings would overstate this valuation input by $573.375m. The frozen engine used the cash-based input, so the review requires no repricing.

From the 09:00 UTC review cutoff on 25 November, fresh and cached Corpay inputs require an operating cash and cash capex pair for each valuation window. If quarterly data is incomplete, a complete fiscal year may support an explicitly annual valuation. When every available window lacks one of the cash components, the valuation is unavailable. The test replays the issuer’s four quarters with its adjusted earnings deliberately placed in the provider’s generic free-cash-flow field and repeats the missing-component case through a pre-review cache.

The 30 September balance sheet carries $6,339.902m of restricted cash and $8,070.388m of customer deposits. Some of the $3,072.988m in unrestricted cash also relates to customers or regulatory and operating requirements. The cash statement combines payables, accrued expenses and customer deposits in one working-capital line, which added $930.866m in 9M 2026. A recurring parent-shareholder cash estimate requires a separate reconciliation of these flows. Mastercard's 2.3% interest in the cross-border business had a $320m redemption value at period end. The adjustment to redemption value passes through retained earnings as a noncash financing item. The 8% compounded return enters the contractual repurchase price. The agreement gives Mastercard a put beginning in August 2027. Treating the $320m carrying balance, its remeasurement, or that future option as a current parent cash dividend would misstate cash available to common shareholders. [Q3 Form 10-Q, cover, Note 1 and Liquidity and Capital Resources](https://www.sec.gov/Archives/edgar/data/1175454/000117545426000059/cpay-20260930.htm)
