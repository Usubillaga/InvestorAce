# Scoreboard review corrections (2026-11-04)

Three defects found while auditing the v17 regime reading and the opportunity
ranking. Weights, label boundaries, caps and the frozen v15.1 regime-fit
formula are unchanged.

## 1. Regime read from one noisy close

The market growth/inflation impulses are 6-month rates of change read at a
single close; both the endpoint and the base date move every session. Recorded
builds read the inflation impulse as 7.4, 4.4, 0.2, 0.4, 3.4 and 2.6 % between
30 Oct and 3 Nov 2026 while the official data (CPI 3.72 % y/y, +0.25 pp over 3
months; unemployment gap 0.00; payrolls +51k) did not change. The inflation
score sat at 0.44-0.51 around the 0.5 INFLATION/REFLATION edge, so the regime
flipped and NVDA's current fit moved 62 <-> 8 with an unchanged price.

Correction: the classifier reads the mean of the last 21 common-date sessions
of the aligned path (`REGIME_SMOOTHING_SESSIONS`), about one month, the cadence
of the official data it is combined with. Fewer than 21 sessions falls back to
the latest close and says so. The page shows the regime input and the margin
to the nearest regime boundary. On the 2026-11-04 03:09 build the smoothed
reading is growth +9.9 %, inflation +9.3 %, scores 0.55 / 0.59: INFLATION,
margin 0.09; each of the last five rolling windows gives the same regime.

## 2. Unlabelled rows sorted below Sell

The front page and the scanner sorted every row without a label after all
labelled rows. A bounded score whose interval spans a band edge is still known
to be at least its lower bound: Sanofi (6.92-7.29) was ranked 80th, below
Sell-rated Intel (2.89). Ranking now uses the capped lower bound for every row
with a price-current interval (`opportunity.rank_order`); at equal bounds a
labelled row comes first; rows without an interval stay last. Labels and the
"positive" filter are unchanged.

## 3. Leverage from an inconsistent provider EBITDA

EBITDA cannot be below EBIT on one basis. Yahoo's EBITDA row is derived from
pre-tax income and keeps unusual items its Operating Income row excludes.
Gilead (TTM 2026-09-30) read EBITDA 1.29bn vs operating income 11.70bn, so net
debt/EBITDA was 15.3x instead of ~1.7x, the balance score 1.5 and the value-trap
cap forced Hold Negative. Same pattern: GIS, INTC, SAN.PA, MO.

Correction (`live_analysis.leverage_ebitda`): when reported EBITDA is below a
positive operating income, leverage uses operating income plus D&A from the
same cash-flow periods, or operating income alone as a conservative floor
(it can understate EBITDA, never inflate it). A consistent provider EBITDA is
used unchanged. The basis is recorded in `parameters.leverage_ebitda_basis`
and the missing-cash balance bound uses the same figure. Reported negative net
income still scores P/E 0 and caps at Hold Positive, as specified.

## Open methodology points (not changed here)

- FCF yield (15 %) and reverse-DCF expectations (15 %) are both functions of
  FCF / price, so 30 % of the score is effectively one input.
- The current-regime fit moves a score by up to ~0.8 points (NVDA fit 62 vs 8);
  the regime is now stable, but its weight in the label is large.
- The labour signal maps an unchanged unemployment rate (gap 0) to +1, the
  maximum growth reading.
- Revenue growth for commodity producers uses one fiscal-year change (CNX
  +49 %), while their valuation uses multi-year averages.
