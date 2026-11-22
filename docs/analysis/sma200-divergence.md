# SMA200 entry buffer investigation

The one-percentage-point entry buffer remains under investigation. The original 2018–21 result was a CAGR advantage of 7.56 percentage points over v1.6. Rounded window aggregates alone cannot identify the orders responsible. The three-period adoption criterion continues to apply.

Each monthly backtest traces order plans and executed long lots inside the existing v1.6 and buffer simulations. It uses their shared downloaded price panel. The first different plan can precede the first different fill. For each symbol and entry date the JSON retains both sides, including differing sizes, signal-date distance above SMA200, entry cost, exit price or final carried mark, and net P&L. Trades opened on different dates are separate lots. Same-day alternatives and later buys are observable consequences of the simulated portfolio path. Individual substitutions are not assigned a causal probability.

Signed contributions sum to the difference in ending equity divided by initial capital (total-return percentage points). Annualized differences use compounding and cannot be summed by position. The two largest positive contributions are compared with all positive contributions before offsets. Matching 1%, 2% and 3% is checked against actual order plans and position records in each window.

## Deferred Monte Carlo risk measure

If the paper-account experiment is built, the primary event is at least one daily account close strictly below 90% of initial account value over 63 trading sessions. Ending below that level on session 63 is a separate secondary statistic. No trade threshold is set.
