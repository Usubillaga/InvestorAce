# Score explanations and observational timing

Approved in conversation: implement the review's explainability approach and a
minimal experimental timing view; retain all existing investment decisions.

- Preserve DATA, score(), risk(), verdict(), all five regime formulas, rankings,
  entry ceilings and portfolio construction. No technical points, trading gate,
  automatic sales, new stops or allocation changes.
- Show the eight existing category assessments, nominal/effective weights and
  exact contributions. Published-total fallbacks must never invent categories;
  missing priced-in expectations must expose the existing renormalisation.
- Show the existing five-regime components, raw sum and clamped/rounded total.
- Calculate a 200-session SMA and signed extension from the 21-session EMA in
  Wilder ATR(14) units, using the existing adjusted daily momentum history pull.
  The EMA is the extension reference, not another vote or scored signal.
- Require 200 valid completed bars. Conservatively exclude the current exchange
  local date and later dates, even after market close; no exchange calendar is
  inferred. Use SMA-seeded EMA and mean-seeded Wilder ATR, starting TR at H-L.
- Reject nonfinite/nonpositive OHLC, impossible ranges, naive or duplicate daily
  dates and unordered eligible dates. Never fill gaps or reuse a prior run.
  Zero ATR leaves extension unavailable. More than 7 calendar days of lag is
  explicitly stale; this is an operational flag, not a trading threshold.
- Record version, parameters, adjusted-price basis, provider, calculation time,
  last bar, input hash, raw indicator values and availability reasons. Archive
  the observation and source through the existing paired publication mechanism.
  Raw OHLC is not archived; the hash identifies the retrieved input window.
- Keep timing visibly experimental and descriptive, without buy/sell language
  or claimed return improvement. Preserve existing momentum calculations.
- Add offline regression tests, causal-prefix checks, a full report smoke test
  and visual checks. Historical evidence and generated reports are not edited.

Research adoption remains separate: compare the current policy, a simple trend
candidate and a Supertrend candidate on point-in-time data, with execution lag,
cost/tax/cash-yield scenarios, untouched periods and exposure-matched baselines.
This feature only begins collecting prospective observations.
