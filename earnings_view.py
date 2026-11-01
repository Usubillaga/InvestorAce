"""Earnings calendar and alerts for the universe, from the nightly Yahoo packet.

A report within the next 7 days is highlighted in red at the top of the page
and on the stock's row. After a report, the stock shows whether the nightly
data already carries the reported quarter or still waits for it; the scores
update by themselves once the provider publishes the new statements.
"""
from datetime import date, datetime, timezone
from html import escape

HORIZON_DAYS = 90
ALERT_DAYS = 7
AFTER_DAYS = 21        # how long a published report stays in the alert
QUARTER_LAG_DAYS = 100  # a report covers a quarter that ended at most ~100 days earlier

CSS = """
.earnings-alert{border:1px solid #f06a6a;background:#2a1215;border-radius:10px;padding:12px 16px;margin:0 0 16px;font-size:13px;line-height:1.7}
.earnings-alert h2{color:#f06a6a;font-size:15px;margin:0 0 6px}
.earnings-alert .earnings-soon{color:#ff8a8a;font-weight:650}
.earnings-alert .earnings-pending{color:#e5b45c}.earnings-alert .earnings-updated{color:#66e39c}
#earnings-calendar tr.earnings-row-soon td{background:#3a1416;color:#ffb3b3}
#earnings-calendar tr.earnings-row-pending td{background:#2e2410}
"""


def _day(value):
    try:
        return date.fromisoformat(str(value)[:10]) if value else None
    except ValueError:
        return None


def status(row, today):
    """Next date, last reported date and whether the data carries that report."""
    dynamic = row.get('dynamic_analysis') or {}
    events = dynamic.get('events') or {}
    event = events.get('earnings') or {}
    when = _day(event.get('date'))
    last = _day(events.get('last_reported'))
    if when is not None and when <= today:
        last = max(last, when) if last else when
    period = _day(dynamic.get('financial_period'))
    updated = None
    if last is not None:
        updated = period is not None and (last - period).days <= QUARTER_LAG_DAYS
    return dict(next=when if when is not None and when >= today else None, estimated=bool(event.get('estimated')),
                date_end=event.get('date_end'), last=last, period=period, updated=updated)


def events(data, opportunities, today=None):
    """Calendar rows: reports of the last 21 days and the next 90, soonest first."""
    today = today or datetime.now(timezone.utc).date()
    rows, missing = [], []
    for ticker, row in data.items():
        s = status(row, today)
        if s['next'] is None and s['last'] is None:
            missing.append(ticker)
            continue
        label = (opportunities.get(ticker) or {}).get('label')
        if s['last'] is not None and (today - s['last']).days <= AFTER_DAYS and s['last'] != s['next']:
            rows.append(dict(ticker=ticker, date=s['last'].isoformat(), days=(s['last'] - today).days,
                             estimated=False, date_end=None, label=label, updated=s['updated']))
        if s['next'] is not None and (s['next'] - today).days <= HORIZON_DAYS:
            rows.append(dict(ticker=ticker, date=s['next'].isoformat(), days=(s['next'] - today).days,
                             estimated=s['estimated'], date_end=s['date_end'], label=label,
                             updated=s['updated'] if s['next'] == today else None))
    return sorted(rows, key=lambda r: (r['date'], r['ticker'])), sorted(missing)


def _item(ticker, text, label):
    return ticker+' '+text+(' ('+label+')' if label else '')


def alert(data, opportunities, today=None):
    """Red box for reports in the next 7 days; post-report data status."""
    today = today or datetime.now(timezone.utc).date()
    soon, pending, updated = [], [], []
    for ticker, row in sorted(data.items()):
        s = status(row, today)
        label = (opportunities.get(ticker) or {}).get('label')
        if s['next'] is not None and (s['next'] - today).days <= ALERT_DAYS:
            soon.append((s['next'], _item(ticker, ('~' if s['estimated'] else '')+s['next'].isoformat(), label)))
        if s['last'] is not None and 0 <= (today - s['last']).days <= AFTER_DAYS:
            target = updated if s['updated'] else pending
            target.append((s['last'], _item(ticker, s['last'].isoformat(), label)))
    if not (soon or pending or updated):
        return ''
    # One text node per line: i18n translates the leading label and keeps the
    # tickers, dates and labels after it as data.
    line = lambda css, title, items: ('<div class="'+css+'">'+escape(title+' '+' · '.join(x for _, x in sorted(items)))
                                      +'</div>' if items else '')
    return ('<div class="earnings-alert" id="earnings-alert"><h2>Earnings alert</h2>'
            + line('earnings-soon', 'Reporting in the next 7 days:', soon)
            + line('earnings-pending', 'Reported, waiting for the new quarter in the data:', pending)
            + line('earnings-updated', 'Reported and updated with the new quarter:', updated)
            + '<small class="opportunity-metrics">Scores, buy prices and labels refresh by themselves '
              'with every nightly build once the new quarter is published. ~ marks an estimated date.</small></div>')


def row_css(data, today=None):
    """Red marker on the universe table rows of stocks reporting within 7 days."""
    today = today or datetime.now(timezone.utc).date()
    rules = []
    for ticker, row in data.items():
        s = status(row, today)
        if s['next'] is not None and (s['next'] - today).days <= ALERT_DAYS:
            sel = '#master-table tr[data-assessment="'+ticker.replace('"', '')+'"]'
            rules.append(sel+' td{background:#3a1416}'+sel+' td:first-child{box-shadow:inset 4px 0 #f06a6a}')
    return ''.join(rules)


def panel(data, opportunities, today=None):
    rows, missing = events(data, opportunities, today)
    def css(r):
        if 0 <= r['days'] <= ALERT_DAYS:
            return ' class="earnings-row-soon"'
        return ' class="earnings-row-pending"' if r['updated'] is False else ''
    def state(r):
        if r['days'] > 0:
            return 'estimated' if r['estimated'] else 'confirmed'
        if r['updated'] is None:
            return 'confirmed'
        return 'updated' if r['updated'] else 'waiting for data'
    body = ''.join(
        '<tr'+css(r)+'><td>'+escape(r['date'])+(' – '+escape(r['date_end']) if r['date_end'] else '')+'</td>'
        '<td class="tk">'+escape(r['ticker'])+'</td>'
        '<td>'+('%+d' % r['days'])+'</td>'
        '<td>'+state(r)+'</td>'
        '<td>'+escape(r['label'] or 'Data incomplete')+'</td></tr>' for r in rows)
    return ('<div class="box" id="earnings-calendar"><h2>Earnings calendar</h2>'
            '<p class="opportunity-metrics">Next reporting dates of the universe, next 90 days. '
            'Dates come from Yahoo; estimated dates can move. Labels are the current automatic signal.</p>'
            '<div class="tw"><table><thead><tr><th>Date</th><th>Ticker</th><th>Days ahead</th><th>Status</th>'
            '<th>Signal</th></tr></thead><tbody>'+(body or '<tr><td colspan="5">No dated earnings in the next 90 days</td></tr>')
            +'</tbody></table></div>'
            +('<p class="opportunity-metrics">No earnings date: '+escape(', '.join(missing))+'</p>' if missing else '')
            +'</div>')
