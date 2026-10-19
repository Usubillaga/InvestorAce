# InvestorAce daily politics and economy briefing

Publish the same evidence and conclusions in Spanish, English and German.
The scheduled task researches and writes each edition; GitHub Actions validates,
renders and deploys it. The publisher itself does not generate news.
Schedule: every day, including weekends, around 08:00 Europe/Berlin, starting
2026-10-18. This feed is separate from Monday's market briefing and Friday's
research notebook.

| Language | Latest edition | Dated archive |
|---|---|---|
| Español | daily-es.html | daily/YYYY-MM-DD-es.html |
| English | daily-en.html | daily/YYYY-MM-DD-en.html |
| Deutsch | daily-de.html | daily/YYYY-MM-DD-de.html |

daily.html and daily/YYYY-MM-DD.html show German. Navigation preserves the
selected language. Until the first edition, the overview explicitly says that
no edition has been published.

## Editorial contract

Exactly four sections, in this order:

1. **Regime impact:** inflation, growth/recession, stagflation, reflation and
   disinflation/Goldilocks as supported by the evidence. Explain the channel
   from policy to prices, demand, interest rates, earnings and valuations.
   A headline alone does not establish a regime change.
2. **United States:** unemployment and jobs, growth, inflation, Fed policy,
   fiscal/trade/immigration/regulatory decisions, Trump and other relevant
   political actors. Compare specific conservative and liberal proposals on
   the same economic criteria. Distinguish statements, proposals, enacted
   measures, implementation, litigation and observed outcomes. No partisan
   endorsement or unsupported attribution of market moves to a politician.
3. **European Union:** growth, inflation, ECB, war and energy/trade risks,
   fiscal policy and EUR/USD, including effects on European listed companies.
4. **Colombia:** growth, jobs, inflation, Banco de la República, fiscal and
   political developments, material security/institutional risks, and COP
   relative to EUR and USD.

Target 600–900 substantive words per language, approximately 3–5 minutes at
200 words/minute. The renderer shows the actual estimate. The upper limit is
validated for each language; quiet days can be shorter without padding. Include
what changed, the economic transmission channel and the next evidence to watch.
The final priority statement contains at most three concrete InvestorAce review
questions. Regime fit remains separate from fundamental score and sizing.

Research material developments since the previous daily cut-off; on the first
run use the past 24 hours plus clearly dated baseline context. Read the latest
published official data rather than treating old monthly statistics as today's
release. Distinguish publication date, reference period, market observation
time and retrieval time. On weekends use the last available market observation
and its date; never invent a new quote or daily change.

Use primary sources (BLS, BEA, Federal Reserve, official US measures; Eurostat,
ECB, EU institutions; DANE, Banco de la República, Colombian official measures)
and dated reputable reporting for verified political/war developments. Verify
current officeholders and the status of policy measures. Explain uncertainty
and conflicting evidence. Use [Sicher], [Wahrscheinlich] and [Vermutung] as the
canonical confidence tags; the website displays their local-language equivalents.

Show FX as **1 EUR = X USD**, **1 EUR = X COP** and **1 USD = X COP**, with
provider, observation date/time, and a comparable prior observation when
available. Make currency appreciation/depreciation explicit. If COP per EUR is
derived from COP per USD times USD per EUR, label it as derived and disclose
both observation times; do not silently mix dates or quote directions. Mark
unavailable observations instead of inserting estimates as facts.

No private holdings or conversation details in the public report. This task
publishes commentary; it does not change model rules, scores, regime-fit
formulas, portfolio allocations or execute trades.

## JSON publication contract

Read [the shared schema](../weekly-research/README.md) and the most recent daily
edition before publishing. Create exactly one UTF-8 file
daily-briefings/YYYY-MM-DD.json on main, using the Europe/Berlin issue date.
Base schema_version 1, period_start, period_end, summary, priority_review and
items follow the shared schema. English is canonical; include translations.es
and translations.de with the exact shared translation shape. Do not create
translations.en. All three languages must preserve numbers, signs, confidence
tags, sources, facts, policy status, comparison periods and conclusions.

Daily additions and constraints:

- data_cutoff: ISO 8601 research cut-off with an explicit UTC offset; it must
  fall on issue_date in Europe/Berlin. period_end must equal issue_date.
- items: exactly four shared-schema objects, with additional section values
  regime, usa, eu and colombia in that order. Each title is the section's main
  finding, not an assertion that its leading source covers the entire section.
- Each item has sources: one to eight objects with title, url and
  publication_date (ISO date). Original source titles remain shared across
  languages. The section's source_url must be one of these URLs. Use an
  actual dated publication or market snapshot, not an invented document.
  Reference supporting sources in prose by institution/date where needed.
- Shared item publication_date may describe the dated evidence covered by the
  section. authors attributes the sources, not a private user or conversation.
- Use existing topic keys and review/confidence codes. Normal daily commentary
  usually has topics ["macro_regimes"] and review "framework" or "neither".
- what_changed contains verified data/policy with dates and reference periods;
  investorace_implication contains the transmission/analysis; review_question
  contains the next checkpoint; limitations discloses uncertainty/stale data.
- Even with no material change, preserve all four sections and state that
  honestly, carrying forward only clearly dated baseline observations.

The tests' daily_example() demonstrates the payload structure with **synthetic
test evidence**; never publish that fixture as news.

Before writing, read the target path. Reuse an existing valid edition on
retries; do not duplicate it or overwrite concurrent changes. Corrections use
the freshly read blob SHA. Routine publication commits only that day's JSON.
The user's request authorizes these recurring publication commits. Do not
modify publisher code, configuration, other reports or generated HTML during
a routine run.

## Verification and deployment

Run python -m unittest test_weekly_research test_daily_briefing -v and
python weekly_research.py --output research-output --require-committed-report.
All daily editions, translations, source links and word limits are checked
before writing an uploadable site; malformed content must not replace a valid
site. Pushes to daily-briefings/** trigger publish-weekly-research, using the
same Pages lock as the scoreboard. Verify the successful Actions publication
and Pages deployment before calling the report live. Send the user the three
dated links; if publishing fails, deliver the report in chat with the exact
failure instead of claiming success.
