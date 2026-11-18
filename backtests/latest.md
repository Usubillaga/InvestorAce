# Backtest of the technical rules · 2021-11-17 → 2026-11-17

Technical rules only (no InvestorAce label, which has no history); universe = today's members (survivorship bias lifts every variant alike). Decide on close t, fill at close t+1, 0.10% per fill. Compare the variants with each other.

## 1 · After a close far above the 36-day average

| Distance to 36-day avg | days | stocks | 21-day mean | 63-day mean | 63-day vs S&P | P(−10% within 21 d) | P(63 d < 0) |
|---|---|---|---|---|---|---|---|
| -100..0% | 66963 | 120 | 1.33% | 4.37% | 0.98% | 25.67% | 46.7% |
| 0..10% | 57499 | 120 | 0.98% | 2.94% | 0.23% | 19.8% | 47.54% |
| 10..20% | 10733 | 119 | 1.55% | 5.29% | 2.61% | 29.94% | 47.84% |
| 20..30% | 2184 | 82 | 3.45% | 9.59% | 7.17% | 40.2% | 46.98% |
| 30..+% | 1498 | 50 | 6.37% | 17.0% | 14.55% | 51.67% | 46.19% |

## 2 · Breakouts above the prior 60-session high (in an uptrend) · failure rate 33.02%

| Case | days | 5-day mean | 21-day mean | 63-day mean | 63-day vs S&P |
|---|---|---|---|---|---|
| all_uptrend_days | 55900 | 0.34% | 1.54% | 4.75% | 1.75% |
| breakout_day | 3449 | 0.21% | 1.63% | 4.6% | 1.74% |
| breakout_failed | 1139 | -4.18% | -4.98% | -1.06% | -3.02% |
| breakout_held | 2310 | 2.38% | 4.9% | 7.4% | 4.08% |
| confirmed_second_close | 2501 | 0.2% | 1.79% | 4.9% | 1.96% |
| just_under_resistance | 16061 | 0.22% | 0.95% | 2.97% | 0.01% |

"breakout_failed" and "breakout_held" use the next 10 sessions to sort the cases, so they are not tradable signals; they show how much a failure costs.

## 3 · Portfolio simulation (10,000, max 8 positions)

| Variant | CAGR | max drawdown | Sharpe | trades | win rate | avg trade | avg days |
|---|---|---|---|---|---|---|---|
| base_v1_6 | 27.46% | -42.18% | 0.78 | 279 | 30.11% | 4.68% | 29.2 |
| base_v1_5 | 31.22% | -42.88% | 0.83 | 257 | 30.35% | 5.39% | 31.8 |
| no_buy_above_30pct_36d | 23.97% | -42.99% | 0.75 | 257 | 31.13% | 4.2% | 31.2 |
| sell_above_30pct_36d | 18.0% | -34.37% | 0.6 | 340 | 33.82% | 2.55% | 24.2 |
| wait_under_resistance | 29.6% | -40.41% | 0.84 | 306 | 27.78% | 4.66% | 26.7 |
| two_closes_above_resistance | 31.95% | -44.05% | 0.87 | 273 | 31.87% | 4.98% | 29.4 |
| sell_failed_breakout | 27.46% | -42.18% | 0.78 | 279 | 30.11% | 4.68% | 29.2 |
| wait_res_and_sell_failed | 26.16% | -36.97% | 0.76 | 308 | 28.9% | 3.85% | 26.5 |
| kell_crossback_exit | 26.91% | -31.32% | 0.83 | 641 | 35.1% | 1.83% | 12.4 |
| kell_base_n_break_entry | 12.01% | -28.3% | 0.5 | 216 | 28.24% | 2.64% | 35.5 |
| kell_wedge_pop_entry | 9.16% | -28.91% | 0.42 | 228 | 29.39% | 1.74% | 32.0 |
| kell_full | 9.52% | -26.4% | 0.48 | 515 | 34.37% | 0.82% | 13.5 |
| buffer_200d_1pct | 27.46% | -42.18% | 0.78 | 279 | 30.11% | 4.68% | 29.2 |
| buffer_200d_2pct | 27.46% | -42.18% | 0.78 | 279 | 30.11% | 4.68% | 29.2 |
| buffer_200d_3pct | 27.46% | -42.18% | 0.78 | 279 | 30.11% | 4.68% | 29.2 |
| sell_all_in_correction | 24.03% | -30.29% | 0.77 | 358 | 33.8% | 3.23% | 20.8 |

S&P 500 buy and hold: CAGR 9.38%, max drawdown -25.43%.

## 4 · Separate periods (same variants)

Members enter a period once they have 200 days of prices, so early periods hold fewer stocks.

### 2014-01-02 → 2017-12-29 · 95 stocks · S&P CAGR 9.94%, max drawdown -14.16%

Breakout failure rate 22.57% · 63-day mean: uptrend days 4.54%, just under resistance 4.25%, failed breakouts 0.48% · more than 30% above the 36-day average: n=209, 63-day 13.78%, P(−10% in 21 d) 53.59%

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

### 2018-01-02 → 2021-12-31 · 109 stocks · S&P CAGR 15.33%, max drawdown -33.92%

Breakout failure rate 30.89% · 63-day mean: uptrend days 5.38%, just under resistance 3.07%, failed breakouts 0.23% · more than 30% above the 36-day average: n=767, 63-day 18.9%, P(−10% in 21 d) 50.33%

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

### 2022-01-03 → 2026-11-17 · 120 stocks · S&P CAGR 9.13%, max drawdown -25.43%

Breakout failure rate 32.87% · 63-day mean: uptrend days 5.14%, just under resistance 3.2%, failed breakouts -0.77% · more than 30% above the 36-day average: n=1492, 63-day 17.19%, P(−10% in 21 d) 51.47%

| Variant | CAGR | max drawdown | Sharpe | trades |
|---|---|---|---|---|
| base_v1_6 | 29.92% | -42.22% | 0.82 | 268 |
| base_v1_5 | 34.65% | -42.9% | 0.88 | 248 |
| no_buy_above_30pct_36d | 27.02% | -42.98% | 0.8 | 248 |
| sell_above_30pct_36d | 19.55% | -34.37% | 0.62 | 330 |
| wait_under_resistance | 33.51% | -40.42% | 0.91 | 293 |
| two_closes_above_resistance | 35.02% | -44.06% | 0.89 | 259 |
| sell_failed_breakout | 29.92% | -42.22% | 0.82 | 268 |
| wait_res_and_sell_failed | 29.96% | -36.97% | 0.87 | 295 |
| kell_crossback_exit | 29.63% | -30.97% | 0.88 | 619 |
| kell_base_n_break_entry | 13.75% | -28.37% | 0.54 | 210 |
| kell_wedge_pop_entry | 9.67% | -28.91% | 0.43 | 215 |
| kell_full | 10.9% | -26.42% | 0.54 | 493 |
| buffer_200d_1pct | 29.92% | -42.22% | 0.82 | 268 |
| buffer_200d_2pct | 29.92% | -42.22% | 0.82 | 268 |
| buffer_200d_3pct | 29.92% | -42.22% | 0.82 | 268 |
| sell_all_in_correction | 26.22% | -30.29% | 0.82 | 347 |

### Robustness: windows in which a variant beat base_v1_6 (the current rules)

| Variant | CAGR | max drawdown (less deep) | Sharpe |
|---|---|---|---|
| no_buy_above_30pct_36d | 1/3 | 0/3 | 0/3 |
| sell_above_30pct_36d | 1/3 | 2/3 | 1/3 |
| wait_under_resistance | 1/3 | 2/3 | 1/3 |
| two_closes_above_resistance | 2/3 | 2/3 | 2/3 |
| sell_failed_breakout | 0/3 | 0/3 | 0/3 |
| wait_res_and_sell_failed | 1/3 | 2/3 | 1/3 |
| kell_crossback_exit | 0/3 | 1/3 | 1/3 |
| kell_base_n_break_entry | 0/3 | 3/3 | 0/3 |
| kell_wedge_pop_entry | 0/3 | 3/3 | 0/3 |
| kell_full | 0/3 | 2/3 | 0/3 |
| buffer_200d_1pct | 0/3 | 0/3 | 0/3 |
| buffer_200d_2pct | 0/3 | 0/3 | 0/3 |
| buffer_200d_3pct | 0/3 | 0/3 | 0/3 |
| sell_all_in_correction | 1/3 | 1/3 | 0/3 |

Symbols: 120 · generated 2026-11-18T14:28+00:00
