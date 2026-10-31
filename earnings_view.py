"""Earnings calendar for the universe: dates from the nightly Yahoo packet."""
from datetime import date, datetime, timezone
from html import escape

HORIZON_DAYS = 90


def events(data, opportunities, today=None):
    """Upcoming (and up to 7 days past) earnings dates, soonest first."""
    today = today or datetime.now(timezone.utc).date()
    rows, missing = [], []
    for ticker, row in data.items():
        event = ((row.get('dynamic_analysis') or {}).get('events') or {}).get('earnings')
        try:
            when = date.fromisoformat(event['date']) if event else None
        except (TypeError, ValueError, KeyError):
            when = None
        if when is None:
            missing.append(ticker)
            continue
        days = (when - today).days
        if -7 <= days <= HORIZON_DAYS:
            label = (opportunities.get(ticker) or {}).get('label')
            rows.append(dict(ticker=ticker, date=when.isoformat(), days=days, estimated=event.get('estimated'),
                             date_end=event.get('date_end'), label=label))
    return sorted(rows, key=lambda r: (r['date'], r['ticker'])), sorted(missing)


def panel(data, opportunities, today=None):
    rows, missing = events(data, opportunities, today)
    body = ''.join(
        '<tr><td>'+escape(r['date'])+(' – '+escape(r['date_end']) if r['date_end'] else '')+'</td>'
        '<td class="tk">'+escape(r['ticker'])+'</td>'
        '<td>'+('%+d' % r['days'])+'</td>'
        '<td>'+('estimated' if r['estimated'] else 'confirmed')+'</td>'
        '<td>'+escape(r['label'] or 'Data incomplete')+'</td></tr>' for r in rows)
    return ('<div class="box" id="earnings-calendar"><h2>Earnings calendar</h2>'
            '<p class="opportunity-metrics">Next reporting dates of the universe, next 90 days. '
            'Dates come from Yahoo; estimated dates can move. Labels are the current automatic signal.</p>'
            '<div class="tw"><table><thead><tr><th>Date</th><th>Ticker</th><th>Days ahead</th><th>Status</th>'
            '<th>Signal</th></tr></thead><tbody>'+(body or '<tr><td colspan="5">No dated earnings in the next 90 days</td></tr>')
            +'</tbody></table></div>'
            +('<p class="opportunity-metrics">No earnings date: '+escape(', '.join(missing))+'</p>' if missing else '')
            +'</div>')
