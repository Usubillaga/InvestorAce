# Common-equity input correction

The previous OXY fix withdrew valuations on two recorded conflicts. This change
also corrects the input path: provider disclosures work without a ticker-specific
register entry, while dated issuer bridges can supply verified comparable periods.
Raw provider inputs remain available beside the derived common-equity proxy.

Cash dividends paid on preferred shares are distinct from the earnings deduction.
Already-common income wins without a second deduction. Explicit paid zero is
valid; missing payments on a known obligation remain unknown. Redemption principal
is a separate financing flow, not an annual preferred dividend.

Cash flow and spending must cover the same business perimeter. A nonzero
discontinued-operations row requires explicit matching continuing cash/capex rows
or an issuer bridge. Earnings and revenue must also match that scope for their
ratios. An older consolidated year cannot extend a continuing-operations cycle.
Existing primary financial packets take precedence over optional provider rows.

## OXY reconciliation

Amounts below are USD millions; continuing operations exclude OxyChem. Cash capex
equals reported capex minus the signed change in capital accrual. These figures
are historical cash proxies before other common-equity claims and normalization,
not certified sustainable FCFE or investment recommendations.

| Measure | FY2023 | FY2024 | FY2025 | TTM June 2026 |
|---|---:|---:|---:|---:|
| Continuing operating cash | 10,235 | 10,519 | 9,606 | 11,323 |
| Reported continuing capex | 5,696 | 6,263 | 6,427 | 6,183 |
| Signed capital-accrual change | -22 | 100 | 32 | -59 |
| Cash capex | 5,718 | 6,163 | 6,395 | 6,242 |
| Preferred cash dividends paid | 762 | 679 | 679 | Unknown |
| Cash proxy after preferred dividends | 3,755 | 3,677 | 2,532 | Unknown |
| Continuing income attributable to common | 2,409 | 2,165 | 1,385 | 3,439 |
| Preferred earnings deduction | 923 | 679 | 679 | 679 |

The 2023 earnings deduction is 736 dividends + 151 redemption premium + 36 carrying
value adjustment. It is not the 762 paid cash-dividend figure. The separate 1,661
preferred redemption cash flow already includes its premium.

TTM is FY2025 minus H1 2025 plus H1 2026. Separately paid H1 preferred cash was not
confirmed. Comparable FY2022 continuing figures are unavailable and stay out of the
mean.

*Superseded on 2026-11-07* ([review](common-equity-review-2026-11-07.md)): the
preferred balance stayed at 8,287 from 2023 to June 2026, so the 679 declared in
the TTM is the cash claim (`DECLARED_STABLE_BALANCE`; paid cash still wins where
reported). TTM common cash is 5,081 - 679 = 4,402. Both recorded conflicts resolve
on these matched data; OXY is valued on the FY2023-25 continuing cycle mean of
3,321 (NGV about USD 43 against a USD 56–57 quote, automatic label Hold Positive).
A later provider quarter still never inherits this June row: its current cash
ratios are unknown until an issuer check, while the bridged cycle keeps the value.

EPV cannot bypass a monetary conflict or rely on annual enterprise inputs whose
perimeter/preferred-capital bridge is missing, including a previously cached EPV.
Preferred book carrying value is not assumed to be a verified redemption claim.
Complete, dated, matching monetary data can resolve the two typed input conflicts
automatically; this does not grant analyst approval or normalize the commodity cycle.

## Sources and limitations

- [2025 10-K, filed 18 February 2026](https://www.sec.gov/Archives/edgar/data/797468/000162828026009059/oxy-20251231.htm): recast operations, cash flows and earnings bridge.
- [2024 10-K, filed 18 February 2025](https://www.sec.gov/Archives/edgar/data/797468/000079746825000029/oxy-20241231.htm): preferred cash paid.
- [2023 10-K, filed 14 February 2024](https://www.sec.gov/Archives/edgar/data/797468/000079746824000034/oxy-20231231.htm): preferred payments and redemption components.
- [June 2026 10-Q, filed 5 August 2026](https://www.sec.gov/Archives/edgar/data/797468/000162828026053388/oxy-20260630.htm): recast H1 operations and earnings.

Investing and AlphaSpread were cross-checks. Their cash-flow definitions and
valuation assumptions are not substituted for issuer figures or imported targets.
The bridge has separate publication/retrieval dates, issuer and listing identities,
currency, period/basis, source URLs and arithmetic validation. A later SEC window
cannot inherit a prior period's preferred cash payment. A pending analyst review
alone does not suppress an otherwise supported automatic label.

Frozen replay against PR107 used 81 cached company packets and the same dated
November 4 quotes/rates: only OXY numerical results changed. Its cached EPV67.20
is withdrawn, and cash/payout components become unknown. Older caches lack the
new optional provider rows; this is not a claim that future fresh extracts for
all other issuers are unchanged. Synthetic regressions exercise those new rows.
