# InvestorAce: evidence and path framework

Built from Usubillaga/InvestorAce commit `9b161971a3ad1402952f699bd2d4ffd489cfe91d`.
This local implementation does not publish to GitHub or place trades.

## Run

Use Python 3.11 or newer, from this directory:

```console
python -m pip install -r requirements-research.txt
python -m unittest discover -p "test_*.py" -v
python engine.py
```

The last command fetches market data and writes the dashboard and observations.
Open `index.html`. The existing dashboard remains, with a new **Evidence and path
diagnostics** section. It shows data availability, a separately defined business
quality heuristic, macro path direction/persistence, and a constrained portfolio
proposal. Existing score, NGV, EPV, risk, verdict and regime formulae are retained.
The table now calls the existing composite **Legacy Score**.

## What changed

| File | Responsibility |
| --- | --- |
| `evidence.py` | Explicit input status, declared cash-flow/rate matching, immutable observations and archived source |
| `path_features.py` | Descriptive dated paths and exact level-two piecewise-linear signatures |
| `portfolio.py` | Equal-slot proposal with sector/position limits and residual cash |
| `framework_view.py` | Separate diagnostic and proposed-portfolio panels |
| `research.py` | Offline comparison of level, simple-history and signature features |
| `engine.py` | One macro capture, validation/render before observation publication, diagnostics integration |
| `macro.py` | Archive fetched close series; common-date historical proxy paths |

The original regime constants and formula fingerprint are unchanged. Regression
tests compare the new calculations with a frozen copy of the upstream engine in
`tests/fixtures/upstream_engine.txt`, including 5,000 deterministic random inputs.
The original ten contract tests remain. Additional tests cover immutability,
replay, failed builds, path ordering, temporal leakage, constraints and costs.

## Evidence contract

- `history/runs/<timestamp>-<uuid>.json`: every validated run, append-only.
- `history/YYYY-MM-DD.json`: first validated observation for the UTC day. Reruns
  never replace it, including existing legacy snapshots. This keeps the current
  `forward.py` and frozen cohort compatible.
- `history/models/<hash>.json`: executable source and dependency declarations.
- `_evidence`: all row inputs, the exact macro object used for the report,
  capture time, universe identity, source identity and installed runtime versions.
- Each row has explicit availability and valuation-basis diagnostics.

A rerun can update the dashboard while the daily forward-test observation remains
the first observation of the day. Corrections are recorded as additional runs;
there is no automatic retrospective replacement. The report's forward panel reads
prior published observations; a newly created cohort appears on the next build.

Publication sequence is: acquire lock; fetch inputs; read macro once; validate and
serialise the record; render HTML in memory; publish model/run/daily records;
atomically replace HTML; freeze a cohort if none exists. Render/validation errors
leave the existing report and observation archive untouched. An HTML filesystem
failure after observation publication can leave a valid observation without a new
report; retry the build. These files are not claimed to be one filesystem transaction.
EPV cache updates during fetching are operational cache writes, not observations.

`history/_build.lock` prevents concurrent local builds. After a hard process crash,
check that no build is running before manually removing the stale lock. Immutable
publication uses same-filesystem hard links (supported by NTFS and the Linux Actions
runner); failures on unsupported filesystems stop the build instead of overwriting.

Do not infer publication dates for fundamentals that lack them. Quote retrieval
time and quote observation time are distinct; fast-info quotes have unknown exchange
timestamps unless a timestamped close fallback was used. A captured record becomes
known at capture time, not at the earliest date in its reconstructed price history.
The current forward test still measures its existing price-return definition; it
has not been converted into a dividend/corporate-action-aware portfolio backtest.

## Signal definitions

**Business Quality v1:** weighted growth, profitability, cash conversion, balance
sheet and dilution, renormalised using existing `W` weights. It excludes the static
valuation and payout subscores and the live priced-in component. It returns missing
when components are unavailable. It is an explicit heuristic, not a calibrated
probability, and does not change the legacy action rules.

**Valuation contract:** existing generic FCF rows remain `UNVERIFIED` until a
cash-flow basis, matching rate basis and dated fundamentals are supplied. No debt
bridge or rate change is silently applied to NGV. The separate opt-in
`declared_perpetuity()` API accepts FCFE/cost-of-equity or FCFF/WACC/net-debt inputs.
EPV retains the template formula; its capex-minus-depreciation adjustment is not
certified as an economic maintenance/growth split. Original EPV inputs are archived.

**Macro path:** all four market proxies are aligned by common dates. The last 63
available observations drive diagnostics. Persistence counts sampled sessions,
not months, and is marked censored if it extends to the start of the window.
Boundary distance is in percentage points, never labelled a probability.
The legacy classifier remains unchanged and can differ because it permits partial
inputs and uses each series' own trading observations. Market proxies are not GDP
or CPI releases. Reconstructed Yahoo histories can contain later corrections.

**Signature:** coordinates are normalised elapsed calendar time, growth and
inflation fractions. Level two retains ordered interactions. The growth/inflation
signed-area diagnostic changes when the order of moves changes even if their
endpoints agree. No trained signature strategy is enabled in the live engine.

**Portfolio proposal:** raw regime ranking is unchanged. The separate proposal
fills up to 10 equal slots with at most two names per sector; missing slots stay
in cash. Positive prices are required. Correlation, liquidity, tax and execution
constraints remain separate research requirements. This does not change holdings.
Entry, initial-stop and holding-period columns use the configurable rules in
`TEN_STOCK_PLAN.md`.

## Offline path experiment

```console
python research.py observations.csv --output research-output/report.json
```

Input CSV columns:

```csv
timestamp,known_at,price,growth,inflation,baseline_weight
2026-01-02T21:00:00+00:00,2026-01-02T21:00:00+00:00,100.0,2.1,1.3,0.5
2026-01-05T21:00:00+00:00,2026-01-05T21:00:00+00:00,101.0,2.2,1.4,0.5
```

This snippet illustrates the schema, not sufficient training data. Defaults need
at least 105 chronological observations to produce any out-of-sample output; useful
evidence needs substantially more. All rows must concern one instrument and one
consistent price/total-return index. `known_at` is when the signal inputs became
available; it must not exceed the decision timestamp. An earlier observation may
be carried forward only after publication. The code does not count distinct data
releases or claim repeated macro values are independent observations.

Optional `baseline_weight` is a genuinely frozen [0,1] allocation for the same
instrument. Supply it for every row or omit the column. This lets the experiment
compare an externally prepared InvestorAce baseline without inventing historical
InvestorAce scores. Built-in references are buy-and-hold and positive-window-momentum.

The experiment compares level features, simple history features and level-two
signature features with the same ridge regression and long-only [0,1] exposure
mapping. End levels are included because signatures remove starting levels.
All scaling is fitted on training data. Training feature/outcome windows end before
the current feature window begins. A signal at t executes at t+1 and earns the
t+1 to t+2 return. The fixed cost is charged on drift-aware notional turnover,
initial entry and final liquidation. It is a first-order execution-cost approximation.

Outputs include every decision, execution and outcome timestamp, training cutoff,
weights, turnover, net return, drawdown and descriptive Sharpe statistics. There is
no significance claim or automatic selection of the best model. Input/config hashes
are saved. Inspect performance stability across periods and instruments manually
before considering any live integration. Do not tune repeatedly on a final holdout.

This is a **signature-feature experiment**, not the paper's direct mean-variance
Sig-Trading optimizer or a demonstrated profitable strategy. The latter requires
additional estimation, execution and robustness work. There is no automatic
conversion of the existing short archive into a valid historical training sample.

## Installation into the existing repository

Copy the changed/new code files and this guide into a branch of the repository,
including the new tests and frozen fixture. Preserve the repository's existing
`history/` and `_cohort.json`. The accompanying patch is based on the commit above;
check it against any later upstream changes before applying.

The deploy workflow now runs all tests before building and refuses to continue
after a failed history push. No remote deployment has been performed here.

The downloadable source archive intentionally excludes production `history/` so
extracting it does not overwrite frozen observations. Tests include a separate
archived-data fixture. Keep your existing history when installing into the live
repository; a standalone fresh installation starts a new history.
