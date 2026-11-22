"""Volatility forecasts for the backtest's sizing variants (asked for on 22 Nov 2026). Research only.

* EWMA (RiskMetrics, lambda 0.94): next-day variance = lambda * variance + (1 - lambda) * return squared.
* GARCH(1,1): next-day variance = omega + alpha * return squared + beta * variance, with variance targeting
  (omega = long-run variance * (1 - alpha - beta)). alpha and beta are fitted by Gaussian maximum likelihood on a
  grid (numpy only), once a year on at most 1,000 earlier daily returns, never on data after the fit date.

Both return annualised volatility forecasts for the next session, known at each close.
Literature: Hansen & Lunde (2005), "Does anything beat a GARCH(1,1)?"; Moreira & Muir (2017),
"Volatility-managed portfolios".
"""
import math

import numpy as np
import pandas as pd

LAMBDA = 0.94
ALPHAS = np.linspace(0.01, 0.25, 25)
BETAS = np.linspace(0.60, 0.985, 36)
FIT_WINDOW, MIN_FIT = 1000, 250


def log_returns(close):
    return np.log(close.ffill(limit=3)).diff()


def ewma_vol(returns, lam=LAMBDA):
    """Annualised next-session volatility from returns up to and including each date."""
    var = (returns ** 2).ewm(alpha=1 - lam, adjust=False, ignore_na=True).mean()
    return np.sqrt(252 * var)


def garch_fit(r):
    """(omega, alpha, beta) maximising the Gaussian likelihood on a grid; None for too little data."""
    r = np.asarray(r, dtype=float)
    r = r[np.isfinite(r)]
    if len(r) < MIN_FIT:
        return None
    r = r - r.mean()
    long_run = r.var()
    if long_run <= 0:
        return None
    a, b = np.meshgrid(ALPHAS, BETAS, indexing='ij')
    ok = a + b < 0.999
    a, b = a[ok], b[ok]
    omega = long_run * (1 - a - b)
    var = np.full(a.shape, long_run)
    ll = np.zeros(a.shape)
    for x in r:
        ll -= np.log(var) + x * x / var
        var = omega + a * x * x + b * var
    i = int(np.argmax(ll))
    return float(omega[i]), float(a[i]), float(b[i])


def garch_vol(returns):
    """Annualised next-session GARCH(1,1) volatility, parameters refitted at the start of each calendar year."""
    out = pd.Series(np.nan, index=returns.index)
    values = returns.to_numpy(dtype=float)
    years = sorted({d.year for d in returns.index})
    for year in years:
        idx = np.where(returns.index.year == year)[0]
        if not len(idx):
            continue
        first = idx[0]
        params = garch_fit(values[max(0, first - FIT_WINDOW):first])
        if params is None:
            continue
        omega, alpha, beta = params
        history = values[max(0, first - FIT_WINDOW):first]
        history = history[np.isfinite(history)]
        var = float(np.var(history))
        for x in history[-60:]:                      # warm the filter on the last fitted returns
            var = omega + alpha * x * x + beta * var
        for i in idx:
            x = values[i]
            if math.isfinite(x):
                var = omega + alpha * x * x + beta * var
            out.iloc[i] = math.sqrt(252 * var)
    return out


_CACHE = {}


def panel(kind, close):
    """Forecast panel (dates x symbols) for 'ewma' or 'garch', computed once per price panel."""
    key = (kind, id(close))
    if key not in _CACHE:
        returns = log_returns(close)
        if kind == 'ewma':
            _CACHE[key] = ewma_vol(returns)
        elif kind == 'garch':
            _CACHE[key] = pd.DataFrame({s: garch_vol(returns[s]) for s in close.columns}, index=close.index)
        else:
            raise ValueError(f'unknown volatility model {kind}')
    return _CACHE[key]


def series(kind, prices):
    """Forecast for one price series (the S&P 500), cached the same way."""
    key = (kind, id(prices))
    if key not in _CACHE:
        returns = log_returns(prices)
        _CACHE[key] = ewma_vol(returns) if kind == 'ewma' else garch_vol(returns)
    return _CACHE[key]
