# Backtest of the technical rules · 2021-11-20 → 2026-11-20

Technical rules on current members. Historical membership and full label history are unavailable. Survivorship bias may affect strategies differently. Decision on close t, fill at close t+1, 0.10% per fill. Historical technical simulation uses local quote units and excludes FX. Compare variants within this simulation.

## 1 · After a close far above the 36-day average

| Distance to 36-day avg | days | stocks | 21-day mean | 63-day mean | 63-day vs S&P | P(−10% within 21 d) | P(63 d < 0) |
|---|---|---|---|---|---|---|---|
| -100..0% | 68203 | 122 | 1.39% | 4.4% | 1.03% | 25.82% | 46.64% |
| 0..10% | 58258 | 122 | 0.95% | 2.91% | 0.18% | 20.05% | 47.64% |
| 10..20% | 11029 | 121 | 1.51% | 5.24% | 2.56% | 29.87% | 47.73% |
| 20..30% | 2262 | 85 | 3.27% | 9.31% | 6.93% | 40.05% | 47.04% |
| 30..+% | 1542 | 52 | 6.16% | 16.56% | 14.24% | 51.69% | 46.3% |

## 2 · Breakouts above the prior 60-session high (in an uptrend) · failure rate 33.21%

| Case | days | 5-day mean | 21-day mean | 63-day mean | 63-day vs S&P |
|---|---|---|---|---|---|
| all_uptrend_days | 56778 | 0.34% | 1.52% | 4.74% | 1.71% |
| breakout_day | 3502 | 0.2% | 1.58% | 4.54% | 1.66% |
| breakout_failed | 1163 | -4.21% | -5.02% | -1.11% | -3.06% |
| breakout_held | 2339 | 2.39% | 4.86% | 7.35% | 4.01% |
| confirmed_second_close | 2536 | 0.17% | 1.73% | 4.86% | 1.92% |
| just_under_resistance | 16234 | 0.23% | 0.93% | 2.94% | -0.08% |

"breakout_failed" and "breakout_held" use the next 10 sessions to sort the cases, so they are not tradable signals; they show how much a failure costs.

## 3 · Portfolio simulation (10,000, max 8 positions)

| Variant | CAGR | max drawdown | Sharpe | trades | win rate | avg trade | avg days |
|---|---|---|---|---|---|---|---|
| base_v1_6 | 19.35% | -33.83% | 0.82 | 280 | 28.93% | 4.37% | 29.2 |
| base_v1_5 | 25.55% | -33.37% | 1.02 | 276 | 30.43% | 4.94% | 29.5 |
| no_buy_above_30pct_36d | 23.7% | -30.82% | 0.96 | 274 | 31.02% | 4.15% | 29.5 |
| sell_above_30pct_36d | 7.83% | -27.25% | 0.49 | 358 | 32.12% | 1.65% | 22.8 |
| wait_under_resistance | 27.74% | -30.34% | 1.02 | 295 | 27.8% | 4.87% | 27.4 |
| two_closes_above_resistance | 20.76% | -27.74% | 0.86 | 275 | 30.91% | 4.06% | 29.7 |
| sell_failed_breakout | 19.35% | -33.83% | 0.82 | 280 | 28.93% | 4.37% | 29.2 |
| two_closes_and_sell_failed | 28.6% | -31.36% | 1.08 | 268 | 31.72% | 5.51% | 30.1 |
| wait_res_and_sell_failed | 30.24% | -36.53% | 1.08 | 324 | 27.47% | 4.84% | 25.4 |
| kell_crossback_exit | 25.41% | -31.0% | 0.99 | 651 | 35.64% | 1.82% | 12.1 |
| kell_base_n_break_entry | 13.32% | -17.37% | 0.91 | 208 | 28.37% | 2.58% | 36.5 |
| kell_wedge_pop_entry | 6.85% | -20.11% | 0.48 | 230 | 27.83% | 0.94% | 31.2 |
| kell_full | 9.99% | -24.81% | 0.57 | 518 | 33.78% | 0.94% | 13.3 |
| buffer_200d_1pct | 19.35% | -33.83% | 0.82 | 280 | 28.93% | 4.37% | 29.2 |
| buffer_200d_2pct | 19.35% | -33.83% | 0.82 | 280 | 28.93% | 4.37% | 29.2 |
| buffer_200d_3pct | 19.35% | -33.83% | 0.82 | 280 | 28.93% | 4.37% | 29.2 |
| sell_all_in_correction | 25.14% | -29.46% | 0.96 | 353 | 36.54% | 4.3% | 21.6 |
| sell_all_weak_breadth | 18.16% | -29.37% | 0.75 | 611 | 38.79% | 1.79% | 12.3 |
| sell_all_correction_and_weak_breadth | 34.18% | -30.4% | 1.14 | 329 | 34.65% | 4.98% | 24.0 |
| shorts_in_correction | 19.18% | -38.11% | 0.77 | 419 | 31.98% | 1.98% | 22.3 |
| shorts_always | 17.6% | -32.95% | 0.69 | 558 | 32.62% | 1.98% | 23.6 |

S&P 500 buy and hold: CAGR 8.1%, max drawdown -25.43%.

## 4 · Separate periods (same variants)

Members enter a period once they have 200 days of prices, so early periods hold fewer stocks.

### 2014-01-02 → 2017-12-29 · 96 stocks · S&P CAGR 9.94%, max drawdown -14.16%

Breakout failure rate 22.48% · 63-day mean: uptrend days 4.59%, just under resistance 4.29%, failed breakouts 0.61% · more than 30% above the 36-day average: n=209, 63-day 13.78%, P(−10% in 21 d) 53.59%

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
| kell_crossback_exit | 13.33% | -17.45% | 0.87 | 508 |
| kell_base_n_break_entry | 7.23% | -14.28% | 0.63 | 137 |
| kell_wedge_pop_entry | 7.33% | -18.12% | 0.64 | 175 |
| kell_full | 0.79% | -24.93% | 0.13 | 462 |
| buffer_200d_1pct | 17.87% | -15.06% | 1.15 | 155 |
| buffer_200d_2pct | 17.87% | -15.06% | 1.15 | 155 |
| buffer_200d_3pct | 17.87% | -15.06% | 1.15 | 155 |
| sell_all_in_correction | 15.74% | -13.63% | 1.1 | 212 |
| sell_all_weak_breadth | 18.19% | -15.38% | 1.18 | 159 |
| sell_all_correction_and_weak_breadth | 18.19% | -15.38% | 1.18 | 159 |
| shorts_in_correction | 15.54% | -22.96% | 1.0 | 218 |
| shorts_always | 9.71% | -20.75% | 0.59 | 371 |

### 2018-01-02 → 2021-12-31 · 111 stocks · S&P CAGR 15.33%, max drawdown -33.92%

Breakout failure rate 30.94% · 63-day mean: uptrend days 5.49%, just under resistance 3.11%, failed breakouts 0.09% · more than 30% above the 36-day average: n=820, 63-day 19.72%, P(−10% in 21 d) 48.41%

| Variant | CAGR | max drawdown | Sharpe | trades |
|---|---|---|---|---|
| base_v1_6 | 36.19% | -20.45% | 1.36 | 219 |
| base_v1_5 | 33.87% | -22.12% | 1.32 | 207 |
| no_buy_above_30pct_36d | 30.37% | -20.27% | 1.23 | 192 |
| sell_above_30pct_36d | 28.55% | -20.18% | 1.3 | 236 |
| wait_under_resistance | 27.13% | -26.67% | 1.08 | 232 |
| two_closes_above_resistance | 27.92% | -21.57% | 1.12 | 207 |
| sell_failed_breakout | 36.19% | -20.45% | 1.36 | 219 |
| two_closes_and_sell_failed | 27.63% | -20.08% | 1.14 | 223 |
| wait_res_and_sell_failed | 22.22% | -28.36% | 0.94 | 251 |
| kell_crossback_exit | 27.3% | -24.74% | 1.12 | 578 |
| kell_base_n_break_entry | 22.16% | -15.97% | 1.32 | 139 |
| kell_wedge_pop_entry | 14.64% | -17.23% | 0.86 | 185 |
| kell_full | 15.19% | -21.99% | 0.84 | 474 |
| buffer_200d_1pct | 29.97% | -18.88% | 1.2 | 218 |
| buffer_200d_2pct | 29.97% | -18.88% | 1.2 | 218 |
| buffer_200d_3pct | 29.97% | -18.88% | 1.2 | 218 |
| sell_all_in_correction | 31.99% | -23.29% | 1.27 | 296 |
| sell_all_weak_breadth | 32.88% | -18.66% | 1.29 | 233 |
| sell_all_correction_and_weak_breadth | 32.88% | -18.66% | 1.29 | 233 |
| shorts_in_correction | 36.65% | -25.83% | 1.32 | 302 |
| shorts_always | 16.98% | -28.72% | 0.71 | 474 |

### 2022-01-03 → 2026-11-20 · 122 stocks · S&P CAGR 7.77%, max drawdown -25.43%

Breakout failure rate 33.12% · 63-day mean: uptrend days 5.06%, just under resistance 3.11%, failed breakouts -0.94% · more than 30% above the 36-day average: n=1540, 63-day 16.62%, P(−10% in 21 d) 51.62%

| Variant | CAGR | max drawdown | Sharpe | trades |
|---|---|---|---|---|
| base_v1_6 | 30.47% | -31.42% | 1.05 | 271 |
| base_v1_5 | 28.23% | -29.81% | 1.06 | 255 |
| no_buy_above_30pct_36d | 29.2% | -29.67% | 1.06 | 276 |
| sell_above_30pct_36d | 8.56% | -27.93% | 0.53 | 356 |
| wait_under_resistance | 25.98% | -28.21% | 0.97 | 269 |
| two_closes_above_resistance | 43.8% | -34.57% | 1.38 | 262 |
| sell_failed_breakout | 30.47% | -31.42% | 1.05 | 271 |
| two_closes_and_sell_failed | 34.87% | -32.02% | 1.17 | 270 |
| wait_res_and_sell_failed | 25.69% | -32.19% | 0.95 | 313 |
| kell_crossback_exit | 25.36% | -26.92% | 1.0 | 622 |
| kell_base_n_break_entry | 11.65% | -17.78% | 0.84 | 203 |
| kell_wedge_pop_entry | 6.45% | -19.75% | 0.47 | 219 |
| kell_full | 11.06% | -25.17% | 0.62 | 497 |
| buffer_200d_1pct | 30.47% | -31.42% | 1.05 | 271 |
| buffer_200d_2pct | 30.47% | -31.42% | 1.05 | 271 |
| buffer_200d_3pct | 30.47% | -31.42% | 1.05 | 271 |
| sell_all_in_correction | 26.86% | -24.14% | 1.01 | 346 |
| sell_all_weak_breadth | 15.34% | -31.15% | 0.69 | 606 |
| sell_all_correction_and_weak_breadth | 27.73% | -31.23% | 1.0 | 317 |
| shorts_in_correction | 29.58% | -34.0% | 1.07 | 395 |
| shorts_always | 25.61% | -31.42% | 0.93 | 516 |

### Robustness: windows in which a variant beat base_v1_6 (the current rules)

| Variant | CAGR | max drawdown (less deep) | Sharpe |
|---|---|---|---|
| no_buy_above_30pct_36d | 0/3 | 2/3 | 1/3 |
| sell_above_30pct_36d | 0/3 | 3/3 | 0/3 |
| wait_under_resistance | 1/3 | 2/3 | 1/3 |
| two_closes_above_resistance | 2/3 | 0/3 | 2/3 |
| sell_failed_breakout | 0/3 | 0/3 | 0/3 |
| two_closes_and_sell_failed | 2/3 | 2/3 | 2/3 |
| wait_res_and_sell_failed | 1/3 | 0/3 | 1/3 |
| kell_crossback_exit | 0/3 | 1/3 | 0/3 |
| kell_base_n_break_entry | 0/3 | 3/3 | 0/3 |
| kell_wedge_pop_entry | 0/3 | 2/3 | 0/3 |
| kell_full | 0/3 | 1/3 | 0/3 |
| buffer_200d_1pct | 0/3 | 1/3 | 0/3 |
| buffer_200d_2pct | 0/3 | 1/3 | 0/3 |
| buffer_200d_3pct | 0/3 | 1/3 | 0/3 |
| sell_all_in_correction | 0/3 | 2/3 | 0/3 |
| sell_all_weak_breadth | 1/3 | 2/3 | 1/3 |
| sell_all_correction_and_weak_breadth | 1/3 | 2/3 | 1/3 |
| shorts_in_correction | 1/3 | 0/3 | 1/3 |
| shorts_always | 0/3 | 0/3 | 0/3 |

Symbols: 122 · generated 2026-11-22T10:32+00:00 · price data 113c206e94116917

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

## SMA200 buffer divergence: v1.6 versus 1%

Contributions include entry and exit costs, size changes and ending marks on open positions. Subsequent entries describe the portfolio path; an individual replacement is not necessarily causal.

### 2021-11-20 → 2026-11-20

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

Ending equity difference: -5849.32; total-return difference -58.49 percentage points. Differing positions: 269.

Two largest positive contributions: 18.6% of gross positive contributions. This describes concentration within this historical path.

Largest positive lot: PHR entered 2020-11-12, +19.788 total-return pp.
Largest positive lot: TTD entered 2020-09-28, +16.568 total-return pp.

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

### 2022-01-03 → 2026-11-20

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
| sell_above_30pct_36d | 1 / 0 / 19 | -1.96 | -3.27 [-8.23, +1.38] | +0.24 [-2.01, +2.05] | -0.14 [-0.41, +0.09] |
| wait_under_resistance | 5 / 0 / 15 | +2.59 | -1.24 [-4.54, +5.43] | +1.07 [-1.30, +6.78] | -0.05 [-0.21, +0.29] |
| two_closes_above_resistance | 12 / 0 / 8 | +5.33 | +0.33 [-4.30, +6.29] | -0.91 [-4.30, +1.17] | -0.01 [-0.23, +0.28] |
| sell_failed_breakout | 0 / 20 / 0 | +0.00 | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] |
| two_closes_and_sell_failed | 7 / 0 / 13 | +2.39 | -0.62 [-6.20, +6.46] | -1.41 [-4.85, +4.75] | -0.03 [-0.33, +0.32] |
| wait_res_and_sell_failed | 10 / 0 / 10 | +2.83 | -0.01 [-4.72, +4.89] | +0.83 [-1.91, +6.78] | +0.01 [-0.27, +0.27] |
| kell_crossback_exit | 0 / 0 / 20 | -4.55 | -8.97 [-15.32, -1.32] | -1.18 [-2.38, +3.11] | -0.46 [-0.78, -0.11] |
| kell_base_n_break_entry | 0 / 0 / 20 | -10.64 | -15.50 [-19.99, -9.48] | +1.04 [-4.08, +3.98] | -0.82 [-1.06, -0.46] |
| kell_wedge_pop_entry | 0 / 0 / 20 | -10.54 | -11.19 [-14.68, -2.74] | -1.47 [-4.58, +3.60] | -0.51 [-0.65, +0.02] |
| kell_full | 0 / 0 / 20 | -17.08 | -17.30 [-23.67, -10.81] | -6.65 [-9.87, -1.38] | -0.99 [-1.34, -0.68] |
| buffer_200d_1pct | 0 / 19 / 1 | +0.00 | +0.00 [-4.96, +0.00] | +0.00 [-0.07, +0.00] | +0.00 [-0.24, +0.00] |
| buffer_200d_2pct | 0 / 19 / 1 | +0.00 | +0.00 [-4.96, +0.00] | +0.00 [-0.07, +0.00] | +0.00 [-0.24, +0.00] |
| buffer_200d_3pct | 0 / 19 / 1 | +0.00 | +0.00 [-4.96, +0.00] | +0.00 [-0.07, +0.00] | +0.00 [-0.24, +0.00] |
| sell_all_in_correction | 1 / 0 / 19 | -2.14 | -5.11 [-8.84, +1.23] | +0.88 [-2.97, +2.73] | -0.22 [-0.41, +0.10] |
| sell_all_weak_breadth | 4 / 0 / 16 | +0.32 | -2.99 [-7.83, +5.08] | +0.12 [-1.67, +2.35] | -0.15 [-0.42, +0.22] |
| sell_all_correction_and_weak_breadth | 4 / 0 / 16 | +0.32 | -2.99 [-7.83, +5.08] | +0.12 [-1.67, +2.35] | -0.15 [-0.42, +0.22] |
| shorts_in_correction | 0 / 0 / 20 | -2.34 | -3.61 [-6.93, -0.04] | -6.78 [-9.06, -4.82] | -0.21 [-0.39, -0.00] |
| shorts_always | 0 / 0 / 20 | -8.16 | -9.64 [-16.10, -1.80] | -4.86 [-7.89, +0.19] | -0.61 [-0.95, -0.25] |

### 2018-01-02 → 2021-12-31

20 paired starts. Counts use unrounded ending equity.

| Variant | W / T / L | Original start ΔCAGR | ΔCAGR | ΔMax DD | ΔSharpe |
|---|---|---:|---|---|---|
| base_v1_5 | 7 / 0 / 13 | -2.32 | -2.46 [-13.62, +8.39] | -0.99 [-5.06, +1.02] | -0.06 [-0.40, +0.24] |
| no_buy_above_30pct_36d | 7 / 0 / 13 | -5.82 | -2.96 [-9.75, +10.94] | +1.06 [-3.08, +2.62] | -0.08 [-0.30, +0.32] |
| sell_above_30pct_36d | 6 / 0 / 14 | -7.64 | -3.79 [-11.06, +4.07] | -0.40 [-4.93, +3.03] | +0.09 [-0.19, +0.32] |
| wait_under_resistance | 7 / 0 / 13 | -9.06 | -1.64 [-10.02, +7.05] | -4.47 [-8.22, +1.40] | -0.07 [-0.28, +0.19] |
| two_closes_above_resistance | 5 / 0 / 15 | -8.28 | -3.01 [-13.65, +6.27] | -0.31 [-6.70, +1.38] | -0.08 [-0.40, +0.17] |
| sell_failed_breakout | 0 / 20 / 0 | +0.00 | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] |
| two_closes_and_sell_failed | 7 / 0 / 13 | -8.56 | -2.30 [-15.42, +9.45] | +1.53 [-2.75, +3.30] | -0.06 [-0.45, +0.29] |
| wait_res_and_sell_failed | 4 / 0 / 16 | -13.97 | -5.47 [-13.97, +2.95] | -5.47 [-15.90, -1.49] | -0.18 [-0.43, +0.10] |
| kell_crossback_exit | 5 / 0 / 15 | -8.89 | -3.98 [-16.97, +6.55] | -1.13 [-8.61, +0.76] | -0.12 [-0.48, +0.19] |
| kell_base_n_break_entry | 0 / 0 / 20 | -14.03 | -16.72 [-23.67, -8.24] | +5.17 [+0.23, +7.58] | -0.14 [-0.40, +0.11] |
| kell_wedge_pop_entry | 0 / 0 / 20 | -21.56 | -13.95 [-21.56, -7.01] | +6.54 [+2.01, +7.86] | -0.15 [-0.50, +0.06] |
| kell_full | 0 / 0 / 20 | -21.01 | -20.04 [-27.81, -12.27] | -2.09 [-6.66, +2.08] | -0.52 [-0.77, -0.27] |
| buffer_200d_1pct | 12 / 0 / 8 | -6.22 | +1.06 [-9.20, +8.20] | +1.12 [-3.80, +2.64] | +0.05 [-0.22, +0.25] |
| buffer_200d_2pct | 13 / 0 / 7 | -6.22 | +1.48 [-6.22, +8.20] | +1.19 [-3.80, +2.64] | +0.06 [-0.17, +0.25] |
| buffer_200d_3pct | 13 / 0 / 7 | -6.22 | +1.48 [-6.22, +8.20] | +1.19 [-3.80, +2.64] | +0.06 [-0.17, +0.25] |
| sell_all_in_correction | 5 / 0 / 15 | -4.21 | -4.83 [-12.51, +9.54] | +2.41 [-2.95, +4.12] | -0.11 [-0.35, +0.24] |
| sell_all_weak_breadth | 12 / 0 / 8 | -3.31 | +2.14 [-8.76, +9.73] | +2.75 [-0.89, +5.56] | +0.09 [-0.22, +0.31] |
| sell_all_correction_and_weak_breadth | 12 / 0 / 8 | -3.31 | +2.14 [-8.76, +9.73] | +2.75 [-0.89, +5.56] | +0.09 [-0.22, +0.31] |
| shorts_in_correction | 10 / 0 / 10 | +0.46 | -0.42 [-11.25, +13.13] | -3.99 [-7.18, -0.44] | -0.05 [-0.32, +0.30] |
| shorts_always | 0 / 0 / 20 | -19.21 | -14.40 [-22.18, -4.96] | -9.12 [-18.81, -6.61] | -0.53 [-0.78, -0.26] |

### 2022-01-03 → 2026-11-20

20 paired starts. Counts use unrounded ending equity.

| Variant | W / T / L | Original start ΔCAGR | ΔCAGR | ΔMax DD | ΔSharpe |
|---|---|---:|---|---|---|
| base_v1_5 | 6 / 0 / 14 | -2.24 | -2.47 [-12.40, +8.77] | +1.14 [-3.57, +5.69] | -0.13 [-0.32, +0.14] |
| no_buy_above_30pct_36d | 1 / 0 / 19 | -1.27 | -6.30 [-22.96, +1.28] | -1.00 [-1.50, +6.43] | -0.24 [-0.55, +0.15] |
| sell_above_30pct_36d | 0 / 0 / 20 | -21.91 | -20.30 [-22.84, -12.82] | +7.17 [-3.59, +10.69] | -0.42 [-0.56, -0.15] |
| wait_under_resistance | 10 / 0 / 10 | -4.48 | +0.37 [-6.37, +13.13] | +3.29 [-4.08, +6.74] | -0.02 [-0.19, +0.31] |
| two_closes_above_resistance | 20 / 0 / 0 | +13.33 | +7.47 [+3.26, +20.94] | +3.55 [-3.16, +7.17] | +0.14 [+0.03, +0.43] |
| sell_failed_breakout | 0 / 20 / 0 | +0.00 | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] |
| two_closes_and_sell_failed | 15 / 0 / 5 | +4.40 | +11.27 [-8.10, +19.45] | -1.43 [-4.41, +4.97] | +0.19 [-0.21, +0.43] |
| wait_res_and_sell_failed | 11 / 0 / 9 | -4.78 | +1.04 [-13.87, +7.63] | -4.25 [-6.27, +4.41] | -0.06 [-0.37, +0.12] |
| kell_crossback_exit | 6 / 0 / 14 | -5.10 | -5.15 [-12.79, +3.29] | +0.31 [-2.89, +5.71] | -0.10 [-0.26, +0.00] |
| kell_base_n_break_entry | 0 / 0 / 20 | -18.82 | -21.83 [-27.92, -13.41] | +15.53 [+11.02, +18.39] | -0.38 [-0.49, -0.08] |
| kell_wedge_pop_entry | 0 / 0 / 20 | -24.02 | -27.82 [-34.34, -20.66] | +9.82 [+6.18, +18.04] | -0.71 [-0.87, -0.47] |
| kell_full | 0 / 0 / 20 | -19.41 | -19.34 [-26.89, -10.29] | +9.20 [+4.51, +13.76] | -0.43 [-0.79, -0.20] |
| buffer_200d_1pct | 0 / 20 / 0 | +0.00 | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] |
| buffer_200d_2pct | 0 / 20 / 0 | +0.00 | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] |
| buffer_200d_3pct | 0 / 20 / 0 | +0.00 | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] |
| sell_all_in_correction | 15 / 0 / 5 | -3.61 | +7.66 [-4.47, +12.51] | +7.23 [+1.35, +9.99] | +0.14 [-0.17, +0.34] |
| sell_all_weak_breadth | 0 / 0 / 20 | -15.13 | -15.29 [-21.49, -4.08] | -3.12 [-4.93, +0.27] | -0.40 [-0.56, -0.14] |
| sell_all_correction_and_weak_breadth | 2 / 0 / 18 | -2.74 | -6.10 [-17.36, +4.43] | -2.87 [-5.15, +0.45] | -0.20 [-0.36, +0.07] |
| shorts_in_correction | 7 / 0 / 13 | -0.89 | -2.46 [-16.69, +6.48] | -1.88 [-4.55, +0.59] | -0.10 [-0.43, +0.09] |
| shorts_always | 2 / 0 / 18 | -4.86 | -10.20 [-23.17, +2.03] | -2.83 [-7.57, +1.71] | -0.35 [-0.61, -0.01] |


## Pairs trading (same-sector, Engle-Granger + Ornstein-Uhlenbeck)

Yearly formation on 504 sessions, entry |z|>2, exit |z|<0.5, stop |z|>4, dollar-neutral 5% legs, 0.1% per fill, 2% borrow. Passes only with a positive return and Sharpe ≥ 0.5 in every period.

| Method | Period | Pairs/year | CAGR | Sharpe | Max DD | Trades | Win rate | Corr. S&P |
|---|---|---|---:|---:|---:|---:|---:|---:|
| pairs_static | 2014-01-01 → 2018-01-01 | 7,6,4 | -2.92 | -1.03 | -9.31 | 59 | 32.2 | -0.0 |
| pairs_static | 2018-01-01 → 2022-01-01 | 9,4,6,10 | -2.51 | -0.64 | -12.3 | 111 | 30.6 | 0.08 |
| pairs_static | 2022-01-01 → now | 9,4,8,4,2 | 0.61 | 0.19 | -5.77 | 108 | 38.9 | 0.09 |
| pairs_static | **fails** | | | | | | | |
| pairs_kalman | 2014-01-01 → 2018-01-01 | 7,6,4 | 0.47 | 0.14 | -7.56 | 141 | 46.1 | -0.02 |
| pairs_kalman | 2018-01-01 → 2022-01-01 | 9,4,6,10 | -1.77 | -0.56 | -6.87 | 244 | 47.5 | 0.04 |
| pairs_kalman | 2022-01-01 → now | 9,4,8,4,2 | -0.57 | -0.2 | -7.1 | 192 | 54.2 | -0.05 |
| pairs_kalman | **fails** | | | | | | | |
