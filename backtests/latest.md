# Backtest of the technical rules · 2021-11-11 → 2026-11-11

Technical rules only (no InvestorAce label, which has no history); universe = today's members (survivorship bias lifts every variant alike). Decide on close t, fill at close t+1, 0.10% per fill. Compare the variants with each other.

## 1 · After a close far above the 36-day average

| Distance to 36-day avg | days | stocks | 21-day mean | 63-day mean | 63-day vs S&P | P(−10% within 21 d) | P(63 d < 0) |
|---|---|---|---|---|---|---|---|
| -100..0% | 60627 | 109 | 1.36% | 4.58% | 1.21% | 26.58% | 46.84% |
| 0..10% | 51467 | 109 | 1.04% | 3.12% | 0.38% | 20.24% | 47.42% |
| 10..20% | 10011 | 108 | 1.71% | 5.48% | 2.84% | 30.93% | 48.14% |
| 20..30% | 2164 | 77 | 3.46% | 9.6% | 7.21% | 40.34% | 47.37% |
| 30..+% | 1485 | 49 | 6.32% | 17.09% | 14.62% | 51.85% | 46.26% |

## 2 · Breakouts above the prior 60-session high (in an uptrend) · failure rate 33.61%

| Case | days | 5-day mean | 21-day mean | 63-day mean | 63-day vs S&P |
|---|---|---|---|---|---|
| all_uptrend_days | 50759 | 0.37% | 1.66% | 5.1% | 2.08% |
| breakout_day | 3130 | 0.25% | 1.77% | 4.98% | 2.07% |
| breakout_failed | 1052 | -4.21% | -4.94% | -0.66% | -2.69% |
| breakout_held | 2078 | 2.51% | 5.17% | 7.83% | 4.48% |
| confirmed_second_close | 2267 | 0.25% | 1.93% | 5.4% | 2.46% |
| just_under_resistance | 14449 | 0.22% | 1.02% | 3.11% | 0.11% |

"breakout_failed" and "breakout_held" use the next 10 sessions to sort the cases, so they are not tradable signals; they show how much a failure costs.

## 3 · Portfolio simulation (10,000, max 8 positions)

| Variant | CAGR | max drawdown | Sharpe | trades | win rate | avg trade | avg days |
|---|---|---|---|---|---|---|---|
| base_v1_5 | 29.76% | -43.11% | 0.81 | 261 | 30.27% | 5.25% | 31.7 |
| no_buy_above_30pct_36d | 24.71% | -44.47% | 0.76 | 263 | 30.42% | 4.24% | 31.0 |
| sell_above_30pct_36d | 14.36% | -36.11% | 0.52 | 344 | 34.01% | 1.87% | 23.9 |
| wait_under_resistance | 33.54% | -40.06% | 0.89 | 294 | 29.59% | 5.17% | 27.8 |
| two_closes_above_resistance | 30.05% | -43.98% | 0.79 | 283 | 31.8% | 4.69% | 29.3 |
| sell_failed_breakout | 31.85% | -44.22% | 0.84 | 273 | 31.14% | 5.39% | 30.2 |
| wait_res_and_sell_failed | 26.64% | -35.58% | 0.78 | 300 | 30.0% | 4.1% | 27.1 |

S&P 500 buy and hold: CAGR 10.39%, max drawdown -25.43%.

Symbols: 109 · generated 2026-11-12T13:13+00:00
