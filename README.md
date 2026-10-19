# InvestorAce

Investment strategy with friends: a scoreboard of stocks scored on the
InvestorAce framework (normalised gross value, EPV, WACC, risk, macro regime),
rebuilt nightly and published to GitHub Pages.

## How it runs

| Step | Where |
|---|---|
| Nightly build (weekdays 23:00 UTC): tests, then `python engine.py` commits a report/evidence pair and deploys its verified report to Pages | `.github/workflows/deploy.yml` |
| Tests + lint on every push / PR | `.github/workflows/test.yml` |
| Friday research briefings and dated archives; publishes immediately when a new edition is committed | `.github/workflows/research-pages.yml`, `weekly-research/` |
| Add a ticker: an `add-ticker: MSFT` issue (owner/collaborators only) or manual run produces a tested draft PR for review; no direct main/report update | `.github/workflows/add-ticker.yml` |

## Local use

```console
python -m pip install -r requirements-research.txt
python -m unittest discover -p "test_*.py" -v   # offline
python engine.py                                  # fetches Yahoo data, writes index.html
python add_ticker.py ASML.AS                      # add a ticker row to engine.py
python reprice.py 4.40 5.04                       # NGV impact of a risk-free change
```

## Aktien-Scanner

`scanner.html` has two lists that are never mixed:

- **Gesamtmarkt USA** (default tab): `market-scan/latest.json`, written every
  Saturday by `.github/workflows/market-scan.yml` (`market_universe.py`). It
  starts from every NYSE/Nasdaq company in the SEC ticker list, applies hard
  filters on SEC XBRL frames (revenue >= 1 bn USD, operating profit, positive
  FCF) and prices the survivors with dated Yahoo closes. Walking down that
  pre-score ranking it skips banks, insurers and REITs (SIC 6000–6799) until
  the shortlist is full, flags 20-F/40-F filers (ADS share counts) and
  rebuilds trailing twelve months per company from SEC companyfacts (last
  fiscal year + current YTD − prior YTD, identical windows for every measure).
  The screening score uses autoscore's bands and the engine's eight weights
  with a flat 8 % rate: a mechanical draft for the research list, not an
  InvestorAce model score. Candidates already in `engine.py` are marked; new
  ones link to the existing `add-ticker` issue workflow. Europe is not covered
  yet. Offline contracts: `python -m unittest test_market_universe -v`.
- **Mein Universum**: the existing InvestorAce universe as before.

The existing lists now replay the saved numerical inputs through
`market-screen-evidence-gates-v2`. Unknown debt, capex, growth, D&A or dilution
does not become zero or five points. All eight components remain visible;
missing contributions are null, their weights are not redistributed, and no
composite/band is assigned until every category is supported. The data-review
filter exposes partial rows rather than calling them Sell. Prior draft scores
remain separately archived; existing engine scores and WKL/DIS objections are
not overwritten. A complete mechanical screen still has no approved rating.

SIC classification, a documented ADS/diluted-share bridge and commodity
mid-cycle normalization gate the affected valuation categories. An explicit
`VERIFIED` normalized FCF (including zero), evidence URLs and corresponding
denominator metadata support a reviewed input path; a URL alone does not
authenticate that assertion. Reported FCF capitalized at 8% is labeled a
scenario rather than verified NGV. Untagged dividends stay unknown. Where the
known share-reduction proxy already reaches the top Returns curve, that
category is proven invariant to any additional nonnegative dividend rather
than assuming a zero dividend. It is not a cash-buyback measurement.

Each page build checks market quotes against 96 hours, conservatively from
00:00 UTC on the daily close date; no exact exchange timestamp is invented.
Missing, future or expired quotes withdraw current price-dependent categories
per company. A weekday 23:13 UTC quote-only run updates saved candidates and
replays their scores without re-dating the weekly financial scan. Failed
quotes are recorded, and a successful later refresh clears that quote failure.
Run it with `python market_scanner.py --refresh-market-quotes`; no SEC calls
are made. The full SEC discovery scan remains weekly.

**One-time setup:** the SEC requires a real contact address in the
User-Agent and refuses GitHub noreply addresses with 403. Add the repository
secret `SEC_USER_AGENT` (Settings → Secrets and variables → Actions), e.g.
`InvestorAce Firstname Lastname name@domain.tld`. Without it the scan stops
before its first request and says so on the pull request. A manual live run:
`SEC_USER_AGENT="…" python market_universe.py --output market-scan`.

The regime column defaults to the regime the engine read at capture time
(`_evidence.macro.regime`), not to a fixed choice.

The universe list ranks the unrounded, archived engine score and keeps regime
fit separate. The five unchanged model bands are Strong Buy (>=8.50), Buy
(>=7.00), Hold positiv (>=5.50), Hold negativ (>=3.50) and Sell (<3.50).
Missing scores are never classified as Sell. These are provisional model bands,
not completed investment-committee ratings.

The scanner reads only the hash-verified committed generation resolved by
`evidence.current_build()`; it does not import/fetch live engine data, rewrite
inputs, recalculate scores or use a potentially stale root HTML mirror.
Source status, quote timestamp, fixed-total provenance, valuation-basis gaps,
normalization and recorded analyst objections are visible for each candidate.
`scanner_notes.json` holds dated research theses, counterarguments and unresolved
objections; these notes do not change the scores. The CSV export contains only
the current filtered selection and marks every model band as unreviewed.

A fetched quote with an unknown exchange timestamp cannot pass the 96-calendar-
hour freshness policy. Retrieval time is not substituted for market time. A
source marked `SOURCE_CHECKED` does not certify normalized FCF or a completed
cross-review. Current ratings and valuation outputs remain null until a
subsequent explicit, evidenced cross-review supports them; archived model
calculations are separately inspectable. This version deliberately produces
research candidates, not automatic purchase approvals.

The normal Pages build creates `scanner.html` and `scanner.json`, adds a
scoreboard navigation link, and includes future notes/assets changes in its
deployment trigger. For an offline standalone copy:

```console
python market_scanner.py --output research-output/scanner
python -m unittest test_market_scanner -v
```

The optional `node tests/scanner_browser.cjs` check requires Playwright and a
Chromium installation. It checks filters, stable ordering when the regime
changes, WKL/DIS objections and responses, filtered CSV, standalone JSON,
form reset and mobile overflow. `SCANNER_BROWSER_EXECUTABLE` can select an
existing browser; `SCANNER_PAGE` can select another generated HTML file.

## Growth comparisons and review status

`deliver` is expressed in percentage points. Only an explicit
`deliver_basis='CASH_FLOW'` permits `deliver - 100 * implied_growth` to enter
the cushion and its existing penalties. Revenue, bookings, ARR, production,
earnings and untyped metrics remain descriptive; they do not produce a
cash-flow cushion. The existing mid-cycle producer exclusion and 0.5pp
tolerance remain. Metric typing does not verify a source, establish the
cash-flow/rate contract or certify normalization.

The existing labels in `DATA` are typed without changing their numbers. ENB's
declared DCF/share CAGR retains the cash-flow comparison; ambiguous PFE
guidance remains `UNSPECIFIED`. NFLX retains its draft Yahoo inputs and is
marked `REVIEW_REQUIRED`; its primary cash-flow bridge, period, publication
date and share-count date still require review. Main-table badges expose
unverified valuation contracts and noncomparable growth beside the signal.
The growth contract and its model version are archived with each new build.
Historical generations and the frozen regime contract are unchanged.

Ticker automation tests and validates its candidate before pushing a new
branch, opens a draft PR, and explicitly dispatches `test.yml` because a
`GITHUB_TOKEN` push does not trigger push workflows. Enable **Allow GitHub
Actions to create and approve pull requests** in the repository's Actions
settings for this flow. Review and merge are separate human actions. Configure
a main-branch ruleset requiring the `test` check and pull requests to enforce
that policy for every writer; workflow changes alone cannot protect main.
Model, rendering, dependency, fixture and workflow changes on main trigger the
tested deployment; generated history-only commits do not retrigger it.

## Build integrity

### Score explanations and experimental entry observations

The report has a separate, collapsed inspection view for the eight existing
score categories, nominal/effective weights, contributions and all five regime
component sums. Published-total fallbacks disclose that category splits are
unavailable. Missing priced-in expectations expose the existing 0.85
renormalisation. These explanations do not validate the underlying financial
assessments or change their formulas.

`timing.py` consumes the existing adjusted 13-month daily momentum history
request. It records SMA(200), SMA-seeded EMA(21), Wilder ATR(14), distance from
SMA(200), and `(adjusted close - EMA21) / ATR14`. EMA21 is the extension
reference, not another trend vote. No technical score, entry gate, automatic
sale, stop or allocation rule is introduced; legacy momentum remains unchanged.

Timing uses only dates strictly before the calculation's exchange-local date,
even after today's market close. This conservative policy can lag one completed
session. It requires 200 valid bars; it never fills invalid prices or reuses
the last successful run. Zero ATR leaves extension unavailable and more than
7 calendar days of lag is flagged stale. These are availability policies, not
calibrated trading thresholds. Source, price basis, parameters, timestamps,
raw indicator values and the eligible-input hash are frozen in each new paired
observation. Raw OHLC is not archived and provider adjustments may change on
refetch. Existing immutable history is not backfilled.

The experiment also displays dated technical BUY/SELL events. A BUY requires
previous close <= previous EMA21, current close > current EMA21, and current
close > current SMA200. A SELL requires previous close >= previous SMA200 and
current close < current SMA200. Crossings use completed bars and require 201
valid bars; 200 bars still permit the existing indicator observations. No new
crossing is shown as a distinct status rather than repeating an older signal.
The most recent event within 20 completed sessions is labelled separately as
history, with its date and age. Stale, partial or unavailable inputs suppress
current signals. Archived v1 observations are not reconstructed or backfilled.
These alerts do not place trades, resize positions or alter the fundamental
verdict, score, regime fit or portfolio rules.

The timing view is descriptive and experimental. Adoption requires separate
point-in-time research comparing current decisions with simple-trend and
Supertrend candidates, delayed fills, costs/tax/cash-yield scenarios, untouched
test periods and exposure-matched benchmarks. No return improvement is claimed.

Required modules import normally: a missing module, missing export or broken
implementation stops the build with its original traceback. Numeric row inputs
are checked before valuation arithmetic. Missing data remains missing; a row
without a positive finite quote displays `NO QUOTE` and is excluded from the
default action screens. Quote coverage and manual WACC fallbacks are reported
in both the HTML and observation; sanity-band and currency rejections remain
visible rather than being silently accepted.

Filing-monitoring gaps appear as `FILING GAP` badges beside affected tickers,
with dated reasons, primary-source links and a concrete next review. The
`monitoring_status.json` register is a source-coverage diagnostic: it does not
change financial inputs, scores, regime fit, rankings or portfolio rules. An
absent entry does not certify complete coverage. Mark a gap `RESOLVED` only
after the missing source interval has been checked; restoring one directory
head alone is insufficient. Update the register only when the documented
coverage status changes, rather than committing every repeated check.
The build rejects removal of an active ticker's unresolved warning against the
previous committed generation; publish its explicit `RESOLVED` state first.

The register is included in each model-source bundle and observation so old
reports retain their own check status. A change to the register on `main`
triggers the regular tested build and Pages deployment; old history files and
committed reports are never edited to insert new labels.

Each report build stages `index.html`, `observation.json` and a hash manifest
under `history/_builds/`. The atomic replacement of `history/_current.json`
commits that complete pair. `evidence.current_build()` verifies the report,
observation and archived model before returning the report path used by Pages.
Only generations reachable from that pointer feed the daily forward evidence;
pending or abandoned builds are ignored. The first capture per UTC day and
existing legacy daily files remain unchanged.

Root `index.html`, `history/YYYY-MM-DD.json` and `history/runs/*.json` are
compatibility mirrors written after commit. A mirror write failure is reported
explicitly and may leave that mirror stale; deployment and the forward harness
use the committed generation instead. Run the build from the repository root.
The build lock must be held when calling `evidence.publish_build()` directly.

## Interface languages

The scoreboard has English, German and Spanish variants at `index.html`,
`index.de.html` and `index.es.html`. The language control uses ordinary links,
so selection works without JavaScript. Briefing and research pages link back
to the scoreboard in their selected language. Interface text, experimental
signal labels, tooltips and chart labels are translated. Original issuer
source wording remains identified as original text; ticker symbols, source
URLs, financial values, quote units and calculation contracts are preserved.

`i18n.py` and its `i18n_data.py` catalog apply presentation-only translations to
the canonical English HTML.
`weekly_research.py` derives all three scoreboards from the same verified
report and prepares every translation before writing the site. Translation
does not fetch market data, recalculate a score or modify archived evidence.
The English report/evidence pair remains the build's verified source.

## Daily politics and economy

The daily briefing is a separate series at `daily.html`, with complete Spanish,
English and German editions at `daily-es.html`, `daily-en.html` and
`daily-de.html`. It covers regime impact, the United States, the European Union
and Colombia, including politics, employment, risks and dated FX observations.
Each language targets a 3–5 minute read. Dated archives preserve the selected
language. The scheduled task starts on 2026-10-18, around 08:00 Europe/Berlin,
including weekends. Monday's market briefing and Friday's research keep their
own pages and archives.

Read [the daily editorial and publication contract](daily-briefings/README.md)
before adding a dated JSON edition. All four sections, evidence links,
timezone-aware cut-off, three translations and reading budget are validated
before deployment. Until a real edition exists, the page shows the schedule.

A second daily edition written by Claude is published beside it at
`claude-daily.html` (`claude-daily-es.html`, `-en`, `-de`) so the two can be
compared. It follows the same four-section contract without the word limit;
see [claude-briefings/README.md](claude-briefings/README.md).

## Layout

| File | Role |
|---|---|
| `engine.py` | Data table, scoring, validation, HTML rendering, history snapshot |
| `wacc.py`, `epv.py`, `forward.py` | Discount rate, earnings power value, forward estimates |
| `macro.py`, `regime_contract.json` | Macro regime classifier and its frozen contract |
| `evidence.py`, `path_features.py`, `portfolio.py`, `framework_view.py` | Evidence/path diagnostics and portfolio proposal |
| `timing.py`, `decision_view.py` | Experimental dated timing alerts and exact score/regime explanations |
| `i18n.py`, `i18n_data.py` | English, German and Spanish interface and language navigation |
| `autoscore.py`, `add_ticker.py`, `verify_tickers.py`, `tickers.js` | Ticker onboarding and the ticker library |
| `integrity.py`, `reprice.py` | Build integrity checks, risk-free repricing tool |
| `research.py` | Offline feature research (not part of the build) |
| `weekly_research.py`, `weekly-research/` | Published research briefings, schema and dated archives |
| `market-briefings/`, `daily-briefings/`, `claude-briefings/` | Separate Monday market and daily politics/economy editions (ChatGPT and Claude) |
| `test_*.py`, `tests/fixtures/` | Contract and regression tests |
| `history/` | Daily observations committed by the build bot — do not edit by hand |
| `docs/` | Framework spec, implementation notes, ten-stock plan |
| `docs/archive/` | Applied patches and their write-ups, kept for reference |

Not investment advice.
