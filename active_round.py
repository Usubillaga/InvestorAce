"""Daily trading round for the active paper account, run by .github/workflows/active-round.yml.

It replaces the chat-run round (asked for on 21 Nov 2026: cheaper and not dependent on one chat session).
The rules are unchanged: active_rules.plan decides, and every order is recorded through the same
active_trading.intake as an order placed by hand. Paper only.

    python active_round.py plan      -> prints {"skip": reason} or the plan with titles and bodies
"""
import json
import sys
from datetime import datetime, timezone

# NYSE full-day closures (nyse.com holiday calendar). Weekends are excluded by the workflow schedule.
NYSE_HOLIDAYS = {
    '2026-01-01', '2026-01-19', '2026-02-16', '2026-04-03', '2026-05-25', '2026-06-19', '2026-07-03',
    '2026-09-07', '2026-11-26', '2026-12-25',
    '2027-01-01', '2027-01-18', '2027-02-15', '2027-03-26', '2027-05-31', '2027-06-18', '2027-07-05',
    '2027-09-06', '2027-11-25', '2027-12-24',
}
COVERED_YEARS = {2026, 2027}


def skip_reason(today):
    if today.weekday() >= 5:
        return 'weekend'
    if today.isoformat() in NYSE_HOLIDAYS:
        return 'NYSE holiday'
    if today.year not in COVERED_YEARS:
        return f'no NYSE holiday calendar for {today.year}; add it to active_round.py'
    return None


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv != ['plan']:
        print(__doc__, file=sys.stderr)
        return 2
    today = datetime.now(timezone.utc).date()
    reason = skip_reason(today)
    if reason:
        print(json.dumps(dict(skip=reason, date=today.isoformat())))
        return 0
    import io
    from contextlib import redirect_stdout
    import active_rules
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        active_rules.main([])
    print(buffer.getvalue().strip())
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
