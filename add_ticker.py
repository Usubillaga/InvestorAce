#!/usr/bin/env python3
"""
add_ticker.py · v3 · safe, idempotent ticker adder

Usage:
    python add_ticker.py ASML.AS

The script adds only Yahoo-supplied mechanical data. It does not pretend that
Yahoo can determine the model's two judgement fields (deliver and clock).

The generated row is marked built='auto'. Negative/non-usable FCF is converted
to fcf=None with an explanatory na= reason so the engine cannot create a fake
NGV from negative cash flow.
"""
from __future__ import annotations

import math
import os
import re
import sys
from pathlib import Path

import yfinance as yf
from autoscore import auto_row

TARGET = Path(os.environ.get("INVESTORACE_ENGINE", "engine.py"))

LONDON_PENCE_SUFFIX = ".L"

KNOWN_FIX = {
    "ENG": ("ENG.MC", "Enagas — ENGIE uses ENGI.PA and is a different company"),
    "SAN": ("SAN.PA", "Sanofi — SAN.MC is Banco Santander"),
    "ENB": ("ENB.TO", "use .TO for the CAD listing"),
    "MUV2": ("MUV2.DE", "Munich Re"),
    "NVO": ("NVO", "NYSE ADR quotes USD; NOVO-B.CO quotes DKK"),
}


def clean_number(value):
    """Return a finite float or None."""
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return None if not math.isfinite(value) else value


def normalize_symbol(raw):
    """Normalize a Yahoo symbol and apply known ticker corrections."""
    symbol = (raw or "").strip().upper()
    if not symbol:
        raise ValueError("ticker is empty")

    # Common accidental spaces are removed, but internal punctuation is kept.
    symbol = re.sub(r"\s+", "", symbol)

    key = symbol.split(".", 1)[0]
    if key in KNOWN_FIX:
        expected, _ = KNOWN_FIX[key]
        if symbol == key:
            symbol = expected

    # Yahoo's London listing reports pence; preserve .L.
    return symbol


def extract_data_row(text):
    """Return the insertion position immediately before DATA's closing brace."""
    match = re.search(r"(?m)^DATA\s*=\s*\{", text)
    if not match:
        raise RuntimeError('could not find "DATA = {" in engine.py')

    pos = match.end()
    close = text.find("\n}", pos)
    if close < 0:
        raise RuntimeError("could not find the closing brace of DATA")
    return close + 1


def has_ticker(text, key):
    return re.search(rf"(?m)^\s*['\"]{re.escape(key)}['\"]\s*:", text) is not None


def format_dict_as_python(row):
    """
    Use repr() only for values, with a stable dict(...) representation that is
    valid Python and easy for a human to edit later.
    """
    parts = []
    for key, value in row.items():
        parts.append(f"{key}={value!r}")
    return f"'{row['yf'].split('.')[0]}': dict({', '.join(parts)}),\n"


def repair_negative_fcf(row, warning_list):
    """Never persist a negative FCF as an NGV-producing number."""
    fcf = clean_number(row.get("fcf"))
    if fcf is None:
        return

    if fcf <= 0:
        row["fcf"] = None
        row["na"] = (
            f'FCF non-positive ({fcf:,.1f}m from Yahoo); '
            "NGV intentionally disabled until a model-appropriate metric is supplied"
        )
        row["built"] = "auto"
        warning_list.append(
            f"FCF is non-positive ({fcf:,.1f}m); wrote fcf=None and na= instead"
        )


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print("usage: python add_ticker.py <YAHOO_TICKER>", file=sys.stderr)
        return 2

    try:
        symbol = normalize_symbol(argv[0])
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    key = symbol.split(".", 1)[0]

    if not TARGET.exists():
        print(f"ERROR: target file not found: {TARGET}", file=sys.stderr)
        return 1

    source = TARGET.read_text(encoding="utf-8")
    if has_ticker(source, key):
        print(f"{key} is already in DATA. Nothing written.")
        return 0

    # One source of truth: autoscore owns the Yahoo extraction and calculations.
    try:
        row, warnings = auto_row(symbol)
    except Exception as exc:
        print(f"ERROR: Yahoo/autoscore failed for {symbol}: {type(exc).__name__}: {exc}")
        return 1

    warnings = list(warnings or [])

    if row is None:
        print(f"ERROR: could not build a row for {symbol}.")
        for warning in warnings:
            print(f"  ! {warning}")
        return 1

    row["yf"] = symbol
    row["built"] = "auto"

    # Normalize currency for London listings.
    if symbol.endswith(LONDON_PENCE_SUFFIX) and str(row.get("cur") or "").upper() == "GBP":
        row["cur"] = "GBp"

    # Make missing sanity ranges explicit and valid.
    sanity = row.get("sanity")
    if sanity is not None:
        try:
            lo, hi = sanity
            lo = clean_number(lo)
            hi = clean_number(hi)
            row["sanity"] = (lo, hi) if lo is not None and hi is not None and 0 <= lo < hi else None
        except (TypeError, ValueError):
            row["sanity"] = None

    repair_negative_fcf(row, warnings)

    if symbol == key and key in KNOWN_FIX:
        expected, explanation = KNOWN_FIX[key]
        warnings.append(f"known ticker mapping applied: {key} -> {expected} ({explanation})")

    if row.get("sanity") is None:
        warnings.append("no valid 52-week sanity range; price validation will be unbounded")

    # Defensive compile check before touching the real engine.py.
    entry = format_dict_as_python(row)
    candidate = source[:extract_data_row(source)] + entry + source[extract_data_row(source):]

    try:
        compile(candidate, str(TARGET), "exec")
    except SyntaxError as exc:
        print(f"ERROR: generated engine.py would not compile: {exc}", file=sys.stderr)
        return 1

    TARGET.write_text(candidate, encoding="utf-8")

    print(f"ADDED {key} ({symbol})")
    print(f"  built={row.get('built')} | sector={row.get('sector') or 'unknown'}")
    print(f"  currency={row.get('cur') or 'unknown'} | FCF={row.get('fcf')}")
    print(f"  shares={row.get('shares')} | sanity={row.get('sanity')}")
    print("  NGV, cover, score, risk, verdict and regime will be recomputed by engine.py.")

    for warning in warnings:
        print(f"  ! {warning}")

    print("\nHUMAN REVIEW STILL REQUIRED:")
    print("  deliver  Replace the revenue-growth proxy with the company's own leading metric.")
    print("  clock    Confirm CLOCK / CONC / DIV.")
    print("  special  REITs use AFFO; pipelines use DCF/distributable cash flow.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
