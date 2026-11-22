# Backtest of the technical rules · 2021-11-20 → 2026-11-20

Technical rules on current members. Historical membership and full label history are unavailable. Survivorship bias may affect strategies differently. Decision on close t, fill at close t+1, 0.10% per fill. Historical technical simulation uses local quote units and excludes FX. Compare variants within this simulation.

## 1 · After a close far above the 36-day average

| Distance to 36-day avg | days | stocks | 21-day mean | 63-day mean | 63-day vs S&P | P(−10% within 21 d) | P(63 d < 0) |
|---|---|---|---|---|---|---|---|
| -100..0% | 68200 | 122 | 1.39% | 4.4% | 1.03% | 25.82% | 46.65% |
| 0..10% | 58261 | 122 | 0.95% | 2.91% | 0.18% | 20.05% | 47.63% |
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
| wait_under_resistance | 29.52% | -30.34% | 1.06 | 285 | 28.77% | 5.11% | 28.2 |
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
| sell_all_weak_breadth | 19.63% | -29.37% | 0.8 | 613 | 39.31% | 1.59% | 12.2 |
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
| sell_above_30pct_36d | 15.34% | -14.91% | 1.02 | 165 |
| wait_under_resistance | 20.46% | -13.13% | 1.26 | 145 |
| two_closes_above_resistance | 23.2% | -16.13% | 1.38 | 156 |
| sell_failed_breakout | 17.87% | -15.06% | 1.15 | 155 |
| two_closes_and_sell_failed | 20.27% | -14.96% | 1.24 | 161 |
| wait_res_and_sell_failed | 20.7% | -15.71% | 1.26 | 148 |
| kell_crossback_exit | 13.32% | -17.45% | 0.87 | 508 |
| kell_base_n_break_entry | 7.23% | -14.28% | 0.63 | 137 |
| kell_wedge_pop_entry | 7.33% | -18.12% | 0.64 | 175 |
| kell_full | 2.09% | -19.76% | 0.23 | 454 |
| buffer_200d_1pct | 17.87% | -15.06% | 1.15 | 155 |
| buffer_200d_2pct | 17.87% | -15.06% | 1.15 | 155 |
| buffer_200d_3pct | 17.87% | -15.06% | 1.15 | 155 |
| sell_all_in_correction | 17.81% | -13.63% | 1.19 | 215 |
| sell_all_weak_breadth | 18.19% | -15.38% | 1.18 | 159 |
| sell_all_correction_and_weak_breadth | 18.19% | -15.38% | 1.18 | 159 |
| shorts_in_correction | 15.54% | -22.96% | 1.0 | 218 |
| shorts_always | 10.29% | -20.7% | 0.62 | 372 |

### 2018-01-02 → 2021-12-31 · 111 stocks · S&P CAGR 15.33%, max drawdown -33.92%

Breakout failure rate 30.94% · 63-day mean: uptrend days 5.49%, just under resistance 3.11%, failed breakouts 0.09% · more than 30% above the 36-day average: n=820, 63-day 19.72%, P(−10% in 21 d) 48.41%

| Variant | CAGR | max drawdown | Sharpe | trades |
|---|---|---|---|---|
| base_v1_6 | 26.05% | -20.09% | 1.07 | 237 |
| base_v1_5 | 33.34% | -21.69% | 1.31 | 203 |
| no_buy_above_30pct_36d | 32.39% | -20.62% | 1.29 | 189 |
| sell_above_30pct_36d | 31.32% | -20.18% | 1.39 | 236 |
| wait_under_resistance | 27.42% | -26.83% | 1.14 | 230 |
| two_closes_above_resistance | 29.85% | -21.86% | 1.2 | 203 |
| sell_failed_breakout | 26.05% | -20.09% | 1.07 | 237 |
| two_closes_and_sell_failed | 28.31% | -21.14% | 1.17 | 221 |
| wait_res_and_sell_failed | 29.28% | -28.01% | 1.15 | 240 |
| kell_crossback_exit | 27.3% | -24.74% | 1.12 | 578 |
| kell_base_n_break_entry | 22.16% | -15.97% | 1.32 | 139 |
| kell_wedge_pop_entry | 14.64% | -17.23% | 0.86 | 185 |
| kell_full | 15.19% | -21.99% | 0.84 | 474 |
| buffer_200d_1pct | 33.61% | -18.78% | 1.33 | 217 |
| buffer_200d_2pct | 33.61% | -18.78% | 1.33 | 217 |
| buffer_200d_3pct | 33.61% | -18.78% | 1.33 | 217 |
| sell_all_in_correction | 31.99% | -23.29% | 1.27 | 296 |
| sell_all_weak_breadth | 29.88% | -19.12% | 1.2 | 233 |
| sell_all_correction_and_weak_breadth | 29.88% | -19.12% | 1.2 | 233 |
| shorts_in_correction | 27.64% | -27.23% | 1.11 | 313 |
| shorts_always | 9.59% | -30.3% | 0.48 | 478 |

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
| no_buy_above_30pct_36d | 1/3 | 1/3 | 2/3 |
| sell_above_30pct_36d | 1/3 | 2/3 | 1/3 |
| wait_under_resistance | 2/3 | 2/3 | 2/3 |
| two_closes_above_resistance | 3/3 | 0/3 | 3/3 |
| sell_failed_breakout | 0/3 | 0/3 | 0/3 |
| two_closes_and_sell_failed | 3/3 | 1/3 | 3/3 |
| wait_res_and_sell_failed | 2/3 | 0/3 | 2/3 |
| kell_crossback_exit | 1/3 | 1/3 | 1/3 |
| kell_base_n_break_entry | 0/3 | 3/3 | 1/3 |
| kell_wedge_pop_entry | 0/3 | 2/3 | 0/3 |
| kell_full | 0/3 | 1/3 | 0/3 |
| buffer_200d_1pct | 1/3 | 1/3 | 1/3 |
| buffer_200d_2pct | 1/3 | 1/3 | 1/3 |
| buffer_200d_3pct | 1/3 | 1/3 | 1/3 |
| sell_all_in_correction | 1/3 | 2/3 | 2/3 |
| sell_all_weak_breadth | 2/3 | 2/3 | 2/3 |
| sell_all_correction_and_weak_breadth | 2/3 | 2/3 | 2/3 |
| shorts_in_correction | 1/3 | 0/3 | 2/3 |
| shorts_always | 0/3 | 0/3 | 0/3 |

Symbols: 122 · generated 2026-11-22T09:46+00:00

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

Ending equity difference: +6606.18; total-return difference +66.06 percentage points. Differing positions: 281.

Two largest positive contributions: 15.5% of gross positive contributions. This describes concentration within this historical path.

Largest positive lot: MRNA entered 2021-07-07, +21.017 total-return pp.
Largest positive lot: AR entered 2020-12-29, +20.589 total-return pp.

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
| base_v1_5 | 3 / 0 / 17 | +0.69 | -3.38 [-7.35, +3.82] | +0.21 [-2.01, +1.92] | -0.18 [-0.39, +0.24] |
| no_buy_above_30pct_36d | 0 / 0 / 20 | -1.41 | -7.70 [-11.82, -0.65] | +0.21 [-2.01, +1.92] | -0.39 [-0.56, -0.03] |
| sell_above_30pct_36d | 1 / 0 / 19 | -2.54 | -3.36 [-8.23, +1.38] | +0.24 [-2.01, +2.05] | -0.15 [-0.41, +0.09] |
| wait_under_resistance | 4 / 0 / 16 | +2.59 | -1.26 [-4.54, +6.06] | +1.07 [-1.30, +6.80] | -0.06 [-0.21, +0.29] |
| two_closes_above_resistance | 11 / 0 / 9 | +5.33 | +0.28 [-4.61, +6.29] | -1.12 [-4.30, +1.17] | -0.01 [-0.23, +0.28] |
| sell_failed_breakout | 0 / 20 / 0 | +0.00 | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] |
| two_closes_and_sell_failed | 6 / 0 / 14 | +2.39 | -0.47 [-6.47, +6.46] | -1.21 [-4.85, +4.75] | -0.04 [-0.33, +0.32] |
| wait_res_and_sell_failed | 10 / 0 / 10 | +2.83 | -0.02 [-4.72, +5.25] | +1.03 [-1.91, +6.80] | +0.01 [-0.27, +0.28] |
| kell_crossback_exit | 0 / 0 / 20 | -4.55 | -9.11 [-16.97, -1.37] | -1.12 [-2.89, +3.11] | -0.48 [-0.87, -0.11] |
| kell_base_n_break_entry | 0 / 0 / 20 | -10.64 | -15.46 [-19.99, -9.48] | +1.04 [-4.09, +3.98] | -0.82 [-1.06, -0.46] |
| kell_wedge_pop_entry | 0 / 0 / 20 | -10.54 | -11.87 [-14.68, -2.74] | -1.47 [-4.03, +3.60] | -0.51 [-0.66, +0.02] |
| kell_full | 0 / 0 / 20 | -15.78 | -18.13 [-23.67, -10.51] | -6.62 [-10.23, -1.35] | -0.98 [-1.34, -0.65] |
| buffer_200d_1pct | 0 / 19 / 1 | +0.00 | +0.00 [-4.96, +0.00] | +0.00 [-0.07, +0.00] | +0.00 [-0.24, +0.00] |
| buffer_200d_2pct | 0 / 19 / 1 | +0.00 | +0.00 [-4.96, +0.00] | +0.00 [-0.07, +0.00] | +0.00 [-0.24, +0.00] |
| buffer_200d_3pct | 0 / 19 / 1 | +0.00 | +0.00 [-4.96, +0.00] | +0.00 [-0.07, +0.00] | +0.00 [-0.24, +0.00] |
| sell_all_in_correction | 0 / 0 / 20 | -0.06 | -5.12 [-8.48, -0.06] | +0.87 [-2.42, +2.72] | -0.22 [-0.42, +0.04] |
| sell_all_weak_breadth | 4 / 0 / 16 | +0.32 | -3.10 [-7.83, +5.08] | +0.12 [-1.67, +2.35] | -0.17 [-0.42, +0.22] |
| sell_all_correction_and_weak_breadth | 4 / 0 / 16 | +0.32 | -3.10 [-7.83, +5.08] | +0.12 [-1.67, +2.35] | -0.17 [-0.42, +0.22] |
| shorts_in_correction | 1 / 0 / 19 | -2.34 | -3.18 [-6.93, +0.37] | -6.78 [-9.06, -4.82] | -0.20 [-0.39, -0.04] |
| shorts_always | 0 / 0 / 20 | -7.59 | -9.19 [-15.52, -1.80] | -4.92 [-8.48, +0.20] | -0.59 [-0.92, -0.25] |

### 2018-01-02 → 2021-12-31

20 paired starts. Counts use unrounded ending equity.

| Variant | W / T / L | Original start ΔCAGR | ΔCAGR | ΔMax DD | ΔSharpe |
|---|---|---:|---|---|---|
| base_v1_5 | 9 / 0 / 11 | +7.30 | -0.81 [-15.33, +7.30] | -0.70 [-4.92, +2.16] | -0.01 [-0.45, +0.24] |
| no_buy_above_30pct_36d | 10 / 0 / 10 | +6.34 | +0.16 [-12.35, +6.34] | -0.29 [-2.91, +2.21] | +0.00 [-0.35, +0.22] |
| sell_above_30pct_36d | 7 / 0 / 13 | +5.27 | -1.28 [-18.11, +5.46] | -1.07 [-4.64, +2.07] | +0.14 [-0.43, +0.32] |
| wait_under_resistance | 4 / 0 / 16 | +1.38 | -2.65 [-12.91, +8.42] | -4.87 [-7.92, -1.06] | -0.07 [-0.40, +0.25] |
| two_closes_above_resistance | 7 / 0 / 13 | +3.80 | -2.02 [-14.34, +6.12] | -0.93 [-6.19, +1.49] | -0.05 [-0.42, +0.20] |
| sell_failed_breakout | 0 / 20 / 0 | +0.00 | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] |
| two_closes_and_sell_failed | 5 / 0 / 15 | +2.26 | -3.41 [-15.55, +5.02] | +0.66 [-3.54, +2.78] | -0.10 [-0.43, +0.14] |
| wait_res_and_sell_failed | 6 / 0 / 14 | +3.24 | -6.87 [-14.61, +7.61] | -7.18 [-17.02, -2.11] | -0.22 [-0.47, +0.21] |
| kell_crossback_exit | 5 / 0 / 15 | +1.26 | -3.30 [-9.64, +6.71] | -1.76 [-8.31, +1.01] | -0.10 [-0.28, +0.18] |
| kell_base_n_break_entry | 0 / 0 / 20 | -3.89 | -15.41 [-23.09, -3.89] | +4.80 [+0.53, +6.62] | -0.11 [-0.39, +0.25] |
| kell_wedge_pop_entry | 0 / 0 / 20 | -11.41 | -12.76 [-21.19, -5.61] | +5.96 [+2.31, +7.72] | -0.12 [-0.41, +0.10] |
| kell_full | 0 / 0 / 20 | -10.86 | -19.28 [-26.79, -10.86] | -2.33 [-6.36, +0.87] | -0.55 [-0.74, -0.23] |
| buffer_200d_1pct | 11 / 0 / 9 | +7.56 | +0.98 [-6.11, +14.22] | +0.15 [-2.76, +2.76] | +0.02 [-0.19, +0.39] |
| buffer_200d_2pct | 11 / 0 / 9 | +7.56 | +1.25 [-6.11, +14.22] | -0.05 [-2.76, +2.76] | +0.03 [-0.19, +0.39] |
| buffer_200d_3pct | 11 / 0 / 9 | +7.56 | +1.25 [-6.11, +14.22] | -0.05 [-2.76, +2.76] | +0.03 [-0.19, +0.39] |
| sell_all_in_correction | 6 / 0 / 14 | +5.94 | -3.30 [-12.82, +6.29] | +1.90 [-3.21, +4.40] | -0.09 [-0.40, +0.21] |
| sell_all_weak_breadth | 12 / 0 / 8 | +3.84 | +1.71 [-5.35, +6.53] | +0.53 [-1.68, +3.72] | +0.06 [-0.16, +0.21] |
| sell_all_correction_and_weak_breadth | 12 / 0 / 8 | +3.84 | +1.71 [-5.35, +6.53] | +0.53 [-1.68, +3.72] | +0.06 [-0.16, +0.21] |
| shorts_in_correction | 9 / 0 / 11 | +1.59 | -2.22 [-10.49, +10.09] | -5.00 [-7.80, -2.53] | -0.10 [-0.34, +0.22] |
| shorts_always | 0 / 0 / 20 | -16.45 | -15.81 [-28.48, -4.33] | -10.65 [-21.09, -7.39] | -0.57 [-0.97, -0.25] |

### 2022-01-03 → 2026-11-20

20 paired starts. Counts use unrounded ending equity.

| Variant | W / T / L | Original start ΔCAGR | ΔCAGR | ΔMax DD | ΔSharpe |
|---|---|---:|---|---|---|
| base_v1_5 | 6 / 0 / 14 | -2.24 | -2.48 [-12.40, +8.77] | +1.14 [-3.57, +5.69] | -0.13 [-0.32, +0.14] |
| no_buy_above_30pct_36d | 1 / 0 / 19 | -1.27 | -6.30 [-22.96, +1.28] | -1.00 [-1.50, +6.43] | -0.24 [-0.55, +0.15] |
| sell_above_30pct_36d | 0 / 0 / 20 | -21.91 | -20.30 [-22.84, -12.82] | +7.17 [-3.59, +10.69] | -0.42 [-0.56, -0.15] |
| wait_under_resistance | 10 / 0 / 10 | -4.48 | +0.37 [-6.37, +13.13] | +3.29 [-4.08, +6.74] | -0.02 [-0.19, +0.31] |
| two_closes_above_resistance | 20 / 0 / 0 | +13.33 | +7.47 [+3.26, +20.94] | +3.55 [-3.16, +7.17] | +0.14 [+0.03, +0.43] |
| sell_failed_breakout | 0 / 20 / 0 | +0.00 | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] |
| two_closes_and_sell_failed | 16 / 0 / 4 | +4.40 | +11.27 [-8.10, +19.45] | -1.43 [-4.41, +4.97] | +0.19 [-0.21, +0.43] |
| wait_res_and_sell_failed | 11 / 0 / 9 | -4.78 | +1.04 [-13.87, +7.63] | -4.25 [-6.27, +4.41] | -0.06 [-0.37, +0.12] |
| kell_crossback_exit | 6 / 0 / 14 | -5.10 | -5.15 [-16.11, +3.29] | +0.58 [-2.89, +5.44] | -0.10 [-0.36, +0.00] |
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
