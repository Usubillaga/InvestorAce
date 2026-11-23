"""Fixed historical large-cap samples outside the InvestorAce universe; no outcome-based replacements."""

import csv
import hashlib
from concurrent.futures import ThreadPoolExecutor
from io import StringIO
from urllib.request import urlopen

from .download import HERE, SEC_MAP, chart, fetch_all, fetch_sec, get

SOURCE = (
    "https://raw.githubusercontent.com/fja05680/sp500/"
    "a2430f2af0c79ddf0748e91de11bdeb1616ab5a7/sp500_ticker_start_end.csv"
)


def main():
    ranges = list(csv.reader(StringIO(urlopen(SOURCE, timeout=30).read().decode("utf-8-sig"))))[1:]
    universe = {r["quote"] for r in csv.DictReader((HERE / "universe.csv").open())}
    groups = []
    for year in (2014, 2018, 2022):
        cutoff = f"{year}-01-01"
        members = {
            s.replace(".", "-")
            for s, start, end in ranges
            if start <= cutoff and (not end or cutoff < end)
        }
        candidates = members - universe
        fixed = sorted(
            candidates, key=lambda s: hashlib.sha256(("weekly200-v1/" + s).encode()).hexdigest()
        )[:150]
        groups += [(year, s) for s in fixed]
    with (HERE / "replication.csv").open("w") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["period", "quote"])
        writer.writerows(groups)
    unique = sorted({s for _, s in groups})
    mapping = {row["ticker"]: row["cik_str"] for row in get(SEC_MAP).values()}
    issuer_jobs = [(s, mapping[s]) for s in unique if s in mapping]
    print("replication unique", len(unique), "SEC targets", len(issuer_jobs), flush=True)
    with ThreadPoolExecutor(2) as pool:
        a = pool.submit(fetch_all, chart, unique, 6)
        b = pool.submit(fetch_all, fetch_sec, issuer_jobs, 2)
        print("failures", a.result(), b.result(), flush=True)


if __name__ == "__main__":
    main()
