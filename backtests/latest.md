# Backtest of the technical rules · 2021-11-23 → 2026-11-23

Technical rules on current members. Historical membership and full label history are unavailable. Survivorship bias may affect strategies differently. Decision on close t, fill at close t+1, 0.10% per fill. Historical technical simulation uses local quote units and excludes FX. Compare variants within this simulation.

## 1 · After a close far above the 36-day average

| Distance to 36-day avg | days | stocks | 21-day mean | 63-day mean | 63-day vs S&P | P(−10% within 21 d) | P(63 d < 0) |
|---|---|---|---|---|---|---|---|
| -100..0% | 69916 | 125 | 1.36% | 4.34% | 0.99% | 25.55% | 46.73% |
| 0..10% | 59927 | 125 | 0.94% | 2.87% | 0.13% | 19.92% | 47.63% |
| 10..20% | 11219 | 124 | 1.46% | 5.24% | 2.57% | 29.68% | 47.47% |
| 20..30% | 2264 | 85 | 3.28% | 9.29% | 6.91% | 40.02% | 47.08% |
| 30..+% | 1545 | 52 | 6.17% | 16.52% | 14.22% | 51.72% | 46.34% |

## 2 · Breakouts above the prior 60-session high (in an uptrend) · failure rate 33.02%

| Case | days | 5-day mean | 21-day mean | 63-day mean | 63-day vs S&P |
|---|---|---|---|---|---|
| all_uptrend_days | 58159 | 0.34% | 1.5% | 4.68% | 1.6% |
| breakout_day | 3592 | 0.19% | 1.54% | 4.44% | 1.51% |
| breakout_failed | 1186 | -4.18% | -5.0% | -1.15% | -3.14% |
| breakout_held | 2406 | 2.35% | 4.77% | 7.2% | 3.8% |
| confirmed_second_close | 2602 | 0.18% | 1.69% | 4.77% | 1.8% |
| just_under_resistance | 16673 | 0.23% | 0.91% | 2.89% | -0.19% |

"breakout_failed" and "breakout_held" use the next 10 sessions to sort the cases, so they are not tradable signals; they show how much a failure costs.

## 3 · Portfolio simulation (10,000, max 8 positions)

| Variant | CAGR | max drawdown | Sharpe | trades | win rate | avg trade | avg days |
|---|---|---|---|---|---|---|---|
| base_v1_6 | 32.54% | -38.14% | 1.11 | 274 | 31.75% | 5.56% | 29.6 |
| base_v1_5 | 30.47% | -31.95% | 1.08 | 272 | 30.15% | 5.81% | 29.7 |
| no_buy_above_30pct_36d | 25.32% | -29.54% | 0.98 | 275 | 28.73% | 4.09% | 29.5 |
| sell_above_30pct_36d | 10.78% | -26.47% | 0.64 | 343 | 30.9% | 1.52% | 24.0 |
| wait_under_resistance | 34.46% | -31.58% | 1.14 | 297 | 28.28% | 4.98% | 27.5 |
| two_closes_above_resistance | 31.36% | -26.4% | 1.23 | 258 | 34.88% | 6.3% | 31.2 |
| sell_failed_breakout | 32.54% | -38.14% | 1.11 | 274 | 31.75% | 5.56% | 29.6 |
| two_closes_and_sell_failed | 27.08% | -34.56% | 0.98 | 292 | 27.05% | 4.01% | 27.5 |
| wait_res_and_sell_failed | 27.89% | -30.18% | 1.02 | 304 | 31.58% | 5.59% | 26.8 |
| kell_crossback_exit | 18.96% | -27.92% | 0.8 | 663 | 33.79% | 1.34% | 11.8 |
| kell_base_n_break_entry | 10.72% | -17.53% | 0.75 | 217 | 30.41% | 2.06% | 35.3 |
| kell_wedge_pop_entry | 6.63% | -18.94% | 0.49 | 221 | 29.41% | 1.09% | 32.6 |
| kell_full | 10.42% | -24.17% | 0.6 | 520 | 35.38% | 0.92% | 13.4 |
| buffer_200d_1pct | 32.54% | -38.14% | 1.11 | 274 | 31.75% | 5.56% | 29.6 |
| buffer_200d_2pct | 32.54% | -38.14% | 1.11 | 274 | 31.75% | 5.56% | 29.6 |
| buffer_200d_3pct | 28.97% | -33.67% | 1.02 | 290 | 28.28% | 4.18% | 27.5 |
| sell_all_in_correction | 29.07% | -25.21% | 1.08 | 347 | 36.89% | 4.26% | 22.0 |
| sell_all_weak_breadth | 19.26% | -34.65% | 0.77 | 618 | 37.86% | 1.61% | 12.0 |
| sell_all_correction_and_weak_breadth | 28.67% | -28.3% | 1.02 | 330 | 32.73% | 3.86% | 23.8 |
| shorts_in_correction | 37.14% | -35.74% | 1.18 | 412 | 32.28% | 4.33% | 22.6 |
| shorts_always | 15.04% | -35.74% | 0.66 | 566 | 31.1% | 1.36% | 22.8 |
| garch_position_size | 22.29% | -19.21% | 1.3 | 262 | 33.59% | 5.96% | 31.3 |
| ewma_position_size | 21.31% | -21.29% | 1.24 | 254 | 31.89% | 6.88% | 32.0 |
| garch_exposure | 35.58% | -31.14% | 1.21 | 271 | 31.73% | 6.42% | 30.0 |
| ewma_exposure | 29.36% | -33.74% | 1.01 | 285 | 28.42% | 4.6% | 28.3 |
| rebound_sleeve | 24.42% | -25.26% | 0.99 | 535 | 41.5% | 1.98% | 18.7 |
| rebound_sleeve_below_200d | 30.24% | -27.03% | 1.18 | 519 | 44.7% | 2.93% | 19.2 |
| rebound_sleeve_no_stop | 19.64% | -29.88% | 0.85 | 503 | 41.75% | 3.03% | 19.4 |

S&P 500 buy and hold: CAGR 9.06%, max drawdown -25.43%.

## 4 · Separate periods (same variants)

Members enter a period once they have 200 days of prices, so early periods hold fewer stocks.

### 2014-01-02 → 2017-12-29 · 97 stocks · S&P CAGR 9.94%, max drawdown -14.16%

Breakout failure rate 22.41% · 63-day mean: uptrend days 4.57%, just under resistance 4.26%, failed breakouts 0.6% · more than 30% above the 36-day average: n=209, 63-day 13.78%, P(−10% in 21 d) 53.59%

| Variant | CAGR | max drawdown | Sharpe | trades |
|---|---|---|---|---|
| base_v1_6 | 17.87% | -15.06% | 1.15 | 155 |
| base_v1_5 | 18.56% | -15.24% | 1.16 | 156 |
| no_buy_above_30pct_36d | 16.46% | -15.24% | 1.07 | 154 |
| sell_above_30pct_36d | 15.91% | -14.91% | 1.06 | 163 |
| wait_under_resistance | 20.46% | -13.13% | 1.26 | 145 |
| two_closes_above_resistance | 23.2% | -16.13% | 1.38 | 156 |
| sell_failed_breakout | 17.87% | -15.06% | 1.15 | 155 |
| two_closes_and_sell_failed | 20.27% | -14.96% | 1.24 | 161 |
| wait_res_and_sell_failed | 20.7% | -15.71% | 1.26 | 148 |
| kell_crossback_exit | 13.58% | -16.38% | 0.89 | 495 |
| kell_base_n_break_entry | 5.02% | -13.81% | 0.46 | 140 |
| kell_wedge_pop_entry | 7.3% | -18.09% | 0.64 | 171 |
| kell_full | 0.85% | -22.84% | 0.13 | 455 |
| buffer_200d_1pct | 17.87% | -15.06% | 1.15 | 155 |
| buffer_200d_2pct | 17.87% | -15.06% | 1.15 | 155 |
| buffer_200d_3pct | 17.87% | -15.06% | 1.15 | 155 |
| sell_all_in_correction | 15.63% | -13.83% | 1.1 | 213 |
| sell_all_weak_breadth | 17.71% | -15.51% | 1.13 | 159 |
| sell_all_correction_and_weak_breadth | 17.71% | -15.51% | 1.13 | 159 |
| shorts_in_correction | 15.54% | -22.96% | 1.0 | 218 |
| shorts_always | 9.71% | -20.75% | 0.59 | 371 |
| garch_position_size | 14.91% | -17.01% | 1.05 | 161 |
| ewma_position_size | 17.87% | -16.18% | 1.26 | 152 |
| garch_exposure | 19.61% | -16.74% | 1.23 | 140 |
| ewma_exposure | 18.44% | -15.94% | 1.2 | 153 |
| rebound_sleeve | 18.37% | -16.28% | 1.16 | 234 |
| rebound_sleeve_below_200d | 17.77% | -18.67% | 1.1 | 242 |
| rebound_sleeve_no_stop | 19.74% | -21.11% | 1.23 | 243 |

### 2018-01-02 → 2021-12-31 · 114 stocks · S&P CAGR 15.33%, max drawdown -33.92%

Breakout failure rate 30.86% · 63-day mean: uptrend days 5.38%, just under resistance 3.03%, failed breakouts 0.05% · more than 30% above the 36-day average: n=836, 63-day 19.14%, P(−10% in 21 d) 48.8%

| Variant | CAGR | max drawdown | Sharpe | trades |
|---|---|---|---|---|
| base_v1_6 | 36.3% | -20.52% | 1.33 | 217 |
| base_v1_5 | 30.26% | -21.58% | 1.22 | 204 |
| no_buy_above_30pct_36d | 30.45% | -19.82% | 1.23 | 210 |
| sell_above_30pct_36d | 28.14% | -20.24% | 1.29 | 243 |
| wait_under_resistance | 32.23% | -26.67% | 1.23 | 230 |
| two_closes_above_resistance | 31.36% | -21.05% | 1.24 | 216 |
| sell_failed_breakout | 36.3% | -20.52% | 1.33 | 217 |
| two_closes_and_sell_failed | 27.82% | -20.18% | 1.12 | 225 |
| wait_res_and_sell_failed | 32.36% | -31.94% | 1.23 | 240 |
| kell_crossback_exit | 26.34% | -27.5% | 1.08 | 579 |
| kell_base_n_break_entry | 21.9% | -15.13% | 1.31 | 143 |
| kell_wedge_pop_entry | 15.47% | -17.23% | 0.91 | 180 |
| kell_full | 14.64% | -23.12% | 0.78 | 475 |
| buffer_200d_1pct | 35.72% | -19.59% | 1.33 | 217 |
| buffer_200d_2pct | 35.72% | -19.59% | 1.33 | 217 |
| buffer_200d_3pct | 35.72% | -19.59% | 1.33 | 217 |
| sell_all_in_correction | 31.6% | -23.29% | 1.27 | 296 |
| sell_all_weak_breadth | 27.46% | -18.66% | 1.13 | 225 |
| sell_all_correction_and_weak_breadth | 27.46% | -18.66% | 1.13 | 225 |
| shorts_in_correction | 29.04% | -25.92% | 1.15 | 304 |
| shorts_always | 20.12% | -27.89% | 0.8 | 478 |
| garch_position_size | 18.77% | -14.91% | 1.13 | 199 |
| ewma_position_size | 17.8% | -17.79% | 1.04 | 218 |
| garch_exposure | 30.82% | -16.02% | 1.38 | 207 |
| ewma_exposure | 19.36% | -17.25% | 0.97 | 215 |
| rebound_sleeve | 35.91% | -27.28% | 1.37 | 352 |
| rebound_sleeve_below_200d | 30.77% | -32.03% | 1.18 | 339 |
| rebound_sleeve_no_stop | 31.89% | -24.2% | 1.29 | 345 |

### 2022-01-03 → 2026-11-23 · 125 stocks · S&P CAGR 8.78%, max drawdown -25.43%

Breakout failure rate 32.97% · 63-day mean: uptrend days 4.97%, just under resistance 3.05%, failed breakouts -1.02% · more than 30% above the 36-day average: n=1543, 63-day 16.59%, P(−10% in 21 d) 51.65%

| Variant | CAGR | max drawdown | Sharpe | trades |
|---|---|---|---|---|
| base_v1_6 | 31.69% | -33.24% | 1.1 | 273 |
| base_v1_5 | 31.06% | -30.33% | 1.13 | 263 |
| no_buy_above_30pct_36d | 22.4% | -32.5% | 0.91 | 257 |
| sell_above_30pct_36d | 13.69% | -22.87% | 0.73 | 334 |
| wait_under_resistance | 27.96% | -29.59% | 1.02 | 269 |
| two_closes_above_resistance | 20.78% | -27.52% | 0.88 | 265 |
| sell_failed_breakout | 31.69% | -33.24% | 1.1 | 273 |
| two_closes_and_sell_failed | 33.42% | -31.38% | 1.16 | 267 |
| wait_res_and_sell_failed | 20.75% | -31.27% | 0.84 | 295 |
| kell_crossback_exit | 25.93% | -26.01% | 1.01 | 629 |
| kell_base_n_break_entry | 10.92% | -19.66% | 0.78 | 213 |
| kell_wedge_pop_entry | 4.8% | -24.57% | 0.38 | 224 |
| kell_full | 12.13% | -28.49% | 0.68 | 499 |
| buffer_200d_1pct | 31.69% | -33.24% | 1.1 | 273 |
| buffer_200d_2pct | 31.69% | -33.24% | 1.1 | 273 |
| buffer_200d_3pct | 31.69% | -33.24% | 1.1 | 273 |
| sell_all_in_correction | 30.81% | -24.08% | 1.1 | 338 |
| sell_all_weak_breadth | 23.19% | -24.23% | 0.91 | 605 |
| sell_all_correction_and_weak_breadth | 33.6% | -34.73% | 1.13 | 307 |
| shorts_in_correction | 33.52% | -34.9% | 1.11 | 389 |
| shorts_always | 17.22% | -35.46% | 0.69 | 562 |
| garch_position_size | 22.79% | -19.23% | 1.34 | 253 |
| ewma_position_size | 23.36% | -19.42% | 1.35 | 245 |
| garch_exposure | 36.57% | -33.11% | 1.24 | 255 |
| ewma_exposure | 40.74% | -30.23% | 1.33 | 257 |
| rebound_sleeve | 19.11% | -30.16% | 0.88 | 526 |
| rebound_sleeve_below_200d | 28.58% | -26.62% | 1.18 | 501 |
| rebound_sleeve_no_stop | 12.12% | -34.96% | 0.61 | 522 |

### Robustness: windows in which a variant beat base_v1_6 (the current rules)

| Variant | CAGR | max drawdown (less deep) | Sharpe |
|---|---|---|---|
| no_buy_above_30pct_36d | 0/3 | 2/3 | 0/3 |
| sell_above_30pct_36d | 0/3 | 3/3 | 0/3 |
| wait_under_resistance | 1/3 | 2/3 | 1/3 |
| two_closes_above_resistance | 1/3 | 1/3 | 1/3 |
| sell_failed_breakout | 0/3 | 0/3 | 0/3 |
| two_closes_and_sell_failed | 2/3 | 3/3 | 2/3 |
| wait_res_and_sell_failed | 1/3 | 1/3 | 1/3 |
| kell_crossback_exit | 0/3 | 1/3 | 0/3 |
| kell_base_n_break_entry | 0/3 | 3/3 | 0/3 |
| kell_wedge_pop_entry | 0/3 | 2/3 | 0/3 |
| kell_full | 0/3 | 1/3 | 0/3 |
| buffer_200d_1pct | 0/3 | 1/3 | 0/3 |
| buffer_200d_2pct | 0/3 | 1/3 | 0/3 |
| buffer_200d_3pct | 0/3 | 1/3 | 0/3 |
| sell_all_in_correction | 0/3 | 2/3 | 0/3 |
| sell_all_weak_breadth | 0/3 | 2/3 | 0/3 |
| sell_all_correction_and_weak_breadth | 1/3 | 1/3 | 1/3 |
| shorts_in_correction | 1/3 | 0/3 | 1/3 |
| shorts_always | 0/3 | 0/3 | 0/3 |
| garch_position_size | 0/3 | 2/3 | 1/3 |
| ewma_position_size | 0/3 | 2/3 | 2/3 |
| garch_exposure | 2/3 | 2/3 | 3/3 |
| ewma_exposure | 2/3 | 2/3 | 2/3 |
| rebound_sleeve | 1/3 | 1/3 | 2/3 |
| rebound_sleeve_below_200d | 0/3 | 1/3 | 1/3 |
| rebound_sleeve_no_stop | 1/3 | 0/3 | 1/3 |

Symbols: 125 · generated 2026-11-24T12:01+00:00 · price data 7dea579e2f034afa

## Valuation coverage

Positions carry their last observed close on missing dates. No execution at a carried price. Extended gaps and terminal gaps leave delisting proceeds unresolved.

| Variant | Longest gap (sessions) | Missing on final date |
|---|---|---|
| base_v1_6 | 1 | ELE, WKL |
| base_v1_5 | 1 | ELE, WKL |
| no_buy_above_30pct_36d | 1 | ELE, WKL |
| sell_above_30pct_36d | 1 | ELE, WKL |
| wait_under_resistance | 1 | ELE |
| two_closes_above_resistance | 1 | ELE, WKL |
| sell_failed_breakout | 1 | ELE, WKL |
| two_closes_and_sell_failed | 1 | ELE, WKL |
| wait_res_and_sell_failed | 1 | ELE |
| kell_crossback_exit | 1 | None |
| kell_base_n_break_entry | 1 | ELE |
| kell_wedge_pop_entry | 1 | ELE |
| kell_full | 1 | SAN |
| buffer_200d_1pct | 1 | ELE, WKL |
| buffer_200d_2pct | 1 | ELE, WKL |
| buffer_200d_3pct | 1 | ELE, WKL |
| sell_all_in_correction | 1 | None |
| sell_all_weak_breadth | 1 | None |
| sell_all_correction_and_weak_breadth | 1 | None |
| shorts_in_correction | 1 | ELE, WKL |
| shorts_always | 1 | ELE, ENG, WKL |
| garch_position_size | 1 | ELE, WKL |
| ewma_position_size | 1 | ELE, WKL |
| garch_exposure | 1 | ELE, WKL |
| ewma_exposure | 1 | ELE, WKL |
| rebound_sleeve | 1 | ELE, WKL |
| rebound_sleeve_below_200d | 1 | ELE, WKL |
| rebound_sleeve_no_stop | 1 | ELE, ENG, WKL |

## SMA200 buffer divergence: v1.6 versus 1%

Contributions include entry and exit costs, size changes and ending marks on open positions. Subsequent entries describe the portfolio path; an individual replacement is not necessarily causal.

### 2021-11-23 → 2026-11-23

Order plans identical.

Ending equity difference: +0.00; total-return difference +0.00 percentage points. Differing positions: 0.

buffer_200d_2pct vs 1%: order plans identical = True, executed positions identical = True.
buffer_200d_3pct vs 1%: order plans identical = False, executed positions identical = False.

### 2014-01-02 → 2017-12-29

Order plans identical.

Ending equity difference: +0.00; total-return difference +0.00 percentage points. Differing positions: 0.

buffer_200d_2pct vs 1%: order plans identical = True, executed positions identical = True.
buffer_200d_3pct vs 1%: order plans identical = True, executed positions identical = True.

### 2018-01-02 → 2021-12-31

First differing order plan on 2018-10-12 (side, symbol, shares): v1.6 only [('BUY', 'B', 133)], 1% only [].

Ending equity difference: -582.75; total-return difference -5.83 percentage points. Differing positions: 135.

Two largest positive contributions: 24.6% of gross positive contributions. This describes concentration within this historical path.

Largest positive lot: O entered 2018-10-17, +5.939 total-return pp.
Largest positive lot: TSLA entered 2021-11-30, +5.056 total-return pp.

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

### 2022-01-03 → 2026-11-23

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
| base_v1_5 | 3 / 0 / 17 | +0.69 | -3.38 [-7.35, +1.34] | +0.21 [-2.01, +1.92] | -0.17 [-0.39, +0.10] |
| no_buy_above_30pct_36d | 0 / 0 / 20 | -1.41 | -7.81 [-11.82, -0.65] | +0.21 [-2.01, +1.92] | -0.38 [-0.56, -0.03] |
| sell_above_30pct_36d | 1 / 0 / 19 | -1.96 | -3.76 [-8.23, +1.38] | +0.28 [-2.01, +2.05] | -0.19 [-0.41, +0.09] |
| wait_under_resistance | 5 / 0 / 15 | +2.59 | -1.22 [-4.54, +5.43] | +1.07 [-1.30, +6.78] | -0.05 [-0.21, +0.29] |
| two_closes_above_resistance | 12 / 0 / 8 | +5.33 | +0.33 [-4.30, +6.29] | -0.91 [-4.30, +1.17] | -0.01 [-0.23, +0.28] |
| sell_failed_breakout | 0 / 20 / 0 | +0.00 | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] |
| two_closes_and_sell_failed | 7 / 0 / 13 | +2.39 | -0.61 [-6.20, +6.46] | -1.33 [-4.85, +4.75] | -0.04 [-0.33, +0.32] |
| wait_res_and_sell_failed | 10 / 0 / 10 | +2.83 | -0.01 [-4.72, +4.89] | +0.83 [-1.91, +6.78] | +0.01 [-0.27, +0.27] |
| kell_crossback_exit | 0 / 0 / 20 | -4.30 | -8.67 [-17.43, -1.03] | -1.11 [-2.69, +5.06] | -0.44 [-0.91, -0.10] |
| kell_base_n_break_entry | 0 / 0 / 20 | -12.85 | -16.09 [-20.36, -9.43] | +0.89 [-3.85, +4.06] | -0.84 [-1.07, -0.45] |
| kell_wedge_pop_entry | 0 / 0 / 20 | -10.58 | -11.97 [-18.55, -2.74] | -1.46 [-4.06, +3.60] | -0.51 [-0.86, +0.02] |
| kell_full | 0 / 0 / 20 | -17.02 | -16.50 [-20.99, -9.13] | -4.84 [-7.78, +3.03] | -0.86 [-1.20, -0.54] |
| buffer_200d_1pct | 0 / 19 / 1 | +0.00 | +0.00 [-4.96, +0.00] | +0.00 [-0.07, +0.00] | +0.00 [-0.24, +0.00] |
| buffer_200d_2pct | 0 / 19 / 1 | +0.00 | +0.00 [-4.96, +0.00] | +0.00 [-0.07, +0.00] | +0.00 [-0.24, +0.00] |
| buffer_200d_3pct | 0 / 19 / 1 | +0.00 | +0.00 [-4.96, +0.00] | +0.00 [-0.07, +0.00] | +0.00 [-0.24, +0.00] |
| sell_all_in_correction | 0 / 0 / 20 | -2.25 | -4.86 [-8.18, -1.51] | +0.76 [-3.11, +2.53] | -0.21 [-0.40, -0.04] |
| sell_all_weak_breadth | 4 / 0 / 16 | -0.16 | -3.45 [-5.82, +1.80] | +0.00 [-1.80, +2.22] | -0.20 [-0.34, +0.08] |
| sell_all_correction_and_weak_breadth | 4 / 0 / 16 | -0.16 | -3.45 [-5.82, +1.80] | +0.00 [-1.80, +2.22] | -0.20 [-0.34, +0.08] |
| shorts_in_correction | 1 / 0 / 19 | -2.34 | -3.61 [-6.93, +0.37] | -6.78 [-9.06, -4.82] | -0.21 [-0.39, -0.00] |
| shorts_always | 0 / 0 / 20 | -8.16 | -9.64 [-16.10, -1.80] | -4.67 [-7.89, +0.19] | -0.61 [-0.95, -0.25] |
| garch_position_size | 4 / 0 / 16 | -2.96 | -0.81 [-3.16, +7.15] | +2.56 [-1.95, +8.07] | +0.10 [-0.10, +0.49] |
| ewma_position_size | 1 / 0 / 19 | -0.00 | -2.06 [-4.94, +3.96] | +1.84 [-3.71, +4.49] | +0.04 [-0.12, +0.34] |
| garch_exposure | 4 / 0 / 16 | +1.73 | -2.80 [-4.98, +5.64] | +0.17 [-5.05, +4.87] | -0.14 [-0.28, +0.25] |
| ewma_exposure | 5 / 0 / 15 | +0.57 | -1.74 [-3.98, +4.01] | -0.26 [-1.35, +2.16] | -0.06 [-0.17, +0.26] |
| rebound_sleeve | 13 / 0 / 7 | +0.50 | +0.70 [-5.66, +5.45] | -3.34 [-8.39, +2.89] | +0.01 [-0.34, +0.24] |
| rebound_sleeve_below_200d | 11 / 0 / 9 | -0.11 | +0.43 [-5.72, +9.01] | -2.77 [-6.22, +1.59] | -0.03 [-0.33, +0.41] |
| rebound_sleeve_no_stop | 14 / 0 / 6 | +1.87 | +0.88 [-4.36, +8.73] | -2.44 [-6.05, +2.98] | +0.01 [-0.24, +0.36] |

### 2018-01-02 → 2021-12-31

20 paired starts. Counts use unrounded ending equity.

| Variant | W / T / L | Original start ΔCAGR | ΔCAGR | ΔMax DD | ΔSharpe |
|---|---|---:|---|---|---|
| base_v1_5 | 5 / 0 / 15 | -6.04 | -5.55 [-18.54, +8.48] | -1.03 [-4.56, +0.72] | -0.13 [-0.50, +0.24] |
| no_buy_above_30pct_36d | 7 / 0 / 13 | -5.85 | -1.56 [-14.52, +5.37] | +0.67 [-1.93, +2.83] | -0.05 [-0.38, +0.13] |
| sell_above_30pct_36d | 4 / 0 / 16 | -8.16 | -3.55 [-13.79, +5.08] | +0.28 [-2.83, +2.86] | +0.08 [-0.22, +0.32] |
| wait_under_resistance | 8 / 0 / 12 | -4.08 | -1.17 [-16.46, +6.07] | -4.73 [-8.33, +0.48] | -0.07 [-0.45, +0.16] |
| two_closes_above_resistance | 4 / 0 / 16 | -4.94 | -2.82 [-16.56, +5.56] | -0.29 [-4.88, +1.54] | -0.08 [-0.50, +0.16] |
| sell_failed_breakout | 0 / 20 / 0 | +0.00 | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] |
| two_closes_and_sell_failed | 8 / 0 / 12 | -8.48 | -2.09 [-12.39, +7.57] | +1.33 [-1.59, +4.28] | -0.08 [-0.35, +0.22] |
| wait_res_and_sell_failed | 8 / 0 / 12 | -3.94 | -3.33 [-10.76, +8.83] | -7.72 [-14.16, -1.49] | -0.11 [-0.34, +0.23] |
| kell_crossback_exit | 4 / 0 / 16 | -9.96 | -6.95 [-16.24, +3.17] | -1.48 [-6.98, +1.43] | -0.19 [-0.51, +0.09] |
| kell_base_n_break_entry | 0 / 0 / 20 | -14.40 | -14.47 [-28.08, -6.54] | +5.14 [+2.60, +6.12] | -0.11 [-0.45, +0.15] |
| kell_wedge_pop_entry | 0 / 0 / 20 | -20.83 | -12.90 [-24.40, -3.10] | +6.64 [+3.29, +8.02] | -0.14 [-0.47, +0.23] |
| kell_full | 0 / 0 / 20 | -21.66 | -19.32 [-28.67, -11.25] | -1.63 [-4.64, +0.86] | -0.51 [-0.74, -0.27] |
| buffer_200d_1pct | 12 / 0 / 8 | -0.58 | +2.64 [-7.34, +11.44] | -0.22 [-2.91, +2.52] | +0.05 [-0.21, +0.32] |
| buffer_200d_2pct | 13 / 0 / 7 | -0.58 | +2.64 [-7.03, +11.44] | -0.22 [-2.91, +2.75] | +0.08 [-0.21, +0.32] |
| buffer_200d_3pct | 13 / 0 / 7 | -0.58 | +2.64 [-7.03, +11.44] | -0.22 [-2.91, +2.75] | +0.08 [-0.21, +0.32] |
| sell_all_in_correction | 9 / 0 / 11 | -4.70 | -3.03 [-12.77, +7.75] | +1.73 [-3.02, +4.88] | -0.07 [-0.34, +0.25] |
| sell_all_weak_breadth | 11 / 0 / 9 | -8.84 | +0.67 [-9.89, +14.74] | +3.25 [-0.88, +5.75] | +0.04 [-0.24, +0.43] |
| sell_all_correction_and_weak_breadth | 11 / 0 / 9 | -8.84 | +0.67 [-9.89, +14.74] | +3.25 [-0.88, +5.75] | +0.04 [-0.24, +0.43] |
| shorts_in_correction | 10 / 0 / 10 | -7.27 | -0.03 [-15.26, +9.95] | -3.88 [-6.29, -1.68] | -0.06 [-0.45, +0.23] |
| shorts_always | 0 / 0 / 20 | -16.18 | -15.98 [-31.64, -7.38] | -11.73 [-14.15, -6.40] | -0.56 [-1.00, -0.31] |
| garch_position_size | 0 / 0 / 20 | -17.54 | -15.72 [-26.74, -9.98] | +5.49 [+3.15, +7.01] | -0.21 [-0.49, -0.07] |
| ewma_position_size | 0 / 0 / 20 | -18.50 | -15.76 [-25.40, -6.37] | +3.21 [+2.17, +5.67] | -0.21 [-0.44, +0.05] |
| garch_exposure | 3 / 0 / 17 | -5.48 | -4.10 [-18.19, +4.36] | +4.48 [+1.07, +6.70] | +0.03 [-0.41, +0.29] |
| ewma_exposure | 0 / 0 / 20 | -16.95 | -9.76 [-17.95, -0.34] | +3.90 [+1.63, +5.98] | -0.17 [-0.36, +0.10] |
| rebound_sleeve | 13 / 0 / 7 | -0.39 | +3.11 [-7.47, +17.25] | -6.48 [-9.91, -1.54] | +0.04 [-0.25, +0.35] |
| rebound_sleeve_below_200d | 10 / 0 / 10 | -5.53 | +0.34 [-11.26, +9.48] | -6.22 [-11.51, -2.94] | +0.01 [-0.35, +0.28] |
| rebound_sleeve_no_stop | 16 / 0 / 4 | -4.41 | +3.72 [-7.13, +10.58] | -4.22 [-7.75, -0.47] | +0.11 [-0.18, +0.31] |

### 2022-01-03 → 2026-11-23

20 paired starts. Counts use unrounded ending equity.

| Variant | W / T / L | Original start ΔCAGR | ΔCAGR | ΔMax DD | ΔSharpe |
|---|---|---:|---|---|---|
| base_v1_5 | 8 / 0 / 12 | -0.64 | -1.89 [-12.65, +11.17] | +1.83 [-2.24, +5.08] | -0.06 [-0.25, +0.28] |
| no_buy_above_30pct_36d | 5 / 0 / 15 | -9.29 | -8.42 [-27.02, +2.52] | +4.55 [+0.20, +7.09] | -0.16 [-0.63, +0.18] |
| sell_above_30pct_36d | 0 / 0 / 20 | -18.01 | -19.20 [-30.86, -12.89] | +9.53 [-2.67, +11.21] | -0.39 [-0.71, -0.23] |
| wait_under_resistance | 8 / 0 / 12 | -3.74 | -2.91 [-14.91, +9.58] | -0.94 [-5.55, +4.20] | -0.07 [-0.25, +0.15] |
| two_closes_above_resistance | 16 / 0 / 4 | -10.91 | +5.21 [-10.91, +16.23] | +4.25 [-0.80, +6.39] | +0.20 [-0.23, +0.39] |
| sell_failed_breakout | 0 / 20 / 0 | +0.00 | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] |
| two_closes_and_sell_failed | 11 / 0 / 9 | +1.72 | +1.74 [-13.10, +10.15] | +4.42 [-5.21, +6.46] | +0.19 [-0.18, +0.30] |
| wait_res_and_sell_failed | 6 / 0 / 14 | -10.95 | -10.62 [-12.90, +15.48] | +0.57 [-3.24, +3.72] | -0.18 [-0.30, +0.32] |
| kell_crossback_exit | 2 / 0 / 18 | -5.77 | -6.18 [-16.03, +6.62] | +2.47 [-2.52, +7.24] | -0.11 [-0.33, +0.20] |
| kell_base_n_break_entry | 0 / 0 / 20 | -20.78 | -27.69 [-40.59, -12.18] | +11.90 [+8.06, +16.22] | -0.68 [-0.91, -0.11] |
| kell_wedge_pop_entry | 0 / 0 / 20 | -26.89 | -27.17 [-40.03, -17.46] | +7.56 [+2.86, +13.66] | -0.71 [-0.96, -0.41] |
| kell_full | 0 / 0 / 20 | -19.57 | -20.95 [-34.72, -12.85] | +9.34 [+4.49, +11.49] | -0.49 [-0.69, -0.23] |
| buffer_200d_1pct | 0 / 20 / 0 | +0.00 | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] |
| buffer_200d_2pct | 1 / 19 / 0 | +0.00 | +0.00 [+0.00, +4.61] | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.14] |
| buffer_200d_3pct | 1 / 19 / 0 | +0.00 | +0.00 [+0.00, +4.61] | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.14] |
| sell_all_in_correction | 7 / 0 / 13 | -0.88 | -4.81 [-18.73, +5.91] | +3.91 [-0.26, +9.79] | -0.06 [-0.33, +0.25] |
| sell_all_weak_breadth | 5 / 0 / 15 | -8.50 | -12.25 [-22.95, +7.15] | +3.10 [-5.96, +9.01] | -0.28 [-0.51, +0.18] |
| sell_all_correction_and_weak_breadth | 11 / 0 / 9 | +1.90 | +1.19 [-13.31, +17.89] | +3.09 [-3.80, +9.40] | +0.02 [-0.24, +0.39] |
| shorts_in_correction | 9 / 0 / 11 | +1.83 | -1.47 [-16.79, +12.42] | -1.63 [-5.56, +1.51] | -0.04 [-0.39, +0.27] |
| shorts_always | 1 / 0 / 19 | -14.47 | -13.32 [-33.83, +7.42] | -1.18 [-7.17, +2.43] | -0.33 [-0.78, +0.14] |
| garch_position_size | 0 / 0 / 20 | -8.90 | -8.56 [-20.49, -0.16] | +13.37 [+9.53, +14.29] | +0.25 [+0.10, +0.52] |
| ewma_position_size | 2 / 0 / 18 | -8.34 | -9.86 [-20.22, +0.53] | +11.10 [+5.87, +13.82] | +0.24 [-0.08, +0.53] |
| garch_exposure | 18 / 0 / 2 | +4.88 | +4.49 [-6.08, +15.82] | -1.87 [-5.52, +1.80] | +0.10 [-0.10, +0.39] |
| ewma_exposure | 12 / 0 / 8 | +9.04 | +6.20 [-3.47, +12.63] | +0.36 [-6.29, +3.07] | +0.17 [-0.12, +0.27] |
| rebound_sleeve | 5 / 0 / 15 | -12.58 | -12.36 [-21.70, +16.62] | +0.21 [-3.04, +6.38] | -0.14 [-0.48, +0.46] |
| rebound_sleeve_below_200d | 3 / 0 / 17 | -3.12 | -7.94 [-26.05, +11.51] | +3.38 [-1.39, +9.47] | -0.08 [-0.43, +0.32] |
| rebound_sleeve_no_stop | 5 / 0 / 15 | -19.58 | -10.38 [-29.64, +15.97] | +0.47 [-6.08, +9.55] | -0.12 [-0.59, +0.40] |


## Pairs trading (same-sector, Engle-Granger + Ornstein-Uhlenbeck)

Yearly formation on 504 sessions, entry |z|>2, exit |z|<0.5, stop |z|>4, dollar-neutral 5% legs, 0.1% per fill, 2% borrow. Passes only with a positive return and Sharpe ≥ 0.5 in every period.

| Method | Period | Pairs/year | CAGR | Sharpe | Max DD | Trades | Win rate | Corr. S&P |
|---|---|---|---:|---:|---:|---:|---:|---:|
| pairs_static | 2014-01-01 → 2018-01-01 | 7,6,5 | -2.6 | -0.91 | -8.67 | 61 | 34.4 | -0.0 |
| pairs_static | 2018-01-01 → 2022-01-01 | 10,4,6,10 | -2.2 | -0.55 | -11.41 | 115 | 32.2 | 0.08 |
| pairs_static | 2022-01-01 → now | 10,4,8,4,3 | 1.05 | 0.3 | -5.12 | 117 | 41.0 | 0.11 |
| pairs_static | **fails** | | | | | | | |
| pairs_kalman | 2014-01-01 → 2018-01-01 | 7,6,5 | 0.45 | 0.13 | -7.56 | 146 | 46.6 | -0.02 |
| pairs_kalman | 2018-01-01 → 2022-01-01 | 10,4,6,10 | -1.93 | -0.61 | -7.49 | 258 | 46.9 | 0.04 |
| pairs_kalman | 2022-01-01 → now | 10,4,8,4,3 | -0.05 | -0.01 | -7.37 | 203 | 54.2 | -0.01 |
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
| 2022-01-03 → 2026-11-23 | buy_and_hold | — | 9.06% | — | — | — |
| 2022-01-03 → 2026-11-23 | codex_20d_5d_long_short | 0/20 | -9.17% | -20.58 [-25.89, -18.02] | -1.35 | -21.46 |
| 2022-01-03 → 2026-11-23 | codex_20d_5d_long_only | 0/20 | 1.55% | -10.23 [-13.59, -8.60] | -0.50 | +13.57 |
| 2022-01-03 → 2026-11-23 | trend_200d | 0/20 | 8.21% | -3.44 [-6.33, -2.53] | +0.04 | +12.63 |
| 2022-01-03 → 2026-11-23 | codex_intraday_account | 0/20 | -24.30% | -36.06 [-40.34, -33.26] | -4.96 | -50.88 |

Passes: codex_20d_5d_long_short no, codex_20d_5d_long_only no, trend_200d no, codex_intraday_account no


## Buy the oversold dip, sell the rebound

Signal: three red closes and at least 3 ATR under the 21-day EMA. Entry at the signal close, exit at the first close above the 10-day EMA or after 10 sessions; stop 8% (close) unless "no_stop"; 0.1% cost per side. Passes only with at least 30 trades and a positive mean and median excess over the S&P 500 in every period.

| Period | Variant | Trades | Win rate | Mean | Median | Mean vs S&P | Median vs S&P | Worst | 5th pct | Stops |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2014-01-02 → 2017-12-29 | all | 307 | 66% | +1.33% | +2.03% | +0.50% | +0.55% | -24.82% | -10.25% | 12% |
| 2014-01-02 → 2017-12-29 | above_sma200 | 52 | 71% | +1.59% | +2.17% | +0.81% | +1.42% | -9.22% | -8.57% | 8% |
| 2014-01-02 → 2017-12-29 | below_sma200 | 260 | 65% | +1.19% | +1.98% | +0.36% | +0.53% | -24.82% | -10.68% | 13% |
| 2014-01-02 → 2017-12-29 | all_no_stop | 293 | 67% | +1.17% | +2.03% | +0.31% | +0.56% | -33.26% | -11.01% | 0% |
| 2014-01-02 → 2017-12-29 | below_sma200_no_stop | 247 | 66% | +0.98% | +2.01% | +0.12% | +0.53% | -33.26% | -11.54% | 0% |
| 2014-01-02 → 2017-12-29 | at_weekly_sma200 | 8 | 25% | -3.18% | -3.92% | -3.61% | -3.94% | -9.13% | -9.13% | 12% |
| 2014-01-02 → 2017-12-29 | at_weekly_sma200_no_stop | 8 | 25% | -3.06% | -3.92% | -3.36% | -3.94% | -8.13% | -8.13% | 0% |
| 2018-01-02 → 2021-12-31 | all | 417 | 58% | +1.05% | +2.16% | +1.09% | +0.82% | -52.11% | -15.94% | 24% |
| 2018-01-02 → 2021-12-31 | above_sma200 | 68 | 69% | +2.31% | +3.27% | +1.63% | +1.72% | -19.00% | -12.80% | 15% |
| 2018-01-02 → 2021-12-31 | below_sma200 | 355 | 57% | +0.84% | +1.63% | +0.97% | +0.73% | -52.11% | -16.10% | 25% |
| 2018-01-02 → 2021-12-31 | all_no_stop | 385 | 61% | +0.66% | +2.62% | +1.11% | +1.22% | -59.26% | -23.28% | 0% |
| 2018-01-02 → 2021-12-31 | below_sma200_no_stop | 326 | 59% | +0.27% | +2.06% | +0.90% | +1.03% | -59.26% | -23.41% | 0% |
| 2018-01-02 → 2021-12-31 | at_weekly_sma200 | 58 | 62% | -0.51% | +1.55% | +0.32% | +0.50% | -21.38% | -17.25% | 21% |
| 2018-01-02 → 2021-12-31 | at_weekly_sma200_no_stop | 58 | 62% | -1.07% | +1.55% | +0.56% | +0.29% | -36.69% | -21.10% | 0% |
| 2022-01-03 → 2026-11-23 | all | 679 | 60% | +1.18% | +2.02% | +0.36% | +0.70% | -26.68% | -12.34% | 18% |
| 2022-01-03 → 2026-11-23 | above_sma200 | 60 | 53% | +0.45% | +0.55% | -0.82% | -0.18% | -13.90% | -9.59% | 10% |
| 2022-01-03 → 2026-11-23 | below_sma200 | 627 | 61% | +1.26% | +2.18% | +0.46% | +0.78% | -26.68% | -12.36% | 18% |
| 2022-01-03 → 2026-11-23 | all_no_stop | 643 | 63% | +1.60% | +2.29% | +0.67% | +0.98% | -29.38% | -12.26% | 0% |
| 2022-01-03 → 2026-11-23 | below_sma200_no_stop | 593 | 64% | +1.71% | +2.44% | +0.78% | +1.03% | -29.38% | -12.26% | 0% |
| 2022-01-03 → 2026-11-23 | at_weekly_sma200 | 110 | 57% | +0.87% | +1.79% | +0.24% | +0.69% | -12.47% | -10.68% | 17% |
| 2022-01-03 → 2026-11-23 | at_weekly_sma200_no_stop | 110 | 58% | +0.99% | +1.79% | +0.38% | +0.76% | -21.46% | -10.33% | 0% |

Passes: all yes, above_sma200 no, below_sma200 yes, all_no_stop yes, below_sma200_no_stop yes, at_weekly_sma200 no, at_weekly_sma200_no_stop no

NVDA in November 2026 under this rule (with the 8% stop): signal 2026-11-16 at 156.14 (-3.5 ATR) → stop on 2026-11-20, -19.76%

NVDA's 200-week average on 2026-11-23: 123.33.

## Thermometer "Panic · buy": buy the leader

Signal: the thermometer (market_pulse.py, rebuilt without Fear & Greed) closes under 20; one signal per episode (63 sessions apart). Bought at the next close; 0.1% per side. Leader: highest 21/200-day average ratio in the universe on the signal day; top5: the five highest. Today's universe, so stock baskets are flattered by survivorship.

Rebuilt thermometer on 2026-11-23: 29.3.

### First panic close

| Sessions | Signals | Leader mean / median | Top 5 mean / median | Universe mean | S&P 500 mean / median | Leader beats S&P | Leader worst |
|---:|---:|---|---|---:|---|---:|---:|
| 21 | 6 | +4.4% / +5.8% | +5.8% / +3.2% | +5.3% | +4.2% / +5.0% | 3/6 | -15.1% |
| 63 | 6 | +33.7% / +33.1% | +30.8% / +26.5% | +17.5% | +11.7% / +11.5% | 5/6 | -0.6% |
| 126 | 6 | +72.8% / +85.2% | +63.4% / +38.4% | +24.7% | +13.5% / +15.1% | 5/6 | -7.1% |
| 252 | 6 | +138.8% / +73.5% | +72.8% / +49.9% | +40.2% | +21.7% / +25.4% | 4/6 | -6.4% |

Signals: 2015-08-24 (heat 6.4, leader NFLX: 63 sessions +22.9%, S&P +11.5%); 2016-01-15 (heat 18.9, leader NVDA: 63 sessions +33.1%, S&P +11.4%); 2018-12-19 (heat 19.7, leader TTD: 63 sessions +67.9%, S&P +13.2%); 2020-03-09 (heat 8.3, leader TSLA: 63 sessions +45.5%, S&P +11.1%); 2022-03-07 (heat 14.7, leader DVN: 63 sessions +33.1%, S&P -0.4%); 2025-04-04 (heat 5.2, leader BABA: 63 sessions -0.6%, S&P +23.5%); 2026-11-20 (heat 15.8, leader MRNA: 63 sessions —, S&P —)

### First close back above 20

| Sessions | Signals | Leader mean / median | Top 5 mean / median | Universe mean | S&P 500 mean / median | Leader beats S&P | Leader worst |
|---:|---:|---|---|---:|---|---:|---:|
| 21 | 6 | +23.0% / +19.4% | +15.2% / +11.5% | +6.9% | +4.4% / +3.9% | 4/6 | -16.6% |
| 63 | 6 | +44.3% / +29.4% | +52.0% / +29.6% | +16.6% | +10.3% / +13.3% | 5/6 | +5.4% |
| 126 | 6 | +63.5% / +75.8% | +88.4% / +50.3% | +25.5% | +13.6% / +18.6% | 5/6 | -16.6% |
| 252 | 6 | +126.0% / +87.8% | +107.8% / +60.6% | +41.9% | +22.4% / +26.6% | 3/6 | -17.4% |

Signals: 2015-08-27 (heat 30.5, leader NFLX: 63 sessions +6.4%, S&P +4.9%); 2016-01-22 (heat 25.3, leader NVDA: 63 sessions +28.5%, S&P +11.0%); 2019-01-02 (heat 21.8, leader TTD: 63 sessions +80.4%, S&P +17.4%); 2020-04-14 (heat 26.2, leader MRNA: 63 sessions +114.9%, S&P +15.7%); 2022-03-09 (heat 21.2, leader DVN: 63 sessions +30.4%, S&P -5.9%); 2025-04-09 (heat 20.6, leader BABA: 63 sessions +5.4%, S&P +18.8%)

### S&P 500 leaders, point in time

Members on the signal day from the fja05680/sp500 history (including companies that later left the index); leader = highest 21/200-day average ratio among members with 200 sessions of prices. Members without Yahoo prices (mostly delisted later) are counted and left out, so a little survivorship remains.

#### First panic close

| Sessions | Signals | Leader mean / median | Top 5 mean | Top 10 mean | All members mean | S&P 500 mean | Leader beats S&P | Leader worst |
|---:|---:|---|---:|---:|---:|---:|---:|---:|
| 21 | 6 | +9.2% / +2.0% | +7.2% | +5.5% | +3.7% | +4.2% | 3/6 | -0.5% |
| 63 | 6 | +35.8% / +33.1% | +21.1% | +16.7% | +12.1% | +11.7% | 5/6 | +3.7% |
| 126 | 6 | +55.9% / +50.4% | +20.8% | +16.1% | +12.8% | +13.5% | 4/6 | -7.1% |
| 252 | 6 | +75.0% / +44.9% | +31.6% | +27.3% | +26.1% | +21.7% | 4/6 | -6.4% |

Signals: 2015-08-24 (368/500 members priced; leader NFLX, 63 sessions +22.9%; top 5 NFLX, AMZN, UAA, EXPE, REGN); 2016-01-15 (373/504 members priced; leader NVDA, 63 sessions +33.1%; top 5 NVDA, HRL, FSLR, AMZN, TSN); 2018-12-19 (417/505 members priced; leader MKC, 63 sessions +3.7%; top 5 MKC, CHD, LLY, AAP, TRIP); 2020-03-09 (435/505 members priced; leader NVDA, 63 sessions +38.4%; top 5 NVDA, AMD, REGN, DVA, LRCX); 2022-03-07 (457/505 members priced; leader DVN, 63 sessions +33.1%; top 5 DVN, APA, OXY, HAL, COP); 2025-04-04 (485/503 members priced; leader PLTR, 63 sessions +83.5%; top 5 PLTR, TPR, GILD, EQT, VRSN); 2026-11-20 (497/503 members priced; leader MRNA, 63 sessions —; top 5 MRNA, CRL, VEEV, RVTY, CRWD)

#### First close back above 20

| Sessions | Signals | Leader mean / median | Top 5 mean | Top 10 mean | All members mean | S&P 500 mean | Leader beats S&P | Leader worst |
|---:|---:|---|---:|---:|---:|---:|---:|---:|
| 21 | 6 | +5.6% / +7.9% | +5.8% | +4.6% | +4.9% | +4.4% | 3/6 | -16.6% |
| 63 | 6 | +28.0% / +25.9% | +14.9% | +12.9% | +11.8% | +10.3% | 5/6 | +6.4% |
| 126 | 6 | +39.1% / +19.2% | +17.8% | +12.9% | +14.5% | +13.6% | 3/6 | -16.6% |
| 252 | 6 | +54.6% / +11.5% | +26.7% | +18.2% | +28.6% | +22.4% | 2/6 | -17.4% |

Signals: 2015-08-27 (326/500 members priced; leader NFLX, 63 sessions +6.4%; top 5 NFLX, AMZN, UAA, EXPE, MLM); 2016-01-22 (329/505 members priced; leader NVDA, 63 sessions +28.5%; top 5 NVDA, HRL, FSLR, EXR, AMZN); 2019-01-02 (368/505 members priced; leader MKC, 63 sessions +11.3%; top 5 MKC, LLY, MRK, WELL, NRG); 2020-04-14 (384/505 members priced; leader REGN, 63 sessions +23.4%; top 5 REGN, KR, NVDA, NEM, AMD); 2022-03-09 (402/505 members priced; leader DVN, 63 sessions +30.4%; top 5 DVN, OXY, APA, HAL, CF); 2025-04-09 (429/503 members priced; leader PLTR, 63 sessions +68.0%; top 5 PLTR, TPR, GILD, EQT, VRSN)

#### Ten largest S&P 500 members by market cap, cap-weighted (first panic close)

Market cap = close x Yahoo shares outstanding on the day; looked up for the 40 most traded members. This is the rule of the index-leaders paper account (index_leaders.py).

| Sessions | Signals | Top 10 by weight mean / median | S&P 500 mean / median | Beats S&P | Worst |
|---:|---:|---|---|---:|---:|
| 21 | 5 | +5.4% / +4.9% | +4.4% / +6.7% | 3/5 | -2.2% |
| 63 | 5 | +13.7% / +15.5% | +11.7% / +11.4% | 3/5 | -5.7% |
| 126 | 5 | +22.2% / +20.7% | +15.4% / +15.4% | 3/5 | -7.2% |
| 252 | 5 | +30.3% / +39.2% | +22.8% / +30.3% | 4/5 | -15.9% |

Signals: 2016-01-15 (AAPL 15%, GOOGL 14%, GOOG 13%, MSFT 11%, XOM 9%…; 63 sessions +10.4% vs S&P +11.4%; no shares for BKNG); 2018-12-19 (MSFT 15%, AAPL 14%, AMZN 13%, GOOGL 13%, GOOG 13%…; 63 sessions +15.5% vs S&P +13.2%); 2020-03-09 (AAPL 18%, MSFT 17%, AMZN 13%, GOOGL 13%, GOOG 13%…; 63 sessions +16.0% vs S&P +11.1%); 2022-03-07 (AAPL 21%, MSFT 17%, GOOG 13%, GOOGL 13%, AMZN 11%…; 63 sessions -5.7% vs S&P -0.4%); 2025-04-04 (AAPL 17%, MSFT 16%, NVDA 14%, AMZN 11%, GOOG 11%…; 63 sessions +32.5% vs S&P +23.5%); 2026-11-20 (AAPL 19%, MSFT 14%, GOOGL 12%, GOOG 12%, NVDA 12%…; 63 sessions — vs S&P —; no shares for SNDK)

#### Exit rules for the same buy (ten largest by weight)

hold_63 sells after 63 sessions; euphoria at the close after the first thermometer close at or above 80 (however long); euphoria_after_63 likewise, after at least 63 sessions; euphoria_or_252 the euphoria exit within at most 252 sessions (the paper account's rule). Open = no euphoria yet, marked at the last close.

euphoria_stop_basket_10/15 and euphoria_stop_spx_10 add a stop to euphoria_or_252: sold at the close after the basket (or the S&P 500) closes 10%/15% under its value at the buy.

| Exit | Signals | Still open | Stopped | Median sessions held | Mean / median return | S&P 500 same span | Beats S&P | Worst |
|---|---:|---:|---:|---:|---|---:|---:|---:|
| hold_63 | 6 | 1 | 0 | 63 | +11.4% / +12.9% | +10.0% | 3/6 | -5.7% |
| euphoria | 6 | 1 | 0 | 60 | +10.2% / +12.5% | +9.4% | 3/6 | -11.1% |
| euphoria_after_63 | 6 | 1 | 0 | 66 | +13.2% / +14.1% | +11.1% | 3/6 | -11.1% |
| euphoria_or_252 | 6 | 1 | 0 | 60 | +10.2% / +12.5% | +9.4% | 3/6 | -11.1% |
| euphoria_stop_basket_10 | 6 | 1 | 2 | 50 | +7.5% / +4.4% | +6.1% | 3/6 | -7.7% |
| euphoria_stop_basket_15 | 6 | 1 | 2 | 54 | +5.1% / +4.4% | +3.4% | 3/6 | -15.6% |
| euphoria_stop_spx_10 | 6 | 1 | 2 | 54 | +6.1% / +4.4% | +4.9% | 3/6 | -15.6% |

Per signal (euphoria): 2016-01-15 → 2016-04-04 (52 sessions): +8.9% vs S&P +9.8%; 2018-12-19 → 2019-03-22 (62 sessions): +16.0% vs S&P +13.5%; 2020-03-09 → 2020-06-09 (63 sessions): +16.0% vs S&P +11.3%; 2022-03-07 → 2023-02-03 (229 sessions): -11.1% vs S&P -0.8%; 2025-04-04 → 2025-06-30 (57 sessions): +31.3% vs S&P +22.6%; 2026-11-20 → 2026-11-23 (0 sessions, open): -0.2% vs S&P +0.0%

Per signal (euphoria_stop_basket_15): 2016-01-15 → 2016-04-04 (52 sessions): +8.9% vs S&P +9.8%; 2018-12-19 → 2019-03-22 (62 sessions): +16.0% vs S&P +13.5%; 2020-03-09 → 2020-03-24 (10 sessions, stopped): -10.1% vs S&P -15.1%; 2022-03-07 → 2022-06-14 (68 sessions, stopped): -15.6% vs S&P -10.4%; 2025-04-04 → 2025-06-30 (57 sessions): +31.3% vs S&P +22.6%; 2026-11-20 → 2026-11-23 (0 sessions, open): -0.2% vs S&P +0.0%

Per signal (euphoria_stop_spx_10): 2016-01-15 → 2016-04-04 (52 sessions): +8.9% vs S&P +9.8%; 2018-12-19 → 2019-03-22 (62 sessions): +16.0% vs S&P +13.5%; 2020-03-09 → 2020-03-13 (3 sessions, stopped): -3.6% vs S&P -5.9%; 2022-03-07 → 2022-06-14 (68 sessions, stopped): -15.6% vs S&P -10.4%; 2025-04-04 → 2025-06-30 (57 sessions): +31.3% vs S&P +22.6%; 2026-11-20 → 2026-11-23 (0 sessions, open): -0.2% vs S&P +0.0%

#### Buy only at a later close still in panic (the paper account's rule since 23 Nov 2026)

Same ten largest by weight, bought at the first close after the signal with the thermometer still under 20 (the close value stands in for the intraday check 20 minutes earlier); episodes without such a close within 63 sessions buy nothing. Skipped: 2026-11-20.

| Exit | Signals | Mean / median return | S&P 500 same span | Beats S&P | Worst |
|---|---:|---|---:|---:|---:|
| hold_63 | 5 | +13.7% / +15.5% | +12.0% | 3/5 | -5.7% |
| euphoria_or_252 | 5 | +12.2% / +16.0% | +11.3% | 3/5 | -11.1% |

Per signal (euphoria_or_252): bought 2016-01-15 → 2016-04-04: +8.9% vs S&P +9.8%; bought 2018-12-19 → 2019-03-22: +16.0% vs S&P +13.5%; bought 2020-03-09 → 2020-06-09: +16.0% vs S&P +11.3%; bought 2022-03-07 → 2023-02-03: -11.1% vs S&P -0.8%; bought 2025-04-04 → 2025-06-30: +31.3% vs S&P +22.6%
