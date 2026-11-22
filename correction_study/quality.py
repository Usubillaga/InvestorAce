"""June 2026 cohort sensitivity. Input files supplied to build.py."""
import csv, io, json, statistics, zipfile
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from bs4 import BeautifulSoup


def quote(symbol, start="2026-06-30"):
    if symbol=='WBD' and start=='2026-06-30':
        # Delisted: June 30 close verified against Yahoo historical table and FinanceCharts.
        # Merger cash per share includes ticking fee; cash held at zero until November 20.
        return round(100*(31.01666668/26.66-1),3)
    url = 'https://query1.finance.yahoo.com/v8/finance/chart/'+symbol.replace('.', '-')+'?period1=1782691200&period2=1795305600&interval=1d'
    doc = json.load(urlopen(Request(url, headers={'User-Agent':'Mozilla/5.0'}), timeout=25))['chart']['result'][0]
    values = dict(zip([datetime.fromtimestamp(t,timezone.utc).date().isoformat() for t in doc['timestamp']],doc['indicators']['adjclose'][0]['adjclose']))
    terminal = values['2026-11-20']
    return round(100*(terminal/values[start]-1),3)


def measure(folder):
    rows = BeautifulSoup((folder/'junewiki').read_bytes(),'html.parser').select('#constituents tr')[1:]
    names = {}
    for row in rows:
        s,_,sector,_,_,added,cik,_ = [c.get_text(strip=True) for c in row.select('td')]
        if added and added[:10] <= '2026-06-30':
            names.setdefault(int(cik),(s,sector))
    ranks = defaultdict(list)
    for filename in ['sec1.zip','sec.zip']:
        with zipfile.ZipFile(folder/filename) as z:
            def read(name):
                return csv.DictReader(io.TextIOWrapper(z.open(name),encoding='utf-8'),delimiter='\t')
            filings = {r['adsh']:r for r in read('sub.txt') if int(r['cik']) in names and r['form']=='10-K' and r['filed']<='20260630'}
            facts = defaultdict(dict)
            for r in read('num.txt'):
                f = filings.get(r['adsh'])
                if f and r['ddate']==f['period'] and r['uom']=='USD' and not r['segments'] and not r['coreg'] and (r['tag'],r['qtrs']) in [('Assets','0'),('NetIncomeLoss','4')] and r['value']:
                    facts[r['adsh']][r['tag']]=float(r['value'])
            for ad, data in facts.items():
                if data.get('Assets',0)>0 and 'NetIncomeLoss' in data:
                    s,sector=names[int(filings[ad]['cik'])]
                    ranks[sector].append((data['NetIncomeLoss']/data['Assets'],s))
    out={}
    selected={}
    for sector, rows in ranks.items():
        rows=sorted(set(rows))
        n=min(4,len(rows)//2)
        if n: selected[sector]=(len(rows), [s for _,s in rows[-n:]], [s for _,s in rows[:n]])
    symbols=sorted({s for _,hi,lo in selected.values() for s in hi+lo}|{'RSP','SPY','QUAL'})
    cache=folder/'june_returns.json'
    prices=json.loads(cache.read_text()) if cache.exists() else {}
    def observed(symbol):
        try:
            return quote(symbol)
        except (KeyError,IndexError):
            return None
    missing=[s for s in symbols if s not in prices]
    with ThreadPoolExecutor(8) as pool:
        prices.update(zip(missing,pool.map(observed,missing)))
    prices={s:prices[s] for s in symbols}
    cache.write_text(json.dumps(prices))
    for sector,(size,hi,lo) in selected.items():
        out[sector]={'n':size,'high':hi,'low':lo,'gap':round(statistics.mean(prices[s] for s in hi)-statistics.mean(prices[s] for s in lo),2) if all(prices[s] is not None for s in hi+lo) else None}
    return {'sectors':out,'returns':prices}
