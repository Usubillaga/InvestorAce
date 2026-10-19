# Claude daily politics and economy edition

A second daily edition, written by Claude, published next to the ChatGPT
daily briefing (`daily-briefings/`) so both can be compared side by side.

| Language | Latest edition | Dated archive |
|---|---|---|
| Español | claude-daily-es.html | claude-daily/YYYY-MM-DD-es.html |
| English | claude-daily-en.html | claude-daily/YYYY-MM-DD-en.html |
| Deutsch | claude-daily-de.html | claude-daily/YYYY-MM-DD-de.html |

`claude-daily.html` shows German.

## Contract

Identical to [the daily briefing contract](../daily-briefings/README.md) —
same four sections (regime, usa, eu, colombia), dated sources, timezone-aware
cut-off, verified ES/EN/DE translations and FX conventions — with one
difference: **there is no word limit.** The page still shows the estimated
reading time.

Routine publication commits only `claude-briefings/YYYY-MM-DD.json` (Europe/
Berlin issue date). It never edits `daily-briefings/`, publisher code, other
reports, model rules, scores or portfolio allocations.

Validate before committing:

```console
python -m unittest test_weekly_research test_daily_briefing test_claude_briefing -v
python weekly_research.py --output research-output
```
