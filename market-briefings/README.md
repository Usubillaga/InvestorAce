# InvestorAce Montagsbriefing

The Monday market task publishes here and sends the same briefing in chat.
It runs around 08:00 Europe/Berlin. It covers macro regime changes, valuation,
sector and earnings trends, with concrete review implications for InvestorAce.

This series is separate from Friday's research shortlist:

- Monday overview: https://usubillaga.github.io/InvestorAce/market.html
- Monday archive: https://usubillaga.github.io/InvestorAce/market/YYYY-MM-DD.html
- Friday overview: https://usubillaga.github.io/InvestorAce/research.html

## Publication contract

Create one UTF-8 JSON file `market-briefings/YYYY-MM-DD.json` on `main`, using
the issue's Europe/Berlin date. Use the schema_version 1 fields, allowed topics,
review verdicts and confidence labels documented in
[the research schema](../weekly-research/README.md). Use at most five items and
keep substantive text under 600 words. Include a clear data timestamp, distinct
monthly/quarterly comparison periods, evidence limits and source links.

Read existing Monday editions to identify the last market briefing and avoid
unjustified repetition. A Friday edition does not define the Monday coverage
start. `period_start` and `period_end` describe the last completed trading week;
date any material newer developments explicitly in the text.

Before writing, inspect the target file. Reuse an existing edition on retries;
never create duplicates or overwrite concurrent work. Any correction must use
the currently read blob SHA. Commit only the dated JSON file for routine
publication. Do not place Monday issues in `weekly-research` or change market
models, scoring, regime fit, portfolio code or generated HTML.

## Build and deployment

`python weekly_research.py --output public` builds both series with independent
latest editions and archives. The nightly build uses the same publisher, so
it includes both sections too. Pushes to `market-briefings/**` trigger
`publish-weekly-research`. Verify the Actions build and successful Pages
deployment before reporting a release as live. If publication fails, still
deliver the briefing in chat and state the failure.

The first Monday issue moved from `weekly-research/2026-10-12.json`.
`legacy_research_dates` keeps its previously shared archive URL as a redirect
to the Monday archive; it does not include the issue in Friday's feed.
