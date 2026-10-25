# Organize the main InvestorAce page without losing information

The user explicitly requests a clearer main page and preservation of all
information. This extends the authorized InvestorAce improvement; implementation
choices are delegated. Preserve the current dark visual identity and all three
languages. Work on a new branch; the user merges the pull request.

Chosen approach: a short snapshot header followed immediately by the full
universe table in a bounded scroll area. Search and a holdings filter help find
rows. A compact column view has a clear all-columns toggle; the full 21-column
table remains in the document. Below it, native expandable sections group market
context, analysis/timing, portfolio access and data/model controls. A short section
navigation links to each group. Existing research navigation remains available.

Alternatives: cosmetic spacing alone leaves the information hierarchy unchanged;
moving detail to new pages makes source and historical links harder to preserve.
Grouping the existing panels in place is the smallest useful change.

All original panels, cells, sources, warnings, hidden portfolio payload and
assessment JSON remain present. Search only changes row visibility. Compact
mode only changes column visibility. Neither changes financial calculations,
rankings, holdings, analyst approval or date/expiry behavior. Important review
status remains visible in compact rows. Without JavaScript the full table and
native sections remain usable. Navigation opens a linked collapsed section;
charts resize when sections become visible. Mobile scrolling stays inside tables.

Validation: compare rendered text, financial cells, assessment JSON and portfolio
payload before/after with the same committed inputs. Exercise search, holdings,
reset, all-columns toggle, section links and mobile layout in Chromium; rerun
existing approval-expiry and language checks. Run full tests and obtain one fresh
code review before creating an unmerged PR.

## User extension: company PDFs

The user also explicitly requests downloadable company analyses. Generate real
PDF files from the same frozen review packets used by the page. Main-page row
links download that edition's language; scanner details offer all three
languages. Universe and market-screening PDFs use separate paths, even for the
same ticker, and reflect their distinct data/methods. Include dated inputs,
current calculations/assumptions, research, sources and outstanding issues;
missing values remain unavailable. Original research language stays identified.
No live refresh, recomputation or automatic approval occurs during export.

Render with embedded Unicode fonts from ReportLab's own package and validate
layout and text. PDF creation is part of the existing consistent site build;
binary files are atomically written into its output. No archives/ZIP downloads.
