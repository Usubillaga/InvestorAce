# Provider-data corrections (2026-11-04)

Follow-up to `2026-11-04-scoreboard-review-corrections.md`. Each item is a
provider artefact that changed points without any change in the business.
Weights, bands and caps are unchanged; opportunity schema `opportunity-v17.2`.

## Share classes

Yahoo's `sharesOutstanding` counts only the quoted class of a multi-class
company. GOOGL read 5,888m shares, exactly the Class A line of Alphabet's 10-Q
cover (5,888m A + 827m B + 5,579m C = 12,294m, 21 Oct 2026): market value, P/E
and FCF yield used 48% of the company (P/E 7.0 instead of ~15). META, NKE and
TTD show smaller gaps of the same kind.

`all_class_shares`: when both the market-value-implied count
(`impliedSharesOutstanding`, else `marketCap / price`) and the latest diluted
average share count exceed the listed count by 5-150%, the smaller of the two
is used (`ALL_CLASSES_MIN_IMPLIED_DILUTED`, with a visible note). A split after
the latest quarter moves only the diluted average; ADR ordinary counts fall
outside the band; issuer overrides (NVO) still win. Effective from the next
fetch, because the cache holds neither count yet.

## Earnings above operating income

Net income above pre-tax operating income requires non-operating gains or tax
benefits. Alphabet's TTM net income was 235.7bn against operating income of
157.0bn (marks on private stakes). The valuation multiple now caps earnings at
operating income (`earnings_basis = CAPPED_AT_OPERATING_INCOME`); reported P/E
remains as a diagnostic. It can only lower a P/E score. Affected on
2026-11-04: GOOGL, UBER, CRM, MRVL, BABA, GRAB. Commodity producers keep their
multi-year earnings mean.

## Missing EBITDA

Salesforce's quarterly EBITDA row was absent in two of four builds on 1-4 Nov
2026 while operating income was present; the balance score, the macro fit and
the Buy label disappeared and returned. A missing row is now handled like an
inconsistent one: operating income plus D&A (new `depreciation` input from the
cash-flow statement), or operating income as a conservative floor.

## Commodity revenue growth

Producers' one-year revenue change is mostly the commodity price (FY2025: CNX
+49%, AG +124%, AR +22%) and scored up to 9.5 growth points while their
valuation already used cycle averages. Growth for `midcycle` rows is now the
revenue CAGR over the same consecutive years as the FCF and earnings averages
(new `annual_revenue_series`), or unknown (bounded, flagged
`CYCLE_REVENUE_GROWTH_UNAVAILABLE`) when those years are not available.

## Short interest

OXY and BA read 0.02% of float on 15 Oct 2026 (132k and 166k shares short
against 21.6m and 14.2m a month earlier). A value below 5% of a prior month of
at least 1m shares is not displayed. Short interest is never scored.
