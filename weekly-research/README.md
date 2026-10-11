# InvestorAce weekly research

The existing ChatGPT Friday task researches and publishes each briefing here.
It runs around 08:00 Europe/Berlin, starting 2026-10-16, and also sends the
shortlist in chat. GitHub Actions only validates and renders the submitted
content; it does not generate research or require an API key.

## Publication contract

Create one UTF-8 JSON file `weekly-research/YYYY-MM-DD.json` on `main`, using
the issue's local Berlin date. Read this document and existing editions before
publishing. A retry must reuse the issue file rather than create a duplicate.
Use `schema_version: 1`, at most five items, and all the fields below.

```json
{
  "schema_version": 1,
  "issue_date": "YYYY-MM-DD",
  "period_start": "YYYY-MM-DD",
  "period_end": "YYYY-MM-DD",
  "summary": "Brief explanation of the week's material findings, or lack of them.",
  "items": [
    {
      "title": "Verified source title",
      "authors": "Author or institution",
      "publication_date": "Verified publication or substantial revision date; state any date uncertainty",
      "source_url": "https://primary-source.example/paper",
      "topics": ["stock_selection"],
      "what_changed": "New result or substantive change, distinguished from familiar claims.",
      "investorace_implication": "Why this could improve or challenge the framework; label inference.",
      "review": "code",
      "review_question": "Concrete code or framework review question/test, or why no review is needed.",
      "limitations": "Material evidence limitations and source-access limitations.",
      "confidence": "Wahrscheinlich"
    }
  ],
  "priority_review": "Highest-priority review candidate, or no review warranted."
}
```

Allowed `topics`: `stock_selection`, `valuation_reverse_dcf`,
`portfolio_construction`, `macro_regimes`. Use one or more as applicable.
Allowed `review`: `code`, `framework`, `both`, `neither`.
Allowed `confidence`: `Sicher`, `Wahrscheinlich`, `Vermutung`.
Do not invent exact source dates. Clearly identify substantive revisions of
previously covered sources. On quiet weeks use `items: []` with an honest
summary and priority-review statement. Keep the substantive text under 600 words.

Read the latest existing edition to determine the coverage start; use the prior
seven days for the first edition. Verify links and dates through current web
research. Avoid duplicate sources within an issue and repeated coverage across
issues unless there is a material revision.

Commit only the issue JSON for routine publication. The authorized destination
is the public InvestorAce site; do not include private portfolio details or
conversation history in editions. Research verdicts are review proposals;
publication does not authorize implementing changes to investment rules.

## Build and deployment

`python weekly_research.py --output public` renders `research.html`, an archive
page per issue under `research/`, and a navigation link on the scoreboard.
All user/source text is escaped, source URLs are checked, and malformed issues
stop publication. No market-data request is made by this publisher.

`.github/workflows/research-pages.yml` publishes on pushes of research content
to `main`, with the same Pages concurrency lock as the nightly workflow. It
uses the last verified report/evidence generation. Before the first generation
exists, it can reuse the checked-in legacy scoreboard. A corrupt or missing
generation referenced by an existing pointer is always a blocking error.

The nightly workflow passes `--require-committed-report` after its market build.
The archived report/evidence pair is unchanged; the navigation link is added
only to the Pages copy. The latest issue and all previous editions are included
in both publication routes.

Check the `publish-weekly-research` Actions run after committing. Report a
publication as live only when deployment succeeds; send the chat briefing even
if publication fails and clearly state the failure.
