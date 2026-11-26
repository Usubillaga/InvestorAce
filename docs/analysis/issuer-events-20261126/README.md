# Issuer/payment review — 26 November 2026

## Scope and result

132 active DATA symbols at main `b2726f086a4fda64ad8ffbdb07b6e5cdae87307d`. The new names since the task cursor are VIS, JD, BIDU and FPS. PAYX is the only inherited scheduled report/payment review due on 25–26 November. Five intensive partial issuer checks, no completed full issuer checks; no excess due workload. Thursday has no rotation fillers. The other 127 names received calendar planning only, not a new source/financial certification.

The inherited 128-calendar inventory is the pinned `source_reviews.json#/calendar_checks/issuers` at open PR233 head `42715eb3ae4eacbdd426af8c14877abd01b3b932`. It is monitoring evidence pending integration, not main production data. PR233 is retained separately. Its issuer changes and tests are not copied into this branch. PR245's proposed ORCL patch is not in main DATA, so ORCL is not added to the active count or rotation. PR242 concerns separate panic accounts.

## New source-backed records

| Issuer | What the original documents establish | What remains unverified / next check |
|---|---|---|
| VIS / VIS.MC / EUR | Issuer memorandum via CNMV pp7–8 schedules the optional cash election for **21 December**. Final supplement and BORME fix **EUR1.434** and **38 rights** per new share; record 26 November, election ends 9 December. | Not cash paid. Election totals, matched treasury cancellation and the resulting net denominator remain open. Check results 10 December, payment evidence after 21 December. |
| JD / Nasdaq ADS / USD | Q1 release says the annual dividend was completed **in April**; no exact payment day is asserted. Q3 release supplies the TTM cashflow reconciliation. | No future declaration established. Model OCF-minus-net-capex proxy differs from issuer consumer-financing-adjusted FCF; gross cash-capex bridge and sustainable FCFE remain open. Check 3 December. |
| BIDU / Nasdaq ADS / USD | Q3 release expects a first dividend declaration by end-2026, subject to board approval and conditions. | No amount, record date, payable date or payment. Negative cashflow base is preserved. Check 3 December for an actual declaration, not automatic payment recognition. |
| FPS / NYSE Class A / USD | Original Q1 FY2027 10-Q, Note15 p18, explicitly reports zero tax distributions to noncontrolling OpCo holders **for the quarter**. | This does not establish zero TTM preferred/common cash. Customer advances, Up-C/TRA obligations and economic-interest cashflow remain open. Check 3 December. |
| PAYX / Nasdaq common / USD | October15 notice declares **USD1.19**, record October26, payable **November25**. The August-quarter 10-Q separately reports USD424.1m common cash paid and USD423.6m declared. | November actual payment is unverified. Quarter paid cash does not prove that later event. Paycor/client-fund normalization and TTM bridge remain open. IR calendar supplies no confirmed next earnings date; review December18, not an issuer-confirmed event. |

`packet.json` retains original URLs, publication/retrieval dates, exact fund/payment definitions, document SHA256 and locators. Direct Viscofan pages returned errors; the two actual issuer PDFs were read through CNMV, and the BOE notice was independently read. Month-only completion and payable dates remain separate from actual payment days. Missing cash is not zero.

## Financial and growth boundaries

No numeric valuation input is replaced. Existing subjective categories, approval status, growth basis, rates and ticker mappings stay intact.

- VIS FY2025 reported OCF EUR195.369m less cash PPE EUR80.447m = EUR114.922m; model subtracts EUR6.775m SBC to EUR108.147m. This source proxy does not certify sustainable common FCFE. Gross issued shares including treasury cannot replace the dated net denominator automatically.
- JD TTM reported OCF CNY40.444bn less net capex CNY20.898bn = CNY19.546bn. Issuer adjusted FCF CNY18.803bn additionally reflects CNY0.743bn consumer-financing movement. The model SBC adjustment of CNY4.487bn produces a different CNY15.059bn valuation proxy. CECONOMY closed after the September perimeter; no unbridged combination is inserted. Revenue growth is not cashflow growth.
- BIDU Q3 OCF CNY2.778bn less capex CNY7.349bn = negative CNY4.571bn. Current TTM reported FCF negative CNY15.134bn less SBC CNY3.031bn remains negative CNY18.165bn. The release's AI Cloud growth is not consolidated or cashflow growth. Eight ordinary Class A shares per ADS remains separate from the provider count.
- FPS quarter OCF USD136.115m less cash PPE USD31.706m = USD104.409m; USD159.408m deferred-revenue inflow warrants sustainable-cash caution. Class A plus paired OpCo economic units is not Class A plus Class B plus OpCo units. Current model TTM FCF USD121.539m less SBC USD23.360m is USD98.179m, without new sustainability approval.
- PAYX quarter OCF USD413.5m less PPE USD56.1m = USD357.4m, not TTM. Cash dividends and declared dividends differ. Dated cover shares are distinct from weighted EPS shares.

The native USD discount assumption for CNY/ADS cashflows and sustainable equity-cash/rate matching is not newly certified. NGV and reverse DCF continue using existing matching rate paths; this source-only proposal does not change either formula.

## Public ownership disclosures

`disclosures.json` preserves native IR page URLs/hashes, dated inventories and original-document hashes. FPS pagination: 2 pages, 12 in-window filings including one Form3, 11 Form4 documents with Table I. PAYX: 4 pages, 32 mixed in-window filings, 16 original Form4s with Table I; the other retrieved attachments are not counted as ownership transactions. Both lists reach before the 90-day cutoff. SEC-native reconciliation, acceptance times, amendments and full derivative/footnote adjudication remain partial.

Two explicitly adjudicated samples preserve instrument, role, dates, P/F code, quantity, price, ownership and unknown plan evidence: FPS Spierkel's November20 P-coded acquisition; PAYX Gibson's October19 tax-withholding disposition. P does not establish exchange venue. PAYX awards, gifts, holdings and Form144 proposals are not net sales. Native CNMV/HKEX full-window coverage for VIS/JD/BIDU remains open. No CHECKED_NO_EVENTS certification is added. Prior dated insider reviews/rows are retained; a new monitoring window does not relabel their historical dates.

## Review and verification

Two review rounds covered source quality, valuation and risk separately. The initial missing cash-day objection was resolved by reading Viscofan's issuer memorandum, not by inferring payment. All five sustainable valuation conclusions remain blocked pending explicit bridges; a source gap is not a Hold/Sell judgment. `review.json` and `audit-result.json` record the contract, open issues and review roles. A valid audit record is not independent source truth or economic valuation approval.

The executable `verify_frozen.py` compares all 132 current archived inputs with the exact base register versus the proposed register. It holds quotes, rates, fundamentals and macro fixed, comparing score/NGV/reverse/Cover/cushion/risk/verdict/opportunity, all five raw regime books, explicit quality/regime/duration screens and portfolio proposals. Results are identical. It separately checks Golden Master and the identical register in model bundle, Observation and rendered HTML. See `comparison.json` for capture date and result.

Three new regression tests distinguish optional/declared/paid-month/actual-paid dates, quarter cash-paid versus declared, the narrow OpCo zero and existing rejection of future cash confirmation. Tests pin the dated packet, not the mutable watchlist or live register hashes. No runtime, Golden Master, validation, evidence lock/hash, atomic publisher or workflow gate is changed. Full Python, JavaScript, pyflakes and WACC check results are recorded in the PR after execution.
