# Backtest of the technical rules · 2021-11-25 → 2026-11-25

Technical rules on current members. Historical membership and full label history are unavailable. Survivorship bias may affect strategies differently. Decision on close t, fill at close t+1, 0.10% per fill. Historical technical simulation uses local quote units and excludes FX. Compare variants within this simulation.

## 1 · After a close far above the 36-day average

| Distance to 36-day avg | days | stocks | 21-day mean | 63-day mean | 63-day vs S&P | P(−10% within 21 d) | P(63 d < 0) |
|---|---|---|---|---|---|---|---|
| -100..0% | 72428 | 130 | 1.37% | 4.32% | 0.97% | 25.6% | 46.87% |
| 0..10% | 61786 | 130 | 0.91% | 2.82% | 0.09% | 20.11% | 47.78% |
| 10..20% | 11593 | 128 | 1.47% | 5.2% | 2.52% | 29.69% | 47.83% |
| 20..30% | 2377 | 89 | 3.35% | 9.36% | 6.89% | 40.05% | 47.2% |
| 30..+% | 1645 | 57 | 6.71% | 17.74% | 15.4% | 51.0% | 46.5% |

## 2 · Breakouts above the prior 60-session high (in an uptrend) · failure rate 33.09%

| Case | days | 5-day mean | 21-day mean | 63-day mean | 63-day vs S&P |
|---|---|---|---|---|---|
| all_uptrend_days | 59924 | 0.35% | 1.52% | 4.77% | 1.67% |
| breakout_day | 3687 | 0.22% | 1.51% | 4.4% | 1.44% |
| breakout_failed | 1220 | -4.16% | -5.24% | -1.37% | -3.35% |
| breakout_held | 2467 | 2.4% | 4.84% | 7.26% | 3.81% |
| confirmed_second_close | 2666 | 0.2% | 1.69% | 4.76% | 1.73% |
| just_under_resistance | 17169 | 0.23% | 0.9% | 2.91% | -0.18% |

"breakout_failed" and "breakout_held" use the next 10 sessions to sort the cases, so they are not tradable signals; they show how much a failure costs.

## 3 · Portfolio simulation (10,000, max 8 positions)

| Variant | CAGR | max drawdown | Sharpe | trades | win rate | avg trade | avg days |
|---|---|---|---|---|---|---|---|
| base_v1_6 | 27.72% | -33.48% | 1.01 | 295 | 28.14% | 5.04% | 27.5 |
| base_v1_5 | 35.0% | -30.75% | 1.22 | 267 | 30.71% | 5.5% | 30.3 |
| no_buy_above_30pct_36d | 18.88% | -33.04% | 0.79 | 292 | 28.77% | 4.11% | 27.5 |
| sell_above_30pct_36d | 7.68% | -26.85% | 0.49 | 366 | 32.51% | 1.48% | 22.2 |
| wait_under_resistance | 21.83% | -32.87% | 0.82 | 304 | 26.64% | 3.5% | 27.2 |
| two_closes_above_resistance | 19.24% | -37.92% | 0.76 | 289 | 30.1% | 4.29% | 27.9 |
| sell_failed_breakout | 27.72% | -33.48% | 1.01 | 295 | 28.14% | 5.04% | 27.5 |
| two_closes_and_sell_failed | 34.46% | -34.33% | 1.12 | 282 | 31.56% | 6.03% | 28.4 |
| wait_res_and_sell_failed | 16.5% | -29.08% | 0.73 | 311 | 27.97% | 3.49% | 25.9 |
| kell_crossback_exit | 26.59% | -32.22% | 1.0 | 663 | 34.99% | 1.74% | 11.9 |
| kell_base_n_break_entry | 6.66% | -17.03% | 0.52 | 212 | 26.42% | 1.11% | 36.4 |
| kell_wedge_pop_entry | 9.17% | -18.57% | 0.62 | 218 | 29.36% | 1.64% | 33.6 |
| kell_full | 11.02% | -21.91% | 0.63 | 514 | 34.63% | 0.8% | 13.5 |
| buffer_200d_1pct | 27.72% | -33.48% | 1.01 | 295 | 28.14% | 5.04% | 27.5 |
| buffer_200d_2pct | 27.72% | -33.48% | 1.01 | 295 | 28.14% | 5.04% | 27.5 |
| buffer_200d_3pct | 27.72% | -33.48% | 1.01 | 295 | 28.14% | 5.04% | 27.5 |
| sell_all_in_correction | 32.13% | -26.57% | 1.1 | 366 | 35.25% | 4.0% | 20.8 |
| sell_all_weak_breadth | 8.83% | -28.7% | 0.51 | 672 | 39.88% | 1.25% | 11.1 |
| sell_all_correction_and_weak_breadth | 27.07% | -34.1% | 1.04 | 333 | 34.83% | 4.26% | 23.6 |
| shorts_in_correction | 33.29% | -36.26% | 1.07 | 412 | 32.04% | 3.73% | 22.4 |
| shorts_always | 25.67% | -33.14% | 0.9 | 549 | 32.24% | 2.45% | 23.8 |
| garch_position_size | 19.87% | -18.53% | 1.17 | 269 | 30.48% | 6.47% | 30.3 |
| ewma_position_size | 17.62% | -21.34% | 1.04 | 277 | 30.32% | 5.63% | 29.7 |
| garch_exposure | 29.77% | -32.9% | 1.13 | 284 | 32.39% | 6.0% | 28.7 |
| ewma_exposure | 34.66% | -30.59% | 1.22 | 281 | 30.6% | 6.46% | 28.9 |
| rebound_sleeve | 27.92% | -26.66% | 1.1 | 539 | 42.12% | 2.33% | 18.4 |
| rebound_sleeve_below_200d | 27.01% | -23.97% | 1.11 | 524 | 44.47% | 2.98% | 18.6 |
| rebound_sleeve_no_stop | 29.96% | -29.0% | 1.07 | 523 | 40.73% | 2.67% | 19.1 |

S&P 500 buy and hold: CAGR 9.35%, max drawdown -25.43%.

## 4 · Separate periods (same variants)

Members enter a period once they have 200 days of prices, so early periods hold fewer stocks.

### 2014-01-02 → 2017-12-29 · 101 stocks · S&P CAGR 9.94%, max drawdown -14.16%

Breakout failure rate 22.58% · 63-day mean: uptrend days 4.5%, just under resistance 4.21%, failed breakouts 0.35% · more than 30% above the 36-day average: n=210, 63-day 13.61%, P(−10% in 21 d) 53.33%

| Variant | CAGR | max drawdown | Sharpe | trades |
|---|---|---|---|---|
| base_v1_6 | 17.4% | -16.64% | 1.11 | 169 |
| base_v1_5 | 18.74% | -14.55% | 1.16 | 162 |
| no_buy_above_30pct_36d | 13.63% | -14.55% | 0.92 | 160 |
| sell_above_30pct_36d | 14.39% | -16.03% | 0.95 | 177 |
| wait_under_resistance | 16.75% | -15.7% | 1.08 | 147 |
| two_closes_above_resistance | 17.12% | -16.72% | 1.09 | 165 |
| sell_failed_breakout | 17.4% | -16.64% | 1.11 | 169 |
| two_closes_and_sell_failed | 14.7% | -17.7% | 0.97 | 162 |
| wait_res_and_sell_failed | 20.12% | -16.17% | 1.26 | 153 |
| kell_crossback_exit | 11.34% | -15.55% | 0.77 | 521 |
| kell_base_n_break_entry | 4.91% | -14.79% | 0.47 | 135 |
| kell_wedge_pop_entry | 11.26% | -15.33% | 0.88 | 187 |
| kell_full | 0.49% | -19.06% | 0.1 | 462 |
| buffer_200d_1pct | 17.4% | -16.64% | 1.11 | 169 |
| buffer_200d_2pct | 17.4% | -16.64% | 1.11 | 169 |
| buffer_200d_3pct | 17.4% | -16.64% | 1.11 | 169 |
| sell_all_in_correction | 15.08% | -13.78% | 1.07 | 212 |
| sell_all_weak_breadth | 12.31% | -14.94% | 0.82 | 175 |
| sell_all_correction_and_weak_breadth | 12.31% | -14.94% | 0.82 | 175 |
| shorts_in_correction | 13.26% | -27.77% | 0.86 | 226 |
| shorts_always | 9.07% | -20.35% | 0.55 | 369 |
| garch_position_size | 17.0% | -13.62% | 1.18 | 166 |
| ewma_position_size | 17.43% | -13.35% | 1.21 | 171 |
| garch_exposure | 15.58% | -16.12% | 0.98 | 165 |
| ewma_exposure | 16.76% | -15.07% | 1.11 | 162 |
| rebound_sleeve | 20.4% | -17.07% | 1.21 | 252 |
| rebound_sleeve_below_200d | 21.08% | -17.28% | 1.21 | 236 |
| rebound_sleeve_no_stop | 20.0% | -16.75% | 1.23 | 248 |

### 2018-01-02 → 2021-12-31 · 118 stocks · S&P CAGR 15.33%, max drawdown -33.92%

Breakout failure rate 31.0% · 63-day mean: uptrend days 5.36%, just under resistance 3.08%, failed breakouts 0.07% · more than 30% above the 36-day average: n=851, 63-day 18.69%, P(−10% in 21 d) 48.3%

| Variant | CAGR | max drawdown | Sharpe | trades |
|---|---|---|---|---|
| base_v1_6 | 25.95% | -21.15% | 1.06 | 208 |
| base_v1_5 | 33.34% | -20.2% | 1.29 | 199 |
| no_buy_above_30pct_36d | 31.47% | -20.22% | 1.24 | 187 |
| sell_above_30pct_36d | 32.18% | -20.39% | 1.43 | 236 |
| wait_under_resistance | 31.76% | -26.68% | 1.24 | 222 |
| two_closes_above_resistance | 27.73% | -21.63% | 1.12 | 202 |
| sell_failed_breakout | 25.95% | -21.15% | 1.06 | 208 |
| two_closes_and_sell_failed | 25.33% | -20.58% | 1.05 | 213 |
| wait_res_and_sell_failed | 29.0% | -29.65% | 1.11 | 230 |
| kell_crossback_exit | 30.3% | -23.15% | 1.19 | 572 |
| kell_base_n_break_entry | 21.19% | -14.74% | 1.27 | 148 |
| kell_wedge_pop_entry | 13.12% | -17.23% | 0.75 | 184 |
| kell_full | 14.98% | -22.5% | 0.81 | 467 |
| buffer_200d_1pct | 30.68% | -20.18% | 1.21 | 212 |
| buffer_200d_2pct | 30.68% | -20.18% | 1.21 | 212 |
| buffer_200d_3pct | 30.68% | -20.18% | 1.21 | 212 |
| sell_all_in_correction | 25.7% | -23.29% | 1.09 | 296 |
| sell_all_weak_breadth | 24.95% | -18.66% | 1.04 | 231 |
| sell_all_correction_and_weak_breadth | 24.95% | -18.66% | 1.04 | 231 |
| shorts_in_correction | 27.81% | -26.46% | 1.06 | 293 |
| shorts_always | 22.6% | -30.3% | 0.87 | 454 |
| garch_position_size | 21.09% | -14.67% | 1.24 | 192 |
| ewma_position_size | 17.39% | -17.79% | 1.01 | 211 |
| garch_exposure | 32.51% | -16.02% | 1.42 | 199 |
| ewma_exposure | 24.79% | -17.03% | 1.14 | 210 |
| rebound_sleeve | 35.02% | -26.29% | 1.34 | 353 |
| rebound_sleeve_below_200d | 42.16% | -31.12% | 1.52 | 329 |
| rebound_sleeve_no_stop | 32.24% | -27.8% | 1.25 | 332 |

### 2022-01-03 → 2026-11-25 · 130 stocks · S&P CAGR 8.6%, max drawdown -25.43%

Breakout failure rate 33.17% · 63-day mean: uptrend days 5.02%, just under resistance 3.05%, failed breakouts -1.25% · more than 30% above the 36-day average: n=1643, 63-day 17.8%, P(−10% in 21 d) 50.94%

| Variant | CAGR | max drawdown | Sharpe | trades |
|---|---|---|---|---|
| base_v1_6 | 33.02% | -33.8% | 1.18 | 277 |
| base_v1_5 | 30.92% | -31.14% | 1.12 | 259 |
| no_buy_above_30pct_36d | 27.59% | -26.74% | 1.07 | 263 |
| sell_above_30pct_36d | 10.88% | -24.83% | 0.67 | 344 |
| wait_under_resistance | 31.59% | -27.17% | 1.13 | 272 |
| two_closes_above_resistance | 45.64% | -27.83% | 1.44 | 266 |
| sell_failed_breakout | 33.02% | -33.8% | 1.18 | 277 |
| two_closes_and_sell_failed | 32.13% | -32.66% | 1.12 | 278 |
| wait_res_and_sell_failed | 40.05% | -32.05% | 1.27 | 287 |
| kell_crossback_exit | 22.02% | -31.23% | 0.89 | 643 |
| kell_base_n_break_entry | 4.08% | -17.21% | 0.37 | 214 |
| kell_wedge_pop_entry | 6.79% | -19.15% | 0.51 | 215 |
| kell_full | 8.51% | -28.65% | 0.52 | 511 |
| buffer_200d_1pct | 33.02% | -33.8% | 1.18 | 277 |
| buffer_200d_2pct | 33.02% | -33.8% | 1.18 | 277 |
| buffer_200d_3pct | 33.02% | -33.8% | 1.18 | 277 |
| sell_all_in_correction | 32.0% | -28.93% | 1.2 | 351 |
| sell_all_weak_breadth | 17.56% | -24.41% | 0.76 | 653 |
| sell_all_correction_and_weak_breadth | 31.48% | -34.17% | 1.1 | 324 |
| shorts_in_correction | 38.61% | -33.34% | 1.22 | 402 |
| shorts_always | 28.36% | -33.36% | 0.93 | 545 |
| garch_position_size | 20.58% | -19.1% | 1.23 | 253 |
| ewma_position_size | 21.35% | -20.87% | 1.25 | 257 |
| garch_exposure | 31.84% | -33.47% | 1.18 | 266 |
| ewma_exposure | 34.97% | -31.73% | 1.25 | 259 |
| rebound_sleeve | 15.65% | -27.96% | 0.73 | 534 |
| rebound_sleeve_below_200d | 27.91% | -32.1% | 1.11 | 526 |
| rebound_sleeve_no_stop | 29.27% | -24.32% | 1.08 | 524 |

### Robustness: windows in which a variant beat base_v1_6 (the current rules)

| Variant | CAGR | max drawdown (less deep) | Sharpe |
|---|---|---|---|
| no_buy_above_30pct_36d | 1/3 | 3/3 | 1/3 |
| sell_above_30pct_36d | 1/3 | 3/3 | 1/3 |
| wait_under_resistance | 1/3 | 2/3 | 1/3 |
| two_closes_above_resistance | 2/3 | 1/3 | 2/3 |
| sell_failed_breakout | 0/3 | 0/3 | 0/3 |
| two_closes_and_sell_failed | 0/3 | 2/3 | 0/3 |
| wait_res_and_sell_failed | 3/3 | 2/3 | 3/3 |
| kell_crossback_exit | 1/3 | 2/3 | 1/3 |
| kell_base_n_break_entry | 0/3 | 3/3 | 1/3 |
| kell_wedge_pop_entry | 0/3 | 3/3 | 0/3 |
| kell_full | 0/3 | 1/3 | 0/3 |
| buffer_200d_1pct | 1/3 | 1/3 | 1/3 |
| buffer_200d_2pct | 1/3 | 1/3 | 1/3 |
| buffer_200d_3pct | 1/3 | 1/3 | 1/3 |
| sell_all_in_correction | 0/3 | 2/3 | 2/3 |
| sell_all_weak_breadth | 0/3 | 3/3 | 0/3 |
| sell_all_correction_and_weak_breadth | 0/3 | 2/3 | 0/3 |
| shorts_in_correction | 2/3 | 1/3 | 1/3 |
| shorts_always | 0/3 | 1/3 | 0/3 |
| garch_position_size | 0/3 | 3/3 | 3/3 |
| ewma_position_size | 1/3 | 3/3 | 2/3 |
| garch_exposure | 1/3 | 3/3 | 1/3 |
| ewma_exposure | 1/3 | 3/3 | 2/3 |
| rebound_sleeve | 2/3 | 1/3 | 2/3 |
| rebound_sleeve_below_200d | 2/3 | 1/3 | 2/3 |
| rebound_sleeve_no_stop | 2/3 | 1/3 | 2/3 |

Symbols: 130 · generated 2026-11-27T21:28+00:00 · price data 06c58425f20ed845

## Valuation coverage

Positions carry their last observed close on missing dates. No execution at a carried price. Extended gaps and terminal gaps leave delisting proceeds unresolved.

| Variant | Longest gap (sessions) | Missing on final date |
|---|---|---|
| base_v1_6 | 1 | None |
| base_v1_5 | 1 | None |
| no_buy_above_30pct_36d | 1 | None |
| sell_above_30pct_36d | 1 | None |
| wait_under_resistance | 1 | None |
| two_closes_above_resistance | 1 | None |
| sell_failed_breakout | 1 | None |
| two_closes_and_sell_failed | 1 | None |
| wait_res_and_sell_failed | 1 | None |
| kell_crossback_exit | 1 | None |
| kell_base_n_break_entry | 1 | None |
| kell_wedge_pop_entry | 1 | None |
| kell_full | 1 | None |
| buffer_200d_1pct | 1 | None |
| buffer_200d_2pct | 1 | None |
| buffer_200d_3pct | 1 | None |
| sell_all_in_correction | 1 | None |
| sell_all_weak_breadth | 1 | None |
| sell_all_correction_and_weak_breadth | 1 | None |
| shorts_in_correction | 1 | None |
| shorts_always | 1 | None |
| garch_position_size | 1 | None |
| ewma_position_size | 1 | None |
| garch_exposure | 1 | None |
| ewma_exposure | 1 | None |
| rebound_sleeve | 1 | None |
| rebound_sleeve_below_200d | 1 | None |
| rebound_sleeve_no_stop | 1 | None |

## SMA200 buffer divergence: v1.6 versus 1%

Contributions include entry and exit costs, size changes and ending marks on open positions. Subsequent entries describe the portfolio path; an individual replacement is not necessarily causal.

### 2021-11-25 → 2026-11-25

Order plans identical.

Ending equity difference: +0.00; total-return difference +0.00 percentage points. Differing positions: 0.

buffer_200d_2pct vs 1%: order plans identical = True, executed positions identical = True.
buffer_200d_3pct vs 1%: order plans identical = True, executed positions identical = True.

### 2014-01-02 → 2017-12-29

Order plans identical.

Ending equity difference: +0.00; total-return difference +0.00 percentage points. Differing positions: 0.

buffer_200d_2pct vs 1%: order plans identical = True, executed positions identical = True.
buffer_200d_3pct vs 1%: order plans identical = True, executed positions identical = True.

### 2018-01-02 → 2021-12-31

First differing order plan on 2018-10-12 (side, symbol, shares): v1.6 only [('BUY', 'B', 133)], 1% only [].

Ending equity difference: +3984.03; total-return difference +39.84 percentage points. Differing positions: 233.

Two largest positive contributions: 34.2% of gross positive contributions. This describes concentration within this historical path.

Largest positive lot: BBW entered 2021-04-26, +28.839 total-return pp.
Largest positive lot: MRNA entered 2021-06-21, +27.387 total-return pp.

First differing fills and subsequent positions (first 10; complete ledger in backtests/latest.json).

| Entry | Symbol | v1.6 shares | 1% shares | Difference in total return (pp) |
|---|---|---:|---:|---:|
| 2018-10-15 | B | 133 | 0 | +0.201 |
| 2018-10-17 | O | 0 | 37 | +5.939 |
| 2018-11-08 | ALM | 95 | 96 | -0.009 |
| 2018-11-08 | BSX | 36 | 37 | -0.019 |
| 2018-12-04 | AMD | 57 | 58 | -0.012 |
| 2018-12-04 | MCD | 0 | 8 | -0.750 |
| 2018-12-04 | O | 32 | 0 | +0.266 |
| 2018-12-04 | TTD | 92 | 93 | -0.017 |
| 2019-02-13 | AVGO | 56 | 57 | -0.015 |
| 2019-02-13 | ELE | 96 | 98 | +0.074 |

buffer_200d_2pct vs 1%: order plans identical = True, executed positions identical = True.
buffer_200d_3pct vs 1%: order plans identical = True, executed positions identical = True.

### 2022-01-03 → 2026-11-25

Order plans identical.

Ending equity difference: +0.00; total-return difference +0.00 percentage points. Differing positions: 0.

buffer_200d_2pct vs 1%: order plans identical = True, executed positions identical = True.
buffer_200d_3pct vs 1%: order plans identical = True, executed positions identical = True.


## Start-date sensitivity (paired with v1.6)

Each row compares a variant with v1.6 started on the same day with the same capital. Wins / ties / losses count ending equity; Δ columns show median [min, max] of the paired differences. The starts overlap, so the counts describe sensitivity to the start date, not a probability of future outperformance.

### 2014-01-02 → 2017-12-29

20 paired starts. Counts use unrounded ending equity.

| Variant | W / T / L | Original start ΔCAGR | ΔCAGR | ΔMax DD | ΔSharpe |
|---|---|---:|---|---|---|
| base_v1_5 | 5 / 0 / 15 | +1.34 | -1.23 [-7.37, +1.84] | +0.04 [-2.16, +4.14] | -0.07 [-0.37, +0.07] |
| no_buy_above_30pct_36d | 0 / 0 / 20 | -3.77 | -5.86 [-9.87, -0.43] | +0.04 [-2.16, +4.14] | -0.28 [-0.49, -0.03] |
| sell_above_30pct_36d | 1 / 0 / 19 | -3.01 | -2.70 [-9.65, +1.97] | +0.13 [-4.16, +2.34] | -0.12 [-0.49, +0.15] |
| wait_under_resistance | 6 / 0 / 14 | -0.65 | -1.57 [-4.73, +2.50] | +1.60 [-0.45, +4.09] | -0.03 [-0.26, +0.11] |
| two_closes_above_resistance | 5 / 0 / 15 | -0.28 | -1.37 [-4.03, +3.73] | -1.44 [-3.74, +2.95] | -0.07 [-0.24, +0.18] |
| sell_failed_breakout | 0 / 20 / 0 | +0.00 | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] |
| two_closes_and_sell_failed | 4 / 0 / 16 | -2.70 | -2.36 [-6.33, +2.42] | -1.89 [-7.11, +0.93] | -0.11 [-0.32, +0.13] |
| wait_res_and_sell_failed | 12 / 0 / 8 | +2.72 | +0.54 [-4.93, +4.21] | +0.57 [-2.63, +4.71] | +0.04 [-0.25, +0.22] |
| kell_crossback_exit | 0 / 0 / 20 | -6.06 | -9.59 [-15.72, -3.62] | -0.52 [-3.59, +3.18] | -0.54 [-0.87, -0.20] |
| kell_base_n_break_entry | 0 / 0 / 20 | -12.49 | -15.89 [-21.27, -10.91] | -0.44 [-8.10, +4.00] | -0.82 [-1.21, -0.55] |
| kell_wedge_pop_entry | 1 / 0 / 19 | -6.14 | -10.27 [-15.50, +0.07] | -1.48 [-5.46, +1.97] | -0.37 [-0.70, +0.17] |
| kell_full | 0 / 0 / 20 | -16.91 | -15.48 [-18.89, -10.60] | -2.54 [-4.57, -0.28] | -0.81 [-1.06, -0.61] |
| buffer_200d_1pct | 0 / 20 / 0 | +0.00 | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] |
| buffer_200d_2pct | 0 / 19 / 1 | +0.00 | +0.00 [-1.44, +0.00] | +0.00 [+0.00, +0.00] | +0.00 [-0.08, +0.00] |
| buffer_200d_3pct | 0 / 19 / 1 | +0.00 | +0.00 [-1.44, +0.00] | +0.00 [+0.00, +0.00] | +0.00 [-0.08, +0.00] |
| sell_all_in_correction | 0 / 0 / 20 | -2.32 | -4.51 [-9.88, -1.47] | +1.03 [-2.69, +4.53] | -0.17 [-0.49, +0.02] |
| sell_all_weak_breadth | 2 / 0 / 18 | -5.09 | -4.84 [-7.54, +0.73] | +0.56 [-1.60, +2.82] | -0.26 [-0.39, +0.04] |
| sell_all_correction_and_weak_breadth | 2 / 0 / 18 | -5.09 | -4.84 [-7.54, +0.73] | +0.56 [-1.60, +2.82] | -0.26 [-0.39, +0.04] |
| shorts_in_correction | 0 / 0 / 20 | -4.14 | -3.33 [-5.99, -0.93] | -6.84 [-11.13, -4.47] | -0.20 [-0.33, -0.09] |
| shorts_always | 0 / 0 / 20 | -8.33 | -9.77 [-17.52, -4.57] | -5.27 [-8.52, -2.34] | -0.62 [-0.99, -0.38] |
| garch_position_size | 6 / 0 / 14 | -0.40 | -0.67 [-3.07, +3.38] | +2.30 [-1.17, +6.03] | +0.08 [-0.06, +0.29] |
| ewma_position_size | 3 / 0 / 17 | +0.03 | -2.57 [-5.37, +1.57] | +2.44 [-3.86, +3.68] | -0.02 [-0.20, +0.21] |
| garch_exposure | 3 / 0 / 17 | -1.82 | -2.02 [-5.16, +1.09] | -1.19 [-3.45, +1.82] | -0.13 [-0.31, +0.05] |
| ewma_exposure | 3 / 0 / 17 | -0.64 | -1.78 [-3.33, +0.82] | -0.19 [-1.58, +1.68] | -0.07 [-0.16, +0.06] |
| rebound_sleeve | 13 / 0 / 7 | +3.00 | +0.69 [-4.42, +3.41] | -3.18 [-9.51, -0.03] | +0.01 [-0.26, +0.15] |
| rebound_sleeve_below_200d | 11 / 0 / 9 | +3.68 | +0.08 [-3.57, +6.06] | -3.11 [-8.54, +0.17] | -0.03 [-0.18, +0.26] |
| rebound_sleeve_no_stop | 12 / 0 / 8 | +2.60 | +0.49 [-5.02, +4.32] | -2.32 [-9.97, +0.49] | +0.00 [-0.29, +0.15] |

### 2018-01-02 → 2021-12-31

20 paired starts. Counts use unrounded ending equity.

| Variant | W / T / L | Original start ΔCAGR | ΔCAGR | ΔMax DD | ΔSharpe |
|---|---|---:|---|---|---|
| base_v1_5 | 14 / 0 / 6 | +7.39 | +2.54 [-8.25, +14.42] | -0.72 [-4.37, +1.24] | +0.04 [-0.25, +0.35] |
| no_buy_above_30pct_36d | 10 / 0 / 10 | +5.51 | +0.01 [-7.93, +7.38] | +1.20 [-2.33, +4.76] | +0.00 [-0.22, +0.23] |
| sell_above_30pct_36d | 13 / 0 / 7 | +6.23 | +2.23 [-9.94, +11.88] | +2.36 [-1.42, +5.71] | +0.24 [-0.19, +0.53] |
| wait_under_resistance | 10 / 0 / 10 | +5.80 | -0.37 [-8.05, +5.80] | -4.14 [-7.24, +2.79] | -0.03 [-0.21, +0.21] |
| two_closes_above_resistance | 5 / 0 / 15 | +1.78 | -1.61 [-8.25, +7.79] | +1.30 [-3.16, +4.13] | -0.06 [-0.24, +0.25] |
| sell_failed_breakout | 0 / 20 / 0 | +0.00 | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] |
| two_closes_and_sell_failed | 7 / 0 / 13 | -0.63 | -1.77 [-6.99, +10.20] | +2.22 [-3.38, +5.02] | -0.06 [-0.19, +0.28] |
| wait_res_and_sell_failed | 7 / 0 / 13 | +3.05 | -3.38 [-16.77, +11.09] | -7.26 [-15.74, +0.56] | -0.09 [-0.52, +0.33] |
| kell_crossback_exit | 12 / 0 / 8 | +4.35 | +1.12 [-5.53, +6.37] | -0.44 [-6.70, +3.19] | +0.05 [-0.18, +0.18] |
| kell_base_n_break_entry | 0 / 0 / 20 | -4.77 | -12.44 [-18.29, -3.76] | +7.18 [+3.24, +8.61] | -0.04 [-0.29, +0.22] |
| kell_wedge_pop_entry | 0 / 0 / 20 | -12.83 | -10.85 [-16.84, -3.85] | +6.53 [+3.29, +8.34] | -0.11 [-0.39, +0.05] |
| kell_full | 0 / 0 / 20 | -10.97 | -17.63 [-21.90, -10.08] | -0.98 [-4.88, +0.65] | -0.47 [-0.65, -0.24] |
| buffer_200d_1pct | 8 / 0 / 12 | +4.73 | -1.66 [-8.43, +10.29] | +0.54 [-3.78, +5.07] | -0.04 [-0.25, +0.31] |
| buffer_200d_2pct | 9 / 0 / 11 | +4.73 | -0.83 [-8.43, +10.29] | +0.54 [-3.78, +5.07] | -0.01 [-0.25, +0.31] |
| buffer_200d_3pct | 9 / 0 / 11 | +4.73 | -0.83 [-8.43, +10.29] | +0.54 [-3.78, +5.07] | -0.01 [-0.25, +0.31] |
| sell_all_in_correction | 9 / 0 / 11 | -0.25 | -0.18 [-7.21, +11.45] | +3.21 [-2.15, +6.95] | +0.02 [-0.22, +0.37] |
| sell_all_weak_breadth | 8 / 0 / 12 | -1.00 | -0.33 [-7.64, +7.34] | +3.56 [-0.68, +6.92] | -0.00 [-0.22, +0.23] |
| sell_all_correction_and_weak_breadth | 8 / 0 / 12 | -1.00 | -0.33 [-7.64, +7.34] | +3.56 [-0.68, +6.92] | -0.00 [-0.22, +0.23] |
| shorts_in_correction | 7 / 0 / 13 | +1.86 | -1.42 [-13.75, +3.29] | -3.25 [-7.09, +0.20] | -0.10 [-0.47, +0.09] |
| shorts_always | 0 / 0 / 20 | -3.35 | -11.59 [-19.77, -1.84] | -10.77 [-16.26, -7.45] | -0.42 [-0.68, -0.14] |
| garch_position_size | 0 / 0 / 20 | -4.86 | -13.14 [-17.22, -4.64] | +6.32 [+3.26, +8.99] | -0.11 [-0.34, +0.18] |
| ewma_position_size | 0 / 0 / 20 | -8.56 | -14.06 [-16.84, -4.57] | +4.63 [+1.74, +7.64] | -0.19 [-0.31, +0.06] |
| garch_exposure | 14 / 0 / 6 | +6.55 | +0.84 [-4.30, +11.26] | +5.34 [+1.38, +8.94] | +0.18 [-0.00, +0.44] |
| ewma_exposure | 0 / 0 / 20 | -1.16 | -10.92 [-19.31, -1.16] | +4.84 [+1.79, +7.61] | -0.24 [-0.54, +0.09] |
| rebound_sleeve | 16 / 0 / 4 | +9.07 | +7.75 [-2.21, +16.39] | -4.24 [-9.61, +0.20] | +0.15 [-0.09, +0.48] |
| rebound_sleeve_below_200d | 16 / 0 / 4 | +16.21 | +6.96 [-2.61, +16.21] | -6.47 [-10.03, -1.92] | +0.18 [-0.08, +0.47] |
| rebound_sleeve_no_stop | 18 / 0 / 2 | +6.29 | +6.83 [-4.18, +20.33] | -3.62 [-9.76, +0.61] | +0.21 [-0.17, +0.55] |

### 2022-01-03 → 2026-11-25

20 paired starts. Counts use unrounded ending equity.

| Variant | W / T / L | Original start ΔCAGR | ΔCAGR | ΔMax DD | ΔSharpe |
|---|---|---:|---|---|---|
| base_v1_5 | 13 / 0 / 7 | -2.11 | +2.80 [-13.50, +19.44] | +1.29 [-2.10, +6.22] | +0.06 [-0.25, +0.42] |
| no_buy_above_30pct_36d | 6 / 0 / 14 | -5.43 | -1.75 [-21.24, +2.35] | +0.75 [-0.83, +7.40] | -0.05 [-0.40, -0.01] |
| sell_above_30pct_36d | 0 / 0 / 20 | -22.14 | -23.08 [-30.02, -7.37] | +4.51 [-1.23, +8.97] | -0.61 [-0.65, -0.07] |
| wait_under_resistance | 9 / 0 / 11 | -1.43 | -1.01 [-13.70, +8.97] | +1.42 [-4.92, +7.73] | -0.06 [-0.32, +0.17] |
| two_closes_above_resistance | 14 / 0 / 6 | +12.61 | +3.48 [-7.92, +28.01] | +2.40 [-2.68, +5.97] | +0.05 [-0.12, +0.50] |
| sell_failed_breakout | 0 / 20 / 0 | +0.00 | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] |
| two_closes_and_sell_failed | 15 / 0 / 5 | -0.89 | +5.21 [-2.41, +17.86] | +3.21 [-5.67, +7.82] | +0.05 [-0.06, +0.49] |
| wait_res_and_sell_failed | 9 / 0 / 11 | +7.03 | -2.24 [-14.44, +7.68] | -0.45 [-6.00, +3.00] | -0.13 [-0.33, +0.13] |
| kell_crossback_exit | 1 / 0 / 19 | -11.00 | -4.47 [-16.71, +0.86] | +1.88 [-1.38, +15.52] | -0.13 [-0.42, +0.04] |
| kell_base_n_break_entry | 0 / 0 / 20 | -28.94 | -27.30 [-37.44, -17.00] | +15.38 [+11.94, +20.05] | -0.66 [-0.95, -0.46] |
| kell_wedge_pop_entry | 0 / 0 / 20 | -26.24 | -25.63 [-35.70, -15.64] | +14.36 [+10.10, +19.56] | -0.62 [-0.86, -0.27] |
| kell_full | 0 / 0 / 20 | -24.51 | -22.93 [-31.57, -17.52] | +7.42 [+2.86, +9.84] | -0.63 [-0.74, -0.39] |
| buffer_200d_1pct | 0 / 20 / 0 | +0.00 | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] |
| buffer_200d_2pct | 0 / 20 / 0 | +0.00 | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] |
| buffer_200d_3pct | 1 / 19 / 0 | +0.00 | +0.00 [+0.00, +1.56] | +0.00 [-0.81, +0.00] | +0.00 [+0.00, +0.00] |
| sell_all_in_correction | 11 / 0 / 9 | -1.02 | +4.92 [-5.70, +19.86] | +4.86 [+0.27, +10.95] | +0.08 [-0.15, +0.37] |
| sell_all_weak_breadth | 0 / 0 / 20 | -15.47 | -11.39 [-23.85, -4.16] | +3.01 [-5.30, +9.39] | -0.29 [-0.57, -0.12] |
| sell_all_correction_and_weak_breadth | 12 / 0 / 8 | -1.55 | +4.14 [-9.56, +13.86] | +3.38 [-4.60, +7.37] | +0.06 [-0.26, +0.35] |
| shorts_in_correction | 11 / 0 / 9 | +5.58 | +0.72 [-19.48, +10.51] | -1.51 [-5.66, +2.79] | -0.16 [-0.42, +0.12] |
| shorts_always | 1 / 0 / 19 | -4.67 | -9.46 [-26.43, +0.59] | -3.83 [-8.53, +1.87] | -0.35 [-0.68, -0.06] |
| garch_position_size | 0 / 0 / 20 | -12.44 | -9.45 [-18.76, -0.06] | +12.91 [+9.51, +17.06] | +0.19 [-0.03, +0.39] |
| ewma_position_size | 0 / 0 / 20 | -11.68 | -10.46 [-23.08, -2.22] | +9.91 [+5.95, +13.74] | +0.10 [-0.25, +0.35] |
| garch_exposure | 14 / 0 / 6 | -1.19 | +3.15 [-11.35, +14.21] | -1.75 [-4.81, +3.23] | +0.10 [-0.14, +0.25] |
| ewma_exposure | 15 / 0 / 5 | +1.95 | +5.67 [-6.67, +15.38] | +1.88 [-6.60, +6.29] | +0.13 [-0.08, +0.27] |
| rebound_sleeve | 3 / 0 / 17 | -17.37 | -10.09 [-27.07, +6.46] | +2.84 [-2.35, +9.46] | -0.17 [-0.54, +0.17] |
| rebound_sleeve_below_200d | 3 / 0 / 17 | -5.12 | -4.54 [-19.20, +8.99] | +2.15 [-1.71, +11.68] | -0.08 [-0.42, +0.18] |
| rebound_sleeve_no_stop | 3 / 0 / 17 | -3.75 | -11.77 [-22.65, +9.82] | -0.54 [-5.43, +9.48] | -0.20 [-0.54, +0.27] |


## Pairs trading (same-sector, Engle-Granger + Ornstein-Uhlenbeck)

Yearly formation on 504 sessions, entry |z|>2, exit |z|<0.5, stop |z|>4, dollar-neutral 5% legs, 0.1% per fill, 2% borrow. Passes only with a positive return and Sharpe ≥ 0.5 in every period.

| Method | Period | Pairs/year | CAGR | Sharpe | Max DD | Trades | Win rate | Corr. S&P |
|---|---|---|---:|---:|---:|---:|---:|---:|
| pairs_static | 2014-01-01 → 2018-01-01 | 7,6,5 | -2.6 | -0.91 | -8.67 | 61 | 34.4 | -0.0 |
| pairs_static | 2018-01-01 → 2022-01-01 | 10,4,6,10 | -1.28 | -0.31 | -8.04 | 122 | 32.8 | 0.15 |
| pairs_static | 2022-01-01 → now | 10,4,8,6,3 | 0.51 | 0.15 | -5.99 | 126 | 41.3 | 0.1 |
| pairs_static | **fails** | | | | | | | |
| pairs_kalman | 2014-01-01 → 2018-01-01 | 7,6,5 | 0.45 | 0.13 | -7.56 | 146 | 46.6 | -0.02 |
| pairs_kalman | 2018-01-01 → 2022-01-01 | 10,4,6,10 | -1.39 | -0.42 | -6.51 | 258 | 47.7 | 0.11 |
| pairs_kalman | 2022-01-01 → now | 10,4,8,6,3 | -0.32 | -0.1 | -6.41 | 217 | 54.4 | -0.01 |
| pairs_kalman | **fails** | | | | | | | |

## Index ETF timing (SPY, QQQ, DAX, DIA, IWM; equal weight)

Rules against buy and hold from 20 paired starts per period. Costs 0.1% per position change, 2% a year borrow on shorts, cash earns nothing, no stops. Passes only with a positive median ΔCAGR and ΔSharpe in every period.

| Period | Rule | Beats buy & hold | Median CAGR | ΔCAGR median [min, max] | ΔSharpe median | ΔMax DD median |
|---|---|---|---:|---|---:|---:|
| 2014-01-02 → 2017-12-29 | buy_and_hold | — | 12.02% | — | — | — |
| 2014-01-02 → 2017-12-29 | codex_20d_5d_long_short | 0/20 | -16.50% | -29.29 [-30.42, -28.40] | -2.79 | -33.90 |
| 2014-01-02 → 2017-12-29 | codex_20d_5d_long_only | 0/20 | -4.48% | -17.25 [-18.19, -16.72] | -1.68 | -4.88 |
| 2014-01-02 → 2017-12-29 | trend_200d | 0/20 | 8.56% | -4.21 [-4.43, -4.02] | -0.09 | +3.46 |
| 2014-01-02 → 2017-12-29 | codex_intraday_account | 0/20 | -27.92% | -40.87 [-41.82, -39.96] | -7.28 | -54.33 |
| 2018-01-02 → 2021-12-31 | buy_and_hold | — | 14.54% | — | — | — |
| 2018-01-02 → 2021-12-31 | codex_20d_5d_long_short | 0/20 | -8.30% | -23.38 [-25.33, -21.24] | -1.15 | -4.97 |
| 2018-01-02 → 2021-12-31 | codex_20d_5d_long_only | 0/20 | 2.17% | -12.94 [-13.91, -11.46] | -0.48 | +24.82 |
| 2018-01-02 → 2021-12-31 | trend_200d | 0/20 | 7.85% | -6.99 [-7.12, -6.79] | -0.08 | +18.78 |
| 2018-01-02 → 2021-12-31 | codex_intraday_account | 0/20 | -25.59% | -40.58 [-42.15, -38.68] | -5.30 | -32.76 |
| 2022-01-03 → 2026-11-27 | buy_and_hold | — | 9.36% | — | — | — |
| 2022-01-03 → 2026-11-27 | codex_20d_5d_long_short | 0/20 | -9.39% | -21.13 [-26.44, -18.54] | -1.38 | -21.46 |
| 2022-01-03 → 2026-11-27 | codex_20d_5d_long_only | 0/20 | 1.55% | -10.55 [-13.92, -8.91] | -0.52 | +13.57 |
| 2022-01-03 → 2026-11-27 | trend_200d | 0/20 | 8.19% | -3.77 [-6.68, -2.86] | +0.02 | +12.63 |
| 2022-01-03 → 2026-11-27 | codex_intraday_account | 0/20 | -24.55% | -36.62 [-40.92, -33.80] | -5.02 | -50.88 |

Passes: codex_20d_5d_long_short no, codex_20d_5d_long_only no, trend_200d no, codex_intraday_account no


## Buy the oversold dip, sell the rebound

Signal: three red closes and at least 3 ATR under the 21-day EMA. Entry at the signal close, exit at the first close above the 10-day EMA or after 10 sessions; stop 8% (close) unless "no_stop"; 0.1% cost per side. Passes only with at least 30 trades and a positive mean and median excess over the S&P 500 in every period.

| Period | Variant | Trades | Win rate | Mean | Median | Mean vs S&P | Median vs S&P | Worst | 5th pct | Stops |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2014-01-02 → 2017-12-29 | all | 314 | 66% | +1.31% | +2.03% | +0.51% | +0.55% | -24.82% | -10.46% | 12% |
| 2014-01-02 → 2017-12-29 | above_sma200 | 54 | 72% | +1.67% | +2.41% | +0.85% | +1.42% | -9.22% | -8.57% | 7% |
| 2014-01-02 → 2017-12-29 | below_sma200 | 265 | 65% | +1.15% | +1.95% | +0.36% | +0.49% | -24.82% | -10.68% | 13% |
| 2014-01-02 → 2017-12-29 | all_no_stop | 300 | 66% | +1.17% | +2.03% | +0.33% | +0.56% | -33.26% | -11.01% | 0% |
| 2014-01-02 → 2017-12-29 | below_sma200_no_stop | 252 | 65% | +0.97% | +1.98% | +0.14% | +0.53% | -33.26% | -11.54% | 0% |
| 2014-01-02 → 2017-12-29 | at_weekly_sma200 | 8 | 25% | -3.18% | -3.92% | -3.61% | -3.94% | -9.13% | -9.13% | 12% |
| 2014-01-02 → 2017-12-29 | at_weekly_sma200_no_stop | 8 | 25% | -3.06% | -3.92% | -3.36% | -3.94% | -8.13% | -8.13% | 0% |
| 2018-01-02 → 2021-12-31 | all | 431 | 58% | +1.00% | +2.08% | +1.07% | +0.82% | -52.11% | -15.94% | 23% |
| 2018-01-02 → 2021-12-31 | above_sma200 | 70 | 70% | +2.28% | +3.16% | +1.57% | +1.72% | -19.00% | -12.80% | 14% |
| 2018-01-02 → 2021-12-31 | below_sma200 | 367 | 56% | +0.78% | +1.63% | +0.96% | +0.73% | -52.11% | -16.08% | 25% |
| 2018-01-02 → 2021-12-31 | all_no_stop | 399 | 61% | +0.64% | +2.62% | +1.12% | +1.22% | -59.26% | -23.28% | 0% |
| 2018-01-02 → 2021-12-31 | below_sma200_no_stop | 338 | 58% | +0.27% | +2.02% | +0.93% | +1.05% | -59.26% | -23.41% | 0% |
| 2018-01-02 → 2021-12-31 | at_weekly_sma200 | 60 | 62% | -0.55% | +1.55% | +0.35% | +0.50% | -21.38% | -17.25% | 20% |
| 2018-01-02 → 2021-12-31 | at_weekly_sma200_no_stop | 60 | 62% | -1.09% | +1.55% | +0.58% | +0.29% | -36.69% | -21.10% | 0% |
| 2022-01-03 → 2026-11-25 | all | 711 | 60% | +1.28% | +2.11% | +0.46% | +0.77% | -26.68% | -12.25% | 18% |
| 2022-01-03 → 2026-11-25 | above_sma200 | 62 | 53% | +0.38% | +0.55% | -0.81% | -0.18% | -13.90% | -8.83% | 11% |
| 2022-01-03 → 2026-11-25 | below_sma200 | 656 | 61% | +1.38% | +2.26% | +0.57% | +0.88% | -26.68% | -12.36% | 19% |
| 2022-01-03 → 2026-11-25 | all_no_stop | 673 | 63% | +1.65% | +2.37% | +0.69% | +1.01% | -29.38% | -12.56% | 0% |
| 2022-01-03 → 2026-11-25 | below_sma200_no_stop | 620 | 64% | +1.76% | +2.52% | +0.81% | +1.12% | -29.38% | -13.10% | 0% |
| 2022-01-03 → 2026-11-25 | at_weekly_sma200 | 117 | 57% | +1.02% | +1.83% | +0.37% | +0.72% | -12.47% | -10.83% | 17% |
| 2022-01-03 → 2026-11-25 | at_weekly_sma200_no_stop | 117 | 58% | +1.14% | +1.83% | +0.50% | +0.79% | -21.46% | -11.31% | 0% |

Passes: all yes, above_sma200 no, below_sma200 yes, all_no_stop yes, below_sma200_no_stop yes, at_weekly_sma200 no, at_weekly_sma200_no_stop no

NVDA in November 2026 under this rule (with the 8% stop): signal 2026-11-16 at 156.14 (-3.5 ATR) → stop on 2026-11-20, -19.76%

NVDA's 200-week average on 2026-11-25: 123.33.

## Thermometer "Panic · buy": buy the leader

Signal: the thermometer (market_pulse.py, rebuilt without Fear & Greed) closes under 20; one signal per episode (63 sessions apart). Bought at the next close; 0.1% per side. Leader: highest 21/200-day average ratio in the universe on the signal day; top5: the five highest. Today's universe, so stock baskets are flattered by survivorship.

Rebuilt thermometer on 2026-11-25: 28.6.

### First panic close

| Sessions | Signals | Leader mean / median | Top 5 mean / median | Universe mean | S&P 500 mean / median | Leader beats S&P | Leader worst |
|---:|---:|---|---|---:|---|---:|---:|
| 21 | 6 | +4.4% / +5.8% | +5.8% / +3.2% | +5.2% | +4.2% / +5.0% | 3/6 | -15.1% |
| 63 | 6 | +33.7% / +33.1% | +30.8% / +26.5% | +17.5% | +11.7% / +11.5% | 5/6 | -0.6% |
| 126 | 6 | +72.8% / +85.2% | +63.4% / +38.4% | +24.7% | +13.5% / +15.1% | 5/6 | -7.1% |
| 252 | 6 | +138.8% / +73.5% | +72.8% / +49.9% | +42.7% | +21.7% / +25.4% | 4/6 | -6.4% |

Signals: 2015-08-24 (heat 6.2, leader NFLX: 63 sessions +22.9%, S&P +11.5%); 2016-01-15 (heat 18.7, leader NVDA: 63 sessions +33.1%, S&P +11.4%); 2018-12-19 (heat 19.5, leader TTD: 63 sessions +67.9%, S&P +13.2%); 2020-03-09 (heat 8.3, leader TSLA: 63 sessions +45.5%, S&P +11.1%); 2022-03-07 (heat 14.6, leader DVN: 63 sessions +33.1%, S&P -0.4%); 2025-04-04 (heat 5.3, leader BABA: 63 sessions -0.6%, S&P +23.5%); 2026-11-20 (heat 15.6, leader MRNA: 63 sessions —, S&P —)

### First close back above 20

| Sessions | Signals | Leader mean / median | Top 5 mean / median | Universe mean | S&P 500 mean / median | Leader beats S&P | Leader worst |
|---:|---:|---|---|---:|---|---:|---:|
| 21 | 6 | +23.0% / +19.4% | +14.7% / +11.5% | +6.8% | +4.4% / +3.9% | 4/6 | -16.6% |
| 63 | 6 | +44.3% / +29.4% | +49.1% / +29.6% | +16.6% | +10.3% / +13.3% | 5/6 | +5.4% |
| 126 | 6 | +63.5% / +75.8% | +83.0% / +50.3% | +25.5% | +13.6% / +18.6% | 5/6 | -16.6% |
| 252 | 6 | +126.0% / +87.8% | +96.9% / +60.6% | +44.8% | +22.4% / +26.6% | 3/6 | -17.4% |

Signals: 2015-08-27 (heat 30.1, leader NFLX: 63 sessions +6.4%, S&P +4.9%); 2016-01-22 (heat 25.0, leader NVDA: 63 sessions +28.5%, S&P +11.0%); 2019-01-02 (heat 21.6, leader TTD: 63 sessions +80.4%, S&P +17.4%); 2020-04-14 (heat 26.4, leader MRNA: 63 sessions +114.9%, S&P +15.7%); 2022-03-09 (heat 21.0, leader DVN: 63 sessions +30.4%, S&P -5.9%); 2025-04-09 (heat 20.5, leader BABA: 63 sessions +5.4%, S&P +18.8%); 2026-11-23 (heat 29.1, leader MRNA: 63 sessions —, S&P —)

### S&P 500 leaders, point in time

Members on the signal day from the fja05680/sp500 history (including companies that later left the index); leader = highest 21/200-day average ratio among members with 200 sessions of prices. Members without Yahoo prices (mostly delisted later) are counted and left out, so a little survivorship remains.

#### First panic close

| Sessions | Signals | Leader mean / median | Top 5 mean | Top 10 mean | All members mean | S&P 500 mean | Leader beats S&P | Leader worst |
|---:|---:|---|---:|---:|---:|---:|---:|---:|
| 21 | 6 | +9.2% / +2.0% | +7.2% | +5.5% | +3.7% | +4.2% | 3/6 | -0.5% |
| 63 | 6 | +35.8% / +33.1% | +21.1% | +16.7% | +12.1% | +11.7% | 5/6 | +3.7% |
| 126 | 6 | +55.9% / +50.4% | +20.8% | +16.1% | +12.8% | +13.5% | 4/6 | -7.1% |
| 252 | 6 | +75.0% / +44.9% | +31.6% | +27.3% | +26.1% | +21.7% | 4/6 | -6.4% |

Signals: 2015-08-24 (368/500 members priced; leader NFLX, 63 sessions +22.9%; top 5 NFLX, AMZN, UAA, EXPE, REGN); 2016-01-15 (373/504 members priced; leader NVDA, 63 sessions +33.1%; top 5 NVDA, HRL, FSLR, AMZN, TSN); 2018-12-19 (417/505 members priced; leader MKC, 63 sessions +3.7%; top 5 MKC, CHD, LLY, AAP, TRIP); 2020-03-09 (435/505 members priced; leader NVDA, 63 sessions +38.4%; top 5 NVDA, AMD, REGN, DVA, LRCX); 2022-03-07 (458/505 members priced; leader DVN, 63 sessions +33.1%; top 5 DVN, APA, OXY, HAL, COP); 2025-04-04 (485/503 members priced; leader PLTR, 63 sessions +83.5%; top 5 PLTR, TPR, GILD, EQT, VRSN); 2026-11-20 (497/503 members priced; leader MRNA, 63 sessions —; top 5 MRNA, CRL, VEEV, RVTY, CRWD)

#### First close back above 20

| Sessions | Signals | Leader mean / median | Top 5 mean | Top 10 mean | All members mean | S&P 500 mean | Leader beats S&P | Leader worst |
|---:|---:|---|---:|---:|---:|---:|---:|---:|
| 21 | 6 | +7.7% / +7.9% | +5.2% | +4.7% | +4.8% | +4.4% | 3/6 | -16.6% |
| 63 | 6 | +28.3% / +25.9% | +15.3% | +12.7% | +11.6% | +10.3% | 5/6 | +6.4% |
| 126 | 6 | +38.6% / +19.0% | +18.8% | +13.2% | +14.5% | +13.6% | 3/6 | -16.6% |
| 252 | 6 | +52.0% / +3.5% | +27.6% | +17.5% | +28.4% | +22.4% | 2/6 | -17.4% |

Signals: 2015-08-27 (368/500 members priced; leader NFLX, 63 sessions +6.4%; top 5 NFLX, AMZN, UAA, EXPE, MLM); 2016-01-22 (374/505 members priced; leader NVDA, 63 sessions +28.5%; top 5 NVDA, HRL, FSLR, EXR, AMZN); 2019-01-02 (418/505 members priced; leader CHD, 63 sessions +13.2%; top 5 CHD, MKC, AZO, LLY, MRK); 2020-04-14 (437/505 members priced; leader REGN, 63 sessions +23.4%; top 5 REGN, KR, NVDA, NEM, AMD); 2022-03-09 (458/505 members priced; leader DVN, 63 sessions +30.4%; top 5 DVN, OXY, APA, HAL, CF); 2025-04-09 (485/503 members priced; leader PLTR, 63 sessions +68.0%; top 5 PLTR, TPR, GILD, EQT, VRSN); 2026-11-23 (497/503 members priced; leader MRNA, 63 sessions —; top 5 MRNA, CRL, VEEV, RVTY, CRWD)

#### Ten largest S&P 500 members by market cap, cap-weighted (first panic close)

Market cap = close x Yahoo shares outstanding on the day; looked up for the 40 most traded members. This is the rule of the index-leaders paper account (index_leaders.py).

| Sessions | Signals | Top 10 by weight mean / median | S&P 500 mean / median | Beats S&P | Worst |
|---:|---:|---|---|---:|---:|
| 21 | 5 | +5.4% / +4.9% | +4.4% / +6.7% | 3/5 | -1.9% |
| 63 | 5 | +13.7% / +15.5% | +11.7% / +11.4% | 3/5 | -5.7% |
| 126 | 5 | +22.2% / +20.7% | +15.4% / +15.4% | 3/5 | -7.2% |
| 252 | 5 | +30.3% / +39.2% | +22.8% / +30.3% | 4/5 | -15.9% |

Signals: 2016-01-15 (AAPL 15%, GOOGL 14%, GOOG 13%, MSFT 11%, XOM 9%…; 63 sessions +10.4% vs S&P +11.4%; no shares for BKNG); 2018-12-19 (MSFT 15%, AAPL 14%, AMZN 13%, GOOGL 13%, GOOG 13%…; 63 sessions +15.5% vs S&P +13.2%); 2020-03-09 (AAPL 17%, MSFT 17%, AMZN 13%, GOOGL 12%, GOOG 12%…; 63 sessions +16.1% vs S&P +11.1%); 2022-03-07 (AAPL 21%, MSFT 17%, GOOG 13%, GOOGL 13%, AMZN 11%…; 63 sessions -5.7% vs S&P -0.4%); 2025-04-04 (AAPL 17%, MSFT 16%, NVDA 14%, AMZN 11%, GOOG 11%…; 63 sessions +32.5% vs S&P +23.5%); 2026-11-20 (AAPL 19%, MSFT 14%, GOOGL 12%, GOOG 12%, NVDA 12%…; 63 sessions — vs S&P —; no shares for SNDK)

#### Exit rules for the same buy (ten largest by weight)

hold_63 sells after 63 sessions; euphoria at the close after the first thermometer close at or above 80 (however long); euphoria_after_63 likewise, after at least 63 sessions; euphoria_or_252 the euphoria exit within at most 252 sessions (the paper account's rule). Open = no euphoria yet, marked at the last close.

euphoria_stop_basket_10/15 and euphoria_stop_spx_10 add a stop to euphoria_or_252: sold at the close after the basket (or the S&P 500) closes 10%/15% under its value at the buy.

| Exit | Signals | Still open | Stopped | Median sessions held | Mean / median return | S&P 500 same span | Beats S&P | Worst |
|---|---:|---:|---:|---:|---|---:|---:|---:|
| hold_63 | 6 | 1 | 0 | 63 | +11.1% / +12.9% | +9.8% | 3/6 | -5.7% |
| euphoria | 6 | 1 | 0 | 60 | +9.8% / +12.5% | +9.3% | 3/6 | -11.1% |
| euphoria_after_63 | 6 | 1 | 0 | 66 | +11.8% / +14.1% | +10.5% | 3/6 | -11.1% |
| euphoria_or_252 | 6 | 1 | 0 | 60 | +9.8% / +12.5% | +9.3% | 3/6 | -11.1% |
| euphoria_stop_basket_10 | 6 | 1 | 2 | 50 | +7.1% / +3.3% | +5.9% | 3/6 | -7.7% |
| euphoria_stop_basket_15 | 6 | 1 | 2 | 54 | +4.8% / +3.3% | +3.3% | 3/6 | -15.6% |
| euphoria_stop_spx_10 | 6 | 1 | 2 | 54 | +5.8% / +3.3% | +4.8% | 3/6 | -15.6% |

Per signal (euphoria): 2016-01-15 → 2016-04-04 (52 sessions): +8.9% vs S&P +9.8%; 2018-12-19 → 2019-03-22 (62 sessions): +16.0% vs S&P +13.5%; 2020-03-09 → 2020-06-09 (63 sessions): +16.1% vs S&P +11.3%; 2022-03-07 → 2023-02-03 (229 sessions): -11.1% vs S&P -0.8%; 2025-04-04 → 2025-06-30 (57 sessions): +31.3% vs S&P +22.6%; 2026-11-20 → 2026-11-25 (2 sessions, open): -2.4% vs S&P -0.8%

Per signal (euphoria_stop_basket_15): 2016-01-15 → 2016-04-04 (52 sessions): +8.9% vs S&P +9.8%; 2018-12-19 → 2019-03-22 (62 sessions): +16.0% vs S&P +13.5%; 2020-03-09 → 2020-03-24 (10 sessions, stopped): -9.6% vs S&P -15.1%; 2022-03-07 → 2022-06-14 (68 sessions, stopped): -15.6% vs S&P -10.4%; 2025-04-04 → 2025-06-30 (57 sessions): +31.3% vs S&P +22.6%; 2026-11-20 → 2026-11-25 (2 sessions, open): -2.4% vs S&P -0.8%

Per signal (euphoria_stop_spx_10): 2016-01-15 → 2016-04-04 (52 sessions): +8.9% vs S&P +9.8%; 2018-12-19 → 2019-03-22 (62 sessions): +16.0% vs S&P +13.5%; 2020-03-09 → 2020-03-13 (3 sessions, stopped): -3.6% vs S&P -5.9%; 2022-03-07 → 2022-06-14 (68 sessions, stopped): -15.6% vs S&P -10.4%; 2025-04-04 → 2025-06-30 (57 sessions): +31.3% vs S&P +22.6%; 2026-11-20 → 2026-11-25 (2 sessions, open): -2.4% vs S&P -0.8%

#### Buy only at a later close still in panic (the paper account's rule since 23 Nov 2026)

Same ten largest by weight, bought at the first close after the signal with the thermometer still under 20 (the close value stands in for the intraday check 20 minutes earlier); episodes without such a close within 63 sessions buy nothing. Skipped: 2026-11-20.

| Exit | Signals | Mean / median return | S&P 500 same span | Beats S&P | Worst |
|---|---:|---|---:|---:|---:|
| hold_63 | 5 | +13.7% / +15.5% | +12.0% | 3/5 | -5.7% |
| euphoria_or_252 | 5 | +12.2% / +16.0% | +11.3% | 3/5 | -11.1% |

Per signal (euphoria_or_252): bought 2016-01-15 → 2016-04-04: +8.9% vs S&P +9.8%; bought 2018-12-19 → 2019-03-22: +16.0% vs S&P +13.5%; bought 2020-03-09 → 2020-06-09: +16.1% vs S&P +11.3%; bought 2022-03-07 → 2023-02-03: -11.1% vs S&P -0.8%; bought 2025-04-04 → 2025-06-30: +31.3% vs S&P +22.6%
