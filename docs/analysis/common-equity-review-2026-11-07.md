# Common-equity inputs: review of PR108/PR109 · 2026-11-07

PR108 and PR109 added the common-equity bridge and dated issuer corrections
for the cases where Yahoo or SEC data are missing. The issuer figures checked
here are correct. Four rules withheld valuations that the reported data
support, and the frozen replay could not show it.

## What the live builds did

The PRs reported 54 → 57 automatic signals from cached packets. Those caches
lacked the new provider rows. The nightly builds re-extract every stock:

| Build (UTC) | Signals | Valuations blocked by input conflicts |
| --- | ---: | --- |
| 2026-11-05 03:25, before the merges | 61 | none |
| 2026-11-05 21:32 | 56 | AMD, APP, OXY, PG, SAN, SPCX, SPGI |
| 2026-11-06 03:30 | 55 | + PFE |
| 2026-11-07 02:43 | 55 | + SMCI |

OXY was withheld on purpose (PR107). AMD, APP, PFE, PG and SPGI lost a signal,
and SAN lost its bounded score.

## Defects

1. **Row names.** yfinance 0.2.66 serves `Cash From Discontinued Operating
   Activities`, `Cash From Discontinued Investing Activities` and `Cash Flow From
   Discontinued Operation` (const.py keys through `camel2title`). It has no
   continuing-operations capex row. The aliases `Cash Flow From Discontinued
   Operating Activities` and `Capital Expenditure From Continuing Operations`
   never matched. The unit test built those rows itself. In production any
   `Net Income Discontinuous Operations` value left the window unresolved, and
   the continuing-operations path could not be reached from provider data.
2. **No materiality.** Pfizer reported USD −5m of discontinued operations over
   the nine months to September 2026 against USD 5,710m of net income, and nil
   in Q4 2025. That line blocked the whole valuation.
3. **Paid preferred cash only.** P&G discloses its ESOP preferred dividends
   (USD 291m TTM, 72–73m a quarter) in the equity statement. Its cash statement
   shows one dividend line. The claim is 1.9% of USD 15.3bn FCF, yet it blocked
   the stock. OXY's Berkshire preferred stayed at USD 8,287m from 2023 to June
   2026, and 679m was declared in the TTM. The TTM was blocked anyway.
4. **Commodity cycle.** For a mid-cycle stock the value and the multiple use
   the cycle years. A gap in the current TTM still blocked a cycle that the
   issuer bridge covered completely. Any later quarter would block it again.
5. **Scope over all history.** Without a current provider row, for example in
   an SEC catch-up window, any older unresolved row unresolved the current
   window. Broadcom's FY2024 VMware disposal was enough.

## Changes

- Discontinued rows use yfinance's own names, and their amounts are stored per
  window. Amounts at or below 5% of the window's net income and operating cash
  stay in the reported figures, with a warning.
- A material disposal moves the window to continuing operations when the
  provider separates its cash. That needs a discontinued cash row, plus
  continuing operating cash or a discontinued operating row to subtract. Capex
  and the other investing rows then belong to the continuing business.
  Earnings come from `Net Income From Continuing Operation Net Minority
  Interest`. Revenue on the face of the statement already excludes
  discontinued operations. Without that separation the window stays
  unresolved and blocked, as before.
- The preferred cash claim is the paid amount where it is reported. Otherwise
  it is the same-window declared dividend, if every known preferred balance
  from the window's opening to its end stays within 5%. With a stable balance,
  the deduction holds no redemption premium and the payable does not move. A
  moved balance keeps the claim unknown: issues (GOOGL June 2026, SMCI),
  conversions (SPCX) and redemptions (OXY 2023, 9,762m → 8,287m, 923m
  deduction against 762m paid). The basis is recorded as `PAID`,
  `DECLARED_STABLE_BALANCE` or `NO_PREFERRED_CLAIM`.
- A mid-cycle stock keeps its valuation while its current window is open, if
  three things hold:
  - an issuer bridge fixes the perimeter;
  - at least three consecutive cycle years are complete on that perimeter;
  - each of those years carries its preferred claim.

  The current cash ratios become unknown. Without such a bridge, a current
  disposal still blocks the stock.
- Only rows that share days with the current window can unresolve it.
- Conflicts the calculator detects are first-party text, translated into DE
  and ES. Recorded conflicts stay original-language review text.
- The data and model section, `_data_quality.input_gaps` and the build log list
  blocked valuations, open windows and issuer-bridge coverage. An issuer bridge
  never rolls into a newer provider window, so this list shows what needs a new
  issuer check.

## Replay

This replays generation `20261107T024312423790-8799572194e341be8a05eee947a929f2`
with the same cached facts, quotes, rates and macro weights. Signals go from 55
to 57:

| Ticker | Before | After | Score | NGV (USD) | Quote (USD) | Basis |
| --- | --- | --- | ---: | ---: | ---: | --- |
| OXY | blocked | Hold Positive | 6.67 | 43.20 | 56.38 | FY2023-25 continuing cycle, 3,321m |
| PG | blocked | Hold Positive | 6.26 | 84.42 | 165.40 | 15,340m − 291m declared |

All other rows are unchanged. Cached rows from 5–7 November lack the
materiality amounts, so they keep the conservative reading until the next
extraction. A simulation with Pfizer's reported amounts (TTM −5m, FY2025 25m,
FY2024 11m) gives PFE Hold Positive 6.23. AMD, APP, SAN and SPGI depend on
Yahoo's row coverage and are re-evaluated at the next live fetch. That
extraction will also show any provider rows in other stocks that change the
result.

On the 7 November inputs OXY becomes a Buy below USD 46.27. That price comes
from the model, not from an independent recommendation. Commodity normalization
remains open. The FY2023-25 years also still carry interest on debt that was
repaid with the OxyChem proceeds.

## Open

- **SEC claims.** The SEC catch-up window carries no preferred, minority or
  discontinued tags. SMCI's September window is blocked although its 10-Q
  reports the payment.
- **Run rate of a new preferred.** The GOOGL TTM holds one payment, 234m. The
  6.25% coupon on USD 19bn is about 1.19bn a year until the May 2029 mandatory
  conversion. The FCF yield is 0.6% on either basis.
- **SPCX.** The venture preferred converted in 2026. A cash-dividend zero is not
  yet confirmed.

## Sources

- [Alphabet Q3 2026 Form 10-Q (PDF)](https://s206.q4cdn.com/479360582/files/doc_financials/2026/q3/GOOG-10-Q-Q3-2026.pdf): 6.25% mandatory convertible preferred issued 5 June 2026; 234m preferred cash dividends paid; 384m nine-month preferred deduction; combined dividend line.
- [Pfizer Q3 2026 earnings release (PDF)](https://s206.q4cdn.com/795948973/files/doc_financials/2026/q3/Q3-2026-PFE-Earnings-Release-FINAL.pdf) and [Q4 2025 release (PDF)](https://s206.q4cdn.com/795948973/files/doc_financials/2025/q4/Q4-2025-PFE-Earnings-Release-FINAL2.pdf): discontinued operations −5m (9M 2026), nil (Q4 2025), 25m (FY2025).
- [S&P Global Q3 2026 earnings exhibits (PDF)](https://s29.q4cdn.com/690959130/files/doc_financials/2026/q3/S-P-Global-3Q-2026-Earnings-Release-Exhibits-10-27-2026.pdf): Mobility spin-off on 1 July 2026; continuing operating cash 3,661m and a single discontinued cash line of 387m (9M 2026).
- [yfinance 0.2.66 `const.py`](https://github.com/ranaroussi/yfinance/blob/0.2.66/yfinance/const.py): statement keys; row labels via `utils.camel2title`.
- P&G and OXY figures: the issuer filings already cited in `source_reviews.json`.
