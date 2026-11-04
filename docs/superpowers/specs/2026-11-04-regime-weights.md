# Regime weights and labour signal (2026-11-04)

Builds on `2026-11-04-scoreboard-review-corrections.md` (21-session mean
impulses). Schema `opportunity-v17.3`. Weights, bands, caps and the frozen
v15.1 fit formula are unchanged.

## Problem: a cliff at every regime boundary

The regime is a hard classification of two noisy scores at fixed boundaries
(growth 0; inflation 0 and 0.5). Rebuilding month-end readings for Jun 2025 -
Oct 2026 from the archived inputs gives a one-month standard deviation of 0.23
(growth score) and 0.34 (inflation score), and 10 regime changes in 16 months,
even with smoothed market inputs. Each change moves a stock's fit by up to 50
points (NVDA: REFLATION 63.5, INFLATION 13.3), i.e. up to 0.75 score points
through the 15% macro weight, without any change in the business.

## Correction: regime weights

`macro.regime_weights(gs, is)` treats next month's scores as normal around
today's with the observed one-month spread (`REGIME_SCORE_STEP`) and assigns
each regime the probability of its side of the boundaries:

    up   = Phi(gs / 0.23)
    hot  = Phi((is - 0.5) / 0.34),  warm = Phi(is / 0.34)
    INFLATION = up*hot   REFLATION = up*(warm-hot)   GOLDILOCKS = up*(1-warm)
    STAGFLATION = (1-up)*warm   RECESSION = (1-up)*(1-warm)

The opportunity macro component and the Buy/Strong Buy fit gates use the
weighted fit (sum of weight x regime fit; bounds combine the same way). The
current regime is still the most likely one and stays highlighted. Weights are
a statement about measurement noise, not a forecast. On 2026-11-04: INFLATION
59%, REFLATION 34%, GOLDILOCKS 4%, STAGFLATION 2%. Across the six recorded
single-close readings of 31 Oct - 4 Nov, NVDA's hard fit jumped between 13.3
and 63.5; the weighted fit stays within 34.9-43.4.

The calibration rows are in `tests/fixtures/regime_monthly_scores.json`;
`test_regime_weights` checks that the constants reproduce from them.

## Labour signal

The former labour input `(0.3 - gap) / 0.3` is a deterioration detector: an
unchanged unemployment rate (gap 0) read +1, the strongest growth signal.
`labour_signal` is now positive only if the rate fell over twelve months
(-0.5pp = +1) and the detector still caps it as soon as the rate rises from its
low. Flat reads 0. On 2026-11-04: -0.2pp over twelve months reads +0.4.

## Payroll breakeven

Estimates of the payroll growth that keeps unemployment steady in 2026 range
from under 10k (FEDS Notes, 2 Apr 2026) through 15-68k (AEI-Brookings) to 87k
(CBO); the Blue Chip consensus was 55k (St. Louis Fed, Mar 2026). The breakeven
moves from 75k to 50k (`PAYROLL_BREAKEVEN_THOUSANDS`), so 51k a month reads as
neutral rather than as contraction.

Sources:
- https://www.stlouisfed.org/on-the-economy/2026/mar/breakeven-employment-growth-estimate-range-widens-2026
- https://federalreserve.gov/econres/notes/feds-notes/labor-force-growth-breakeven-employment-and-potential-gdp-growth-20260402.html
