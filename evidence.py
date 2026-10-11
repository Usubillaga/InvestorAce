"""Immutable observations and explicit diagnostics; no live score changes."""
from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
import uuid
import platform
import re
import shutil
from importlib import metadata
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from integrity import atomic_json, atomic_text

VERSION = 'evidence-v1'


def number(value):
    if isinstance(value, bool):
        return None
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError, OverflowError):
        return None


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def model_bundle(root):
    """Archive executable source, not merely an unrecoverable hash."""
    sources = {p.name: p.read_text(encoding='utf-8')
               for p in sorted(Path(root).glob('*.py')) if not p.name.startswith('test_')}
    for p in sorted(Path(root).glob('requirements*.txt')):
        sources[p.name] = p.read_text(encoding='utf-8')
    return {'sha256': digest(sources), 'sources': sources}


def runtime():
    packages = {}
    for package in ('yfinance', 'pandas', 'numpy'):
        try:
            packages[package] = metadata.version(package)
        except metadata.PackageNotFoundError:
            packages[package] = None
    return {'python': platform.python_version(), 'platform': platform.system(), 'packages': packages}


def business_quality(row, weights):
    """New diagnostic: g,p,c,b and dilution only, reweighted to 0..10.

    Excludes v, payout r and live valuation pr. Missing components are not
    filled from a published total. This is a declared heuristic, not calibrated.
    """
    sub = row.get('sub')
    if not sub or len(sub) != 6:
        return None
    values = {key: number(sub[i]) for key, i in [('g', 0), ('p', 1), ('c', 2), ('b', 3)]}
    values['d'] = number(row.get('dil'))
    if any(v is None or not 0 <= v <= 10 for v in values.values()):
        return None
    return sum(values[k] * weights[k] for k in values) / sum(weights[k] for k in values)


def valuation_contract(row):
    """Require a declared cash-flow basis; do not reinterpret legacy FCF."""
    basis = row.get('cash_flow_basis', 'UNSPECIFIED')
    rate_basis = row.get('discount_rate_basis', 'WACC' if row.get('r_wacc') else 'UNSPECIFIED')
    expected = {'FCFE': 'COST_OF_EQUITY', 'FCFF': 'WACC'}.get(basis)
    missing = [k for k in ('financial_period', 'financial_published_at', 'cur', 'shares')
               if row.get(k) is None]
    status = 'UNVERIFIED'
    if expected and rate_basis != expected:
        status = 'MISMATCH'
    elif expected and not missing:
        status = 'DECLARED'
    return {'status': status, 'cash_flow_basis': basis, 'discount_rate_basis': rate_basis,
            'missing': missing, 'legacy_formula': '(fcf / shares) / rate',
            'equity_bridge_required': basis == 'FCFF',
            'note': 'Legacy NGV is retained; a declared basis does not certify its inputs.'}


def declared_perpetuity(cash_flow, shares, rate, basis, rate_basis, net_debt=None):
    """Opt-in, separate valuation; never replaces engine.ngv()."""
    f, s, r = number(cash_flow), number(shares), number(rate)
    if f is None or s is None or s <= 0 or r is None or r <= 0:
        raise ValueError('Finite cash flow, positive shares and positive rate required')
    if basis == 'FCFE' and rate_basis == 'COST_OF_EQUITY':
        if net_debt is not None:
            raise ValueError('Do not subtract net debt from an equity cash-flow valuation')
        return f / r / s
    if basis == 'FCFF' and rate_basis == 'WACC' and number(net_debt) is not None:
        return (f / r - float(net_debt)) / s
    raise ValueError('Declare matching cash flow/rate bases and the FCFF net-debt bridge')


def row_diagnostics(row, weights):
    sub = row.get('sub')
    complete = bool(sub and len(sub) == 6 and all(number(x) is not None for x in sub))
    px = number(row.get('price'))
    status = lambda value: 'AVAILABLE' if number(value) is not None else 'MISSING'
    return {'business_quality': business_quality(row, weights),
            'quality_version': 'g-p-c-b-d-renormalised-v1',
            'score_basis': 'LIVE_COMPOSITE' if complete else 'FIXED_TOTAL',
            'price': 'AVAILABLE' if px is not None and px > 0 else 'MISSING',
            'price_observed_at': row.get('quote_observed_at'),
            'fundamentals': 'COMPONENTS_PRESENT' if complete else 'INCOMPLETE',
            'ngv': 'NOT_APPLICABLE' if row.get('na') and not row.get('midcycle') else
                   ('INPUTS_PRESENT' if number(row.get('fcf')) is not None and
                    number(row.get('shares')) not in (None, 0) else 'MISSING'),
            'epv': status(row.get('epv_value')),
            'momentum': status(row.get('mom_12_1')),
            'regime_assumptions': [] if complete else ['balance=6', 'payout=6'],
            'valuation_contract': valuation_contract(row)}


def create_record(rows, outputs, macro, models, source_hash, captured_at=None):
    captured_at = captured_at or datetime.now(timezone.utc).isoformat()
    stamp = datetime.fromisoformat(captured_at.replace('Z', '+00:00'))
    if stamp.tzinfo is None:
        raise ValueError('captured_at must include timezone')
    record = dict(outputs)
    record['_evidence'] = {'schema': VERSION, 'captured_at': stamp.astimezone(timezone.utc).isoformat(),
                           'inputs': rows, 'macro': macro, 'model_source_sha256': source_hash,
                           'universe_sha256': digest(sorted(rows)),
                           'runtime': runtime(),
                           'time_policy': 'Known from capture onward; older market history is reconstructed.'}
    record['_models'] = dict(models, evidence=VERSION)
    # Roundtrip also detaches mutable DATA and refuses non-JSON/non-finite values.
    return json.loads(canonical(record))


def immutable_json(path, value):
    """Publish a complete file atomically without replacing an existing file."""
    path = Path(path)
    payload = canonical(value) + '\n'
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.pending-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(tmp, path)
        except FileExistsError:
            return False
        return True
    finally:
        os.unlink(tmp)


@contextmanager
def build_lock(root='history'):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    lock = root / '_build.lock'
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise RuntimeError('Another build is active, or a crashed build left history/_build.lock') from exc
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(str(os.getpid()))
        yield
    finally:
        lock.unlink()


def _validate_record_bundle(record, bundle):
    canonical(record)
    if bundle['sha256'] != digest(bundle['sources']):
        raise ValueError('Model bundle hash mismatch')
    if record['_evidence']['model_source_sha256'] != bundle['sha256']:
        raise ValueError('Observation/model bundle mismatch')
    stamp = datetime.fromisoformat(record['_evidence']['captured_at'])
    if stamp.tzinfo is None:
        raise ValueError('captured_at must include timezone')
    return stamp.astimezone(timezone.utc)


def publish_record(record, bundle, root='history'):
    """Standalone snapshot API; report builds use publish_build instead."""
    root = Path(root)
    stamp = _validate_record_bundle(record, bundle)
    day = stamp.astimezone(timezone.utc).date().isoformat()
    run_id = stamp.strftime('%Y%m%dT%H%M%S%f') + '-' + uuid.uuid4().hex
    model_path = root / 'models' / (bundle['sha256'] + '.json')
    if not immutable_json(model_path, bundle):
        if json.loads(model_path.read_text(encoding='utf-8')) != bundle:
            raise ValueError('Existing model archive is corrupt')
    if not immutable_json(root / 'runs' / (run_id + '.json'), record):
        raise FileExistsError(run_id)
    daily_created = immutable_json(root / (day + '.json'), record)
    return {'day': day, 'run_id': run_id, 'daily_created': daily_created}


def _load_build(root, run_id):
    if not isinstance(run_id, str) or not re.fullmatch(r'\d{8}T\d{12}-[0-9a-f]{32}', run_id):
        raise ValueError('Invalid build ID')
    folder = Path(root) / '_builds' / run_id
    manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
    if manifest.get('schema') != 'report-build-v1' or manifest.get('run_id') != run_id:
        raise ValueError('Invalid build manifest')
    record = json.loads((folder / 'observation.json').read_text(encoding='utf-8'))
    if digest(record) != manifest['observation_sha256']:
        raise ValueError('Build observation hash mismatch')
    report = folder / 'index.html'
    if hashlib.sha256(report.read_bytes()).hexdigest() != manifest['report_sha256']:
        raise ValueError('Build report hash mismatch')
    model_hash = manifest['model_source_sha256']
    if not re.fullmatch(r'[0-9a-f]{64}', model_hash):
        raise ValueError('Invalid model hash')
    bundle = json.loads((Path(root) / 'models' / (model_hash + '.json')).read_text(encoding='utf-8'))
    stamp = _validate_record_bundle(record, bundle)
    if bundle['sha256'] != model_hash or stamp.date().isoformat() != manifest['day']:
        raise ValueError('Build manifest does not match its observation/model')
    return {'manifest': manifest, 'record': record, 'report_path': report}


def current_build(root='history'):
    """Resolve one pointer once and verify its complete report/evidence pair.

    Deployments must use this report_path, never the compatibility index.html.
    """
    pointer = json.loads((Path(root) / '_current.json').read_text(encoding='utf-8'))
    build = _load_build(root, pointer['run_id'])
    if build['manifest'] != pointer:
        raise ValueError('Current build pointer/manifest mismatch')
    return build


def daily_records(root='history'):
    """First committed observation per UTC day, with legacy files preserved.

    Only builds reachable from _current.json count: a process killed before
    the pointer switch can leave staged/uncommitted files but no new evidence.
    """
    root = Path(root)
    days = {}
    for path in sorted(root.glob('????-??-??.json')):
        try:
            datetime.strptime(path.name, '%Y-%m-%d.json')
            value = json.loads(path.read_text(encoding='utf-8'))
            if isinstance(value, dict):
                days[path.stem] = value
        except (OSError, ValueError):
            continue
    if (root / '_current.json').exists():
        builds, seen = [], set()
        build = current_build(root)
        while True:
            manifest = build['manifest']
            if manifest['run_id'] in seen:
                raise ValueError('Cycle in committed build history')
            seen.add(manifest['run_id'])
            builds.append(build)
            previous = manifest.get('previous_run_id')
            if previous is None:
                break
            build = _load_build(root, previous)
        first = {}
        for build in reversed(builds):
            first.setdefault(build['manifest']['day'], build)
        for day, build in first.items():
            manifest = build['manifest']
            if manifest['daily_observation_sha256'] == manifest['observation_sha256']:
                # A failed mirror followed by a retry must not replace the first capture.
                days[day] = build['record']
            elif day not in days or digest(days[day]) != manifest['daily_observation_sha256']:
                raise ValueError(f'Legacy daily observation {day} is missing or corrupt')
    return sorted(days.items())


def publish_build(record, bundle, html, root='history', report_path='index.html'):
    """Commit a report and observation through one atomic pointer switch.

    Call under build_lock. Legacy day/run files and root index.html are
    compatibility mirrors written after commit; their failure cannot split
    the authoritative pair or feed uncommitted data to the forward harness.
    """
    stamp = _validate_record_bundle(record, bundle)
    root = Path(root)
    previous = current_build(root)['manifest'] if (root / '_current.json').exists() else None
    day = stamp.date().isoformat()
    prior_days = dict(daily_records(root))
    daily_created = day not in prior_days
    daily_record = prior_days.get(day, record)
    run_id = stamp.strftime('%Y%m%dT%H%M%S%f') + '-' + uuid.uuid4().hex
    manifest = {'schema': 'report-build-v1', 'run_id': run_id, 'day': day,
                'previous_run_id': previous['run_id'] if previous else None,
                'observation_sha256': digest(record),
                'daily_observation_sha256': digest(daily_record),
                'report_sha256': hashlib.sha256(html.encode('utf-8')).hexdigest(),
                'model_source_sha256': bundle['sha256']}
    model_path = root / 'models' / (bundle['sha256'] + '.json')
    if not immutable_json(model_path, bundle):
        if json.loads(model_path.read_text(encoding='utf-8')) != bundle:
            raise ValueError('Existing model archive is corrupt')
    builds = root / '_builds'
    builds.mkdir(parents=True, exist_ok=True)
    staged = Path(tempfile.mkdtemp(prefix='.pending-', dir=builds))
    destination = builds / run_id
    committed = False
    try:
        atomic_text(staged / 'index.html', html)
        atomic_text(staged / 'observation.json', canonical(record) + '\n')
        atomic_text(staged / 'manifest.json', canonical(manifest) + '\n')
        os.rename(staged, destination)
        atomic_json(root / '_current.json', manifest)
        committed = True
    finally:
        if staged.exists():
            shutil.rmtree(staged)
        if not committed and destination.exists():
            shutil.rmtree(destination)
    notes = []
    for path, value in ((root / 'runs' / (run_id + '.json'), record),
                        (root / (day + '.json'), daily_record)):
        try:
            immutable_json(path, value)
        except OSError as exc:
            notes.append(f'Compatibility archive {path} was not written: {exc}')
    try:
        atomic_text(report_path, html)
    except OSError as exc:
        notes.append(f'Compatibility report {report_path} was not written: {exc}; '
                     'use evidence.current_build() for the committed report')
    return {'day': day, 'run_id': run_id, 'daily_created': daily_created,
            'report_path': str(destination / 'index.html'), 'compatibility_warnings': notes}
