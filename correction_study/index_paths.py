"""Rebuild the four-market, first-barrier historical scenario study for the atlas."""
import argparse
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from urllib.parse import quote
from urllib.request import Request, urlopen

if __package__:
    from .rebounds import interval
else:
    from rebounds import interval

INDICES = {'SPX': ('S&P 500','^GSPC'), 'IXIC': ('Nasdaq Composite','^IXIC'),
           'DJI': ('Dow Jones Industrial Average','^DJI'), 'DAX': ('DAX','^GDAXI')}
HORIZON = 63
AS_OF = '2026-11-20'


def scenario(path):
    for i, value in enumerate(path[1:], 1):
        if value >= 1.05:
            return 'up', i
        if value <= 0.95:
            return 'down', i
    return 'range', None


def study(rows):
    dates, values = zip(*rows)
    if dates[-1] != AS_OF or any(a >= b for a,b in zip(dates, dates[1:])):
        raise ValueError('Missing cutoff or unordered sessions')
    high = max(values)
    ratio = values[-1] / high
    if ratio >= 1:
        raise ValueError('The reference point must be in a drawdown')
    current_peak = max(i for i,v in enumerate(values) if v==high)
    peak = 0
    crossed = False
    events = []
    for i, price in enumerate(values):
        if price >= values[peak]:
            peak, crossed = i, False
        elif not crossed and price <= values[peak] * ratio + 1e-9:
            crossed = True
            if i + HORIZON >= len(rows) or peak >= current_peak:
                continue
            path = [v / price for v in values[i:i+HORIZON+1]]
            kind, day = scenario(path)
            events.append((kind,day,dates[i],path))
    counts = Counter(e[0] for e in events)
    winners = [k for k,v in counts.items() if v==max(counts.values())]
    out = dict(start=dates[0], close=values[-1], high=high, drawdown=round((ratio-1)*100,2),
               n=len(events), counts=dict(counts), winner=None)
    if len(winners)!=1:
        return out
    winner=winners[0]
    group=[e for e in events if e[0]==winner]
    center=[median(xs) for xs in zip(*(e[3] for e in group))]
    # A real path closest to the pointwise median preserves barrier crossing order.
    selected=min(group,key=lambda e:sum(abs(a-b) for a,b in zip(e[3],center)))
    out.update(winner=winner,hits=len(group),ci=interval(len(group),len(events)), exemplar=selected[2],
               path=[round(100*(v-1),3) for v in selected[3]],
               sessions=median(e[1] for e in group) if winner!='range' else None,
               median_final=round(100*(center[-1]-1),2))
    return out


def get_rows(symbol, cache):
    name=cache/(symbol[1:]+'.json')
    if not name.exists():
        url='https://query1.finance.yahoo.com/v8/finance/chart/'+quote(symbol,safe='')+'?period1=-1420070400&period2=1795305600&interval=1d'
        with urlopen(Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=45) as response:
            data=response.read()
        name.write_bytes(data)
    obj=json.loads(name.read_bytes())['chart']['result'][0]
    if obj['meta']['symbol']!=symbol:
        raise ValueError(symbol)
    return [(datetime.fromtimestamp(t,timezone.utc).date().isoformat(),p)
            for t,p in zip(obj['timestamp'],obj['indicators']['quote'][0]['close'])
            if p is not None and math.isfinite(p) and p>0]


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('cache',type=Path)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    args.cache.mkdir(exist_ok=True,parents=True)
    data={key:dict(name=name,symbol=symbol,**study(get_rows(symbol,args.cache)))
          for key,(name,symbol) in INDICES.items()}
    args.output.write_text(json.dumps(dict(as_of=AS_OF,horizon=HORIZON,indices=data),indent=2,allow_nan=False)+'\n')
