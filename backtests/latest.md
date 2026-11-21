# Backtest of the technical rules · 2021-11-20 → 2026-11-20

Technical rules on current members. Historical membership and full label history are unavailable. Survivorship bias may affect strategies differently. Decision on close t, fill at close t+1, 0.10% per fill. Historical technical simulation uses local quote units and excludes FX. Compare variants within this simulation.

## 1 · After a close far above the 36-day average

| Distance to 36-day avg | days | stocks | 21-day mean | 63-day mean | 63-day vs S&P | P(−10% within 21 d) | P(63 d < 0) |
|---|---|---|---|---|---|---|---|
| -100..0% | 67595 | 121 | 1.36% | 4.38% | 1.0% | 25.8% | 46.72% |
| 0..10% | 57834 | 121 | 0.96% | 2.93% | 0.21% | 19.96% | 47.58% |
| 10..20% | 10889 | 120 | 1.54% | 5.28% | 2.62% | 29.94% | 47.82% |
| 20..30% | 2245 | 84 | 3.3% | 9.35% | 6.96% | 40.27% | 47.22% |
| 30..+% | 1533 | 51 | 6.26% | 16.72% | 14.34% | 51.4% | 45.99% |

## 2 · Breakouts above the prior 60-session high (in an uptrend) · failure rate 33.14%

| Case | days | 5-day mean | 21-day mean | 63-day mean | 63-day vs S&P |
|---|---|---|---|---|---|
| all_uptrend_days | 56302 | 0.34% | 1.54% | 4.75% | 1.73% |
| breakout_day | 3476 | 0.21% | 1.59% | 4.59% | 1.72% |
| breakout_failed | 1152 | -4.17% | -5.04% | -1.09% | -3.04% |
| breakout_held | 2324 | 2.39% | 4.87% | 7.4% | 4.08% |
| confirmed_second_close | 2523 | 0.18% | 1.73% | 4.88% | 1.95% |
| just_under_resistance | 16124 | 0.23% | 0.95% | 2.97% | -0.03% |

"breakout_failed" and "breakout_held" use the next 10 sessions to sort the cases, so they are not tradable signals; they show how much a failure costs.

## 3 · Portfolio simulation (10,000, max 8 positions)

| Variant | CAGR | max drawdown | Sharpe | trades | win rate | avg trade | avg days |
|---|---|---|---|---|---|---|---|
| base_v1_6 | 19.37% | -33.83% | 0.82 | 280 | 28.93% | 4.37% | 29.2 |
| base_v1_5 | 25.56% | -33.37% | 1.02 | 276 | 30.43% | 4.94% | 29.5 |
| no_buy_above_30pct_36d | 23.71% | -30.82% | 0.96 | 274 | 31.02% | 4.15% | 29.5 |
| sell_above_30pct_36d | 7.84% | -27.25% | 0.49 | 358 | 32.12% | 1.65% | 22.8 |
| wait_under_resistance | 29.52% | -30.34% | 1.06 | 285 | 28.77% | 5.11% | 28.2 |
| two_closes_above_resistance | 16.48% | -33.18% | 0.74 | 288 | 29.51% | 3.45% | 28.1 |
| sell_failed_breakout | 19.37% | -33.83% | 0.82 | 280 | 28.93% | 4.37% | 29.2 |
| two_closes_and_sell_failed | 28.61% | -31.36% | 1.08 | 268 | 31.72% | 5.51% | 30.1 |
| wait_res_and_sell_failed | 30.24% | -36.53% | 1.08 | 324 | 27.47% | 4.84% | 25.4 |
| kell_crossback_exit | 25.41% | -31.0% | 0.99 | 651 | 35.64% | 1.82% | 12.1 |
| kell_base_n_break_entry | 11.8% | -17.37% | 0.83 | 215 | 27.44% | 2.31% | 35.7 |
| kell_wedge_pop_entry | 6.85% | -20.11% | 0.48 | 230 | 27.83% | 0.94% | 31.2 |
| kell_full | 9.91% | -24.81% | 0.57 | 518 | 33.78% | 0.94% | 13.3 |
| buffer_200d_1pct | 19.37% | -33.83% | 0.82 | 280 | 28.93% | 4.37% | 29.2 |
| buffer_200d_2pct | 19.37% | -33.83% | 0.82 | 280 | 28.93% | 4.37% | 29.2 |
| buffer_200d_3pct | 19.37% | -33.83% | 0.82 | 280 | 28.93% | 4.37% | 29.2 |
| sell_all_in_correction | 25.14% | -29.46% | 0.96 | 353 | 36.54% | 4.3% | 21.6 |
| sell_all_weak_breadth | 15.44% | -28.87% | 0.72 | 627 | 39.39% | 1.72% | 11.9 |
| sell_all_correction_and_weak_breadth | 34.15% | -29.63% | 1.14 | 331 | 34.74% | 4.98% | 23.8 |

S&P 500 buy and hold: CAGR 8.1%, max drawdown -25.43%.

## 4 · Separate periods (same variants)

Members enter a period once they have 200 days of prices, so early periods hold fewer stocks.

### 2014-01-02 → 2017-12-29 · 95 stocks · S&P CAGR 9.94%, max drawdown -14.16%

Breakout failure rate 22.58% · 63-day mean: uptrend days 4.54%, just under resistance 4.25%, failed breakouts 0.48% · more than 30% above the 36-day average: n=209, 63-day 13.78%, P(−10% in 21 d) 53.59%

| Variant | CAGR | max drawdown | Sharpe | trades |
|---|---|---|---|---|
| base_v1_6 | 20.35% | -15.06% | 1.3 | 150 |
| base_v1_5 | 18.56% | -15.24% | 1.16 | 149 |
| no_buy_above_30pct_36d | 16.16% | -15.24% | 1.03 | 155 |
| sell_above_30pct_36d | 17.64% | -14.91% | 1.16 | 163 |
| wait_under_resistance | 20.6% | -13.5% | 1.26 | 135 |
| two_closes_above_resistance | 22.63% | -16.57% | 1.37 | 150 |
| sell_failed_breakout | 20.35% | -15.06% | 1.3 | 150 |
| two_closes_and_sell_failed | 17.42% | -16.54% | 1.12 | 153 |
| wait_res_and_sell_failed | 18.26% | -15.48% | 1.13 | 160 |
| kell_crossback_exit | 8.35% | -16.68% | 0.6 | 519 |
| kell_base_n_break_entry | 1.71% | -20.82% | 0.2 | 148 |
| kell_wedge_pop_entry | 5.78% | -20.75% | 0.53 | 174 |
| kell_full | 1.94% | -17.76% | 0.22 | 456 |
| buffer_200d_1pct | 20.35% | -15.06% | 1.3 | 150 |
| buffer_200d_2pct | 20.35% | -15.06% | 1.3 | 150 |
| buffer_200d_3pct | 20.35% | -15.06% | 1.3 | 150 |
| sell_all_in_correction | 18.61% | -13.63% | 1.26 | 214 |
| sell_all_weak_breadth | 20.6% | -15.38% | 1.3 | 153 |
| sell_all_correction_and_weak_breadth | 20.6% | -15.38% | 1.3 | 153 |

### 2018-01-02 → 2021-12-31 · 110 stocks · S&P CAGR 15.33%, max drawdown -33.92%

Breakout failure rate 30.97% · 63-day mean: uptrend days 5.47%, just under resistance 3.07%, failed breakouts 0.15% · more than 30% above the 36-day average: n=810, 63-day 19.34%, P(−10% in 21 d) 49.01%

| Variant | CAGR | max drawdown | Sharpe | trades |
|---|---|---|---|---|
| base_v1_6 | 35.29% | -19.76% | 1.37 | 218 |
| base_v1_5 | 41.82% | -21.53% | 1.54 | 201 |
| no_buy_above_30pct_36d | 25.96% | -21.35% | 1.09 | 201 |
| sell_above_30pct_36d | 33.47% | -20.44% | 1.51 | 230 |
| wait_under_resistance | 33.15% | -23.03% | 1.31 | 218 |
| two_closes_above_resistance | 34.45% | -23.29% | 1.41 | 200 |
| sell_failed_breakout | 35.29% | -19.76% | 1.37 | 218 |
| two_closes_and_sell_failed | 30.93% | -19.75% | 1.25 | 213 |
| wait_res_and_sell_failed | 29.01% | -30.7% | 1.19 | 226 |
| kell_crossback_exit | 31.89% | -23.84% | 1.25 | 559 |
| kell_base_n_break_entry | 22.16% | -15.97% | 1.32 | 139 |
| kell_wedge_pop_entry | 14.64% | -17.23% | 0.86 | 185 |
| kell_full | 17.34% | -21.99% | 0.97 | 472 |
| buffer_200d_1pct | 35.02% | -19.76% | 1.34 | 209 |
| buffer_200d_2pct | 35.02% | -19.76% | 1.34 | 209 |
| buffer_200d_3pct | 35.02% | -19.76% | 1.34 | 209 |
| sell_all_in_correction | 35.2% | -22.69% | 1.36 | 297 |
| sell_all_weak_breadth | 23.81% | -20.85% | 1.0 | 230 |
| sell_all_correction_and_weak_breadth | 23.81% | -20.85% | 1.0 | 230 |

### 2022-01-03 → 2026-11-20 · 121 stocks · S&P CAGR 7.77%, max drawdown -25.43%

Breakout failure rate 33.05% · 63-day mean: uptrend days 5.07%, just under resistance 3.15%, failed breakouts -0.91% · more than 30% above the 36-day average: n=1531, 63-day 16.79%, P(−10% in 21 d) 51.34%

| Variant | CAGR | max drawdown | Sharpe | trades |
|---|---|---|---|---|
| base_v1_6 | 30.49% | -31.42% | 1.05 | 271 |
| base_v1_5 | 28.25% | -29.81% | 1.06 | 255 |
| no_buy_above_30pct_36d | 29.22% | -29.67% | 1.06 | 276 |
| sell_above_30pct_36d | 8.57% | -27.93% | 0.53 | 356 |
| wait_under_resistance | 34.06% | -26.84% | 1.13 | 275 |
| two_closes_above_resistance | 34.09% | -32.91% | 1.18 | 255 |
| sell_failed_breakout | 30.49% | -31.42% | 1.05 | 271 |
| two_closes_and_sell_failed | 20.93% | -32.63% | 0.9 | 271 |
| wait_res_and_sell_failed | 25.84% | -34.31% | 0.97 | 302 |
| kell_crossback_exit | 25.36% | -26.92% | 1.0 | 622 |
| kell_base_n_break_entry | 14.41% | -15.93% | 0.96 | 207 |
| kell_wedge_pop_entry | 6.45% | -19.75% | 0.47 | 219 |
| kell_full | 10.89% | -25.17% | 0.61 | 496 |
| buffer_200d_1pct | 30.49% | -31.42% | 1.05 | 271 |
| buffer_200d_2pct | 30.49% | -31.42% | 1.05 | 271 |
| buffer_200d_3pct | 30.49% | -31.42% | 1.05 | 271 |
| sell_all_in_correction | 26.86% | -24.14% | 1.01 | 346 |
| sell_all_weak_breadth | 18.74% | -30.5% | 0.8 | 620 |
| sell_all_correction_and_weak_breadth | 26.97% | -29.34% | 1.02 | 308 |

### Robustness: windows in which a variant beat base_v1_6 (the current rules)

| Variant | CAGR | max drawdown (less deep) | Sharpe |
|---|---|---|---|
| no_buy_above_30pct_36d | 0/3 | 1/3 | 1/3 |
| sell_above_30pct_36d | 0/3 | 2/3 | 1/3 |
| wait_under_resistance | 2/3 | 2/3 | 1/3 |
| two_closes_above_resistance | 2/3 | 0/3 | 3/3 |
| sell_failed_breakout | 0/3 | 0/3 | 0/3 |
| two_closes_and_sell_failed | 0/3 | 1/3 | 0/3 |
| wait_res_and_sell_failed | 0/3 | 0/3 | 0/3 |
| kell_crossback_exit | 0/3 | 1/3 | 0/3 |
| kell_base_n_break_entry | 0/3 | 2/3 | 0/3 |
| kell_wedge_pop_entry | 0/3 | 2/3 | 0/3 |
| kell_full | 0/3 | 1/3 | 0/3 |
| buffer_200d_1pct | 0/3 | 0/3 | 0/3 |
| buffer_200d_2pct | 0/3 | 0/3 | 0/3 |
| buffer_200d_3pct | 0/3 | 0/3 | 0/3 |
| sell_all_in_correction | 0/3 | 2/3 | 0/3 |
| sell_all_weak_breadth | 1/3 | 1/3 | 0/3 |
| sell_all_correction_and_weak_breadth | 1/3 | 1/3 | 0/3 |

Symbols: 121 · generated 2026-11-21T06:41+00:00

## Valuation coverage

Positions carry their last observed close on missing dates. No execution at a carried price. Extended gaps and terminal gaps leave delisting proceeds unresolved.

| Variant | Longest gap (sessions) | Missing on final date |
|---|---|---|
| base_v1_6 | 1 | WKL |
| base_v1_5 | 1 | WKL |
| no_buy_above_30pct_36d | 1 | WKL |
| sell_above_30pct_36d | 1 | WKL |
| wait_under_resistance | 1 | None |
| two_closes_above_resistance | 1 | WKL |
| sell_failed_breakout | 1 | WKL |
| two_closes_and_sell_failed | 1 | WKL |
| wait_res_and_sell_failed | 1 | None |
| kell_crossback_exit | 1 | None |
| kell_base_n_break_entry | 1 | None |
| kell_wedge_pop_entry | 1 | None |
| kell_full | 1 | SAN |
| buffer_200d_1pct | 1 | WKL |
| buffer_200d_2pct | 1 | WKL |
| buffer_200d_3pct | 1 | WKL |
| sell_all_in_correction | 1 | None |
| sell_all_weak_breadth | 1 | None |
| sell_all_correction_and_weak_breadth | 1 | None |
