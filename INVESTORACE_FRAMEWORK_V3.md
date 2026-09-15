# InvestorAce Framework v15.2 — Regime Contract + EPV Lens

## Why this version exists

The previous v2 refactor improved architecture but changed the regime model while claiming exact preservation. That failure mode is now treated as a framework problem, not a documentation problem.

This version makes three changes without changing the existing Score, Verdict, NGV formula, or pre-v2 regime outputs:

1. **Freeze the regime model as a contract.**
2. **Add EPV beside NGV, not inside the score.**
3. **Build the 30-name regime book from regime fit only.**

## 1. Regime model is now a golden contract

The live formula remains:

```
50
+ 12.0 * sector affinity
+ DUR_W[regime] * clamp((cover - 0.60) * 100, -40, +40)
+ BS_W[regime] * (balance_sheet - 6)
+ PAY_W[regime] * (payout - 6)
```

`regime_fit_components()` exposes those five terms but `regime_scores()` still produces the same total.

Two different protections exist:

- a SHA-256 fingerprint protects the complete AFF / DUR_W / BS_W / PAY_W specification;
- golden fixtures protect formula behaviour, including NVDA 88.9 Goldilocks, ROAD 6.4 Stagflation, SAN 86.6 Recession, and both duration clamps.

A model change is allowed, but it must now be explicit: change the model version, contract hash, and expected fixtures together. Silent drift blocks the build.

## 2. EPV is a second valuation lens

`epv.py` implements the uploaded ValueInvesting.io EPV chain:

- 3-year sustainable revenue;
- 3-year sustainable gross margin;
- 3-year R&D + SG&A;
- selected/effective tax rate;
- 5-year average of capex minus D&A;
- normalised earnings / WACC = enterprise value;
- minus net debt = equity value;
- divided by shares = EPV per share.

The scoreboard shows:

```
NGV | EPV | EPV vs NGV | Entry@60%
```

The gap is `EPV / NGV - 1`. It is **diagnostic only**. It never changes Score, Risk, Verdict, Regime Fit or portfolio ranking.

The ValueInvesting.io sheet has a separately selected tax-rate assumption. Yahoo cannot recover that human choice reliably, so live EPV reports tax provenance. A row may set `epv_tax_rate=` to override Yahoo's latest effective rate.

Annual statement inputs are cached for seven days in `history/_epv_cache.json`; EPV is recomputed every run using the current WACC/manual fallback.

## 3. NGV-N/A no longer means price-N/A

Previously a row with `na=` skipped normal price fetching. That prevented an EPV-capable company such as a capital-intensive utility from receiving a price simply because NGV was structurally inappropriate.

Now `na=` means **NGV unavailable**. Price and momentum still fetch, and EPV may still be available.

## 4. Pure 30-name regime book

`regime_book(regime, 30)` orders only by current regime fit. Score, risk, NGV, EPV and current portfolio weight do not participate in ranking or tie-breaking. Exact fit ties are resolved alphabetically so output is deterministic.

## 5. Evidence quality stays separate

EPV confidence reports data coverage/provenance only. It is never multiplied into valuation or score. In particular, a Yahoo-derived current effective tax rate is flagged as less template-faithful than an explicit `epv_tax_rate` override.

## Validation performed

Offline validation for this package:

- Python compilation passed for `engine.py` and `epv.py`.
- 10 contract tests passed.
- 5,000 random factor combinations matched the uploaded pre-v2 `regime_scores()` exactly: **0 mismatches**.
- Apple EPV fixture from the uploaded `epv.py` reproduces **$62.86**.
- Historical Apple cells from the ValueInvesting.io EPV sheet reproduce **41.9352258307** and **58.7575306761** at the sheet's two WACC endpoints.
- HTML smoke build passed and atomic write left no `index.html.tmp` behind.
- A synthetic REFLATION build rendered the 30-name regime book and EPV/NGV columns.

## What was not validated here

No live Yahoo statement pull was executed in this environment. The first normal GitHub Actions run is therefore the correct place to populate `history/_epv_cache.json` and inspect live EPV coverage/tax provenance across the full universe.

## Repo installation

Copy into the repository:

```
engine.py
epv.py
test_framework_contract.py
.github/workflows/framework-contract.yml
```

Run locally:

```
python test_framework_contract.py
python engine.py
```

Do not delete the contract tests after the first successful deploy; their purpose is to make future model changes visible.

