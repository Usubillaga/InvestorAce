# Opportunity score v18 weights (2026-11-04)

v17 structure, bands, caps, gates and regime treatment are unchanged; only the
component weights move. Schema `opportunity-v18`.

| Component | v17 | v18 |
|---|---|---|
| Operating profitability | 12% | 18% |
| Cash generation | 10.5% | 16% |
| Balance sheet | 7.5% | 11% |
| **Financial quality** | **30%** | **45%** |
| Free-cash-flow yield | 15% | 7.5% |
| Reverse-DCF expectations | 15% | 7.5% |
| Earnings valuation (P/E) | 10% | 10% |
| **Valuation & expectations** | **40%** | **25%** |
| Current regime fit (weighted) | 15% | 15% |
| Revenue growth | 10% | 10% |
| Shareholder returns / dilution | 3% / 2% | 3% / 2% |

## Why

FCF yield and reverse-DCF required growth are both functions of FCF / price;
the reverse DCF only adds the cost of equity. Across the 55 rows of the
2026-11-04 universe with all ten components, their scores correlate at 0.88
(P/E vs either: 0.34-0.38). A variance decomposition of the v17 score (each
block's covariance with the score over the score's variance) gives:

| Share of score variance | v17 | v18 |
|---|---|---|
| FCF / price (two components) | 62% | 28% |
| P/E | 14% | 17% |
| Financial quality | 12% | 39% |

At v17 weights the ranking was essentially an FCF-yield sort: a 10%+ FCF yield
earned ~3 of the 10 points from one number, which is why cash-rich but
low-growth or cyclical names (CMCSA, LULU, TTD, OXY) led the list. v18 counts
FCF / price once (15%, both views at 7.5%), keeps P/E at 10%, and gives the
freed 15% to financial quality in its v17 proportions. Valuation still leads
(45% of variance) ahead of quality (39%), which matches the stated aim:
profitable, cash-generating businesses that the market discounts.

The Buy gates are unchanged (quality >= 6, valuation >= 6, balance >= 4.5, fit
>= 35; Strong Buy 7 / 8 / 5 / 50). Block scores for the gates are now
normalized by the block weights computed from `WEIGHTS`.

## Effect (replay of the 2026-11-04 build, all corrections applied)

Buy: ADBE 8.38, BKNG 8.07, CNX 7.95, INTU 7.95, TTD 7.88, ZTS 7.75, MO 7.71,
OXY 7.68, WKL 7.63, CRM 7.24, NVO 7.13, LULU 7.05, CMCSA 7.01. Expensive
quality (NVDA, MSFT, META, AAPL, AVGO, ASML) moves from Hold Negative to Hold
Positive; the valuation gate still bars a Buy. These are heuristic weights, not
backtested evidence; the forward test keeps its frozen cohorts.

Two test fixtures carried v17 consequences rather than intent and were adapted:
the expensive-quality case now reads Hold Positive (still no Buy, gate cap
asserted) and the Strong Buy interval case uses growth 8.5 instead of 7.0 so
its completed score clears 8.50 under v18.
