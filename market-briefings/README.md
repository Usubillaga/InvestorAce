# InvestorAce Montagsbriefing

The Monday market task publishes here and sends the briefing in chat in
Spanish, English and German. It runs around 08:00 Europe/Berlin and covers
macro regime changes, valuations, sector and earnings trends, with concrete
review implications for InvestorAce.

Monday and Friday have separate data folders, overviews and archives:

| Monday language | Overview | Dated archive |
|---|---|---|
| Español | market-es.html | market/YYYY-MM-DD-es.html |
| English | market-en.html | market/YYYY-MM-DD-en.html |
| Deutsch | market-de.html | market/YYYY-MM-DD-de.html |

The language selector and archive links preserve the selected language.
Existing Monday links at market.html and market/YYYY-MM-DD.html show German.
Friday's research remains under research.html and research/.

## Publication contract

Create exactly one UTF-8 JSON file market-briefings/YYYY-MM-DD.json on main
using the local Europe/Berlin issue date. Use the shared schema_version 1
fields, topic keys, review verdicts and confidence codes documented in
[the research schema](../weekly-research/README.md).

Write the canonical base fields in English, including summary, priority_review
and all item text. Keep verified original source titles in the canonical items.
Add translations.es and translations.de to the same JSON file. Do not create
translations.en: English is the canonical base, as in the Friday series.

Each translation contains summary, priority_review and an items array covering
the same items in exactly the same order. Each translated item must contain
source_url plus title, publication_date, what_changed, investorace_implication,
review_question and limitations. Repeat the exact canonical source URL to
verify item alignment. Monday items may also include authors as a translated
attribution; preserve the same personal and institutional identities.

Dates, coverage, URLs, topics, review verdicts and confidence codes remain shared
in the canonical edition. Never override metadata in translations. Preserve all
numerical values, signs, units, conditions, confidence labels and priorities;
decimal comma or point and the order of values may differ by language. Keep
the canonical inline tags [Sicher], [Wahrscheinlich] and [Vermutung] in JSON;
the pages display their native equivalents. Missing or misaligned languages,
changed numbers or confidence labels, or extra metadata stop publication.
See 2026-10-12.json for a complete example.

Use at most five items and keep each language's substantive text under 600
words. State the data timestamp and distinguish monthly, quarterly and weekly
comparisons. Read prior Monday editions to avoid unjustified repetition.
Friday does not determine the Monday coverage start. period_start and
period_end describe the last completed trading week; explicitly date material
newer developments. Quiet editions still require all three summaries and
priority statements, with empty item arrays.

Before writing, inspect the target file. Reuse an existing edition on retries;
never duplicate or overwrite concurrent work. Corrections must use the current
blob SHA. For routine publication commit only the dated JSON file. Do not
put Monday issues in weekly-research or change configuration, models, scoring,
regime fit, portfolio code, workflows or generated HTML.

## Build and deployment

python weekly_research.py --output public builds both series in all configured
languages, with separate latest editions and archives. The nightly build uses
the same publisher. Pushes to market-briefings/** trigger publish-weekly-research.
Verify the Actions build and successful Pages deployment before reporting a
release as live. If publication fails, still send all three versions in chat
and state the failure.

The first Monday issue moved from weekly-research/2026-10-12.json.
legacy_research_dates keeps its previously shared URL as a redirect to the
Monday archive; it does not include the issue in Friday's feed.
