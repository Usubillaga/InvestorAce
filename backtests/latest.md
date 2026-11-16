# Backtest of the technical rules · 2021-11-16 → 2026-11-16

Technical rules only (no InvestorAce label, which has no history); universe = today's members (survivorship bias lifts every variant alike). Decide on close t, fill at close t+1, 0.10% per fill. Compare the variants with each other.

## 1 · After a close far above the 36-day average

| Distance to 36-day avg | days | stocks | 21-day mean | 63-day mean | 63-day vs S&P | P(−10% within 21 d) | P(63 d < 0) |
|---|---|---|---|---|---|---|---|
| -100..0% | 65821 | 118 | 1.34% | 4.41% | 1.03% | 25.93% | 46.7% |
| 0..10% | 56324 | 118 | 1.01% | 3.0% | 0.29% | 19.88% | 47.42% |
| 10..20% | 10657 | 117 | 1.55% | 5.32% | 2.63% | 30.13% | 47.96% |
| 20..30% | 2184 | 82 | 3.43% | 9.6% | 7.17% | 40.2% | 46.98% |
| 30..+% | 1496 | 50 | 6.37% | 17.02% | 14.56% | 51.74% | 46.19% |

## 2 · Breakouts above the prior 60-session high (in an uptrend) · failure rate 33.23%

| Case | days | 5-day mean | 21-day mean | 63-day mean | 63-day vs S&P |
|---|---|---|---|---|---|
| all_uptrend_days | 54944 | 0.35% | 1.57% | 4.82% | 1.81% |
| breakout_day | 3386 | 0.21% | 1.69% | 4.64% | 1.73% |
| breakout_failed | 1125 | -4.19% | -4.96% | -1.07% | -3.07% |
| breakout_held | 2261 | 2.4% | 5.0% | 7.48% | 4.12% |
| confirmed_second_close | 2462 | 0.18% | 1.82% | 4.96% | 2.0% |
| just_under_resistance | 15745 | 0.23% | 0.98% | 3.01% | 0.02% |

"breakout_failed" and "breakout_held" use the next 10 sessions to sort the cases, so they are not tradable signals; they show how much a failure costs.

## 3 · Portfolio simulation (10,000, max 8 positions)

| Variant | CAGR | max drawdown | Sharpe | trades | win rate | avg trade | avg days |
|---|---|---|---|---|---|---|---|
| base_v1_6 | 27.08% | -42.17% | 0.77 | 282 | 29.43% | 4.61% | 28.8 |
| base_v1_5 | 31.12% | -42.88% | 0.83 | 262 | 29.77% | 5.27% | 31.1 |
| no_buy_above_30pct_36d | 24.1% | -42.99% | 0.75 | 262 | 30.92% | 4.16% | 30.6 |
| sell_above_30pct_36d | 17.99% | -34.37% | 0.59 | 342 | 33.33% | 2.54% | 24.1 |
| wait_under_resistance | 29.34% | -40.41% | 0.87 | 308 | 27.27% | 4.56% | 26.0 |
| two_closes_above_resistance | 30.57% | -44.05% | 0.81 | 278 | 30.94% | 4.74% | 29.5 |
| sell_failed_breakout | 27.08% | -42.17% | 0.77 | 282 | 29.43% | 4.61% | 28.8 |
| wait_res_and_sell_failed | 26.4% | -36.97% | 0.77 | 308 | 28.9% | 3.85% | 26.4 |
| kell_crossback_exit | 27.29% | -32.05% | 0.84 | 641 | 35.41% | 1.85% | 12.4 |
| kell_base_n_break_entry | 12.64% | -21.75% | 0.52 | 213 | 27.23% | 2.73% | 35.0 |
| kell_wedge_pop_entry | 12.3% | -36.39% | 0.48 | 214 | 29.91% | 2.05% | 33.1 |
| kell_full | 10.1% | -26.53% | 0.5 | 512 | 34.38% | 0.93% | 13.4 |
| buffer_200d_1pct | 27.08% | -42.17% | 0.77 | 282 | 29.43% | 4.61% | 28.8 |
| buffer_200d_2pct | 27.08% | -42.17% | 0.77 | 282 | 29.43% | 4.61% | 28.8 |
| buffer_200d_3pct | 27.08% | -42.17% | 0.77 | 282 | 29.43% | 4.61% | 28.8 |

S&P 500 buy and hold: CAGR 9.55%, max drawdown -25.43%.

## 4 · Separate periods (same variants)

Members enter a period once they have 200 days of prices, so early periods hold fewer stocks.

### 2014-01-02 → 2017-12-29 · 94 stocks · S&P CAGR 9.94%, max drawdown -14.16%

Breakout failure rate 22.68% · 63-day mean: uptrend days 4.56%, just under resistance 4.29%, failed breakouts 0.45% · more than 30% above the 36-day average: n=209, 63-day 13.78%, P(−10% in 21 d) 53.59%

| Variant | CAGR | max drawdown | Sharpe | trades |
|---|---|---|---|---|
| base_v1_6 | 22.14% | -33.01% | 0.7 | 152 |
| base_v1_5 | 19.7% | -34.7% | 0.61 | 158 |
| no_buy_above_30pct_36d | 17.23% | -34.7% | 0.57 | 157 |
| sell_above_30pct_36d | 19.69% | -32.38% | 0.6 | 158 |
| wait_under_resistance | 19.48% | -31.28% | 0.65 | 137 |
| two_closes_above_resistance | 20.67% | -30.68% | 0.64 | 153 |
| sell_failed_breakout | 22.14% | -33.01% | 0.7 | 152 |
| wait_res_and_sell_failed | 19.67% | -30.35% | 0.65 | 156 |
| kell_crossback_exit | 16.75% | -41.92% | 0.54 | 520 |
| kell_base_n_break_entry | 8.62% | -28.94% | 0.4 | 127 |
| kell_wedge_pop_entry | 8.05% | -18.55% | 0.46 | 179 |
| kell_full | 6.74% | -31.43% | 0.36 | 445 |
| buffer_200d_1pct | 22.14% | -33.01% | 0.7 | 152 |
| buffer_200d_2pct | 22.14% | -33.01% | 0.7 | 152 |
| buffer_200d_3pct | 22.14% | -33.01% | 0.7 | 152 |

### 2018-01-02 → 2021-12-31 · 107 stocks · S&P CAGR 15.33%, max drawdown -33.92%

Breakout failure rate 31.13% · 63-day mean: uptrend days 5.36%, just under resistance 3.02%, failed breakouts 0.26% · more than 30% above the 36-day average: n=767, 63-day 18.9%, P(−10% in 21 d) 50.33%

| Variant | CAGR | max drawdown | Sharpe | trades |
|---|---|---|---|---|
| base_v1_6 | 28.88% | -36.66% | 0.77 | 217 |
| base_v1_5 | 25.02% | -41.22% | 0.68 | 213 |
| no_buy_above_30pct_36d | 32.81% | -47.09% | 0.74 | 200 |
| sell_above_30pct_36d | 34.12% | -40.47% | 0.87 | 229 |
| wait_under_resistance | 27.27% | -31.23% | 0.84 | 224 |
| two_closes_above_resistance | 31.38% | -26.21% | 0.86 | 201 |
| sell_failed_breakout | 28.88% | -36.66% | 0.77 | 217 |
| wait_res_and_sell_failed | 26.19% | -24.87% | 0.78 | 242 |
| kell_crossback_exit | 23.97% | -41.3% | 0.63 | 603 |
| kell_base_n_break_entry | 19.23% | -21.56% | 0.64 | 143 |
| kell_wedge_pop_entry | 18.19% | -23.31% | 0.65 | 175 |
| kell_full | 5.57% | -34.87% | 0.34 | 495 |
| buffer_200d_1pct | 28.66% | -36.67% | 0.76 | 218 |
| buffer_200d_2pct | 28.66% | -36.67% | 0.76 | 218 |
| buffer_200d_3pct | 28.66% | -36.67% | 0.76 | 218 |

### 2022-01-03 → 2026-11-16 · 118 stocks · S&P CAGR 9.37%, max drawdown -25.43%

Breakout failure rate 33.0% · 63-day mean: uptrend days 5.25%, just under resistance 3.28%, failed breakouts -0.73% · more than 30% above the 36-day average: n=1489, 63-day 17.24%, P(−10% in 21 d) 51.51%

| Variant | CAGR | max drawdown | Sharpe | trades |
|---|---|---|---|---|
| base_v1_6 | 29.6% | -42.21% | 0.81 | 271 |
| base_v1_5 | 34.07% | -42.89% | 0.87 | 251 |
| no_buy_above_30pct_36d | 26.7% | -42.98% | 0.8 | 251 |
| sell_above_30pct_36d | 19.14% | -34.37% | 0.61 | 331 |
| wait_under_resistance | 33.46% | -40.42% | 0.9 | 294 |
| two_closes_above_resistance | 34.18% | -44.06% | 0.87 | 263 |
| sell_failed_breakout | 29.6% | -42.21% | 0.81 | 271 |
| wait_res_and_sell_failed | 29.38% | -36.97% | 0.85 | 298 |
| kell_crossback_exit | 29.74% | -30.42% | 0.88 | 618 |
| kell_base_n_break_entry | 15.26% | -21.75% | 0.58 | 203 |
| kell_wedge_pop_entry | 13.04% | -36.39% | 0.49 | 200 |
| kell_full | 11.53% | -26.55% | 0.56 | 489 |
| buffer_200d_1pct | 29.6% | -42.21% | 0.81 | 271 |
| buffer_200d_2pct | 29.6% | -42.21% | 0.81 | 271 |
| buffer_200d_3pct | 29.6% | -42.21% | 0.81 | 271 |

### Robustness: windows in which a variant beat base_v1_6 (the current rules)

| Variant | CAGR | max drawdown (less deep) | Sharpe |
|---|---|---|---|
| no_buy_above_30pct_36d | 1/3 | 0/3 | 0/3 |
| sell_above_30pct_36d | 1/3 | 2/3 | 1/3 |
| wait_under_resistance | 1/3 | 3/3 | 2/3 |
| two_closes_above_resistance | 2/3 | 2/3 | 2/3 |
| sell_failed_breakout | 0/3 | 0/3 | 0/3 |
| wait_res_and_sell_failed | 0/3 | 3/3 | 2/3 |
| kell_crossback_exit | 1/3 | 1/3 | 1/3 |
| kell_base_n_break_entry | 0/3 | 3/3 | 0/3 |
| kell_wedge_pop_entry | 0/3 | 3/3 | 0/3 |
| kell_full | 0/3 | 3/3 | 0/3 |
| buffer_200d_1pct | 0/3 | 0/3 | 0/3 |
| buffer_200d_2pct | 0/3 | 0/3 | 0/3 |
| buffer_200d_3pct | 0/3 | 0/3 | 0/3 |

Symbols: 118 · generated 2026-11-16T22:36+00:00
