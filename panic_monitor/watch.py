"""One scheduled check. All writes are confined to the feed and notification thread."""
import base64
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

from .market import CAL, MAX_AGE, NY, UTC, observe, session
from .weights import read_weights

REPO = 'Usubillaga/InvestorAce'
BRANCH = 'panic-feed'
FILE = 'panic-status.json'
THREAD = 241
BERLIN = ZoneInfo('Europe/Berlin')


def advance(state, reading):
    previous = state.get('reading')
    prior = previous and previous['heat']
    if previous and reading['as_of'] <= previous['as_of']:
        return
    if not previous or previous['session'] < reading['session']:
        if reading['previous_close'] is not None:
            prior = reading['previous_close']
    # Preserve a still-current pending alert across an interrupted delivery.
    pending = state.get('pending')
    if pending and (pending['session'] != reading['session'] or reading['heat'] >= 20):
        state.pop('pending', None)
    if reading['heat'] < 20 and (prior is None or prior >= 20):
        state['pending'] = {**reading, 'prior': prior}
    state.update(status='observed', reading=reading)


def grade(as_of, day, previous):
    if not as_of:
        return 'nicht verifiziert'
    if as_of == day:
        return 'Stand des Handelstags'
    if as_of == previous:
        return 'Schlussstand des vorigen Handelstags'
    return 'veraltet'


def notice(event, weights, owner):
    stamp = datetime.fromisoformat(event['as_of'])
    prior = event['prior']
    lines = [f"@{owner} **InvestorAce-Panikindikator {event['heat']:.3f} / 100**",
             f"Vergleichswert {prior:.3f}" if prior is not None else 'Erste Beobachtung unter 20, Übergangszeit unbekannt.',
             f"Kursstand {stamp.astimezone(NY):%d.%m.%Y %H:%M %Z} · {stamp.astimezone(BERLIN):%H:%M %Z}.",
             f"Berechnet {event['checked_at']} · {event['components']}/4 Komponenten · "
             f"{event['breadth_count']} Titel mit gültigem 200-Tage-Mittel."
             + (" Marktbreite fehlt in der Strategieformel." if event['components'] == 3 else ""),
             f"[S&P 500]({event['source']}) · [VIX]({event['source'].replace('%5EGSPC', '%5EVIX')}) · [InvestorAce-Formel]({event['method']})"]
    for key, name in [('SPX', 'S&P 500'), ('NDX', 'Nasdaq-100')]:
        item = weights.get(key, {})
        stamp = item.get('as_of')
        label = grade(stamp, event['session'], event['previous_session'])
        if item.get('fetch_error'):
            label += ' · Abruf fehlgeschlagen'
        lines += [f"**{name}** · {stamp or '—'} ({label}) · [Quelle]({item['source']})"]
        for rank, row in enumerate(item.get('rows', []), 1):
            ticker = f" ({row['ticker']})" if row.get('ticker') else ''
            lines.append(f"{rank}. {row['name']}{ticker} · {row['pct']:.2f} %")
    return '\n\n'.join(lines)


class Feed:
    def __init__(self):
        self.api = requests.Session()
        self.api.headers.update(Authorization='Bearer ' + os.environ['GITHUB_TOKEN'])
        self.root = 'https://api.github.com/repos/' + REPO
        self.sha = None

    def load(self):
        r = self.api.get(f'{self.root}/contents/{FILE}', params={'ref': BRANCH}, timeout=15)
        r.raise_for_status()
        data = r.json()
        self.sha = data['sha']
        state = json.loads(base64.b64decode(data['content']))
        if state.get('schema') != 1:
            raise ValueError('Unrecognized monitor state')
        return state

    def save(self, state):
        encoded = base64.b64encode((json.dumps(state, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode())
        r = self.api.put(f'{self.root}/contents/{FILE}', timeout=20,
                         json=dict(message='Record intraday panic check', branch=BRANCH, sha=self.sha,
                                   content=encoded.decode()))
        r.raise_for_status()
        self.sha = r.json()['content']['sha']

    def deliver(self, state, now):
        event = state.get('pending')
        if not event:
            return
        marker = '<!-- panic-crossing ' + event['as_of'] + ' -->'
        url = f'{self.root}/issues/{THREAD}/comments'
        r = self.api.get(url, params={'since': event['as_of'], 'per_page': 100}, timeout=12)
        r.raise_for_status()
        comments = r.json()
        while 'next' in r.links:
            r = self.api.get(r.links['next']['url'], timeout=12)
            r.raise_for_status()
            comments.extend(r.json())
        existing = next((c for c in comments if c['user']['login'] == 'github-actions[bot]' and
                         marker in c['body']), None)
        if not existing:
            latest = state['reading']
            stamp = now()
            if (not session(stamp) or stamp >= datetime.fromisoformat(event['close']) or
                    latest['heat'] >= 20 or stamp - datetime.fromisoformat(latest['as_of']) > MAX_AGE):
                return
            # If delivery was interrupted, use the current confirmed reading and
            # retain the original crossing timestamp as the stable event key.
            body = notice({**latest, 'prior': event['prior']}, state['weights'], REPO.split('/')[0])
            r = self.api.post(url, json={'body': body + '\n\n' + marker}, timeout=12)
            r.raise_for_status()
            existing = r.json()
        state['last_alert'] = {'as_of': event['as_of'], 'url': existing['html_url']}
        del state['pending']
        self.save(state)


def run():
    now = lambda: datetime.now(UTC)
    started = now()
    if not session(started):
        print('Outside the regular XNYS session.')
        return
    from engine import DATA
    feed = Feed()
    state = feed.load()
    day = started.astimezone(NY).date()
    try:
        reading = observe(started, {v.get('yf') or k for k, v in DATA.items()})
    except (ValueError, KeyError) as exc:
        state.update(status='unavailable', checked_at=now().isoformat(), reason=str(exc))
        feed.save(state)
        raise
    reading['checked_at'] = now().isoformat()
    if not session(now()) or now() - datetime.fromisoformat(reading['as_of']) > MAX_AGE:
        print('Observation expired before publication.')
        return
    if state.get('weights_checked') != day.isoformat() or any(
            x.get('fetch_error') for x in state.get('weights', {}).values()):
        state['weights'] = read_weights(day, state.get('weights'))
        state['weights_checked'] = day.isoformat()
        state['weights_previous_session'] = str(CAL.previous_session(str(day)).date())
    advance(state, reading)
    state['checked_at'] = reading['checked_at']
    state.pop('reason', None)
    feed.save(state)
    feed.deliver(state, now)


if __name__ == '__main__':
    run()
