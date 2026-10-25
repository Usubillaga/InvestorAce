# Main dashboard and dated company PDFs

The main report now leads with its snapshot summary and universe table. Search
accepts company/ticker and the displayed sector language. The holdings filter
and compact/all-columns toggle change presentation only: all original rows,
21 cells per row, sources, review data and portfolio payload remain present.
Market, research, portfolio and model/data panels are grouped in native details.
Without JavaScript, the full table and native sections remain usable.

Each main-table company has a PDF download in that page's language. Scanner
details offer English, German and Spanish PDFs for both universe companies and
outside market candidates. The two methods use separate paths:

- `analysis-pdfs/TICKER.LANGUAGE.pdf`: universe analysis.
- `analysis-pdfs/market/TICKER.LANGUAGE.pdf`: market screening analysis.

`company_pdf.render_pdf()` formats the exact frozen research packet without
fetching data, changing financial calculations or granting approval. Every PDF
contains the source/capture dates, financial periods, units, model inputs,
available valuation scenarios, original research, sources and recorded issues
and responses. Original research prose remains in its original language; report
labels are translated. PDFs are dated snapshots and do not update after download.
They are regenerated on the next successful site build.

Native financial amounts and full share counts are explicitly distinguished
from the engine's cash-flow/share inputs in millions. Saved market inputs are
labelled as archived, separate from the current replay status/metrics. The
captured assessment controls the recorded rating; missing optional metrics do
not create another approval rule. A missing value never means Sell.

`company_reports.pdf_pages()` builds every language/scope artifact. The scanner
CLI and `weekly_research.build_site()` publish the binary files atomically with
the matching page generation. ReportLab supplies embedded Unicode fonts; pypdf
is a test dependency only. No external PDF service, broker or account is needed.

## Verification

`tests/dashboard_pages.py BASE_COMMIT output-directory` renders before/after
reports from identical committed inputs. `tests/dashboard_browser.cjs` checks
all original text, links, 21-column rows, assessment JSON and private payload,
plus controls, translated searches, legacy portfolio entry, responsive charts
and no-JavaScript fallback. `tests/company_pdf_browser.cjs` tests real downloads
against a served build and checks every linked language/scope PDF endpoint.

This change was checked with 82 universe companies and 150 market candidates:
696 PDF artifacts. Representative PDFs were rendered to images for layout review.
The Python suite includes regressions for current/archived units and statuses,
retained objection responses, missing values, source links and pagination.
