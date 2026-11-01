"""Daily index moves and a market-heat thermometer (0 = panic, 100 = euphoria).

Only inputs the nightly build can fetch itself are used: Yahoo closes for the
indices, VIX, the S&P 500 against its 50- and 200-day averages, the share of
the universe above its 200-day average, and CNN's Fear & Greed index when its
public endpoint answers. BofA Bull & Bear and the AAII survey have no free
machine-readable source; they are left out, never estimated. The thermometer
is information for timing and is not part of any stock score.
"""
import json
import math
import urllib.request
from datetime import datetime, timezone
from html import escape

INDICES = (('^GSPC', 'S&P 500'), ('^NDX', 'Nasdaq 100'), ('^DJI', 'Dow Jones'), ('^RUT', 'Russell 2000'),
           ('^STOXX50E', 'Euro Stoxx 50'), ('^GDAXI', 'DAX'), ('^IBEX', 'IBEX 35'), ('^VIX', 'VIX'),
           ('^TNX', 'US 10Y'), ('EURUSD=X', 'EUR/USD'), ('COP=X', 'USD/COP'), ('CL=F', 'WTI'), ('GC=F', 'Gold'))
FEAR_GREED_URL = 'https://production.dataviz.cnn.io/index/fearandgreed/graphdata'
BANDS = ((20, 'Panic'), (40, 'Fear'), (60, 'Neutral'), (80, 'Greed'), (101, 'Euphoria'))

CSS = """
.pulse-strip{display:flex;flex-wrap:wrap;gap:4px 16px;align-items:baseline;padding:8px 12px;margin:0 0 10px;border:1px solid var(--line);border-radius:8px;background:#0e1822;font-size:12px;font-variant-numeric:tabular-nums}
.pulse-strip .pulse-item{white-space:nowrap}.pulse-strip b{font-weight:600;color:#cfe0ee}.pulse-up{color:#66e39c}.pulse-down{color:#f06a6a}
.pulse-strip .pulse-heat{font-weight:650}.pulse-strip small{color:var(--mu)}
.pulse-thermo .pulse-bar{display:flex;height:12px;border-radius:6px;overflow:hidden;margin:10px 0 4px;position:relative}
.pulse-thermo .pulse-bar span{flex:1}.pulse-thermo .pulse-marker{position:absolute;top:-3px;width:3px;height:18px;background:#fff}
.pulse-thermo table td{padding:4px 8px}.pulse-thermo .pulse-big{font-size:34px;font-weight:700}
"""


def _clip(value):
    return max(0., min(100., value))


def _finite(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def band(score):
    return next(name for limit, name in BANDS if score < limit) if score is not None else None


def _series(frame, symbol):
    try:
        column = frame['Close'][symbol] if symbol in frame['Close'] else None
    except (KeyError, TypeError):
        column = None
    if column is None:
        return []
    return [(idx.date().isoformat(), float(v)) for idx, v in column.dropna().items() if math.isfinite(float(v))]


def _fear_greed(fetch=None):
    try:
        if fetch is not None:
            payload = fetch(FEAR_GREED_URL)
        else:
            request = urllib.request.Request(FEAR_GREED_URL, headers={
                'User-Agent': 'Mozilla/5.0 (InvestorAce market pulse)', 'Accept': 'application/json'})
            with urllib.request.urlopen(request, timeout=15) as response:
                payload = json.loads(response.read().decode('utf-8'))
        block = payload.get('fear_and_greed') or {}
        score = _finite(block.get('score'))
        stamp = str(block.get('timestamp') or '')[:10] or None
        return dict(value=round(score, 1), date=stamp) if score is not None else None
    except Exception:
        return None


def summarize(closes, universe_closes, fear_greed=None, as_of=None):
    """Index moves and thermometer from {symbol: [(date, close)]} series."""
    moves = []
    for symbol, name in INDICES:
        series = closes.get(symbol) or []
        if len(series) >= 2 and series[-2][1]:
            (_, prev), (day, last) = series[-2], series[-1]
            moves.append(dict(symbol=symbol, name=name, close=last, date=day,
                              change_pct=100 * (last / prev - 1)))
    components = {}
    vix = closes.get('^VIX') or []
    if vix:
        components['vix'] = dict(value=round(vix[-1][1], 2), date=vix[-1][0],
                                 score=round(_clip((40 - vix[-1][1]) / 30 * 100), 1))
    spx = [v for _, v in closes.get('^GSPC') or []]
    if len(spx) >= 200:
        ma200, ma50 = sum(spx[-200:]) / 200, sum(spx[-50:]) / 50
        d200, d50 = 100 * (spx[-1] / ma200 - 1), 100 * (spx[-1] / ma50 - 1)
        day = closes['^GSPC'][-1][0]
        components['sp500_ma200'] = dict(value=round(d200, 2), date=day, score=round(_clip(50 + 5 * d200), 1))
        components['sp500_ma50'] = dict(value=round(d50, 2), date=day, score=round(_clip(50 + 10 * d50), 1))
    above = total = 0
    for series in universe_closes.values():
        values = [v for _, v in series]
        if len(values) >= 200:
            total += 1
            above += values[-1] > sum(values[-200:]) / 200
    if total >= 20:
        share = 100 * above / total
        components['universe_above_ma200'] = dict(value=round(share, 1), count=total, score=round(share, 1))
    if fear_greed:
        components['fear_greed'] = dict(value=fear_greed['value'], date=fear_greed.get('date'),
                                        score=fear_greed['value'])
    scores = [c['score'] for c in components.values()]
    heat = round(sum(scores) / len(scores), 1) if len(scores) >= 3 else None
    return dict(schema='market-pulse-v1', as_of=(as_of or datetime.now(timezone.utc)).isoformat(),
                moves=moves, components=components, heat=heat, band=band(heat),
                omitted=['BofA Bull & Bear (no free machine-readable source)',
                         'AAII sentiment survey (no free machine-readable source)'])


def read(universe_symbols=(), download=None, fear_greed=None, as_of=None):
    """Fetch one year of closes for indices and universe; None if Yahoo fails."""
    try:
        if download is None:
            import yfinance as yf
            download = yf.download
        symbols = [s for s, _ in INDICES] + sorted(set(universe_symbols))
        frame = download(symbols, period='1y', interval='1d', auto_adjust=False,
                         progress=False, threads=True, group_by='column')
    except Exception:
        return None
    closes = {s: _series(frame, s) for s, _ in INDICES}
    universe = {s: _series(frame, s) for s in set(universe_symbols)}
    return summarize(closes, universe, _fear_greed(fear_greed), as_of)


def _number(value, digits=2):
    return format(value, f',.{digits}f')


def strip(pulse):
    """One line at the very top: daily moves and the market heat."""
    if not pulse or not pulse.get('moves'):
        return ''
    items = []
    for m in pulse['moves']:
        digits = 4 if m['symbol'] in ('EURUSD=X',) else 0 if m['symbol'] == 'COP=X' else 2
        css = 'pulse-up' if m['change_pct'] > 0 else 'pulse-down' if m['change_pct'] < 0 else ''
        items.append('<span class="pulse-item"><b>' + escape(m['name']) + '</b> ' + _number(m['close'], digits)
                     + ' <span class="' + css + '">' + ('%+.2f' % m['change_pct']) + '%</span></span>')
    heat = pulse.get('heat')
    if heat is not None:
        items.append('<a class="pulse-item pulse-heat" href="#market-heat"><span>Market heat</span> <b>'
                     + _number(heat, 0) + '</b>/100 · <span>' + escape(pulse['band']) + '</span></a>')
    last = max(m['date'] for m in pulse['moves'])
    return ('<div class="pulse-strip" id="market-pulse">' + ''.join(items)
            + '<small><span>Closing date:</span> ' + escape(last) + '</small></div>')


NAMES = {'vix': 'VIX (inverted)', 'sp500_ma200': 'S&P 500 vs 200-day average',
         'sp500_ma50': 'S&P 500 vs 50-day average', 'universe_above_ma200': 'Universe above 200-day average',
         'fear_greed': 'CNN Fear & Greed'}


def thermometer(pulse):
    """Box with the heat score, its bar and every component that was available."""
    if not pulse or pulse.get('heat') is None:
        return ''
    heat = pulse['heat']
    colours = ('#0b6b2b', '#7fb07f', '#c8c6b8', '#7a4a0a', '#8f2525')
    bar = ''.join('<span style="background:' + c + '"></span>' for c in colours)
    def shown(k, value):
        if k.startswith('sp500_'):
            return ('%+.1f' % value) + '%'
        return _number(value, 1) + ('%' if k == 'universe_above_ma200' else '')
    rows = ''.join('<tr><td>' + escape(NAMES[k]) + '</td><td class="mono">' + shown(k, c['value'])
                   + '</td><td class="mono"><b>'
                   + _number(c['score'], 0) + '</b>/100</td></tr>'
                   for k, c in pulse['components'].items())
    return ('<div class="box pulse-thermo" id="market-heat"><h2>Market heat</h2>'
            '<span class="pulse-big">' + _number(heat, 0) + '</span> /100 · <b>' + escape(pulse['band']) + '</b>'
            '<div class="pulse-bar">' + bar + '<i class="pulse-marker" style="left:' + _number(heat, 1)
            + '%"></i></div><small class="opportunity-metrics">Panic · buy — Neutral — Euphoria · sell</small>'
            '<div class="tw"><table><tbody>' + rows + '</tbody></table></div>'
            '<p class="opportunity-metrics">Simple average of the available indicators on a 0–100 scale '
            '(0 = panic, 100 = euphoria). Own index, not official, and not part of any stock score. '
            'BofA Bull &amp; Bear and the AAII survey have no free machine-readable source and are left out.</p></div>')
