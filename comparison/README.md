# Stock comparison

`compare.html` is a separate, responsive InvestorAce page with two stock selectors,
English/German/Spanish controls, 29 metrics, annual history, shareable URLs and CSV
export. The published selectors and JSON are projected onto the **frozen universe
of the paired scoreboard build**. Market-scanner candidates never enter it.

## Data and definitions

`stock_compare.py --refresh` fetches Yahoo Finance through the project's pinned
yfinance version and writes `comparison/latest.json` atomically. The publishing
builder reads this snapshot without network requests or importing the engine.

- Annual income statements anchor up to four fiscal years. Balance-sheet and
  cash-flow values must have the identical fiscal-year-end date; missing years
  are not substituted. Annual reporting currency comes only from
  `financialCurrency`, never from a quote currency or the valuation model.
- All saved monetary amounts use base currency units; share counts use shares.
  The UI displays millions, while CSV exports base units and each currency.
- FCF = operating cash flow minus absolute capital expenditure. It is separate
  from the engine's sustainable FCF, mid-cycle FCF, AFFO and DCF assumptions.
- Net debt = total debt minus cash, equivalents and short-term investments;
  cash and equivalents alone are used when the broader line is unavailable.
  The provider's debt and lease definitions may differ between companies.
- Dilution = YoY change in diluted weighted-average shares, requiring adjacent
  annual periods. Changes of at least 3× or at most one third are withheld for
  corporate-action review. This does not establish gross issuance or the full
  effect of unissued awards. Stock compensation is a separate metric.
- Outstanding shares and float use a separately identified provider snapshot.
  Retrieval time is **not** an issuer observation date. Float above outstanding
  shares is flagged and its percentage withheld. Multi-class and ADR definitions
  still require review even when the arithmetic is plausible.
- Negative values and zero remain distinct from missing values. Financial dates,
  currencies, source links, stale data and provider inconsistencies are visible.
  No investment score, regime fit, model input or portfolio weight is changed.

## Refresh and failure handling

The existing weekday build refreshes at most 16 stocks per run, reusing successful
snapshots younger than seven days. Older or missing data is prioritized. This
limits provider requests and rotates the universe across runs. Attempt timestamps
are tracked separately from data retrieval, so persistent failures cannot starve
unattempted stocks. New symbols and
provider failures can leave fields unavailable. A failed refresh preserves the
last usable snapshot, its original timestamp and an explicit failure warning.
Partial transport failures also preserve the previous usable snapshot instead of
replacing complete fields with blanks.
Changing a listing invalidates the old security's cache. Data older than 14 days
is flagged by the page. The first collection is committed so the page is usable
on deployment.

These are aggregated provider statements, **not fully audited primary-source
financials**. Annual reporting dates differ; currencies are not converted and
unreported values are not estimated.

## Verification

```bash
python -m unittest discover -p 'test_*.py'
node --check compare.js
python weekly_research.py --output research-output/comparison --require-committed-report
node tests/comparison_browser.cjs
```

The optional browser check uses Playwright and accepts `COMPARE_BROWSER_EXECUTABLE`
and `COMPARE_PAGE`. It exercises both selectors, URL membership restrictions,
period selection, translation, currency labels, negative numeric CSV exports
and 320–390px mobile layouts.
