"""Read-only, expanding-window experiments on the verified build chain."""
import calendar
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import date, timedelta
from html import escape
from pathlib import Path

from evidence import committed_builds
from paper_portfolio import merge_series
from trading_desk import GROUPS, trend_group

REGIMES = ('GOLDILOCKS', 'REFLATION', 'INFLATION', 'STAGFLATION', 'RECESSION')
TRENDS = tuple(name for name, _ in GROUPS) + ('UNCLASSIFIED',)
FREEZE = date(2026, 11, 22)
COST = 0.001  # one-way execution cost


def sample(build, versions, root):
    meta = build['record']['_evidence']
    manifest = build['manifest']
    day = date.fromisoformat(manifest['day'])
    key = manifest['model_source_sha256']
    if key not in versions:
        sources = json.loads((root / 'models' / (key + '.json')).read_text())['sources']
        versions[key] = {name: hashlib.sha256(sources[name].encode()).hexdigest()
                         for name in ('macro.py', 'timing.py') if name in sources}
    versions_used = versions[key]
    macro = meta.get('macro') or {}
    regime = macro.get('regime')
    basis = macro.get('regime_basis')
    market = {}
    if macro.get('ok') and regime in REGIMES and basis and 'macro.py' in versions_used:
        market['US'] = (regime, basis + '/' + versions_used['macro.py'])
    stocks = {}
    for ticker, row in (meta.get('inputs') or {}).items():
        t = row.get('timing') or {}
        if t.get('status') != 'AVAILABLE' or 'timing.py' not in versions_used:
            continue
        try:
            age = (day - date.fromisoformat(t['last_bar'][:10])).days
        except (ValueError, KeyError, TypeError):
            continue
        if 0 <= age <= 3 and all(isinstance(t.get(k), (float, int)) and math.isfinite(t[k]) and t[k] > 0
                                 for k in ('close', 'sma36', 'sma50', 'sma200')):
            stocks[row.get('yf') or ticker] = (trend_group(t) or 'UNCLASSIFIED', versions_used['timing.py'])
    return day, market, stocks


def paper_return(symbol, start, end, prices, sessions):
    dates = [d for d in sessions if start.isoformat() < d <= end.isoformat()]
    closes = prices.get(symbol, {})
    if len(dates) < 2 or any(d not in closes or closes[d] <= 0 for d in dates):
        return None
    entry = closes[dates[0]]
    # A close-triggered stop executes at the following close, including gaps.
    exit_price = closes[dates[-1]]
    for i, d in enumerate(dates[1:-1], 2):
        if closes[d] <= entry * 0.92:
            exit_price = closes[dates[i]]
            break
    return exit_price * (1 - COST) / (entry * (1 + COST)) - 1


def evaluate(samples, states, monthly, prices, sessions):
    counts = defaultdict(Counter)
    totals = defaultdict(Counter)
    scored, forecasts, transitions, trades = [], [], [], []
    missing = 0
    for start in sorted(samples):
        rows, build = samples[start]
        end = ((start + timedelta(days=1)).replace(day=calendar.monthrange(
            (start + timedelta(days=1)).year, (start + timedelta(days=1)).month)[1])
               if monthly else start + timedelta(days=7))
        later = samples.get(end)
        batch = []
        forecasts = []
        for symbol, (state, version) in sorted(rows.items()):
            history = counts[version, state]
            n = history.total()
            probabilities = {s: history[s] / n for s in states} if n else {}
            forecasts.append(dict(symbol=symbol, state=state, version=version, n=n, probabilities=probabilities))
            if later is None:
                continue
            baseline = totals[version]
            if not monthly and n and state == 'PULLBACK':
                net = paper_return(symbol, start, end, prices, sessions)
                selected = probabilities['UPTREND'] > baseline['UPTREND'] / baseline.total()
                trades.append(dict(start=str(start), symbol=symbol, forward=start >= FREEZE,
                                   selected=selected, base_net=net,
                                   filtered_net=(net if selected else 0) if net is not None else None))
            outcome = later[0].get(symbol)
            if not outcome or outcome[1] != version:
                missing += 1
                continue
            target = outcome[0]
            batch.append((version, state, target))
            if not n or (not monthly and state != 'PULLBACK'):
                continue
            baseline = totals[version]
            keys = states if monthly else ('UPTREND',)
            losses = {}
            for name, probs in [('markov', probabilities), ('persistence', {state: 1}),
                                ('frequency', {s: baseline[s] / baseline.total() for s in keys})]:
                losses[name] = sum((probs.get(s, 0) - (target == s)) ** 2 for s in keys)
            result = dict(start=str(start), end=str(end), symbol=symbol, source=build,
                          outcome_build=later[1], losses=losses, forward=start >= FREEZE)
            scored.append(result)
        # All forecasts for the same date precede every update from that date.
        for version, state, target in batch:
            counts[version, state][target] += 1
            totals[version][target] += 1
        if later:
            transitions.append(dict(start=str(start), end=str(end), source=build, outcome_build=later[1], n=len(batch)))
    return dict(observations=len(samples), transitions=transitions, missing_or_changed=missing,
                matrix=[dict(version=v, state=s, outcomes=dict(c)) for (v, s), c in counts.items() if c],
                trades=trades, scores=scored, latest=forecasts, snapshots={str(d): b for d, (_, b) in samples.items()})


def run(root, current):
    history = Path(root) / 'history'
    weeks, months, versions, prices = {}, {}, {}, defaultdict(dict)
    asof = date.fromisoformat(current['manifest']['day'])
    for build in committed_builds(history, current):
        day, market, stocks = sample(build, versions, history)
        identity = build['manifest']['run_id']
        # Newest build wins within the sampling window. An empty sample remains visible.
        if day.weekday() == 4:
            weeks.setdefault(day, (stocks, identity))
        last = day.replace(day=calendar.monthrange(day.year, day.month)[1])
        if last < asof and (last - day).days <= 3:
            months.setdefault(last, (market, identity))
        for symbol, rows in merge_series([build['record']]).items():
            for d, close in rows:
                if d <= asof.isoformat():
                    prices[symbol].setdefault(d, close)
    sessions = sorted(prices['^GSPC'])
    return dict(build=current['manifest']['run_id'], freeze=str(FREEZE),
                macro=evaluate(months, REGIMES, True, prices, sessions),
                desk=evaluate(weeks, TRENDS, False, prices, sessions))


def page(report):
    from war_scenario import shell
    body = ['<p>Forschungsstand ab 22.11.2026 · <a href="markov-experiments.json">Daten, Prognosen und Build-IDs</a></p>']
    for key, title, goal in (
        ('macro', 'InvestorAce · Welches US-Regime folgt im nächsten Monat?',
         'Monatsende gegen Monatsende. Ziel ist eine bessere Wahrscheinlichkeitsverteilung für die fünf Regime. '
         'Verglichen werden nur identische Datenbasis und Makro-Codeversion.'),
        ('desk', 'Tradingdesk · Wann wird aus einem Pullback wieder ein Aufwärtstrend?',
         'Freitag gegen Folgefreitag. Ziel ist die Wahrscheinlichkeit für UPTREND je PULLBACK. '
         'Separater Long-Papiertest je Gelegenheit: Einstieg zum nächsten Schlusskurs, Ausstieg bis Folgefreitag. '
         '8 % Verlust am Schluss löst den Ausstieg zum nächsten Schlusskurs aus. Kosten: 10 Basispunkte je Seite. '
         'Der Filter nimmt eine Gelegenheit nur oberhalb der historischen UPTREND-Grundrate wahr. '
         'Ausgelassene Gelegenheiten zählen mit 0 %.')):

        exp = report[key]
        body.append(f'<h2>{title}</h2><p>{goal}</p><p>{exp["observations"]} Stichtage · '
                    f'{sum(r["n"] for r in exp["transitions"])} vergleichbare Übergänge · '
                    f'{exp["missing_or_changed"]} Fälle mit fehlendem oder inkompatiblem Folgezustand.</p>')
        applicable = [f for f in exp['latest'] if key == 'macro' or f['state'] == 'PULLBACK']
        if applicable:
            f = applicable[0]
            text = ' · '.join(f'{escape(s)} {v:.1%}' for s, v in f['probabilities'].items())
            body.append(f'<p>Letzter Stichtag {max(exp["snapshots"])} · {escape(f["state"])} · '
                        f'{f["n"]} frühere Übergänge aus diesem Zustand. {text or "Prognose offen."}</p>')
        body.append(f'<p>Zeiträume mit vergleichbaren Übergängen: '
                    f'{sum(t["n"] > 0 for t in exp["transitions"])}.</p>')
        for forward, label in [(False, 'Historischer Walk-forward'), (True, 'Prospektiv ab 22.11.2026')]:
            rows = [r for r in exp['scores'] if r['forward'] == forward]
            body.append(f'<h3>{label}</h3>')
            if not rows:
                body.append('<p>Noch keine auswertbaren Prognosen.</p>')
            else:
                body.append(f'<p>{len(rows)} Prognosen · Brier-Score (kleiner ist besser): ' +
                        ' / '.join(f'{name} {sum(r["losses"][k] for r in rows)/len(rows):.4f}'
                                   for k, name in [('markov','Markov'), ('persistence','Fortschreibung'),
                                                   ('frequency','Grundrate')]) + '.</p>')
            if key == 'desk':
                paired = [r for r in exp['trades'] if r['forward'] == forward and r['base_net'] is not None]
                if paired:
                    body.append('<p>Mittlerer Nettoertrag je Gelegenheit, gleiche Gewichtung: ' +
                                ' / '.join(f'{name} {sum(r[k] for r in paired)/len(paired):.2%}'
                                           for k, name in [('base_net','alle'), ('filtered_net','gefiltert')]) +
                                f' ({len(paired)} vollständige Kurspfade).</p>')
                else:
                    body.append('<p>Keine vollständigen Kurspfade für den Renditevergleich.</p>')
    body.append('<p>Beide Modelle lernen nur aus abgeschlossenen Vorperioden. Ohne Beobachtung für einen '
                'Ausgangszustand bleibt die Prognose offen. Die Ergebnisse dienen der Forschung.</p>')
    return shell('Markov-Experimente', ''.join(body))


def site_pages(root, current):
    try:
        report = run(root, current)
    except (OSError, ValueError, KeyError, TypeError) as error:
        from war_scenario import shell
        message = 'Archiv für die Markov-Experimente nicht auswertbar: ' + escape(str(error))
        return [(Path('markov-experiments.html'), shell('Markov-Experimente', '<p>' + message + '</p>'))]
    return [(Path('markov-experiments.html'), page(report)),
            (Path('markov-experiments.json'), json.dumps(report, allow_nan=False, ensure_ascii=False))]
