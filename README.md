# InvestorAce

Investment strategy with friends: a scoreboard of stocks scored on the
InvestorAce framework (normalised gross value, EPV, WACC, risk, macro regime),
rebuilt nightly and published to GitHub Pages.

## How it runs

| Step | Where |
|---|---|
| Nightly build (weekdays 23:00 UTC): tests, then `python engine.py` writes `index.html` and `history/YYYY-MM-DD.json`, then deploys to Pages | `.github/workflows/deploy.yml` |
| Tests + lint on every push / PR | `.github/workflows/test.yml` |
| Add a ticker: open an issue titled `add-ticker: MSFT` (owner/collaborators only) or run the workflow manually | `.github/workflows/add-ticker.yml` |

## Local use

```console
python -m pip install -r requirements-research.txt
python -m unittest discover -p "test_*.py" -v   # offline
python engine.py                                  # fetches Yahoo data, writes index.html
python add_ticker.py ASML.AS                      # add a ticker row to engine.py
python reprice.py 4.40 5.04                       # NGV impact of a risk-free change
```

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
| `test_*.py`, `tests/fixtures/` | Contract and regression tests |
| `history/` | Daily observations committed by the build bot — do not edit by hand |
| `docs/` | Framework spec, implementation notes, ten-stock plan |
| `docs/archive/` | Applied patches and their write-ups, kept for reference |

Not investment advice.
