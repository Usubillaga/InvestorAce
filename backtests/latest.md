# Backtest of the technical rules · 2021-11-12 → 2026-11-12

Technical rules only (no InvestorAce label, which has no history); universe = today's members (survivorship bias lifts every variant alike). Decide on close t, fill at close t+1, 0.10% per fill. Compare the variants with each other.

## 1 · After a close far above the 36-day average

| Distance to 36-day avg | days | stocks | 21-day mean | 63-day mean | 63-day vs S&P | P(−10% within 21 d) | P(63 d < 0) |
|---|---|---|---|---|---|---|---|
| -100..0% | 61185 | 110 | 1.35% | 4.54% | 1.17% | 26.57% | 46.86% |
| 0..10% | 51995 | 110 | 1.04% | 3.13% | 0.38% | 20.23% | 47.35% |
| 10..20% | 10125 | 109 | 1.65% | 5.38% | 2.74% | 31.0% | 48.09% |
| 20..30% | 2164 | 78 | 3.43% | 9.56% | 7.17% | 40.48% | 47.37% |
| 30..+% | 1488 | 49 | 6.35% | 17.03% | 14.57% | 51.81% | 46.37% |

## 2 · Breakouts above the prior 60-session high (in an uptrend) · failure rate 33.49%

| Case | days | 5-day mean | 21-day mean | 63-day mean | 63-day vs S&P |
|---|---|---|---|---|---|
| all_uptrend_days | 51274 | 0.37% | 1.66% | 5.1% | 2.08% |
| breakout_day | 3165 | 0.24% | 1.74% | 4.95% | 2.03% |
| breakout_failed | 1060 | -4.22% | -4.99% | -0.76% | -2.82% |
| breakout_held | 2105 | 2.49% | 5.13% | 7.82% | 4.47% |
| confirmed_second_close | 2296 | 0.24% | 1.9% | 5.35% | 2.41% |
| just_under_resistance | 14602 | 0.23% | 1.04% | 3.17% | 0.16% |

"breakout_failed" and "breakout_held" use the next 10 sessions to sort the cases, so they are not tradable signals; they show how much a failure costs.

## 3 · Portfolio simulation (10,000, max 8 positions)

| Variant | CAGR | max drawdown | Sharpe | trades | win rate | avg trade | avg days |
|---|---|---|---|---|---|---|---|
| base_v1_6 | 34.11% | -38.71% | 0.92 | 279 | 30.82% | 5.52% | 29.6 |
| base_v1_5 | 32.1% | -45.91% | 0.84 | 272 | 29.41% | 5.3% | 30.3 |
| no_buy_above_30pct_36d | 23.95% | -44.95% | 0.75 | 267 | 29.96% | 4.04% | 30.3 |
| sell_above_30pct_36d | 13.08% | -34.19% | 0.5 | 356 | 34.55% | 1.8% | 23.2 |
| wait_under_resistance | 29.43% | -34.01% | 0.89 | 296 | 29.39% | 4.91% | 26.9 |
| two_closes_above_resistance | 30.52% | -42.15% | 0.82 | 289 | 31.49% | 4.85% | 28.5 |
| sell_failed_breakout | 34.11% | -38.71% | 0.92 | 279 | 30.82% | 5.52% | 29.6 |
| wait_res_and_sell_failed | 27.07% | -35.58% | 0.81 | 298 | 30.54% | 4.12% | 26.9 |
| kell_crossback_exit | 30.98% | -31.29% | 0.91 | 647 | 36.01% | 2.02% | 12.3 |
| kell_base_n_break_entry | 11.86% | -24.48% | 0.49 | 219 | 28.31% | 2.39% | 34.5 |
| kell_wedge_pop_entry | 10.62% | -29.51% | 0.45 | 214 | 29.91% | 1.71% | 32.8 |
| kell_full | 7.74% | -26.64% | 0.41 | 509 | 34.38% | 0.8% | 13.4 |

S&P 500 buy and hold: CAGR 10.16%, max drawdown -25.43%.

## 4 · Separate periods (same variants)

Members enter a period once they have 200 days of prices, so early periods hold fewer stocks.

### 2014-01-02 → 2017-12-29 · 85 stocks · S&P CAGR 9.94%, max drawdown -14.16%

Breakout failure rate 22.73% · 63-day mean: uptrend days 4.67%, just under resistance 4.32%, failed breakouts 0.57% · more than 30% above the 36-day average: n=208, 63-day 13.81%, P(−10% in 21 d) 53.85%

| Variant | CAGR | max drawdown | Sharpe | trades |
|---|---|---|---|---|
| base_v1_6 | 19.85% | -29.56% | 0.69 | 145 |
| base_v1_5 | 20.46% | -29.66% | 0.64 | 151 |
| no_buy_above_30pct_36d | 18.0% | -29.66% | 0.59 | 150 |
| sell_above_30pct_36d | 19.75% | -26.47% | 0.69 | 154 |
| wait_under_resistance | 19.73% | -37.02% | 0.64 | 149 |
| two_closes_above_resistance | 20.31% | -30.61% | 0.65 | 155 |
| sell_failed_breakout | 19.85% | -29.56% | 0.69 | 145 |
| wait_res_and_sell_failed | 20.1% | -35.88% | 0.64 | 150 |
| kell_crossback_exit | 17.64% | -38.59% | 0.56 | 519 |
| kell_base_n_break_entry | 8.51% | -28.82% | 0.4 | 128 |
| kell_wedge_pop_entry | 7.46% | -20.85% | 0.39 | 176 |
| kell_full | 5.29% | -26.97% | 0.32 | 449 |

### 2018-01-02 → 2021-12-31 · 99 stocks · S&P CAGR 15.33%, max drawdown -33.92%

Breakout failure rate 30.87% · 63-day mean: uptrend days 5.71%, just under resistance 3.29%, failed breakouts 0.87% · more than 30% above the 36-day average: n=765, 63-day 18.96%, P(−10% in 21 d) 50.46%

| Variant | CAGR | max drawdown | Sharpe | trades |
|---|---|---|---|---|
| base_v1_6 | 31.27% | -27.15% | 0.86 | 235 |
| base_v1_5 | 22.48% | -39.63% | 0.65 | 228 |
| no_buy_above_30pct_36d | 31.87% | -23.91% | 0.93 | 221 |
| sell_above_30pct_36d | 30.09% | -27.84% | 0.9 | 252 |
| wait_under_resistance | 24.4% | -26.54% | 0.83 | 227 |
| two_closes_above_resistance | 28.11% | -28.27% | 0.79 | 221 |
| sell_failed_breakout | 31.27% | -27.15% | 0.86 | 235 |
| wait_res_and_sell_failed | 24.02% | -27.34% | 0.76 | 254 |
| kell_crossback_exit | 25.04% | -30.17% | 0.7 | 589 |
| kell_base_n_break_entry | 16.27% | -21.71% | 0.59 | 146 |
| kell_wedge_pop_entry | 17.75% | -27.71% | 0.6 | 192 |
| kell_full | 8.81% | -33.32% | 0.41 | 484 |

### 2022-01-03 → 2026-11-12 · 110 stocks · S&P CAGR 9.93%, max drawdown -25.43%

Breakout failure rate 33.3% · 63-day mean: uptrend days 5.56%, just under resistance 3.45%, failed breakouts -0.44% · more than 30% above the 36-day average: n=1478, 63-day 17.36%, P(−10% in 21 d) 51.49%

| Variant | CAGR | max drawdown | Sharpe | trades |
|---|---|---|---|---|
| base_v1_6 | 35.61% | -38.71% | 0.94 | 270 |
| base_v1_5 | 35.1% | -45.96% | 0.89 | 262 |
| no_buy_above_30pct_36d | 26.6% | -44.95% | 0.8 | 257 |
| sell_above_30pct_36d | 13.74% | -34.19% | 0.51 | 346 |
| wait_under_resistance | 33.76% | -34.07% | 0.92 | 279 |
| two_closes_above_resistance | 32.46% | -42.16% | 0.85 | 281 |
| sell_failed_breakout | 35.61% | -38.71% | 0.94 | 270 |
| wait_res_and_sell_failed | 29.65% | -35.62% | 0.86 | 286 |
| kell_crossback_exit | 32.86% | -31.3% | 0.94 | 626 |
| kell_base_n_break_entry | 13.16% | -24.48% | 0.52 | 209 |
| kell_wedge_pop_entry | 12.02% | -29.5% | 0.47 | 206 |
| kell_full | 8.79% | -26.65% | 0.45 | 488 |

### Robustness: windows in which a variant beat base_v1_6 (the current rules)

| Variant | CAGR | max drawdown (less deep) | Sharpe |
|---|---|---|---|
| no_buy_above_30pct_36d | 1/3 | 1/3 | 1/3 |
| sell_above_30pct_36d | 0/3 | 2/3 | 1/3 |
| wait_under_resistance | 0/3 | 2/3 | 0/3 |
| two_closes_above_resistance | 1/3 | 0/3 | 0/3 |
| sell_failed_breakout | 0/3 | 0/3 | 0/3 |
| wait_res_and_sell_failed | 1/3 | 1/3 | 0/3 |
| kell_crossback_exit | 0/3 | 1/3 | 0/3 |
| kell_base_n_break_entry | 0/3 | 3/3 | 0/3 |
| kell_wedge_pop_entry | 0/3 | 2/3 | 0/3 |
| kell_full | 0/3 | 2/3 | 0/3 |

Symbols: 110 · generated 2026-11-12T20:13+00:00
