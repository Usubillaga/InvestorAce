"""52-week-low radar for the tracked InvestorAce listings."""
from datetime import datetime, timedelta, timezone
from math import isfinite


def positive(value):
    return value if type(value) in (float, int) and isfinite(value) and value > 0 else None


def quote_fields(info, symbol, currency):
    """Keep the price, low and previous close from one dated listing quote."""
    if (str(info.get('symbol') or '').upper() != symbol.upper() or info.get('currency') != currency
            or info.get('quoteType') != 'EQUITY'):
        return None
    price = positive(info.get('regularMarketPrice'))
    low = positive(info.get('fiftyTwoWeekLow'))
    stamp = positive(info.get('regularMarketTime'))
    if not price or not low or not stamp or price < low:
        return None
    try:
        observed = datetime.fromtimestamp(stamp, timezone.utc).isoformat()
    except (ValueError, OverflowError, OSError):
        return None
    return dict(symbol=symbol, currency=currency, name=info.get('longName') or info.get('shortName') or symbol,
                exchange=info.get('fullExchangeName') or info.get('exchange') or '',
                price=price, low=low, previous=positive(info.get('regularMarketPreviousClose')),
                observed=observed)


def snapshot(record):
    evidence = record['_evidence']
    captured = datetime.fromisoformat(evidence['captured_at'])
    rows = []
    for ticker, inputs in evidence['inputs'].items():
        quote = inputs.get('low_radar_quote')
        if not quote:
            continue
        observed = datetime.fromisoformat(quote['observed'])
        if not timedelta(0) <= captured - observed <= timedelta(days=5):
            continue
        previous = quote['previous']
        metrics = record[ticker].get('opportunity') or {}
        financial = inputs.get('dynamic_analysis') or {}
        # The model's cap is denominated in the issuer's financial currency.
        # Only join valuations marked on the same UTC date as the quote.
        same_day = (metrics.get('quote_observed_at') or '')[:10] == quote['observed'][:10]
        values = (metrics.get('metrics') or {}) if same_day else {}
        cap_currency = financial.get('financial_currency')
        rows.append(dict(**quote, ticker=ticker, distance=100 * (quote['price'] / quote['low'] - 1),
                         change=100 * (quote['price'] / previous - 1) if previous else None,
                         market_cap=positive(values.get('market_cap')) if cap_currency else None,
                         cap_currency=cap_currency, pe=positive(values.get('reported_pe'))))
    rows.sort(key=lambda r: (r['distance'], r['symbol']))
    return dict(schema=1, captured=captured.isoformat(), universe=len(evidence['inputs']),
                eligible=len(rows), rows=rows[:30])
