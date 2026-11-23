"""Freeze chart responses and dated annual SEC rows. Run from repository root."""

import csv
import gzip
import json
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
UNTIL = date(2026, 11, 21)  # exclusive, after the last completed Friday
START = date(2005, 1, 1)
TAGS = {
    "profit": ["NetIncomeLoss"],
    "assets": ["Assets"],
    "ocf": ["NetCashProvidedByUsedInOperatingActivities"],
    "capex": ["PaymentsToAcquireProductiveAssets", "PaymentsToAcquirePropertyPlantAndEquipment"],
}
DATA_ERRORS = (OSError, ValueError, KeyError, TypeError, IndexError)
SEC_MAP = "https://www.sec.gov/files/company_tickers.json"


def get(url):
    for attempt in range(3):
        try:
            request = Request(
                url,
                headers={
                    "User-Agent": "InvestorAce weekly historical research (github.com/Usubillaga/InvestorAce)"
                },
            )
            with urlopen(request, timeout=30) as response:
                return json.load(response)
        except (OSError, ValueError):
            if attempt == 2:
                raise
            time.sleep(1 + attempt)


def save(path, data):
    tmp = path.with_suffix(".tmp")
    with gzip.open(tmp, "wt") as stream:
        json.dump(data, stream, separators=(",", ":"), allow_nan=False)
    tmp.replace(path)


def load(path):
    with gzip.open(path, "rt") as stream:
        return json.load(stream)


def epoch(day):
    return int(datetime.combine(day, datetime.min.time(), UTC).timestamp())


def chart(symbol):
    path = CACHE / (symbol + ".prices.gz")
    if path.exists():
        return
    qs = f"period1={epoch(START)}&period2={epoch(UNTIL)}&interval=1d"
    for host in ["query1", "query2"]:
        try:
            url = f"https://{host}.finance.yahoo.com/v8/finance/chart/{quote(symbol)}?{qs}"
            data = get(url)["chart"]["result"][0]
            if data["meta"]["symbol"].upper() != symbol.upper() or not data.get("timestamp"):
                raise ValueError(f"No matching dated prices for {symbol}")
            save(path, data)
            return
        except DATA_ERRORS as exc:
            last = exc
    raise last


def annual_rows(raw):
    """Use original annual 10-Ks and contemporaneous comparative figures in that same filing."""
    groups = {}
    for typ, tags in TAGS.items():
        for tag in tags:
            for row in (
                raw.get("facts", {}).get("us-gaap", {}).get(tag, {}).get("units", {}).get("USD", [])
            ):
                if (
                    row.get("form") != "10-K"
                    or row.get("fp") != "FY"
                    or row.get("filed", "") >= UNTIL.isoformat()
                ):
                    continue
                end = date.fromisoformat(row["end"])
                if typ != "assets" and (
                    "start" not in row
                    or not 345 <= (end - date.fromisoformat(row["start"])).days <= 385
                ):
                    continue
                key = (row["filed"], row["accn"])
                record = groups.setdefault(key, {})
                values = record.setdefault(row["end"], {})
                if typ not in values:
                    values[typ] = row["val"]
                    if typ == "capex":
                        values["capex_tag"] = tag
    reports = []
    for (filed, accession), facts in sorted(groups.items()):
        periods = sorted(facts, reverse=True)
        end = periods[0]
        if (date.fromisoformat(filed) - date.fromisoformat(end)).days not in range(1, 181):
            continue
        prior = next(
            (
                p
                for p in periods
                if 345 <= (date.fromisoformat(end) - date.fromisoformat(p)).days <= 385
            ),
            None,
        )
        current, previous = facts[end], facts.get(prior, {})
        known = (
            set(TAGS) <= current.keys()
            and {"profit", "ocf", "capex"} <= previous.keys()
            and current["assets"] > 0
            and min(current["capex"], previous["capex"]) >= 0
        )
        passed = (
            (
                current["profit"] / current["assets"] >= 0.05
                and previous["profit"] > 0
                and all(r["ocf"] > r["capex"] for r in (current, previous))
            )
            if known
            else None
        )
        reports.append(
            {
                "filed": filed,
                "accession": accession,
                "end": end,
                "previous_end": prior,
                "current": current,
                "previous": previous,
                "quality": passed,
            }
        )
    return reports


def fetch_sec(item):
    sym, cik = item
    path = CACHE / (sym + ".annual.gz")
    if path.exists():
        return
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
    raw = get(url)
    if int(raw["cik"]) != cik:
        raise ValueError(f"Unexpected issuer for {sym}")
    save(path, {"cik": cik, "source": url, "reports": annual_rows(raw)})


def fetch_all(fn, jobs, workers):
    def one(j):
        try:
            fn(j)
            return None
        except DATA_ERRORS as exc:
            print(fn.__name__, j, str(exc), flush=True)
            return [str(j), str(exc)]

    with ThreadPoolExecutor(workers) as pool:
        return [v for v in pool.map(one, jobs) if v]


def main():
    CACHE.mkdir(exist_ok=True)
    records = list(csv.DictReader((HERE / "universe.csv").open()))
    symbols = [r["quote"] for r in records]
    mapping = {v["ticker"]: v["cik_str"] for v in get(SEC_MAP).values()}
    issuer_jobs = [(s, mapping[s]) for s in symbols if s in mapping and "." not in s]
    print("prices", len(symbols), "SEC", len(issuer_jobs), flush=True)
    with ThreadPoolExecutor(2) as pool:
        prices = pool.submit(fetch_all, chart, symbols + ["^GSPC", "SPY"], 7)
        sec = pool.submit(fetch_all, fetch_sec, issuer_jobs, 3)
        errors = {"prices": prices.result(), "sec": sec.result()}
    print(errors, flush=True)
    (CACHE / "errors.json").write_text(json.dumps(errors))


if __name__ == "__main__":
    main()
