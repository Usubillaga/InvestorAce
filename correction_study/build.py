"""Reproduce the dated US correction atlas: python build.py CACHE_DIR OUTPUT.json.
Downloads public series; June cohort requires beautifulsoup4. Cached sources can be retained for replay.
"""
import bisect, calendar, csv, io, json, math, sys, zipfile
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

HERE=Path(__file__).resolve().parent
SOURCES={
 'dow':'https://en.wikipedia.org/wiki/Historical_components_of_the_Dow_Jones_Industrial_Average',
 'early.zip':'https://www.billschwert.com/stkdatd.zip',
 'dsector':'https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/12_Industry_Portfolios_daily_CSV.zip',
 'sp':'https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC?period1=-1420070400&period2=1795305600&interval=1d',
 'cpi':'https://fred.stlouisfed.org/graph/fredgraph.csv?id=CPIAUCNS',
 'rec':'https://fred.stlouisfed.org/graph/fredgraph.csv?id=USREC',
 'sh':'https://raw.githubusercontent.com/datasets/s-and-p-500/main/data/data.csv',
 'aq':'https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_5_Factors_2x3_CSV.zip',
 'sect':'https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/12_Industry_Portfolios_CSV.zip',
 'junewiki':'https://en.wikipedia.org/w/index.php?title=List_of_S%26P_500_companies&oldid=1361794875',
 'sec.zip':'https://www.sec.gov/files/dera/data/financial-statement-data-sets/2026q2.zip',
 'sec1.zip':'https://www.sec.gov/files/dera/data/financial-statement-data-sets/2026q1.zip'}
SECTORS=['Consumo no duradero','Consumo duradero','Manufacturas','Energía','Química','Informática','Telecomunicaciones','Servicios públicos','Comercio','Salud','Finanzas','Otros']


def episodes(values, local):
    peak=low=0
    active=False
    out=[]
    for i,price in enumerate(values):
        if not active:
            if price>=values[peak]: peak=i
            elif price<=values[peak]*.9:
                active=True
                low=i
        elif price<values[low]: low=i
        elif price >= (values[low]*1.1 if local else values[peak]):
            out.append((peak,low,i))
            active=False
            peak=i
    if active: out.append((peak,low,None))
    return out


def french(path):
    with zipfile.ZipFile(path) as z:
        lines=z.read(z.namelist()[0]).decode('latin1').splitlines()
    start=next(i for i,s in enumerate(lines) if s.startswith(','))
    data={}
    for row in csv.reader(lines[start+1:]):
        if not row or not row[0].strip().isdigit(): break
        data[row[0][:4]+'-'+row[0][4:6]+('-'+row[0][6:8] if len(row[0])==8 else '')]=[float(x) for x in row[1:]]
    return data


def product(rows,i):
    return round(100*(math.prod(1+r[i]/100 for r in rows)-1),2)


def main(folder):
    folder.mkdir(exist_ok=True,parents=True)
    for k,url in SOURCES.items():
        dest=folder/k
        if not dest.exists():
            dest.write_bytes(urlopen(Request(url,headers={'User-Agent':'InvestorAce research contact github.com/Usubillaga'}),timeout=90).read())
    x=json.loads((folder/'sp').read_text())['chart']['result'][0]
    daily=[(datetime.fromtimestamp(t,timezone.utc).date(),c) for t,c in zip(x['timestamp'],x['indicators']['quote'][0]['close']) if c is not None]
    assert daily[-1][0]==date(2026,11,20)
    monthly=list(csv.DictReader((folder/'sh').read_text().splitlines()))
    early=[(date.fromisoformat(r['Date']),float(r['SP500'])) for r in monthly if '1925'<=r['Date']<'1927-12']
    macro={}
    for key in ['rec','cpi']:
        macro[key]={r[0][:7]:float(r[1]) for r in list(csv.reader((folder/key).read_text().splitlines()))[1:] if r[1] not in ('','.')}
    leaders=json.loads((HERE/'leaders.json').read_text())
    sectors=french(folder/'dsector')
    sd=sorted(sectors)
    factors=french(folder/'aq')
    rows=[]
    def inflation(d):
        key=d.isoformat()[:7]
        n=macro['cpi'].get(key)
        base=macro['cpi'].get(str(d.year-1)+key[4:])
        return round(100*(n/base-1),2) if n and base else None
    with zipfile.ZipFile(folder/'early.zip') as z:
        proxy=[]
        level=100
        for line in z.read(z.namelist()[0]).decode().splitlines():
            fields=line.split()
            if fields and '1925'<=fields[0]<'19271230':
                level*=1+float(fields[2])
                proxy.append((datetime.strptime(fields[0],'%Y%m%d').date(),level))
    for series,freq in [(proxy,'Dow proxy'),(early,'mensual'),(daily,'diaria')]:
        dates,prices=zip(*series)
        for local in [False,True]:
            for a,b,end in episodes(prices,local):
                p,t=dates[a],dates[b]
                bounce=next((i for i in range(b+1,len(prices)) if prices[i]>=prices[b]*1.1),None)
                recovery=next((i for i in range(b+1,len(prices)) if prices[i]>=prices[a]),None)
                pm,tm=p.isoformat()[:7],t.isoformat()[:7]
                months=[sectors[d] for d in sd[bisect.bisect_right(sd,str(p)):bisect.bisect_right(sd,str(t))]]
                returns={s:product(months,i) for i,s in enumerate(SECTORS)} if months and sd[0]<=str(p) and str(t)<=sd[-1] else {}
                recess=[v for m,v in macro['rec'].items() if pm<=m<=tm]
                leader=lambda y:leaders.get(str(y))
                context={1929:'Especulación bursátil y crédito',1973:'Shock petrolero y gran inflación',1987:'Crash bursátil de octubre',2000:'Burbuja puntocom',2020:'Pandemia y recesión',2022:'Inflación y endurecimiento monetario',2007:'Burbuja inmobiliaria y crédito hipotecario'}.get(p.year)
                forward={}
                if freq=='diaria':
                    for years in (1,2):
                        cutoff=p.replace(year=p.year+years,day=min(p.day,calendar.monthrange(p.year+years,p.month)[1]))
                        k=bisect.bisect_right(dates,cutoff)-1
                        if cutoff<=dates[-1]:
                            interval=sd[bisect.bisect_right(sd,str(p)):bisect.bisect_right(sd,str(dates[k]))]
                            sec={s:product([sectors[d] for d in interval],i) for i,s in enumerate(SECTORS)} if interval and sd[0]<=str(p) and str(dates[k])<=sd[-1] else {}
                            forward[years]=dict(index=round(100*(prices[k]/prices[a]-1),2),sectors=sec)
                cape=next((float(r['PE10']) for r in reversed(monthly) if r['Date'][:7]<pm and float(r['PE10'] or 0)>0 and (p-date.fromisoformat(r['Date'])).days<65),None)
                rows.append(dict(cape=cape,forward=forward,mode='local' if local else 'récord',freq=freq,peak=str(p),top=round(prices[a],2),low=str(t),bottom=round(prices[b],2),dd=round(100*(prices[b]/prices[a]-1),2),days=(t-p).days,
                    bounce=str(dates[bounce]) if bounce is not None else None,recovery=str(dates[recovery]) if recovery is not None else None,
                    open=end is None,cpi=inflation(p),cpiEnd=inflation(t),recession='Sí' if any(recess) else 'No' if tm<=max(macro['rec']) else 'Pendiente',
                    context=context,leader=[leader(p.year-1),leader(t.year)],sector=returns))
    dates,prices=zip(*daily)
    high=max(prices); idx=max(i for i,v in enumerate(prices) if v==high)
    last=dates[-1]
    dd=1-prices[-1]/high
    # Compare earlier record declines at first crossing of today's depth; CPI lagged two months.
    def lagged(d):
        serial=d.year*12+d.month-3
        return inflation(date(serial//12,serial%12+1,1))
    analog=[]
    for a,b,end in episodes(prices,False):
        if dates[a]>=dates[idx] or prices[b]>prices[a]*(1-dd):continue
        i=next(i for i in range(a,b+1) if prices[i]<=prices[a]*(1-dd))
        c=lagged(dates[i]);now=lagged(last)
        if c is None or now is None:continue
        days=(dates[i]-dates[a]).days
        distance=abs(math.log((days+1)/((last-dates[idx]).days+1)))+abs(c-now)/5
        analog.append([round(distance,3),str(dates[a]),days,c,round(100*(prices[b]/prices[a]-1),2)])
    qpath=folder/'quality_june'
    if not qpath.exists():
        from quality import measure
        qpath.write_text(json.dumps(measure(folder)))
    sector_path=folder/'sector_etfs'
    if not sector_path.exists():
        from quality import quote
        tickers='XLK XLI XLF XLP XLB XLV XLRE XLC XLE XLY XLU'.split()
        sector_path.write_text(json.dumps({s:[quote(s),quote(s,str(dates[idx]))] for s in tickers}))
    ff=[v for m,v in factors.items() if '2026-06'<m<='2026-11']
    from bs4 import BeautifulSoup
    dow={}
    for table in BeautifulSoup((folder/'dow').read_bytes(),'html.parser').select('table.wikitable'):
        h=table.find_previous(['h2','h3','h4'])
        try: d=datetime.strptime(h.get_text(strip=True),'%B %d, %Y').date()
        except (ValueError,AttributeError):continue
        if d.year<1925 or d>last: continue
        adds=[]; drops=[]
        for cell in table.select('td'):
            name=cell.get_text(' ',strip=True)
            if '↑' in name: adds.append(name.split('↑')[0].strip())
            if '↓' in name: drops.append(name.split('↓')[0].strip())
        if adds or drops: dow[str(d)]=[adds,drops]
    from rebounds import study
    rebounds=study(dates,prices,episodes(prices,False),dd)
    return dict(rebounds=rebounds,eps=json.loads((HERE/'eps.json').read_text()),etfs=json.loads(sector_path.read_text()),dow=dow,asof=str(last),high=[str(dates[idx]),round(high,2)],last=round(prices[-1],2),dd=round(-100*dd,2),days=(last-dates[idx]).days,cpi=lagged(last),analog=sorted(analog)[:5],rows=rows,quality=json.loads(qpath.read_text()),rmw=[max(m for m in factors if m<='2026-11'),product(ff,3)],sources=SOURCES)

if __name__=='__main__':
    result=main(Path(sys.argv[1]))
    output=Path(sys.argv[2])
    output.with_name('rebounds.json').write_text(json.dumps(result.pop('rebounds'),indent=2,allow_nan=False)+'\n')
    output.write_text(json.dumps(result,ensure_ascii=False,separators=(',',':'),allow_nan=False))
