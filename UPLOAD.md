# What to upload, and in what order

Four files. Three replace existing ones, one is new.

| File | Action | Repo path |
|---|---|---|
| `wacc.py` | **replace** | `wacc.py` |
| `integrity.py` | **replace** | `integrity.py` |
| `engine.py` | **replace** | `engine.py` |
| `reprice.py` | **add** | `reprice.py` |

Nothing else in the repo is touched. No data files, no `history/`, no
`index.html`, no `regime_contract.json`.

---

## Before you upload: set the one decision

Open `engine.py`, find `RISK_FREE_MODE` (just above `sync_risk_free()`):

```python
RISK_FREE_MODE = 'spot'            # 'spot' | 'normalized'
RISK_FREE_NORMALIZED = 4.40        # % -- only consulted when mode is 'normalized'
RISK_FREE_NORMALIZED_DRIFT_BP = 150
```

- **`'spot'`** (default) prices the book on the observed 10y — 5.04% today.
  This is `wacc.py`'s stated design intent. It also imports a cyclical-peak
  yield into a perpetuity with no terminal value to absorb it.
- **`'normalized'`** prices on 4.40%, and the staleness check widens to tolerate
  the deliberate gap while printing it as a warning on **every** build.

This is the difference between roughly −9% and −23% on NGV depending on the row,
and it moves every entry price in the book. It is left as a literal you have to
look at on purpose.

---

## Upload order matters

**Do not push straight to `main`.** `main` → Actions cron → Pages, so a merge
publishes a fully repriced board before you have seen the diff.

1. Push to a branch (`fix/risk-free-staleness`).
2. On that branch, run `python reprice.py 4.40 5.04` and read the table.
3. Set `RISK_FREE_MODE` to what you decided.
4. Merge.

If you use git rather than the web UI, `investorace-riskfree-fix.patch` applies
the whole thing in one step:

```
git checkout -b fix/risk-free-staleness
git apply investorace-riskfree-fix.patch
python reprice.py 4.40 5.04
```

---

## What breaks if you get it wrong

`risk_free_faults()` is **blocking**. If `RISK_FREE_MODE` is `'normalized'` but
you leave the tolerance at the default 50bp, the 64bp gap to spot fails the
build and `index.html` is never written. That is the check working — it refuses
to let "the rate we price on" and "the rate the market shows" diverge silently.
Widen `RISK_FREE_NORMALIZED_DRIFT_BP` deliberately or stay on `'spot'`.

If the `^TNX` pull fails at build time, `sync_risk_free()` falls back to the
workbook literal, `LIVE_10Y` stays `None`, and the staleness check downgrades to
a warning rather than blocking — a failed network call should not kill a deploy.

---

## Verified before shipping

- `python wacc.py` still reproduces both source workbooks: JNJ 5.34% vs 5.36%,
  AAPL 8.66% vs 8.67%. The new `bands()` do not disturb them.
- Both risk-free modes tested: `'spot'` clean, `'normalized'` warns at 64bp
  without blocking, a stale literal blocks at 137bp.
- All four files compile.
- `REGIME_GOLDEN` regression checks are unaffected — `_regime_fixture()` uses
  synthetic covers, so they do not move with the discount rate.

**Not verified:** `reprice.py` has never been run against live data. This
sandbox has no `yfinance` and no Yahoo access. Every per-row number in the
write-up (LVMH 94%→80%, the −23.3%/−8.9% range) is computed at representative
WACC levels, not from your actual betas. `reprice.py` is the thing that produces
the real ones, and its first live run is also its first real test.

---

## Still outside this patch

- **INFLATION is unreachable.** `macro.read_macro()` has four branches;
  `regime_contract.json` defines five regimes. Either wire a third axis or
  delete the dead weights. Editing that file changes `regime_spec_sha256()` and
  blocks the build until you update `REGIME_SPEC_EXPECTED_SHA256` — by design.
- **`^TNX` sits in the inflation impulse** and now also sets the discount rate.
  The Fed hiking mechanically pushes the regime classifier. Feature or
  double-count, but it should be decided.
- **The live proximity alerts are void.** Every AT NGV / CLEARS / NEAR ENTRY on
  the published board was computed at rf 3.67; `entry_price()` is NGV/0.6, so
  they are all 9–23% too high until the rebuild.
