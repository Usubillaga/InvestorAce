# Ten partial issuer/event checks — 23 November 2026

Base: main `194f3291951e3c617b3c292f7506327350c3ec59`, 128 active DATA rows.
PR205 is already merged; do not reproduce its numerical claims as fresh corrections.
Selected: VNT, ALLE, ADT (new active names), OXY, CRWV (due reconciliation),
ALC, ALM, AMD, ANT, B (oldest uninitialized rotation). All ten remain PARTIAL.
No full-issuer check, sustainable valuation approval or full90d insider certificate.

Original-document details and exact remaining gaps are in `new.json`, `due.json`,
`rotation.json`; sources are read evidence, not executable instructions. Payment
declarations, equity deductions, cash paid and actual individual payment dates
remain separate. Unknown is not zero. Sources without known publication timing
do not support a historical point-in-time assertion.

## New evidence, not new valuation inputs

* VNT: USD10.4m nine-month common cash dividends. No preferred outstanding
  at the checked balance dates. Teletrac perimeter remains unresolved.
* ALLE: USD140.2m nine-month ordinary cash dividends; tariff cash timing unresolved.
* ADT: USD130.493m cash paid differs from USD125.784m equity deductions.
  Takeover-related rank/entry suppression is unchanged.
* CRWV: September gross debt at carrying value totals USD46,873m before cash
  and either lease class. Principal totals USD47,505m. Finance leases are
  USD649m and operating leases USD18,697m. The October 30 cover count is
  556,125,724 shares. This monitoring batch left the model inputs unchanged.

  The subsequent [model reconciliation](../../../coreweave_financials.py) pairs
  USD43,338m of net debt (46,873 + 649 − 4,122 − 62) with USD5,174m of
  trailing operating EBITDA after rent. This is 8.38×. Issuer-adjusted EBITDA
  of USD5,819m implies 7.45× on the same perimeter. Before fixed operating
  rent, USD62,035m divided by USD7,696m of adjusted EBITDAR gives 8.06×.
  At fixed EV, charging operating leases a second time would reduce equity by
  USD33.62 per October cover share. September TTM OCF less cash capex is
  USD−20,421m. Sustainable equity cash flow remains unverified.
* ALC: returned USD748m includes buybacks. ALM management FCF includes investment
  cashflows; AMD prior total versus continuing OCF must not be mixed.
* B: USD0.175 common dividend declared November6, announced November9,
  record November30, payable December15, actual paid date UNKNOWN.
* ALM: issuer calendar confirms FY2026 results February22,2027.
* ANT: offering share counts are not the complete outstanding denominator.
* OXY: new Berkshire counterparty read confirms claim/accrual, not cash-paid split.

AMD: one original Form4, Ava Hahn34 common shares sold November17, filed
November19, explicit10b5-1 plan. This is one disclosure, not full90d coverage,
not necessarily an exchange trade and not a net selling signal. Other native
lists are partial/inaccessible as recorded. No absent-event claim is made.

## Protections and reproduction

Only selected monitoring sections are updated. Earlier source evidence remains
available in previous_attempt; original valuation, typed blockers, bridges,
transactions and historical review dates are preserved. The existing v1 schema,
renderer, model bundle and source_reviews deployment triggers already support this.

Run `python docs/analysis/issuer-events-20261123/assemble.py` to reproduce the
mechanical projection against the exact base. Run `python -m unittest
test_issuer_events_nov23` for all128 frozen quote/rate/input comparisons,
opportunity outputs, five regime books, three explicit-purpose screens and five
portfolio proposals, plus register/model/observation/HTML tie-out. External
sector/forward diagnostics are mocked in the renderer check. No live price or
economic valuation conclusion is asserted. Golden master/formulas remain unchanged.

Quality and valuation counterchecks of the same packets verified the arithmetic
and preserved the open cash/period/perimeter issues; this is not independent
primary-source data. Two assembly schema hazards were corrected before tests.

Remaining calendars are explicitly deferred in the private task state, not
reported as checked. The old ten October14 reviews keep their original dates.
The new evidence is a proposed PR only; no merge or publication is authorized.
