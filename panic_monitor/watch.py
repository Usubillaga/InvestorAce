"""One scheduled check. All writes are confined to the feed and notification thread."""
import base64
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

from . import market, published
from .market import CAL, MAX_AGE, NY, UTC, session
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
    model = (f"{event['components']} verfügbare Komponenten"
             if event.get('indicator') == 'market-pulse-v1' else f"{event['components']}/4 Komponenten")
    lag = max(0, int((datetime.fromisoformat(event['checked_at']) - stamp).total_seconds()))
    delay = "verzögert" if lag >= 60 else "beobachtetes Kursalter"
    name = "Market Thermometer" if event.get('indicator') == 'market-pulse-v1' else "Index-Leader-Thermometer"
    lines = [f"@{owner} **InvestorAce · {name} {event['heat']:.3f} / 100**",
             f"Vergleichswert {prior:.3f}" if prior is not None else 'Erste Beobachtung unter 20, Übergangszeit unbekannt.',
             f"Kursstand {stamp.astimezone(NY):%d.%m.%Y %H:%M %Z} · {stamp.astimezone(BERLIN):%H:%M %Z}.",
             f"Berechnet {event['checked_at']} · ältester Indexkurs {lag // 60} min {lag % 60} s zuvor ({delay}). "
             "Zusätzliche Feed-Latenz unbekannt. "
             f"{model} · "
             f"{event['breadth_count']} Titel mit gültigem 200-Tage-Mittel."
             + (" Marktbreite fehlt in der Strategieformel." if event['components'] == 3 else ""),
             f"[S&P 500]({event['source']}) · [VIX]({event['source'].replace('%5EGSPC', '%5EVIX')}) · [InvestorAce-Formel]({event['method']})"]
    if event.get('scores', {}).get('fear_greed'):
        fear = event['scores']['fear_greed']
        flag = " · verzögert" if fear.get('date') and fear['date'] < event['session'] else ""
        lines.append(f"[CNN Fear & Greed](https://production.dataviz.cnn.io/index/fearandgreed/graphdata) · Stand {fear.get('date') or 'unbekannt'}{flag}")
    for key, name in [('SPX', 'S&P 500'), ('NDX', 'Nasdaq-100')]:
        item = weights.get(key, {})
        stamp = item.get('as_of')
        label = grade(stamp, event['session'], event['previous_session'])
        if stamp and stamp < event['session']:
            label += ' · verzögert'
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
        # Both views use the same quotes. Deliver simultaneous crossings in one comment.
        slots = [('market-pulse', state.get('dashboard', {})), ('index-leaders', state)]
        events = []
        for model, slot in slots:
            event = slot.get('pending')
            if event:
                tag = 'panic-crossing' if model == 'index-leaders' else 'panic-market-pulse'
                events.append((slot, event, f"<!-- {tag} {event['as_of']} -->"))
        if not events:
            return
        since = min(event['as_of'] for _, event, _ in events)
        url = f'{self.root}/issues/{THREAD}/comments'
        r = self.api.get(url, params={'since': since, 'per_page': 100}, timeout=12)
        r.raise_for_status()
        comments = r.json()
        while 'next' in r.links:
            r = self.api.get(r.links['next']['url'], timeout=12)
            r.raise_for_status()
            comments.extend(r.json())
        send = []
        changed = False
        for slot, event, marker in events:
            existing = next((c for c in comments if c['user']['login'] == 'github-actions[bot]'
                             and marker in c['body']), None)
            if existing:
                slot['last_alert'] = {'as_of': event['as_of'], 'url': existing['html_url']}
                del slot['pending']
                changed = True
                continue
            latest = slot['reading']
            stamp = now()
            if (slot.get('status') == 'unavailable' or not session(stamp) or stamp >= datetime.fromisoformat(event['close'])
                    or latest['heat'] >= 20 or stamp - datetime.fromisoformat(latest['as_of']) > MAX_AGE):
                continue
            body = notice(event, state['weights'], REPO.split('/')[0])
            if latest['as_of'] != event['as_of']:
                body += f"\n\nLetzte Messung {latest['heat']:.3f} / 100 · {latest['as_of']}."
            send.append((slot, event, body + '\n\n' + marker))
        if send and session(now()):
            r = self.api.post(url, json={'body': '\n\n---\n\n'.join(item[2] for item in send)}, timeout=12)
            r.raise_for_status()
            for slot, event, _ in send:
                slot['last_alert'] = {'as_of': event['as_of'], 'url': r.json()['html_url']}
                del slot['pending']
            changed = True
        if changed:
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
    symbols = {v.get('yf') or k for k, v in DATA.items()}
    quotes = market.collect_quotes(symbols)
    dashboard = state.setdefault('dashboard', {})
    for slot, calculate in [(state, market.observe), (dashboard, published.observe)]:
        try:
            reading = calculate(started, symbols, quotes)
            checked = now()
            if not session(checked) or checked - datetime.fromisoformat(reading['as_of']) > MAX_AGE:
                raise ValueError('Observation expired before publication')
            reading['checked_at'] = checked.isoformat()
            advance(slot, reading)
            slot.pop('reason', None)
        except (ValueError, KeyError) as exc:
            slot.update(status='unavailable', reason=str(exc))
        slot['checked_at'] = now().isoformat()
    if state.get('weights_checked') != day.isoformat() or any(
            x.get('fetch_error') for x in state.get('weights', {}).values()):
        state['weights'] = read_weights(day, state.get('weights'))
        state['weights_checked'] = day.isoformat()
        state['weights_previous_session'] = str(CAL.previous_session(str(day)).date())
    feed.save(state)
    feed.deliver(state, now)
    if state.get('status') == 'unavailable' or dashboard.get('status') == 'unavailable':
        raise RuntimeError(f"Data unavailable: {state.get('reason', '')} {dashboard.get('reason', '')}")


if __name__ == '__main__':
    run()
