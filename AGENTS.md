# InvestorAce decision behavior

The user requested the v17 opportunity methodology and, on 2026-11-04, its
review; v18 keeps its structure and changes the weights below.

- The main ranking and automatic five-label signal use `opportunity.py`:
  financial quality 45%, valuation/expectations 25% (FCF yield and reverse-DCF
  expectations 7.5% each, P/E 10%), current macro 15%, growth 10%, shareholder
  returns/dilution 5%. FCF yield and reverse DCF are both FCF / price; do not
  give them separate full weights again without new evidence.
- Show Strong Buy, Buy, Hold Positive, Hold Negative and Sell when supported
  by the calculation. A pending analyst review must not hide the automatic
  model label; show review status separately. Do not describe an automatic
  label as an independently approved purchase recommendation.
- Preserve defensive/cyclical/growth/income profiles and all five regime
  fits. Highlight the actual current regime from the dated macro snapshot.
  The macro component scores the fit weighted over the regimes the reading
  could be in (`macro.regime_weights`, calibrated one-month score spread);
  the regime itself is read from 21-session mean market impulses.
- Missing inputs remain unknown. A robust label can span a bounded partial
  score, but no midpoint score or neutral input is fabricated. Stale quotes
  withdraw price-dependent labels, including in an already-open browser.
- Keep legacy score APIs, frozen history, primary research, sources, alerts
  and open objections. Reconfiguration never resolves an old objection by
  assertion and never deletes Zoetis or other universe members.
- Antero Resources, Zoetis and WKL are calibration cases for behavior, not
  hardcoded recommendations. Commodity peak multiples do not substitute for
  multi-year valuation inputs. A low P/E alone is insufficient.

Implementation rationale and validation cases are in
`docs/superpowers/specs/2026-10-28-opportunity-score-design.md`.
