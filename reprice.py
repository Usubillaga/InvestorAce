#!/usr/bin/env python3
"""
reprice.py - what the book is worth at a different risk-free rate
=================================================================
Written 2026-09-16, the day the FOMC took the funds rate to 3.75-4.00% and
the 10y closed at 5.04%, against a wacc.py that had RISK_FREE frozen at 3.67.

THE QUESTION THIS ANSWERS, WHICH THE BUILD DOES NOT
---------------------------------------------------
wacc.py's own docstring says: "Change it once and every NGV, cover, cushion
and entry price in the book reprices." True -- and that is exactly why you
cannot change it casually. NGV is a perpetuity, (FCF/shares)/r, so

    NGV(r + d) / NGV(r) = r / (r + d)

and the sensitivity goes as 1/r-squared. The rows that move MOST are the
LOW-WACC rows -- the producers and the low-beta defensives -- not the
high-beta growth rows everyone calls "long duration". That inversion is an
artefact of the perpetuity, not a statement about the businesses, and it is
worth seeing in full before it silently rewrites every entry price.

    WACC 4.50% -> rf +137bp:  NGV -23.3%
    WACC 14.0% -> rf +137bp:  NGV  -8.9%

WHY IT RUNS BESIDE THE ENGINE AND NOT INSIDE IT
------------------------------------------------
It writes nothing. No index.html, no history/, no observation. Changing the
rate that prices the book is a decision, and a decision wants a diff in front
of it first. Run this, read it, then set the rate in the build.

RUN:
    python reprice.py                  live 10y against the rate now in force
    python reprice.py 4.40 5.04        explicit scenarios, in percent
    python reprice.py --held 4.40      portfolio rows only
"""
import sys

import engine as E
import wacc as WACC


def _rows():
    """Fundamentals and prices once; every scenario reuses them."""
    E.bootstrap_fundamentals()
    E.fetch_prices()
    return {t: d for t, d in E.DATA.items()
            if d.get('price') and d.get('fcf') is not None and d.get('shares')}


def _at(d, rf):
    """(wacc, ngv, cover, entry, duration_input) for one row at one rf."""
    inp = d.get('wacc_inputs') or {}
    if inp.get('beta') is None:
        r = d.get('r', .08)                    # hand-set row; rf does not reach it
        clamped = 'no-beta'
    else:
        r, det = WACC.compute(beta=inp['beta'], market_cap=inp.get('market_cap'),
                              total_debt=inp.get('total_debt'),
                              tax_rate=inp.get('tax_rate'), risk_free=rf)
        clamped = det.get('clamped')
    n = (d['fcf'] / d['shares']) / r
    c = n / d['price']
    dur = max(-E.REGIME_DURATION_CLAMP, min(E.REGIME_DURATION_CLAMP, (c - 0.60) * 100))
    return r, n, c, n / 0.60, dur, clamped


def report(rows, base_rf, rf, held_only=False):
    print(f'\n{"=" * 92}')
    print(f'RISK-FREE {base_rf:.2f}%  ->  {rf:.2f}%   ({100 * (rf - base_rf):+.0f}bp)')
    print('=' * 92)
    print(f'{"tkr":<6}{"WACC":>13}{"NGV":>19}{"cover":>16}{"entry":>17}{"dur":>14}')
    print(f'{"":6}{"now   new":>13}{"now      new   chg":>19}'
          f'{"now   new":>16}{"now     new":>17}{"now    new":>14}')
    print('-' * 92)

    out, worst = [], []
    for t, d in sorted(rows.items()):
        if held_only and not d.get('held'):
            continue
        r0, n0, c0, e0, du0, _ = _at(d, base_rf)
        r1, n1, c1, e1, du1, cl = _at(d, rf)
        chg = n1 / n0 - 1 if n0 else 0.0
        flag = ' *' if cl in ('floor', 'ceiling') else ''
        out.append(f'{t:<6}{100*r0:5.2f} {100*r1:5.2f}  {n0:8.2f} {n1:8.2f} {chg:+6.1%}'
                   f'  {c0:5.0%} {c1:5.0%}  {e0:7.2f} {e1:7.2f}  {du0:+6.1f} {du1:+6.1f}{flag}')
        worst.append((chg, t, du0, du1))

    print('\n'.join(out))
    print('-' * 92)
    worst.sort()
    print('largest NGV haircuts: ' + ', '.join(f'{t} {c:+.1%}' for c, t, _, _ in worst[:6]))
    print('smallest:             ' + ', '.join(f'{t} {c:+.1%}' for c, t, _, _ in worst[-6:]))

    # The clamp is where discrimination by beta quietly stops.
    n_cl = sum(1 for _, d in rows.items() if _at(d, rf)[5] in ('floor', 'ceiling'))
    fl, ce = WACC.bands(rf)
    print(f'clamp band at this rf: {100*fl:.2f}% - {100*ce:.2f}%;  {n_cl}/{len(rows)} rows bind (*)')

    # Duration is what the regime model actually consumes, and REFLATION weights
    # it at 0.00 -- so none of this touches Regime Fit until the regime moves.
    moved = [(t, du0, du1) for _, t, du0, du1 in worst if abs(du1 - du0) > 1.0]
    print(f'duration input moved on {len(moved)}/{len(worst)} rows '
          f'(the +/-40 clamp absorbs both tails; the middle is where it lands)')
    for regime, w in (('REFLATION', 0.00), ('GOLDILOCKS', -0.35), ('STAGFLATION', 0.55)):
        worst_fit = min(((du1 - du0) * w, t) for t, du0, du1 in moved) if moved else (0, '-')
        print(f'  DUR_W {regime:<12}{w:+.2f} -> largest Regime Fit change '
              f'{worst_fit[0]:+.1f} pts ({worst_fit[1]})')


def main(argv):
    held = '--held' in argv
    args = [a for a in argv if not a.startswith('--')]
    base = WACC.resolve_risk_free()
    rows = _rows()
    if not rows:
        print('no priced rows; is the price fetch working?')
        return 1
    scenarios = [float(a) for a in args] or [E.sync_risk_free() or base]
    for rf in scenarios:
        report(rows, base, rf, held)
    print('\nnothing was written. set the rate in the build when you have decided.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
