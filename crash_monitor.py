"""Industry crash monitor after Greenwood, Shleifer & You (2019), "Bubbles for Fama".

A run-up is a two-year industry return above 100%, both raw and net of the
market. A crash is a 40% fall from the running peak within the following two
years. History (Kenneth French's 49 value-weighted US industries since 1926)
gives the base rates; the nightly build applies the same rules to industry
ETFs and to the universe. This is information next to the score: it never
changes a score, a label or a portfolio, and it gives probabilities, not dates.
"""
import io
import json
import math
import zipfile
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from statistics import median, pstdev

SCHEMA = 'crash-monitor-v1'
CALIBRATION = Path(__file__).resolve().parent / 'history' / '_crash_calibration.json'
REFRESH_DAYS = 35        # the French library updates monthly
FF_BASE = 'https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/'
FF_FILES = ('49_Industry_Portfolios_CSV.zip', 'F-F_Research_Data_Factors_CSV.zip')
HORIZON = 24            # months, before and after identification
RUN_UP = 1.0            # +100% over 24 months, raw and net of market
CRASH = 0.40            # 40% below the running peak
MIN_FIRMS = 10          # tiny industries are noise, not bubbles
Z90 = 1.6449


# --- Kenneth French CSV ---------------------------------------------------

def parse_section(text, title):
    """Monthly rows of one section: (names, [(yyyymm, [value or None])]).

    `title` is the section heading, or the header row's first column names
    (',Mkt-RF') for the factor file, whose monthly table has no heading."""
    lines = text.splitlines()
    if title.startswith(','):
        start = next(i for i, line in enumerate(lines) if line.replace(' ', '').startswith(title)) - 1
    else:
        start = next(i for i, line in enumerate(lines) if line.strip() == title)
    names = [n.strip() for n in lines[start + 1].split(',')[1:]]
    rows = []
    for line in lines[start + 2:]:
        cells = [c.strip() for c in line.split(',')]
        if not cells or not cells[0].isdigit() or len(cells[0]) != 6:
            break
        values = []
        for cell in cells[1:]:
            try:
                value = float(cell)
            except ValueError:
                value = None
            values.append(None if value is None or value <= -99.99 else value)
        rows.append((int(cells[0]), values))
    return names, rows


def _csv_from_zip(blob):
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        name = next(n for n in archive.namelist() if n.lower().endswith('.csv'))
        return archive.read(name).decode('latin-1')


def load_french(industry_zip, factor_zip):
    """{industry: [(yyyymm, return)]}, {industry: {yyyymm: firms}}, [(yyyymm, market return)]."""
    text = _csv_from_zip(industry_zip)
    names, rows = parse_section(text, 'Average Value Weighted Returns -- Monthly')
    industries = {n: [(ym, v[i] / 100) for ym, v in rows if v[i] is not None] for i, n in enumerate(names)}
    _, firm_rows = parse_section(text, 'Number of Firms in Portfolios')
    firms = {n: {ym: v[i] for ym, v in firm_rows if v[i] is not None} for i, n in enumerate(names)}
    _, factor_rows = parse_section(_csv_from_zip(factor_zip), ',Mkt-RF')
    market = [(ym, (v[0] + v[3]) / 100) for ym, v in factor_rows if v[0] is not None and v[3] is not None]
    return industries, firms, market


# --- the rules ------------------------------------------------------------

def index(returns):
    out, level = [], 1.
    for r in returns:
        level *= 1 + r
        out.append(level)
    return out


def outcome(prices, t0, horizon=HORIZON):
    """Crash within `horizon` months after t0, measured from the running peak."""
    peak, worst, crash_month = prices[t0], 0., None
    end = min(len(prices) - 1, t0 + horizon)
    for t in range(t0 + 1, end + 1):
        peak = max(peak, prices[t])
        drawdown = prices[t] / peak - 1
        worst = min(worst, drawdown)
        if crash_month is None and drawdown <= -CRASH:
            crash_month = t - t0
    complete = crash_month is not None or end - t0 == horizon
    return dict(crash=crash_month is not None, months_to_crash=crash_month, max_drawdown=worst,
                forward_return=prices[end] / prices[t0] - 1, complete=complete, months_observed=end - t0)


def features(prices, returns, t):
    """What the run-up looked like when it was first identified."""
    recent, before = returns[t - 11:t + 1], returns[t - 23:t - 11]
    vol_ratio = pstdev(recent) / pstdev(before) if pstdev(before) > 0 else None
    raw = prices[t] / prices[t - HORIZON] - 1
    six = prices[t] / prices[t - 6] - 1
    # Positive: the last six months ran faster than the two-year average pace.
    acceleration = math.log(1 + six) - math.log(1 + raw) / 4
    return dict(vol_ratio=vol_ratio, acceleration=acceleration)


def episodes(name, series, market, firms=None, *, min_firms=MIN_FIRMS):
    """Run-up episodes of one industry, each with its outcome and path."""
    market_by = dict(market)
    months = [ym for ym, _ in series if ym in market_by]
    returns = [r for ym, r in series if ym in market_by]
    prices = index(returns)
    mprices = index([market_by[ym] for ym in months])
    out, blocked_until = [], -1
    for t in range(HORIZON, len(months)):
        if t <= blocked_until:
            continue
        raw = prices[t] / prices[t - HORIZON] - 1
        net = raw - (mprices[t] / mprices[t - HORIZON] - 1)
        if raw <= RUN_UP or net <= RUN_UP:
            continue
        count = (firms or {}).get(months[t])
        if firms is not None and (count is None or count < min_firms):
            continue
        before = (firms or {}).get(months[t - HORIZON])
        result = dict(industry=name, start=str(months[t]), raw=raw, net=net, firms=count,
                      firm_growth=(count / before - 1) if count and before else None,
                      **features(prices, returns, t), **outcome(prices, t))
        result['path'] = [round(prices[t + k] / prices[t], 4) if 0 <= t + k < len(prices) else None
                          for k in range(-HORIZON, HORIZON + 1)]
        out.append(result)
        blocked_until = t + HORIZON
    return out


def wilson(hits, n, z=Z90):
    if not n:
        return None, None
    p = hits / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return max(0., centre - half), min(1., centre + half)


def rate(rows):
    hits = sum(1 for r in rows if r['crash'])
    low, high = wilson(hits, len(rows))
    return dict(n=len(rows), crashes=hits, p=hits / len(rows) if rows else None, low=low, high=high)


RISK_FEATURES = (('big_run_up', 'Run-up of 150% or more net of market', lambda e: e['net'] >= 1.5),
                 ('rising_volatility', 'Volatility over the last 12 months above the 12 months before',
                  lambda e: (e['vol_ratio'] or 0) > 1),
                 ('accelerating', 'Last 6 months faster than the 2-year pace', lambda e: e['acceleration'] > 0))


def baseline(industries, market, firms, *, min_firms=MIN_FIRMS):
    """Share of all industry-months followed by a 40% crash within 24 months."""
    market_by = dict(market)
    hits = total = 0
    for name, series in industries.items():
        months = [ym for ym, _ in series if ym in market_by]
        prices = index([r for ym, r in series if ym in market_by])
        for t in range(HORIZON, len(prices) - HORIZON):
            if (firms.get(name) or {}).get(months[t], 0) < min_firms:
                continue
            total += 1
            hits += outcome(prices, t)['crash']
    return dict(n=total, crashes=hits, p=hits / total if total else None)


RECENT_MONTHS = 72


def recent_series(industries, firms, market, months=RECENT_MONTHS):
    """The last six years of every industry and the market, as index levels."""
    market_by = dict(market)
    start = [ym for ym, _ in market][-months]
    def levels(rows):
        return [[ym, round(v, 5)] for (ym, _), v in zip(rows, index([r for _, r in rows]))]
    out = {}
    for name, series in sorted(industries.items()):
        rows = [(ym, r) for ym, r in series if ym in market_by and ym >= start]
        if len(rows) > HORIZON:
            out[name] = dict(firms=(firms.get(name) or {}).get(rows[-1][0]), levels=levels(rows))
    return dict(market=levels([(ym, r) for ym, r in market if ym >= start]), industries=out)


def calibrate(industries, firms, market, *, source_end=None):
    found = [e for name, series in sorted(industries.items())
             for e in episodes(name, series, market, firms.get(name) or {})]
    done = [e for e in found if e['complete']]
    crashed = [e for e in done if e['crash']]
    calm = [e for e in done if not e['crash']]
    growth = median([e['firm_growth'] for e in done if e['firm_growth'] is not None])
    splits = []
    for key, text, test in RISK_FEATURES:
        splits.append(dict(key=key, text=text, yes=rate([e for e in done if test(e)]),
                           no=rate([e for e in done if not test(e)])))
    splits.append(dict(key='firm_growth', text=f'Number of listed firms grew more than the median ({growth:.0%}) '
                       'over the run-up (issuance proxy)',
                       yes=rate([e for e in done if (e['firm_growth'] or 0) > growth]),
                       no=rate([e for e in done if (e['firm_growth'] or 0) <= growth])))
    after_drawdown = {}
    for level in (.2, .3):
        reached = [e for e in done if e['max_drawdown'] <= -level]
        after_drawdown[f'{int(level * 100)}'] = rate(reached)
    def mean_path(rows):
        out = []
        for k in range(2 * HORIZON + 1):
            values = [r['path'][k] for r in rows if r['path'][k] is not None]
            out.append(round(sum(values) / len(values), 4) if values else None)
        return out
    return dict(schema=SCHEMA, source='Kenneth R. French Data Library: 49 industry portfolios (value-weighted) '
                'and Fama/French market factor, monthly, total returns', source_end=source_end,
                generated_at=datetime.now(timezone.utc).isoformat(timespec='seconds'),
                rules=dict(run_up='24-month return above 100% raw and net of market', crash='40% below the running '
                           'peak within 24 months', min_firms=MIN_FIRMS, horizon_months=HORIZON),
                episodes_total=len(found), open_episodes=[e['industry'] + ' ' + e['start'] for e in found
                                                          if not e['complete']],
                base=rate(done), baseline=baseline(industries, market, firms), splits=splits,
                after_drawdown=after_drawdown,
                paths=dict(crash=mean_path(crashed), calm=mean_path(calm), months=list(range(-HORIZON, HORIZON + 1))),
                episodes=[{k: (round(v, 4) if isinstance(v, float) else v) for k, v in e.items() if k != 'path'}
                          for e in done],
                recent=recent_series(industries, firms, market))


def refresh_calibration(fetch=None, path=CALIBRATION):
    """Download the French data and rewrite crash_calibration.json."""
    import urllib.request
    fetch = fetch or (lambda url: urllib.request.urlopen(
        urllib.request.Request(url, headers={'User-Agent': 'InvestorAce crash monitor'}), timeout=60).read())
    industry_zip, factor_zip = (fetch(FF_BASE + name) for name in FF_FILES)
    industries, firms, market = load_french(industry_zip, factor_zip)
    result = calibrate(industries, firms, market, source_end=str(max(ym for ym, _ in market)))
    Path(path).write_text(json.dumps(result, sort_keys=True, separators=(',', ':')) + '\n', encoding='utf-8')
    return result


# --- live monitor ---------------------------------------------------------

# A fixed list by area, independent of the universe. Themes are younger and more
# concentrated than industries; countries are measured in USD against the S&P 500.
INDUSTRY_ETFS = (
    ('XLK', 'Technology', 'US sector'), ('XLC', 'Communication services', 'US sector'),
    ('XLY', 'Consumer discretionary', 'US sector'), ('XLP', 'Consumer staples', 'US sector'),
    ('XLE', 'Energy', 'US sector'), ('XLB', 'Materials', 'US sector'), ('XLV', 'Health care', 'US sector'),
    ('XLF', 'Financials', 'US sector'), ('XLI', 'Industrials', 'US sector'), ('XLRE', 'Real estate', 'US sector'),
    ('XLU', 'Utilities', 'US sector'),
    ('SOXX', 'Semiconductors', 'US industry'), ('IGV', 'Software', 'US industry'),
    ('SKYY', 'Cloud computing', 'US industry'), ('CIBR', 'Cybersecurity', 'US industry'),
    ('XTL', 'Telecom', 'US industry'), ('XRT', 'Retail', 'US industry'), ('ITB', 'Homebuilders', 'US industry'),
    ('JETS', 'Airlines', 'US industry'), ('PEJ', 'Leisure and entertainment', 'US industry'),
    ('XOP', 'Oil and gas producers', 'US industry'), ('OIH', 'Oil services', 'US industry'),
    ('XME', 'Metals and mining', 'US industry'), ('COPX', 'Copper miners', 'US industry'),
    ('GDX', 'Gold miners', 'US industry'), ('SIL', 'Silver miners', 'US industry'),
    ('LIT', 'Lithium and batteries', 'US industry'), ('MOO', 'Agribusiness', 'US industry'),
    ('XBI', 'Biotech', 'US industry'), ('XPH', 'Pharmaceuticals', 'US industry'),
    ('IHI', 'Medical devices', 'US industry'), ('IHF', 'Health care providers', 'US industry'),
    ('KBE', 'Banks', 'US industry'), ('KRE', 'Regional banks', 'US industry'), ('KIE', 'Insurance', 'US industry'),
    ('IAI', 'Brokers and exchanges', 'US industry'), ('IYT', 'Transportation', 'US industry'),
    ('ITA', 'Aerospace and defence', 'US industry'), ('PAVE', 'Infrastructure', 'US industry'),
    ('BOTZ', 'Robotics and AI', 'Theme'), ('UFO', 'Space', 'Theme'), ('TAN', 'Solar', 'Theme'),
    ('ICLN', 'Clean energy', 'Theme'), ('NLR', 'Nuclear and power', 'Theme'), ('URA', 'Uranium', 'Theme'),
    ('WGMI', 'Bitcoin miners', 'Theme'), ('ARKK', 'Disruptive innovation', 'Theme'),
    ('KWEB', 'China internet', 'Theme'),
    ('EWJ', 'Japan', 'Country'), ('EWG', 'Germany', 'Country'), ('EWU', 'United Kingdom', 'Country'),
    ('EWQ', 'France', 'Country'), ('EWP', 'Spain', 'Country'), ('EWI', 'Italy', 'Country'),
    ('EZU', 'Eurozone', 'Country'), ('EWC', 'Canada', 'Country'), ('EWA', 'Australia', 'Country'),
    ('EWY', 'South Korea', 'Country'), ('EWT', 'Taiwan', 'Country'), ('INDA', 'India', 'Country'),
    ('FXI', 'China large caps', 'Country'), ('EWZ', 'Brazil', 'Country'), ('EWW', 'Mexico', 'Country'),
    ('COLO', 'Colombia', 'Country'), ('ARGT', 'Argentina', 'Country'), ('EZA', 'South Africa', 'Country'),
    ('TUR', 'Turkey', 'Country'), ('EEM', 'Emerging markets', 'Country'),
)
GROUPS = ('US sector', 'US industry', 'Theme', 'Country')
FRENCH_GROUP = 'All US stocks (French 49)'
FRENCH_NAMES = {
    'Agric': 'Agriculture', 'Food': 'Food products', 'Soda': 'Candy and soda', 'Beer': 'Beer and liquor',
    'Smoke': 'Tobacco', 'Toys': 'Recreation', 'Fun': 'Entertainment', 'Books': 'Printing and publishing',
    'Hshld': 'Consumer goods', 'Clths': 'Apparel', 'Hlth': 'Health care services', 'MedEq': 'Medical equipment',
    'Drugs': 'Pharmaceuticals', 'Chems': 'Chemicals', 'Rubbr': 'Rubber and plastics', 'Txtls': 'Textiles',
    'BldMt': 'Construction materials', 'Cnstr': 'Construction', 'Steel': 'Steel', 'FabPr': 'Fabricated products',
    'Mach': 'Machinery', 'ElcEq': 'Electrical equipment', 'Autos': 'Autos and trucks', 'Aero': 'Aircraft',
    'Ships': 'Ships and railroad equipment', 'Guns': 'Defence', 'Gold': 'Precious metals',
    'Mines': 'Industrial metal mining', 'Coal': 'Coal', 'Oil': 'Oil and gas', 'Util': 'Utilities',
    'Telcm': 'Communication', 'PerSv': 'Personal services', 'BusSv': 'Business services',
    'Hardw': 'Computer hardware', 'Softw': 'Software', 'Chips': 'Chips and electronic equipment',
    'LabEq': 'Measuring and control equipment', 'Paper': 'Business supplies', 'Boxes': 'Shipping containers',
    'Trans': 'Transportation', 'Whlsl': 'Wholesale', 'Rtail': 'Retail', 'Meals': 'Restaurants and hotels',
    'Banks': 'Banks', 'Insur': 'Insurance', 'RlEst': 'Real estate', 'Fin': 'Trading and finance',
    'Other': 'Other',
}
MARKET = 'SPY'
SECTOR_ETF = {
    'Semis': 'SOXX', 'Software': 'IGV', 'Ad Tech': 'IGV', 'Technology': 'XLK', 'AI Infra': 'XLK',
    'AdTech': 'XLC', 'Communication Services': 'XLC', 'Media': 'XLC',
    'Consumer Cyclical': 'XLY', 'Apparel': 'XLY', 'Automotive': 'XLY', 'Restaurant': 'XLY', 'Luxury': 'XLY',
    'Platform': 'XLY', 'Consumer Defensive': 'XLP', 'Staples': 'XLP', 'Energy': 'XLE', 'Midstream': 'XLE',
    'Materials': 'XLB', 'Healthcare': 'XLV', 'Pharma': 'XPH', 'MedTech': 'IHI', 'Health Ins': 'IHF',
    'Health Data': 'XLV', 'Animal Health': 'XLV', 'Biotech': 'XBI', 'Utilities': 'XLU', 'Industrials': 'XLI',
    'Services': 'XLI', 'Aerospace': 'ITA', 'Space': 'UFO', 'Real Estate': 'XLRE', 'REIT': 'XLRE',
    'Info Svcs': 'XLF',
}
TICKER_ETF = {'AMAT': 'SOXX', 'AMD': 'SOXX', 'MU': 'SOXX', 'FSLR': 'TAN', 'MSFT': 'IGV', 'INTU': 'IGV', 'ADSK': 'IGV',
              'MNDY': 'IGV', 'AG': 'SIL', 'B': 'GDX', 'FNV': 'GDX', 'CEG': 'NLR', 'VST': 'NLR', 'NRG': 'NLR',
              'BABA': 'KWEB', 'RCAT': 'ITA', 'BYRN': 'ITA'}


def industry_of(ticker, row):
    return TICKER_ETF.get(ticker) or SECTOR_ETF.get(row.get('sector') or '')


def _monthly(frame, symbol):
    try:
        column = frame['Close'][symbol] if symbol in frame['Close'] else None
    except (KeyError, TypeError):
        column = None
    if column is None:
        return []
    return [(idx.date().isoformat(), float(v)) for idx, v in column.dropna().items() if math.isfinite(float(v))]


def status(series, market, calibration):
    """Run-up episode of one monthly price series against the market."""
    by = dict(market)
    rows = [(d, v) for d, v in series if d in by]
    if len(rows) < HORIZON + 1:
        return dict(state='NO_DATA')
    dates = [d for d, _ in rows]
    prices = [v for _, v in rows]
    mprices = [by[d] for d in dates]
    returns = [0.] + [prices[i] / prices[i - 1] - 1 for i in range(1, len(prices))]
    last = len(prices) - 1
    raw = prices[last] / prices[last - HORIZON] - 1
    net = raw - (mprices[last] / mprices[last - HORIZON] - 1)
    out = dict(state='NO_RUN_UP', date=dates[last], price=prices[last], raw_24m=raw, net_24m=net)
    start, blocked_until = None, -1
    for t in range(HORIZON, len(prices)):
        if t <= blocked_until:
            continue
        r = prices[t] / prices[t - HORIZON] - 1
        if r > RUN_UP and r - (mprices[t] / mprices[t - HORIZON] - 1) > RUN_UP:
            start, blocked_until = t, t + HORIZON
    if start is None or last - start >= HORIZON:
        return out                      # no run-up, or its 24-month window has closed
    result = outcome(prices, start)
    peak = max(prices[start:])
    drawdown = prices[last] / peak - 1
    feats = features(prices, returns, start) if start >= HORIZON else {}
    out.update(state='CRASHED' if result['crash'] else 'RUN_UP', start=dates[start], months_since=last - start,
               start_price=prices[start], peak=peak, drawdown=drawdown, max_drawdown=result['max_drawdown'],
               crash_line=(1 - CRASH) * peak, run_up_raw=prices[start] / prices[start - HORIZON] - 1,
               run_up_net=(prices[start] / prices[start - HORIZON] - 1)
               - (mprices[start] / mprices[start - HORIZON] - 1), **feats,
               path=[round(prices[start + k] / prices[start], 4) if 0 <= start + k <= last else None
                     for k in range(-HORIZON, min(HORIZON, last - start) + 1)])
    if calibration and not result['crash']:
        if result['max_drawdown'] <= -.3:
            basis, odds = 'Already fell 30% from the peak', calibration['after_drawdown']['30']
        elif result['max_drawdown'] <= -.2:
            basis, odds = 'Already fell 20% from the peak', calibration['after_drawdown']['20']
        else:
            split = next(x for x in calibration['splits'] if x['key'] == 'rising_volatility')
            rising = (feats.get('vol_ratio') or 0) > 1
            basis = 'Volatility ' + ('rising' if rising else 'not rising') + ' at identification'
            odds = split['yes' if rising else 'no']
        out['probability'] = dict(basis=basis, **odds)
        separation = separation_month(calibration['paths'])
        out['separation_month'] = separation
        if separation is None or out['months_since'] < separation:
            out['path_closer_to'] = None          # both averages still sit near 1.0
            return out
        months = range(1, out['months_since'] + 1)
        def distance(reference):
            pairs = [(out['path'][HORIZON + k], reference[HORIZON + k]) for k in months
                     if reference[HORIZON + k] is not None]
            return math.sqrt(sum((a - b) ** 2 for a, b in pairs) / len(pairs)) if pairs else None
        crash, calm = distance(calibration['paths']['crash']), distance(calibration['paths']['calm'])
        out['path_closer_to'] = None if None in (crash, calm) else 'crash' if crash < calm else 'calm'
    return out


def separation_month(paths, gap=.05):
    """First month after identification where the crash and no-crash averages differ by `gap`."""
    for k in range(1, HORIZON + 1):
        a, b = paths['crash'][HORIZON + k], paths['calm'][HORIZON + k]
        if a is not None and b is not None and abs(a - b) >= gap:
            return k
    return None


def load_calibration(path=CALIBRATION):
    try:
        data = json.loads(Path(path).read_text(encoding='utf-8'))
        return data if data.get('schema') == SCHEMA else None
    except (OSError, ValueError):
        return None


def fresh_calibration(path=CALIBRATION, now=None, fetch=None, log=print):
    """The committed calibration, refreshed from the French library when stale."""
    current = load_calibration(path)
    now = now or datetime.now(timezone.utc)
    try:
        age = (now - datetime.fromisoformat(current['generated_at'])).days if current else None
    except (KeyError, TypeError, ValueError):
        age = None
    if current and age is not None and age < REFRESH_DAYS:
        return current
    try:
        result = refresh_calibration(fetch=fetch, path=path)
        log(f"Crash calibration refreshed: {len(result['episodes'])} episodes to {result['source_end']}")
        return result
    except Exception as exc:
        log('Crash calibration refresh failed, keeping the committed one:', type(exc).__name__)
        return current


def french_left_out(calibration):
    """Industries below the firm minimum, with their latest firm count."""
    recent = ((calibration or {}).get('recent') or {}).get('industries') or {}
    return sorted([name, int(item.get('firms') or 0)] for name, item in recent.items()
                  if (item.get('firms') or 0) < MIN_FIRMS)


def french_status(calibration):
    """All 49 US industries from the stored French series (every listed stock, monthly lag)."""
    recent = (calibration or {}).get('recent') or {}
    if not recent.get('market'):
        return []
    to_date = lambda ym: f'{ym // 100}-{ym % 100:02d}-01'
    market = [(to_date(ym), v) for ym, v in recent['market']]
    out = []
    for name, item in sorted((recent.get('industries') or {}).items()):
        if (item.get('firms') or 0) < MIN_FIRMS:
            continue
        series = [(to_date(ym), v) for ym, v in item['levels']]
        out.append(dict(etf=name, name=FRENCH_NAMES.get(name, name), group=FRENCH_GROUP, members=[],
                        firms=item.get('firms'), **status(series, market, calibration)))
    return out


def read(rows, download=None, calibration=None, as_of=None):
    """Industry ETFs and USD universe stocks, from five years of monthly closes."""
    calibration = calibration or load_calibration()
    try:
        if download is None:
            import yfinance as yf
            download = yf.download
        stocks = {t: r.get('yf') or t for t, r in rows.items() if (r.get('cur') or 'USD') == 'USD'}
        symbols = sorted({e for e, _, _ in INDUSTRY_ETFS} | {MARKET} | set(stocks.values()))
        frame = download(symbols, period='5y', interval='1mo', auto_adjust=True, progress=False,
                         threads=True, group_by='column')
    except Exception:
        return None
    market = _monthly(frame, MARKET)
    if len(market) < HORIZON + 1:
        return None
    members = {}
    for ticker, row in rows.items():
        members.setdefault(industry_of(ticker, row), []).append(ticker)
    industries = [dict(etf=etf, name=name, group=group, members=sorted(members.get(etf, [])),
                       **status(_monthly(frame, etf), market, calibration)) for etf, name, group in INDUSTRY_ETFS]
    universe = []
    for ticker, symbol in sorted(stocks.items()):
        result = status(_monthly(frame, symbol), market, None)
        if result['state'] != 'NO_DATA':
            universe.append(dict(ticker=ticker, industry=industry_of(ticker, rows[ticker]),
                                 **{k: v for k, v in result.items() if k != 'path'}))
    summary = None
    if calibration:
        summary = {k: calibration.get(k) for k in ('source', 'source_end', 'rules', 'base', 'baseline', 'splits',
                                                   'after_drawdown', 'paths', 'episodes_total', 'open_episodes')}
        summary['episodes'] = len(calibration.get('episodes', []))
    return dict(schema=SCHEMA, as_of=(as_of or datetime.now(timezone.utc)).isoformat(timespec='seconds'),
                market=MARKET, industries=industries, french=french_status(calibration),
                french_left_out=french_left_out(calibration), stocks=universe,
                calibration=summary)


# --- page -----------------------------------------------------------------

PAGE = 'crash-monitor.html'
STATES = {'RUN_UP': 'Run-up, no crash yet', 'CRASHED': 'Crash reached (−40% from peak)',
          'NO_RUN_UP': 'No run-up', 'NO_DATA': 'No data'}


def _pct(value, digits=0):
    return '—' if value is None else format(100 * value, f'+.{digits}f') + '%'


def _odds(p):
    if not p or p.get('p') is None:
        return '—'
    return (f"<b>{100 * p['p']:.0f}%</b> <span class=\"muted\">({100 * p['low']:.0f}–{100 * p['high']:.0f}%, "
            f"{p['crashes']} of {p['n']})</span>")


NEAR_GAP = .40      # within 40 points of the run-up rule counts as approaching one


def run_up_gap(row):
    """Points still missing to the run-up rule (both raw and net of market above 100%)."""
    raw, net = row.get('raw_24m'), row.get('net_24m')
    if raw is None or net is None:
        return None
    return max(0., RUN_UP - raw, RUN_UP - net)


def watch(row):
    """Ordering by risk: crash reached, then closest to the crash line, then closest to a run-up."""
    state = row.get('state')
    if state == 'CRASHED':
        return (0, 0., 'crash')
    if state == 'RUN_UP' and row.get('crash_line') and row.get('price'):
        return (1, 1 - row['crash_line'] / row['price'], 'risk')     # further fall needed
    gap = run_up_gap(row) if state == 'NO_RUN_UP' else None
    if gap is not None and gap <= NEAR_GAP:
        return (2, gap, 'near')
    return (3, -(row.get('net_24m') if row.get('net_24m') is not None else -9), 'other')


def distance(row):
    rank, value, kind = watch(row)
    if kind == 'crash':
        return 'crash reached'
    if kind == 'risk':
        return f'a further {100 * value:.0f}% fall reaches the crash line'
    if kind == 'near':
        return f'{100 * value:.0f} points from a run-up'
    return '—'


def chart(industry, paths):
    """Inline SVG: crash and calm averages, this industry and its crash line."""
    width, height, left, right, top, bottom = 720, 300, 44, 12, 12, 28
    values = [v for line in (paths['crash'], paths['calm'], industry['path']) for v in line if v is not None]
    line_level = industry['crash_line'] / industry['start_price']
    low, high = min(values + [line_level]) * .95, max(values + [line_level]) * 1.05
    x = lambda k: left + (k + HORIZON) / (2 * HORIZON) * (width - left - right)
    y = lambda v: top + (high - v) / (high - low) * (height - top - bottom)
    def poly(line, colour, dash=''):
        points = ' '.join(f'{x(k - HORIZON):.1f},{y(v):.1f}' for k, v in enumerate(line) if v is not None)
        return (f'<polyline fill="none" stroke="{colour}" stroke-width="2.2" {dash} points="{points}"/>'
                if points else '')
    grid = ''.join(f'<line x1="{left}" x2="{width - right}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="#2a3040"/>'
                   f'<text x="{left - 6}" y="{y(v) + 4:.1f}" text-anchor="end">{v:.1f}</text>'
                   for v in [round(low + i * (high - low) / 4, 1) for i in range(5)])
    ticks = ''.join(f'<text x="{x(k):.1f}" y="{height - 8}" text-anchor="middle">{k:+d}</text>'
                    for k in range(-HORIZON, HORIZON + 1, 6))
    return (f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Path of {escape(industry["etf"])} '
            f'against historical averages" style="width:100%;height:auto;font-size:11px;fill:#a0aabe">'
            + grid + ticks
            + f'<line x1="{x(0):.1f}" x2="{x(0):.1f}" y1="{top}" y2="{height - bottom}" stroke="#a0aabe" '
              'stroke-dasharray="4 4"/>'
            + f'<line x1="{left}" x2="{width - right}" y1="{y(line_level):.1f}" y2="{y(line_level):.1f}" '
              'stroke="#f06a6a" stroke-dasharray="6 4"/>'
            + poly(paths['calm'], '#66e39c', 'stroke-dasharray="2 4"')
            + poly(paths['crash'], '#f0a35e', 'stroke-dasharray="8 5"')
            + poly(industry['path'], '#5aa9ff') + '</svg>'
            + '<p class="muted" style="font-size:13px"><span style="color:#5aa9ff">━ '
            + escape(industry['etf']) + '</span> · <span style="color:#f0a35e">╍ history: crash average</span> · '
            '<span style="color:#66e39c">┈ history: no-crash average</span> · <span style="color:#f06a6a">╍ crash '
            'line (−40% from peak)</span> · 1.0 = month of identification, x-axis in months</p>')


def render(monitor, *, now=None):
    from war_scenario import shell
    now = now or datetime.now(timezone.utc)
    cal = monitor.get('calibration') or {}
    base, baseline = cal.get('base') or {}, cal.get('baseline') or {}
    body = ['<h1>Crash monitor</h1><p class="lead">Which industries had a bubble-sized run-up, and how often '
            'such run-ups ended in a crash in 100 years of US data. Probabilities, not dates: nobody can time a '
            f'crash. Updated {escape(str(monitor.get("as_of", now.isoformat()))[:16].replace("T", " "))} UTC from '
            'monthly closes.</p>']
    if base:
        body.append(
            '<div class="tiles">'
            f'<div class="tile"><span>Run-ups since 1926</span><b>{base["n"]}</b></div>'
            f'<div class="tile"><span>Ended in a crash</span><b>{100 * base["p"]:.0f}%</b></div>'
            f'<div class="tile"><span>Any industry-month (baseline)</span><b>{100 * baseline["p"]:.0f}%</b></div>'
            '</div><div class="note"><b>Rules</b> (Greenwood, Shleifer &amp; You, "Bubbles for Fama", Journal of '
            'Financial Economics 2019): a run-up is a 24-month return above 100%, raw and net of the market; a crash '
            'is a fall of 40% from the running peak within the next 24 months. History: '
            f'{escape(cal.get("source", ""))}, to {escape(str(cal.get("source_end", "")))}, industries with at least '
            f'{(cal.get("rules") or {}).get("min_firms", MIN_FIRMS)} firms. The paper reports about 53% for its own '
            'sample; this replication counts every complete episode. Ranges are 90% intervals.</div>')
    french, etfs = monitor.get('french') or [], monitor.get('industries') or []
    flagged = sorted((i for i in french + etfs if i.get('state') in ('RUN_UP', 'CRASHED')), key=watch)
    watched = sorted((i for i in french + etfs if watch(i)[2] != 'other'), key=watch)
    body.append('<h2>Watch list</h2><p class="lead"><span class="key crash">red</span> crash reached or in a run-up, '
                'closest to the crash line first; <span class="key near">green</span> approaching a run-up, closest to '
                'the rule first. Green means momentum towards a possible bubble, not a buy signal; red means the '
                'historical crash odds below, not a forecast of which falls next.</p>')
    rows = ''.join(
        f'<tr class="{watch(i)[2]}"><td><b>{escape(i["etf"])}</b></td><td class="l">{escape(i["name"])}</td>'
        f'<td class="l muted">{escape(i.get("group") or "")}</td><td class="l">{escape(distance(i))}</td>'
        f'<td>{_odds(i.get("probability")) if i.get("probability") else "—"}</td>'
        f'<td>{_pct(i.get("raw_24m"))}</td><td>{_pct(i.get("net_24m"))}</td></tr>' for i in watched)
    body.append('<div class="tw"><table><thead><tr><th>Code</th><th class="l">Name</th><th class="l">Source</th>'
                '<th class="l">Distance</th><th>Historical crash rate</th><th>24 m return</th>'
                '<th>Net of S&amp;P 500</th></tr></thead><tbody>'
                + (rows or '<tr><td colspan="7" class="l muted">Nothing on the watch list today.</td></tr>')
                + '</tbody></table></div>')
    body.append('<h2>In a run-up now</h2><p class="lead">Two independent sources, neither chosen from the universe: '
                f'all 49 US industries from every listed stock (French data, to {escape(str(cal.get("source_end", "")))}, '
                f'monthly) and {len(etfs)} ETFs by area (US sectors, industries, themes and countries, latest close).</p>')
    if not flagged:
        body.append('<p class="muted">No industry or ETF meets the run-up rule today.</p>')
    for ind in flagged:
        prob = ind.get('probability')
        separation = ind.get('separation_month')
        closer = {'crash': f'closer to the crash average after {ind["months_since"]} months',
                  'calm': f'closer to the no-crash average after {ind["months_since"]} months'}.get(
            ind.get('path_closer_to'),
            f'too early to compare: the two historical averages only separate after about {separation} months'
            if separation else 'not comparable')
        french_row = ind.get('group') == FRENCH_GROUP
        last_tile = (f'<div class="tile"><span>Data to</span><b>{escape(str(ind.get("date", ""))[:7])}</b></div>'
                     if french_row else
                     f'<div class="tile"><span>Crash line (price)</span><b>{ind["crash_line"]:,.2f}</b></div>')
        body.append(
            f'<h3>{escape(ind["etf"])} · {escape(ind["name"])} · {escape(STATES[ind["state"]])}</h3>'
            f'<p class="muted">{escape(ind.get("group") or "")}</p><div class="tiles">'
            f'<div class="tile"><span>Identified</span><b>{escape(ind["start"][:7])}</b></div>'
            f'<div class="tile"><span>Run-up then (net of market)</span><b>{_pct(ind["run_up_net"])}</b></div>'
            f'<div class="tile"><span>From peak now</span><b>{_pct(ind["drawdown"])}</b></div>'
            + last_tile + '</div>'
            + (f'<p>Historical crash rate: {_odds(prob)} · basis: {escape(prob["basis"])} · path: '
               f'{escape(closer)}.</p>' if prob else '')
            + (chart(ind, cal['paths']) if cal.get('paths') else ''))
        if ind['members']:
            body.append(f'<p class="muted">Universe members: {escape(", ".join(ind["members"]))}</p>')
    def table(items, first, group_column):
        rows = ''.join(
            f'<tr class="{watch(i)[2]}"><td><b>{escape(i["etf"])}</b></td><td class="l">{escape(i["name"])}</td>'
            + (f'<td class="l muted">{escape(i.get("group") or "")}</td>' if group_column else '')
            + f'<td class="l">{escape(STATES[i["state"]])}</td><td class="l">{escape(distance(i))}</td>'
            f'<td>{_pct(i.get("raw_24m"))}</td><td>{_pct(i.get("net_24m"))}</td>'
            f'<td class="l muted">{escape(", ".join(i.get("members") or []))}</td></tr>'
            for i in sorted(items, key=watch))
        return ('<div class="tw"><table><thead><tr><th>' + first + '</th><th class="l">Name</th>'
                + ('<th class="l">Area</th>' if group_column else '')
                + '<th class="l">Status</th><th class="l">Distance</th><th>24 m return</th><th>Net of S&amp;P 500</th>'
                  '<th class="l">Universe</th></tr></thead><tbody>' + rows + '</tbody></table></div>')
    if french:
        body.append(f'<h2>All 49 US industries</h2><p class="lead">Every US-listed stock, value-weighted, data to '
                    f'{escape(str(cal.get("source_end", "")))}. Same order and colours as the watch list.</p>'
                    + table(french, 'Code', False))
        left = monitor.get('french_left_out') or []
        if left:
            body.append(f'<p class="muted">Left out with fewer than {MIN_FIRMS} listed firms, as in the history: '
                        + escape(', '.join(f'{FRENCH_NAMES.get(n, n)} ({k})' for n, k in left))
                        + '. Gold and silver are covered by the GDX and SIL ETFs below.</p>')
    body.append('<h2>ETFs by area</h2><p class="lead">Same order and colours as the watch list. Themes are younger and '
                'more concentrated than industries; countries are measured in USD against the S&amp;P 500, so the US '
                'industry history applies only loosely to them.</p>' + table(etfs, 'ETF', True))
    hot = [s for s in monitor.get('stocks', []) if watch(s)[2] != 'other']
    rows = ''.join(
        f'<tr class="{watch(s)[2]}"><td><b>{escape(s["ticker"])}</b></td><td class="l">{escape(STATES[s["state"]])}</td>'
        f'<td class="l">{escape(distance(s))}</td><td>{_pct(s.get("raw_24m"))}</td><td>{_pct(s.get("net_24m"))}</td>'
        f'<td>{_pct(s.get("drawdown"))}</td><td class="l">{escape(s.get("industry") or "—")}</td></tr>'
        for s in sorted(hot, key=watch))
    body.append('<h2>Universe stocks: crash risk and approaching run-ups</h2><p class="lead">Single stocks swing more '
                'than industries, so the industry crash rates above apply only loosely. USD listings only.</p>'
                + ('<div class="tw"><table><thead><tr><th>Ticker</th><th class="l">Status</th><th class="l">Distance</th>'
                   '<th>24 m return</th><th>Net of S&amp;P 500</th><th>From peak since run-up</th>'
                   '<th class="l">Industry ETF</th></tr></thead><tbody>' + rows + '</tbody></table></div>' if rows else
                   '<p class="muted">None today.</p>'))
    if cal.get('splits'):
        rows = ''.join(f'<tr><td class="l">{escape(x["text"])}</td><td>{_odds(x["yes"])}</td><td>{_odds(x["no"])}</td></tr>'
                       for x in cal['splits'])
        rows += ''.join(f'<tr><td class="l">After a {level}% fall from the peak</td><td>{_odds(odds)}</td><td>—</td></tr>'
                        for level, odds in sorted((cal.get('after_drawdown') or {}).items()))
        body.append('<h2>What history says raises the odds</h2><div class="tw"><table><thead><tr>'
                    '<th class="l">At identification</th><th>Yes: crash rate</th><th>No: crash rate</th></tr></thead>'
                    '<tbody>' + rows + '</tbody></table></div>')
    body.append('<div class="note">Turnover and the age of firms, two further signals in the paper, need data this '
                'site does not have. ETFs are proxies for industries. Information next to the score: it never changes '
                'a score, a label or the paper test. Research, not an approved purchase recommendation.</div>')
    return shell('Crash monitor', ''.join(body))


def site_pages(root, build, *, now=None):
    monitor = (((build['record'].get('_evidence') or {}).get('macro') or {}).get('crash_monitor'))
    return [(Path(PAGE), render(monitor, now=now))] if monitor else []


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Crash monitor calibration')
    parser.add_argument('--calibrate', action='store_true', help='download the French data and rewrite the calibration')
    if parser.parse_args().calibrate:
        result = refresh_calibration()
        print(f"{len(result['episodes'])} episodes, {result['base']['crashes']} crashes, data to {result['source_end']}")
