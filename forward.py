#!/usr/bin/env python3
"""
forward.py Â· does the scorecard actually rank? â€” and when will you know?
=======================================================================
This is NOT a backtest. A backtest reconstructs the past, and there are no
past scores to reconstruct: the scorecard did not exist before you built it,
and every subscore in it was set with today's information. Reconstructing it
backwards would be the purest form of the selection bias the Minerva paper
is about (arXiv:2608.23808, Â§9.1-9.2).

What is legitimate is a FORWARD test, and it needs exactly one discipline:
the cohort assignment must be frozen BEFORE the outcome is observed.

  1. On first run, split every priced ticker into quintiles by today's
     signal and write history/_cohort.json. That file is never rewritten.
  2. On every later run, read history/*.json and compute each quintile's
     cumulative return from prices that did not exist at freeze time.
  3. Report the top-minus-bottom spread with a t-statistic, and â€” the part
     that actually matters â€” how many more trading days are needed before
     that spread could be distinguished from noise.

THREE SIGNALS ARE TESTED (score, cover, cushion), so the significance
threshold is Bonferroni-adjusted to alpha/3. Testing three and reporting
the best without adjustment is the error the paper names.

The harness refuses to state a verdict below an evidence floor (Â§4.1 of the
paper): too few days is reported as INSUFFICIENT EVIDENCE, which is a
different statement from "no effect".
"""
import json, os, glob, math
from datetime import datetime, timezone

COHORT_FILE = 'history/_cohort.json'
SIGNALS     = ('score', 'cover', 'cushion')
N_BUCKETS   = 5
ALPHA       = 0.05
N_TESTS     = len(SIGNALS)          # Bonferroni: alpha / 3
Z_CRIT      = 2.394                 # two-sided z for alpha/3 = 0.0167
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
            with open(fp) as f:
                out.append((base[:-5], json.load(f)))
        except Exception:
            continue
    return out


def freeze_cohorts(force=False):
    """Split into quintiles by each signal, using the OLDEST snapshot only.
       Written once. Re-bucketing after seeing outcomes destroys the test."""
    if os.path.exists(COHORT_FILE) and not force:
        return json.load(open(COHORT_FILE))
    d = _days()
    if not d:
        return None
    date, snap = d[0]
    coh = {'frozen_on': date, 'written': datetime.now(timezone.utc).isoformat(), 'buckets': {}}
    for sig in SIGNALS:
        pairs = []
        for t, row in snap.items():
            if t.startswith('_'):
                continue
            v, px = row.get(sig), row.get('price')
            if v is None or not px:
                continue
            try:
                pairs.append((t, float(v)))
            except (TypeError, ValueError):
                continue
        if len(pairs) < N_BUCKETS * MIN_PER_BUCKET:
            continue
        pairs.sort(key=lambda kv: kv[1])
        n, per = len(pairs), max(1, len(pairs) // N_BUCKETS)
        b = {}
        for i, (t, _) in enumerate(pairs):
            b[t] = min(N_BUCKETS - 1, i // per)      # 0 = lowest signal
        coh['buckets'][sig] = b
    os.makedirs('history', exist_ok=True)
    with open(COHORT_FILE, 'w') as f:
        json.dump(coh, f, indent=1)
    return coh


def _returns(days, tickers):
    """Equal-weighted daily returns for a set of tickers, using only rows
       priced on BOTH days. A ticker that stops pricing simply drops out."""
    out = []
    for i in range(1, len(days)):
        _, a = days[i - 1]
        _, b = days[i]
        rs = []
        for t in tickers:
            pa, pb = (a.get(t) or {}).get('price'), (b.get(t) or {}).get('price')
            try:
                pa, pb = float(pa), float(pb)
            except (TypeError, ValueError):
                continue
            if pa and pb and abs(pb / pa - 1) < 0.5:      # ignore splits / bad quotes
                rs.append(pb / pa - 1)
        out.append(sum(rs) / len(rs) if rs else 0.0)
    return out


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
    """[(date, top_ret, bot_ret)] for consecutive priced pairs."""
    out = []
    for i in range(1, len(days)):
        (da, a), (db, b) = days[i - 1], days[i]
        def avg(ts):
            rs = []
            for t in ts:
                pa, pb = (a.get(t) or {}).get('price'), (b.get(t) or {}).get('price')
                try: pa, pb = float(pa), float(pb)
                except (TypeError, ValueError): continue
                if pa and pb and abs(pb / pa - 1) < 0.5: rs.append(pb / pa - 1)
            return sum(rs) / len(rs) if rs else 0.0
        out.append((db, avg(top), avg(bot)))
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
    coh = freeze_cohorts()
    days = _days()
    if not coh or len(days) < 2:
        return {'ok': False, 'days': len(days),
                'note': 'cohorts frozen; the test starts once there are two or more snapshots'
                        if coh else 'no history yet'}

    res = {'ok': True, 'frozen_on': coh['frozen_on'], 'days': len(days),
           'obs': len(days) - 1, 'floor': MIN_DAYS, 'signals': {}}

    for sig, b in coh['buckets'].items():
        top = [t for t, k in b.items() if k == N_BUCKETS - 1]
        bot = [t for t, k in b.items() if k == 0]
        if len(top) < MIN_PER_BUCKET or len(bot) < MIN_PER_BUCKET:
            continue
        rt, rb = _returns(days, top), _returns(days, bot)
        spread = [x - y for x, y in zip(rt, rb)]
        n = len(spread)
        if n < 2:
            continue
        mu = sum(spread) / n
        var = sum((x - mu) ** 2 for x in spread) / (n - 1)
        sd = math.sqrt(var) if var > 0 else 0.0
        t_stat = (mu * math.sqrt(n) / sd) if sd else 0.0
        # projection: trading days needed for |t| to reach the adjusted critical value
        need = int(math.ceil((Z_CRIT * sd / abs(mu)) ** 2)) if (sd and mu) else None
        ser = _daily_series(days, top, bot)
        mo  = by_period(ser, 'month')
        yr  = by_period(ser, 'year')
        cum = _compound([x for x in spread])
        ann = ((1 + cum) ** (252.0 / n) - 1) if n else None
        res['signals'][sig] = dict(
            n_top=len(top), n_bot=len(bot), obs=n,
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
