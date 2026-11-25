"""Published index composition. Fund holdings are never substituted for index weights."""
import io
import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader
from pypdf.errors import PyPdfError

SP = 'https://www.ssga.com/us/en/intermediary/etfs/state-street-spdr-sp-500-etf-trust-spy'
NDX = 'https://www.nasdaq.com/docs/global-indexes/NDX'
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; InvestorAce/1.0; index monitor)'}
# The S&P publisher supplies names only. These aliases identify share classes;
# inclusion and ranking always come from the dated index table.
SYMBOLS = {'Apple Inc.': 'AAPL', 'NVIDIA Corporation': 'NVDA', 'Microsoft Corporation': 'MSFT',
           'Amazon.com Inc.': 'AMZN', 'Alphabet Inc. Class A': 'GOOGL', 'Alphabet Inc. Class C': 'GOOG',
           'Broadcom Inc.': 'AVGO', 'Meta Platforms Inc Class A': 'META', 'Tesla Inc.': 'TSLA',
           'Eli Lilly and Company': 'LLY'}


def sp_weights(raw):
    soup = BeautifulSoup(raw, 'html.parser')
    heading = next(h for h in soup.select('h3') if h.get_text(' ', strip=True).startswith('Index Top Holdings'))
    stamp = datetime.strptime(heading.select_one('.date').get_text(strip=True), 'as of %b %d %Y').date()
    table = heading.find_next('table')
    if [h.get_text(strip=True) for h in table.select('thead th')] != ['Name', 'Weight']:
        raise ValueError('Unrecognized index weight table')
    rows = []
    for row in table.select('tbody tr'):
        name, weight = [c.get_text(strip=True) for c in row.select('td')]
        rows.append((name, SYMBOLS.get(name), float(weight.removesuffix('%'))))
    return stamp, rows


def ndx_weights(raw):
    pages = [p.extract_text(extraction_mode='layout') for p in PdfReader(io.BytesIO(raw)).pages]
    if not re.search(r'Ticker:\s*NDX\b', pages[0]):
        raise ValueError('Unexpected Nasdaq index')
    stamp = re.search(r'Data as of:\s*(\d{2}/\d{2}/\d{4})', pages[0])
    rows = [(n.strip(), s, float(w)) for n, s, w in re.findall(
        r'^\s*([^\n]+?)\s{2,}([A-Z][A-Z.\-]{0,8})\s+(\d+\.\d+)\s*$', '\n'.join(pages), re.M)]
    if not 95 <= len(rows) <= 110 or not 98 <= sum(r[2] for r in rows) <= 102:
        raise ValueError('Incomplete Nasdaq weights')
    return datetime.strptime(stamp[1], '%m/%d/%Y').date(), rows


def read_weights(day, saved=None):
    weights = {}
    for key, url, parse in [('SPX', SP, sp_weights), ('NDX', NDX, ndx_weights)]:
        previous = (saved or {}).get(key, {})
        try:
            response = requests.get(url, headers=HEADERS, timeout=9)
            response.raise_for_status()
            stamp, rows = parse(response.content)
            if (stamp > day or stamp.isoformat() < (previous.get('as_of') or '') or len(rows) < 6
                    or len({r[0] for r in rows}) != len(rows) or any(not 0 <= r[2] <= 100 for r in rows)):
                raise ValueError('Invalid composition')
            leaders = sorted(rows, key=lambda x: -x[2])[:6]
            weights[key] = dict(as_of=stamp.isoformat(), source=url,
                                rows=[dict(name=n, ticker=s, pct=w) for n, s, w in leaders])
        except (PyPdfError, requests.RequestException, ValueError, TypeError, AttributeError, IndexError, StopIteration, OSError) as exc:
            weights[key] = {**previous, 'source': url, 'fetch_error': type(exc).__name__}
    return weights
