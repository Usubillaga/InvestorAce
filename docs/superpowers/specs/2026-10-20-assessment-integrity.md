# InvestorAce assessment integrity — 20 October 2026

## Intended outcome
Repair the existing valuation and publication flow so a legacy total, incomplete arithmetic, a source check and an approved investment rating cannot be confused. Preserve the eight nominal weights, golden regime formulas, immutable history, current holdings (50% cash / 30% WKL / 20% DIS), and absence of forced selling or rotation.

## Confirmed defects
At base 8521596aa5381e3d5b3086094e376ab78883f377:
- engine.score returns fixed historical totals, renormalizes missing expectations over 0.85, and supplies dilution=6. The main table, verdict and portfolio proposal can consume these as actionable results.
- Scanner, comparison and main report use different review rules. The comparison's model leader ignores review eligibility.
- EPV substitutes missing debt/cash with zero, mixes independent fiscal-year subsets, accepts invalid scalar inputs, and can cache nonfinite values.
- autoscore uses neutral scores for unknown inputs and can compare a TTM revenue numerator with a prior annual denominator.

## Repair design
1. Add a pure assessment contract beside legacy arithmetic. Report all eight nominal contributions; missing contributions remain null, without reweighting. Show supported score bounds and coverage. A fixed total remains separately identified. All consumer surfaces project this same frozen contract. Complete arithmetic is a model result, not approval.
2. Add a versioned, input-bound review register. Approval requires a complete score, a consistent declared valuation contract, verified normalization, dated category/source evidence, nonfuture review and valid quote. A changed financial/price/rate input invalidates approval. SOURCE_CHECKED alone never approves. An empty register contains no invented approvals.
3. Gate operative verdicts and new-entry proposals. Unreviewed rows retain research model values and raw historical calculations; they do not produce approved trade instructions or allocation slots. Raw regime rankings remain untouched. Existing holdings are never sold by a data gap.
4. Preserve missing automatic fundamentals and period consistency, including explicit partial category metadata. No neutral five or invented zero dividend/debt.
5. EPV windows use aligned fiscal-year inputs and finite scalar checks; debt and cash must be known to build net debt. Old cached inputs are invalidated. Disclosed R&D-zero and tax defaults remain assumptions with explicit confidence reasons. Valid Apple workbook fixtures must reproduce unchanged.

## Integration and validation
Files: assessment.py + assessment_reviews.json; engine.py; evidence.py; market_scanner.py; stock_compare.py; compare_duel.js; compare.js; autoscore.py; epv.py; translations; focused regression tests; README.
Run the existing offline Python suite, lint/import checks, financial duel tests and WACC reproduction. Reproduce each defect with a failing regression before implementation. Review final code independently, then verify publication. Never edit generated history by hand.

## Scope and limits
This repairs reproducibility and decision eligibility. It does not independently authenticate every company's financial statement, calibrate score bands, prove outperformance, or complete the missing Enagás hydrogen funding forecast. DCF case outputs remain conditional. A full sector-specific model migration, currency-specific risk-free curve and return/tax research remain separately documented review work, not silently changed formulas.
