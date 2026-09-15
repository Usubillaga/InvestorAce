# Ten-stock entry and exit planning

## Install this update

Extract `InvestorAce-10-stock-update.zip` into the repository root and commit its
contents, preserving directories. It updates `portfolio.py`, `framework_view.py`
and `engine.py`, adds the portfolio-plan tests, and includes both required fixtures
to avoid the earlier missing-file failure. It requires the previous evidence/path
framework modules already installed in the repository.

Run `python -m unittest discover -p "test_*.py" -v`, then rebuild with `python engine.py`.
No live website or GitHub repository has been changed by this local update.

## Defaults

| Setting | Default |
| --- | --- |
| Number of proposed stocks | 10 |
| Maximum per sector | 2 |
| Planned weight per filled slot | 10% |
| Buy limit | Lower of reference quote and existing NGV / 0.60 entry ceiling |
| Initial stop | 10% below planned entry; anchor to actual fill when purchased |
| Holding plan | 90–180 calendar days after actual fill |
| Review | Every 30 calendar days; sooner on regime/thesis changes |
| Entry-plan validity | 7 calendar days; refresh before using a later entry |

The NGV threshold means 60% cover, not a 60% discount. If the reference price exceeds
the ceiling, the table says **Wait for pullback**. A quote below the ceiling is not
a guarantee of an available fill. An unavailable ceiling or currency produces no
entry/stop estimate. The raw regime ranking and legacy scoring formulae are unchanged.

For example, a reference quote of 100 with an NGV entry ceiling of 80 produces a
buy limit of 80 and an initial stop of 72. With an actual fill of 78, the stop is
70.20. Currency is the listing's quote currency, including GBp where applicable;
confirm the broker's price increment before entering any order.

The fixed 10% stop and 90–180-day horizon are configurable heuristics. They have
not been optimised or validated as profitable for these stocks. The stop may
trigger before the holding period. At 180 days, reassess rather than assume an
automatic profitable exit. Stops can fill below their trigger during gaps; see
[Investor.gov](https://www.investor.gov/introduction-investing/investing-basics/glossary/stop-order).

These columns describe proposed **new entries**, including when the same ticker
is already held. They do not manage active positions or broker orders. Save the
actual fill and its initial stop separately; never lower an existing stop simply
because the dashboard refreshes. `portfolio.filled_plan(plan, fill_price, filled_on)`
returns a fixed initial stop and dated reviews for explicit position tracking.
It does not submit or persist an order.

Ten slots allocated does not mean ten positions have been purchased. Until entry
conditions are met and orders filled, the corresponding allocation remains cash.
At 10% allocation with a 10% stop distance, the planned price loss is 1% of the
portfolio per position before fees/gaps/FX; that is not a guaranteed loss limit.

To change assumptions, edit `DEFAULT_POLICY` in `portfolio.py`, for example:

```python
DEFAULT_POLICY = TradePolicy(stop_loss_pct=0.10, holding_min_days=90,
                            holding_max_days=180, review_every_days=30,
                            entry_valid_days=7)
```

The separate legacy 30-name raw-regime reference list is retained. The section
named **Constrained portfolio proposal** is now the ten-stock planning book.
