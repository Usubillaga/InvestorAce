# Backtest of the technical rules · 2021-11-11 → 2026-11-11

Technical rules only (no InvestorAce label, which has no history); universe = today's members (survivorship bias lifts every variant alike). Decide on close t, fill at close t+1, 0.10% per fill. Compare the variants with each other.

## 1 · After a close far above the 36-day average

| Distance to 36-day avg | days | stocks | 21-day mean | 63-day mean | 63-day vs S&P | P(−10% within 21 d) | P(63 d < 0) |
|---|---|---|---|---|---|---|---|
| -100..0% | 61170 | 110 | 1.35% | 4.54% | 1.17% | 26.57% | 46.87% |
| 0..10% | 52006 | 110 | 1.04% | 3.12% | 0.38% | 20.23% | 47.37% |
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

S&P 500 buy and hold: CAGR 10.39%, max drawdown -25.43%.

Symbols: 110 · generated 2026-11-12T13:12+00:00
