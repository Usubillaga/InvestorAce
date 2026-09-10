#!/usr/bin/env python3
"""
forward.py &middot; does the scorecard actually rank? &mdash; and when will you know?
=======================================================================
This is NOT a backtest. A backtest reconstructs the past, and there are no
past scores to reconstruct: the scorecard did not exist before you built it,
and every subscore in it was set with today's information. Reconstructing it
backwards would be the purest form of the selection bias the Minerva paper
is about (arXiv:2608.23808, section 9.1-9.2).

What is legitimate is a FORWARD test, and it needs exactly one discipline:
the cohort assignment must be frozen BEFORE the outcome is observed.

  1. Explicitly freeze the newest validated snapshot into quintiles.
     Write history/_cohort.json once; analysis never creates or rewrites it.
  2. On every later run, read history/*.json and compute each quintile's
     cumulative return from prices that did not exist at freeze time.
  3. Report the top-minus-bottom spread with a t-statistic, and &mdash; the part
     that actually matters &mdash; how many more trading days are needed before
     that spread could be distinguished from noise.

FOUR SIGNALS ARE TESTED (score, cover, cushion, momentum), so the threshold
is Bonferroni-adjusted to alpha/4. Momentum is included NOT because it is
assumed to work but so that it is tested rather than believed -- and adding
it raises the bar for all four, which is the honest cost of another look.

The harness refuses to state a verdict below an evidence floor (section 4.1 of the
paper): too few days is reported as INSUFFICIENT EVIDENCE, which is a
different statement from "no effect".
"""
import json, os, glob, math
from datetime import datetime, timezone
from statistics import NormalDist
from integrity import atomic_json, finite_number, positive_number

COHORT_FILE = 'history/_cohort.json'
SIGNALS     = ('score', 'cover', 'cushion', 'momentum')
N_BUCKETS   = 5
ALPHA       = 0.05
N_TESTS     = len(SIGNALS)          # Predeclared family, even if a cohort is absent.
Z_CRIT      = NormalDist().inv_cdf(1 - ALPHA / (2 * N_TESTS))
MIN_DAYS    = 60                    # evidence floor: below this, no verdict
MIN_PER_BUCKET = 3


def _days():
    """Every daily snapshot, oldest first, as (date, {ticker: row})."""
    out = []
    for fp in sorted(glob.glob('history/*.json')):
        base = os.path.basename(fp)
        if base.startswith('_'):
            continue
        try:
            datetime.strptime(base, '%Y-%m-%d.json')
            with open(fp) as f:
                snapshot = json.load(f)
            if isinstance(snapshot, dict):
                out.append((base[:-5], snapshot))
        except Exception:
            continue
    return out


def freeze_cohorts(force=False):
    """Freeze the newest available observation, preserving existing cohorts."""
    if os.path.exists(COHORT_FILE):
        if force:
            raise ValueError('Never overwrite a frozen cohort; start a versioned experiment')
        with open(COHORT_FILE, encoding='utf-8') as stream:
            return json.load(stream)
    days = _days()
    if not days:
        return None
    date, snap = days[-1]
    written = datetime.now(timezone.utc).isoformat()
    coh = {'frozen_on': date, 'written': written, 'buckets': {},
           'method': 'equal-name-complete-case-price-returns-v2'}
    for sig in SIGNALS:
        pairs = []
        for ticker, row in snap.items():
            if ticker.startswith('_') or not isinstance(row, dict):
                continue
            value, price = finite_number(row.get(sig)), positive_number(row.get('price'))
            if value is not None and price is not None:
                pairs.append((ticker, value))
        if len(pairs) < N_BUCKETS * MIN_PER_BUCKET:
            continue
        pairs.sort(key=lambda pair: (pair[1], pair[0]))
        # Balanced buckets; the final bucket must not absorb the entire remainder.
        coh['buckets'][sig] = {ticker: i * N_BUCKETS // len(pairs)
                              for i, (ticker, _) in enumerate(pairs)}
    if not coh['buckets']:
        return None
    atomic_json(COHORT_FILE, coh)
    return coh


def _bucket_return(a, b, tickers):
    """Require all frozen members; never silently reweight surviving quotes."""
    if not tickers:
        return None
    values = []
    for ticker in tickers:
        pa = positive_number((a.get(ticker) or {}).get('price'))
        pb = positive_number((b.get(ticker) or {}).get('price'))
        if pa is None or pb is None or abs(pb / pa - 1) >= 0.5:
            return None  # unresolved split, extreme move, or missing quote
        values.append(pb / pa - 1)
    return sum(values) / len(values)


def _returns(days, tickers):
    """Aligned intervals; missing data is None, never a fabricated zero."""
    return [_bucket_return(a, b, tickers)
            for (_, a), (_, b) in zip(days, days[1:])]


# ---------------------------------------------------------------------
# Period breakdown: monthly and yearly
#
# Useful, and dangerous in a specific way. Reading twelve monthly cells is
# twelve more looks at the same data, and one good month is noise. So the
# monthly table is reported ALONGSIDE a stability number rather than on its
# own: the paper's regime gate (Eq. 3) applied to the monthly spreads
# instead of to per-window Sharpes.
#
#   rho = 0.5*p+  +  0.3*clip(1 - sd/sigma_ref)  +  0.2*logistic(worst)
#
# A spread that comes entirely from one month scores low here even when the
# cumulative number looks strong. That is the point.
# ---------------------------------------------------------------------
def _daily_series(days, top, bot):
    """Only matched, complete, near-daily intervals for both frozen buckets."""
    out = []
    for (da, a), (db, b) in zip(days, days[1:]):
        start, end = datetime.fromisoformat(da), datetime.fromisoformat(db)
        if end.weekday() >= 5 or start.weekday() >= 5 or not 1 <= (end-start).days <= 4:
            continue
        rt, rb = _bucket_return(a, b, top), _bucket_return(a, b, bot)
        if rt is not None and rb is not None:
            out.append((db, rt, rb))
    return out


def _compound(xs):
    v = 1.0
    for x in xs: v *= (1 + x)
    return v - 1


def by_period(series, width):
    """width='month' -> 'YYYY-MM', width='year' -> 'YYYY'."""
    n = 7 if width == 'month' else 4
    buckets = {}
    for d, rt, rb in series:
        buckets.setdefault(d[:n], []).append((rt, rb))
    rows = []
    for k in sorted(buckets):
        v = buckets[k]
        t = _compound([x for x, _ in v]); b = _compound([y for _, y in v])
        rows.append(dict(period=k, obs=len(v),
                         top=round(100 * t, 2), bot=round(100 * b, 2),
                         spread=round(100 * (t - b), 2)))
    return rows


def stability(monthly):
    """The paper's regime composite, computed on monthly spreads.
       Returns None below three months -- two points cannot show stability."""
    sp = [m['spread'] for m in monthly]
    if len(sp) < 3: return None
    p_pos = sum(1 for x in sp if x > 0) / len(sp)
    mu = sum(sp) / len(sp)
    sd = (sum((x - mu) ** 2 for x in sp) / (len(sp) - 1)) ** 0.5
    sigma_ref = 4.0                                   # 4pp monthly spread dispersion
    worst = min(sp)
    rho = (0.5 * p_pos
           + 0.3 * max(0.0, min(1.0, 1 - sd / sigma_ref))
           + 0.2 * (1 / (1 + math.exp(-worst))))
    return dict(rho=round(max(0.0, min(1.0, rho)), 3),
                months=len(sp), pct_positive=round(100 * p_pos, 0),
                dispersion=round(sd, 2), worst=round(worst, 2),
                reads=('concentrated in few months' if rho < 0.45 else
                       'mixed' if rho < 0.60 else 'spread across months'))


def run():
    if not os.path.exists(COHORT_FILE):
        return {'ok': False, 'note': 'no frozen cohort yet; build a validated snapshot first'}
    with open(COHORT_FILE, encoding='utf-8') as stream:
        coh = json.load(stream)
    # Legacy cohorts were written later than their chosen historical snapshot.
    # Do not count outcomes observed before the actual freeze was recorded.
    start = max(coh['frozen_on'], coh.get('written', coh['frozen_on'])[:10])
    days = [(date, snap) for date, snap in _days() if date >= start]
    if not coh or len(days) < 2:
        return {'ok': False, 'days': len(days),
                'note': 'cohorts frozen; the test starts once there are two or more snapshots'
                        if coh else 'no history yet'}

    res = {'ok': True, 'frozen_on': coh['frozen_on'], 'days': len(days),
           'obs': len(days) - 1, 'floor': MIN_DAYS, 'signals': {},
           'n_tests': N_TESTS, 'z_crit': Z_CRIT, 'analysis_start': start}

    for sig, b in coh['buckets'].items():
        top = [t for t, k in b.items() if k == N_BUCKETS - 1]
        bot = [t for t, k in b.items() if k == 0]
        if len(top) < MIN_PER_BUCKET or len(bot) < MIN_PER_BUCKET:
            continue
        ser = _daily_series(days, top, bot)
        rt, rb = [x for _, x, _ in ser], [y for _, _, y in ser]
        spread = [x - y for x, y in zip(rt, rb)]
        n = len(spread)
        if n < 2:
            continue
        mu = sum(spread) / n
        var = sum((x - mu) ** 2 for x in spread) / (n - 1)
        sd = math.sqrt(var) if var > 0 else 0.0
        t_stat = (mu * math.sqrt(n) / sd) if sd else 0.0
        # projection: trading days needed for |t| to reach the adjusted critical value
        need = max(MIN_DAYS, int(math.ceil((Z_CRIT * sd / abs(mu)) ** 2))) if (sd and mu) else None
        mo  = by_period(ser, 'month')
        yr  = by_period(ser, 'year')
        cum = _compound([x for x in spread])
        ann = ((1 + cum) ** (252.0 / n) - 1) if n >= MIN_DAYS and n == len(days)-1 else None
        res['signals'][sig] = dict(
            n_top=len(top), n_bot=len(bot), obs=n,
            excluded_intervals=len(days)-1-n,
            return_basis='local-currency unadjusted price; complete-case intervals',
            monthly=mo, yearly=yr, stability=stability(mo),
            annualised_pct=(round(100 * ann, 2) if ann is not None else None),
            cum_top=round(100 * (math.prod(1 + x for x in rt) - 1), 2),
            cum_bot=round(100 * (math.prod(1 + x for x in rb) - 1), 2),
            spread_pct=round(100 * (math.prod(1 + x for x in rt) - 1
                                    - (math.prod(1 + x for x in rb) - 1)), 2),
            daily_bp=round(1e4 * mu, 2), t=round(t_stat, 2),
            days_needed=need,
            years_needed=(round(need / 252, 1) if need else None),
            verdict=('INSUFFICIENT EVIDENCE' if n < MIN_DAYS else
                     'RANKS' if t_stat >= Z_CRIT else
                     'RANKS INVERSELY' if t_stat <= -Z_CRIT else
                     'NO DETECTABLE EFFECT'))
    return res


if __name__ == '__main__':
    print(json.dumps(run(), indent=1))
