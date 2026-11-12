# Backtest of the technical rules · 2021-11-11 → 2026-11-11

Technical rules only (no InvestorAce label, which has no history); universe = today's members (survivorship bias lifts every variant alike). Decide on close t, fill at close t+1, 0.10% per fill. Compare the variants with each other.

## 1 · After a close far above the 36-day average

| Distance to 36-day avg | days | stocks | 21-day mean | 63-day mean | 63-day vs S&P | P(−10% within 21 d) | P(63 d < 0) |
|---|---|---|---|---|---|---|---|
| -100..0% | 61171 | 110 | 1.35% | 4.54% | 1.17% | 26.57% | 46.87% |
| 0..10% | 52005 | 110 | 1.04% | 3.12% | 0.38% | 20.23% | 47.36% |
| 10..20% | 10120 | 109 | 1.65% | 5.38% | 2.74% | 30.99% | 48.1% |
| 20..30% | 2165 | 78 | 3.45% | 9.58% | 7.19% | 40.37% | 47.39% |
| 30..+% | 1485 | 49 | 6.32% | 17.09% | 14.62% | 51.85% | 46.26% |

## 2 · Breakouts above the prior 60-session high (in an uptrend) · failure rate 33.52%

| Case | days | 5-day mean | 21-day mean | 63-day mean | 63-day vs S&P |
|---|---|---|---|---|---|
| all_uptrend_days | 51296 | 0.37% | 1.65% | 5.09% | 2.07% |
| breakout_day | 3165 | 0.24% | 1.74% | 4.94% | 2.02% |
| breakout_failed | 1061 | -4.22% | -4.99% | -0.77% | -2.82% |
| breakout_held | 2104 | 2.49% | 5.13% | 7.81% | 4.46% |
| confirmed_second_close | 2295 | 0.24% | 1.89% | 5.34% | 2.39% |
| just_under_resistance | 14615 | 0.23% | 1.03% | 3.16% | 0.16% |

"breakout_failed" and "breakout_held" use the next 10 sessions to sort the cases, so they are not tradable signals; they show how much a failure costs.

## 3 · Portfolio simulation (10,000, max 8 positions)

| Variant | CAGR | max drawdown | Sharpe | trades | win rate | avg trade | avg days |
|---|---|---|---|---|---|---|---|
| base_v1_5 | 32.17% | -45.92% | 0.85 | 274 | 29.2% | 5.27% | 30.1 |
| no_buy_above_30pct_36d | 24.1% | -44.95% | 0.75 | 269 | 29.74% | 4.02% | 30.2 |
| sell_above_30pct_36d | 11.88% | -34.17% | 0.47 | 358 | 33.52% | 1.67% | 23.1 |
| wait_under_resistance | 31.23% | -34.04% | 0.88 | 291 | 29.9% | 5.21% | 28.0 |
| two_closes_above_resistance | 29.76% | -42.15% | 0.81 | 291 | 31.27% | 4.73% | 28.4 |
| sell_failed_breakout | 33.41% | -38.71% | 0.91 | 284 | 30.28% | 5.35% | 29.1 |
| wait_res_and_sell_failed | 26.21% | -35.57% | 0.79 | 303 | 29.7% | 3.97% | 26.5 |

S&P 500 buy and hold: CAGR 10.39%, max drawdown -25.43%.

## 4 · Separate periods (same variants)

Members enter a period once they have 200 days of prices, so early periods hold fewer stocks.

### 2014-01-02 → 2017-12-29 · 85 stocks · S&P CAGR 9.94%, max drawdown -14.16%

Breakout failure rate 22.73% · 63-day mean: uptrend days 4.67%, just under resistance 4.32%, failed breakouts 0.57% · more than 30% above the 36-day average: n=208, 63-day 13.81%, P(−10% in 21 d) 53.85%

| Variant | CAGR | max drawdown | Sharpe | trades |
|---|---|---|---|---|
| base_v1_5 | 20.46% | -29.66% | 0.64 | 151 |
| no_buy_above_30pct_36d | 18.0% | -29.66% | 0.59 | 150 |
| sell_above_30pct_36d | 19.75% | -26.47% | 0.69 | 154 |
| wait_under_resistance | 19.73% | -37.02% | 0.64 | 149 |
| two_closes_above_resistance | 20.31% | -30.61% | 0.65 | 155 |
| sell_failed_breakout | 19.85% | -29.56% | 0.69 | 145 |
| wait_res_and_sell_failed | 20.1% | -35.88% | 0.64 | 150 |

### 2018-01-02 → 2021-12-31 · 99 stocks · S&P CAGR 15.33%, max drawdown -33.92%

Breakout failure rate 30.89% · 63-day mean: uptrend days 5.71%, just under resistance 3.29%, failed breakouts 0.87% · more than 30% above the 36-day average: n=765, 63-day 18.96%, P(−10% in 21 d) 50.46%

| Variant | CAGR | max drawdown | Sharpe | trades |
|---|---|---|---|---|
| base_v1_5 | 22.48% | -39.63% | 0.65 | 228 |
| no_buy_above_30pct_36d | 31.87% | -23.91% | 0.93 | 221 |
| sell_above_30pct_36d | 30.09% | -27.84% | 0.9 | 252 |
| wait_under_resistance | 24.4% | -26.54% | 0.83 | 227 |
| two_closes_above_resistance | 28.11% | -28.27% | 0.79 | 221 |
| sell_failed_breakout | 31.27% | -27.15% | 0.86 | 235 |
| wait_res_and_sell_failed | 24.02% | -27.34% | 0.76 | 254 |

### 2022-01-03 → 2026-11-11 · 110 stocks · S&P CAGR 10.0%, max drawdown -25.43%

Breakout failure rate 33.32% · 63-day mean: uptrend days 5.57%, just under resistance 3.45%, failed breakouts -0.44% · more than 30% above the 36-day average: n=1474, 63-day 17.48%, P(−10% in 21 d) 51.49%

| Variant | CAGR | max drawdown | Sharpe | trades |
|---|---|---|---|---|
| base_v1_5 | 34.99% | -45.96% | 0.89 | 262 |
| no_buy_above_30pct_36d | 26.57% | -44.95% | 0.8 | 257 |
| sell_above_30pct_36d | 13.76% | -34.19% | 0.51 | 346 |
| wait_under_resistance | 33.8% | -34.07% | 0.93 | 279 |
| two_closes_above_resistance | 32.34% | -42.16% | 0.85 | 281 |
| sell_failed_breakout | 35.5% | -38.71% | 0.94 | 270 |
| wait_res_and_sell_failed | 29.67% | -35.62% | 0.86 | 286 |

### Robustness: windows in which a variant beat the base (higher is better for all three)

| Variant | CAGR | max drawdown (less deep) | Sharpe |
|---|---|---|---|
| no_buy_above_30pct_36d | 1/3 | 2/3 | 1/3 |
| sell_above_30pct_36d | 1/3 | 3/3 | 2/3 |
| wait_under_resistance | 1/3 | 2/3 | 2/3 |
| two_closes_above_resistance | 1/3 | 2/3 | 2/3 |
| sell_failed_breakout | 2/3 | 3/3 | 3/3 |
| wait_res_and_sell_failed | 1/3 | 2/3 | 1/3 |

Symbols: 110 · generated 2026-11-12T13:45+00:00
