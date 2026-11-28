# Backtest of the technical rules · 2021-11-27 → 2026-11-27

Technical rules on current members. Historical membership and full label history are unavailable. Survivorship bias may affect strategies differently. Decision on close t, fill at close t+1, 0.10% per fill. Historical technical simulation uses local quote units and excludes FX. Compare variants within this simulation.

## 1 · After a close far above the 36-day average

| Distance to 36-day avg | days | stocks | 21-day mean | 63-day mean | 63-day vs S&P | P(−10% within 21 d) | P(63 d < 0) |
|---|---|---|---|---|---|---|---|
| -100..0% | 72415 | 130 | 1.36% | 4.31% | 0.96% | 25.6% | 46.88% |
| 0..10% | 61800 | 130 | 0.91% | 2.82% | 0.09% | 20.13% | 47.77% |
| 10..20% | 11600 | 128 | 1.46% | 5.2% | 2.52% | 29.71% | 47.85% |
| 20..30% | 2376 | 89 | 3.37% | 9.38% | 6.91% | 40.03% | 47.18% |
| 30..+% | 1649 | 57 | 6.7% | 17.69% | 15.38% | 51.0% | 46.57% |

## 2 · Breakouts above the prior 60-session high (in an uptrend) · failure rate 33.15%

| Case | days | 5-day mean | 21-day mean | 63-day mean | 63-day vs S&P |
|---|---|---|---|---|---|
| all_uptrend_days | 59928 | 0.35% | 1.51% | 4.77% | 1.68% |
| breakout_day | 3692 | 0.22% | 1.49% | 4.39% | 1.44% |
| breakout_failed | 1224 | -4.16% | -5.26% | -1.39% | -3.34% |
| breakout_held | 2468 | 2.39% | 4.84% | 7.25% | 3.81% |
| confirmed_second_close | 2674 | 0.18% | 1.63% | 4.7% | 1.7% |
| just_under_resistance | 17160 | 0.23% | 0.89% | 2.92% | -0.17% |

"breakout_failed" and "breakout_held" use the next 10 sessions to sort the cases, so they are not tradable signals; they show how much a failure costs.

## 3 · Portfolio simulation (10,000, max 8 positions)

| Variant | CAGR | max drawdown | Sharpe | trades | win rate | avg trade | avg days |
|---|---|---|---|---|---|---|---|
| base_v1_6 | 21.81% | -33.03% | 0.95 | 291 | 29.21% | 4.75% | 27.9 |
| base_v1_5 | 34.11% | -34.02% | 1.12 | 275 | 28.73% | 5.5% | 29.4 |
| no_buy_above_30pct_36d | 32.25% | -30.92% | 1.16 | 277 | 28.52% | 4.64% | 29.3 |
| sell_above_30pct_36d | 5.53% | -28.88% | 0.38 | 353 | 32.58% | 1.35% | 23.2 |
| wait_under_resistance | 25.0% | -28.81% | 1.01 | 283 | 30.39% | 4.27% | 27.4 |
| two_closes_above_resistance | 25.74% | -31.61% | 0.97 | 286 | 29.02% | 4.68% | 28.3 |
| sell_failed_breakout | 21.81% | -33.03% | 0.95 | 291 | 29.21% | 4.75% | 27.9 |
| two_closes_and_sell_failed | 37.53% | -31.32% | 1.22 | 276 | 30.07% | 5.61% | 29.0 |
| wait_res_and_sell_failed | 29.55% | -31.17% | 1.05 | 287 | 29.27% | 5.32% | 27.4 |
| kell_crossback_exit | 32.82% | -28.49% | 1.12 | 655 | 34.35% | 2.09% | 12.0 |
| kell_base_n_break_entry | 6.84% | -17.03% | 0.53 | 212 | 26.42% | 1.11% | 36.4 |
| kell_wedge_pop_entry | 8.26% | -18.56% | 0.57 | 229 | 29.69% | 1.59% | 32.4 |
| kell_full | 11.33% | -25.45% | 0.64 | 525 | 35.05% | 0.77% | 13.2 |
| buffer_200d_1pct | 21.81% | -33.03% | 0.95 | 291 | 29.21% | 4.75% | 27.9 |
| buffer_200d_2pct | 21.81% | -33.03% | 0.95 | 291 | 29.21% | 4.75% | 27.9 |
| buffer_200d_3pct | 21.81% | -33.03% | 0.95 | 291 | 29.21% | 4.75% | 27.9 |
| sell_all_in_correction | 31.73% | -24.99% | 1.1 | 361 | 36.29% | 4.39% | 21.1 |
| sell_all_weak_breadth | 15.84% | -34.81% | 0.69 | 661 | 39.18% | 1.26% | 11.3 |
| sell_all_correction_and_weak_breadth | 19.55% | -25.05% | 0.89 | 331 | 34.44% | 4.42% | 23.7 |
| shorts_in_correction | 32.24% | -35.39% | 1.09 | 405 | 32.59% | 4.07% | 22.6 |
| shorts_always | 13.72% | -35.12% | 0.6 | 572 | 32.34% | 1.45% | 22.7 |
| garch_position_size | 21.12% | -19.37% | 1.25 | 265 | 31.32% | 5.83% | 30.7 |
| ewma_position_size | 23.67% | -21.45% | 1.33 | 266 | 31.2% | 6.89% | 30.9 |
| garch_exposure | 34.4% | -33.43% | 1.2 | 269 | 30.48% | 6.41% | 30.1 |
| ewma_exposure | 39.09% | -36.24% | 1.23 | 302 | 29.14% | 6.23% | 26.8 |
| rebound_sleeve | 35.92% | -29.68% | 1.23 | 560 | 40.89% | 2.47% | 17.8 |
| rebound_sleeve_below_200d | 23.83% | -31.27% | 1.03 | 512 | 42.38% | 3.37% | 19.2 |
| rebound_sleeve_no_stop | 24.41% | -32.04% | 1.01 | 525 | 41.33% | 3.42% | 18.9 |

S&P 500 buy and hold: CAGR 9.42%, max drawdown -25.43%.

## 4 · Separate periods (same variants)

Members enter a period once they have 200 days of prices, so early periods hold fewer stocks.

### 2014-01-02 → 2017-12-29 · 101 stocks · S&P CAGR 9.94%, max drawdown -14.16%

Breakout failure rate 22.58% · 63-day mean: uptrend days 4.5%, just under resistance 4.21%, failed breakouts 0.35% · more than 30% above the 36-day average: n=210, 63-day 13.61%, P(−10% in 21 d) 53.33%

| Variant | CAGR | max drawdown | Sharpe | trades |
|---|---|---|---|---|
| base_v1_6 | 17.4% | -16.64% | 1.11 | 169 |
| base_v1_5 | 17.81% | -14.55% | 1.12 | 162 |
| no_buy_above_30pct_36d | 13.63% | -14.55% | 0.92 | 160 |
| sell_above_30pct_36d | 14.39% | -16.03% | 0.95 | 177 |
| wait_under_resistance | 16.63% | -15.7% | 1.06 | 149 |
| two_closes_above_resistance | 17.12% | -16.72% | 1.09 | 165 |
| sell_failed_breakout | 17.4% | -16.64% | 1.11 | 169 |
| two_closes_and_sell_failed | 19.88% | -17.69% | 1.24 | 162 |
| wait_res_and_sell_failed | 20.13% | -16.17% | 1.26 | 153 |
| kell_crossback_exit | 11.18% | -15.74% | 0.77 | 515 |
| kell_base_n_break_entry | 4.91% | -14.79% | 0.47 | 135 |
| kell_wedge_pop_entry | 11.26% | -15.33% | 0.88 | 187 |
| kell_full | 0.86% | -19.06% | 0.13 | 460 |
| buffer_200d_1pct | 17.4% | -16.64% | 1.11 | 169 |
| buffer_200d_2pct | 17.4% | -16.64% | 1.11 | 169 |
| buffer_200d_3pct | 17.4% | -16.64% | 1.11 | 169 |
| sell_all_in_correction | 15.12% | -13.77% | 1.07 | 212 |
| sell_all_weak_breadth | 12.31% | -14.94% | 0.82 | 175 |
| sell_all_correction_and_weak_breadth | 12.31% | -14.94% | 0.82 | 175 |
| shorts_in_correction | 13.26% | -27.77% | 0.86 | 226 |
| shorts_always | 9.07% | -20.35% | 0.55 | 369 |
| garch_position_size | 17.0% | -13.62% | 1.18 | 166 |
| ewma_position_size | 17.43% | -13.35% | 1.21 | 171 |
| garch_exposure | 15.58% | -16.12% | 0.98 | 165 |
| ewma_exposure | 16.75% | -15.07% | 1.1 | 162 |
| rebound_sleeve | 20.4% | -17.07% | 1.21 | 252 |
| rebound_sleeve_below_200d | 21.08% | -17.28% | 1.21 | 236 |
| rebound_sleeve_no_stop | 19.33% | -16.66% | 1.19 | 241 |

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
| kell_base_n_break_entry | 20.57% | -14.12% | 1.25 | 148 |
| kell_wedge_pop_entry | 13.12% | -17.23% | 0.75 | 184 |
| kell_full | 14.98% | -22.5% | 0.81 | 467 |
| buffer_200d_1pct | 30.68% | -20.18% | 1.21 | 212 |
| buffer_200d_2pct | 30.68% | -20.18% | 1.21 | 212 |
| buffer_200d_3pct | 30.68% | -20.18% | 1.21 | 212 |
| sell_all_in_correction | 25.7% | -23.29% | 1.09 | 296 |
| sell_all_weak_breadth | 24.95% | -18.66% | 1.04 | 231 |
| sell_all_correction_and_weak_breadth | 24.95% | -18.66% | 1.04 | 231 |
| shorts_in_correction | 26.56% | -26.46% | 1.03 | 294 |
| shorts_always | 22.6% | -30.3% | 0.87 | 454 |
| garch_position_size | 21.09% | -14.67% | 1.24 | 192 |
| ewma_position_size | 17.39% | -17.79% | 1.01 | 211 |
| garch_exposure | 32.5% | -16.02% | 1.42 | 199 |
| ewma_exposure | 24.79% | -17.01% | 1.14 | 210 |
| rebound_sleeve | 35.02% | -26.29% | 1.34 | 353 |
| rebound_sleeve_below_200d | 42.16% | -31.12% | 1.52 | 329 |
| rebound_sleeve_no_stop | 32.24% | -27.8% | 1.25 | 332 |

### 2022-01-03 → 2026-11-27 · 130 stocks · S&P CAGR 8.95%, max drawdown -25.43%

Breakout failure rate 33.23% · 63-day mean: uptrend days 5.02%, just under resistance 3.04%, failed breakouts -1.26% · more than 30% above the 36-day average: n=1647, 63-day 17.75%, P(−10% in 21 d) 50.94%

| Variant | CAGR | max drawdown | Sharpe | trades |
|---|---|---|---|---|
| base_v1_6 | 33.21% | -33.8% | 1.19 | 277 |
| base_v1_5 | 31.07% | -31.14% | 1.12 | 259 |
| no_buy_above_30pct_36d | 27.74% | -26.74% | 1.07 | 263 |
| sell_above_30pct_36d | 11.02% | -24.83% | 0.67 | 344 |
| wait_under_resistance | 31.65% | -27.17% | 1.14 | 272 |
| two_closes_above_resistance | 45.79% | -27.83% | 1.45 | 266 |
| sell_failed_breakout | 33.21% | -33.8% | 1.19 | 277 |
| two_closes_and_sell_failed | 32.21% | -32.66% | 1.13 | 278 |
| wait_res_and_sell_failed | 40.08% | -32.05% | 1.27 | 287 |
| kell_crossback_exit | 22.02% | -31.23% | 0.89 | 643 |
| kell_base_n_break_entry | 4.26% | -17.21% | 0.38 | 214 |
| kell_wedge_pop_entry | 6.87% | -19.15% | 0.51 | 215 |
| kell_full | 8.5% | -28.66% | 0.52 | 511 |
| buffer_200d_1pct | 33.21% | -33.8% | 1.19 | 277 |
| buffer_200d_2pct | 33.21% | -33.8% | 1.19 | 277 |
| buffer_200d_3pct | 33.21% | -33.8% | 1.19 | 277 |
| sell_all_in_correction | 40.58% | -27.8% | 1.28 | 343 |
| sell_all_weak_breadth | 17.54% | -24.41% | 0.76 | 653 |
| sell_all_correction_and_weak_breadth | 31.44% | -34.17% | 1.1 | 324 |
| shorts_in_correction | 38.42% | -33.34% | 1.21 | 402 |
| shorts_always | 28.22% | -33.36% | 0.93 | 545 |
| garch_position_size | 20.71% | -19.1% | 1.24 | 253 |
| ewma_position_size | 21.51% | -20.87% | 1.26 | 257 |
| garch_exposure | 32.0% | -33.47% | 1.18 | 266 |
| ewma_exposure | 35.13% | -31.73% | 1.26 | 259 |
| rebound_sleeve | 16.1% | -27.96% | 0.74 | 534 |
| rebound_sleeve_below_200d | 27.18% | -32.11% | 1.08 | 528 |
| rebound_sleeve_no_stop | 29.58% | -24.32% | 1.09 | 524 |

### Robustness: windows in which a variant beat base_v1_6 (the current rules)

| Variant | CAGR | max drawdown (less deep) | Sharpe |
|---|---|---|---|
| no_buy_above_30pct_36d | 1/3 | 3/3 | 1/3 |
| sell_above_30pct_36d | 1/3 | 3/3 | 1/3 |
| wait_under_resistance | 1/3 | 2/3 | 1/3 |
| two_closes_above_resistance | 2/3 | 1/3 | 2/3 |
| sell_failed_breakout | 0/3 | 0/3 | 0/3 |
| two_closes_and_sell_failed | 1/3 | 2/3 | 1/3 |
| wait_res_and_sell_failed | 3/3 | 2/3 | 3/3 |
| kell_crossback_exit | 1/3 | 2/3 | 1/3 |
| kell_base_n_break_entry | 0/3 | 3/3 | 1/3 |
| kell_wedge_pop_entry | 0/3 | 3/3 | 0/3 |
| kell_full | 0/3 | 1/3 | 0/3 |
| buffer_200d_1pct | 1/3 | 1/3 | 1/3 |
| buffer_200d_2pct | 1/3 | 1/3 | 1/3 |
| buffer_200d_3pct | 1/3 | 1/3 | 1/3 |
| sell_all_in_correction | 1/3 | 2/3 | 2/3 |
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

Symbols: 130 · generated 2026-11-28T11:13+00:00 · price data 25c913b248b87a79

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

### 2021-11-27 → 2026-11-27

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

Ending equity difference: +3984.02; total-return difference +39.84 percentage points. Differing positions: 233.

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

### 2022-01-03 → 2026-11-27

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
| base_v1_5 | 6 / 0 / 14 | +0.41 | -1.31 [-3.91, +1.65] | -0.03 [-2.16, +4.15] | -0.08 [-0.16, +0.14] |
| no_buy_above_30pct_36d | 0 / 0 / 20 | -3.77 | -5.94 [-10.87, -0.44] | -0.03 [-2.16, +4.15] | -0.29 [-0.55, -0.03] |
| sell_above_30pct_36d | 1 / 0 / 19 | -3.01 | -2.78 [-8.55, +1.97] | +0.22 [-4.16, +2.34] | -0.12 [-0.44, +0.15] |
| wait_under_resistance | 5 / 0 / 15 | -0.77 | -0.93 [-4.73, +2.50] | +1.48 [-0.45, +4.09] | -0.04 [-0.26, +0.11] |
| two_closes_above_resistance | 7 / 0 / 13 | -0.28 | -0.48 [-4.03, +2.21] | -1.24 [-3.65, +2.95] | -0.03 [-0.19, +0.11] |
| sell_failed_breakout | 0 / 20 / 0 | +0.00 | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] |
| two_closes_and_sell_failed | 5 / 0 / 15 | +2.48 | -1.52 [-6.33, +2.48] | -1.80 [-7.13, +0.99] | -0.07 [-0.32, +0.13] |
| wait_res_and_sell_failed | 13 / 0 / 7 | +2.72 | +0.67 [-3.75, +3.35] | +0.57 [-2.63, +4.71] | +0.05 [-0.21, +0.18] |
| kell_crossback_exit | 0 / 0 / 20 | -6.22 | -9.40 [-13.90, -6.16] | -0.57 [-3.76, +3.41] | -0.48 [-0.72, -0.34] |
| kell_base_n_break_entry | 0 / 0 / 20 | -12.49 | -15.56 [-19.24, -11.88] | -0.40 [-8.13, +4.01] | -0.81 [-1.06, -0.64] |
| kell_wedge_pop_entry | 0 / 0 / 20 | -6.14 | -10.08 [-15.63, -0.90] | -1.79 [-5.46, +1.97] | -0.36 [-0.70, +0.13] |
| kell_full | 0 / 0 / 20 | -16.54 | -15.64 [-19.20, -11.57] | -3.04 [-4.57, -0.33] | -0.82 [-1.03, -0.65] |
| buffer_200d_1pct | 0 / 20 / 0 | +0.00 | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] |
| buffer_200d_2pct | 0 / 20 / 0 | +0.00 | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] |
| buffer_200d_3pct | 0 / 20 / 0 | +0.00 | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] |
| sell_all_in_correction | 0 / 0 / 20 | -2.28 | -4.61 [-9.88, -0.96] | +0.50 [-2.69, +4.58] | -0.18 [-0.49, +0.05] |
| sell_all_weak_breadth | 2 / 0 / 18 | -5.09 | -5.11 [-7.50, +1.59] | +0.55 [-1.60, +2.76] | -0.28 [-0.40, +0.05] |
| sell_all_correction_and_weak_breadth | 2 / 0 / 18 | -5.09 | -5.11 [-7.50, +1.59] | +0.55 [-1.60, +2.76] | -0.28 [-0.40, +0.05] |
| shorts_in_correction | 0 / 0 / 20 | -4.14 | -3.33 [-5.33, -1.70] | -6.85 [-11.13, -4.48] | -0.20 [-0.30, -0.12] |
| shorts_always | 0 / 0 / 20 | -8.33 | -9.33 [-16.43, -5.53] | -5.38 [-8.53, -1.78] | -0.61 [-0.94, -0.42] |
| garch_position_size | 7 / 0 / 13 | -0.40 | -0.70 [-3.06, +3.38] | +1.60 [-1.30, +6.03] | +0.08 [-0.06, +0.29] |
| ewma_position_size | 3 / 0 / 17 | +0.03 | -2.17 [-5.37, +1.57] | +2.49 [-3.91, +3.97] | +0.01 [-0.20, +0.21] |
| garch_exposure | 2 / 0 / 18 | -1.82 | -1.84 [-5.16, +1.08] | -1.35 [-3.69, +1.83] | -0.13 [-0.31, -0.01] |
| ewma_exposure | 2 / 0 / 18 | -0.65 | -1.70 [-2.95, +0.72] | -0.21 [-2.37, +1.69] | -0.07 [-0.12, +0.06] |
| rebound_sleeve | 14 / 0 / 6 | +3.00 | +1.11 [-3.32, +3.44] | -3.15 [-9.51, -0.08] | +0.01 [-0.20, +0.15] |
| rebound_sleeve_below_200d | 11 / 0 / 9 | +3.68 | +0.10 [-2.69, +5.85] | -3.49 [-8.57, +0.12] | -0.03 [-0.15, +0.22] |
| rebound_sleeve_no_stop | 12 / 0 / 8 | +1.93 | +0.56 [-4.62, +3.42] | -2.83 [-9.97, +0.45] | +0.00 [-0.28, +0.14] |

### 2018-01-02 → 2021-12-31

20 paired starts. Counts use unrounded ending equity.

| Variant | W / T / L | Original start ΔCAGR | ΔCAGR | ΔMax DD | ΔSharpe |
|---|---|---:|---|---|---|
| base_v1_5 | 14 / 0 / 6 | +7.39 | +2.54 [-8.31, +14.42] | -0.72 [-4.37, +1.24] | +0.04 [-0.27, +0.35] |
| no_buy_above_30pct_36d | 10 / 0 / 10 | +5.51 | -0.31 [-7.93, +7.38] | +1.20 [-2.33, +4.76] | -0.01 [-0.22, +0.23] |
| sell_above_30pct_36d | 13 / 0 / 7 | +6.23 | +1.97 [-9.94, +11.88] | +2.36 [-1.42, +5.71] | +0.24 [-0.19, +0.53] |
| wait_under_resistance | 10 / 0 / 10 | +5.80 | -0.37 [-8.05, +7.17] | -4.14 [-7.24, +2.79] | -0.03 [-0.21, +0.23] |
| two_closes_above_resistance | 5 / 0 / 15 | +1.78 | -1.61 [-8.25, +7.79] | +1.30 [-3.16, +4.13] | -0.06 [-0.24, +0.25] |
| sell_failed_breakout | 0 / 20 / 0 | +0.00 | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] |
| two_closes_and_sell_failed | 7 / 0 / 13 | -0.63 | -1.77 [-6.99, +10.20] | +2.22 [-3.38, +5.02] | -0.06 [-0.19, +0.28] |
| wait_res_and_sell_failed | 7 / 0 / 13 | +3.05 | -3.38 [-16.77, +11.09] | -7.26 [-15.74, +0.56] | -0.09 [-0.52, +0.33] |
| kell_crossback_exit | 11 / 0 / 9 | +4.35 | +0.36 [-5.53, +6.69] | -0.44 [-6.70, +3.19] | +0.03 [-0.18, +0.18] |
| kell_base_n_break_entry | 0 / 0 / 20 | -5.38 | -12.44 [-19.80, -3.76] | +7.06 [+3.24, +8.61] | -0.05 [-0.42, +0.20] |
| kell_wedge_pop_entry | 0 / 0 / 20 | -12.83 | -10.85 [-16.84, -3.85] | +6.53 [+3.29, +8.34] | -0.11 [-0.39, +0.05] |
| kell_full | 0 / 0 / 20 | -10.97 | -17.72 [-22.97, -9.67] | -1.02 [-4.88, +2.68] | -0.47 [-0.71, -0.24] |
| buffer_200d_1pct | 8 / 0 / 12 | +4.73 | -1.66 [-8.43, +10.29] | +0.54 [-3.78, +5.07] | -0.04 [-0.25, +0.31] |
| buffer_200d_2pct | 9 / 0 / 11 | +4.73 | -0.83 [-8.43, +10.29] | +0.54 [-3.78, +5.07] | -0.01 [-0.25, +0.31] |
| buffer_200d_3pct | 9 / 0 / 11 | +4.73 | -0.83 [-8.43, +10.29] | +0.54 [-3.78, +5.07] | -0.01 [-0.25, +0.31] |
| sell_all_in_correction | 8 / 0 / 12 | -0.25 | -0.64 [-7.21, +11.45] | +3.21 [-2.15, +6.95] | +0.01 [-0.22, +0.37] |
| sell_all_weak_breadth | 8 / 0 / 12 | -1.00 | -0.53 [-7.64, +7.34] | +3.56 [-0.68, +6.92] | -0.00 [-0.22, +0.23] |
| sell_all_correction_and_weak_breadth | 8 / 0 / 12 | -1.00 | -0.53 [-7.64, +7.34] | +3.56 [-0.68, +6.92] | -0.00 [-0.22, +0.23] |
| shorts_in_correction | 5 / 0 / 15 | +0.61 | -1.82 [-13.75, +3.91] | -3.25 [-7.09, +0.20] | -0.10 [-0.47, +0.07] |
| shorts_always | 0 / 0 / 20 | -3.35 | -11.11 [-19.77, -1.84] | -10.77 [-16.26, -7.45] | -0.42 [-0.68, -0.14] |
| garch_position_size | 0 / 0 / 20 | -4.86 | -13.34 [-17.22, -4.64] | +6.32 [+3.26, +8.99] | -0.12 [-0.34, +0.18] |
| ewma_position_size | 0 / 0 / 20 | -8.56 | -14.22 [-16.84, -4.57] | +4.63 [+1.74, +7.64] | -0.19 [-0.31, +0.06] |
| garch_exposure | 14 / 0 / 6 | +6.55 | +0.84 [-4.30, +11.26] | +5.34 [+1.38, +8.94] | +0.18 [-0.00, +0.44] |
| ewma_exposure | 0 / 0 / 20 | -1.16 | -10.92 [-19.31, -1.16] | +4.84 [+1.79, +7.61] | -0.24 [-0.54, +0.09] |
| rebound_sleeve | 16 / 0 / 4 | +9.07 | +6.55 [-2.21, +16.39] | -4.24 [-9.61, +0.20] | +0.15 [-0.11, +0.48] |
| rebound_sleeve_below_200d | 16 / 0 / 4 | +16.21 | +6.53 [-2.61, +16.21] | -7.24 [-10.03, -1.92] | +0.14 [-0.08, +0.47] |
| rebound_sleeve_no_stop | 18 / 0 / 2 | +6.29 | +6.83 [-4.18, +20.33] | -3.60 [-9.76, +0.61] | +0.20 [-0.17, +0.55] |

### 2022-01-03 → 2026-11-27

20 paired starts. Counts use unrounded ending equity.

| Variant | W / T / L | Original start ΔCAGR | ΔCAGR | ΔMax DD | ΔSharpe |
|---|---|---:|---|---|---|
| base_v1_5 | 13 / 0 / 7 | -2.14 | +2.79 [-13.34, +19.44] | +1.29 [-2.10, +6.22] | +0.06 [-0.24, +0.42] |
| no_buy_above_30pct_36d | 6 / 0 / 14 | -5.47 | -1.79 [-21.26, +2.28] | +0.75 [-0.83, +7.40] | -0.06 [-0.40, -0.01] |
| sell_above_30pct_36d | 0 / 0 / 20 | -22.19 | -23.20 [-30.07, -7.31] | +4.51 [-1.23, +8.97] | -0.61 [-0.65, -0.07] |
| wait_under_resistance | 9 / 0 / 11 | -1.56 | -1.11 [-13.81, +8.88] | +1.42 [-4.92, +7.73] | -0.06 [-0.32, +0.17] |
| two_closes_above_resistance | 14 / 0 / 6 | +12.58 | +3.44 [-7.94, +28.02] | +2.40 [-2.68, +5.97] | +0.04 [-0.12, +0.50] |
| sell_failed_breakout | 0 / 20 / 0 | +0.00 | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] |
| two_closes_and_sell_failed | 15 / 0 / 5 | -1.00 | +5.15 [-2.42, +17.94] | +3.21 [-5.67, +7.82] | +0.05 [-0.06, +0.49] |
| wait_res_and_sell_failed | 9 / 0 / 11 | +6.87 | -2.34 [-14.55, +7.57] | -0.45 [-6.00, +3.00] | -0.13 [-0.33, +0.12] |
| kell_crossback_exit | 1 / 0 / 19 | -11.20 | -4.62 [-16.87, +0.74] | +1.82 [-1.38, +15.52] | -0.14 [-0.43, +0.03] |
| kell_base_n_break_entry | 0 / 0 / 20 | -28.95 | -27.29 [-37.45, -16.87] | +15.38 [+11.94, +20.05] | -0.65 [-0.94, -0.45] |
| kell_wedge_pop_entry | 0 / 0 / 20 | -26.34 | -25.80 [-35.75, -15.68] | +14.36 [+10.10, +19.56] | -0.62 [-0.85, -0.27] |
| kell_full | 0 / 0 / 20 | -24.71 | -23.04 [-31.74, -17.68] | +7.32 [+2.86, +9.84] | -0.64 [-0.75, -0.39] |
| buffer_200d_1pct | 0 / 20 / 0 | +0.00 | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] |
| buffer_200d_2pct | 0 / 20 / 0 | +0.00 | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] |
| buffer_200d_3pct | 1 / 19 / 0 | +0.00 | +0.00 [+0.00, +1.56] | +0.00 [-0.81, +0.00] | +0.00 [+0.00, +0.00] |
| sell_all_in_correction | 12 / 0 / 8 | +7.37 | +7.28 [-5.90, +19.69] | +5.27 [+0.27, +10.95] | +0.07 [-0.16, +0.37] |
| sell_all_weak_breadth | 0 / 0 / 20 | -15.67 | -11.56 [-24.03, -4.34] | +3.01 [-5.30, +9.39] | -0.29 [-0.57, -0.12] |
| sell_all_correction_and_weak_breadth | 12 / 0 / 8 | -1.77 | +3.93 [-9.75, +13.70] | +3.38 [-4.60, +7.37] | +0.06 [-0.27, +0.34] |
| shorts_in_correction | 11 / 0 / 9 | +5.21 | +0.42 [-19.68, +10.31] | -1.51 [-5.66, +2.79] | -0.17 [-0.42, +0.11] |
| shorts_always | 2 / 0 / 18 | -4.99 | -9.81 [-26.65, +3.65] | -3.71 [-8.53, +1.87] | -0.37 [-0.68, -0.07] |
| garch_position_size | 0 / 0 / 20 | -12.50 | -9.46 [-18.77, -0.03] | +12.91 [+9.51, +17.06] | +0.19 [-0.02, +0.39] |
| ewma_position_size | 0 / 0 / 20 | -11.70 | -10.44 [-23.06, -2.14] | +9.91 [+5.95, +13.74] | +0.11 [-0.25, +0.36] |
| garch_exposure | 14 / 0 / 6 | -1.21 | +3.18 [-11.26, +14.22] | -1.75 [-4.81, +3.23] | +0.10 [-0.13, +0.25] |
| ewma_exposure | 15 / 0 / 5 | +1.92 | +5.59 [-6.67, +15.40] | +1.88 [-6.60, +6.29] | +0.13 [-0.08, +0.27] |
| rebound_sleeve | 2 / 0 / 18 | -17.11 | -11.72 [-26.78, +8.68] | +3.27 [-2.08, +9.46] | -0.20 [-0.52, +0.20] |
| rebound_sleeve_below_200d | 4 / 0 / 16 | -6.03 | -7.70 [-19.15, +9.09] | +1.40 [-1.71, +9.80] | -0.10 [-0.41, +0.21] |
| rebound_sleeve_no_stop | 1 / 0 / 19 | -3.63 | -9.26 [-20.44, +10.64] | -0.12 [-2.54, +9.48] | -0.26 [-0.54, +0.27] |


## Pairs trading (same-sector, Engle-Granger + Ornstein-Uhlenbeck)

Yearly formation on 504 sessions, entry |z|>2, exit |z|<0.5, stop |z|>4, dollar-neutral 5% legs, 0.1% per fill, 2% borrow. Passes only with a positive return and Sharpe ≥ 0.5 in every period.

| Method | Period | Pairs/year | CAGR | Sharpe | Max DD | Trades | Win rate | Corr. S&P |
|---|---|---|---:|---:|---:|---:|---:|---:|
| pairs_static | 2014-01-01 → 2018-01-01 | 7,6,5 | -2.6 | -0.91 | -8.67 | 61 | 34.4 | -0.0 |
| pairs_static | 2018-01-01 → 2022-01-01 | 10,4,6,10 | -1.28 | -0.31 | -8.04 | 122 | 32.8 | 0.15 |
| pairs_static | 2022-01-01 → now | 10,4,8,6,3 | 0.48 | 0.15 | -5.99 | 126 | 41.3 | 0.1 |
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
| 2022-01-03 → 2026-11-27 | all | 719 | 61% | +1.38% | +2.26% | +0.53% | +0.86% | -26.68% | -12.25% | 18% |
| 2022-01-03 → 2026-11-27 | above_sma200 | 63 | 54% | +0.50% | +0.84% | -0.66% | -0.13% | -13.90% | -8.83% | 11% |
| 2022-01-03 → 2026-11-27 | below_sma200 | 663 | 62% | +1.48% | +2.34% | +0.64% | +0.98% | -26.68% | -12.34% | 18% |
| 2022-01-03 → 2026-11-27 | all_no_stop | 680 | 63% | +1.74% | +2.49% | +0.76% | +1.07% | -29.38% | -12.56% | 0% |
| 2022-01-03 → 2026-11-27 | below_sma200_no_stop | 627 | 64% | +1.87% | +2.62% | +0.88% | +1.19% | -29.38% | -12.26% | 0% |
| 2022-01-03 → 2026-11-27 | at_weekly_sma200 | 117 | 57% | +1.02% | +1.83% | +0.37% | +0.72% | -12.47% | -10.83% | 17% |
| 2022-01-03 → 2026-11-27 | at_weekly_sma200_no_stop | 117 | 58% | +1.14% | +1.83% | +0.50% | +0.79% | -21.46% | -11.31% | 0% |

Passes: all yes, above_sma200 no, below_sma200 yes, all_no_stop yes, below_sma200_no_stop yes, at_weekly_sma200 no, at_weekly_sma200_no_stop no

NVDA in November 2026 under this rule (with the 8% stop): signal 2026-11-16 at 156.14 (-3.5 ATR) → stop on 2026-11-20, -19.76%

NVDA's 200-week average on 2026-11-27: 123.87.

## Thermometer "Panic · buy": buy the leader

Signal: the thermometer (market_pulse.py, rebuilt without Fear & Greed) closes under 20; one signal per episode (63 sessions apart). Bought at the next close; 0.1% per side. Leader: highest 21/200-day average ratio in the universe on the signal day; top5: the five highest. Today's universe, so stock baskets are flattered by survivorship.

Rebuilt thermometer on 2026-11-27: 37.6.

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
| hold_63 | 6 | 1 | 0 | 63 | +11.3% / +12.9% | +10.1% | 3/6 | -5.7% |
| euphoria | 6 | 1 | 0 | 60 | +10.1% / +12.5% | +9.5% | 3/6 | -11.1% |
| euphoria_after_63 | 6 | 1 | 0 | 66 | +12.0% / +14.1% | +10.7% | 3/6 | -11.1% |
| euphoria_or_252 | 6 | 1 | 0 | 60 | +10.1% / +12.5% | +9.5% | 3/6 | -11.1% |
| euphoria_stop_basket_10 | 6 | 1 | 2 | 50 | +7.3% / +4.1% | +6.2% | 3/6 | -7.7% |
| euphoria_stop_basket_15 | 6 | 1 | 2 | 54 | +5.0% / +4.1% | +3.5% | 3/6 | -15.6% |
| euphoria_stop_spx_10 | 6 | 1 | 2 | 54 | +6.0% / +4.1% | +5.1% | 3/6 | -15.6% |

Per signal (euphoria): 2016-01-15 → 2016-04-04 (52 sessions): +8.9% vs S&P +9.8%; 2018-12-19 → 2019-03-22 (62 sessions): +16.0% vs S&P +13.5%; 2020-03-09 → 2020-06-09 (63 sessions): +16.1% vs S&P +11.3%; 2022-03-07 → 2023-02-03 (229 sessions): -11.1% vs S&P -0.8%; 2025-04-04 → 2025-06-30 (57 sessions): +31.3% vs S&P +22.6%; 2026-11-20 → 2026-11-27 (3 sessions, open): -0.8% vs S&P +0.8%

Per signal (euphoria_stop_basket_15): 2016-01-15 → 2016-04-04 (52 sessions): +8.9% vs S&P +9.8%; 2018-12-19 → 2019-03-22 (62 sessions): +16.0% vs S&P +13.5%; 2020-03-09 → 2020-03-24 (10 sessions, stopped): -9.6% vs S&P -15.1%; 2022-03-07 → 2022-06-14 (68 sessions, stopped): -15.6% vs S&P -10.4%; 2025-04-04 → 2025-06-30 (57 sessions): +31.3% vs S&P +22.6%; 2026-11-20 → 2026-11-27 (3 sessions, open): -0.8% vs S&P +0.8%

Per signal (euphoria_stop_spx_10): 2016-01-15 → 2016-04-04 (52 sessions): +8.9% vs S&P +9.8%; 2018-12-19 → 2019-03-22 (62 sessions): +16.0% vs S&P +13.5%; 2020-03-09 → 2020-03-13 (3 sessions, stopped): -3.6% vs S&P -5.9%; 2022-03-07 → 2022-06-14 (68 sessions, stopped): -15.6% vs S&P -10.4%; 2025-04-04 → 2025-06-30 (57 sessions): +31.3% vs S&P +22.6%; 2026-11-20 → 2026-11-27 (3 sessions, open): -0.8% vs S&P +0.8%

#### Buy only at a later close still in panic (the paper account's rule since 23 Nov 2026)

Same ten largest by weight, bought at the first close after the signal with the thermometer still under 20 (the close value stands in for the intraday check 20 minutes earlier); episodes without such a close within 63 sessions buy nothing. Skipped: 2026-11-20.

| Exit | Signals | Mean / median return | S&P 500 same span | Beats S&P | Worst |
|---|---:|---|---:|---:|---:|
| hold_63 | 5 | +13.7% / +15.5% | +12.0% | 3/5 | -5.7% |
| euphoria_or_252 | 5 | +12.2% / +16.0% | +11.3% | 3/5 | -11.1% |

Per signal (euphoria_or_252): bought 2016-01-15 → 2016-04-04: +8.9% vs S&P +9.8%; bought 2018-12-19 → 2019-03-22: +16.0% vs S&P +13.5%; bought 2020-03-09 → 2020-06-09: +16.1% vs S&P +11.3%; bought 2022-03-07 → 2023-02-03: -11.1% vs S&P -0.8%; bought 2025-04-04 → 2025-06-30: +31.3% vs S&P +22.6%
