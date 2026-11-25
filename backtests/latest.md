# Backtest of the technical rules · 2021-11-24 → 2026-11-24

Technical rules on current members. Historical membership and full label history are unavailable. Survivorship bias may affect strategies differently. Decision on close t, fill at close t+1, 0.10% per fill. Historical technical simulation uses local quote units and excludes FX. Compare variants within this simulation.

## 1 · After a close far above the 36-day average

| Distance to 36-day avg | days | stocks | 21-day mean | 63-day mean | 63-day vs S&P | P(−10% within 21 d) | P(63 d < 0) |
|---|---|---|---|---|---|---|---|
| -100..0% | 71856 | 128 | 1.35% | 4.28% | 0.92% | 25.54% | 46.86% |
| 0..10% | 61277 | 128 | 0.89% | 2.74% | 0.0% | 20.04% | 47.83% |
| 10..20% | 11420 | 126 | 1.39% | 4.97% | 2.32% | 29.82% | 48.03% |
| 20..30% | 2323 | 87 | 3.16% | 8.85% | 6.48% | 40.34% | 47.52% |
| 30..+% | 1567 | 54 | 6.0% | 16.1% | 13.81% | 51.88% | 47.03% |

## 2 · Breakouts above the prior 60-session high (in an uptrend) · failure rate 33.11%

| Case | days | 5-day mean | 21-day mean | 63-day mean | 63-day vs S&P |
|---|---|---|---|---|---|
| all_uptrend_days | 59239 | 0.33% | 1.44% | 4.51% | 1.43% |
| breakout_day | 3642 | 0.2% | 1.48% | 4.28% | 1.32% |
| breakout_failed | 1206 | -4.16% | -5.11% | -1.43% | -3.44% |
| breakout_held | 2436 | 2.36% | 4.74% | 7.11% | 3.68% |
| confirmed_second_close | 2639 | 0.17% | 1.62% | 4.6% | 1.6% |
| just_under_resistance | 17030 | 0.22% | 0.87% | 2.82% | -0.26% |

"breakout_failed" and "breakout_held" use the next 10 sessions to sort the cases, so they are not tradable signals; they show how much a failure costs.

## 3 · Portfolio simulation (10,000, max 8 positions)

| Variant | CAGR | max drawdown | Sharpe | trades | win rate | avg trade | avg days |
|---|---|---|---|---|---|---|---|
| base_v1_6 | 26.84% | -34.73% | 1.05 | 287 | 29.62% | 4.84% | 28.3 |
| base_v1_5 | 27.96% | -35.77% | 1.03 | 265 | 31.7% | 5.72% | 30.8 |
| no_buy_above_30pct_36d | 15.87% | -27.35% | 0.73 | 271 | 30.26% | 2.65% | 29.9 |
| sell_above_30pct_36d | 10.88% | -27.06% | 0.63 | 353 | 32.01% | 1.55% | 23.3 |
| wait_under_resistance | 28.88% | -33.48% | 0.98 | 296 | 27.03% | 4.51% | 27.6 |
| two_closes_above_resistance | 38.38% | -29.59% | 1.32 | 261 | 32.57% | 7.04% | 30.9 |
| sell_failed_breakout | 26.84% | -34.73% | 1.05 | 287 | 29.62% | 4.84% | 28.3 |
| two_closes_and_sell_failed | 31.83% | -26.4% | 1.18 | 257 | 31.91% | 5.54% | 31.8 |
| wait_res_and_sell_failed | 25.02% | -31.3% | 0.91 | 313 | 26.84% | 3.71% | 26.0 |
| kell_crossback_exit | 27.19% | -32.04% | 1.01 | 647 | 35.39% | 1.73% | 12.2 |
| kell_base_n_break_entry | 7.78% | -16.57% | 0.59 | 204 | 26.47% | 1.29% | 38.3 |
| kell_wedge_pop_entry | 7.85% | -18.57% | 0.55 | 217 | 29.49% | 1.31% | 33.6 |
| kell_full | 10.93% | -21.95% | 0.62 | 515 | 34.56% | 0.79% | 13.5 |
| buffer_200d_1pct | 26.84% | -34.73% | 1.05 | 287 | 29.62% | 4.84% | 28.3 |
| buffer_200d_2pct | 26.84% | -34.73% | 1.05 | 287 | 29.62% | 4.84% | 28.3 |
| buffer_200d_3pct | 26.84% | -34.73% | 1.05 | 287 | 29.62% | 4.84% | 28.3 |
| sell_all_in_correction | 32.94% | -31.65% | 1.11 | 340 | 37.65% | 4.58% | 22.4 |
| sell_all_weak_breadth | 14.87% | -34.17% | 0.63 | 686 | 40.09% | 1.2% | 10.8 |
| sell_all_correction_and_weak_breadth | 25.96% | -23.99% | 0.97 | 333 | 34.23% | 3.69% | 23.6 |
| shorts_in_correction | 29.15% | -35.14% | 0.99 | 416 | 32.69% | 3.38% | 22.4 |
| shorts_always | 14.58% | -33.19% | 0.61 | 568 | 31.69% | 1.53% | 23.1 |
| garch_position_size | 19.77% | -19.16% | 1.19 | 263 | 32.7% | 5.73% | 30.6 |
| ewma_position_size | 20.27% | -20.97% | 1.2 | 259 | 32.43% | 6.32% | 31.4 |
| garch_exposure | 31.2% | -29.22% | 1.17 | 271 | 30.26% | 6.63% | 29.5 |
| ewma_exposure | 36.09% | -34.19% | 1.23 | 290 | 30.69% | 6.17% | 28.1 |
| rebound_sleeve | 23.29% | -30.75% | 0.93 | 563 | 43.52% | 3.0% | 17.7 |
| rebound_sleeve_below_200d | 31.35% | -33.49% | 1.11 | 545 | 40.92% | 3.09% | 18.1 |
| rebound_sleeve_no_stop | 27.03% | -29.85% | 1.03 | 538 | 40.71% | 2.39% | 18.7 |

S&P 500 buy and hold: CAGR 8.9%, max drawdown -25.43%.

## 4 · Separate periods (same variants)

Members enter a period once they have 200 days of prices, so early periods hold fewer stocks.

### 2014-01-02 → 2017-12-29 · 100 stocks · S&P CAGR 9.94%, max drawdown -14.16%

Breakout failure rate 22.57% · 63-day mean: uptrend days 4.53%, just under resistance 4.25%, failed breakouts 0.37% · more than 30% above the 36-day average: n=210, 63-day 13.61%, P(−10% in 21 d) 53.33%

| Variant | CAGR | max drawdown | Sharpe | trades |
|---|---|---|---|---|
| base_v1_6 | 18.57% | -15.53% | 1.14 | 165 |
| base_v1_5 | 18.78% | -14.73% | 1.16 | 162 |
| no_buy_above_30pct_36d | 13.59% | -14.73% | 0.92 | 160 |
| sell_above_30pct_36d | 16.56% | -16.39% | 1.07 | 172 |
| wait_under_resistance | 18.27% | -13.79% | 1.18 | 139 |
| two_closes_above_resistance | 23.74% | -17.09% | 1.39 | 159 |
| sell_failed_breakout | 18.57% | -15.53% | 1.14 | 165 |
| two_closes_and_sell_failed | 17.85% | -18.86% | 1.12 | 163 |
| wait_res_and_sell_failed | 20.12% | -16.77% | 1.27 | 159 |
| kell_crossback_exit | 8.27% | -17.87% | 0.6 | 513 |
| kell_base_n_break_entry | 5.5% | -14.86% | 0.5 | 146 |
| kell_wedge_pop_entry | 11.41% | -17.36% | 0.92 | 172 |
| kell_full | 1.45% | -19.28% | 0.18 | 462 |
| buffer_200d_1pct | 18.57% | -15.53% | 1.14 | 165 |
| buffer_200d_2pct | 18.57% | -15.53% | 1.14 | 165 |
| buffer_200d_3pct | 18.57% | -15.53% | 1.14 | 165 |
| sell_all_in_correction | 12.34% | -15.49% | 0.88 | 222 |
| sell_all_weak_breadth | 14.61% | -14.68% | 0.93 | 186 |
| sell_all_correction_and_weak_breadth | 14.61% | -14.68% | 0.93 | 186 |
| shorts_in_correction | 16.64% | -21.82% | 1.04 | 216 |
| shorts_always | 9.07% | -20.35% | 0.55 | 369 |
| garch_position_size | 17.71% | -16.31% | 1.2 | 153 |
| ewma_position_size | 16.47% | -13.28% | 1.15 | 176 |
| garch_exposure | 20.15% | -16.56% | 1.24 | 156 |
| ewma_exposure | 17.81% | -14.72% | 1.13 | 156 |
| rebound_sleeve | 19.72% | -14.93% | 1.22 | 253 |
| rebound_sleeve_below_200d | 19.01% | -15.61% | 1.15 | 232 |
| rebound_sleeve_no_stop | 21.38% | -14.18% | 1.3 | 250 |

### 2018-01-02 → 2021-12-31 · 117 stocks · S&P CAGR 15.33%, max drawdown -33.92%

Breakout failure rate 30.98% · 63-day mean: uptrend days 5.38%, just under resistance 3.09%, failed breakouts 0.1% · more than 30% above the 36-day average: n=851, 63-day 18.69%, P(−10% in 21 d) 48.3%

| Variant | CAGR | max drawdown | Sharpe | trades |
|---|---|---|---|---|
| base_v1_6 | 25.22% | -19.98% | 1.05 | 222 |
| base_v1_5 | 29.83% | -22.84% | 1.19 | 206 |
| no_buy_above_30pct_36d | 31.47% | -20.22% | 1.24 | 187 |
| sell_above_30pct_36d | 32.31% | -20.39% | 1.44 | 236 |
| wait_under_resistance | 31.75% | -26.67% | 1.24 | 222 |
| two_closes_above_resistance | 24.0% | -21.62% | 1.01 | 205 |
| sell_failed_breakout | 25.22% | -19.98% | 1.05 | 222 |
| two_closes_and_sell_failed | 25.24% | -20.58% | 1.04 | 211 |
| wait_res_and_sell_failed | 27.13% | -30.73% | 1.05 | 232 |
| kell_crossback_exit | 27.47% | -23.15% | 1.11 | 581 |
| kell_base_n_break_entry | 20.08% | -14.15% | 1.22 | 152 |
| kell_wedge_pop_entry | 13.51% | -17.23% | 0.77 | 183 |
| kell_full | 15.7% | -22.22% | 0.84 | 471 |
| buffer_200d_1pct | 30.72% | -20.18% | 1.21 | 212 |
| buffer_200d_2pct | 30.72% | -20.18% | 1.21 | 212 |
| buffer_200d_3pct | 30.72% | -20.18% | 1.21 | 212 |
| sell_all_in_correction | 25.69% | -23.29% | 1.09 | 296 |
| sell_all_weak_breadth | 29.74% | -18.66% | 1.15 | 219 |
| sell_all_correction_and_weak_breadth | 29.74% | -18.66% | 1.15 | 219 |
| shorts_in_correction | 27.8% | -26.46% | 1.06 | 293 |
| shorts_always | 18.91% | -29.84% | 0.76 | 456 |
| garch_position_size | 21.09% | -14.67% | 1.24 | 192 |
| ewma_position_size | 17.41% | -17.79% | 1.02 | 211 |
| garch_exposure | 32.51% | -16.02% | 1.42 | 199 |
| ewma_exposure | 17.7% | -17.25% | 0.88 | 227 |
| rebound_sleeve | 34.91% | -26.54% | 1.3 | 345 |
| rebound_sleeve_below_200d | 30.61% | -25.61% | 1.22 | 334 |
| rebound_sleeve_no_stop | 32.53% | -27.22% | 1.26 | 337 |

### 2022-01-03 → 2026-11-24 · 128 stocks · S&P CAGR 8.66%, max drawdown -25.43%

Breakout failure rate 33.14% · 63-day mean: uptrend days 4.78%, just under resistance 2.96%, failed breakouts -1.29% · more than 30% above the 36-day average: n=1565, 63-day 16.16%, P(−10% in 21 d) 51.82%

| Variant | CAGR | max drawdown | Sharpe | trades |
|---|---|---|---|---|
| base_v1_6 | 24.57% | -32.8% | 0.95 | 274 |
| base_v1_5 | 34.77% | -30.21% | 1.14 | 261 |
| no_buy_above_30pct_36d | 23.76% | -32.12% | 0.95 | 252 |
| sell_above_30pct_36d | 9.74% | -25.63% | 0.59 | 343 |
| wait_under_resistance | 26.32% | -29.51% | 0.96 | 279 |
| two_closes_above_resistance | 21.37% | -27.7% | 0.91 | 259 |
| sell_failed_breakout | 24.57% | -32.8% | 0.95 | 274 |
| two_closes_and_sell_failed | 31.15% | -31.66% | 1.19 | 265 |
| wait_res_and_sell_failed | 25.31% | -31.47% | 0.94 | 298 |
| kell_crossback_exit | 29.7% | -30.23% | 1.09 | 621 |
| kell_base_n_break_entry | 3.92% | -17.2% | 0.35 | 214 |
| kell_wedge_pop_entry | 7.76% | -16.55% | 0.56 | 215 |
| kell_full | 7.97% | -26.34% | 0.49 | 500 |
| buffer_200d_1pct | 24.57% | -32.8% | 0.95 | 274 |
| buffer_200d_2pct | 24.57% | -32.8% | 0.95 | 274 |
| buffer_200d_3pct | 24.57% | -32.8% | 0.95 | 274 |
| sell_all_in_correction | 24.44% | -25.72% | 1.01 | 344 |
| sell_all_weak_breadth | 17.23% | -24.41% | 0.73 | 675 |
| sell_all_correction_and_weak_breadth | 28.31% | -34.17% | 1.01 | 315 |
| shorts_in_correction | 23.67% | -33.54% | 0.92 | 405 |
| shorts_always | 22.1% | -34.98% | 0.81 | 536 |
| garch_position_size | 20.8% | -19.08% | 1.24 | 250 |
| ewma_position_size | 21.47% | -20.87% | 1.27 | 247 |
| garch_exposure | 32.47% | -33.47% | 1.15 | 258 |
| ewma_exposure | 32.14% | -30.14% | 1.18 | 264 |
| rebound_sleeve | 19.13% | -25.63% | 0.82 | 531 |
| rebound_sleeve_below_200d | 23.62% | -29.07% | 0.95 | 514 |
| rebound_sleeve_no_stop | 24.46% | -31.03% | 0.99 | 501 |

### Robustness: windows in which a variant beat base_v1_6 (the current rules)

| Variant | CAGR | max drawdown (less deep) | Sharpe |
|---|---|---|---|
| no_buy_above_30pct_36d | 1/3 | 2/3 | 1/3 |
| sell_above_30pct_36d | 1/3 | 1/3 | 1/3 |
| wait_under_resistance | 2/3 | 2/3 | 3/3 |
| two_closes_above_resistance | 1/3 | 1/3 | 1/3 |
| sell_failed_breakout | 0/3 | 0/3 | 0/3 |
| two_closes_and_sell_failed | 2/3 | 1/3 | 1/3 |
| wait_res_and_sell_failed | 3/3 | 1/3 | 1/3 |
| kell_crossback_exit | 2/3 | 1/3 | 2/3 |
| kell_base_n_break_entry | 0/3 | 3/3 | 1/3 |
| kell_wedge_pop_entry | 0/3 | 2/3 | 0/3 |
| kell_full | 0/3 | 1/3 | 0/3 |
| buffer_200d_1pct | 1/3 | 0/3 | 1/3 |
| buffer_200d_2pct | 1/3 | 0/3 | 1/3 |
| buffer_200d_3pct | 1/3 | 0/3 | 1/3 |
| sell_all_in_correction | 1/3 | 2/3 | 2/3 |
| sell_all_weak_breadth | 1/3 | 3/3 | 1/3 |
| sell_all_correction_and_weak_breadth | 2/3 | 2/3 | 2/3 |
| shorts_in_correction | 1/3 | 0/3 | 1/3 |
| shorts_always | 0/3 | 0/3 | 0/3 |
| garch_position_size | 0/3 | 2/3 | 3/3 |
| ewma_position_size | 0/3 | 3/3 | 2/3 |
| garch_exposure | 3/3 | 1/3 | 3/3 |
| ewma_exposure | 1/3 | 3/3 | 1/3 |
| rebound_sleeve | 2/3 | 2/3 | 2/3 |
| rebound_sleeve_below_200d | 2/3 | 1/3 | 2/3 |
| rebound_sleeve_no_stop | 2/3 | 2/3 | 3/3 |

Symbols: 128 · generated 2026-11-25T22:30+00:00 · price data 875baebb3622fbf9

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

### 2021-11-24 → 2026-11-24

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

Ending equity difference: +4606.24; total-return difference +46.06 percentage points. Differing positions: 260.

Two largest positive contributions: 24.3% of gross positive contributions. This describes concentration within this historical path.

Largest positive lot: BBW entered 2021-04-26, +28.868 total-return pp.
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

### 2022-01-03 → 2026-11-24

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
| base_v1_5 | 6 / 0 / 14 | +0.21 | -1.72 [-6.96, +6.68] | +0.79 [-2.47, +4.93] | -0.09 [-0.34, +0.34] |
| no_buy_above_30pct_36d | 2 / 0 / 18 | -4.98 | -5.27 [-8.55, +4.39] | +0.79 [-2.47, +4.93] | -0.27 [-0.41, +0.23] |
| sell_above_30pct_36d | 1 / 0 / 19 | -2.01 | -2.79 [-7.39, +2.77] | +0.68 [-3.81, +4.93] | -0.11 [-0.37, +0.17] |
| wait_under_resistance | 8 / 0 / 12 | -0.31 | -0.36 [-5.35, +7.53] | +2.19 [-1.74, +7.61] | +0.03 [-0.27, +0.33] |
| two_closes_above_resistance | 10 / 0 / 10 | +5.17 | +0.03 [-7.18, +6.20] | -0.93 [-5.87, +2.77] | +0.04 [-0.34, +0.30] |
| sell_failed_breakout | 0 / 20 / 0 | +0.00 | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] |
| two_closes_and_sell_failed | 7 / 0 / 13 | -0.72 | -1.95 [-6.01, +1.20] | -1.43 [-5.87, +1.44] | -0.11 [-0.33, +0.10] |
| wait_res_and_sell_failed | 10 / 0 / 10 | +1.55 | -0.01 [-3.87, +5.13] | +0.87 [-1.51, +5.62] | +0.03 [-0.16, +0.22] |
| kell_crossback_exit | 0 / 0 / 20 | -10.30 | -9.15 [-16.79, -3.15] | -0.90 [-4.09, +6.21] | -0.47 [-0.94, -0.20] |
| kell_base_n_break_entry | 0 / 0 / 20 | -13.07 | -14.70 [-18.45, -10.57] | +0.63 [-5.19, +3.14] | -0.74 [-0.99, -0.46] |
| kell_wedge_pop_entry | 0 / 0 / 20 | -7.16 | -9.69 [-14.02, -3.28] | -1.32 [-5.57, +3.64] | -0.33 [-0.66, +0.03] |
| kell_full | 0 / 0 / 20 | -17.12 | -16.18 [-20.06, -11.31] | -3.61 [-7.45, +1.05] | -0.85 [-1.12, -0.60] |
| buffer_200d_1pct | 1 / 19 / 0 | +0.00 | +0.00 [+0.00, +1.49] | +0.00 [+0.00, +3.80] | +0.00 [+0.00, +0.08] |
| buffer_200d_2pct | 1 / 18 / 1 | +0.00 | +0.00 [-1.60, +1.49] | +0.00 [+0.00, +3.80] | +0.00 [-0.06, +0.08] |
| buffer_200d_3pct | 1 / 18 / 1 | +0.00 | +0.00 [-1.60, +1.49] | +0.00 [+0.00, +3.80] | +0.00 [-0.06, +0.08] |
| sell_all_in_correction | 0 / 0 / 20 | -6.23 | -4.15 [-9.52, -0.19] | +0.21 [-4.28, +4.33] | -0.14 [-0.49, +0.05] |
| sell_all_weak_breadth | 3 / 0 / 17 | -3.96 | -4.34 [-6.64, +1.57] | +0.19 [-1.73, +1.33] | -0.24 [-0.38, +0.05] |
| sell_all_correction_and_weak_breadth | 3 / 0 / 17 | -3.96 | -4.34 [-6.64, +1.57] | +0.19 [-1.73, +1.33] | -0.24 [-0.38, +0.05] |
| shorts_in_correction | 0 / 0 / 20 | -1.93 | -3.03 [-6.45, -0.34] | -6.70 [-11.32, -5.59] | -0.19 [-0.34, -0.05] |
| shorts_always | 0 / 0 / 20 | -9.50 | -9.57 [-14.22, -6.67] | -4.86 [-8.54, +0.02] | -0.60 [-0.82, -0.47] |
| garch_position_size | 6 / 0 / 14 | -0.86 | -0.92 [-4.19, +4.66] | +1.69 [-0.85, +6.05] | +0.08 [-0.09, +0.37] |
| ewma_position_size | 1 / 0 / 19 | -2.10 | -2.33 [-5.60, +1.56] | +2.12 [-2.60, +3.85] | +0.01 [-0.16, +0.21] |
| garch_exposure | 7 / 0 / 13 | +1.58 | -2.57 [-5.42, +2.68] | -0.53 [-4.92, +1.91] | -0.14 [-0.34, +0.16] |
| ewma_exposure | 3 / 0 / 17 | -0.76 | -1.02 [-3.32, +2.55] | +0.38 [-3.36, +3.40] | -0.02 [-0.15, +0.13] |
| rebound_sleeve | 12 / 0 / 8 | +1.15 | +0.47 [-5.01, +5.69] | -3.73 [-8.92, +2.23] | +0.02 [-0.31, +0.25] |
| rebound_sleeve_below_200d | 17 / 0 / 3 | +0.44 | +0.81 [-6.01, +4.81] | -4.10 [-10.23, +2.55] | +0.01 [-0.31, +0.22] |
| rebound_sleeve_no_stop | 11 / 0 / 9 | +2.81 | +0.60 [-4.42, +4.64] | -2.92 [-9.32, +3.07] | -0.01 [-0.27, +0.17] |

### 2018-01-02 → 2021-12-31

20 paired starts. Counts use unrounded ending equity.

| Variant | W / T / L | Original start ΔCAGR | ΔCAGR | ΔMax DD | ΔSharpe |
|---|---|---:|---|---|---|
| base_v1_5 | 11 / 0 / 9 | +4.61 | +1.64 [-8.26, +15.86] | -1.37 [-4.37, +1.46] | -0.00 [-0.24, +0.49] |
| no_buy_above_30pct_36d | 11 / 0 / 9 | +6.25 | +0.56 [-10.47, +9.60] | +1.10 [-2.33, +5.32] | +0.02 [-0.30, +0.30] |
| sell_above_30pct_36d | 12 / 0 / 8 | +7.09 | +0.89 [-6.30, +11.21] | +2.25 [-1.44, +5.71] | +0.23 [-0.03, +0.53] |
| wait_under_resistance | 8 / 0 / 12 | +6.53 | -2.12 [-8.16, +6.53] | -4.26 [-7.24, +2.79] | -0.10 [-0.21, +0.22] |
| two_closes_above_resistance | 5 / 0 / 15 | -1.21 | -2.60 [-10.47, +7.68] | +1.36 [-3.16, +3.82] | -0.08 [-0.33, +0.26] |
| sell_failed_breakout | 0 / 20 / 0 | +0.00 | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] |
| two_closes_and_sell_failed | 7 / 0 / 13 | +0.02 | -2.18 [-8.38, +7.94] | +1.68 [-3.38, +5.02] | -0.06 [-0.23, +0.24] |
| wait_res_and_sell_failed | 6 / 0 / 14 | +1.91 | -4.61 [-12.32, +8.05] | -7.10 [-15.74, +0.56] | -0.15 [-0.39, +0.20] |
| kell_crossback_exit | 6 / 0 / 14 | +2.25 | -3.70 [-9.95, +8.74] | -0.56 [-6.70, +2.81] | -0.07 [-0.32, +0.27] |
| kell_base_n_break_entry | 0 / 0 / 20 | -5.14 | -13.61 [-17.70, -3.62] | +6.79 [+3.24, +8.61] | -0.06 [-0.24, +0.20] |
| kell_wedge_pop_entry | 0 / 0 / 20 | -11.71 | -11.37 [-19.57, -3.47] | +6.32 [+2.75, +8.25] | -0.13 [-0.46, +0.06] |
| kell_full | 0 / 0 / 20 | -9.51 | -16.96 [-24.75, -8.44] | -1.01 [-5.63, +1.69] | -0.46 [-0.75, -0.20] |
| buffer_200d_1pct | 8 / 0 / 12 | +5.51 | -1.71 [-11.64, +10.29] | -0.27 [-4.15, +5.07] | -0.04 [-0.31, +0.31] |
| buffer_200d_2pct | 9 / 0 / 11 | +5.51 | -1.29 [-11.64, +10.29] | -0.27 [-4.15, +5.07] | -0.03 [-0.31, +0.31] |
| buffer_200d_3pct | 9 / 0 / 11 | +5.51 | -1.29 [-11.64, +10.29] | -0.27 [-4.15, +5.07] | -0.03 [-0.31, +0.31] |
| sell_all_in_correction | 9 / 0 / 11 | +0.48 | -2.01 [-8.50, +12.34] | +3.82 [-3.32, +5.05] | -0.03 [-0.25, +0.39] |
| sell_all_weak_breadth | 10 / 0 / 10 | +4.52 | -0.36 [-8.63, +12.64] | +3.52 [-1.50, +7.39] | -0.01 [-0.25, +0.34] |
| sell_all_correction_and_weak_breadth | 10 / 0 / 10 | +4.52 | -0.36 [-8.63, +12.64] | +3.52 [-1.50, +7.39] | -0.01 [-0.25, +0.34] |
| shorts_in_correction | 4 / 0 / 16 | +2.58 | -2.27 [-6.02, +5.14] | -3.64 [-7.09, -1.04] | -0.09 [-0.24, +0.08] |
| shorts_always | 0 / 0 / 20 | -6.31 | -13.09 [-21.79, -2.32] | -11.21 [-15.65, -7.57] | -0.48 [-0.74, -0.16] |
| garch_position_size | 0 / 0 / 20 | -4.13 | -14.31 [-18.79, -4.13] | +6.11 [+3.26, +8.81] | -0.16 [-0.41, +0.19] |
| ewma_position_size | 0 / 0 / 20 | -7.81 | -14.99 [-19.08, -4.57] | +4.63 [+1.74, +7.64] | -0.23 [-0.38, +0.06] |
| garch_exposure | 12 / 0 / 8 | +7.29 | +0.17 [-6.19, +11.26] | +4.65 [+1.38, +8.94] | +0.16 [-0.05, +0.44] |
| ewma_exposure | 0 / 0 / 20 | -7.51 | -12.08 [-19.26, -1.29] | +4.39 [+1.79, +7.61] | -0.27 [-0.55, +0.07] |
| rebound_sleeve | 17 / 0 / 3 | +9.69 | +4.29 [-2.84, +16.05] | -4.79 [-8.72, +0.27] | +0.12 [-0.09, +0.43] |
| rebound_sleeve_below_200d | 15 / 0 / 5 | +5.40 | +2.97 [-2.17, +17.63] | -5.77 [-10.70, -1.92] | +0.07 [-0.09, +0.45] |
| rebound_sleeve_no_stop | 15 / 0 / 5 | +7.31 | +4.65 [-4.33, +13.45] | -3.60 [-8.82, -0.67] | +0.13 [-0.17, +0.34] |

### 2022-01-03 → 2026-11-24

20 paired starts. Counts use unrounded ending equity.

| Variant | W / T / L | Original start ΔCAGR | ΔCAGR | ΔMax DD | ΔSharpe |
|---|---|---:|---|---|---|
| base_v1_5 | 8 / 0 / 12 | +10.20 | -2.05 [-11.87, +24.06] | +1.80 [-1.71, +4.38] | -0.10 [-0.33, +0.54] |
| no_buy_above_30pct_36d | 3 / 0 / 17 | -0.80 | -9.79 [-18.33, +4.01] | +3.16 [-1.33, +8.88] | -0.20 [-0.41, +0.14] |
| sell_above_30pct_36d | 0 / 0 / 20 | -14.83 | -23.47 [-27.62, -8.97] | +7.14 [+1.23, +9.77] | -0.52 [-0.63, -0.21] |
| wait_under_resistance | 7 / 0 / 13 | +1.76 | -3.94 [-7.71, +15.70] | +2.09 [-3.19, +5.93] | -0.10 [-0.21, +0.33] |
| two_closes_above_resistance | 18 / 0 / 2 | -3.19 | +6.96 [-3.19, +18.30] | +4.35 [-5.68, +8.12] | +0.15 [-0.04, +0.48] |
| sell_failed_breakout | 0 / 20 / 0 | +0.00 | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] |
| two_closes_and_sell_failed | 17 / 0 / 3 | +6.58 | +6.15 [-5.98, +16.18] | +4.22 [-5.36, +6.46] | +0.20 [-0.09, +0.37] |
| wait_res_and_sell_failed | 11 / 0 / 9 | +0.75 | +0.55 [-13.24, +19.14] | +0.10 [-5.41, +1.99] | -0.11 [-0.38, +0.40] |
| kell_crossback_exit | 6 / 0 / 14 | +5.13 | -7.72 [-13.87, +7.33] | +2.45 [-5.37, +7.22] | -0.15 [-0.33, +0.19] |
| kell_base_n_break_entry | 0 / 0 / 20 | -20.65 | -31.69 [-36.00, -13.39] | +16.83 [+7.52, +18.49] | -0.86 [-0.97, -0.32] |
| kell_wedge_pop_entry | 0 / 0 / 20 | -16.80 | -27.54 [-31.47, -9.92] | +18.19 [+8.84, +19.81] | -0.56 [-0.81, -0.09] |
| kell_full | 0 / 0 / 20 | -16.59 | -23.99 [-29.37, -8.73] | +8.14 [+1.30, +9.80] | -0.52 [-0.75, -0.23] |
| buffer_200d_1pct | 0 / 20 / 0 | +0.00 | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] |
| buffer_200d_2pct | 0 / 20 / 0 | +0.00 | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] |
| buffer_200d_3pct | 0 / 20 / 0 | +0.00 | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] |
| sell_all_in_correction | 7 / 0 / 13 | -0.12 | -0.62 [-13.82, +13.20] | +4.51 [-1.11, +11.88] | -0.04 [-0.37, +0.35] |
| sell_all_weak_breadth | 2 / 0 / 18 | -7.33 | -8.62 [-23.16, +11.90] | +2.43 [-5.01, +8.39] | -0.23 [-0.59, +0.26] |
| sell_all_correction_and_weak_breadth | 5 / 0 / 15 | +3.75 | -5.31 [-7.92, +20.03] | +5.20 [-7.17, +8.90] | -0.09 [-0.20, +0.45] |
| shorts_in_correction | 6 / 0 / 14 | -0.89 | -2.10 [-15.35, +12.64] | -0.67 [-8.12, +2.30] | -0.16 [-0.43, +0.23] |
| shorts_always | 2 / 0 / 18 | -2.46 | -13.66 [-23.60, +2.84] | -2.47 [-7.74, +4.50] | -0.43 [-0.69, +0.02] |
| garch_position_size | 2 / 0 / 18 | -3.77 | -12.01 [-15.39, +2.78] | +13.87 [+5.92, +14.74] | +0.17 [+0.08, +0.48] |
| ewma_position_size | 2 / 0 / 18 | -3.10 | -11.85 [-19.58, +6.73] | +12.06 [+3.42, +12.39] | +0.19 [-0.29, +0.63] |
| garch_exposure | 13 / 0 / 7 | +7.91 | +4.12 [-6.44, +16.90] | -0.03 [-8.07, +0.78] | +0.13 [-0.16, +0.37] |
| ewma_exposure | 14 / 0 / 6 | +7.58 | +5.80 [-5.73, +25.01] | -0.37 [-8.07, +4.36] | +0.09 [-0.16, +0.58] |
| rebound_sleeve | 4 / 0 / 16 | -5.43 | -7.55 [-21.34, +18.51] | +1.36 [-4.83, +10.35] | -0.14 [-0.52, +0.47] |
| rebound_sleeve_below_200d | 4 / 0 / 16 | -0.94 | -9.90 [-19.12, +6.27] | +2.21 [-8.05, +6.33] | -0.13 [-0.42, +0.20] |
| rebound_sleeve_no_stop | 3 / 0 / 17 | -0.10 | -7.58 [-22.09, +10.60] | +1.57 [-5.73, +6.41] | -0.14 [-0.54, +0.34] |


## Pairs trading (same-sector, Engle-Granger + Ornstein-Uhlenbeck)

Yearly formation on 504 sessions, entry |z|>2, exit |z|<0.5, stop |z|>4, dollar-neutral 5% legs, 0.1% per fill, 2% borrow. Passes only with a positive return and Sharpe ≥ 0.5 in every period.

| Method | Period | Pairs/year | CAGR | Sharpe | Max DD | Trades | Win rate | Corr. S&P |
|---|---|---|---:|---:|---:|---:|---:|---:|
| pairs_static | 2014-01-01 → 2018-01-01 | 7,6,5 | -2.6 | -0.91 | -8.67 | 61 | 34.4 | -0.0 |
| pairs_static | 2018-01-01 → 2022-01-01 | 10,4,6,10 | -2.2 | -0.55 | -11.41 | 115 | 32.2 | 0.08 |
| pairs_static | 2022-01-01 → now | 10,4,8,5,3 | 0.76 | 0.22 | -5.12 | 121 | 40.5 | 0.11 |
| pairs_static | **fails** | | | | | | | |
| pairs_kalman | 2014-01-01 → 2018-01-01 | 7,6,5 | 0.45 | 0.13 | -7.56 | 146 | 46.6 | -0.02 |
| pairs_kalman | 2018-01-01 → 2022-01-01 | 10,4,6,10 | -1.93 | -0.61 | -7.49 | 258 | 46.9 | 0.04 |
| pairs_kalman | 2022-01-01 → now | 10,4,8,5,3 | -0.31 | -0.1 | -7.61 | 209 | 53.6 | -0.01 |
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
| 2022-01-03 → 2026-11-25 | buy_and_hold | — | 8.99% | — | — | — |
| 2022-01-03 → 2026-11-25 | codex_20d_5d_long_short | 0/20 | -9.12% | -20.45 [-25.74, -17.90] | -1.34 | -21.46 |
| 2022-01-03 → 2026-11-25 | codex_20d_5d_long_only | 0/20 | 1.55% | -10.16 [-13.51, -8.54] | -0.50 | +13.57 |
| 2022-01-03 → 2026-11-25 | trend_200d | 0/20 | 8.20% | -3.38 [-6.26, -2.46] | +0.04 | +12.63 |
| 2022-01-03 → 2026-11-25 | codex_intraday_account | 0/20 | -24.51% | -36.20 [-40.47, -33.40] | -4.99 | -50.88 |

Passes: codex_20d_5d_long_short no, codex_20d_5d_long_only no, trend_200d no, codex_intraday_account no


## Buy the oversold dip, sell the rebound

Signal: three red closes and at least 3 ATR under the 21-day EMA. Entry at the signal close, exit at the first close above the 10-day EMA or after 10 sessions; stop 8% (close) unless "no_stop"; 0.1% cost per side. Passes only with at least 30 trades and a positive mean and median excess over the S&P 500 in every period.

| Period | Variant | Trades | Win rate | Mean | Median | Mean vs S&P | Median vs S&P | Worst | 5th pct | Stops |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2014-01-02 → 2017-12-29 | all | 313 | 65% | +1.30% | +2.03% | +0.51% | +0.55% | -24.82% | -10.46% | 12% |
| 2014-01-02 → 2017-12-29 | above_sma200 | 54 | 72% | +1.67% | +2.41% | +0.85% | +1.42% | -9.22% | -8.57% | 7% |
| 2014-01-02 → 2017-12-29 | below_sma200 | 264 | 64% | +1.14% | +1.92% | +0.36% | +0.51% | -24.82% | -10.68% | 13% |
| 2014-01-02 → 2017-12-29 | all_no_stop | 299 | 66% | +1.16% | +2.03% | +0.33% | +0.56% | -33.26% | -11.01% | 0% |
| 2014-01-02 → 2017-12-29 | below_sma200_no_stop | 251 | 65% | +0.95% | +1.95% | +0.14% | +0.53% | -33.26% | -11.54% | 0% |
| 2014-01-02 → 2017-12-29 | at_weekly_sma200 | 8 | 25% | -3.18% | -3.92% | -3.61% | -3.94% | -9.13% | -9.13% | 12% |
| 2014-01-02 → 2017-12-29 | at_weekly_sma200_no_stop | 8 | 25% | -3.06% | -3.92% | -3.36% | -3.94% | -8.13% | -8.13% | 0% |
| 2018-01-02 → 2021-12-31 | all | 428 | 58% | +1.05% | +2.16% | +1.09% | +0.83% | -52.11% | -15.94% | 23% |
| 2018-01-02 → 2021-12-31 | above_sma200 | 69 | 70% | +2.32% | +3.19% | +1.63% | +1.77% | -19.00% | -12.80% | 14% |
| 2018-01-02 → 2021-12-31 | below_sma200 | 365 | 57% | +0.84% | +1.68% | +0.97% | +0.73% | -52.11% | -16.08% | 24% |
| 2018-01-02 → 2021-12-31 | all_no_stop | 396 | 61% | +0.67% | +2.69% | +1.13% | +1.22% | -59.26% | -23.28% | 0% |
| 2018-01-02 → 2021-12-31 | below_sma200_no_stop | 336 | 59% | +0.29% | +2.12% | +0.93% | +1.05% | -59.26% | -23.41% | 0% |
| 2018-01-02 → 2021-12-31 | at_weekly_sma200 | 60 | 62% | -0.55% | +1.55% | +0.35% | +0.50% | -21.38% | -17.25% | 20% |
| 2018-01-02 → 2021-12-31 | at_weekly_sma200_no_stop | 60 | 62% | -1.09% | +1.55% | +0.58% | +0.29% | -36.69% | -21.10% | 0% |
| 2022-01-03 → 2026-11-24 | all | 703 | 60% | +1.34% | +2.18% | +0.50% | +0.79% | -26.68% | -12.23% | 18% |
| 2022-01-03 → 2026-11-24 | above_sma200 | 61 | 54% | +0.53% | +0.84% | -0.71% | -0.13% | -13.90% | -8.45% | 10% |
| 2022-01-03 → 2026-11-24 | below_sma200 | 650 | 61% | +1.43% | +2.26% | +0.60% | +0.88% | -26.68% | -12.34% | 18% |
| 2022-01-03 → 2026-11-24 | all_no_stop | 665 | 63% | +1.72% | +2.44% | +0.75% | +1.03% | -29.38% | -12.26% | 0% |
| 2022-01-03 → 2026-11-24 | below_sma200_no_stop | 614 | 64% | +1.82% | +2.52% | +0.85% | +1.12% | -29.38% | -12.26% | 0% |
| 2022-01-03 → 2026-11-24 | at_weekly_sma200 | 113 | 58% | +0.92% | +1.83% | +0.30% | +0.72% | -12.47% | -10.68% | 17% |
| 2022-01-03 → 2026-11-24 | at_weekly_sma200_no_stop | 113 | 58% | +1.05% | +1.83% | +0.43% | +0.79% | -21.46% | -10.33% | 0% |

Passes: all yes, above_sma200 no, below_sma200 yes, all_no_stop yes, below_sma200_no_stop yes, at_weekly_sma200 no, at_weekly_sma200_no_stop no

NVDA in November 2026 under this rule (with the 8% stop): signal 2026-11-16 at 156.14 (-3.5 ATR) → stop on 2026-11-20, -19.76%

NVDA's 200-week average on 2026-11-24: 123.33.

## Thermometer "Panic · buy": buy the leader

Signal: the thermometer (market_pulse.py, rebuilt without Fear & Greed) closes under 20; one signal per episode (63 sessions apart). Bought at the next close; 0.1% per side. Leader: highest 21/200-day average ratio in the universe on the signal day; top5: the five highest. Today's universe, so stock baskets are flattered by survivorship.

Rebuilt thermometer on 2026-11-24: 29.6.

### First panic close

| Sessions | Signals | Leader mean / median | Top 5 mean / median | Universe mean | S&P 500 mean / median | Leader beats S&P | Leader worst |
|---:|---:|---|---|---:|---|---:|---:|
| 21 | 6 | +4.4% / +5.8% | +5.8% / +3.2% | +5.2% | +4.2% / +5.0% | 3/6 | -15.1% |
| 63 | 6 | +33.7% / +33.1% | +30.8% / +26.5% | +17.5% | +11.7% / +11.5% | 5/6 | -0.6% |
| 126 | 6 | +72.8% / +85.2% | +63.4% / +38.4% | +24.4% | +13.5% / +15.1% | 5/6 | -7.1% |
| 252 | 6 | +138.8% / +73.5% | +72.8% / +49.9% | +39.6% | +21.7% / +25.4% | 4/6 | -6.4% |

Signals: 2015-08-24 (heat 6.3, leader NFLX: 63 sessions +22.9%, S&P +11.5%); 2016-01-15 (heat 18.7, leader NVDA: 63 sessions +33.1%, S&P +11.4%); 2018-12-19 (heat 19.6, leader TTD: 63 sessions +67.9%, S&P +13.2%); 2020-03-09 (heat 8.4, leader TSLA: 63 sessions +45.5%, S&P +11.1%); 2022-03-07 (heat 14.6, leader DVN: 63 sessions +33.1%, S&P -0.4%); 2025-04-04 (heat 5.3, leader BABA: 63 sessions -0.6%, S&P +23.5%); 2026-11-20 (heat 15.6, leader MRNA: 63 sessions —, S&P —)

### First close back above 20

| Sessions | Signals | Leader mean / median | Top 5 mean / median | Universe mean | S&P 500 mean / median | Leader beats S&P | Leader worst |
|---:|---:|---|---|---:|---|---:|---:|
| 21 | 6 | +23.0% / +19.4% | +14.7% / +11.5% | +6.8% | +4.4% / +3.9% | 4/6 | -16.6% |
| 63 | 6 | +44.3% / +29.4% | +49.1% / +29.6% | +16.5% | +10.3% / +13.3% | 5/6 | +5.4% |
| 126 | 6 | +63.5% / +75.8% | +83.0% / +50.3% | +25.1% | +13.6% / +18.6% | 5/6 | -16.6% |
| 252 | 6 | +126.0% / +87.8% | +96.9% / +60.6% | +41.2% | +22.4% / +26.6% | 3/6 | -17.4% |

Signals: 2015-08-27 (heat 30.3, leader NFLX: 63 sessions +6.4%, S&P +4.9%); 2016-01-22 (heat 25.1, leader NVDA: 63 sessions +28.5%, S&P +11.0%); 2019-01-02 (heat 21.6, leader TTD: 63 sessions +80.4%, S&P +17.4%); 2020-04-14 (heat 26.2, leader MRNA: 63 sessions +114.9%, S&P +15.7%); 2022-03-09 (heat 21.0, leader DVN: 63 sessions +30.4%, S&P -5.9%); 2025-04-09 (heat 20.6, leader BABA: 63 sessions +5.4%, S&P +18.8%); 2026-11-23 (heat 29.1, leader MRNA: 63 sessions —, S&P —)

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
| hold_63 | 6 | 1 | 0 | 63 | +11.3% / +12.9% | +9.9% | 3/6 | -5.7% |
| euphoria | 6 | 1 | 0 | 60 | +10.0% / +12.5% | +9.3% | 3/6 | -11.1% |
| euphoria_after_63 | 6 | 1 | 0 | 66 | +12.0% / +14.1% | +10.5% | 3/6 | -11.1% |
| euphoria_or_252 | 6 | 1 | 0 | 60 | +10.0% / +12.5% | +9.3% | 3/6 | -11.1% |
| euphoria_stop_basket_10 | 6 | 1 | 2 | 50 | +7.3% / +3.9% | +6.0% | 3/6 | -7.7% |
| euphoria_stop_basket_15 | 6 | 1 | 2 | 54 | +5.0% / +3.9% | +3.3% | 3/6 | -15.6% |
| euphoria_stop_spx_10 | 6 | 1 | 2 | 54 | +6.0% / +3.9% | +4.8% | 3/6 | -15.6% |

Per signal (euphoria): 2016-01-15 → 2016-04-04 (52 sessions): +8.9% vs S&P +9.8%; 2018-12-19 → 2019-03-22 (62 sessions): +16.0% vs S&P +13.5%; 2020-03-09 → 2020-06-09 (63 sessions): +16.1% vs S&P +11.3%; 2022-03-07 → 2023-02-03 (229 sessions): -11.1% vs S&P -0.8%; 2025-04-04 → 2025-06-30 (57 sessions): +31.3% vs S&P +22.6%; 2026-11-20 → 2026-11-24 (1 sessions, open): -1.2% vs S&P -0.5%

Per signal (euphoria_stop_basket_15): 2016-01-15 → 2016-04-04 (52 sessions): +8.9% vs S&P +9.8%; 2018-12-19 → 2019-03-22 (62 sessions): +16.0% vs S&P +13.5%; 2020-03-09 → 2020-03-24 (10 sessions, stopped): -9.6% vs S&P -15.1%; 2022-03-07 → 2022-06-14 (68 sessions, stopped): -15.6% vs S&P -10.4%; 2025-04-04 → 2025-06-30 (57 sessions): +31.3% vs S&P +22.6%; 2026-11-20 → 2026-11-24 (1 sessions, open): -1.2% vs S&P -0.5%

Per signal (euphoria_stop_spx_10): 2016-01-15 → 2016-04-04 (52 sessions): +8.9% vs S&P +9.8%; 2018-12-19 → 2019-03-22 (62 sessions): +16.0% vs S&P +13.5%; 2020-03-09 → 2020-03-13 (3 sessions, stopped): -3.6% vs S&P -5.9%; 2022-03-07 → 2022-06-14 (68 sessions, stopped): -15.6% vs S&P -10.4%; 2025-04-04 → 2025-06-30 (57 sessions): +31.3% vs S&P +22.6%; 2026-11-20 → 2026-11-24 (1 sessions, open): -1.2% vs S&P -0.5%

#### Buy only at a later close still in panic (the paper account's rule since 23 Nov 2026)

Same ten largest by weight, bought at the first close after the signal with the thermometer still under 20 (the close value stands in for the intraday check 20 minutes earlier); episodes without such a close within 63 sessions buy nothing. Skipped: 2026-11-20.

| Exit | Signals | Mean / median return | S&P 500 same span | Beats S&P | Worst |
|---|---:|---|---:|---:|---:|
| hold_63 | 5 | +13.7% / +15.5% | +12.0% | 3/5 | -5.7% |
| euphoria_or_252 | 5 | +12.2% / +16.0% | +11.3% | 3/5 | -11.1% |

Per signal (euphoria_or_252): bought 2016-01-15 → 2016-04-04: +8.9% vs S&P +9.8%; bought 2018-12-19 → 2019-03-22: +16.0% vs S&P +13.5%; bought 2020-03-09 → 2020-06-09: +16.1% vs S&P +11.3%; bought 2022-03-07 → 2023-02-03: -11.1% vs S&P -0.8%; bought 2025-04-04 → 2025-06-30: +31.3% vs S&P +22.6%
