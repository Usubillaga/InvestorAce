"""Descriptive path features and exact level-two piecewise-linear signatures.

No predicted probability, position recommendation or change to legacy fit.
"""
from __future__ import annotations

import math
from datetime import date
from evidence import number

VERSION = 'path-level2-v1'


def signature2(points):
    """Return level 1 and row-major level 2 (level zero is implicitly 1).

    Chen concatenation: S2 += S1 outer dx + dx outer dx / 2.
    Coordinates are translation invariant; callers must preserve starting levels
    separately when those levels are predictive. Scaling is caller-declared.
    """
    if len(points) < 2 or not points[0]:
        raise ValueError('At least two nonempty points required')
    dim = len(points[0])
    if any(len(p) != dim or any(number(x) is None for x in p) for p in points):
        raise ValueError('Finite points of equal dimension required')
    first = [0.0] * dim
    second = [[0.0] * dim for _ in range(dim)]
    for prev, curr in zip(points, points[1:]):
        dx = [float(b) - float(a) for a, b in zip(prev, curr)]
        for i in range(dim):
            for j in range(dim):
                second[i][j] += first[i] * dx[j] + 0.5 * dx[i] * dx[j]
        first = [a + b for a, b in zip(first, dx)]
    return first, second


def quadrant(growth, inflation):
    return ('REFLATION' if growth >= 0 and inflation >= 0 else
            'GOLDILOCKS' if growth >= 0 else
            'STAGFLATION' if inflation >= 0 else 'RECESSION')


def diagnostics(points, window=63):
    """Dated, aligned daily market-proxy observations, oldest first.

    Persistence is consecutive sampled sessions, capped by the selected window;
    it is not a duration inferred from six sparse chart points.
    """
    if window < 2:
        raise ValueError('window must be at least two observations')
    if len(points) < 2:
        return {'status': 'INSUFFICIENT_HISTORY', 'observations': len(points), 'version': VERSION}
    parsed = []
    for p in points:
        day = date.fromisoformat(p['date'])
        g, i = number(p.get('g')), number(p.get('i'))
        if g is None or i is None:
            raise ValueError('Non-finite macro path point')
        if parsed and day <= parsed[-1][0]:
            raise ValueError('Macro path dates must be strictly increasing')
        parsed.append((day, g, i))
    parsed = parsed[-window:]
    start, finish = parsed[0][0], parsed[-1][0]
    span = (finish - start).days
    # Fixed units: growth/inflation percentage points divided by 100.
    path = [[(d - start).days / span, g / 100, i / 100] for d, g, i in parsed]
    first, second = signature2(path)
    regimes = [quadrant(g, i) for _, g, i in parsed]
    persistence = 0
    for r in reversed(regimes):
        if r != regimes[-1]:
            break
        persistence += 1
    dg = parsed[-1][1] - parsed[0][1]
    di = parsed[-1][2] - parsed[0][2]
    return {'status': 'DESCRIPTIVE', 'version': VERSION, 'observations': len(parsed),
            'start': start.isoformat(), 'end': finish.isoformat(), 'calendar_days': span,
            'regime': regimes[-1], 'persistence_observations': persistence,
            'persistence_censored': persistence == len(parsed),
            'transitions': sum(a != b for a, b in zip(regimes, regimes[1:])),
            'growth_change_pp': dg, 'inflation_change_pp': di,
            'boundary_distance_pp': min(abs(parsed[-1][1]), abs(parsed[-1][2])),
            'growth_inflation_area': (second[1][2] - second[2][1]) / 2,
            'signature_level1': first, 'signature_level2': second,
            'channels': ['normalised_calendar_time', 'growth_fraction', 'inflation_fraction'],
            'note': 'Reconstructed market-proxy path; no calibrated transition probability.'}
