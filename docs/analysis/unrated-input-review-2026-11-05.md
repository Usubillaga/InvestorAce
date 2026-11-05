# InvestorAce unrated input review · 2026-11-05

Reviewed all 31 names without an automatic signal in generation
`20261105T111945687481-061f3668ea0a4140a367e5def4c2fb3f`. The
[source register](../../source_reviews.json) records issuer filings, periods,
publication and retrieval dates, table locators and the six confirmed reporting
dates. Figures below use the company statement currencies.

An expired earnings charge no longer triggers a current cash-payment block.
The last known opening balance and dated claims within the current window
still require a payment reconciliation. This applies to SEC catch-up packets
as well. The exact-period payment corrections retain the provider's raw inputs.

## Replayed automatic signals

The offline run reproduced the original 85 results before changing inputs.
With the same captured quotes, exchange rates, discount rates and macro weights,
the number of signals rose from 54 to 57 and monetary blocks fell from 12 to 6.
The 54 previously scored signals retained their scores and labels. NGV and DCF
below are model outputs based on reported cash proxies.

| Ticker | Quote (USD) | Signal | Score / 10 | NGV (USD) | Base DCF (USD) |
| --- | ---: | --- | ---: | ---: | ---: |
| AVGO | 325.48 | Hold Positive | 6.15 | 68.72 | 77.44 |
| GOOGL | 288.93 | Hold Negative | 5.46 | 14.86 | 17.65 |
| O | 59.22 | Hold Negative | 5.49 | 55.10 | 68.72 |

## Input decisions

| Ticker | Result | Issuer evidence or open item |
| --- | --- | --- |
| APP | Blocked | September filing supplies continuing revenue and common income. Full same-period cash capex and the continuing operating-cash bridge remain open. |
| AVGO | Signal restored | The preferred conversion in 2022 makes the old earnings charge irrelevant to July 2026 TTM. |
| AWK | No signal | Nine-month operating cash less cash capex was USD −772m. |
| BABA | No signal | June issuer FCF was negative. The cached TTM still lacks a complete cash-capex bridge. |
| BNTX | No signal | Nine-month operating cash less capex was EUR −723.1m. |
| BYRN | Input corrected | The historical preferred issue converted. TTM cash is positive and operating EBITDA is negative. |
| CRWV | No signal | H1 cash proxy was USD −10,454m. Q3 results due November 10 after the US close. |
| ENB | Issuer inputs recorded | June TTM raw cash proxy was CAD 1,465m and CAD 1,040m after paid preferred dividends, before noncontrolling distributions. The issuer's distributable cash measure has a different capex basis. Q3 due November 6. |
| ENG | Issuer inputs recorded | June TTM raw cash proxy was EUR 31.302m. Affiliate dividends are investing receipts. The October FFO update and post-acquisition leverage need a separate valuation bridge. |
| GOOGL | Signal restored | September TTM USD 234m of paid preferred dividends reduces cash from USD 19,747m to USD 19,513m. USD 384m is the separate earnings deduction. |
| GRAB | No signal | Reported nine-month cash proxy was USD −35m. The issuer adjusts bank-related working capital in its other FCF measure. |
| IBST | Data gap | June H1 adjusted cash was GBP −22m. A new complete reported TTM cash packet is still unavailable. |
| ISRG | Data gap | Comparable September total debt is unavailable. Prior annual operating lease balances prevent a zero-debt assumption. |
| JEQE | Inapplicable | EUR-hedged UCITS ETF share class. |
| MRNA | No signal | H1 cash proxy was USD −1,255m. Q3 scheduled for November 6. |
| NBIS | No signal | H1 operating cash less cash PPE and intangibles was USD −3,626.2m. Q3 due November 12. |
| O | Signal restored | The 2024 10-K confirms redemption of all outstanding preferred shares. AFFO is a separate measure. |
| OPEN | No signal | H1 cash proxy was USD −973m. Q3 scheduled after the November 5 US close. |
| OXY | Blocked | FY2025 paid preferred cash of USD 679m is verified. June filing aggregates the two share classes. Current paid preferred cash and the comparable common cash cycle remain open. Q3 due November 9 after the US close. |
| PG | Blocked | The USD 291m preferred earnings deduction is known. Separate cash payments and the ESOP settlement still need reconciliation. |
| PL | No signal | The GAAP operating loss and negative TTM operating EBITDA leave the leverage component unavailable. |
| RCAT | Input corrected | The 10-Q shows 4,676 Series B preferred shares. Financing cash totals reconcile to zero preferred dividends paid at statement precision. June TTM cash remains negative. |
| REP | Data gap | Reported financial liabilities and issuer net debt use different perimeters. Comparable gross debt is still missing. |
| RIVN | No signal | Original cash statements reproduce USD −4,192m September TTM FCF. |
| SAN | Blocked | September continuing cash from operations is verified. Same-period total capex and continuing common earnings need reconciliation. |
| SMCI | Input corrected | June TTM paid preferred cash was zero. The November preliminary release reports USD 63.729m paid in September. June and preliminary September cash are both negative. |
| SPCX | Blocked | Preferred conversion in 2026 is verified. The December 2025 outstanding claim falls within the September TTM and paid cash remains unreconciled. |
| SPGI | Blocked | The issuer recast nine-month cash flow. A comparable FY2025 continuing cash baseline is still required. |
| TEM | No signal | Nine-month cash burn is confirmed, including capitalized software. The complete TTM software/capex bridge remains open. |
| VICI | Issuer inputs recorded | September TTM operating cash less own fixed-asset capex was USD 2,677.891m. It excludes portfolio investment funding and uses a different basis from AFFO. |
| WIX | No signal | Negative operating EBITDA leaves the leverage component unavailable. |

The ENB, ENG and VICI observations supplement the specialist rows. Comparable
automatic signals for these rows require a valuation bridge on their cash basis.
The six event dates are issuer announcements. Each release still needs a
period and cash-flow check after publication.
