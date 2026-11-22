"""First crossing of the current drawdown in each prior record cycle, using daily closes."""
from math import sqrt
from statistics import median


def interval(k,n):
    if not n:
        return None
    p=k/n
    z=1.95996398454
    center=p+z*z/(2*n)
    radius=z*sqrt(p*(1-p)/n+z*z/(4*n*n))
    return [round(100*(center+d)/(1+z*z/n),1) for d in (-radius,radius)]


def path_stats(dates, prices, i):
    path=prices[i:i+64]
    base=path[0]
    def first(level,up):
        return next((t for t,x in enumerate(path[1:],1)
                     if (x>=base*level if up else x<=base*level)),None)
    hit=first(1.05,True)
    drop=first(.95,False)
    r=dict(cross=str(dates[i]),price=round(base,2),five=hit,ten=first(1.1,True),down=drop,
           max63=round(100*(max(path)/base-1),2))
    if hit is None:
        return r
    # Eligibility remains fixed at 63 sessions. Follow qualifying rallies until
    # their first 5% closing pullback, including follow-up beyond session 63.
    path=prices[i:]
    low=min(range(hit+1),key=path.__getitem__)
    high=hit
    stop=None
    for t in range(hit+1,len(path)):
        if path[t]>path[high]:
            high=t
        elif path[t]<=path[high]*.95:
            stop=t
            break
    r.update(first=str(dates[i+hit]),start=str(dates[i+low]),peak=str(dates[i+high]),
             end=str(dates[i+stop]) if stop is not None else None,
             rise=round(100*(path[high]/path[low]-1),2),duration=high-low,
             from_cross=round(100*(path[high]/base-1),2))
    return r


def study(dates,prices,cycles,depth):
    events=[]
    for a,b,_ in cycles:
        if prices[b] > prices[a]*(1-depth):
            continue
        i=next(i for i in range(a,b+1) if prices[i]<=prices[a]*(1-depth))
        if i+63>=len(prices):
            continue
        events.append(dict(previous=str(dates[a]),**path_stats(dates,prices,i)))
    bands=[]
    for h in (5,21,42,63):
        for key in ('five','ten'):
            n=len(events)
            k=sum(e[key] is not None and e[key]<=h for e in events)
            bands.append(dict(h=h,target=5 if key=='five' else 10,k=k,n=n,ci=interval(k,n)))
    hits=[e for e in events if e['five'] is not None]
    def med(rows,key):
        return median(e[key] for e in rows) if rows else None
    return dict(events=events,bands=bands,hit=len(hits),wait=med(hits,'five'),
                size=med(hits,'rise'),duration=med(hits,'duration'),gain=med(hits,'from_cross'),
                censored=sum(e['end'] is None for e in hits),maximum=med(events,'max63'),
                downside=sum(e['down'] is not None and (e['five'] is None or e['down']<e['five']) for e in events))
