"""Small shared I/O and numeric boundaries; no market-data dependencies."""
import json
import math
import os
import tempfile
from pathlib import Path


def finite_number(value):
    if isinstance(value, bool):
        return None
    try:
        value = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return value if math.isfinite(value) else None


def positive_number(value):
    value = finite_number(value)
    return value if value is not None and value > 0 else None


def atomic_text(path, text):
    """Replace only after a complete, flushed write in the target directory."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def atomic_json(path, value):
    # Refuse NaN/Infinity instead of producing invalid JSON archives.
    atomic_text(path, json.dumps(value, indent=1, allow_nan=False) + '\n')


def risk_free_faults(provenance, live_10y):
    """[FIX 2026-09-16] The failure this exists to stop: wacc.RISK_FREE sat at
       3.67 while macro.py read ^TNX live at 5.04. Nothing compared them, so a
       137bp error propagated into every NGV, cover, cushion and entry price
       and produced no symptom at all -- the board looked healthy throughout.

       Stays market-data free by taking the observation as an argument; the
       caller passes the ^TNX close it already pulled. Returns (errors,
       warnings): a stale rate is BLOCKING, because unlike an odd beta it does
       not report a fact about one row, it proves the whole output is wrong."""
    err, warn = [], []
    rf = finite_number(provenance.get('risk_free'))
    live = finite_number(live_10y)
    if rf is None:
        return ['risk-free rate is not a finite number; the book cannot be priced'], warn
    if live is None:
        warn.append('no live 10y observation; risk-free staleness went unchecked this build')
        return err, warn
    drift_bp = abs(rf - live) * 100.0
    limit = provenance.get('max_drift_bp') or 50
    if drift_bp > limit:
        err.append(f'RISK_FREE {rf:.2f}% vs live 10y {live:.2f}% -- {drift_bp:.0f}bp drift '
                   f'(limit {limit}bp). Every NGV in this build is scaled by '
                   f'r/(r{live-rf:+.2f}) against the live rate. '
                   f'Call wacc.set_risk_free({live:.2f}) or raise the limit deliberately.')
    elif drift_bp > limit / 2:
        warn.append(f'RISK_FREE {rf:.2f}% vs live 10y {live:.2f}% -- {drift_bp:.0f}bp drift, '
                    f'inside the {limit}bp limit but moving.')
    if provenance.get('source') == 'workbook-literal':
        warn.append('risk-free still on the workbook literal; no live observation was applied.')
    elif provenance.get('source') == 'normalized-longrun':
        # A declared divergence that stops being visible is exactly how 3.67
        # survived for months. Print it every build, whatever the tolerance.
        warn.append(f'risk-free is a declared normalization: pricing at {rf:.2f}% '
                    f'against a live 10y of {live:.2f}% -- {drift_bp:.0f}bp by choice.')
    return err, warn


def clamp_saturation_faults(details, max_share=0.15):
    """A clamp that binds on a few rows is a sanity band. A clamp that binds on
       many is the flat discount rate this module was built to abolish, wearing
       a different name. Reports the share, never blocks."""
    rows = [d for d in details if d]
    if not rows:
        return []
    hit = [d for d in rows if d.get('clamped')]
    share = len(hit) / len(rows)
    if share <= max_share:
        return []
    lo = sum(1 for d in hit if d['clamped'] == 'floor')
    return [f'WACC clamp binds on {len(hit)}/{len(rows)} rows ({share:.0%}) '
            f'-- {lo} at the floor, {len(hit)-lo} at the ceiling. Those rows now '
            f'share a discount rate and are no longer discriminated by beta.']

