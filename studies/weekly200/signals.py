"""Weekly decisions use the exchange's last session of each completed week."""

from bisect import bisect_left
from datetime import timedelta

import numpy as np
import pandas as pd

from .download import START, UNTIL


def prices(chart):
    q = chart["indicators"]["quote"][0]
    adjusted = chart["indicators"]["adjclose"][0]["adjclose"]
    tz = chart["meta"]["exchangeTimezoneName"]
    idx = (
        pd.to_datetime(chart["timestamp"], unit="s", utc=True)
        .tz_convert(tz)
        .normalize()
        .tz_localize(None)
    )
    raw = pd.DataFrame(
        {
            "close": q["close"],
            "high": q["high"],
            "low": q["low"],
            "volume": q["volume"],
            "adjusted": adjusted,
        },
        index=idx,
    )
    raw = raw.loc[(raw.index >= pd.Timestamp(START)) & (raw.index < pd.Timestamp(UNTIL))]
    ratio = (raw.adjusted / raw.close).where((raw.close > 0) & (raw.adjusted > 0))
    out = raw[["close", "high", "low"]].mul(ratio, axis=0).round(4)
    out["volume"] = raw.volume
    if not out.index.is_unique:
        raise ValueError("duplicate prices")
    return out.dropna(subset=["close", "high", "low"])


def weekly_bars(frame, sessions, weeks=200):
    """No forward fill. Every local US session must have a candle in a signal week."""
    d = frame.reindex(sessions)
    g = d.resample("W-FRI")
    bars = g.agg({"close": "last", "low": "min", "high": "max"})
    # A missing final session must never masquerade as a weekly closing print.
    last = pd.Series(sessions, index=sessions).resample("W-FRI").last()
    bars["session"] = last
    closes = d.close.reindex(pd.DatetimeIndex(last.dropna())).set_axis(last.dropna().index)
    bars["close"] = closes
    bars["complete"] = g.close.count().eq(g.size())
    bars = bars.loc[bars.index < pd.Timestamp(UNTIL)]
    line = bars.close.rolling(weeks, min_periods=weeks).mean().shift(1)
    bars["line"] = line
    above = bars.close / line
    # Compare prior price with its own then-known level.
    trend = (
        (line > line.shift(26)) & (above.shift(1) > 1) & (above.shift(1).rolling(13).max() >= 1.10)
    )
    bars["prior_dd"] = bars.close.shift() / bars.close.shift().rolling(13).max() - 1
    bars["control"] = (
        trend
        & bars.complete
        & (bars.low > line * 1.05)
        & (above <= 1.20)
        & (bars.close > bars.close.shift())
        & (bars.prior_dd < 0)
    )
    bars["touch"] = trend & bars.complete & (bars.low <= line * 1.02) & (bars.high >= line * 0.98)
    bars["confirm"] = bars.touch & (bars.close >= line) & (bars.close > bars.close.shift())
    return bars


class Reports:
    def __init__(self, reports):
        self.rows = sorted(reports, key=lambda r: r["filed"])
        self.dates = [r["filed"] for r in self.rows]

    def at(self, session):
        # Exclude same-day filings because their acceptance time may be after the close.
        i = bisect_left(self.dates, session.date().isoformat()) - 1
        if i < 0:
            return None
        row = self.rows[i]
        if (session - pd.Timestamp(row["end"])).days > 550:
            return None
        return row


class Sleeve:
    def __init__(self, entries, breaks, stop=True, fixed_weeks=None):
        self.entries = entries
        self.breaks = breaks
        self.stop = stop
        self.fixed_weeks = fixed_weeks

    def exit_reason(self, symbol, day, close, position):
        if self.fixed_weeks:
            return (
                "MAX_HOLD"
                if day >= position["entered"] + timedelta(weeks=self.fixed_weeks)
                else None
            )
        if self.stop and np.isfinite(close) and close <= position["entry"] * 0.92:
            return "STOP"
        if symbol in self.breaks.get(day, ()):
            return "WEEKLY_BREAK"
        if day >= position["entered"] + timedelta(weeks=26):
            return "MAX_HOLD"
        return None


PRIMARY = "quality_confirm"
ALT = "quality_confirm_40w"
VARIANTS = (
    "confirmed",
    "quality_touch",
    PRIMARY,
    "quality_exact_touch",
    "quality_confirm_no_stop",
    ALT,
    "quality_hold_13w",
)


def collect(symbol, bars, reports, weeks=200):
    events, breaks = [], []
    for r in bars.itertuples():
        if r.close < r.line:
            breaks.append(r.session)
        if not r.touch:
            continue
        report = reports.at(r.session)
        events.append(
            {
                "symbol": symbol,
                "weeks": weeks,
                "day": r.session,
                "line": r.line,
                "close": r.close,
                "distance": abs(r.close / r.line - 1),
                "prior_dd": r.prior_dd,
                "exact_touch": bool(r.low <= r.line <= r.high),
                "confirm": bool(r.confirm),
                "quality": report["quality"] if report else None,
                "filed": report["filed"] if report else None,
                "accession": report["accession"] if report else None,
            }
        )
    return events, breaks


def eligible(row, mode):
    if row["weeks"] != (40 if mode == ALT else 200):
        return False
    if mode == "quality_exact_touch":
        return row["quality"] is True and row["confirm"] and row["exact_touch"]
    if mode == "confirmed":
        return row["confirm"]
    return row["quality"] is True and (mode == "quality_touch" or row["confirm"])


def book_for(mode, entries, breaks):
    return Sleeve(
        entries,
        breaks[40 if mode == ALT else 200],
        stop=mode != "quality_confirm_no_stop",
        fixed_weeks=13 if mode == "quality_hold_13w" else None,
    )
