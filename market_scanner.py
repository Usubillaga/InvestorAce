#!/usr/bin/env python3
"""Read-only idea scanner: the market-wide scan plus the verified InvestorAce universe.

Two lists, never mixed:
- "Gesamtmarkt": market-scan/latest.json from market_universe.py (weekly SEC
  scan of all NYSE/Nasdaq US-GAAP filers). Mechanical screening scores.
- "Mein Universum": the hash-verified committed engine generation.

This page builder fetches nothing and rewrites no engine input or score.
Run: python market_scanner.py --output research-output/scanner
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path
from urllib.parse import quote, urlsplit

from evidence import current_build, number
from integrity import atomic_text
import market_universe


VERSION = 'market-scanner-v2'
BANDS = [(3.5, 'Sell'), (5.5, 'Hold negativ'), (7, 'Hold positiv'),
         (8.5, 'Buy'), (11, 'Strong Buy')]
QUOTE_MAX_AGE_HOURS = 96
ASSETS = Path(__file__).parent
REGIMES = ('GOLDILOCKS', 'REFLATION', 'INFLATION', 'STAGFLATION', 'RECESSION')
REPOSITORY = 'Usubillaga/InvestorAce'


def model_band(value):
    score = number(value)
    if score is None or not 0 <= score <= 10:
        return None
    return next(label for ceiling, label in BANDS if score < ceiling)


def _timestamp(value):
    try:
        stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return stamp.astimezone(timezone.utc) if stamp.tzinfo else None
    except (AttributeError, ValueError, TypeError):
        return None


def _safe_sources(sources):
    result = []
    for source in sources or []:
        try:
            url = source['url']
            parsed = urlsplit(url)
            if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or
                    parsed.password or parsed.port not in (None, 443) or any(c.isspace() for c in url)):
                continue
            result.append({'title': str(source.get('title') or parsed.hostname), 'url': url,
                           'published_at': source.get('published_at')})
        except (KeyError, TypeError, ValueError):
            continue
    return result


def _quote(row, as_of):
    price = number(row.get('price'))
    stamp = _timestamp(row.get('quote_observed_at'))
    if price is None or price <= 0:
        return 'MISSING', None
    if stamp is None:
        return 'TIME_UNKNOWN', None
    age = (as_of - stamp).total_seconds() / 3600
    if age < 0:
        return 'FUTURE', age
    if age > QUOTE_MAX_AGE_HOURS:
        return 'STALE', age
    return 'DATED', age


def current_regime(record):
    """The regime the engine read from market data at capture time, if any."""
    macro = (record.get('_evidence') or {}).get('macro') or {}
    regime = macro.get('regime') if macro.get('ok') else None
    return regime if regime in REGIMES else None


def add_ticker_url(ticker, repository=None):
    """Prefilled issue for the existing add-ticker workflow (owner-only trigger)."""
    repository = repository or os.environ.get('GITHUB_REPOSITORY') or REPOSITORY
    return f'https://github.com/{repository}/issues/new?title=' + quote(f'add-ticker: {ticker}')


def market_section(market, record, as_of, repository=None):
    """Validate the weekly scan and join today's universe membership and engine score."""
    empty = dict(candidates=[], funnel=[], coverage='', generated_at=None, as_of=None, method={},
                 calibration=None)
    if market is None:
        return dict(empty, status='MISSING', note='Noch kein Marktscan gespeichert.')
    errors = market_universe.validate_payload(market, now=as_of)
    if errors:
        return dict(empty, status='INVALID', note='Marktscan verworfen: ' + '; '.join(errors[:3]))
    generated = datetime.fromisoformat(market['generated_at'].replace('Z', '+00:00'))
    age = as_of - generated
    inputs = (record.get('_evidence') or {}).get('inputs') or {}
    universe = {}
    for key, row in inputs.items():
        symbol = str(row.get('yf') or key).upper()
        if '.' not in symbol:          # exchange-suffixed listings are other companies
            universe[symbol] = key
    candidates = []
    for item in market['candidates']:
        key = universe.get(item['ticker'])
        candidates.append(dict(item, universe_key=key, in_universe=key is not None,
                               universe_score=number((record.get(key) or {}).get('score')) if key else None,
                               add_url=None if key else add_ticker_url(item['ticker'], repository)))
    status = 'STALE' if age > timedelta(days=market_universe.MAX_SCAN_AGE_DAYS) else 'OK'
    # How far the mechanical screening score sits from the curated model score on the
    # tickers present in both lists (first live scan: +1.2 points on average, n=16).
    diffs = sorted(c['score'] - c['universe_score'] for c in candidates
                   if c['in_universe'] and number(c['score']) is not None and c['universe_score'] is not None)
    calibration = None
    if diffs:
        mid = len(diffs) // 2
        calibration = dict(n=len(diffs), mean_diff=sum(diffs) / len(diffs),
                           median_diff=diffs[mid] if len(diffs) % 2 else (diffs[mid - 1] + diffs[mid]) / 2,
                           min_diff=diffs[0], max_diff=diffs[-1])
    return dict(status=status, age_days=round(age.total_seconds() / 86400, 1), calibration=calibration,
                note=('Marktscan älter als 14 Tage; Kurse und Zahlen nicht mehr aktuell.'
                      if status == 'STALE' else ''),
                generated_at=market['generated_at'], as_of=market['as_of'],
                coverage=market['coverage'], funnel=market['funnel'], method=market['method'],
                rejected=market.get('rejected', {}), sources=market.get('sources', {}),
                implausible=market.get('implausible', []), candidates=candidates)


def build_scan(record, *, as_of=None, notes=None, run_id=None, market=None, repository=None):
    """Rank archived model scores; leave current ratings pending actual review.

    Source coverage and mechanical completeness do not establish an audited
    investment conclusion. Even a fully populated record needs cross-review.
    The market-wide scan is attached separately and never re-ranks these rows.
    """
    as_of = as_of or datetime.now(timezone.utc)
    if as_of.tzinfo is None:
        raise ValueError('as_of needs a timezone')
    evidence = record.get('_evidence', {})
    captured = _timestamp(evidence.get('captured_at'))
    if captured is None or captured > as_of:
        raise ValueError('Scanner needs a dated, non-future evidence generation')
    inputs = evidence.get('inputs')
    if not isinstance(inputs, dict):
        raise ValueError('Scanner needs frozen per-ticker inputs')
    notes = notes or {'schema_version': 1, 'entries': {}}
    if notes.get('schema_version') != 1 or not isinstance(notes.get('entries'), dict):
        raise ValueError('Invalid scanner notes')
    if notes.get('as_of') and notes['as_of'] > as_of.date().isoformat():
        raise ValueError('Scanner notes cannot postdate analysis')
    reviews = record.get('_source_reviews', {})
    monitoring = record.get('_filing_monitoring', {}).get('entries', {})
    rows = []
    for ticker, raw in inputs.items():
        output = record.get(ticker, {})
        diagnostics = output.get('diagnostics', {})
        contract = diagnostics.get('valuation_contract', {})
        source_review = reviews.get('entries', {}).get(ticker, {})
        source_valuation = source_review.get('valuation', {})
        note = notes['entries'].get(ticker, {})
        issues = []

        def issue(code, message, severity='major'):
            issues.append(dict(code=code, message=message, severity=severity, status='open'))

        quote_status, age = _quote(raw, as_of)
        if quote_status != 'DATED':
            quote_reasons = dict(MISSING='Kein positiver Kurs vorhanden.',
                TIME_UNKNOWN='Kurszeitpunkt unbekannt; die Abrufzeit belegt keinen aktuellen Börsenkurs.',
                STALE='Kurs älter als die offengelegte 96-Stunden-Grenze.',
                FUTURE='Kurszeitpunkt liegt nach dem Analysezeitpunkt.')
            issue('QUOTE_' + quote_status, quote_reasons[quote_status])
        score = number(output.get('score'))
        band = model_band(score)
        if band is None:
            score = None
            issue('NO_SCORE', 'Kein gültiger Modellscore zwischen 0 und 10.')
        explanation = output.get('score_explanation', {})
        if explanation.get('status') != 'DECOMPOSED':
            issue('FIXED_TOTAL', 'Gesamtscore ohne nachvollziehbare Zerlegung der acht Kategorien.')
        elif explanation.get('reconciles') is not True:
            issue('SCORE_TIE_OUT', 'Die Scorebeiträge sind nicht mit dem Gesamtscore abgestimmt.')
        if contract.get('status') != 'DECLARED' and not contract.get('issues'):
            issue('VALUATION_BASIS', 'Cashflow-Definition und passender Diskontsatz sind nicht belegt.')
        for message in contract.get('issues', []):
            issue('VALUATION_BASIS', str(message))
        if source_valuation.get('status') != 'SOURCE_CHECKED':
            issue('SOURCE_REVIEW', 'Primärquellenprüfung der Bewertungsgrundlagen fehlt oder ist unvollständig.')
        if raw.get('normalization_status') == 'REVIEW_REQUIRED' or raw.get('built') in ('auto', 'est', 'back-solved', 'yahoo-draft'):
            issue('NORMALIZATION', 'Nachhaltiger Cashflow und Kategorien benötigen eine belegte Normalisierung.')
        if raw.get('midcycle') and raw.get('normalization_status') != 'VERIFIED':
            issue('MID_CYCLE', 'Rohstoffproduzent: mittlere Zyklusannahmen vor Bewertung prüfen.')
        filing = monitoring.get(ticker, {})
        if filing and filing.get('status') != 'RESOLVED':
            issue('FILING_GAP', filing.get('reason') or 'Offene Lücke im Filing-Monitoring.')
        objections = note.get('objections', [])
        for objection in objections:
            if objection.get('status') not in ('verified', 'rejected'):
                issue(str(objection.get('id') or 'REVIEW_OBJECTION'),
                      str(objection.get('message') or 'Unbeantworteter Einwand.'),
                      objection.get('severity', 'major'))
        unresolved = any(x.get('severity') in ('major', 'critical') and
                         x.get('status') not in ('verified', 'rejected') for x in objections)
        # There is no automatic promotion from source inspection to a CIO decision.
        issue('CROSS_REVIEW_PENDING', 'Für diesen Scannerlauf liegt keine abgeschlossene Cross-Review-Einstufung vor.')
        status = 'UNRESOLVED' if unresolved else ('BLOCKED_BY_DATA' if len(issues) > 1 else 'REVIEW_PENDING')
        archived = {key: number(output.get(key)) for key in ('ngv', 'cover', 'cushion', 'epv')}
        rows.append(dict(ticker=ticker, listing=raw.get('yf') or ticker,
            issuer=note.get('issuer') or source_review.get('issuer') or raw.get('yf') or ticker,
            currency=raw.get('cur') or '?', sector=raw.get('sector') or 'Unbekannt',
            held_in_snapshot=bool(number(output.get('weight')) and output['weight'] > 0),
            model_score=score, model_band=band, score_basis=explanation.get('status') or 'UNKNOWN',
            rating=None, review_status=status, issues=issues, objections=objections,
            price=number(raw.get('price')), quote_status=quote_status,
            quote_observed_at=raw.get('quote_observed_at'), quote_age_hours=age,
            retrieved_at=raw.get('price_ts'), valuation={key: None for key in archived},
            archived_valuation=archived, regime_fit=output.get('regime', {}),
            source_status=source_valuation.get('status') or 'NOT_REVIEWED',
            source_review_as_of=reviews.get('as_of'),
            source_reason=source_valuation.get('reason') or '',
            sources=_safe_sources(source_valuation.get('sources', []) + note.get('sources', [])),
            thesis=note.get('thesis') or '', counterargument=note.get('counterargument') or '',
            next_check=note.get('next_check') or 'Primärquellen, nachhaltigen Cashflow, Aktienzahl und Bewertungsbasis prüfen.',
            notes_as_of=notes.get('as_of') if note else None,
            model_note=raw.get('boot_note') or '', score_components=explanation.get('components', [])))
    rows.sort(key=lambda row: (-(row['model_score'] if row['model_score'] is not None else -1), row['ticker']))
    return dict(schema=VERSION, generated_at=as_of.isoformat(),
        captured_at=captured.isoformat(), run_id=run_id,
        model_source_sha256=evidence.get('model_source_sha256'), models=record.get('_models', {}),
        universe_count=len(rows), rated_count=0,
        coverage='Vorhandenes InvestorAce-Universum (bereits modellierte Titel).',
        current_regime=current_regime(record), regimes=list(REGIMES),
        quote_policy=dict(max_age_hours=QUOTE_MAX_AGE_HOURS,
            note='96 Kalenderstunden, auch am Wochenende; kein Börsenkalender. Abrufzeit ersetzt keinen Kurszeitpunkt.'),
        bands=[dict(upper_exclusive=ceiling, label=label) for ceiling, label in BANDS], rows=rows,
        market=market_section(market, record, as_of, repository))


def render_scan(scan):
    template = (ASSETS / 'scanner_template.html').read_text(encoding='utf-8')
    payload = json.dumps(scan, ensure_ascii=False, allow_nan=False).replace('<', '\\u003c').replace('&', '\\u0026')
    market = scan.get('market') or {}
    fallback = ''.join('<tr><td>' + escape(c['ticker']) + '</td><td>' + escape(c['band'] or 'Ohne Score') +
                       '</td><td>' + escape('—' if c['score'] is None else f'{c["score"]:.2f}') +
                       '</td><td>Marktscan · ungeprüft</td></tr>' for c in market.get('candidates', []))
    fallback += ''.join('<tr><td>' + escape(row['ticker']) + '</td><td>' +
                        escape(row['model_band'] or 'Ohne Score') + '</td><td>' +
                        escape(str(row['model_score'])) + '</td><td>Universum · ungeprüft</td></tr>'
                        for row in scan['rows'])
    return template.replace('__STYLE__', (ASSETS / 'scanner.css').read_text(encoding='utf-8')).replace(
        '__DATA__', payload).replace('__FALLBACK__', fallback).replace(
        '__SCRIPT__', (ASSETS / 'scanner.js').read_text(encoding='utf-8'))


def load_market(root):
    """The committed weekly scan, or None. A broken file is reported, not fatal."""
    path = Path(root) / 'market-scan' / 'latest.json'
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {'schema': 'unreadable'}


def site_pages(root, build, as_of=None):
    root = Path(root)
    note_path = root / 'scanner_notes.json'
    notes = json.loads(note_path.read_text(encoding='utf-8')) if note_path.exists() else None
    scan = build_scan(build['record'], as_of=as_of, notes=notes,
                      run_id=build['manifest']['run_id'], market=load_market(root))
    return [(Path('scanner.html'), render_scan(scan)),
            (Path('scanner.json'), json.dumps(scan, ensure_ascii=False, indent=2, allow_nan=False) + '\n')]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ASSETS)
    parser.add_argument('--output', type=Path, default=Path('research-output/scanner'))
    args = parser.parse_args()
    root, output = args.root.resolve(), args.output.resolve()
    if output == root or root / 'history' == output or root / 'history' in output.parents:
        raise ValueError('Use a separate output directory outside history')
    build = current_build(root / 'history')
    pages = site_pages(root, build)
    output.mkdir(parents=True, exist_ok=True)
    for path, payload in pages:
        atomic_text(output / path, payload)
    market = load_market(root)
    count = len(market.get('candidates', [])) if isinstance(market, dict) else 0
    print(f'Scanner: {len(build["record"]["_evidence"]["inputs"])} Aktien im Universum, '
          f'{count} Marktkandidaten, {output / "scanner.html"}')


if __name__ == '__main__':
    main()
