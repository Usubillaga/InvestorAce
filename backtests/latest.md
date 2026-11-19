# Backtest of the technical rules · 2021-11-18 → 2026-11-18

Technical rules on current members. Historical membership and full label history are unavailable. Survivorship bias may affect strategies differently. Decision on close t, fill at close t+1, 0.10% per fill. Historical technical simulation uses local quote units and excludes FX. Compare variants within this simulation.

## 1 · After a close far above the 36-day average

| Distance to 36-day avg | days | stocks | 21-day mean | 63-day mean | 63-day vs S&P | P(−10% within 21 d) | P(63 d < 0) |
|---|---|---|---|---|---|---|---|
| -100..0% | 66982 | 120 | 1.33% | 4.36% | 0.98% | 25.67% | 46.7% |
| 0..10% | 57478 | 120 | 0.98% | 2.94% | 0.23% | 19.8% | 47.52% |
| 10..20% | 10741 | 119 | 1.56% | 5.29% | 2.61% | 29.93% | 47.84% |
| 20..30% | 2187 | 82 | 3.46% | 9.54% | 7.13% | 40.19% | 47.05% |
| 30..+% | 1500 | 50 | 6.4% | 17.0% | 14.55% | 51.6% | 46.2% |

## 2 · Breakouts above the prior 60-session high (in an uptrend) · failure rate 33.06%

| Case | days | 5-day mean | 21-day mean | 63-day mean | 63-day vs S&P |
|---|---|---|---|---|---|
| all_uptrend_days | 55890 | 0.35% | 1.54% | 4.76% | 1.76% |
| breakout_day | 3448 | 0.21% | 1.63% | 4.61% | 1.73% |
| breakout_failed | 1140 | -4.17% | -4.98% | -1.07% | -3.04% |
| breakout_held | 2308 | 2.38% | 4.9% | 7.41% | 4.09% |
| confirmed_second_close | 2506 | 0.2% | 1.78% | 4.93% | 2.0% |
| just_under_resistance | 16048 | 0.23% | 0.95% | 2.99% | 0.02% |

"breakout_failed" and "breakout_held" use the next 10 sessions to sort the cases, so they are not tradable signals; they show how much a failure costs.

## 3 · Portfolio simulation (10,000, max 8 positions)

| Variant | CAGR | max drawdown | Sharpe | trades | win rate | avg trade | avg days |
|---|---|---|---|---|---|---|---|
| base_v1_6 | 30.16% | -30.24% | 1.07 | 295 | 29.49% | 5.15% | 27.6 |
| base_v1_5 | 28.33% | -29.9% | 1.01 | 273 | 30.4% | 5.49% | 30.3 |
| no_buy_above_30pct_36d | 17.93% | -25.63% | 0.84 | 267 | 29.59% | 3.23% | 30.9 |
| sell_above_30pct_36d | 11.73% | -25.12% | 0.63 | 345 | 31.88% | 1.97% | 23.8 |
| wait_under_resistance | 30.67% | -27.58% | 1.07 | 294 | 26.53% | 4.59% | 27.5 |
| two_closes_above_resistance | 31.13% | -29.67% | 1.13 | 277 | 31.77% | 5.52% | 28.9 |
| sell_failed_breakout | 30.16% | -30.24% | 1.07 | 295 | 29.49% | 5.15% | 27.6 |
| two_closes_and_sell_failed | 30.86% | -31.4% | 1.09 | 279 | 30.11% | 5.55% | 29.2 |
| wait_res_and_sell_failed | 19.13% | -34.29% | 0.8 | 325 | 26.77% | 4.36% | 24.6 |
| kell_crossback_exit | 28.53% | -28.84% | 1.01 | 641 | 34.48% | 1.79% | 12.3 |
| kell_base_n_break_entry | 10.51% | -17.55% | 0.76 | 208 | 27.88% | 2.2% | 36.9 |
| kell_wedge_pop_entry | 7.17% | -18.11% | 0.52 | 225 | 28.0% | 1.27% | 32.6 |
| kell_full | 11.11% | -22.92% | 0.62 | 524 | 32.25% | 0.78% | 13.0 |
| buffer_200d_1pct | 30.16% | -30.24% | 1.07 | 295 | 29.49% | 5.15% | 27.6 |
| buffer_200d_2pct | 30.16% | -30.24% | 1.07 | 295 | 29.49% | 5.15% | 27.6 |
| buffer_200d_3pct | 30.16% | -30.24% | 1.07 | 295 | 29.49% | 5.15% | 27.6 |
| sell_all_in_correction | 27.26% | -27.09% | 0.98 | 365 | 33.7% | 3.42% | 21.0 |
| sell_all_weak_breadth | 12.42% | -33.4% | 0.58 | 621 | 38.81% | 1.19% | 12.0 |
| sell_all_correction_and_weak_breadth | 21.65% | -30.37% | 0.84 | 347 | 32.28% | 3.5% | 22.7 |

S&P 500 buy and hold: CAGR 9.26%, max drawdown -25.43%.

## 4 · Separate periods (same variants)

Members enter a period once they have 200 days of prices, so early periods hold fewer stocks.

### 2014-01-02 → 2017-12-29 · 95 stocks · S&P CAGR 9.94%, max drawdown -14.16%

Breakout failure rate 22.57% · 63-day mean: uptrend days 4.54%, just under resistance 4.25%, failed breakouts 0.48% · more than 30% above the 36-day average: n=209, 63-day 13.78%, P(−10% in 21 d) 53.59%

| Variant | CAGR | max drawdown | Sharpe | trades |
|---|---|---|---|---|
| base_v1_6 | 20.36% | -15.06% | 1.3 | 150 |
| base_v1_5 | 18.67% | -15.24% | 1.18 | 153 |
| no_buy_above_30pct_36d | 16.64% | -15.24% | 1.08 | 154 |
| sell_above_30pct_36d | 17.59% | -14.94% | 1.16 | 163 |
| wait_under_resistance | 19.23% | -14.03% | 1.2 | 143 |
| two_closes_above_resistance | 22.69% | -16.57% | 1.37 | 150 |
| sell_failed_breakout | 20.36% | -15.06% | 1.3 | 150 |
| two_closes_and_sell_failed | 16.12% | -16.52% | 1.05 | 154 |
| wait_res_and_sell_failed | 20.22% | -15.48% | 1.24 | 155 |
| kell_crossback_exit | 10.37% | -16.24% | 0.72 | 508 |
| kell_base_n_break_entry | 1.71% | -20.82% | 0.2 | 148 |
| kell_wedge_pop_entry | 5.78% | -20.75% | 0.53 | 174 |
| kell_full | 1.5% | -17.77% | 0.18 | 460 |
| buffer_200d_1pct | 20.36% | -15.06% | 1.3 | 150 |
| buffer_200d_2pct | 20.36% | -15.06% | 1.3 | 150 |
| buffer_200d_3pct | 20.36% | -15.06% | 1.3 | 150 |
| sell_all_in_correction | 17.74% | -13.62% | 1.21 | 215 |
| sell_all_weak_breadth | 20.54% | -15.38% | 1.3 | 153 |
| sell_all_correction_and_weak_breadth | 20.54% | -15.38% | 1.3 | 153 |

### 2018-01-02 → 2021-12-31 · 109 stocks · S&P CAGR 15.33%, max drawdown -33.92%

Breakout failure rate 30.91% · 63-day mean: uptrend days 5.38%, just under resistance 3.07%, failed breakouts 0.23% · more than 30% above the 36-day average: n=767, 63-day 18.9%, P(−10% in 21 d) 50.33%

| Variant | CAGR | max drawdown | Sharpe | trades |
|---|---|---|---|---|
| base_v1_6 | 35.07% | -23.27% | 1.39 | 214 |
| base_v1_5 | 35.71% | -21.38% | 1.43 | 198 |
| no_buy_above_30pct_36d | 39.97% | -20.94% | 1.51 | 189 |
| sell_above_30pct_36d | 34.78% | -19.98% | 1.56 | 231 |
| wait_under_resistance | 33.97% | -22.96% | 1.39 | 224 |
| two_closes_above_resistance | 32.0% | -24.33% | 1.35 | 202 |
| sell_failed_breakout | 35.07% | -23.27% | 1.39 | 214 |
| two_closes_and_sell_failed | 30.13% | -22.78% | 1.27 | 208 |
| wait_res_and_sell_failed | 30.16% | -25.73% | 1.25 | 222 |
| kell_crossback_exit | 22.42% | -22.95% | 0.98 | 573 |
| kell_base_n_break_entry | 22.16% | -15.97% | 1.32 | 139 |
| kell_wedge_pop_entry | 14.59% | -17.23% | 0.7 | 191 |
| kell_full | 15.49% | -21.32% | 0.85 | 473 |
| buffer_200d_1pct | 36.64% | -21.7% | 1.43 | 220 |
| buffer_200d_2pct | 36.64% | -21.7% | 1.43 | 220 |
| buffer_200d_3pct | 36.64% | -21.7% | 1.43 | 220 |
| sell_all_in_correction | 33.57% | -22.01% | 1.33 | 305 |
| sell_all_weak_breadth | 26.46% | -20.31% | 1.12 | 221 |
| sell_all_correction_and_weak_breadth | 26.46% | -20.31% | 1.12 | 221 |

### 2022-01-03 → 2026-11-18 · 120 stocks · S&P CAGR 9.07%, max drawdown -25.43%

Breakout failure rate 32.92% · 63-day mean: uptrend days 5.13%, just under resistance 3.2%, failed breakouts -0.83% · more than 30% above the 36-day average: n=1495, 63-day 17.16%, P(−10% in 21 d) 51.44%

| Variant | CAGR | max drawdown | Sharpe | trades |
|---|---|---|---|---|
| base_v1_6 | 27.49% | -29.9% | 1.04 | 269 |
| base_v1_5 | 29.09% | -30.06% | 1.06 | 264 |
| no_buy_above_30pct_36d | 22.65% | -33.81% | 0.94 | 258 |
| sell_above_30pct_36d | 15.67% | -23.23% | 0.83 | 331 |
| wait_under_resistance | 30.8% | -29.24% | 1.1 | 277 |
| two_closes_above_resistance | 34.63% | -32.23% | 1.17 | 259 |
| sell_failed_breakout | 27.49% | -29.9% | 1.04 | 269 |
| two_closes_and_sell_failed | 29.22% | -33.18% | 1.06 | 258 |
| wait_res_and_sell_failed | 29.23% | -32.71% | 1.04 | 297 |
| kell_crossback_exit | 26.72% | -32.09% | 1.02 | 615 |
| kell_base_n_break_entry | 12.35% | -15.93% | 0.85 | 214 |
| kell_wedge_pop_entry | 6.6% | -19.75% | 0.48 | 219 |
| kell_full | 9.65% | -23.72% | 0.56 | 502 |
| buffer_200d_1pct | 27.49% | -29.9% | 1.04 | 269 |
| buffer_200d_2pct | 27.49% | -29.9% | 1.04 | 269 |
| buffer_200d_3pct | 27.49% | -29.9% | 1.04 | 269 |
| sell_all_in_correction | 29.27% | -29.57% | 1.03 | 341 |
| sell_all_weak_breadth | 9.98% | -32.61% | 0.54 | 598 |
| sell_all_correction_and_weak_breadth | 24.51% | -29.94% | 0.95 | 324 |

### Robustness: windows in which a variant beat base_v1_6 (the current rules)

| Variant | CAGR | max drawdown (less deep) | Sharpe |
|---|---|---|---|
| no_buy_above_30pct_36d | 1/3 | 1/3 | 1/3 |
| sell_above_30pct_36d | 0/3 | 3/3 | 1/3 |
| wait_under_resistance | 1/3 | 3/3 | 1/3 |
| two_closes_above_resistance | 2/3 | 0/3 | 2/3 |
| sell_failed_breakout | 0/3 | 0/3 | 0/3 |
| two_closes_and_sell_failed | 1/3 | 1/3 | 1/3 |
| wait_res_and_sell_failed | 1/3 | 0/3 | 0/3 |
| kell_crossback_exit | 0/3 | 1/3 | 0/3 |
| kell_base_n_break_entry | 0/3 | 2/3 | 0/3 |
| kell_wedge_pop_entry | 0/3 | 2/3 | 0/3 |
| kell_full | 0/3 | 2/3 | 0/3 |
| buffer_200d_1pct | 1/3 | 1/3 | 1/3 |
| buffer_200d_2pct | 1/3 | 1/3 | 1/3 |
| buffer_200d_3pct | 1/3 | 1/3 | 1/3 |
| sell_all_in_correction | 1/3 | 3/3 | 0/3 |
| sell_all_weak_breadth | 1/3 | 1/3 | 0/3 |
| sell_all_correction_and_weak_breadth | 1/3 | 1/3 | 0/3 |

Symbols: 120 · generated 2026-11-19T12:01+00:00

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

## Change from the prior simulation

Same window and universe count. Ranks use published CAGR on the shared variants; ties share a rank. Differences include data refresh, share sizing, execution and carried marks.

| Variant | Prior rank | Current rank | Prior CAGR | Current CAGR | Prior drawdown | Current drawdown |
|---|---|---|---|---|---|---|
| base_v1_6 | 4 | 3 | 27.37% | 30.16% | -42.19% | -30.24% |
| base_v1_5 | 1 | 9 | 32.06% | 28.33% | -42.89% | -29.9% |
| no_buy_above_30pct_36d | 11 | 13 | 24.76% | 17.93% | -42.98% | -25.63% |
| sell_above_30pct_36d | 14 | 15 | 18.46% | 11.73% | -34.37% | -25.12% |
| wait_under_resistance | 3 | 2 | 28.77% | 30.67% | -40.41% | -27.58% |
| two_closes_above_resistance | 2 | 1 | 31.88% | 31.13% | -44.05% | -29.67% |
| sell_failed_breakout | 4 | 3 | 27.37% | 30.16% | -42.19% | -30.24% |
| wait_res_and_sell_failed | 10 | 12 | 26.37% | 19.13% | -36.97% | -34.29% |
| kell_crossback_exit | 9 | 8 | 26.6% | 28.53% | -32.07% | -28.84% |
| kell_base_n_break_entry | 16 | 17 | 11.56% | 10.51% | -28.3% | -17.55% |
| kell_wedge_pop_entry | 17 | 18 | 9.47% | 7.17% | -28.91% | -18.11% |
| kell_full | 17 | 16 | 9.47% | 11.11% | -26.41% | -22.92% |
| buffer_200d_1pct | 4 | 3 | 27.37% | 30.16% | -42.19% | -30.24% |
| buffer_200d_2pct | 4 | 3 | 27.37% | 30.16% | -42.19% | -30.24% |
| buffer_200d_3pct | 4 | 3 | 27.37% | 30.16% | -42.19% | -30.24% |
| sell_all_in_correction | 12 | 10 | 24.12% | 27.26% | -30.29% | -27.09% |
| sell_all_weak_breadth | 15 | 14 | 14.39% | 12.42% | -32.03% | -33.4% |
| sell_all_correction_and_weak_breadth | 13 | 11 | 20.29% | 21.65% | -31.4% | -30.37% |
