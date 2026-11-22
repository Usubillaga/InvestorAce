"""Claude's independent drawdown and rebound study for the S&P 500, Nasdaq, Dow and DAX (asked for on 22 Nov 2026).

Written separately from correction_study/ (Codex) to check it: own download, own episode and analog code, and a side-by-
side comparison of the shared figures on the page.

* Episodes: every fall of 10% or more from a record close until the record is regained (open when not regained).
  US episodes are matched with NBER recessions (peak and trough months, nber.org/research/business-cycle-dating).
* Analogs: in every earlier record-to-record cycle, the first close at least as far below its record as the index is
  today, whether or not that cycle went on to -10% (the same rule as Codex's index_paths.py). From that close, the next 63 sessions are followed: whether +5% or +10% above it was reached within 5/21/42/63 sessions,
  whether +5% or -5% came first, the best and the final level, and the median path with its middle half.
* Charts show the median path and the band of the middle half of the analogs, not one chosen historical path: with 11 to
  25 cases, a single line would suggest a precision the sample does not have.

Limits: price indices (dividends excluded) except the DAX, which Yahoo serves as a total-return index, so its rebounds are
slightly flattered; Yahoo's Dow starts in 1992 and its DAX in 1987, so they have fewer episodes; the analogs overlap in
calendar time across indices; history is a frequency, not a forecast.
"""
import json
import math
import statistics
from datetime import date
from html import escape
from pathlib import Path

INDICES = {'^GSPC': 'S&P 500', '^IXIC': 'Nasdaq Composite', '^DJI': 'Dow Jones Industrial Average', '^GDAXI': 'DAX'}
OUT = Path('backtests') / 'crash_study.json'
PAGE = 'crash-study.html'
HORIZON, HORIZONS = 63, (5, 21, 42, 63)
# NBER US business-cycle peaks and troughs (months).
NBER = [('1926-10', '1927-11'), ('1929-08', '1933-03'), ('1937-05', '1938-06'), ('1945-02', '1945-10'),
        ('1948-11', '1949-10'), ('1953-07', '1954-05'), ('1957-08', '1958-04'), ('1960-04', '1961-02'),
        ('1969-12', '1970-11'), ('1973-11', '1975-03'), ('1980-01', '1980-07'), ('1981-07', '1982-11'),
        ('1990-07', '1991-03'), ('2001-03', '2001-11'), ('2007-12', '2009-06'), ('2020-02', '2020-04')]


def episodes(dates, closes, threshold=0.10):
    """[(peak, trough, recovery or None)] as indices into closes, for falls of `threshold` or more from a record."""
    out, peak, active, low = [], 0, False, 0
    for i, c in enumerate(closes):
        if not active:
            if c >= closes[peak]:
                peak = i
            elif c <= closes[peak] * (1 - threshold):
                active, low = True, i
        else:
            if c < closes[low]:
                low = i
            if c >= closes[peak]:
                out.append((peak, low, i))
                active, peak = False, i
    if active:
        out.append((peak, low, None))
    return out


def recession(start, end):
    a, b = start[:7], end[:7]
    return any(not (b < p or a > t) for p, t in NBER)


def analogs(dates, closes, eps, depth, horizon=HORIZON):
    """Forward paths (ratios to the signal close) from the first close at or below `depth` below the running record,
    once per record-to-record cycle, including cycles that never became a 10% episode (a -7% fall is compared with
    every earlier -7% fall, not only with those that went on to -10%). The current, open cycle is left out."""
    current = max(range(len(closes)), key=lambda i: (closes[i], i))
    out, peak, crossed = [], 0, False
    for i, price in enumerate(closes):
        if price >= closes[peak]:
            peak, crossed = i, False
        elif not crossed and price <= closes[peak] * (1 + depth) + 1e-9:
            crossed = True
            if peak >= current or i + horizon >= len(closes):
                continue
            out.append(dict(signal=dates[i], peak=dates[peak],
                            path=[closes[i + k] / price - 1 for k in range(horizon + 1)]))
    return out


def stats(cases, horizons=HORIZONS):
    n = len(cases)
    if not n:
        return None

    def hit(path, level, h):
        return any(x >= level for x in path[1:h + 1])

    first = {'up': 0, 'down': 0, 'neither': 0}
    to_up = []
    for c in cases:
        p = c['path']
        up = next((k for k, x in enumerate(p) if k and x >= 0.05), None)
        down = next((k for k, x in enumerate(p) if k and x <= -0.05), None)
        if up is not None and (down is None or up < down):
            first['up'] += 1
        elif down is not None:
            first['down'] += 1
        else:
            first['neither'] += 1
        if up is not None:
            to_up.append(up)
    band = []
    for k in range(len(cases[0]['path'])):
        xs = sorted(c['path'][k] for c in cases)
        band.append([_q(xs, .25), statistics.median(xs), _q(xs, .75)])
    winner = max(first, key=first.get)
    return dict(
        n=n, first=first, winner=winner, winner_share=first[winner] / n, winner_ci=wilson(first[winner], n),
        reach5={str(h): sum(hit(c['path'], 0.05, h) for c in cases) for h in horizons},
        reach10={str(h): sum(hit(c['path'], 0.10, h) for c in cases) for h in horizons},
        best_median=statistics.median(max(c['path'][1:]) for c in cases),
        final_median=statistics.median(c['path'][-1] for c in cases),
        sessions_to_5_median=statistics.median(to_up) if to_up else None, band=band,
        signals=[c['signal'] for c in cases])


def _q(xs, q):
    pos = (len(xs) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def wilson(k, n, z=1.96):
    if not n:
        return None
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return [(c - h) / d, (c + h) / d]


def study(series):
    """series: {symbol: (dates as ISO strings, closes)} -> result document."""
    out = {}
    for symbol, (dates, closes) in series.items():
        eps = episodes(dates, closes)
        rows = []
        for peak, low, rec in eps:
            d0, d1 = date.fromisoformat(dates[peak]), date.fromisoformat(dates[low])
            rows.append(dict(peak=dates[peak], peak_close=closes[peak], trough=dates[low],
                             depth=closes[low] / closes[peak] - 1, days_to_trough=(d1 - d0).days,
                             recovery=dates[rec] if rec is not None else None,
                             days_to_recover=(date.fromisoformat(dates[rec]) - d1).days if rec is not None else None,
                             recession=recession(dates[peak], dates[low]) if symbol != '^GDAXI' else None))
        record = max(range(len(closes)), key=closes.__getitem__)
        depth = closes[-1] / closes[record] - 1
        current = dict(as_of=dates[-1], close=closes[-1], record=dates[record], record_close=closes[record],
                       depth=depth, days=(date.fromisoformat(dates[-1]) - date.fromisoformat(dates[record])).days)
        cases = analogs(dates, closes, eps, depth) if depth <= -0.05 else []
        out[symbol] = dict(name=INDICES.get(symbol, symbol), start=dates[0], current=current, episodes=rows,
                           analogs=stats(cases))
    return out


def download():
    import yfinance as yf
    raw = yf.download(list(INDICES), period='max', interval='1d', auto_adjust=False, progress=False,
                      threads=False, group_by='column')['Close']
    series = {}
    for symbol in INDICES:
        s = raw[symbol].dropna()
        s.index = s.index.tz_localize(None) if s.index.tz is not None else s.index
        series[symbol] = ([d.date().isoformat() for d in s.index], [round(float(x), 4) for x in s.values])
    return series


# ------------------------------------------------------------------ page
def _pct(x, digits=1):
    return '—' if x is None else f'{100 * x:+.{digits}f}%'


def _chart(st, width=460, height=170):
    band = st['band']
    lo = min(min(b[0] for b in band), -0.06)
    hi = max(max(b[2] for b in band), 0.06)
    sx = lambda k: 30 + k * (width - 40) / (len(band) - 1)
    sy = lambda v: 10 + (hi - v) * (height - 30) / (hi - lo)
    area = ' '.join(f'{sx(k):.1f},{sy(b[2]):.1f}' for k, b in enumerate(band)) + ' ' + ' '.join(
        f'{sx(k):.1f},{sy(b[0]):.1f}' for k, b in reversed(list(enumerate(band))))
    line = ' '.join(f'{sx(k):.1f},{sy(b[1]):.1f}' for k, b in enumerate(band))
    guide = ''.join(f'<line x1="30" x2="{width - 10}" y1="{sy(v):.1f}" y2="{sy(v):.1f}" stroke="#666" '
                    f'stroke-dasharray="{"0" if v == 0 else "3 3"}"/><text x="2" y="{sy(v) + 4:.1f}" font-size="10" '
                    f'fill="#999">{v:+.0%}</text>' for v in (0.05, 0, -0.05))
    return (f'<svg viewBox="0 0 {width} {height}" width="100%" style="max-width:{width}px" role="img" '
            f'aria-label="Median path and middle half of the analogs over {len(band) - 1} sessions">{guide}'
            f'<polygon points="{area}" fill="#c1d98b" fill-opacity=".25"/>'
            f'<polyline points="{line}" fill="none" stroke="#c1d98b" stroke-width="2"/>'
            f'<text x="{width - 10}" y="{height - 4}" font-size="10" fill="#999" text-anchor="end">'
            f'{len(band) - 1} sessions</text></svg>')


def render(result, codex=None):
    from war_scenario import shell
    parts = ['<h1>Drawdowns, rebounds and analogs</h1><p class="lead">Claude\'s independent study: own download and '
             'code, written to check Codex\'s correction atlas. Every fall of 10% or more from a record close, and '
             'what happened next in earlier falls as deep as today\'s. Frequencies from history, not forecasts.</p>']
    summary = []
    for symbol, r in result.items():
        a, c = r['analogs'], r['current']
        if not a:
            continue
        label = {'up': '+5% first', 'down': '−5% first', 'neither': 'neither within 63 sessions'}[a['winner']]
        summary.append(f'<tr><td class="l"><b>{escape(r["name"])}</b></td><td>{_pct(c["depth"])}</td><td>{c["days"]}</td>'
                       f'<td>{a["n"]}</td><td>{label}</td><td>{a["winner_share"]:.0%} '
                       f'[{a["winner_ci"][0]:.0%}–{a["winner_ci"][1]:.0%}]</td>'
                       f'<td>{a["reach5"]["63"]}/{a["n"]}</td><td>{_pct(a["best_median"])}</td><td>{_pct(a["final_median"])}</td></tr>')
    parts.append('<h2>Where each index stands, and what followed comparable falls</h2><div class="tw"><table><thead><tr>'
                 '<th class="l">Index</th><th>Below record</th><th>Days since record</th><th>Analogs</th>'
                 '<th>Most frequent first move</th><th>Share [95%]</th><th>Reached +5% in 63 sessions</th>'
                 '<th>Median best</th><th>Median after 63</th></tr></thead><tbody>' + ''.join(summary)
                 + '</tbody></table></div><div class="note">An analog is the first close of any earlier cycle as far '
                 'below its record as the index is now, also in cycles that never reached -10%; the analogs of the four indices overlap in time, so they are not '
                 'independent evidence. "Median best" counts episodes that kept falling too.</div>')
    for symbol, r in result.items():
        a = r['analogs']
        if not a:
            continue
        reach = ' · '.join(f'{h} sessions: +5% {a["reach5"][str(h)]}/{a["n"]}, +10% {a["reach10"][str(h)]}/{a["n"]}'
                           for h in HORIZONS)
        parts.append(f'<h3>{escape(r["name"])}</h3>{_chart(a)}<p class="lead">Median path (line) and middle half '
                     f'(band) of {a["n"]} analogs. {reach}. Median wait for +5% among those that reached it: '
                     f'{a["sessions_to_5_median"] if a["sessions_to_5_median"] is not None else "—"} sessions.</p>')
    spx = result.get('^GSPC')
    if spx:
        eps = [e for e in spx['episodes'] if e['recovery'] is not None]
        groups = {'10% to 20%': [e for e in eps if -0.20 < e['depth'] <= -0.10],
                  '20% or more': [e for e in eps if e['depth'] <= -0.20]}
        gl = ''.join(
            f'<tr><td class="l">{k}</td><td>{len(v)}</td><td>{statistics.median(e["days_to_trough"] for e in v):.0f}</td>'
            f'<td>{statistics.median(e["days_to_recover"] for e in v):.0f}</td>'
            f'<td>{sum(bool(e["recession"]) for e in v)}/{len(v)}</td></tr>' for k, v in groups.items() if v)
        rows = ''.join(
            f'<tr><td>{e["peak"]}</td><td>{e["trough"]}</td><td>{_pct(e["depth"])}</td><td>{e["days_to_trough"]}</td>'
            f'<td>{e["recovery"] or "open"}</td><td>{e["days_to_recover"] if e["days_to_recover"] is not None else "—"}</td>'
            f'<td>{"yes" if e["recession"] else "no"}</td></tr>' for e in spx['episodes'])
        parts.append('<h2>S&amp;P 500: every fall of 10% or more since ' + escape(spx['start'][:4]) + '</h2>'
                     '<div class="tw"><table><thead><tr><th class="l">Completed episodes</th><th>Cases</th>'
                     '<th>Median days record → low</th><th>Median days low → record</th><th>With NBER recession</th>'
                     '</tr></thead><tbody>' + gl + '</tbody></table></div>'
                     '<div class="tw"><table><thead><tr><th>Record</th><th>Low</th><th>Fall</th><th>Days to low</th>'
                     '<th>Record regained</th><th>Days low → record</th><th>NBER recession</th></tr></thead><tbody>'
                     + rows + '</tbody></table></div>')
    if codex:
        parts.append('<h2>Check of Codex\'s figures</h2><div class="tw"><table><thead><tr><th class="l">Index</th>'
                     '<th>Codex analogs</th><th>Claude analogs</th><th>Codex first move</th><th>Claude first move</th>'
                     '<th>Agree</th></tr></thead><tbody>' + ''.join(codex) + '</tbody></table></div>'
                     '<div class="note">Differences can come from the data (download date, adjusted series) or the '
                     'method. A first version here took analogs only from 10% episodes and found 16 DAX cases instead of '
                     'Codex\'s 25: the DAX is only about 7% down, and nine earlier 7% falls stopped before -10%. Codex\'s '
                     'rule is the right one for this question and is used now. Codex charts one historical path per index; this page '
                     'shows the median and middle half instead.</div>')
    parts.append('<div class="note">Method and limits: crash_study.py. NBER recession dates are matched by month; '
                 'the DAX is a total-return index on Yahoo; Yahoo\'s Dow starts in 1992 and its DAX in 1987.</div>')
    return shell('Drawdowns and rebounds', ''.join(parts))


def codex_rows(root, result):
    """Compare with correction_study/index-paths.json when it exists."""
    names = {'SPX': '^GSPC', 'IXIC': '^IXIC', 'DJI': '^DJI', 'DAX': '^GDAXI', 'GDAXI': '^GDAXI'}
    try:
        doc = json.loads((Path(root) / 'correction_study' / 'index-paths.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    rows = []
    for key, theirs in (doc.get('indices') or {}).items():
        symbol = theirs.get('symbol') or names.get(key)
        mine = (result.get(symbol) or {}).get('analogs')
        if not mine:
            continue
        counts = theirs.get('counts') or {}
        if theirs.get('winner') == 'range':
            theirs = dict(theirs, winner='neither')
        their_first = f"{theirs.get('winner')} {theirs.get('hits')}/{theirs.get('n')}"
        my_first = f"{mine['winner']} {mine['first'][mine['winner']]}/{mine['n']}"
        agree = theirs.get('n') == mine['n'] and theirs.get('winner') == mine['winner'] and \
            counts.get(theirs.get('winner')) == mine['first'][mine['winner']]
        rows.append(f'<tr><td class="l">{escape(theirs.get("name") or key)}</td><td>{theirs.get("n")}</td>'
                    f'<td>{mine["n"]}</td><td>{escape(their_first)}</td><td>{escape(my_first)}</td>'
                    f'<td>{"yes" if agree else "<b>no</b>"}</td></tr>')
    return rows


def site_pages(root):
    try:
        result = json.loads((Path(root) / OUT).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return []
    try:
        return [(Path(PAGE), render(result, codex_rows(root, result)))]
    except (KeyError, TypeError, ValueError, statistics.StatisticsError):
        return []


def main():
    result = study(download())
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(result, indent=1, allow_nan=False) + '\n', encoding='utf-8')
    for s, r in result.items():
        a = r['analogs']
        print(s, r['current']['as_of'], f"{r['current']['depth']:+.2%}", len(r['episodes']),
              a and (a['n'], a['winner'], a['first']))


if __name__ == '__main__':
    main()
