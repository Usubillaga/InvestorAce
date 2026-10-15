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

## Layout

| File | Role |
|---|---|
| `engine.py` | Data table, scoring, validation, HTML rendering, history snapshot |
| `wacc.py`, `epv.py`, `forward.py` | Discount rate, earnings power value, forward estimates |
| `macro.py`, `regime_contract.json` | Macro regime classifier and its frozen contract |
| `evidence.py`, `path_features.py`, `portfolio.py`, `framework_view.py` | Evidence/path diagnostics and portfolio proposal |
| `timing.py`, `decision_view.py` | Observation-only daily timing and exact score/regime explanations |
| `autoscore.py`, `add_ticker.py`, `verify_tickers.py`, `tickers.js` | Ticker onboarding and the ticker library |
| `integrity.py`, `reprice.py` | Build integrity checks, risk-free repricing tool |
| `research.py` | Offline feature research (not part of the build) |
| `weekly_research.py`, `weekly-research/` | Published research briefings, schema and dated archives |
| `test_*.py`, `tests/fixtures/` | Contract and regression tests |
| `history/` | Daily observations committed by the build bot — do not edit by hand |
| `docs/` | Framework spec, implementation notes, ten-stock plan |
| `docs/archive/` | Applied patches and their write-ups, kept for reference |

Not investment advice.
