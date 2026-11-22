"""Capture Yahoo's issuer-level rolling EPS history with a fixed fiscal end date."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date
import json
import sys
import yfinance as yf


def estimate(symbol):
    stock = yf.Ticker(symbol)
    row = stock.eps_trend.loc['+1y']
    period = next(x['endDate'] for x in stock._analysis._earnings_trend if x['period']=='+1y')
    return {'end':period,'old':float(row['90daysAgo']),'new':float(row['current'])}


if __name__=='__main__':
    symbols=['AAPL','AMZN','GOOG','META','MSFT','NVDA','TSLA']
    with ThreadPoolExecutor(4) as pool:
        values=dict(zip(symbols,pool.map(estimate,symbols)))
    print(json.dumps({'observed':date.today().isoformat(),'issuers':values},allow_nan=False))
