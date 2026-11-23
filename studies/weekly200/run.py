"""Run from the root with python -m studies.weekly200.run [--sample external]."""

import argparse
import csv
import hashlib
import multiprocessing as mp
from collections import defaultdict

import numpy as np
import pandas as pd

import backtest as bt

from .download import CACHE, HERE, UNTIL, load
from .signals import (
    PRIMARY,
    VARIANTS,
    Reports,
    book_for,
    collect,
    eligible,
    prices,
    weekly_bars,
)

OUT = HERE / "results"
PERIODS = [(pd.Timestamp(lo), pd.Timestamp(hi or UNTIL)) for lo, hi in bt.WINDOWS]
STATE = {}


def read_chart(symbol):
    path = CACHE / (symbol + ".prices.gz")
    if not path.is_file():
        return None
    return prices(load(path))


def write_csv(name, rows):
    pd.DataFrame(rows).to_csv(OUT / name, index=False, float_format="%.10g")


def write_portfolios(spx, frames, sectors, books, workers):
    from start_offsets import STARTS, STEP, summarise

    prepared = bt.portfolio_inputs(frames)
    STATE.update(spx=spx, frames=frames, sectors=sectors, books=books, prepared=prepared)
    jobs = []
    for lo, hi in PERIODS:
        sessions = spx.loc[(spx.index >= lo) & (spx.index < hi)].index
        jobs.extend((lo.year, sessions[i * STEP], hi) for i in range(STARTS))
    with mp.get_context("fork").Pool(workers) as pool:
        runs = list(pool.imap(portfolio_run, jobs))
    pairs, detail = defaultdict(list), []
    for year, start, end, book in runs:
        base = book["v1.6"]
        for variant, metrics in book.items():
            detail.append(
                dict(period=year, start=start.date(), end=end.date(), variant=variant, **metrics)
            )
            if variant != "v1.6":
                pairs[year, variant].append((base, metrics))
    out = []
    for (year, mode), group in pairs.items():
        stats = summarise(group)
        row = {
            "period": year,
            "variant": mode,
            "wins": stats["wins"],
            "ties": stats["ties"],
            "losses": stats["losses"],
        }
        for metric in ("cagr", "max_drawdown", "sharpe"):
            for fn, val in stats[metric].items():
                row[metric + "_" + fn] = val
        row.update(
            fills_median=np.median([v["weekly_fills"] for b, v in group]),
            base_CAGR_median=np.median([b["cagr"] for b, v in group]),
            sleeve_CAGR_median=np.median([v["cagr"] for b, v in group]),
        )
        out.append(row)
    write_csv("portfolio_runs.csv", detail)
    write_csv("portfolio_summary.csv", out)


def portfolio_run(job):
    year, start, end = job
    args = STATE
    results = {}
    for mode in ("v1.6", *VARIANTS):
        extra = {"weekly_sleeve": args["books"][mode]} if mode != "v1.6" else {}
        metrics = bt.simulate(
            args["frames"],
            args["spx"],
            args["sectors"],
            start,
            end,
            args["prepared"],
            precise=True,
            **bt.VARIANTS[bt.BASE],
            **extra,
        )
        results[mode] = {
            k: v
            for k, v in metrics.items()
            if k
            in ("final", "cagr", "max_drawdown", "sharpe", "trades", "weekly_fills", "weekly_open")
        }
    return year, start, args["spx"].index[args["spx"].index < end][-1], results


def event_study(events, stock, spy, breaks, membership):
    """One position per stock and variant. No cross-window trades, no synthetic liquidation."""
    dates = spy.index
    ledgers = []
    for lo, hi in PERIODS:
        boundary = dates.searchsorted(hi)
        year = lo.year
        for mode in VARIANTS:
            occupied = {}
            book = book_for(mode, {}, breaks)
            for row in events:
                s, day = row["symbol"], row["day"]
                if not lo <= day < hi or s not in membership[year] or not eligible(row, mode):
                    continue
                signal_idx = dates.get_loc(day)
                if signal_idx < occupied.get(s, -1):
                    continue
                entry = signal_idx + 1
                px = stock[s]
                trade = {
                    "period": year,
                    "variant": mode,
                    "symbol": s,
                    "signal": day,
                    "entry": None,
                    "exit": None,
                    "outcome": "no_fill",
                    "reason": None,
                    "ret": None,
                    "spy": None,
                    "excess": None,
                    "held": None,
                    "filed": row["filed"],
                    "accession": row["accession"],
                }
                if entry >= boundary or not np.isfinite(px[entry]):
                    ledgers.append(trade)
                    continue
                fill = px[entry]
                pos = {"entry": fill, "entered": dates[entry]}
                trade.update(entry=dates[entry], entry_price=fill, outcome="censored")
                # A drawdown through the stop can carry through the next close, including gaps.
                for i in range(entry, boundary - 1):
                    reason = book.exit_reason(s, dates[i], px[i], pos)
                    if reason is None:
                        continue
                    out = i + 1
                    while out < boundary and not np.isfinite(px[out]):
                        out += 1
                    if out == boundary:
                        break
                    gross = px[out] / fill
                    ret = gross * (1 - bt.COST) / (1 + bt.COST) - 1
                    bench = spy.iat[out] / spy.iat[entry] - 1
                    trade.update(
                        exit=dates[out],
                        exit_price=px[out],
                        reason=reason,
                        outcome="closed",
                        ret=100 * ret,
                        spy=100 * bench,
                        excess=100 * (ret - bench),
                        held=out - entry,
                    )
                    occupied[s] = out
                    break
                if trade["outcome"] == "censored":
                    occupied[s] = boundary
                for horizon in (4, 13, 26):
                    stop = dates.searchsorted(dates[entry] + pd.Timedelta(weeks=horizon))
                    if stop < boundary and np.isfinite(px[stop]):
                        ret = px[stop] / fill * (1 - bt.COST) / (1 + bt.COST) - 1
                        trade[f"excess_{horizon}w"] = 100 * (
                            ret - (spy.iat[stop] / spy.iat[entry] - 1)
                        )
                ledgers.append(trade)
    return pd.DataFrame(ledgers)


def matched_controls(ledger, events, candidates, membership, stock, dates):
    """Same-week quality rebound elsewhere in its uptrend; tie break fixed before forward returns."""
    source = {(r["symbol"], r["day"]): r for r in events if r["weeks"] == 200}
    matched = []
    for trade in ledger[(ledger.variant == PRIMARY) & ledger.entry.notna()].itertuples():
        row = source[trade.symbol, trade.signal]
        pool = [
            (abs(dd - row["prior_dd"]), s)
            for dd, s in candidates.get(trade.signal, ())
            if s in membership[trade.period] and s != trade.symbol
        ]
        result = {
            "period": trade.period,
            "symbol": trade.symbol,
            "signal": trade.signal,
            "control": None,
            "entry": trade.entry,
            "paired_13w": None,
        }
        if pool:
            gap, other = min(pool)
            result.update(control=other, prior_drawdown_gap=100 * gap)
            i = dates.get_loc(trade.entry)
            j = dates.searchsorted(trade.entry + pd.Timedelta(weeks=13))
            until = next(end for lo, end in PERIODS if lo.year == trade.period)
            if j < len(dates) and dates[j] < until:
                a, b = stock[trade.symbol], stock[other]
                if all(np.isfinite(v) and v > 0 for v in (a[i], a[j], b[i], b[j])):
                    result["paired_13w"] = (
                        100 * (a[j] / a[i] - b[j] / b[i]) * (1 - bt.COST) / (1 + bt.COST)
                    )
        matched.append(result)
    return matched


def summarize_events(ledger):
    rows = []
    for (period, mode), df in ledger.groupby(["period", "variant"]):
        closed = df[df.outcome == "closed"]
        obs = closed.excess
        row = {
            "period": period,
            "variant": mode,
            "n": len(closed),
            "tickers": closed.symbol.nunique(),
            "censored": (df.outcome == "censored").sum(),
            "no_fill": (df.outcome == "no_fill").sum(),
            "mean": obs.mean(),
            "median": obs.median(),
            "beat_spy": (obs > 0).mean() * 100,
            "net_return": closed.ret.mean(),
            "p05_net": closed.ret.quantile(0.05),
            "worst": closed.ret.min(),
            "held_median": closed.held.median(),
        }
        for h in (4, 13, 26):
            series = df.get(f"excess_{h}w", pd.Series(dtype=float)).dropna()
            row[f"n_{h}w"] = len(series)
            row[f"median_{h}w"] = series.median()
        rows.append(row)
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", choices=("core", "external"), default="core")
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--events-only", action="store_true")
    args = parser.parse_args()
    OUT.mkdir(exist_ok=True)
    records = list(csv.DictReader((HERE / "universe.csv").open()))
    if args.sample == "external":
        samples = list(csv.DictReader((HERE / "replication.csv").open()))
        membership = {
            y.year: {r["quote"] for r in samples if r["period"] == str(y.year)} for y, _ in PERIODS
        }
        records = [
            {"symbol": s, "quote": s, "currency": "USD", "sector": None}
            for s in sorted(set.union(*membership.values()))
        ]
    else:
        membership = {y.year: {r["symbol"] for r in records} for y, _ in PERIODS}
    spx = read_chart("^GSPC").close
    spy = read_chart("SPY").close.reindex(spx.index)
    assert not spy.isna().any() and spx.index[-1] == pd.Timestamp("2026-11-20")
    events, breaks, frames, stock, coverage, annuals = (
        [],
        {w: defaultdict(set) for w in (40, 200)},
        {},
        {},
        [],
        [],
    )
    controls = defaultdict(list)
    case = []
    for rec in records:
        s, q = rec["symbol"], rec["quote"]
        p = read_chart(q)
        sec_path = CACHE / (q + ".annual.gz")
        sec = load(sec_path) if sec_path.exists() else {}
        reports = Reports(sec.get("reports", []))
        annuals.extend(
            dict(
                symbol=s,
                cik=sec.get("cik"),
                filed=r["filed"],
                end=r["end"],
                accession=r["accession"],
                prior_end=r["previous_end"],
                quality=r["quality"],
                **{"current_" + k: v for k, v in r["current"].items()},
                **{"prior_" + k: v for k, v in r["previous"].items()},
            )
            for r in reports.rows
        )
        doc = {
            "symbol": s,
            "quote": q,
            "price_rows": len(p) if p is not None else 0,
            "first": p.index[0] if p is not None and len(p) else None,
            "last": p.index[-1] if p is not None and len(p) else None,
            "annuals": len(reports.rows),
            "years_known": sum(r["quality"] is not None for r in reports.rows),
            "cik": sec.get("cik"),
            "price_sha256": hashlib.sha256(
                pd.util.hash_pandas_object(p, index=True).values.tobytes()
            ).hexdigest()
            if p is not None
            else None,
        }
        for lo, hi in PERIODS:
            doc.update({f"{kind}_{lo.year}": 0 for kind in ("weeks", "known", "pass")})
        coverage.append(doc)
        if p is None or len(p) < bt.WARMUP + 60:
            continue
        if args.sample == "core":
            frames[s] = (
                bt.indicators(p.close, p.high, p.low, p.volume).reindex(spx.index).loc["2013":]
            )
        if rec["currency"] != "USD":
            continue
        stock[s] = p.close.reindex(spx.index).to_numpy()
        bars = weekly_bars(p, spx.index)
        for lo, hi in PERIODS:
            if s not in membership[lo.year]:
                continue
            dated = bars.loc[
                bars.session.ge(lo) & bars.session.lt(hi) & bars.line.notna() & bars.complete
            ]
            quality = [(reports.at(d) or {}).get("quality") for d in dated.session]
            doc[f"weeks_{lo.year}"] = len(dated)
            doc[f"known_{lo.year}"] = sum(v is not None for v in quality)
            doc[f"pass_{lo.year}"] = sum(v is True for v in quality)
        for r in bars[bars.control].itertuples():
            if (reports.at(r.session) or {}).get("quality") is True:
                controls[r.session].append((r.prior_dd, s))
        if s == "NVDA":
            plotted = bars.close.rolling(200).mean()
            case = [
                {
                    "week": r.session,
                    "close": r.close,
                    "low": r.low,
                    "high": r.high,
                    "prior_sma200": r.line,
                    "chart_sma200": plotted.at[r.Index],
                    "touch": r.touch,
                    "confirmed": r.confirm,
                    "quality": (reports.at(r.session) or {}).get("quality"),
                }
                for r in bars.tail(8).itertuples()
            ]
        for weeks, levels in ((200, bars), (40, weekly_bars(p, spx.index, 40))):
            observations, below = collect(s, levels, reports, weeks)
            events.extend(observations)
            for day in below:
                breaks[weeks][day].add(s)
    events = [
        r
        for r in events
        if any(lo <= r["day"] < hi and r["symbol"] in membership[lo.year] for lo, hi in PERIODS)
    ]
    events.sort(key=lambda r: (r["day"], r["symbol"]))
    for name, rows in [("coverage", coverage), ("annuals", annuals), ("signals", events)]:
        write_csv(f"{args.sample}_{name}.csv", rows)
    if case:
        write_csv("nvda.csv", case)
    ledger = event_study(events, stock, spy, breaks, membership)
    ledger.to_csv(OUT / f"{args.sample}_trades.csv", index=False, float_format="%.10g")
    write_csv(f"{args.sample}_events.csv", summarize_events(ledger))
    matched = matched_controls(ledger, events, controls, membership, stock, spy.index)
    write_csv(f"{args.sample}_controls.csv", matched)
    if args.sample == "core" and not args.events_only:
        books = {}
        for mode in VARIANTS:
            entries = defaultdict(list)
            for row in events:
                if eligible(row, mode):
                    entries[row["day"]].append((row["distance"], row["symbol"]))
            books[mode] = book_for(mode, entries, breaks)
        print("Portfolio runs", len(frames), flush=True)
        write_portfolios(
            spx.loc["2013":],
            frames,
            {r["symbol"]: r["sector"] for r in records},
            books,
            args.workers,
        )


if __name__ == "__main__":
    main()
