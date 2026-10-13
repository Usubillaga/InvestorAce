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
| Add a ticker: open an issue titled `add-ticker: MSFT` (owner/collaborators only) or run the workflow manually | `.github/workflows/add-ticker.yml` |

## Local use

```console
python -m pip install -r requirements-research.txt
python -m unittest discover -p "test_*.py" -v   # offline
python engine.py                                  # fetches Yahoo data, writes index.html
python add_ticker.py ASML.AS                      # add a ticker row to engine.py
python reprice.py 4.40 5.04                       # NGV impact of a risk-free change
```

## Build integrity

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
| `autoscore.py`, `add_ticker.py`, `verify_tickers.py`, `tickers.js` | Ticker onboarding and the ticker library |
| `integrity.py`, `reprice.py` | Build integrity checks, risk-free repricing tool |
| `research.py` | Offline feature research (not part of the build) |
| `weekly_research.py`, `weekly-research/` | Published research briefings, schema and dated archives |
| `test_*.py`, `tests/fixtures/` | Contract and regression tests |
| `history/` | Daily observations committed by the build bot — do not edit by hand |
| `docs/` | Framework spec, implementation notes, ten-stock plan |
| `docs/archive/` | Applied patches and their write-ups, kept for reference |

Not investment advice.
