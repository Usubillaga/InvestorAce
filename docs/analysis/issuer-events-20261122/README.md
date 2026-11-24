# Issuer/payment batch — 22 November 2026

Base: `cb6e102c80633f835304b8ede4e2608a382b1e0f`, 125 active DATA rows.
Ten concrete **partial** reviews: OXY, ENB, CRWV, MRNA, NBIS, OPEN, AVGO,
BYRN, INTU, NVDA. The other 115 calendars were not source-checked in this
Sunday batch. Their unknown calendars remain a Monday initialization backlog,
not invented earnings dates. JEQE is a fund; its distributions are not issuer
preferred claims. SPCX identity remains unresolved, not assumed to be an ETF.

This proposal changes source/payment diagnostics and date handling, not the
financial packet, approved ratings, score weights or valuation formulas.
No gate, golden master, lock, atomic publication, historical build or current
pointer is weakened or manually overwritten. No new sustainable valuation is
certified. All ten remain `PARTIAL`, with separate attempt and completion data.

## Actual evidence and remaining bridges

| Title | Actually read / newly recorded | Still open |
| --- | --- | --- |
| OXY | Nov9 Q3 release + 10-Q; YTD USD1,271m combined cash dividends versus USD509m preferred declarations; common USD0.28 payable Jan15, record Dec10 | Paid preferred split; continuing TTM/midcycle bridge. Declared509 is not paid509. |
| ENB.TO | Nov6 Q3 original CAD statements; preferred319m/common6355m paid; Dec1 common CAD0.97 payable, record Nov13; series-specific preferred payments separate | CAD equity/DCF and total versus maintenance-capex contract; no second preferred deduction from management DCF; SEDI wall. |
| CRWV | Nov10 earnings release, Nov12 Form 10-Q. No preferred outstanding or paid in 9M2026. Cover: 556,125,724 shares on Oct30. | The provider's USD51,608m equals June gross debt plus both lease classes (35,068 + 221 + 16,319). September under that definition is USD66,219m (46,873 + 649 + 18,697). |
| MRNA | Nov6 Q3 actual report; YTD USD OCF−2715m/PPE146m/intangibles74m separate | Preferred/equity-note payment tieout, TTM and normalization. No payment zero from omission. |
| NBIS | Nov12 Q3 actual PDF/6-K; all-class292902405 shares Sept30 match cache | Continuing TTM, capex/SBC, valuation contract and AFM issuer/window export. |
| OPEN | Nov5 release/10-Q; Note13 expressly zero common/preferred declared/paid/accumulated Q3/9M2026/2025 | TTM and cashflow sustainability; zero is not a blanket redemption assertion. Mainstay preferred investment is not OPEN-issued preference capital. |
| AVGO | Aug2 actual fiscal 10-Q; no preferred opening/closing; common dividends9281m USD YTD; Dec9 after-close results announced Nov9 | Cache July31 versus fiscal Aug2 reconciliation; September30 payable not independently proved paid. Existing conversion fix supported, not a new current preferred obligation. |
| BYRN | Aug31 10-Q; old SeriesA converted Apr15 2021; none issued opening/closing; native Section16 pages1–2 and nine4/4A documents | Current sustained cashflow/TTM; historical withholding4/A stays outside current transactions, no net signal. |
| INTU | Nov19 Q1 FY27 release + 10-Q; paid common dividends/rights378m USD versus declared383m; January15 USD1.38 payable, record January8;264015000 outstanding Nov12 | Undated provider267236000 denominator reconciliation; customer funds and pending Mailchimp sale; Q1 is not TTM. |
| NVDA | Nov17 Q3 FY27 release + SEC exhibit; YTD issuer FCF122675−8856−147=113672m USD; December23 USD0.25 payable, record December2 | Cache still July versus new October25 period; spot shares, matched FY/priorYTD, financed-asset principal and sustainable contract. |

All amounts retain source period, units, scope, locator and retrieval limits in
the adjacent JSON files. No actually-paid event date is inferred from payable.
Ex-dates unknown in these documents remain null. Company report dates confirm
publication, not completion of this whole-watchlist audit.

## Insider coverage

Window August24–November22,2026 at the individual retrieval cutoffs.
`insider-intu-nvda-summary.json` plus the two original-document extracts retain
native index hashes and original tables. INTU24/24 documents, NVDA16/16; rows
remain partial pending complete adjudication. NVDA Parker4/A replaces, not
duplicates, the earlier award. BYRN retains nine disclosures and15 separate
transaction rows; a2024 withholding amendment is not a new90-day trade.
Remaining native SEC/SEDI/AFM failures are recorded individually. No incomplete
list certifies absence of trades, and P/S does not certify exchange execution.
Awards, exercises, withholding, gifts, derivatives and ownership/plan facts
remain distinct. No motive or net buying score is inferred.

## Review and reproducibility

Three fresh role passes used the same frozen packets: quality, valuation, risk.
They are model-based packet checks, not three independent primary-data sources.
Round2 quality checked the continuing OXY numerator; valuation checked the
INTU/CRWV spot-versus-weighted denominators. Both support retaining the gaps.
Risk's unvalidated-payment objection was corrected with typed date, amount,
currency and payable/actual-state validation plus targeted regressions.

`review-run.json` intentionally has null audited valuations and no ready
price judgment. Its structural validator cannot authenticate the sources or
make the existing model's valuations economically correct.

Run `python docs/analysis/issuer-events-20261122/assemble.py` to mechanically
project the packets into the existing register. Do not regenerate from unknown
files or use this as a fetch script. `source_reviews.json` contains the exact
packet hashes and dated summaries; `evidence.model_bundle` already freezes that
register, observation embeds it, and HTML renders that supplied generation.
Existing deploy trigger includes the register. The files themselves remain
available at this reviewed commit; no historical model is rewritten.

`verify.py` uses the existing verified build
`20261121T195547981686-ee737f70a3564220a54a1d4386707595` with all125 frozen
quotes/rates/inputs. Executed comparison: identical NGV, reverseDCF, cover,
cushion, score, risk, verdict, all five raw regime books, three explicitly
purposed screens and five portfolio proposals. Financial-packet, typed conflict,
common-equity and conditional-DCF boundaries remain unchanged. Observation,
model hash and HTML register generation checked together without publication.
Golden-master contract unchanged. No numerical/rank claim from changing prices.

Initial full offline suite:741 tests passed; targeted final date/payment suite:
19 passed; JavaScript suites:26 passed; WACC workbook reproduction and diff check
passed. Final full-suite/lint result is recorded in the PR after the last patch.
No full online fetch/deployment or live Pages verification was run locally.
