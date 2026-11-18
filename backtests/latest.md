# Backtest of the technical rules · 2021-11-18 → 2026-11-18

Technical rules only (no InvestorAce label, which has no history); universe = today's members (survivorship bias lifts every variant alike). Decide on close t, fill at close t+1, 0.10% per fill. Compare the variants with each other.

## 1 · After a close far above the 36-day average

| Distance to 36-day avg | days | stocks | 21-day mean | 63-day mean | 63-day vs S&P | P(−10% within 21 d) | P(63 d < 0) |
|---|---|---|---|---|---|---|---|
| -100..0% | 66981 | 120 | 1.33% | 4.36% | 0.98% | 25.67% | 46.7% |
| 0..10% | 57479 | 120 | 0.98% | 2.94% | 0.23% | 19.8% | 47.52% |
| 10..20% | 10741 | 119 | 1.56% | 5.29% | 2.61% | 29.93% | 47.84% |
| 20..30% | 2187 | 82 | 3.46% | 9.55% | 7.13% | 40.19% | 47.05% |
| 30..+% | 1500 | 50 | 6.4% | 17.0% | 14.56% | 51.6% | 46.2% |

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
| base_v1_6 | 27.37% | -42.19% | 0.78 | 280 | 30.0% | 4.69% | 29.1 |
| base_v1_5 | 32.06% | -42.89% | 0.85 | 256 | 31.25% | 5.53% | 31.9 |
| no_buy_above_30pct_36d | 24.76% | -42.98% | 0.77 | 256 | 32.03% | 4.33% | 31.4 |
| sell_above_30pct_36d | 18.46% | -34.37% | 0.61 | 341 | 33.72% | 2.59% | 24.2 |
| wait_under_resistance | 28.77% | -40.41% | 0.86 | 309 | 26.86% | 4.53% | 26.1 |
| two_closes_above_resistance | 31.88% | -44.05% | 0.87 | 276 | 31.52% | 4.95% | 29.1 |
| sell_failed_breakout | 27.37% | -42.19% | 0.78 | 280 | 30.0% | 4.69% | 29.1 |
| wait_res_and_sell_failed | 26.37% | -36.97% | 0.8 | 309 | 29.13% | 3.84% | 26.2 |
| kell_crossback_exit | 26.6% | -32.07% | 0.82 | 644 | 34.94% | 1.8% | 12.3 |
| kell_base_n_break_entry | 11.56% | -28.3% | 0.49 | 217 | 28.11% | 2.59% | 35.4 |
| kell_wedge_pop_entry | 9.47% | -28.91% | 0.43 | 226 | 29.2% | 1.83% | 32.7 |
| kell_full | 9.47% | -26.41% | 0.48 | 515 | 34.56% | 0.84% | 13.4 |
| buffer_200d_1pct | 27.37% | -42.19% | 0.78 | 280 | 30.0% | 4.69% | 29.1 |
| buffer_200d_2pct | 27.37% | -42.19% | 0.78 | 280 | 30.0% | 4.69% | 29.1 |
| buffer_200d_3pct | 27.37% | -42.19% | 0.78 | 280 | 30.0% | 4.69% | 29.1 |
| sell_all_in_correction | 24.12% | -30.29% | 0.77 | 366 | 34.43% | 3.28% | 21.0 |
| sell_all_weak_breadth | 14.39% | -32.03% | 0.56 | 651 | 37.79% | 1.28% | 11.6 |
| sell_all_correction_and_weak_breadth | 20.29% | -31.4% | 0.7 | 337 | 32.94% | 3.55% | 23.5 |

S&P 500 buy and hold: CAGR 9.27%, max drawdown -25.43%.

## 4 · Separate periods (same variants)

Members enter a period once they have 200 days of prices, so early periods hold fewer stocks.

### 2014-01-02 → 2017-12-29 · 95 stocks · S&P CAGR 9.94%, max drawdown -14.16%

Breakout failure rate 22.58% · 63-day mean: uptrend days 4.54%, just under resistance 4.25%, failed breakouts 0.48% · more than 30% above the 36-day average: n=209, 63-day 13.78%, P(−10% in 21 d) 53.59%

| Variant | CAGR | max drawdown | Sharpe | trades |
|---|---|---|---|---|
| base_v1_6 | 22.14% | -33.01% | 0.7 | 152 |
| base_v1_5 | 19.7% | -34.7% | 0.61 | 158 |
| no_buy_above_30pct_36d | 17.23% | -34.7% | 0.57 | 157 |
| sell_above_30pct_36d | 19.69% | -32.38% | 0.6 | 158 |
| wait_under_resistance | 21.77% | -31.28% | 0.69 | 136 |
| two_closes_above_resistance | 20.67% | -30.68% | 0.64 | 153 |
| sell_failed_breakout | 22.14% | -33.01% | 0.7 | 152 |
| wait_res_and_sell_failed | 17.18% | -30.35% | 0.6 | 158 |
| kell_crossback_exit | 16.81% | -41.95% | 0.54 | 520 |
| kell_base_n_break_entry | 5.25% | -29.05% | 0.33 | 127 |
| kell_wedge_pop_entry | 8.3% | -17.67% | 0.47 | 179 |
| kell_full | 6.74% | -31.52% | 0.36 | 445 |
| buffer_200d_1pct | 22.14% | -33.01% | 0.7 | 152 |
| buffer_200d_2pct | 22.14% | -33.01% | 0.7 | 152 |
| buffer_200d_3pct | 22.14% | -33.01% | 0.7 | 152 |
| sell_all_in_correction | 14.08% | -33.01% | 0.53 | 220 |
| sell_all_weak_breadth | 19.72% | -33.01% | 0.67 | 158 |
| sell_all_correction_and_weak_breadth | 19.72% | -33.01% | 0.67 | 158 |

### 2018-01-02 → 2021-12-31 · 109 stocks · S&P CAGR 15.33%, max drawdown -33.92%

Breakout failure rate 30.91% · 63-day mean: uptrend days 5.38%, just under resistance 3.07%, failed breakouts 0.23% · more than 30% above the 36-day average: n=767, 63-day 18.9%, P(−10% in 21 d) 50.33%

| Variant | CAGR | max drawdown | Sharpe | trades |
|---|---|---|---|---|
| base_v1_6 | 31.48% | -26.18% | 0.88 | 218 |
| base_v1_5 | 27.92% | -37.44% | 0.75 | 210 |
| no_buy_above_30pct_36d | 34.58% | -34.65% | 0.86 | 199 |
| sell_above_30pct_36d | 32.61% | -30.85% | 0.9 | 238 |
| wait_under_resistance | 28.67% | -30.23% | 0.86 | 225 |
| two_closes_above_resistance | 34.45% | -25.82% | 0.98 | 198 |
| sell_failed_breakout | 31.48% | -26.18% | 0.88 | 218 |
| wait_res_and_sell_failed | 27.25% | -37.85% | 0.72 | 239 |
| kell_crossback_exit | 25.18% | -41.3% | 0.65 | 603 |
| kell_base_n_break_entry | 20.07% | -21.56% | 0.68 | 138 |
| kell_wedge_pop_entry | 18.27% | -23.31% | 0.65 | 174 |
| kell_full | 4.87% | -34.19% | 0.32 | 491 |
| buffer_200d_1pct | 30.35% | -26.18% | 0.85 | 217 |
| buffer_200d_2pct | 30.35% | -26.18% | 0.85 | 217 |
| buffer_200d_3pct | 30.35% | -26.18% | 0.85 | 217 |
| sell_all_in_correction | 35.68% | -40.81% | 0.87 | 290 |
| sell_all_weak_breadth | 31.85% | -26.41% | 0.89 | 226 |
| sell_all_correction_and_weak_breadth | 31.85% | -26.41% | 0.89 | 226 |

### 2022-01-03 → 2026-11-18 · 120 stocks · S&P CAGR 9.09%, max drawdown -25.43%

Breakout failure rate 32.92% · 63-day mean: uptrend days 5.13%, just under resistance 3.2%, failed breakouts -0.83% · more than 30% above the 36-day average: n=1495, 63-day 17.16%, P(−10% in 21 d) 51.44%

| Variant | CAGR | max drawdown | Sharpe | trades |
|---|---|---|---|---|
| base_v1_6 | 29.61% | -42.22% | 0.82 | 269 |
| base_v1_5 | 34.33% | -42.9% | 0.88 | 249 |
| no_buy_above_30pct_36d | 26.72% | -42.98% | 0.8 | 249 |
| sell_above_30pct_36d | 19.21% | -34.37% | 0.62 | 331 |
| wait_under_resistance | 33.05% | -40.42% | 0.9 | 295 |
| two_closes_above_resistance | 34.62% | -44.06% | 0.88 | 260 |
| sell_failed_breakout | 29.61% | -42.22% | 0.82 | 269 |
| wait_res_and_sell_failed | 29.49% | -36.97% | 0.86 | 297 |
| kell_crossback_exit | 29.13% | -32.1% | 0.87 | 622 |
| kell_base_n_break_entry | 13.27% | -28.37% | 0.53 | 211 |
| kell_wedge_pop_entry | 9.44% | -28.91% | 0.43 | 217 |
| kell_full | 10.62% | -26.42% | 0.53 | 493 |
| buffer_200d_1pct | 29.61% | -42.22% | 0.82 | 269 |
| buffer_200d_2pct | 29.61% | -42.22% | 0.82 | 269 |
| buffer_200d_3pct | 29.61% | -42.22% | 0.82 | 269 |
| sell_all_in_correction | 25.99% | -30.29% | 0.81 | 355 |
| sell_all_weak_breadth | 15.89% | -31.41% | 0.59 | 641 |
| sell_all_correction_and_weak_breadth | 22.17% | -31.42% | 0.74 | 326 |

### Robustness: windows in which a variant beat base_v1_6 (the current rules)

| Variant | CAGR | max drawdown (less deep) | Sharpe |
|---|---|---|---|
| no_buy_above_30pct_36d | 1/3 | 0/3 | 0/3 |
| sell_above_30pct_36d | 1/3 | 2/3 | 1/3 |
| wait_under_resistance | 1/3 | 2/3 | 1/3 |
| two_closes_above_resistance | 2/3 | 2/3 | 2/3 |
| sell_failed_breakout | 0/3 | 0/3 | 0/3 |
| wait_res_and_sell_failed | 0/3 | 2/3 | 1/3 |
| kell_crossback_exit | 0/3 | 1/3 | 1/3 |
| kell_base_n_break_entry | 0/3 | 3/3 | 0/3 |
| kell_wedge_pop_entry | 0/3 | 3/3 | 0/3 |
| kell_full | 0/3 | 2/3 | 0/3 |
| buffer_200d_1pct | 0/3 | 0/3 | 0/3 |
| buffer_200d_2pct | 0/3 | 0/3 | 0/3 |
| buffer_200d_3pct | 0/3 | 0/3 | 0/3 |
| sell_all_in_correction | 1/3 | 1/3 | 0/3 |
| sell_all_weak_breadth | 1/3 | 1/3 | 1/3 |
| sell_all_correction_and_weak_breadth | 1/3 | 1/3 | 1/3 |

Symbols: 120 · generated 2026-11-18T15:01+00:00
